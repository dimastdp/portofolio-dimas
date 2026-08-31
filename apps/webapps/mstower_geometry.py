"""MStower PROFILE/UDP geometry parser and 2D/3D renderer.

The renderer uses two geometry sources:
* Standard PROFILE FACE/PLAN/HIP patterns are reconstructed from explicit
  connectivity templates derived from the MStower/OpenTower Standard Panels
  diagrams. Only validated patterns are rendered; unknown patterns are skipped
  with warnings instead of being replaced by a misleading generic pattern.
* Any PROFILE geometry reference containing a token that starts with ``@`` is
  treated as a UDP call. UDP NODE/MEMB connectivity is plotted directly from
  its coordinates (local Z is translated to the
  target PROFILE panel; X/Y are not re-scaled).

A section/member assignment <= 0 always means that member does not exist and
is therefore omitted from the model and plots.

Keep this file in the same directory as the main Streamlit .py file.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

GEOMETRY_API_VERSION = "22.2"


# -----------------------------------------------------------------------------
# Data models
# -----------------------------------------------------------------------------
Point3D = Tuple[float, float, float]


@dataclass
class SectionInfo:
    section_id: int
    profile: str = ""
    fy: Optional[float] = None
    category: str = ""


@dataclass
class ProfileLine:
    line_type: str
    pattern: str
    assignments: Dict[str, int] = field(default_factory=dict)
    qualifier: str = ""
    options: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass
class PanelSpec:
    sequence: int
    panel_no: int
    height: float
    tw_explicit: Optional[float]
    z_bottom: float = 0.0
    z_top: float = 0.0
    width_bottom: float = 0.0
    width_top: float = 0.0
    face_lines: List[ProfileLine] = field(default_factory=list)
    plan_lines: List[ProfileLine] = field(default_factory=list)
    hip_lines: List[ProfileLine] = field(default_factory=list)
    # Every geometry statement that contains an @TOKEN is stored here and
    # resolved as a UDP reference, irrespective of the geometry keyword.
    udp_lines: List[ProfileLine] = field(default_factory=list)


@dataclass
class TowerMember:
    panel_sequence: int
    panel_no: int
    line_type: str
    pattern: str
    family: str
    member_key: str
    section_id: Optional[int]
    section_profile: str
    fy: Optional[float]
    category: str
    start: Point3D
    end: Point3D
    note: str = ""


@dataclass
class TowerGeometry:
    title_1: str
    title_2: str
    faces: int
    wbase: float
    rlbas: float
    total_height: float
    panels: List[PanelSpec]
    members: List[TowerMember]
    warnings: List[str] = field(default_factory=list)
    used_face_patterns: List[str] = field(default_factory=list)
    used_plan_patterns: List[str] = field(default_factory=list)
    used_hip_patterns: List[str] = field(default_factory=list)


@dataclass
class UDPNode:
    node_id: int
    x: float
    y: float
    z: float


@dataclass
class UDPMember:
    member_id: int
    node_i: int
    node_j: int
    section_id: Optional[int] = None
    member_type: str = "UDP"


@dataclass
class UDPDefinition:
    name: str
    height: float
    top_width: float
    bottom_width: float
    nodes: Dict[int, UDPNode] = field(default_factory=dict)
    members: List[UDPMember] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Public pattern registry
# -----------------------------------------------------------------------------
# The registry intentionally separates pattern recognition from connectivity.
# Adding a new MStower mnemonic only requires extending the renderer functions.
# Patterns below have explicit diagram-based connectivity in this module.
# Unknown patterns are intentionally skipped rather than drawn using a generic
# shape, because a visually plausible but topologically wrong panel is worse
# than an explicit review warning.
SUPPORTED_FACE_PATTERNS = {
    "X", "XTN", "XH1", "XH3", "XH3A",
    "K", "K1", "K1M", "K2", "K2A",
}
SUPPORTED_PLAN_PATTERNS = {
    "PL2A", "PL3S",
}
SUPPORTED_HIP_PATTERNS = {
    "HKA",
}

# Families exposed to the UI. PBR means Plan Bracing to stay compatible with
# the existing application tables; the native MStower keys remain PB1..PB10.
FAMILY_ORDER = ["LEG", "BR", "HOR", "RED", "PBR", "HIP", "CROSS", "UDP"]


# -----------------------------------------------------------------------------
# Source helpers
# -----------------------------------------------------------------------------
def _source_lines(content: str) -> List[str]:
    if content is None:
        return []
    text = str(content).replace("\r\n", "\n").replace("\r", "\n")
    # Keep tabs/newlines; strip other control bytes often found in .mst/.twr.
    text = "".join(ch if ch in "\n\t" or ord(ch) >= 32 else " " for ch in text)
    return text.splitlines()


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", str(line).strip())


def _num(value: Any) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _int_num(value: Any) -> Optional[int]:
    val = _num(value)
    if val is None:
        return None
    return int(round(val))


def _parse_section_catalog(content: str) -> Dict[int, SectionInfo]:
    catalog: Dict[int, SectionInfo] = {}
    capturing = False
    category = "Standard"
    for raw in _source_lines(content):
        line = _clean(raw)
        if not line:
            continue
        upper = line.upper()
        if not capturing:
            if re.match(r"^SECTIONS\b", upper):
                capturing = True
            continue
        if re.match(r"^END\b", upper):
            break
        if line.startswith("$"):
            if "STRENGTHENED" in upper:
                category = "Strengthened"
            continue
        if upper.startswith("LIBR "):
            continue
        m = re.match(r"^(\d+)\s+(\S+)(.*)$", line)
        if not m:
            continue
        sid = int(m.group(1))
        profile = m.group(2)
        fy_m = re.search(r"\bFY\s+([-+]?\d+(?:\.\d+)?)", m.group(3), re.I)
        fy = float(fy_m.group(1)) if fy_m else None
        catalog[sid] = SectionInfo(sid, profile, fy, category)
    return catalog


def _catalog_from_dataframe(df: Optional[pd.DataFrame]) -> Dict[int, SectionInfo]:
    if df is None or df.empty:
        return {}
    out: Dict[int, SectionInfo] = {}
    for _, row in df.iterrows():
        sid = _int_num(row.get("Section ID"))
        if sid is None:
            continue
        fy = _num(row.get("fy"))
        out[sid] = SectionInfo(
            section_id=sid,
            profile=str(row.get("Section / Profile", "") or ""),
            fy=fy,
            category=str(row.get("Category", "") or ""),
        )
    return out


def _parse_profile_line(line: str) -> Optional[ProfileLine]:
    """Parse one PROFILE geometry statement.

    MStower uses ``@NAME`` to call a User Defined Panel (UDP).  The ``@`` is
    the authoritative discriminator: if *any* token after the geometry keyword
    starts with ``@``, the statement is returned as a UDP reference regardless
    of whether the keyword is FACE, PLAN, HIP, CROSSARM, or another geometry
    directive.  This prevents a custom panel from being mistaken for a
    standard-panel mnemonic.
    """
    cleaned = _clean(line)
    tokens = cleaned.split()
    if len(tokens) < 2:
        return None

    line_type = tokens[0].upper()

    # IMPORTANT: @ is authoritative. Search every token after the directive so
    # syntax variants such as ``FACE @POLE6`` or another geometry directive
    # containing ``@CUSTOM`` all resolve through the UDP engine.
    udp_token = next((tok for tok in tokens[1:] if str(tok).startswith("@")), None)
    if udp_token is not None:
        return ProfileLine(
            line_type=line_type,
            pattern=str(udp_token).upper(),
            assignments={},
            qualifier="",
            options={"UDP_REFERENCE": True},
            raw=cleaned,
        )

    # Standard geometry currently modelled by this renderer.
    if line_type not in {"FACE", "PLAN", "HIP"}:
        return None

    pattern = tokens[1].upper()
    assignments: Dict[str, int] = {}
    options: Dict[str, Any] = {}
    qualifiers: List[str] = []

    member_regex = {
        "FACE": re.compile(r"^(?:LEG|BR\d+|H\d+|R\d+)$", re.I),
        "PLAN": re.compile(r"^PB\d+$", re.I),
        "HIP": re.compile(r"^HP\d+$", re.I),
    }[line_type]

    flag_tokens = {"TOP", "BTM", "XIP", "MID", "INV", "LEFT", "RIGHT", "D", "VU", "VD"}
    idx = 2
    while idx < len(tokens):
        key = tokens[idx].upper()
        if key in flag_tokens:
            if key in {"TOP", "BTM", "XIP", "MID"}:
                qualifiers.append(key)
            else:
                options[key] = True
            idx += 1
            continue

        if key == "SPACE":
            vals: List[str] = []
            idx += 1
            while idx < len(tokens):
                nxt = tokens[idx].upper()
                if member_regex.match(nxt) or nxt in flag_tokens or nxt in {"F1", "F2", "NTR", "ND", "NPL"}:
                    break
                vals.append(tokens[idx])
                idx += 1
            options["SPACE"] = vals
            continue

        if idx + 1 < len(tokens):
            value = tokens[idx + 1]
            if member_regex.match(key):
                iv = _int_num(value)
                if iv is not None:
                    assignments[key] = iv
                idx += 2
                continue
            if key in {"F1", "F2", "NTR", "ND", "NPL", "LA", "LB", "LC", "LD"}:
                options[key] = _num(value) if _num(value) is not None else value
                idx += 2
                continue
        idx += 1

    qualifier = "/".join(dict.fromkeys(qualifiers))
    return ProfileLine(
        line_type=line_type,
        pattern=pattern,
        assignments=assignments,
        qualifier=qualifier,
        options=options,
        raw=cleaned,
    )


def parse_profile(content: str) -> Tuple[Dict[str, Any], List[PanelSpec]]:
    """Parse the MStower PROFILE block, preserving panel sequence."""
    meta: Dict[str, Any] = {
        "title_1": "",
        "title_2": "",
        "faces": 4,
        "wbase": 0.0,
        "rlbas": 0.0,
    }
    lines = _source_lines(content)

    for raw in lines:
        line = _clean(raw)
        up = line.upper()
        if up.startswith("TITL1 "):
            meta["title_1"] = line[6:].strip()
        elif up.startswith("TITL2 "):
            meta["title_2"] = line[6:].strip()

    panels: List[PanelSpec] = []
    capturing = False
    current: Optional[PanelSpec] = None

    for raw in lines:
        line = _clean(raw)
        if not line:
            continue
        upper = line.upper()

        if not capturing:
            if re.match(r"^PROFILE\b", upper):
                capturing = True
            continue

        if re.match(r"^END\b", upper):
            break
        if line.startswith("$"):
            continue

        m = re.match(r"^FACES\s+(\d+)", line, re.I)
        if m:
            meta["faces"] = int(m.group(1))
            continue
        m = re.match(r"^WBASE\s+([-+]?\d+(?:\.\d+)?)", line, re.I)
        if m:
            meta["wbase"] = float(m.group(1))
            continue
        m = re.match(r"^(?:RLBAS|RLBASE)\s+([-+]?\d+(?:\.\d+)?)", line, re.I)
        if m:
            meta["rlbas"] = float(m.group(1))
            continue

        m = re.match(
            r"^PANEL\s+(\d+)\s+HT\s+([-+]?\d+(?:\.\d+)?)(?:\s+TW\s+([-+]?\d+(?:\.\d+)?))?",
            line,
            re.I,
        )
        if m:
            current = PanelSpec(
                sequence=len(panels) + 1,
                panel_no=int(m.group(1)),
                height=float(m.group(2)),
                tw_explicit=float(m.group(3)) if m.group(3) is not None else None,
            )
            panels.append(current)
            continue

        if current is None:
            continue
        pl = _parse_profile_line(line)
        if pl is None:
            continue
        if pl.pattern.startswith("@") or pl.options.get("UDP_REFERENCE"):
            current.udp_lines.append(pl)
        elif pl.line_type == "FACE":
            current.face_lines.append(pl)
        elif pl.line_type == "PLAN":
            current.plan_lines.append(pl)
        elif pl.line_type == "HIP":
            current.hip_lines.append(pl)

    return meta, panels


# -----------------------------------------------------------------------------
# UDP custom component helpers
# -----------------------------------------------------------------------------
def _parse_udp_component_refs(content: str) -> Dict[str, Optional[str]]:
    """Parse COMPONENT/COMPONENTS aliases used to resolve UDP references."""
    refs: Dict[str, Optional[str]] = {}
    capturing = False
    for raw in _source_lines(content):
        line = _clean(raw)
        if not line:
            continue
        upper = line.upper()
        if not capturing:
            if re.match(r"^COMPONENTS?\b", upper):
                capturing = True
            continue
        if re.match(r"^END\b", upper):
            break

        # In COMPONENT(S), '$' can prefix an alias and is therefore not
        # treated as a comment marker here.
        candidate = line[1:].strip() if line.startswith("$") else line
        tokens = candidate.split()
        if not tokens:
            continue

        alias = tokens[0].lstrip("@").strip().upper()
        if not alias:
            continue

        filename: Optional[str] = None
        for token in tokens[1:]:
            if str(token).upper().endswith(".UDP"):
                filename = str(token).strip()
                break

        # A one-token form such as ``POLE6.UDP`` uses the stem as alias.
        if alias.endswith(".UDP"):
            filename = filename or tokens[0].strip()
            alias = re.sub(r"\.UDP$", "", alias, flags=re.I)

        refs[alias] = filename
    return refs


def _normalize_udp_sources(udp_sources: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Build a case-insensitive lookup by filename, stem *and internal UDP name*.

    The internal name is the token after ``UDP`` in the UDP header, e.g.
    ``UDP POLE6 HT 6 ...``.  This is required for PROFILE syntax such as
    ``FACE @POLE6`` when the COMPONENT block contains only ``POLE6``.
    """
    out: Dict[str, str] = {}
    for name, content in (udp_sources or {}).items():
        key = str(name).strip()
        if not key:
            continue
        text = str(content)
        base = key.replace("\\", "/").split("/")[-1]
        stem = re.sub(r"\.UDP$", "", base, flags=re.I)

        candidates = {key, base, stem, f"{stem}.UDP"}

        # Read only the UDP header name; avoid depending on the uploaded
        # filename because MStower often references the internal component name.
        internal_name = ""
        for raw in _source_lines(text):
            line = _clean(raw)
            m = re.match(r"^UDP\s+(\S+)", line, re.I)
            if m:
                internal_name = m.group(1).strip()
                break
        if internal_name:
            internal_stem = re.sub(r"\.UDP$", "", internal_name, flags=re.I)
            candidates.update({internal_name, internal_stem, f"{internal_stem}.UDP"})

        for candidate in candidates:
            if candidate:
                out[str(candidate).upper()] = text
    return out


def _resolve_udp_source(
    alias: str,
    filename: Optional[str],
    udp_sources: Dict[str, str],
) -> Optional[str]:
    candidates: List[str] = []
    if filename:
        base = str(filename).replace("\\", "/").split("/")[-1]
        stem = re.sub(r"\.UDP$", "", base, flags=re.I)
        candidates.extend([str(filename), base, stem, f"{stem}.UDP"])
    if alias:
        clean_alias = str(alias).lstrip("@").strip()
        alias_stem = re.sub(r"\.UDP$", "", clean_alias, flags=re.I)
        candidates.extend([clean_alias, alias_stem, f"{alias_stem}.UDP"])

    for candidate in candidates:
        found = udp_sources.get(str(candidate).upper())
        if found is not None:
            return found
    return None


def parse_udp_definition(content: str) -> UDPDefinition:
    """Parse a MStower UDP NODE/MEMB file for optional custom visualization."""
    name = "UDP"
    height = 0.0
    top_width = 0.0
    bottom_width = 0.0
    nodes: Dict[int, UDPNode] = {}
    members: List[UDPMember] = []

    known_member_types = {
        "LEG", "KBR", "BR", "RED", "HOR", "PBR", "HIP", "CROSS",
        "DIAG", "HORIZ", "VERT", "MEMB",
    }

    for raw in _source_lines(content):
        line = _clean(raw)
        if not line:
            continue

        m = re.match(
            r"^UDP\s+(\S+)(?:.*?\bHT\s+([-+0-9.Ee]+))?"
            r"(?:.*?\bTW\s+([-+0-9.Ee]+))?"
            r"(?:.*?\bBW\s+([-+0-9.Ee]+))?",
            line,
            re.I,
        )
        if m:
            name = m.group(1)
            if m.group(2) is not None:
                height = float(m.group(2))
            if m.group(3) is not None:
                top_width = float(m.group(3))
            if m.group(4) is not None:
                bottom_width = float(m.group(4))
            continue

        m = re.match(
            r"^NODE\s+(\d+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)",
            line,
            re.I,
        )
        if m:
            nid = int(m.group(1))
            nodes[nid] = UDPNode(
                node_id=nid,
                x=float(m.group(2)),
                y=float(m.group(3)),
                z=float(m.group(4)),
            )
            continue

        if re.match(r"^MEMB\b", line, re.I):
            tokens = line.split()
            if len(tokens) < 6:
                continue
            try:
                member_id = int(tokens[1])
                node_i = int(tokens[2])
                node_j = int(tokens[3])
            except (TypeError, ValueError):
                continue

            section_id = _int_num(tokens[5]) if len(tokens) > 5 else None
            member_type = "UDP"
            for token in reversed(tokens[6:]):
                upper = str(token).upper()
                if upper in known_member_types:
                    member_type = upper
                    break
            members.append(
                UDPMember(
                    member_id=member_id,
                    node_i=node_i,
                    node_j=node_j,
                    section_id=section_id,
                    member_type=member_type,
                )
            )

    if nodes:
        z_values = [n.z for n in nodes.values()]
        z_min = min(z_values)
        z_max = max(z_values)
        if height <= 0 and z_max > z_min:
            height = z_max - z_min
        # Fallback widths from coordinate extents only when the header omits them.
        if bottom_width <= 0:
            near_bottom = [n for n in nodes.values() if abs(n.z - z_min) < 1e-6]
            if near_bottom:
                bottom_width = 2.0 * max(max(abs(n.x), abs(n.y)) for n in near_bottom)
        if top_width <= 0:
            near_top = [n for n in nodes.values() if abs(n.z - z_max) < 1e-6]
            if near_top:
                top_width = 2.0 * max(max(abs(n.x), abs(n.y)) for n in near_top)

    return UDPDefinition(
        name=name,
        height=height,
        top_width=top_width,
        bottom_width=bottom_width,
        nodes=nodes,
        members=members,
    )


# -----------------------------------------------------------------------------
# Width/elevation generation
# -----------------------------------------------------------------------------
def _interp_piecewise(z: float, anchors: Sequence[Tuple[float, float]]) -> float:
    anchors = sorted(anchors, key=lambda x: x[0])
    if not anchors:
        return 0.0
    if z <= anchors[0][0]:
        return float(anchors[0][1])
    if z >= anchors[-1][0]:
        return float(anchors[-1][1])
    for (z0, w0), (z1, w1) in zip(anchors[:-1], anchors[1:]):
        if z0 <= z <= z1:
            if abs(z1 - z0) < 1e-12:
                return float(w1)
            t = (z - z0) / (z1 - z0)
            return float(w0 + t * (w1 - w0))
    return float(anchors[-1][1])


def _resolve_panel_geometry(meta: Dict[str, Any], panels: List[PanelSpec]) -> float:
    rlbas = float(meta.get("rlbas") or 0.0)
    wbase = float(meta.get("wbase") or 0.0)
    total_height = sum(max(0.0, p.height) for p in panels)
    z_cursor = rlbas + total_height

    anchors: List[Tuple[float, float]] = []
    if wbase > 0:
        anchors.append((rlbas, wbase))

    for panel in panels:
        panel.z_top = z_cursor
        panel.z_bottom = z_cursor - panel.height
        if panel.tw_explicit is not None:
            anchors.append((panel.z_top, panel.tw_explicit))
        z_cursor = panel.z_bottom

    # If no TW was supplied, a vertical/prismatic tower is the safest visual fallback.
    if not any(p.tw_explicit is not None for p in panels):
        if wbase <= 0:
            wbase = 1.0
            meta["wbase"] = wbase
        anchors.append((rlbas + total_height, wbase))

    # If WBASE is absent but there is TW, extend the lowest known width to the base.
    if wbase <= 0 and anchors:
        lowest_width = sorted(anchors)[0][1]
        anchors.append((rlbas, lowest_width))
        meta["wbase"] = lowest_width

    # Top extrapolation should not be necessary because first panel normally carries TW;
    # if not, use the nearest anchor.
    for panel in panels:
        panel.width_top = _interp_piecewise(panel.z_top, anchors)
        panel.width_bottom = _interp_piecewise(panel.z_bottom, anchors)

    return total_height


# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------
def _corners(width: float, z: float, faces: int) -> List[Point3D]:
    width = max(float(width), 1e-6)
    if faces == 1:
        # Pole / one-face models: the principal axis is the tower centreline.
        # Custom @UDP geometry still uses its own explicit X/Y coordinates.
        return [(0.0, 0.0, z)]
    if faces == 3:
        # Equilateral triangle with side length = width.
        radius = width / math.sqrt(3.0)
        angles = [90.0, 210.0, 330.0]
        return [
            (radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a)), z)
            for a in angles
        ]
    # Default to square/4-leg tower.
    h = width / 2.0
    return [(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)]


def _lerp(a: Point3D, b: Point3D, t: float) -> Point3D:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _mean_point(points: Sequence[Point3D]) -> Point3D:
    n = max(len(points), 1)
    return (
        sum(p[0] for p in points) / n,
        sum(p[1] for p in points) / n,
        sum(p[2] for p in points) / n,
    )


def _point_on_face(
    bottom: Sequence[Point3D],
    top: Sequence[Point3D],
    face_idx: int,
    u: float,
    t: float,
) -> Point3D:
    n = len(bottom)
    i0 = face_idx % n
    i1 = (face_idx + 1) % n
    left = _lerp(bottom[i0], top[i0], t)
    right = _lerp(bottom[i1], top[i1], t)
    return _lerp(left, right, u)


def _section_info(section_id: Optional[int], catalog: Dict[int, SectionInfo]) -> SectionInfo:
    if section_id is None:
        return SectionInfo(0, "", None, "")
    return catalog.get(section_id, SectionInfo(section_id, "Unmapped", None, ""))


def _family_from_key(line_type: str, key: str) -> str:
    key = key.upper()
    if key == "LEG":
        return "LEG"
    if line_type == "FACE":
        if key.startswith("BR"):
            return "BR"
        if re.match(r"^H\d+$", key):
            return "HOR"
        if re.match(r"^R\d+$", key):
            return "RED"
    if line_type == "PLAN" and key.startswith("PB"):
        return "PBR"
    if line_type == "HIP" and key.startswith("HP"):
        return "HIP"
    if key.startswith("CR"):
        return "CROSS"
    return key


def _add_member(
    members: List[TowerMember],
    panel: PanelSpec,
    line: ProfileLine,
    key: str,
    start: Point3D,
    end: Point3D,
    catalog: Dict[int, SectionInfo],
    note: str = "",
) -> None:
    sid = line.assignments.get(key)
    if sid is None or sid <= 0:
        return
    info = _section_info(sid, catalog)
    members.append(
        TowerMember(
            panel_sequence=panel.sequence,
            panel_no=panel.panel_no,
            line_type=line.line_type,
            pattern=line.pattern,
            family=_family_from_key(line.line_type, key),
            member_key=key,
            section_id=sid,
            section_profile=info.profile,
            fy=info.fy,
            category=info.category,
            start=start,
            end=end,
            note=note,
        )
    )


def _build_udp_overlay_members(
    panel: PanelSpec,
    alias: str,
    udp: UDPDefinition,
    catalog: Dict[int, SectionInfo],
    members: List[TowerMember],
    reference_type: str = "GEOMETRY",
) -> int:
    """Append a referenced UDP as the ordinary selectable family ``UDP``.

    UDP NODE coordinates already define the custom component geometry.  They
    therefore must not be regenerated from FACE templates or re-scaled to a
    guessed standard panel.  Only the local Z origin is translated to the
    bottom elevation of the PROFILE panel that references the UDP.
    """
    if not udp.nodes or not udp.members:
        return 0

    z_values = [node.z for node in udp.nodes.values()]
    z_min = min(z_values)

    def transform(node: UDPNode) -> Point3D:
        return (
            float(node.x),
            float(node.y),
            float(panel.z_bottom + (node.z - z_min)),
        )

    node_map = {nid: transform(node) for nid, node in udp.nodes.items()}
    added = 0
    for um in udp.members:
        # A zero/negative UDP section is treated exactly like FACE/PLAN/HIP:
        # it represents no physical member and is not drawn.
        if um.section_id is not None and um.section_id <= 0:
            continue
        if um.node_i not in node_map or um.node_j not in node_map:
            continue

        info = _section_info(um.section_id, catalog)
        members.append(
            TowerMember(
                panel_sequence=panel.sequence,
                panel_no=panel.panel_no,
                line_type="UDP",
                pattern=udp.name,
                family="UDP",
                member_key=um.member_type or "UDP",
                section_id=um.section_id,
                section_profile=info.profile if info.profile != "Unmapped" else "",
                fy=info.fy,
                category="UDP custom component",
                start=node_map[um.node_i],
                end=node_map[um.node_j],
                note=f"{reference_type} @{alias} | MEMB {um.member_id} | {um.member_type}",
            )
        )
        added += 1
    return added


def _build_unreferenced_udp_preview_members(
    source_name: str,
    udp: UDPDefinition,
    base_z: float,
    catalog: Dict[int, SectionInfo],
    members: List[TowerMember],
) -> int:
    """Add an uploaded but unreferenced UDP as a selectable raw-coordinate preview.

    There is no PROFILE panel to provide placement, so X/Y are kept exactly as
    stored in the UDP and its local minimum Z is placed at the parent tower
    ``RLBAS``.  The members remain family ``UDP`` and can be hidden/shown from
    the same UI multiselect as LEG/PBR/HIP.
    """
    if not udp.nodes or not udp.members:
        return 0

    z_min = min(node.z for node in udp.nodes.values())
    node_map: Dict[int, Point3D] = {
        nid: (float(node.x), float(node.y), float(base_z + (node.z - z_min)))
        for nid, node in udp.nodes.items()
    }

    added = 0
    for um in udp.members:
        if um.section_id is not None and um.section_id <= 0:
            continue
        if um.node_i not in node_map or um.node_j not in node_map:
            continue
        info = _section_info(um.section_id, catalog)
        members.append(
            TowerMember(
                panel_sequence=0,
                panel_no=0,
                line_type="UDP",
                pattern=udp.name,
                family="UDP",
                member_key=um.member_type or "UDP",
                section_id=um.section_id,
                section_profile=info.profile if info.profile != "Unmapped" else "",
                fy=info.fy,
                category="UDP custom component (unreferenced preview)",
                start=node_map[um.node_i],
                end=node_map[um.node_j],
                note=f"Unreferenced UDP: {source_name} | {udp.name} | MEMB {um.member_id} | {um.member_type}",
            )
        )
        added += 1
    return added


# Normalized 2D FACE segment definitions: (key, u1, t1, u2, t2)
# u runs from the left leg (0) to the right leg (1); t runs from panel bottom
# (0) to panel top (1).  The explicit templates below follow the Standard
# Panels diagrams for the patterns used by the current tower model.
def _face_segments(
    pattern: str,
    assignments: Dict[str, int],
    options: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, float, float, float, float]]:
    """Return validated local FACE connectivity.

    Local coordinates use ``u`` from left leg (0) to right leg (1) and ``t``
    from panel bottom (0) to top (1).  The templates below follow the
    MStower/OpenTower *Standard Panels* diagrams.  A member is emitted only
    when its section assignment is strictly positive.

    Important: several MStower panels are intentionally not fully symmetric.
    In particular, K1/K2/K1M and XH3/XH3A use diagonal redundants on one side
    while horizontal redundant members repeat on both sides.  Previous versions
    mirrored every redundant member and therefore produced an incorrect face.
    """
    p = pattern.upper()
    options = options or {}
    segs: List[Tuple[str, float, float, float, float]] = []

    def enabled(key: str) -> bool:
        try:
            return int(assignments.get(key, 0) or 0) > 0
        except (TypeError, ValueError):
            return False

    def add(key: str, coords: Iterable[Tuple[float, float, float, float]]):
        if not enabled(key):
            return
        for u1, t1, u2, t2 in coords:
            segs.append((key, float(u1), float(t1), float(u2), float(t2)))

    def add_mirror(key: str, coords: Iterable[Tuple[float, float, float, float]]):
        coords = list(coords)
        add(key, coords)
        add(key, [(1-u1, t1, 1-u2, t2) for u1, t1, u2, t2 in coords])

    # ------------------------------------------------------------------
    # X family — Standard Panels p.9
    # ------------------------------------------------------------------
    if p in {"X", "XTN"}:
        add("BR1", [(0, 0, 1, 1), (1, 0, 0, 1)])
        add("H1", [(0, 1, 1, 1)])
        return segs

    if p == "XH1":
        # XH1 = X bracing + H1 through the intersection.
        add("BR1", [(0, 0, 1, 1), (1, 0, 0, 1)])
        add("H1", [(0, 0.5, 1, 0.5)])

        # R1+ and R2+ are conditional centre members.  The '+' note in the
        # Standard Panels drawing means they exist only when VU / VD is used.
        if options.get("VU"):
            add("R1", [(0.5, 0.5, 0.5, 1.0)])
        if options.get("VD"):
            add("R2", [(0.5, 0.0, 0.5, 0.5)])
        return segs

    if p in {"XH3", "XH3A"}:
        # Main X and H1 are common to XH3/XH3A.
        add("BR1", [(0, 0, 1, 1), (1, 0, 0, 1)])
        add("H1", [(0, 0.5, 1, 0.5)])

        # Diagram topology:
        #   - R1/R4 are horizontal redundant members and occur on both halves.
        #   - R2/R3 are the two diagonal redundants on the left half.
        # XH3 uses section R1 for all four redundant classes.
        upper = (0.25, 0.75)   # point on upper-left X branch
        lower = (0.25, 0.25)   # point on lower-left X branch
        if p == "XH3":
            add_mirror("R1", [(0.0, 0.75, upper[0], upper[1])])  # R1
            add("R1", [(0.0, 0.50, upper[0], upper[1])])         # R2
            add("R1", [(0.0, 0.50, lower[0], lower[1])])         # R3
            add_mirror("R1", [(0.0, 0.25, lower[0], lower[1])])  # R4
        else:
            add_mirror("R1", [(0.0, 0.75, upper[0], upper[1])])
            add("R2", [(0.0, 0.50, upper[0], upper[1])])
            add("R3", [(0.0, 0.50, lower[0], lower[1])])
            add_mirror("R4", [(0.0, 0.25, lower[0], lower[1])])

        # Centre vertical redundants are R6+ / R7+ in the standard XH3 drawing.
        if options.get("VU"):
            add("R6", [(0.5, 0.5, 0.5, 1.0)])
        if options.get("VD"):
            add("R7", [(0.5, 0.0, 0.5, 0.5)])
        return segs

    # ------------------------------------------------------------------
    # K family — Standard Panels pp.14–15
    # ------------------------------------------------------------------
    if p == "K":
        # Principal K braces form a V to the top-centre node.
        add("BR1", [(0, 0, 0.5, 1), (1, 0, 0.5, 1)])
        add("H1", [(0, 1, 1, 1)])
        # R1 is the centre vertical shown only when it has a positive section.
        add("R1", [(0.5, 0, 0.5, 1)])
        return segs

    if p == "K1":
        # Literal K1 topology (p.14): one redundant triangular cell at the
        # left side; BR2 continues from the BR1 intersection to the right leg.
        add("BR1", [(0, 0, 0.5, 1), (1, 0, 0.5, 1)])
        add("H1", [(0, 1, 1, 1)])

        c_u, c_t = 0.25, 0.50  # node on left BR1
        add("R1", [(0.0, 1.0, c_u, c_t)])
        add("R2", [(0.0, c_t, c_u, c_t)])
        add("BR2", [(c_u, c_t, 1.0, c_t)])
        return segs

    if p in {"K2", "K2A"}:
        # Two redundant cells.  The diagonal redundants (R1/R3) are on the
        # left half; the horizontal redundants (R2/R4) repeat on both halves,
        # matching the Standard Panels K2/K2A drawing.
        add("BR1", [(0, 0, 0.5, 1), (1, 0, 0.5, 1)])
        add("H1", [(0, 1, 1, 1)])

        c1 = (0.34, 0.68)
        c2 = (0.17, 0.34)

        if p == "K2":
            # K2: all redundant members use the R1 section.
            add("R1", [(0.0, 1.00, *c1)])
            add_mirror("R1", [(0.0, c1[1], *c1)])
            add("R1", [(0.0, c1[1], *c2)])
            add_mirror("R1", [(0.0, c2[1], *c2)])
        else:
            add("R1", [(0.0, 1.00, *c1)])
            add_mirror("R2", [(0.0, c1[1], *c1)])
            add("R3", [(0.0, c1[1], *c2)])
            add_mirror("R4", [(0.0, c2[1], *c2)])
        return segs

    if p == "K1M":
        # Three redundant cells.  Odd R members are the left-hand diagonals;
        # even R members are horizontal members repeated on both halves.
        add("BR1", [(0, 0, 0.5, 1), (1, 0, 0.5, 1)])
        add("H1", [(0, 1, 1, 1)])

        c1 = (0.375, 0.75)
        c2 = (0.250, 0.50)
        c3 = (0.125, 0.25)

        add("R1", [(0.0, 1.00, *c1)])
        add_mirror("R2", [(0.0, c1[1], *c1)])
        add("R3", [(0.0, c1[1], *c2)])
        add_mirror("R4", [(0.0, c2[1], *c2)])
        add("R5", [(0.0, c2[1], *c3)])
        add_mirror("R6", [(0.0, c3[1], *c3)])
        return segs

    # Intentionally no generic fallback. A wrong standard-panel topology can be
    # mistaken for the design model, so unsupported patterns are skipped.
    return segs

def _build_face_members(
    panel: PanelSpec,
    line: ProfileLine,
    bottom: Sequence[Point3D],
    top: Sequence[Point3D],
    catalog: Dict[int, SectionInfo],
    members: List[TowerMember],
) -> None:
    nfaces = len(bottom)

    # LEG is a real member only for a positive section ID.
    if line.assignments.get("LEG", 0) > 0:
        for i in range(nfaces):
            _add_member(members, panel, line, "LEG", bottom[i], top[i], catalog, note=f"Leg {i+1}")

    face_segments = _face_segments(line.pattern, line.assignments, line.options)

    # Do not invent missing H1/H2 geometry. Horizontal members are highly
    # pattern-specific in MStower. A positive assignment that is not represented
    # by the validated FACE template is reported by geometry validation instead
    # of being drawn at an assumed elevation. Section <= 0 is never emitted.

    for face_idx in range(nfaces):
        for key, u1, t1, u2, t2 in face_segments:
            p1 = _point_on_face(bottom, top, face_idx, u1, t1)
            p2 = _point_on_face(bottom, top, face_idx, u2, t2)
            _add_member(
                members, panel, line, key, p1, p2, catalog,
                note=f"Face {face_idx+1}",
            )


def _plan_level(line: ProfileLine, panel: PanelSpec) -> float:
    q = line.qualifier.upper()
    if "BTM" in q:
        return panel.z_bottom
    if "MID" in q or "XIP" in q:
        return (panel.z_bottom + panel.z_top) / 2.0
    return panel.z_top


def _width_at_panel_z(panel: PanelSpec, z: float) -> float:
    if abs(panel.z_top - panel.z_bottom) < 1e-12:
        return panel.width_top
    t = (z - panel.z_bottom) / (panel.z_top - panel.z_bottom)
    return panel.width_bottom + t * (panel.width_top - panel.width_bottom)


def _build_plan_members(
    panel: PanelSpec,
    line: ProfileLine,
    faces: int,
    catalog: Dict[int, SectionInfo],
    members: List[TowerMember],
) -> None:
    """Build validated PLAN patterns from the Standard Panels diagrams."""
    if faces != 4:
        return

    z = _plan_level(line, panel)
    points = _corners(_width_at_panel_z(panel, z), z, faces)
    center = _mean_point(points)
    p0, p1, p2, p3 = points
    m0 = _lerp(p0, p1, 0.5)  # bottom side midpoint
    m1 = _lerp(p1, p2, 0.5)  # right side midpoint
    m2 = _lerp(p2, p3, 0.5)  # top side midpoint
    m3 = _lerp(p3, p0, 0.5)  # left side midpoint
    p = line.pattern.upper()

    def add_segment(key: str, a: Point3D, b: Point3D, note: str = ""):
        if line.assignments.get(key, 0) > 0:
            _add_member(members, panel, line, key, a, b, catalog, note=note or line.qualifier)

    if p == "PL2A":
        # Standard Panels p.35: PB1 lower corner spokes, PB2 upper corner
        # spokes, PB3 horizontal mid-side spokes, PB4 vertical mid-side spokes.
        for pt in (p0, p1):
            add_segment("PB1", pt, center)
        for pt in (p3, p2):
            add_segment("PB2", pt, center)
        for pt in (m3, m1):
            add_segment("PB3", pt, center)
        for pt in (m2, m0):
            add_segment("PB4", pt, center)
        return

    if p == "PL3S":
        # Standard Panels p.35: four corner members surround an inner square;
        # PB5 is the inner-square member class.
        inner_scale = 0.52
        q0 = _lerp(center, p0, inner_scale)
        q1 = _lerp(center, p1, inner_scale)
        q2 = _lerp(center, p2, inner_scale)
        q3 = _lerp(center, p3, inner_scale)
        for key, outer, inner in (
            ("PB1", p0, q0),
            ("PB2", p1, q1),
            ("PB3", p2, q2),
            ("PB4", p3, q3),
        ):
            add_segment(key, outer, inner)
        if line.assignments.get("PB5", 0) > 0:
            for a, b in ((q0,q1),(q1,q2),(q2,q3),(q3,q0)):
                add_segment("PB5", a, b)
        return

    # Unsupported PLAN patterns are intentionally skipped by the caller warning.


def _hip_triangle_for_leg(
    top: Sequence[Point3D],
    bottom: Sequence[Point3D],
    leg_idx: int,
) -> Tuple[Point3D, Point3D, Point3D]:
    """Return (top-left, top-right, apex) of one internal hip plane.

    The hip plane is formed around a tower leg using the midpoints of the two
    adjacent top edges and the corresponding lower leg as its apex. This gives
    the triangular topology shown by HKA while remaining symmetric in 3D.
    """
    n = len(top)
    corner = top[leg_idx]
    prev_corner = top[(leg_idx - 1) % n]
    next_corner = top[(leg_idx + 1) % n]
    left = _lerp(corner, prev_corner, 0.5)
    right = _lerp(corner, next_corner, 0.5)
    apex = bottom[leg_idx]
    return left, right, apex


def _build_hip_members(
    panel: PanelSpec,
    line: ProfileLine,
    faces: int,
    catalog: Dict[int, SectionInfo],
    members: List[TowerMember],
) -> None:
    """Build HKA triangular levels using the HP assignments exactly as switches.

    For HKA, NTR=n uses odd HP keys as the horizontal chords and even HP keys
    as the diagonals between successive chords: for NTR=1 -> HP1/HP2/HP3;
    for NTR=2 -> HP1/HP2/HP3/HP4/HP5.  Any HP with section 0 is omitted.
    """
    if line.pattern.upper() != "HKA" or faces not in {3,4}:
        return

    bottom = _corners(panel.width_bottom, panel.z_bottom, faces)
    top = _corners(panel.width_top, panel.z_top, faces)

    ntr_raw = line.options.get("NTR")
    try:
        ntr = max(0, int(round(float(ntr_raw)))) if ntr_raw is not None else 0
    except (TypeError, ValueError):
        ntr = 0
    if ntr <= 0:
        hp_indices = [int(k[2:]) for k in line.assignments if re.match(r"^HP\d+$", k)]
        max_hp = max(hp_indices, default=0)
        ntr = max(1, (max_hp - 1) // 2) if max_hp else 0
    if ntr <= 0:
        return

    for leg_idx in range(faces):
        top_left, top_right, apex = _hip_triangle_for_leg(top, bottom, leg_idx)

        # Chord levels: NTR=1 -> y=1, 1/2 ; NTR=2 -> 1, 2/3, 1/3.
        chord_levels = [1.0 - j / (ntr + 1.0) for j in range(ntr + 1)]
        chord_points: List[Tuple[Point3D, Point3D]] = []
        for level in chord_levels:
            left = _lerp(apex, top_left, level)
            right = _lerp(apex, top_right, level)
            chord_points.append((left, right))

        # HP1, HP3, HP5... are the horizontal/chord members.
        for j, (left, right) in enumerate(chord_points):
            key = f"HP{2*j + 1}"
            _add_member(
                members, panel, line, key, left, right, catalog,
                note=f"HKA hip {leg_idx+1} chord {j+1}",
            )

        # HP2, HP4... are diagonal members between adjacent triangular levels.
        for j in range(ntr):
            upper_left, upper_right = chord_points[j]
            lower_left, lower_right = chord_points[j+1]
            key = f"HP{2*j + 2}"
            if j % 2 == 0:
                a, b = upper_left, lower_right
            else:
                a, b = upper_right, lower_left
            _add_member(
                members, panel, line, key, a, b, catalog,
                note=f"HKA hip {leg_idx+1} diagonal {j+1}",
            )

        # The final sides converge toward the lower apex as shown by the dashed
        # triangular boundary in the standard diagram. They are boundaries, not
        # additional HP members, so no line is created unless explicitly defined.

# -----------------------------------------------------------------------------
# Public model builder
# -----------------------------------------------------------------------------
def build_tower_geometry(
    content: str,
    section_catalog: Optional[pd.DataFrame] = None,
    udp_sources: Optional[Dict[str, str]] = None,
) -> TowerGeometry:
    meta, panels = parse_profile(content)
    catalog = _catalog_from_dataframe(section_catalog)
    if not catalog:
        catalog = _parse_section_catalog(content)

    total_height = _resolve_panel_geometry(meta, panels)
    faces = int(meta.get("faces") or 4)
    if faces not in {1, 3, 4}:
        faces = 4

    members: List[TowerMember] = []
    warnings: List[str] = []
    face_patterns: List[str] = []
    plan_patterns: List[str] = []
    hip_patterns: List[str] = []

    # UDP definitions are additional components referenced by PROFILE/COMPONENTS.
    # Their generated members use family="UDP", so the UI can filter them in
    # exactly the same way as LEG/BR/PBR/HIP/etc.
    udp_component_refs = _parse_udp_component_refs(content)
    udp_lookup = _normalize_udp_sources(udp_sources)
    used_udp_contents: set[str] = set()

    if not panels:
        warnings.append("PROFILE/PANEL geometry was not detected.")

    for panel in panels:
        bottom = _corners(panel.width_bottom, panel.z_bottom, faces)
        top = _corners(panel.width_top, panel.z_top, faces)

        # -------------------------------------------------------------
        # UDP references: @ is authoritative for ANY geometry directive.
        # Examples: FACE @POLE6, PLAN @CUSTOMPLAN, HIP @CUSTOMHIP, or
        # another PROFILE geometry keyword containing @NAME.
        # -------------------------------------------------------------
        for line in panel.udp_lines:
            alias = line.pattern.lstrip("@").strip().upper()
            udp_filename = udp_component_refs.get(alias)
            udp_content = _resolve_udp_source(alias, udp_filename, udp_lookup)

            if udp_content is None:
                expected = udp_filename or alias
                warnings.append(
                    f"UDP reference {line.line_type} {line.pattern} (lookup {expected}) "
                    f"was used on panel {panel.panel_no}, but no uploaded UDP with that "
                    "component filename/internal name was found."
                )
                continue

            udp_def = parse_udp_definition(udp_content)
            used_udp_contents.add(udp_content)
            added = _build_udp_overlay_members(
                panel, alias, udp_def, catalog, members,
                reference_type=line.line_type,
            )
            if added == 0:
                warnings.append(
                    f"UDP reference {line.line_type} {line.pattern} was resolved to "
                    f"{udp_def.name}, but it contained no drawable NODE/MEMB members."
                )

        # Standard FACE statements. A plain mnemonic is NEVER converted to UDP
        # merely because a similarly named COMPONENT exists; only @ triggers UDP.
        for line in panel.face_lines:
            if line.pattern not in face_patterns:
                face_patterns.append(line.pattern)
            if line.pattern not in SUPPORTED_FACE_PATTERNS:
                warnings.append(
                    f"FACE {line.pattern} belum memiliki template Standard Panels tervalidasi "
                    f"(panel {panel.panel_no}); pattern ini tidak digambar."
                )
                continue
            _build_face_members(panel, line, bottom, top, catalog, members)

        # Standard PLAN statements.
        for line in panel.plan_lines:
            if line.pattern not in plan_patterns:
                plan_patterns.append(line.pattern)
            if line.pattern not in SUPPORTED_PLAN_PATTERNS:
                warnings.append(
                    f"PLAN {line.pattern} belum memiliki template Standard Panels tervalidasi "
                    f"(panel {panel.panel_no}); pattern ini tidak digambar."
                )
                continue
            _build_plan_members(panel, line, faces, catalog, members)

        # Standard HIP statements.
        for line in panel.hip_lines:
            if line.pattern not in hip_patterns:
                hip_patterns.append(line.pattern)
            if line.pattern not in SUPPORTED_HIP_PATTERNS:
                warnings.append(
                    f"HIP {line.pattern} belum memiliki template Standard Panels tervalidasi "
                    f"(panel {panel.panel_no}); pattern ini tidak digambar."
                )
                continue
            _build_hip_members(panel, line, faces, catalog, members)

    # Uploaded UDP files are still useful even when they are not called by
    # PROFILE.  Expose them as the ordinary UDP family using their own NODE/MEMB
    # coordinates.  Because no panel placement exists, preview them with local
    # Z translated to the parent RLBAS.
    for source_name, udp_content in (udp_sources or {}).items():
        text = str(udp_content)
        if text in used_udp_contents:
            continue
        udp_def = parse_udp_definition(text)
        added = _build_unreferenced_udp_preview_members(
            source_name=str(source_name),
            udp=udp_def,
            base_z=float(meta.get("rlbas") or 0.0),
            catalog=catalog,
            members=members,
        )
        if added > 0:
            warnings.append(
                f"UDP {udp_def.name or source_name} tersedia tetapi tidak direferensikan oleh PROFILE; "
                "ditampilkan sebagai UDP preview pada RLBAS dan dapat diaktifkan/nonaktifkan dari filter member."
            )
        else:
            warnings.append(
                f"UDP {udp_def.name or source_name} tersedia tetapi tidak memiliki NODE/MEMB yang dapat digambar."
            )

    # Deduplicate warnings while preserving order.
    warnings = list(dict.fromkeys(warnings))
    if members:
        warnings.append(
            "Visualisasi PROFILE menggunakan template Standard Panels yang telah dipetakan pada module; "
            "pattern yang belum dipetakan sengaja tidak digambar. Setiap geometry @NAME memanggil UDP; "
            "UDP menggunakan koordinat NODE/MEMB langsung."
        )

    return TowerGeometry(
        title_1=str(meta.get("title_1") or ""),
        title_2=str(meta.get("title_2") or ""),
        faces=faces,
        wbase=float(meta.get("wbase") or 0.0),
        rlbas=float(meta.get("rlbas") or 0.0),
        total_height=total_height,
        panels=panels,
        members=members,
        warnings=warnings,
        used_face_patterns=face_patterns,
        used_plan_patterns=plan_patterns,
        used_hip_patterns=hip_patterns,
    )


# -----------------------------------------------------------------------------
# DataFrame exports/debugging
# -----------------------------------------------------------------------------
def geometry_panels_dataframe(model: TowerGeometry) -> pd.DataFrame:
    rows = []
    for p in model.panels:
        rows.append({
            "Sequence": p.sequence,
            "Panel": p.panel_no,
            "Z Bottom (m)": p.z_bottom,
            "Z Top (m)": p.z_top,
            "HT (m)": p.height,
            "Width Bottom (m)": p.width_bottom,
            "Width Top (m)": p.width_top,
            "TW Explicit (m)": p.tw_explicit,
            "FACE": " | ".join(x.pattern for x in p.face_lines),
            "PLAN": " | ".join(f"{x.pattern} {x.qualifier}".strip() for x in p.plan_lines),
            "HIP": " | ".join(x.pattern for x in p.hip_lines),
            "UDP Reference": " | ".join(f"{x.line_type} {x.pattern}" for x in p.udp_lines),
        })
    return pd.DataFrame(rows)


def geometry_members_dataframe(model: TowerGeometry) -> pd.DataFrame:
    rows = []
    for m in model.members:
        rows.append({
            "Panel Sequence": m.panel_sequence,
            "Panel": m.panel_no,
            "Source": m.line_type,
            "Pattern": m.pattern,
            "Family": m.family,
            "Member": m.member_key,
            "Section ID": m.section_id,
            "Section / Profile": m.section_profile,
            "fy": m.fy,
            "Category": m.category,
            "X1": m.start[0], "Y1": m.start[1], "Z1": m.start[2],
            "X2": m.end[0], "Y2": m.end[1], "Z2": m.end[2],
            "Note": m.note,
        })
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Material schedule / legend
# -----------------------------------------------------------------------------
def _material_label(profile: str, section_id: Optional[int]) -> str:
    """Return a compact drawing-style material label.

    Examples:
      EA70X70X7 -> L.70,70,7
      EA40X40X4 -> L.40,40,4
    Profiles that are not equal angles (CHS/DAE/STA/etc.) are kept verbatim.
    """
    text = str(profile or "").strip()
    m = re.match(r"^EA\s*([0-9.]+)X([0-9.]+)X([0-9.]+)$", text, re.I)
    if m:
        vals = [x.rstrip("0").rstrip(".") if "." in x else x for x in m.groups()]
        return f"L.{vals[0]},{vals[1]},{vals[2]}"
    if text and text.upper() != "UNMAPPED":
        return text
    if section_id is not None:
        return f"SEC {int(section_id)}"
    return "—"


def material_schedule_dataframe(model: TowerGeometry) -> pd.DataFrame:
    """Build a material table per PROFILE section/panel.

    The table mirrors the engineering legend convention used in tower drawings:
    MAIN LEG, BRACING, HORIZONTAL, REDUNDANT, PLAN BRACING, HIP STAY and UDP.
    A material is shown once per family per panel even when many physical
    segments share that section.
    """
    family_columns = [
        ("LEG", "MAIN LEG"),
        ("BR", "BRACING"),
        ("HOR", "HORIZONTAL"),
        ("RED", "REDUNDANT"),
        ("PBR", "PLAN BRACING"),
        ("HIP", "HIP STAY"),
        ("CROSS", "CROSS ARM"),
        ("UDP", "UDP"),
    ]
    rows: List[Dict[str, Any]] = []

    for panel in sorted(model.panels, key=lambda p: p.sequence):
        row: Dict[str, Any] = {
            "Section": f"Panel {panel.panel_no}",
            "Elevation (m)": f"{panel.z_bottom:g} – {panel.z_top:g}",
        }
        panel_members = [m for m in model.members if m.panel_no == panel.panel_no]
        for family, column in family_columns:
            labels: List[str] = []
            for m in panel_members:
                if str(m.family).upper() != family:
                    continue
                label = _material_label(m.section_profile, m.section_id)
                if label not in labels:
                    labels.append(label)
            row[column] = " | ".join(labels) if labels else "—"
        rows.append(row)

    # Unreferenced UDP previews have panel_no=0. Keep them visible but separate
    # from the actual PROFILE sections so they are not mistaken for installed
    # panel material.
    preview_members = [m for m in model.members if m.panel_no == 0 and m.family == "UDP"]
    if preview_members:
        labels: List[str] = []
        for m in preview_members:
            label = _material_label(m.section_profile, m.section_id)
            if label not in labels:
                labels.append(label)
        row = {"Section": "UDP preview", "Elevation (m)": f"RLBAS {model.rlbas:g}"}
        for _, column in family_columns:
            row[column] = "—"
        row["UDP"] = " | ".join(labels) if labels else "—"
        rows.append(row)

    columns = ["Section", "Elevation (m)"] + [c for _, c in family_columns]
    return pd.DataFrame(rows, columns=columns)



# -----------------------------------------------------------------------------
# Geometry completeness / drawing validation
# -----------------------------------------------------------------------------
def geometry_validation_dataframe(model: TowerGeometry) -> pd.DataFrame:
    """Validate PROFILE assignments against generated visual geometry.

    Validation is intentionally key-based, not segment-count based. A positive
    PROFILE assignment (e.g. H1 40) must appear at least once in the generated
    geometry for that panel/pattern. A zero/negative assignment must never
    appear. This catches incomplete FACE templates without inventing geometry.
    """
    rows: List[Dict[str, Any]] = []

    def validate_line(panel: PanelSpec, line: ProfileLine) -> None:
        positive = sorted(
            [str(k).upper() for k, v in line.assignments.items() if _int_num(v) is not None and int(v) > 0]
        )
        zero_keys = sorted(
            [str(k).upper() for k, v in line.assignments.items() if _int_num(v) is not None and int(v) <= 0]
        )
        plotted = {
            str(m.member_key).upper()
            for m in model.members
            if m.panel_no == panel.panel_no
            and str(m.line_type).upper() == str(line.line_type).upper()
            and str(m.pattern).upper() == str(line.pattern).upper()
        }
        missing = [k for k in positive if k not in plotted]
        zero_violation = [k for k in zero_keys if k in plotted]
        expected_n = len(positive)
        plotted_expected = expected_n - len(missing)
        completeness = 100.0 if expected_n == 0 else 100.0 * plotted_expected / expected_n

        registry = {
            "FACE": SUPPORTED_FACE_PATTERNS,
            "PLAN": SUPPORTED_PLAN_PATTERNS,
            "HIP": SUPPORTED_HIP_PATTERNS,
        }.get(str(line.line_type).upper(), set())
        supported = str(line.pattern).upper() in registry
        if not supported:
            status = "UNSUPPORTED"
        elif zero_violation:
            status = "ZERO VIOLATION"
        elif missing:
            status = "INCOMPLETE"
        else:
            status = "PASS"

        rows.append({
            "Panel": panel.panel_no,
            "Elevation": f"{panel.z_bottom:g} – {panel.z_top:g} m",
            "Source": str(line.line_type).upper(),
            "Pattern": str(line.pattern).upper(),
            "Positive Assignments": ", ".join(positive) if positive else "—",
            "Plotted Keys": ", ".join(sorted(plotted)) if plotted else "—",
            "Missing Positive": ", ".join(missing) if missing else "—",
            "Zero / Absent": ", ".join(zero_keys) if zero_keys else "—",
            "Zero Violations": ", ".join(zero_violation) if zero_violation else "—",
            "Completeness (%)": completeness,
            "Status": status,
        })

    for panel in model.panels:
        for line in panel.face_lines:
            validate_line(panel, line)
        for line in panel.plan_lines:
            validate_line(panel, line)
        for line in panel.hip_lines:
            validate_line(panel, line)

        for line in panel.udp_lines:
            alias = str(line.pattern).lstrip("@").strip().upper()
            matched = [
                m for m in model.members
                if m.panel_no == panel.panel_no
                and str(m.family).upper() == "UDP"
                and f"@{alias}" in str(m.note).upper()
            ]
            rows.append({
                "Panel": panel.panel_no,
                "Elevation": f"{panel.z_bottom:g} – {panel.z_top:g} m",
                "Source": str(line.line_type).upper(),
                "Pattern": f"@{alias}",
                "Positive Assignments": "UDP NODE/MEMB",
                "Plotted Keys": f"{len(matched):,} segment(s)" if matched else "—",
                "Missing Positive": "—" if matched else "UDP geometry",
                "Zero / Absent": "section <= 0 skipped",
                "Zero Violations": "—",
                "Completeness (%)": 100.0 if matched else 0.0,
                "Status": "PASS" if matched else "INCOMPLETE",
            })

    return pd.DataFrame(rows)


def geometry_validation_summary(model: TowerGeometry) -> Dict[str, Any]:
    df = geometry_validation_dataframe(model)
    if df.empty:
        return {
            "status": "NO DATA", "completeness": 0.0, "statements": 0,
            "pass": 0, "incomplete": 0, "unsupported": 0,
            "zero_violations": 0, "udp_calls": 0, "udp_resolved": 0,
        }
    statuses = df["Status"].astype(str)
    non_udp = df[~df["Pattern"].astype(str).str.startswith("@")]
    completeness = float(non_udp["Completeness (%)"].mean()) if not non_udp.empty else 100.0
    zero_violations = int((df["Zero Violations"].astype(str) != "—").sum())
    udp_df = df[df["Pattern"].astype(str).str.startswith("@")]
    incomplete = int(statuses.isin(["INCOMPLETE", "ZERO VIOLATION"]).sum())
    unsupported = int((statuses == "UNSUPPORTED").sum())
    if zero_violations or incomplete:
        overall = "REVIEW"
    elif unsupported:
        overall = "PARTIAL"
    else:
        overall = "PASS"
    return {
        "status": overall,
        "completeness": completeness,
        "statements": len(df),
        "pass": int((statuses == "PASS").sum()),
        "incomplete": incomplete,
        "unsupported": unsupported,
        "zero_violations": zero_violations,
        "udp_calls": len(udp_df),
        "udp_resolved": int((udp_df["Status"] == "PASS").sum()) if not udp_df.empty else 0,
    }


def _material_spans(model: TowerGeometry) -> List[Dict[str, Any]]:
    """Merge contiguous panels that use the same material within each family."""
    categories = [
        ("LEG", "MAIN LEG"),
        ("BR", "BRACING"),
        ("HOR", "HORIZONTAL"),
        ("RED", "REDUNDANT"),
        ("PBR", "PLAN BRACING"),
        ("HIP", "HIP STAY"),
        ("CROSS", "CROSS ARM"),
        ("UDP", "UDP"),
    ]
    panels = sorted(model.panels, key=lambda p: p.z_bottom)
    spans: List[Dict[str, Any]] = []

    for family, label in categories:
        raw: List[Tuple[float, float, str, int]] = []
        for panel in panels:
            labels: List[str] = []
            for m in model.members:
                if m.panel_no != panel.panel_no or str(m.family).upper() != family:
                    continue
                material = _material_label(m.section_profile, m.section_id)
                if material != "—" and material not in labels:
                    labels.append(material)
            if labels:
                raw.append((panel.z_bottom, panel.z_top, " | ".join(labels), panel.panel_no))

        current: Optional[Dict[str, Any]] = None
        for z0, z1, material, panel_no in raw:
            if (
                current is not None
                and current["material"] == material
                and abs(float(current["z_top"]) - float(z0)) <= 1e-6
            ):
                current["z_top"] = z1
                current["panels"].append(panel_no)
            else:
                if current is not None:
                    spans.append(current)
                current = {
                    "family": family,
                    "label": label,
                    "material": material,
                    "z_bottom": z0,
                    "z_top": z1,
                    "panels": [panel_no],
                }
        if current is not None:
            spans.append(current)
    return spans


def _select_2d_members(
    model: TowerGeometry,
    view: str,
    members: Sequence[TowerMember],
) -> Tuple[List[TowerMember], Optional[Tuple[float, float]], Optional[int]]:
    """Select one physical FACE for drawing while always retaining UDP geometry."""
    view_upper = str(view).upper().strip()
    selected_face: Optional[int] = None
    face_dir: Optional[Tuple[float, float]] = None
    face_match = re.match(r"^FACE\s+(\d+)$", view_upper)
    if face_match and model.faces >= 3:
        selected_face = int(face_match.group(1))
        if selected_face < 1 or selected_face > model.faces:
            selected_face = 1
        unit = _corners(1.0, 0.0, model.faces)
        i0 = (selected_face - 1) % len(unit)
        i1 = selected_face % len(unit)
        dx = unit[i1][0] - unit[i0][0]
        dy = unit[i1][1] - unit[i0][1]
        norm = math.hypot(dx, dy) or 1.0
        face_dir = (dx / norm, dy / norm)
        leg_a, leg_b = i0 + 1, i1 + 1
        selected: List[TowerMember] = []
        for m in members:
            if str(m.family).upper() == "UDP" or str(m.line_type).upper() == "UDP":
                selected.append(m)
            elif str(m.line_type).upper() == "FACE" and m.note == f"Face {selected_face}":
                selected.append(m)
            elif str(m.family).upper() == "LEG" and str(m.line_type).upper() == "FACE" and m.note in {
                f"Leg {leg_a}", f"Leg {leg_b}"
            }:
                selected.append(m)
        return selected, face_dir, selected_face
    return list(members), face_dir, selected_face


def make_engineering_2d_figure(
    model: TowerGeometry,
    view: str = "Face 1",
    height_px: Optional[int] = None,
) -> go.Figure:
    """Create one static engineering drawing with tower and aligned material tracks.

    Tower and schedule share a single elevation axis, removing the alignment and
    overlap problems caused by two independent responsive Plotly figures. The
    tower horizontal dimension is visually enlarged by a constant display factor
    for readability; Z/elevation remains exact.
    """
    panels = sorted(model.panels, key=lambda p: p.z_bottom)
    z_min = min([p.z_bottom for p in panels], default=model.rlbas)
    z_max = max([p.z_top for p in panels], default=model.rlbas + max(model.total_height, 1.0))
    z_span = max(z_max - z_min, 1.0)
    if height_px is None:
        height_px = int(max(900, min(1350, 190 + len(panels) * 47)))

    members, face_dir, selected_face = _select_2d_members(model, view, model.members)
    view_upper = str(view).upper().strip()

    def project(p: Point3D) -> Tuple[float, float]:
        if selected_face is not None and face_dir is not None:
            return p[0] * face_dir[0] + p[1] * face_dir[1], p[2]
        if "SIDE Y" in view_upper or view_upper in {"Y", "FRONT Y"}:
            return p[1], p[2]
        return p[0], p[2]

    raw_x: List[float] = []
    for m in members:
        raw_x.extend([project(m.start)[0], project(m.end)[0]])
    physical_width = (max(raw_x) - min(raw_x)) if raw_x else max(model.wbase, 0.2)
    if model.faces == 1:
        horiz_factor = max(4.0, min(10.0, z_span / max(physical_width, 0.1) / 8.0))
    else:
        horiz_factor = 2.15

    fig = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        column_widths=[0.37, 0.63],
        horizontal_spacing=0.035,
        specs=[[{"type": "xy"}, {"type": "xy"}]],
    )

    ordered_families = FAMILY_ORDER + sorted(set(m.family for m in members) - set(FAMILY_ORDER))
    tower_x: List[float] = []
    for family in ordered_families:
        fam_members = [m for m in members if m.family == family]
        if not fam_members:
            continue
        xs: List[Optional[float]] = []
        ys: List[Optional[float]] = []
        for m in fam_members:
            x1, y1 = project(m.start)
            x2, y2 = project(m.end)
            x1 *= horiz_factor
            x2 *= horiz_factor
            tower_x.extend([x1, x2])
            xs += [x1, x2, None]
            ys += [y1, y2, None]
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines", name=family, hoverinfo="skip",
                line={"width": 2.6 if family == "LEG" else 1.45},
                showlegend=False,
            ),
            row=1, col=1,
        )

    if tower_x:
        xmin, xmax = min(tower_x), max(tower_x)
    else:
        display_w = max(model.wbase, 0.5) * horiz_factor
        xmin, xmax = -display_w / 2, display_w / 2
    xmid = (xmin + xmax) / 2.0
    xspan = max(xmax - xmin, 0.5)
    xpad = max(xspan * 0.16, 0.2)

    # Panel boundaries use the exact same Y coordinates in both drawing areas.
    for panel in panels:
        for xref, xa, xb in [("x", xmin - xpad * 0.2, xmax + xpad * 0.2), ("x2", 0, 8)]:
            fig.add_shape(
                type="line", x0=xa, x1=xb, y0=panel.z_bottom, y1=panel.z_bottom,
                xref=xref, yref="y", line={"width": 0.45, "dash": "dot"}, layer="below",
            )
    if panels:
        fig.add_shape(type="line", x0=0, x1=8, y0=panels[-1].z_top, y1=panels[-1].z_top,
                      xref="x2", yref="y", line={"width": 0.6}, layer="below")

    categories = [
        ("LEG", "MAIN LEG"), ("BR", "BRACING"), ("HOR", "HORIZONTAL"),
        ("RED", "REDUNDANT"), ("PBR", "PLAN BRACING"), ("HIP", "HIP STAY"),
        ("CROSS", "CROSS ARM"), ("UDP", "UDP"),
    ]
    cat_index = {family: i for i, (family, _) in enumerate(categories)}
    for x in range(len(categories) + 1):
        fig.add_shape(type="line", x0=x, x1=x, y0=z_min, y1=z_max,
                      xref="x2", yref="y", line={"width": 0.8}, layer="below")

    # Merge identical contiguous material before adding text. This is the key
    # readability fix: one material span = one annotation, not one per panel.
    pixels_per_m = max((height_px - 150) / z_span, 1.0)
    for span in _material_spans(model):
        family = span["family"]
        if family not in cat_index:
            continue
        i = cat_index[family]
        z0, z1 = float(span["z_bottom"]), float(span["z_top"])
        material = str(span["material"])
        span_px = max((z1 - z0) * pixels_per_m, 1.0)
        fig.add_shape(
            type="rect", x0=i, x1=i + 1, y0=z0, y1=z1,
            xref="x2", yref="y", line={"width": 0.75},
            fillcolor="rgba(0,0,0,0)", layer="below",
        )
        # Avoid forced text collisions in very short spans. The detail table
        # below the drawing retains every value; spans >= ~24 px get labels.
        if span_px >= 24:
            font_size = 8 if span_px < 46 else 9 if span_px < 80 else 10
            fig.add_annotation(
                x=i + 0.5, y=(z0 + z1) / 2.0, xref="x2", yref="y",
                text=material, textangle=-90, showarrow=False,
                font={"size": font_size}, xanchor="center", yanchor="middle",
            )

    for i, (_, label) in enumerate(categories):
        fig.add_annotation(
            x=i + 0.5, y=z_min, xref="x2", yref="y",
            yshift=-30, text=label, textangle=-90, showarrow=False,
            font={"size": 9}, xanchor="center", yanchor="top",
        )

    side_label = f"Face {selected_face}" if selected_face is not None else ("Side Y" if "Y" in view_upper else "Side X")
    fig.add_annotation(
        x=0.0, y=1.035, xref="paper", yref="paper",
        text=f"2D Engineering Drawing — {side_label}", showarrow=False,
        xanchor="left", font={"size": 15},
    )
    fig.add_annotation(
        x=0.405, y=1.035, xref="paper", yref="paper",
        text="Material Schedule by Elevation", showarrow=False,
        xanchor="left", font={"size": 15},
    )

    fig.update_xaxes(
        row=1, col=1, range=[xmid - xspan / 2 - xpad, xmid + xspan / 2 + xpad],
        fixedrange=True, showgrid=False, showticklabels=False, zeroline=False,
    )
    fig.update_xaxes(
        row=1, col=2, range=[0, len(categories)], fixedrange=True,
        showgrid=False, showticklabels=False, zeroline=False,
    )
    fig.update_yaxes(
        row=1, col=1, range=[z_min, z_max], fixedrange=True,
        showgrid=False, zeroline=False, ticksuffix=" m", dtick=5,
    )
    fig.update_yaxes(row=1, col=2, range=[z_min, z_max], fixedrange=True, showticklabels=False)
    fig.update_layout(
        height=height_px,
        margin={"l": 55, "r": 15, "t": 64, "b": 118},
        showlegend=False, hovermode=False, dragmode=False,
    )
    return fig

# -----------------------------------------------------------------------------
# Plotly rendering
# -----------------------------------------------------------------------------
def _filtered_members(
    model: TowerGeometry,
    families: Optional[Sequence[str]] = None,
    panel_numbers: Optional[Sequence[int]] = None,
) -> List[TowerMember]:
    fam_set = {str(x).upper() for x in families} if families is not None else None
    panel_set = {int(x) for x in panel_numbers} if panel_numbers else None
    out = []
    for m in model.members:
        if fam_set is not None and m.family.upper() not in fam_set:
            continue
        if panel_set is not None and m.panel_no not in panel_set:
            continue
        out.append(m)
    return out


def _hover_text(m: TowerMember) -> str:
    fy = "—" if m.fy is None else f"{m.fy:g}"
    return (
        f"Panel: {m.panel_no}<br>"
        f"Pattern: {m.line_type} {m.pattern}<br>"
        f"Member: {m.member_key} ({m.family})<br>"
        f"Section ID: {m.section_id if m.section_id is not None else '—'}<br>"
        f"Profile: {m.section_profile or '—'}<br>"
        f"fy: {fy}<br>"
        f"{m.note}"
    )


def make_tower_3d_figure(
    model: TowerGeometry,
    families: Optional[Sequence[str]] = None,
    panel_numbers: Optional[Sequence[int]] = None,
    height_px: int = 720,
) -> go.Figure:
    members = _filtered_members(model, families, panel_numbers)
    fig = go.Figure()

    ordered_families = FAMILY_ORDER + sorted(
        set(m.family for m in members) - set(FAMILY_ORDER)
    )
    for family in ordered_families:
        fam_members = [m for m in members if m.family == family]
        if not fam_members:
            continue
        xs: List[Optional[float]] = []
        ys: List[Optional[float]] = []
        zs: List[Optional[float]] = []
        texts: List[Optional[str]] = []
        for m in fam_members:
            text = _hover_text(m)
            xs += [m.start[0], m.end[0], None]
            ys += [m.start[1], m.end[1], None]
            zs += [m.start[2], m.end[2], None]
            texts += [text, text, None]
        fig.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="lines",
                name=family,
                text=texts,
                hoverinfo="text",
                line={"width": 5 if family == "LEG" else 3},
            )
        )

    fig.update_layout(
        height=height_px,
        margin={"l": 0, "r": 0, "t": 35, "b": 0},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0},
        scene={
            "xaxis_title": "X (m)",
            "yaxis_title": "Y (m)",
            "zaxis_title": "Elevation (m)",
            "aspectmode": "data",
            "camera": {"eye": {"x": 1.45, "y": 1.45, "z": 0.9}},
        },
        title={"text": "3D Tower Geometry", "x": 0.01, "xanchor": "left"},
    )
    return fig



def make_material_elevation_figure(
    model: TowerGeometry,
    height_px: int = 760,
) -> go.Figure:
    """Render a static drawing-style material schedule aligned to tower elevation.

    Each column is a member family and each rectangular cell spans the actual
    PROFILE panel elevation. This mirrors the material strip convention used on
    tower outline drawings while keeping the schedule generated from the same
    member geometry as the 2D/3D views.
    """
    categories = [
        ("LEG", "MAIN LEG"),
        ("BR", "BRACING"),
        ("HOR", "HORIZONTAL"),
        ("RED", "REDUNDANT"),
        ("PBR", "PLAN BRACING"),
        ("HIP", "HIP STAY"),
        ("UDP", "UDP"),
    ]
    panels = sorted(model.panels, key=lambda p: p.z_bottom)
    z_min = min([p.z_bottom for p in panels], default=model.rlbas)
    z_max = max([p.z_top for p in panels], default=model.rlbas + max(model.total_height, 1.0))

    fig = go.Figure()
    # White dummy trace stabilizes axes without creating an interactive legend.
    fig.add_trace(go.Scatter(x=[0, len(categories)], y=[z_min, z_max], mode="markers", marker={"opacity": 0}, hoverinfo="skip", showlegend=False))

    for panel in panels:
        panel_members = [m for m in model.members if m.panel_no == panel.panel_no]
        for col_idx, (family, label) in enumerate(categories):
            labels: List[str] = []
            for m in panel_members:
                if str(m.family).upper() != family:
                    continue
                material = _material_label(m.section_profile, m.section_id)
                if material != "—" and material not in labels:
                    labels.append(material)
            text = " | ".join(labels) if labels else ""
            fig.add_shape(
                type="rect",
                x0=col_idx,
                x1=col_idx + 1,
                y0=panel.z_bottom,
                y1=panel.z_top,
                line={"width": 0.8},
                fillcolor="rgba(0,0,0,0)",
                layer="below",
            )
            if text:
                # Vertical text fits narrow drawing-style columns and stays
                # readable when many sections are stacked over tower height.
                fig.add_annotation(
                    x=col_idx + 0.5,
                    y=(panel.z_bottom + panel.z_top) / 2.0,
                    text=text,
                    textangle=-90,
                    showarrow=False,
                    font={"size": 10},
                    xanchor="center",
                    yanchor="middle",
                )

    # Full-height category boundaries and bottom category captions.
    for x in range(len(categories) + 1):
        fig.add_shape(type="line", x0=x, x1=x, y0=z_min, y1=z_max, line={"width": 1.0})
    for i, (_, label) in enumerate(categories):
        fig.add_annotation(
            x=i + 0.5,
            y=z_min,
            yshift=-22,
            text=label,
            textangle=-90,
            showarrow=False,
            font={"size": 10},
            xanchor="center",
            yanchor="top",
        )
    return fig


def make_tower_2d_figure(
    model: TowerGeometry,
    view: str = "Face 1",
    families: Optional[Sequence[str]] = None,
    panel_numbers: Optional[Sequence[int]] = None,
    height_px: int = 760,
) -> go.Figure:
    """Render a static, physically proportional 2D side elevation.

    The function keeps the previous optional filters for API compatibility, but
    the Streamlit UI intentionally shows the complete tower and exposes only a
    side selector. For 3/4-leg lattice towers, ``Face N`` shows one physical
    FACE plus every UDP member projected onto the same viewing plane. For a
    FACES=1 pole model, ``Side X`` and ``Side Y`` show the raw coordinate
    projection so @UDP pole geometry remains visible.
    """
    members = _filtered_members(model, families, panel_numbers)
    view_upper = str(view).upper().strip()
    selected_face: Optional[int] = None
    face_dir: Optional[Tuple[float, float]] = None

    face_match = re.match(r"^FACE\s+(\d+)$", view_upper)
    if face_match and model.faces >= 3:
        selected_face = int(face_match.group(1))
        if selected_face < 1 or selected_face > model.faces:
            selected_face = 1

        unit = _corners(1.0, 0.0, model.faces)
        i0 = (selected_face - 1) % len(unit)
        i1 = selected_face % len(unit)
        dx = unit[i1][0] - unit[i0][0]
        dy = unit[i1][1] - unit[i0][1]
        norm = math.hypot(dx, dy) or 1.0
        face_dir = (dx / norm, dy / norm)
        leg_a, leg_b = i0 + 1, i1 + 1

        # Standard FACE: isolate the selected physical face. UDP: always keep,
        # because NODE/MEMB coordinates are already physical and may span more
        # than one conventional face (custom rooftop poles, brackets, etc.).
        selected: List[TowerMember] = []
        for m in members:
            if m.family == "UDP" or m.line_type == "UDP":
                selected.append(m)
                continue
            if m.line_type == "FACE" and m.note == f"Face {selected_face}":
                selected.append(m)
                continue
            if m.family == "LEG" and m.line_type == "FACE" and m.note in {
                f"Leg {leg_a}", f"Leg {leg_b}"
            }:
                selected.append(m)
        members = selected

    def project(p: Point3D) -> Tuple[float, float]:
        if selected_face is not None and face_dir is not None:
            return p[0] * face_dir[0] + p[1] * face_dir[1], p[2]
        if "SIDE Y" in view_upper or view_upper in {"Y", "FRONT Y"}:
            return p[1], p[2]
        return p[0], p[2]

    fig = go.Figure()
    ordered_families = FAMILY_ORDER + sorted(set(m.family for m in members) - set(FAMILY_ORDER))
    all_x: List[float] = []
    all_y: List[float] = []

    for family in ordered_families:
        fam_members = [m for m in members if m.family == family]
        if not fam_members:
            continue
        xs: List[Optional[float]] = []
        ys: List[Optional[float]] = []
        for m in fam_members:
            x1, y1 = project(m.start)
            x2, y2 = project(m.end)
            xs += [x1, x2, None]
            ys += [y1, y2, None]
            all_x.extend([x1, x2])
            all_y.extend([y1, y2])
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=family,
                hoverinfo="skip",
                line={"width": 2.8 if family == "LEG" else 1.6},
            )
        )

    # Explicit ranges + equal engineering scale prevent the tower from being
    # stretched horizontally by responsive Plotly layout.
    if all_x and all_y:
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)
    else:
        xmin, xmax = -max(model.wbase, 1.0) / 2, max(model.wbase, 1.0) / 2
        ymin, ymax = model.rlbas, model.rlbas + max(model.total_height, 1.0)

    xmid = (xmin + xmax) / 2
    width = max(xmax - xmin, max(model.wbase, 0.5), 0.5)
    yspan = max(ymax - ymin, 1.0)
    xpad = max(width * 0.12, 0.15)
    ypad = max(yspan * 0.015, 0.15)

    if selected_face is not None:
        title = f"2D Tower Elevation — Face {selected_face}"
        x_title = f"Face {selected_face} width (m)"
    elif "Y" in view_upper:
        title = "2D Tower Elevation — Side Y"
        x_title = "Y (m)"
    else:
        title = "2D Tower Elevation — Side X"
        x_title = "X (m)"

    # Subtle section boundary guides improve drawing readability but are not
    # structural members. They never substitute for H1/H2 geometry.
    for p in model.panels:
        fig.add_shape(
            type="line",
            x0=xmid - width / 2 - xpad * 0.25,
            x1=xmid + width / 2 + xpad * 0.25,
            y0=p.z_bottom, y1=p.z_bottom,
            line={"width": 0.5, "dash": "dot"},
            layer="below",
        )

    fig.update_layout(
        height=height_px,
        margin={"l": 20, "r": 20, "t": 45, "b": 20},
        showlegend=False,
        title={"text": title, "x": 0.01, "xanchor": "left"},
        hovermode=False,
        dragmode=False,
        xaxis={
            "range": [xmid - width / 2 - xpad, xmid + width / 2 + xpad],
            "fixedrange": True,
            "showgrid": False,
            "showticklabels": False,
            "zeroline": False,
            "constrain": "domain",
        },
        yaxis={
            "range": [ymin - ypad, ymax + ypad],
            "fixedrange": True,
            "showgrid": False,
            "showticklabels": True,
            "ticksuffix": " m",
            "zeroline": False,
            "scaleanchor": "x",
            "scaleratio": 1,
            "constrain": "domain",
        },
    )
    return fig


__all__ = [
    "GEOMETRY_API_VERSION",
    "TowerGeometry",
    "TowerMember",
    "PanelSpec",
    "SUPPORTED_FACE_PATTERNS",
    "SUPPORTED_PLAN_PATTERNS",
    "SUPPORTED_HIP_PATTERNS",
    "FAMILY_ORDER",
    "parse_profile",
    "build_tower_geometry",
    "parse_udp_definition",
    "geometry_panels_dataframe",
    "geometry_members_dataframe",
    "material_schedule_dataframe",
    "geometry_validation_dataframe",
    "geometry_validation_summary",
    "make_engineering_2d_figure",
    "make_material_elevation_figure",
    "make_tower_2d_figure",
    "make_tower_3d_figure",
]