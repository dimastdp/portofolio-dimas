import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import io
import re
import folium
from streamlit_folium import st_folium
from folium.plugins import MeasureControl, Draw, Fullscreen
from geopy.distance import geodesic
from shapely.geometry import shape, Point
import urllib.request
import urllib.parse
import base64
import hashlib
import html
import json


# ==========================================================
# CONFIG
# ==========================================================

st.set_page_config(
    page_title="Geo-Mapper Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================================
# CSS
# ==========================================================

st.markdown(
    """
    <style>

    .stFolium {
        width: 100% !important;
    }

    div[data-testid="stDataFrame"] {
        width: 100%;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        padding: 8px;
        border-radius: 8px;
    }

    .process-box {
        padding: 12px;
        border-radius: 10px;
        border: 1px solid rgba(128,128,128,0.25);
        background: rgba(128,128,128,0.05);
        margin-bottom: 10px;
    }

    .small-info {
        font-size: 12px;
        opacity: 0.75;
    }

    .mode-box {
        padding: 8px 10px;
        border-radius: 8px;
        background: rgba(52,152,219,0.08);
        border: 1px solid rgba(52,152,219,0.20);
        margin-bottom: 8px;
        font-size: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# SESSION STATE
# ==========================================================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "analysis_config" not in st.session_state:
    st.session_state.analysis_config = None

if "processed" not in st.session_state:
    st.session_state.processed = False

if "last_source_hash" not in st.session_state:
    st.session_state.last_source_hash = None

if "tower_reviews" not in st.session_state:
    # review_key -> {"status": "CONTINUE|HOLD|DROP", "remark": "..."}
    st.session_state.tower_reviews = {}

if "last_review_message" not in st.session_state:
    st.session_state.last_review_message = None

if "processed_review_actions" not in st.session_state:
    st.session_state.processed_review_actions = set()


# ==========================================================
# POPUP REVIEW ACTION (via query parameter)
# ==========================================================

def _query_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def process_popup_review_action():
    """
    Menerima aksi dari tombol Continue/Hold/Drop di Folium popup.
    Tombol popup menulis query parameter pada halaman Streamlit utama,
    lalu fungsi ini menyimpannya ke session_state.
    """

    try:
        qp = st.query_params

        review_key = _query_value(
            qp.get("tower_review_key")
        )

        review_status = _query_value(
            qp.get("tower_review_status")
        )

        review_remark = _query_value(
            qp.get("tower_review_remark", "")
        )

        valid_status = {
            "CONTINUE",
            "HOLD",
            "DROP"
        }

        if (
            review_key
            and review_status in valid_status
        ):

            st.session_state.tower_reviews[
                str(review_key)
            ] = {
                "status": str(review_status),
                "remark": str(review_remark or "").strip()
            }

            st.session_state.last_review_message = (
                f"Status tower disimpan: {review_status}"
            )

            # Bersihkan hanya parameter review agar action tidak dieksekusi ulang.
            for key in [
                "tower_review_key",
                "tower_review_status",
                "tower_review_remark"
            ]:
                if key in st.query_params:
                    del st.query_params[key]

    except Exception:
        # Aplikasi tetap berjalan pada versi Streamlit yang tidak mendukung
        # st.query_params secara penuh.
        pass


process_popup_review_action()


# ==========================================================
# HELPER
# ==========================================================

def make_source_hash(data_bytes, filename=""):
    """
    Membuat hash untuk mendeteksi perubahan database.
    """

    if data_bytes is None:
        return None

    h = hashlib.md5()

    h.update(data_bytes)

    h.update(
        filename.encode(
            "utf-8",
            errors="ignore"
        )
    )

    return h.hexdigest()


# ==========================================================
# LOAD DATA
# ==========================================================

@st.cache_data(
    show_spinner=False,
    max_entries=10
)
def load_and_clean_data(
    source_bytes,
    filename="",
    source_type="file"
):

    if source_bytes is None:
        return None

    try:

        # --------------------------------------------------
        # TEXT / CSV PASTE
        # --------------------------------------------------

        if source_type == "text":

            if isinstance(
                source_bytes,
                bytes
            ):

                text = source_bytes.decode(
                    "utf-8",
                    errors="replace"
                )

            else:

                text = str(
                    source_bytes
                )

            df = pd.read_csv(
                io.StringIO(text),
                sep=None,
                engine="python",
                dtype=str,
                on_bad_lines="skip"
            )

        # --------------------------------------------------
        # EXCEL
        # --------------------------------------------------

        elif filename.lower().endswith(
            (
                ".xls",
                ".xlsx"
            )
        ):

            df = pd.read_excel(
                io.BytesIO(
                    source_bytes
                ),
                dtype=str
            )

        # --------------------------------------------------
        # CSV FILE
        # --------------------------------------------------

        else:

            encodings = [
                "utf-8-sig",
                "utf-8",
                "latin1",
                "cp1252",
                "ISO-8859-1"
            ]

            df = None

            for enc in encodings:

                try:

                    text = source_bytes.decode(
                        enc
                    )

                    df = pd.read_csv(
                        io.StringIO(text),
                        sep=None,
                        engine="python",
                        dtype=str,
                        on_bad_lines="skip"
                    )

                    break

                except UnicodeDecodeError:

                    continue

            if df is None:

                raise ValueError(
                    "Format encoding file "
                    "tidak didukung."
                )

        # --------------------------------------------------
        # CLEAN HEADER
        # --------------------------------------------------

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        # --------------------------------------------------
        # REMOVE DUPLICATE COLUMNS
        # --------------------------------------------------

        df = (
            df.loc[
                :,
                ~df.columns.duplicated()
            ]
            .copy()
        )

        return df

    except Exception as e:

        st.error(
            f"Gagal membaca data: {e}"
        )

        return None


# ==========================================================
# SMART COLUMN DETECTION
# ==========================================================

def smart_detect(
    options,
    primary_keys,
    secondary_keys,
    default_idx
):

    if not options:
        return 0

    # ------------------------------------------------------
    # PRIMARY
    # ------------------------------------------------------

    for i, col in enumerate(options):

        col_lower = str(
            col
        ).lower()

        if any(
            k in col_lower
            for k in primary_keys
        ):

            return i

    # ------------------------------------------------------
    # SECONDARY
    # ------------------------------------------------------

    for i, col in enumerate(options):

        col_lower = str(
            col
        ).lower()

        if any(
            k in col_lower
            for k in secondary_keys
        ):

            return i

    return min(
        default_idx,
        len(options) - 1
    )


# ==========================================================
# SAFE FLOAT
# ==========================================================

def safe_to_float(series):

    s = (
        series
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------------
    # Remove spaces
    # ------------------------------------------------------

    s = s.str.replace(
        " ",
        "",
        regex=False
    )

    # ------------------------------------------------------
    # Handle decimal comma
    # ------------------------------------------------------

    s = s.str.replace(
        ",",
        ".",
        regex=False
    )

    return pd.to_numeric(
        s,
        errors="coerce"
    )


# ==========================================================
# HAVERSINE VECTOR
# ==========================================================

def haversine_vectorized(
    lat1,
    lon1,
    lat2,
    lon2
):

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)

    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(
            dlat / 2.0
        ) ** 2
        +
        np.cos(lat1)
        *
        np.cos(lat2)
        *
        np.sin(
            dlon / 2.0
        ) ** 2
    )

    a = np.clip(
        a,
        0,
        1
    )

    return (
        6371000
        *
        2
        *
        np.arcsin(
            np.sqrt(a)
        )
    )


# ==========================================================
# FILTER DATAFRAME BY TARGET RADIUS
# ==========================================================

def filter_dataframe_by_target_radius(
    source_df,
    targets,
    radius_m
):
    """
    Filter tampilan map: tower masuk bila berada dalam radius terhadap
    minimal satu target yang dipilih (union radius). Tidak mengubah
    dataframe hasil analisis utama.
    """

    if (
        source_df is None
        or source_df.empty
        or not targets
    ):
        return source_df.copy() if source_df is not None else pd.DataFrame()

    mask = np.zeros(
        len(source_df),
        dtype=bool
    )

    lat_values = source_df[
        "lat_val"
    ].to_numpy()

    lon_values = source_df[
        "lon_val"
    ].to_numpy()

    for target in targets:

        distances = haversine_vectorized(
            float(target["lat"]),
            float(target["lon"]),
            lat_values,
            lon_values
        )

        mask = (
            mask
            |
            (distances <= float(radius_m))
        )

    return source_df.loc[
        mask
    ].copy()


# ==========================================================
# BUILD DISPLAY NAME
# ==========================================================

def create_display_name(
    df,
    name_col,
    unique_col,
    suffix=""
):

    return (
        df[name_col]
        .fillna("")
        .astype(str)
        .str.strip()
        +
        " ["
        +
        df[unique_col]
        .fillna("")
        .astype(str)
        .str.strip()
        +
        "]"
        +
        suffix
    )


# ==========================================================
# ESCAPE HTML
# ==========================================================

def esc(value):

    return html.escape(
        str(value)
    )


# ==========================================================
# REVIEW / POPUP HELPERS
# ==========================================================

def make_review_key(
    row,
    c_unique_col
):
    """Stable key per tower: unique ID + coordinate."""

    unique_value = str(
        row.get(
            c_unique_col,
            ""
        )
    ).strip()

    try:
        lat = float(
            row.get(
                "lat_val"
            )
        )

        lon = float(
            row.get(
                "lon_val"
            )
        )

        return (
            f"{unique_value}||"
            f"{lat:.7f}||"
            f"{lon:.7f}"
        )

    except Exception:
        return unique_value


def get_review(
    row,
    c_unique_col
):

    review_key = make_review_key(
        row,
        c_unique_col
    )

    review = st.session_state.tower_reviews.get(
        review_key,
        {}
    )

    return (
        review_key,
        review.get(
            "status",
            "BELUM REVIEW"
        ),
        review.get(
            "remark",
            ""
        )
    )


def _popup_url_href(url_text):
    """
    Normalisasi URL untuk href popup.

    Spasi yang memang menjadi bagian URL/file name di-encode menjadi %20,
    tanpa merusak karakter URL penting seperti / ? & = # dan %.
    """

    href = str(url_text).strip()

    if href.lower().startswith("www."):
        href = "https://" + href

    # Browser membutuhkan spasi pada URL sebagai percent-encoding.
    # '%' dibuat safe agar URL yang sudah memiliki %20 tidak menjadi %2520.
    return urllib.parse.quote(
        href,
        safe=":/?&=#%+@!$'()*,-._~[]"
    )


def linkify_popup_value(value):
    """
    Membuat URL dan alamat email pada popup menjadi clickable.

    Perbaikan penting:
    - URL yang mengandung spasi, misalnya ``.../42 M.pdf``, tetap dianggap
      SATU link utuh dan href-nya otomatis menjadi ``.../42%20M.pdf``.
    - Beberapa URL dalam satu cell tetap dapat dibuat clickable satu per satu
      bila dipisahkan newline / koma / titik-koma / pipe sebelum URL berikutnya.
    - URL yang berada di tengah kalimat tetap memakai parsing konservatif agar
      teks biasa setelah URL tidak ikut terseret menjadi link.
    """

    raw = str(value).strip()

    if not raw:
        return ""

    # ==========================================================
    # CASE 1 — CELL DIAWALI URL
    # ==========================================================
    # Pada database link dokumen biasanya seluruh isi cell adalah URL.
    # Karena nama file/path dapat memiliki spasi, JANGAN berhenti di whitespace.
    if re.match(r"(?i)^(?:https?://|www\.)", raw):

        # Pisahkan HANYA bila separator benar-benar diikuti URL berikutnya.
        # Dengan demikian ".../42 M.pdf" tidak terpotong pada spasi.
        url_parts = re.split(
            r"\s*(?:\r?\n|[;,|])\s*(?=(?:https?://|www\.))",
            raw,
            flags=re.IGNORECASE
        )

        rendered = []

        for url_text in url_parts:
            url_text = url_text.strip()

            if not url_text:
                continue

            href = _popup_url_href(url_text)

            label = (
                url_text
                if len(url_text) <= 58
                else url_text[:55] + "..."
            )

            rendered.append(
                "<a "
                f"href='{esc(href)}' "
                "target='_blank' "
                "rel='noopener noreferrer' "
                "style='color:#2980b9;"
                "text-decoration:underline;"
                "font-weight:600;"
                "overflow-wrap:anywhere;' "
                f"title='{esc(url_text)}'>"
                f"{esc(label)}"
                "</a>"
            )

        return "<br>".join(rendered)

    # ==========================================================
    # CASE 2 — TEKS CAMPURAN
    # ==========================================================
    # Untuk URL yang berada di tengah teks, whitespace tetap dianggap pemisah.
    token_pattern = re.compile(
        r"(?P<email>[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})"
        r"|(?P<url>https?://[^\s,;<>]+|www\.[^\s,;<>]+)",
        flags=re.IGNORECASE
    )

    matches = list(token_pattern.finditer(raw))

    if not matches:
        display = raw

        if len(display) > 80:
            display = display[:77] + "..."

        return esc(display)

    parts = []
    last_end = 0

    for match in matches:
        parts.append(
            esc(raw[last_end:match.start()])
        )

        email_text = match.group("email")
        url_text = match.group("url")

        if email_text:
            parts.append(
                "<a "
                f"href='mailto:{esc(email_text)}' "
                "style='color:#2980b9;"
                "text-decoration:underline;"
                "font-weight:600;' "
                f"title='Kirim email ke {esc(email_text)}'>"
                f"{esc(email_text)}"
                "</a>"
            )

        else:
            href = _popup_url_href(url_text)

            label = (
                url_text
                if len(url_text) <= 45
                else url_text[:42] + "..."
            )

            parts.append(
                "<a "
                f"href='{esc(href)}' "
                "target='_blank' "
                "rel='noopener noreferrer' "
                "style='color:#2980b9;"
                "text-decoration:underline;"
                "font-weight:600;"
                "overflow-wrap:anywhere;' "
                f"title='{esc(url_text)}'>"
                f"{esc(label)}"
                "</a>"
            )

        last_end = match.end()

    parts.append(
        esc(raw[last_end:])
    )

    return "".join(parts)



def build_popup_data_grid(
    items,
    visible_limit=9
):
    """
    Grid data popup yang compact dan responsive.
    Hanya sejumlah field pertama yang ditampilkan langsung; sisanya
    dapat dibuka lewat disclosure "Lihat data lainnya".
    """

    items = list(items or [])

    def render_grid(entries):
        if not entries:
            return ""

        html_grid = (
            "<div class='tower-popup-grid'>"
        )

        for k, v in entries:
            html_grid += (
                "<div class='tower-popup-item'>"
                "<div class='tower-popup-key'>"
                f"{esc(k)}"
                "</div>"
                "<div class='tower-popup-value'>"
                f"{linkify_popup_value(v)}"
                "</div>"
                "</div>"
            )

        html_grid += "</div>"

        return html_grid

    primary = items[:visible_limit]
    extra = items[visible_limit:]

    html_code = render_grid(primary)

    if extra:
        html_code += (
            "<details class='tower-popup-more'>"
            "<summary>"
            f"Lihat {len(extra)} data lainnya"
            "</summary>"
            +
            render_grid(extra)
            +
            "</details>"
        )

    return html_code


def build_gmaps_shortcut(
    row,
    c_name_col,
    c_unique_col,
    current_status="BELUM REVIEW",
    current_remark="",
    tower_lat=None,
    tower_lon=None
):
    """
    Shortcut Google Maps berdasarkan latitude dan longitude tower.
    Tombol membuka titik tower langsung pada tab Google Maps baru.
    """

    if (
        tower_lat is None
        or tower_lon is None
    ):
        return ""

    try:
        lat = float(tower_lat)
        lon = float(tower_lon)
    except Exception:
        return ""

    site_id = str(
        row.get(
            c_unique_col,
            ""
        )
    ).strip()

    site_name = str(
        row.get(
            c_name_col,
            ""
        )
    ).strip()

    query = f"{lat:.7f},{lon:.7f}"

    gmaps_url = (
        "https://www.google.com/maps/search/?"
        +
        urllib.parse.urlencode(
            {
                "api": "1",
                "query": query
            }
        )
    )

    tooltip = (
        f"Buka Google Maps | {site_id} | {site_name} | "
        f"{lat:.7f}, {lon:.7f}"
    )

    return (
        "<div class='tower-popup-actions'>"
        "<a class='tower-gmaps-button' "
        f"href='{esc(gmaps_url)}' "
        "target='_blank' "
        "rel='noopener noreferrer' "
        f"title='{esc(tooltip)}'>"
        "📍 GMaps"
        "</a>"
        "<span class='tower-gmaps-coord'>"
        f"{lat:.6f}, {lon:.6f}"
        "</span>"
        "</div>"
    )


def build_review_controls(
    review_key,
    current_status="BELUM REVIEW",
    current_remark="",
    map_js_name=None,
    tower_lat=None,
    tower_lon=None
):
    """
    HTML control pada popup.

    Jalur utama: tombol membuat event Draw khusus di Leaflet map. Event ini
    dikembalikan oleh st_folium melalui all_drawings, lalu disimpan ke
    Streamlit session_state tanpa me-refresh seluruh halaman/browser session.

    Query-parameter dipertahankan sebagai fallback bila map JS tidak tersedia.
    """

    if not review_key:
        return ""

    safe_id = hashlib.md5(
        str(review_key).encode(
            "utf-8",
            errors="ignore"
        )
    ).hexdigest()[:10]

    remark_id = (
        "review_remark_"
        +
        safe_id
    )

    review_key_js = json.dumps(
        str(review_key)
    )

    status_display = esc(
        current_status or "BELUM REVIEW"
    )

    remark_display = esc(
        current_remark or ""
    )

    has_leaflet_channel = (
        map_js_name
        and tower_lat is not None
        and tower_lon is not None
    )

    def button_html(
        label,
        status,
        color
    ):

        if has_leaflet_channel:

            onclick_js = (
                f'var r=document.getElementById("{remark_id}").value;'
                'var actionId="review_"+Date.now().toString()+"_"+'
                'Math.random().toString(36).slice(2);'
                f'var layer=L.marker([{float(tower_lat):.8f},'
                f'{float(tower_lon):.8f}],'
                '{opacity:0,interactive:false});'
                'layer.feature={type:"Feature",properties:{'
                '_review_action:true,'
                'review_action_id:actionId,'
                f'review_key:{review_key_js},'
                f'review_status:"{status}",'
                'review_remark:r'
                '}};'
                f'{map_js_name}.fire(L.Draw.Event.CREATED,'
                '{layer:layer,layerType:"marker"});'
                f'{map_js_name}.closePopup();'
                'return false;'
            )

        else:

            onclick_js = (
                f'var r=document.getElementById("{remark_id}").value;'
                'window.top.location.search='
                '"?tower_review_key="+'
                f'encodeURIComponent({review_key_js})+'
                f'"&tower_review_status={status}"+'
                '"&tower_review_remark="+'
                'encodeURIComponent(r);'
                'return false;'
            )

        return (
            "<button "
            "type='button' "
            "style='border:none;"
            f"background:{color};"
            "color:white;"
            "padding:7px 10px;"
            "border-radius:5px;"
            "font-size:11px;"
            "font-weight:bold;"
            "cursor:pointer;"
            "margin-right:5px;"
            "margin-bottom:5px;' "
            f"onclick='{esc(onclick_js)}'>"
            f"{esc(label)}"
            "</button>"
        )

    return (
        "<div class='tower-review-box' style='margin-top:8px;"
        "padding:8px;"
        "border:1px solid #dfe6e9;"
        "border-radius:6px;"
        "background:#fafafa;'>"
        "<div style='font-size:10px;"
        "font-weight:bold;"
        "color:#2c3e50;"
        "text-transform:uppercase;"
        "margin-bottom:5px;'>"
        "✅ Status Analisa Tower"
        "</div>"
        "<div style='font-size:10px;"
        "margin-bottom:7px;"
        "color:#555;'>"
        "Status saat ini: "
        f"<b>{status_display}</b>"
        "</div>"
        f"<textarea id='{remark_id}' "
        "placeholder='Tulis remark...' "
        "style='width:100%;"
        "min-height:48px;"
        "box-sizing:border-box;"
        "padding:7px;"
        "border:1px solid #ccc;"
        "border-radius:5px;"
        "font-size:11px;"
        "margin-bottom:7px;'>"
        f"{remark_display}"
        "</textarea>"
        +
        button_html(
            "CONTINUE",
            "CONTINUE",
            "#27ae60"
        )
        +
        button_html(
            "HOLD",
            "HOLD",
            "#f39c12"
        )
        +
        button_html(
            "DROP",
            "DROP",
            "#c0392b"
        )
        +
        "<div style='font-size:9px;"
        "color:#7f8c8d;"
        "margin-top:3px;'>"
        "Isi remark lalu klik status untuk menyimpan."
        "</div>"
        "</div>"
    )


# ==========================================================
# POPUP STANDARD
# ==========================================================

def build_popup(
    row,
    c_name_col,
    c_unique_col,
    jarak_m=None,
    title_prefix="",
    review_key=None,
    current_status="BELUM REVIEW",
    current_remark="",
    map_js_name=None,
    tower_lat=None,
    tower_lon=None
):

    unique_value = esc(
        row.get(
            c_unique_col,
            ""
        )
    )

    name_value = esc(
        row.get(
            c_name_col,
            ""
        )
    )

    html_code = (
        "<div class='tower-popup-shell'>"
    )

    # ------------------------------------------------------
    # HEADER
    # ------------------------------------------------------

    html_code += (
        "<div class='tower-popup-header' "
        "style='background:#2C3E50;'>"
        "<div class='tower-popup-title'>"
        f"{esc(title_prefix)}"
        f"ID: {unique_value} | "
        f"{name_value}"
        "</div>"
    )

    if (
        jarak_m is not None
        and pd.notna(jarak_m)
    ):

        html_code += (
            "<div class='tower-popup-distance'>"
            "Jarak: "
            f"<b>{float(jarak_m):,.2f} meter</b>"
            "</div>"
        )

    html_code += "</div>"

    # ------------------------------------------------------
    # EXCLUDE INTERNAL COLUMNS
    # ------------------------------------------------------

    exclude_cols = {
        "display_name",
        "display_name_ext",
        "lat_val",
        "lon_val",
        "Jarak_Fast_Calc",
        "Jarak (m)",
        "Sumber Analisa",
        "Objek Filter",
        "_nearest_key",
        "_coord_key",
        "_target_relations",
        "_relation_count",
        "Analisis_Type",
        "Status Analisa",
        "Remark"
    }

    valid_items = [
        (k, v)
        for k, v in row.items()
        if (
            k not in exclude_cols
            and pd.notna(v)
            and str(v).strip() != ""
        )
    ]

    html_code += build_popup_data_grid(
        valid_items,
        visible_limit=9
    )

    html_code += build_gmaps_shortcut(
        row,
        c_name_col,
        c_unique_col,
        current_status=current_status,
        current_remark=current_remark,
        tower_lat=tower_lat,
        tower_lon=tower_lon
    )

    html_code += build_review_controls(
        review_key,
        current_status,
        current_remark,
        map_js_name=map_js_name,
        tower_lat=tower_lat,
        tower_lon=tower_lon
    )

    html_code += "</div>"

    return html_code


# ==========================================================
# POPUP RELATION
# ==========================================================

def build_relation_popup(
    tower_row,
    c_name_col,
    c_unique_col,
    primary_target,
    primary_distance,
    other_relations=None,
    is_nearest=False,
    is_acuan=False,
    review_key=None,
    current_status="BELUM REVIEW",
    current_remark="",
    map_js_name=None,
    tower_lat=None,
    tower_lon=None
):

    tower_id = esc(
        tower_row.get(
            c_unique_col,
            ""
        )
    )

    tower_name = esc(
        tower_row.get(
            c_name_col,
            ""
        )
    )

    target_label = esc(
        primary_target
    )

    # ------------------------------------------------------
    # HEADER COLOR
    # ------------------------------------------------------

    if is_acuan:
        header_bg = "#d35400"
    elif is_nearest:
        header_bg = "#c0392b"
    else:
        header_bg = "#2C3E50"

    popup = (
        "<div class='tower-popup-shell'>"
        f"<div class='tower-popup-header' style='background:{header_bg};'>"
        "<div class='tower-popup-title'>"
        f"ID: {tower_id} | {tower_name}"
        "</div>"
        "<div class='tower-popup-relation'>"
        f"{target_label} → {tower_name}"
        "</div>"
        "<div class='tower-popup-distance'>"
        f"Jarak: <b>{primary_distance:,.2f} meter</b>"
        "</div>"
        "</div>"
    )

    # ======================================================
    # OVERLAP RELATIONS
    # ======================================================

    if other_relations:
        popup += (
            "<details class='tower-overlap-box'>"
            "<summary>🔗 Irisan titik acuan lainnya "
            f"({len(other_relations)})</summary>"
        )

        for relation in other_relations:
            other_label = esc(
                relation["target"]
            )

            distance = float(
                relation["distance"]
            )

            popup += (
                "<div class='tower-overlap-row'>"
                f"<b>{other_label}</b> → {tower_name}<br>"
                "<span>"
                f"Jarak: {distance:,.2f} meter"
                "</span>"
                "</div>"
            )

        popup += "</details>"

    # ======================================================
    # DETAIL
    # ======================================================

    exclude_cols = {
        "display_name",
        "display_name_ext",
        "lat_val",
        "lon_val",
        "Jarak_Fast_Calc",
        "Jarak (m)",
        "Sumber Analisa",
        "Objek Filter",
        "_nearest_key",
        "_coord_key",
        "_target_relations",
        "_relation_count",
        "Analisis_Type",
        "Status Analisa",
        "Remark"
    }

    valid_items = [
        (k, v)
        for k, v in tower_row.items()
        if (
            k not in exclude_cols
            and pd.notna(v)
            and str(v).strip() != ""
        )
    ]

    popup += build_popup_data_grid(
        valid_items,
        visible_limit=9
    )

    popup += build_gmaps_shortcut(
        tower_row,
        c_name_col,
        c_unique_col,
        current_status=current_status,
        current_remark=current_remark,
        tower_lat=tower_lat,
        tower_lon=tower_lon
    )

    popup += build_review_controls(
        review_key,
        current_status,
        current_remark,
        map_js_name=map_js_name,
        tower_lat=tower_lat,
        tower_lon=tower_lon
    )

    popup += "</div>"

    return popup


# ==========================================================
# PHOTO URL
# ==========================================================

def format_image_link(raw_url):

    if not isinstance(
        raw_url,
        str
    ):

        return None, None

    url = raw_url.strip()

    if (
        url == ""
        or url.lower() == "nan"
    ):

        return None, None

    # ------------------------------------------------------
    # Multiple URLs
    # ------------------------------------------------------

    if "," in url:

        url = (
            url
            .split(",")[0]
            .strip()
        )

    elif " " in url:

        url = (
            url
            .split(" ")[0]
            .strip()
        )

    # ------------------------------------------------------
    # Add HTTPS
    # ------------------------------------------------------

    if not url.startswith(
        "http"
    ):

        if (
            url.startswith("www.")
            or url.startswith("drive.")
            or url.startswith("servpinisi.")
        ):

            url = (
                "https://"
                +
                url
            )

        else:

            return None, None

    # ------------------------------------------------------
    # Google Drive
    # ------------------------------------------------------

    gdrive_match = re.search(
        r"drive\.google\.com/file/d/"
        r"([a-zA-Z0-9_-]+)",
        url
    )

    if gdrive_match:

        file_id = (
            gdrive_match.group(1)
        )

        direct_url = (
            "https://drive.google.com/"
            f"uc?export=view&id={file_id}"
        )

        return (
            direct_url,
            url
        )

    return (
        url,
        url
    )


# ==========================================================
# CACHE PHOTO
# ==========================================================

@st.cache_data(
    show_spinner=False,
    max_entries=200
)
def cached_download_image(url):

    try:

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            req,
            timeout=5
        ) as response:

            return response.read()

    except Exception:

        return None


# ==========================================================
# FIND PHOTO
# ==========================================================

def find_photo_url(
    df,
    lat,
    lon,
    c_lat,
    c_lon
):

    if (
        df is None
        or df.empty
    ):

        return None, None

    tolerance = 0.0005

    lat_diff = (
        abs(
            df[c_lat] - lat
        )
    )

    lon_diff = (
        abs(
            df[c_lon] - lon
        )
    )

    match = df[
        (lat_diff < tolerance)
        &
        (lon_diff < tolerance)
    ]

    photo_col = next(
        (
            col
            for col in df.columns
            if "last photo"
            in str(col).lower()
        ),
        None
    )

    if (
        not match.empty
        and photo_col
    ):

        url = match.iloc[0][
            photo_col
        ]

        if (
            pd.notna(url)
            and str(url).strip() != ""
        ):

            return (
                url,
                match.iloc[0]
            )

    return None, None


# ==========================================================
# EXACT DISTANCE
# ==========================================================

def exact_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    try:

        return round(
            geodesic(
                (
                    lat1,
                    lon1
                ),
                (
                    lat2,
                    lon2
                )
            ).meters,
            2
        )

    except Exception:

        return None


# ==========================================================
# ANALYSIS FUNCTION
# ==========================================================

@st.cache_data(
    show_spinner=False,
    max_entries=20
)
def calculate_analysis(
    df,
    targets,
    radius_m,
    n_nearest,
    analysis_mode
):

    if (
        df is None
        or df.empty
    ):

        return pd.DataFrame()

    if not targets:

        return pd.DataFrame()

    radius_m = float(
        radius_m
    )

    n_nearest = int(
        n_nearest
    )

    master = []

    # ======================================================
    # RELATION STORAGE
    #
    # Menyimpan hubungan tower dengan semua titik acuan.
    # Ini penting supaya tower yang overlap tidak kehilangan
    # hubungan dengan titik acuan lain setelah duplicate
    # removal.
    # ======================================================

    relation_store = {}

    # ======================================================
    # PROCESS TARGET
    # ======================================================

    for target in targets:

        target_lat = float(
            target["lat"]
        )

        target_lon = float(
            target["lon"]
        )

        target_label = str(
            target["label"]
        )

        # --------------------------------------------------
        # FAST DISTANCE
        # --------------------------------------------------

        distances = haversine_vectorized(
            target_lat,
            target_lon,
            df["lat_val"].to_numpy(),
            df["lon_val"].to_numpy()
        )

        temp = df.copy()

        temp[
            "Jarak_Fast_Calc"
        ] = distances

        # ==================================================
        # RADIUS
        # ==================================================

        if analysis_mode in [
            "Radius + Nearest",
            "Radius Only"
        ]:

            radius_mask = (
                temp["Jarak_Fast_Calc"]
                <= radius_m
            )

            radius_df = (
                temp[
                    radius_mask
                ]
                .copy()
            )

            if not radius_df.empty:

                radius_df[
                    "Analisis_Type"
                ] = "Radius"

                radius_df[
                    "Sumber Analisa"
                ] = (
                    "Titik Acuan ("
                    +
                    target_label
                    +
                    ")"
                )

                radius_df[
                    "Objek Filter"
                ] = (
                    f"Radius "
                    f"{radius_m:,.0f} meter"
                )

                master.append(
                    radius_df
                )

                # ------------------------------------------
                # STORE RELATION
                # ------------------------------------------

                for original_idx in (
                    radius_df.index
                ):

                    coord_key = (
                        round(
                            float(
                                df.loc[
                                    original_idx,
                                    "lat_val"
                                ]
                            ),
                            7
                        ),
                        round(
                            float(
                                df.loc[
                                    original_idx,
                                    "lon_val"
                                ]
                            ),
                            7
                        )
                    )

                    if coord_key not in relation_store:

                        relation_store[
                            coord_key
                        ] = []

                    relation_store[
                        coord_key
                    ].append(
                        {
                            "target":
                                target_label,
                            "distance":
                                float(
                                    temp.loc[
                                        original_idx,
                                        "Jarak_Fast_Calc"
                                    ]
                                )
                        }
                    )

        # ==================================================
        # NEAREST
        # ==================================================

        if (
            analysis_mode
            in [
                "Radius + Nearest",
                "Nearest Only"
            ]
            and n_nearest > 0
        ):

            nearest = (
                temp[
                    temp[
                        "Jarak_Fast_Calc"
                    ] > 1.0
                ]
                .sort_values(
                    "Jarak_Fast_Calc"
                )
                .head(
                    n_nearest
                )
                .copy()
            )

            if not nearest.empty:

                nearest[
                    "Analisis_Type"
                ] = "Nearest"

                nearest[
                    "Sumber Analisa"
                ] = (
                    "Titik Acuan ("
                    +
                    target_label
                    +
                    ")"
                )

                nearest[
                    "Objek Filter"
                ] = (
                    f"{n_nearest} "
                    "Tower Terdekat"
                )

                master.append(
                    nearest
                )

    # ======================================================
    # EMPTY
    # ======================================================

    if not master:

        return pd.DataFrame()

    # ======================================================
    # COMBINE
    # ======================================================

    result = pd.concat(
        master,
        ignore_index=True
    )

    # ======================================================
    # EXACT DISTANCE
    # ======================================================

    result[
        "Jarak (m)"
    ] = np.nan

    target_lookup = {
        str(t["label"]): t
        for t in targets
    }

    for idx in result.index:

        try:

            target_source = str(
                result.loc[
                    idx,
                    "Sumber Analisa"
                ]
            )

            target_label = (
                target_source
                .replace(
                    "Titik Acuan (",
                    ""
                )
                .rstrip(")")
            )

            target_match = (
                target_lookup.get(
                    target_label
                )
            )

            if target_match:

                result.loc[
                    idx,
                    "Jarak (m)"
                ] = exact_distance(
                    float(
                        target_match["lat"]
                    ),
                    float(
                        target_match["lon"]
                    ),
                    float(
                        result.loc[
                            idx,
                            "lat_val"
                        ]
                    ),
                    float(
                        result.loc[
                            idx,
                            "lon_val"
                        ]
                    )
                )

        except Exception:

            pass

    # ======================================================
    # COORDINATE KEY
    # ======================================================

    result[
        "_coord_key"
    ] = (
        result["lat_val"]
        .round(7)
        .astype(str)
        +
        "_"
        +
        result["lon_val"]
        .round(7)
        .astype(str)
    )

    # ======================================================
    # ADD RELATIONS
    # ======================================================

    result[
        "_target_relations"
    ] = result[
        "_coord_key"
    ].apply(
        lambda key: relation_store.get(
            tuple(
                map(
                    float,
                    key.split("_")
                )
            ),
            []
        )
    )

    # ======================================================
    # RELATION COUNT
    # ======================================================

    result[
        "_relation_count"
    ] = result[
        "_target_relations"
    ].apply(
        len
    )

    # ======================================================
    # PRIORITY
    #
    # Radius result diberi prioritas daripada nearest
    # ketika tower yang sama muncul dua kali.
    # ======================================================

    result[
        "_priority"
    ] = np.where(
        result["Analisis_Type"]
        == "Radius",
        0,
        1
    )

    # ======================================================
    # REMOVE DUPLICATE TOWER
    # ======================================================

    result = (
        result
        .sort_values(
            by=[
                "_coord_key",
                "_priority",
                "Jarak (m)"
            ],
            na_position="last"
        )
        .drop_duplicates(
            subset=[
                "_coord_key"
            ],
            keep="first"
        )
        .copy()
    )

    # ======================================================
    # REMOVE TEMP
    # ======================================================

    result = result.drop(
        columns=[
            "_priority"
        ],
        errors="ignore"
    )

    return result.reset_index(
        drop=True
    )


# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.title(
    "🛠️ Control Panel"
)


# ==========================================================
# MAIN DATABASE
# ==========================================================

with st.sidebar.expander(
    "📂 1. Source Database Utama",
    expanded=True
):

    uploaded_file = st.file_uploader(
        "Upload Data Utama",
        type=[
            "csv",
            "xlsx",
            "xls"
        ],
        key="main_file"
    )

    csv_input_text = st.text_area(
        "Atau Tempel Data (CSV format)",
        key="main_csv_text"
    )


# ==========================================================
# LOAD MAIN DATA
# ==========================================================

main_source_bytes = None

main_source_type = "file"

file_name_main = ""

if uploaded_file is not None:

    main_source_bytes = (
        uploaded_file.getvalue()
    )

    file_name_main = (
        uploaded_file.name
    )

elif csv_input_text.strip():

    main_source_bytes = (
        csv_input_text.encode(
            "utf-8"
        )
    )

    main_source_type = "text"


df_main_raw = load_and_clean_data(
    main_source_bytes,
    file_name_main,
    main_source_type
)


# ==========================================================
# MAIN APP
# ==========================================================

if df_main_raw is not None:

    # ======================================================
    # SOURCE CHANGE
    # ======================================================

    source_hash = make_source_hash(
        main_source_bytes,
        file_name_main
    )

    if (
        st.session_state.last_source_hash
        != source_hash
    ):

        st.session_state.last_source_hash = (
            source_hash
        )

        st.session_state.processed = False

        st.session_state.analysis_result = None

        st.session_state.analysis_config = None

        # Review lama tidak dibawa ke database yang berbeda.
        st.session_state.tower_reviews = {}
        st.session_state.processed_review_actions = set()


    # ======================================================
    # COLUMN MAPPING
    # ======================================================

    all_cols = (
        df_main_raw.columns.tolist()
    )

    st.sidebar.markdown(
        "### 🔍 Mapping Database"
    )

    c_name = st.sidebar.selectbox(
        "Nama Site",
        all_cols,
        index=smart_detect(
            all_cols,
            [
                "site",
                "name"
            ],
            [
                "actual"
            ],
            0
        ),
        key="main_name"
    )

    c_unique = st.sidebar.selectbox(
        "Kode Unik",
        all_cols,
        index=(
            1
            if len(all_cols) > 1
            else 0
        ),
        key="main_unique"
    )

    c_lat = st.sidebar.selectbox(
        "Latitude",
        all_cols,
        index=smart_detect(
            all_cols,
            [
                "lat"
            ],
            [],
            1
        ),
        key="main_lat"
    )

    c_lon = st.sidebar.selectbox(
        "Longitude",
        all_cols,
        index=smart_detect(
            all_cols,
            [
                "lon",
                "long"
            ],
            [],
            2
        ),
        key="main_lon"
    )


    # ======================================================
    # PREPARE MAIN DATA
    # ======================================================

    df = df_main_raw.copy()

    df["lat_val"] = safe_to_float(
        df[c_lat]
    )

    df["lon_val"] = safe_to_float(
        df[c_lon]
    )

    # ------------------------------------------------------
    # VALID COORDINATES
    # ------------------------------------------------------

    df = df[
        df["lat_val"].notna()
        &
        df["lon_val"].notna()
        &
        (df["lat_val"] != 0)
        &
        (df["lon_val"] != 0)
        &
        df["lat_val"].between(
            -90,
            90
        )
        &
        df["lon_val"].between(
            -180,
            180
        )
    ].reset_index(
        drop=True
    )


    # ======================================================
    # FILTER MAIN DATA
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "🎯 1.5. Filter Data Utama"
    )

    filter_col = st.sidebar.selectbox(
        "Pilih Kolom Filter",
        [
            "-- TIDAK ADA --"
        ]
        +
        list(
            df_main_raw.columns
        ),
        key="main_filter_col"
    )

    if (
        filter_col
        != "-- TIDAK ADA --"
    ):

        unique_vals = (
            df_main_raw[
                filter_col
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        filter_vals = st.sidebar.multiselect(
            f"Pilih Value '{filter_col}'",
            unique_vals,
            key="main_filter_values"
        )

        if filter_vals:

            df = df[
                df[
                    filter_col
                ]
                .astype(str)
                .isin(
                    filter_vals
                )
            ].reset_index(
                drop=True
            )


    # ======================================================
    # DISPLAY NAME
    # ======================================================

    df[
        "display_name"
    ] = create_display_name(
        df,
        c_name,
        c_unique
    )


    # ======================================================
    # EXTERNAL DATA
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "🎯 2. Input Data Luar"
    )

    ext_mode = st.sidebar.radio(
        "Metode:",
        [
            "Tidak Ada",
            "Tempel Teks",
            "Upload File"
        ],
        horizontal=True,
        key="ext_mode"
    )

    df_ext_final = pd.DataFrame()

    r_name = None
    r_unique = None
    r_lat = None
    r_lon = None

    if ext_mode != "Tidak Ada":

        # ==================================================
        # UPLOAD
        # ==================================================

        if ext_mode == "Upload File":

            ext_src = st.sidebar.file_uploader(
                "Upload Data Luar",
                type=[
                    "csv",
                    "xlsx",
                    "xls"
                ],
                key="external_file"
            )

            if ext_src is not None:

                ext_bytes = (
                    ext_src.getvalue()
                )

                ext_file_name = (
                    ext_src.name
                )

                ext_type = "file"

            else:

                ext_bytes = None

                ext_file_name = ""

                ext_type = "file"

        # ==================================================
        # TEXT
        # ==================================================

        else:

            ext_text = st.sidebar.text_area(
                "Tempel Data Luar",
                key="external_text"
            )

            if ext_text.strip():

                ext_bytes = (
                    ext_text.encode(
                        "utf-8"
                    )
                )

                ext_file_name = ""

                ext_type = "text"

            else:

                ext_bytes = None

                ext_file_name = ""

                ext_type = "text"


        # ==================================================
        # LOAD
        # ==================================================

        df_ext_raw = load_and_clean_data(
            ext_bytes,
            ext_file_name,
            ext_type
        )

        if (
            df_ext_raw is not None
            and not df_ext_raw.empty
        ):

            ext_cols = (
                df_ext_raw.columns.tolist()
            )

            st.sidebar.markdown(
                "### 🔍 Mapping Data Luar"
            )

            r_name = st.sidebar.selectbox(
                "Nama Site (Luar)",
                ext_cols,
                index=smart_detect(
                    ext_cols,
                    [
                        "site",
                        "name"
                    ],
                    [
                        "actual"
                    ],
                    0
                ),
                key="ext_name"
            )

            r_unique = st.sidebar.selectbox(
                "Kode Unik (Luar)",
                ext_cols,
                index=(
                    1
                    if len(ext_cols) > 1
                    else 0
                ),
                key="ext_unique"
            )

            r_lat = st.sidebar.selectbox(
                "Lat (Luar)",
                ext_cols,
                index=smart_detect(
                    ext_cols,
                    [
                        "lat"
                    ],
                    [],
                    1
                ),
                key="ext_lat"
            )

            r_lon = st.sidebar.selectbox(
                "Lon (Luar)",
                ext_cols,
                index=smart_detect(
                    ext_cols,
                    [
                        "lon",
                        "long"
                    ],
                    [],
                    2
                ),
                key="ext_lon"
            )


            # ==================================================
            # FILTER EXTERNAL
            # ==================================================

            st.sidebar.markdown("---")

            st.sidebar.subheader(
                "🎯 2.5. Filter Data Luar"
            )

            filter_col_ext = st.sidebar.selectbox(
                "Pilih Kolom Filter Luar",
                [
                    "-- TIDAK ADA --"
                ]
                +
                ext_cols,
                key="ext_filter_col"
            )

            if (
                filter_col_ext
                != "-- TIDAK ADA --"
            ):

                unique_vals_ext = (
                    df_ext_raw[
                        filter_col_ext
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                filter_vals_ext = (
                    st.sidebar.multiselect(
                        f"Pilih Value "
                        f"'{filter_col_ext}'",
                        unique_vals_ext,
                        key="ext_filter_values"
                    )
                )

                if filter_vals_ext:

                    df_ext_raw = (
                        df_ext_raw[
                            df_ext_raw[
                                filter_col_ext
                            ]
                            .astype(str)
                            .isin(
                                filter_vals_ext
                            )
                        ]
                        .reset_index(
                            drop=True
                        )
                    )


            # ==================================================
            # PREPARE EXTERNAL
            # ==================================================

            df_ext_final = (
                df_ext_raw.copy()
            )

            df_ext_final[
                "lat_val"
            ] = safe_to_float(
                df_ext_final[r_lat]
            )

            df_ext_final[
                "lon_val"
            ] = safe_to_float(
                df_ext_final[r_lon]
            )

            df_ext_final = (
                df_ext_final[
                    df_ext_final[
                        "lat_val"
                    ].notna()
                    &
                    df_ext_final[
                        "lon_val"
                    ].notna()
                    &
                    df_ext_final[
                        "lat_val"
                    ].between(
                        -90,
                        90
                    )
                    &
                    df_ext_final[
                        "lon_val"
                    ].between(
                        -180,
                        180
                    )
                ]
                .copy()
            )

            df_ext_final[
                "display_name_ext"
            ] = create_display_name(
                df_ext_final,
                r_name,
                r_unique,
                " (Luar)"
            )


    # ======================================================
    # SELECT REFERENCE POINT
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "📍 3. Pilih Titik Acuan"
    )


    # ======================================================
    # MANUAL
    # ======================================================

    use_manual = st.sidebar.checkbox(
        "Gunakan Input Manual (Lat, Lon)",
        key="use_manual"
    )

    manual_lat = 0.0

    manual_lon = 0.0

    if use_manual:

        manual_lat = st.sidebar.number_input(
            "Latitude Acuan",
            format="%.6f",
            value=0.0,
            key="manual_lat"
        )

        manual_lon = st.sidebar.number_input(
            "Longitude Acuan",
            format="%.6f",
            value=0.0,
            key="manual_lon"
        )


    # ======================================================
    # INTERNAL
    # ======================================================

    options_int = (
        df[
            "display_name"
        ]
        .astype(str)
        .unique()
        .tolist()
    )

    pick_int = st.sidebar.multiselect(
        "Data Utama",
        options_int,
        default=(
            options_int
            if len(options_int) <= 100
            else []
        ),
        key="selected_internal"
    )

    selected_internal = pick_int


    # ======================================================
    # EXTERNAL
    # ======================================================

    selected_external = []

    if not df_ext_final.empty:

        options_ext = (
            df_ext_final[
                "display_name_ext"
            ]
            .astype(str)
            .unique()
            .tolist()
        )

        pick_ext = st.sidebar.multiselect(
            "Data Luar",
            options_ext,
            default=(
                options_ext
                if len(options_ext) <= 100
                else []
            ),
            key="selected_external"
        )

        selected_external = pick_ext


    # ======================================================
    # FINAL TARGETS
    # ======================================================

    final_targets = []


    # ======================================================
    # MANUAL TARGET
    # ======================================================

    if (
        use_manual
        and manual_lat != 0
        and manual_lon != 0
    ):

        final_targets.append(
            {
                "label":
                    "Manual Point Acuan",
                "lat":
                    float(manual_lat),
                "lon":
                    float(manual_lon),
                "is_manual":
                    True
            }
        )


    # ======================================================
    # INTERNAL TARGET
    # ======================================================

    for selected in selected_internal:

        match = df[
            df[
                "display_name"
            ]
            == selected
        ]

        if not match.empty:

            row = match.iloc[0]

            final_targets.append(
                {
                    "label":
                        selected,
                    "lat":
                        float(
                            row["lat_val"]
                        ),
                    "lon":
                        float(
                            row["lon_val"]
                        ),
                    "is_manual":
                        False,
                    "is_external":
                        False,
                    "row_data":
                        row
                }
            )


    # ======================================================
    # EXTERNAL TARGET
    # ======================================================

    for selected in selected_external:

        match = df_ext_final[
            df_ext_final[
                "display_name_ext"
            ]
            == selected
        ]

        if not match.empty:

            row = match.iloc[0]

            final_targets.append(
                {
                    "label":
                        selected,
                    "lat":
                        float(
                            row["lat_val"]
                        ),
                    "lon":
                        float(
                            row["lon_val"]
                        ),
                    "is_manual":
                        False,
                    "is_external":
                        True,
                    "row_data":
                        row,
                    "r_name_col":
                        r_name,
                    "r_unique_col":
                        r_unique
                }
            )


    # ======================================================
    # SETTINGS
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "🎬 4. Settings"
    )


    # ======================================================
    # ANALYSIS MODE
    # ======================================================

    analysis_mode = st.sidebar.radio(
        "Mode Analisis",
        [
            "Radius + Nearest",
            "Radius Only",
            "Nearest Only"
        ],
        index=0,
        key="analysis_mode"
    )

    # ------------------------------------------------------
    # INFO MODE
    # ------------------------------------------------------

    if analysis_mode == "Radius + Nearest":

        st.sidebar.markdown(
            """
            <div class="mode-box">
            <b>Radius + Nearest</b><br>
            Tower dalam radius + N tower terdekat.
            </div>
            """,
            unsafe_allow_html=True
        )

    elif analysis_mode == "Radius Only":

        st.sidebar.markdown(
            """
            <div class="mode-box">
            <b>Radius Only</b><br>
            Hanya tower yang berada dalam radius.
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.sidebar.markdown(
            """
            <div class="mode-box">
            <b>Nearest Only</b><br>
            Hanya N tower terdekat.
            </div>
            """,
            unsafe_allow_html=True
        )


    # ======================================================
    # PHOTO
    # ======================================================

    tampilkan_foto = st.sidebar.checkbox(
        "🖼️ Proses & Tampilkan Foto",
        value=True,
        help=(
            "Matikan untuk meningkatkan "
            "performa aplikasi."
        ),
        key="show_photo"
    )

    preload_photos = st.sidebar.checkbox(
        "📥 Preload/Cache Foto",
        value=False,
        key="preload_photo"
    )


    # ======================================================
    # FOCUS
    # ======================================================

    st.sidebar.markdown(
        "### 🎯 Fokus Peta"
    )

    focus_options = [
        "--- Fokus Otomatis ---"
    ]

    selected_focus_targets = []

    for target in final_targets:

        label = str(
            target["label"]
        )

        if (
            label
            not in selected_focus_targets
        ):

            selected_focus_targets.append(
                label
            )

    focus_options.extend(
        selected_focus_targets
    )

    selected_focus = st.sidebar.selectbox(
        "Fokus Peta Ke:",
        focus_options,
        key="focus_map"
    )


    # ======================================================
    # RADIUS
    # ======================================================

    rad_m = st.sidebar.number_input(
        "📏 Radius Filter (Meter)",
        min_value=1,
        max_value=50000,
        value=2000,
        step=100,
        help=(
            "Tower yang berada di dalam radius "
            "dari titik acuan yang dipilih akan "
            "masuk hasil Radius."
        ),
        key="radius_m"
    )


    # ======================================================
    # NEAREST
    # ======================================================

    n_nearest = st.sidebar.number_input(
        "🎯 Tampilkan N Tower Terdekat",
        min_value=0,
        max_value=50,
        value=4,
        step=1,
        key="n_nearest"
    )


    # ======================================================
    # PROCESS BUTTON
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.markdown(
        """
        <div class="process-box">
        <b>⚡ Analisis dikontrol tombol proses</b><br>
        <span class="small-info">
        Perubahan filter, titik acuan, radius,
        nearest, atau mode analisis belum diterapkan
        sampai tombol ditekan.
        </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    process_clicked = st.sidebar.button(
        "🚀 PROSES ANALISIS",
        type="primary",
        use_container_width=True,
        key="process_analysis"
    )


    # ======================================================
    # PROCESS
    # ======================================================

    if process_clicked:

        if not final_targets:

            st.sidebar.error(
                "Pilih minimal 1 titik acuan."
            )

            st.session_state.processed = False

            st.session_state.analysis_result = None

            st.session_state.analysis_config = None

        else:

            with st.spinner(
                "⚡ Menghitung analisis..."
            ):

                result_df = calculate_analysis(
                    df,
                    final_targets,
                    int(rad_m),
                    int(n_nearest),
                    analysis_mode
                )

            st.session_state.analysis_result = (
                result_df
            )

            st.session_state.analysis_config = {
                "targets":
                    final_targets,
                "radius":
                    int(rad_m),
                "n_nearest":
                    int(n_nearest),
                "analysis_mode":
                    analysis_mode,
                "plot_results":
                    analysis_mode != "Nearest Only",
                "tampilkan_foto":
                    bool(tampilkan_foto),
                "preload_photos":
                    bool(preload_photos)
            }

            st.session_state.processed = True

            st.success(
                "Analisis selesai."
            )


    # ======================================================
    # TITLE
    # ======================================================

    st.title(
        "📍 Tower Geo-Analysis Pro"
    )

    if st.session_state.last_review_message:

        st.success(
            st.session_state.last_review_message
        )

        st.session_state.last_review_message = None

    if not st.session_state.processed:

        st.info(
            "👈 Pilih titik acuan dan setting "
            "kemudian klik **🚀 PROSES ANALISIS**."
        )

        st.stop()


    # ======================================================
    # PROCESSED CONFIG
    # ======================================================

    # ------------------------------------------------------
    # BACKWARD-COMPATIBLE CONFIG MIGRATION
    #
    # Streamlit mempertahankan session_state saat source code
    # di-reload. Session lama dapat mempunyai analysis_config
    # dengan schema versi sebelumnya (mis. tanpa analysis_mode).
    # Gunakan fallback ke nilai UI aktif supaya tidak KeyError.
    # ------------------------------------------------------

    config = st.session_state.get(
        "analysis_config"
    )

    if not isinstance(config, dict):
        config = {}

    result_df = (
        st.session_state.analysis_result
    )

    processed_targets = config.get(
        "targets",
        final_targets
    )

    processed_radius = int(
        config.get(
            "radius",
            rad_m
        )
    )

    processed_nearest = int(
        config.get(
            "n_nearest",
            n_nearest
        )
    )

    processed_mode = config.get(
        "analysis_mode",
        analysis_mode
    )

    processed_plot = bool(
        config.get(
            "plot_results",
            processed_mode != "Nearest Only"
        )
    )

    processed_show_photo = bool(
        config.get(
            "tampilkan_foto",
            tampilkan_foto
        )
    )

    processed_preload_photo = bool(
        config.get(
            "preload_photos",
            preload_photos
        )
    )

    # Simpan kembali schema yang sudah dinormalisasi agar
    # rerun berikutnya langsung memakai struktur terbaru.
    st.session_state.analysis_config = {
        **config,
        "targets": processed_targets,
        "radius": processed_radius,
        "n_nearest": processed_nearest,
        "analysis_mode": processed_mode,
        "plot_results": processed_plot,
        "tampilkan_foto": processed_show_photo,
        "preload_photos": processed_preload_photo
    }


    # ======================================================
    # FILTER PLOT MAP (DISPLAY ONLY)
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "🗺️ 5. Filter Plot Map"
    )

    map_radius_filter_enabled = (
        st.sidebar.checkbox(
            "📏 Batasi marker map berdasarkan radius",
            value=False,
            help=(
                "Hanya memfilter marker yang terlihat pada map. "
                "Hasil analisis dan tabel utama tidak dihapus."
            ),
            key="map_radius_filter_enabled"
        )
    )

    map_plot_radius = st.sidebar.number_input(
        "Radius Plot Map (Meter)",
        min_value=1,
        max_value=50000,
        value=int(processed_radius),
        step=100,
        disabled=not map_radius_filter_enabled,
        key="map_plot_radius"
    )

    map_filter_all_label = (
        "-- SEMUA TITIK ACUAN (UNION) --"
    )

    map_filter_target_options = [
        map_filter_all_label
    ] + [
        str(t["label"])
        for t in processed_targets
    ]

    map_filter_target_label = (
        st.sidebar.selectbox(
            "Acuan Radius Plot",
            map_filter_target_options,
            disabled=not map_radius_filter_enabled,
            key="map_filter_target"
        )
    )

    if (
        map_radius_filter_enabled
        and map_filter_target_label
        != map_filter_all_label
    ):

        map_filter_targets = [
            t
            for t in processed_targets
            if str(t["label"])
            == map_filter_target_label
        ]

    else:

        map_filter_targets = (
            processed_targets
            if map_radius_filter_enabled
            else []
        )

    map_result_df = (
        result_df.copy()
        if result_df is not None
        else pd.DataFrame()
    )

    if (
        map_radius_filter_enabled
        and not map_result_df.empty
    ):

        map_result_df = (
            filter_dataframe_by_target_radius(
                map_result_df,
                map_filter_targets,
                map_plot_radius
            )
        )


    # ======================================================
    # PRELOAD PHOTO
    # ======================================================

    photo_col_name = next(
        (
            col
            for col in df.columns
            if "last photo"
            in str(col).lower()
        ),
        None
    )

    if (
        processed_show_photo
        and processed_preload_photo
        and photo_col_name
    ):

        photo_values = (
            df[
                photo_col_name
            ]
            .dropna()
            .astype(str)
            .unique()
        )

        with st.spinner(
            "📥 Preload foto..."
        ):

            for val in photo_values:

                direct_url, _ = (
                    format_image_link(
                        val
                    )
                )

                if direct_url:

                    cached_download_image(
                        direct_url
                    )


    # ======================================================
    # SUMMARY
    # ======================================================

    col1, col2, col3, col4 = st.columns(
        4
    )

    # ------------------------------------------------------
    # TARGET
    # ------------------------------------------------------

    with col1:

        st.metric(
            "Titik Acuan",
            len(
                processed_targets
            )
        )

    # ------------------------------------------------------
    # RESULT
    # ------------------------------------------------------

    with col2:

        st.metric(
            "Tower Hasil",
            (
                0
                if result_df is None
                else len(result_df)
            )
        )

    # ------------------------------------------------------
    # RADIUS
    # ------------------------------------------------------

    with col3:

        if processed_mode == "Nearest Only":

            st.metric(
                "Radius",
                "OFF"
            )

        else:

            st.metric(
                "Radius",
                f"{processed_radius:,} m"
            )

    # ------------------------------------------------------
    # MODE
    # ------------------------------------------------------

    with col4:

        st.metric(
            "Mode",
            processed_mode
        )


    if (
        result_df is not None
        and not result_df.empty
        and map_radius_filter_enabled
    ):

        st.caption(
            f"🗺️ Filter tampilan map aktif: "
            f"**{len(map_result_df):,} dari {len(result_df):,} tower** "
            f"ditampilkan dalam radius "
            f"**{int(map_plot_radius):,} m**."
        )


    # ======================================================
    # LAYOUT
    # ======================================================

    if processed_show_photo:

        col_map, col_photo = st.columns(
            [7, 3]
        )

    else:

        col_map = st.container()

        col_photo = None


    # ======================================================
    # MAP
    # ==========================================================

    with col_map:

        # ==================================================
        # FOCUS LOCATION
        # ==================================================

        focus_target = None

        if (
            selected_focus
            != "--- Fokus Otomatis ---"
        ):

            focus_target = next(
                (
                    t
                    for t in processed_targets
                    if str(
                        t["label"]
                    )
                    == selected_focus
                ),
                None
            )

        if focus_target:

            m_center = [
                focus_target["lat"],
                focus_target["lon"]
            ]

            m_zoom = 15

        elif processed_targets:

            lats = [
                t["lat"]
                for t in processed_targets
            ]

            lons = [
                t["lon"]
                for t in processed_targets
            ]

            m_center = [
                float(
                    np.mean(lats)
                ),
                float(
                    np.mean(lons)
                )
            ]

            m_zoom = 10

        elif not df.empty:

            m_center = [
                float(
                    df[
                        "lat_val"
                    ].iloc[0]
                ),
                float(
                    df[
                        "lon_val"
                    ].iloc[0]
                )
            ]

            m_zoom = 12

        else:

            m_center = [
                0,
                0
            ]

            m_zoom = 2


        # ==================================================
        # CREATE MAP
        # ==================================================

        m = folium.Map(
            location=m_center,
            zoom_start=m_zoom,
            control_scale=True,
            prefer_canvas=True
        )

        # Nama variable JavaScript Folium map untuk komunikasi popup -> Draw event.
        map_js_name = m.get_name()

        # ==================================================
        # RESPONSIVE / ZOOM-AWARE POPUP UI
        # ==================================================
        # Popup adalah overlay UI Leaflet, sehingga secara default ukurannya
        # tidak ikut berubah ketika map di-zoom. CSS + listener di bawah membuat
        # popup lebih compact, scrollable, dan lebarnya menyesuaikan level zoom.

        popup_ui_css = """
        <style>
        :root {
            --tower-popup-width: 430px;
        }

        .leaflet-popup-content-wrapper {
            border-radius: 10px !important;
            overflow: hidden;
        }

        .leaflet-popup-content {
            margin: 8px 10px !important;
            width: auto !important;
            max-width: calc(100vw - 90px) !important;
        }

        .tower-popup-shell {
            font-family: Arial, sans-serif;
            width: min(var(--tower-popup-width, 430px), calc(100vw - 110px));
            max-width: 100%;
            max-height: min(68vh, 610px);
            overflow-y: auto;
            overflow-x: hidden;
            box-sizing: border-box;
            padding-right: 2px;
            scrollbar-width: thin;
        }

        .tower-popup-header {
            color: white;
            padding: 8px 9px;
            margin-bottom: 7px;
            border-radius: 6px;
            position: sticky;
            top: 0;
            z-index: 3;
        }

        .tower-popup-title {
            font-size: 13px;
            font-weight: 700;
            line-height: 1.35;
        }

        .tower-popup-relation {
            font-size: 11px;
            margin-top: 3px;
            line-height: 1.3;
        }

        .tower-popup-distance {
            font-size: 11px;
            color: #f1c40f;
            margin-top: 3px;
        }

        .tower-popup-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
            gap: 0;
            border-top: 1px solid #edf0f2;
            border-left: 1px solid #edf0f2;
        }

        .tower-popup-item {
            min-width: 0;
            padding: 4px 5px;
            box-sizing: border-box;
            border-right: 1px solid #edf0f2;
            border-bottom: 1px solid #edf0f2;
        }

        .tower-popup-key {
            color: #7f8c8d;
            font-weight: 700;
            font-size: 8px;
            line-height: 1.2;
            text-transform: uppercase;
        }

        .tower-popup-value {
            color: #2c3e50;
            font-size: 10px;
            line-height: 1.25;
            overflow-wrap: anywhere;
            margin-top: 2px;
        }

        .tower-popup-more,
        .tower-overlap-box {
            margin-top: 6px;
            padding: 5px 7px;
            border: 1px solid #e5e8eb;
            border-radius: 6px;
            background: #fafbfc;
        }

        .tower-popup-more > summary,
        .tower-overlap-box > summary {
            cursor: pointer;
            font-size: 10px;
            font-weight: 700;
            color: #34495e;
            user-select: none;
        }

        .tower-popup-more .tower-popup-grid {
            margin-top: 6px;
        }

        .tower-overlap-row {
            font-size: 9px;
            line-height: 1.4;
            padding: 4px 0;
            border-bottom: 1px solid #e5e8eb;
            color: #555;
        }

        .tower-popup-actions {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 7px;
        }

        .tower-gmaps-button {
            display: inline-block;
            background: #ffffff;
            color: #1a73e8 !important;
            border: 1px solid #d5d8dc;
            padding: 6px 10px;
            border-radius: 5px;
            font-size: 10px;
            line-height: 1;
            font-weight: 700;
            text-decoration: none !important;
            cursor: pointer;
            white-space: nowrap;
        }

        .tower-gmaps-button:hover {
            background: #f1f6ff;
            border-color: #1a73e8;
        }

        .tower-gmaps-coord {
            font-size: 9px;
            color: #7f8c8d;
            line-height: 1.2;
        }

        .tower-review-box textarea {
            resize: vertical;
            max-height: 100px;
        }

        @media (max-width: 720px) {
            .leaflet-popup-content {
                max-width: calc(100vw - 55px) !important;
            }

            .tower-popup-shell {
                width: calc(100vw - 75px);
                max-height: 62vh;
            }

            .tower-popup-grid {
                grid-template-columns: repeat(auto-fit, minmax(105px, 1fr));
            }
        }
        </style>
        """

        m.get_root().html.add_child(
            folium.Element(
                popup_ui_css
            )
        )

        popup_zoom_js = f"""
        <script>
        window.addEventListener('load', function() {{
            try {{
                const mapObj = {map_js_name};

                function resizeTowerPopup() {{
                    const z = mapObj.getZoom();
                    let popupWidth = 430;

                    if (z <= 9) {{
                        popupWidth = 330;
                    }} else if (z <= 11) {{
                        popupWidth = 365;
                    }} else if (z <= 13) {{
                        popupWidth = 400;
                    }} else if (z <= 15) {{
                        popupWidth = 440;
                    }} else {{
                        popupWidth = 480;
                    }}

                    document.documentElement.style.setProperty(
                        '--tower-popup-width',
                        popupWidth + 'px'
                    );

                    if (mapObj._popup) {{
                        setTimeout(function() {{
                            try {{ mapObj._popup.update(); }} catch (e) {{}}
                        }}, 0);
                    }}
                }}

                mapObj.on('zoomend', resizeTowerPopup);
                mapObj.on('popupopen', resizeTowerPopup);
                resizeTowerPopup();
            }} catch (e) {{
                console.log('Popup responsive fallback:', e);
            }}
        }});
        </script>
        """

        m.get_root().html.add_child(
            folium.Element(
                popup_zoom_js
            )
        )


        # ==================================================
        # FULLSCREEN
        # ==================================================

        Fullscreen(
            position="topright",
            title="Full Screen",
            title_cancel="Exit Full Screen"
        ).add_to(m)


        # ==================================================
        # MEASURE
        # ==================================================

        MeasureControl(
            position="topleft"
        ).add_to(m)


        # ==================================================
        # DRAW
        # ==================================================

        draw_plugin = Draw(
            export=True,
            draw_options={
                "polyline": True,
                "rectangle": True,
                "polygon": True,
                "circle": True,
                "marker": True,
                "circlemarker": False
            }
        )

        m.add_child(
            draw_plugin
        )


        # ==================================================
        # REFERENCE POINTS
        # ==================================================

        for target in processed_targets:

            acuan_pt = (
                target["lat"],
                target["lon"]
            )

            target_label = str(
                target["label"]
            )

            # ------------------------------------------------
            # TARGET POPUP
            # ------------------------------------------------

            popup_html = (
                "<div "
                "style='font-family:sans-serif;'>"
                "<b>📍 TITIK ACUAN</b><br>"
                f"{esc(target_label)}"
                "<br><br>"
                f"Lat: {target['lat']:.6f}<br>"
                f"Lon: {target['lon']:.6f}"
                "</div>"
            )

            # ------------------------------------------------
            # MARKER
            # ------------------------------------------------

            folium.Marker(
                acuan_pt,
                icon=folium.Icon(
                    color="orange",
                    icon="star"
                ),
                popup=folium.Popup(
                    popup_html,
                    max_width=400
                ),
                tooltip=(
                    "ACUAN: "
                    +
                    target_label
                )
            ).add_to(m)

            # ------------------------------------------------
            # RADIUS CIRCLE
            # ------------------------------------------------

            if processed_plot:

                folium.Circle(
                    acuan_pt,
                    radius=processed_radius,
                    color="blue",
                    fill=True,
                    fill_opacity=0.05,
                    weight=1,
                    tooltip=(
                        f"Radius "
                        f"{processed_radius:,} m"
                    )
                ).add_to(m)

            # ------------------------------------------------
            # MAP DISPLAY FILTER CIRCLE
            # ------------------------------------------------

            if (
                map_radius_filter_enabled
                and (
                    map_filter_target_label
                    == map_filter_all_label
                    or target_label
                    == map_filter_target_label
                )
            ):

                folium.Circle(
                    acuan_pt,
                    radius=map_plot_radius,
                    color="purple",
                    fill=False,
                    weight=2,
                    dash_array="6,6",
                    tooltip=(
                        f"Filter Plot Map "
                        f"{int(map_plot_radius):,} m"
                    )
                ).add_to(m)


        # ==================================================
        # RESULT TOWERS
        # ==================================================

        if (
            map_result_df is not None
            and not map_result_df.empty
        ):

            # ==================================================
            # BUILD RELATION MAP
            # ==================================================

            relation_map = {}

            for idx, row in map_result_df.iterrows():

                coord_key = (
                    round(
                        float(
                            row["lat_val"]
                        ),
                        7
                    ),
                    round(
                        float(
                            row["lon_val"]
                        ),
                        7
                    )
                )

                relations = (
                    row.get(
                        "_target_relations",
                        []
                    )
                )

                # ----------------------------------------------
                # Jika relation tersedia
                # ----------------------------------------------

                if relations:

                    relation_map[
                        coord_key
                    ] = relations

                # ----------------------------------------------
                # Fallback
                # ----------------------------------------------

                else:

                    source_text = str(
                        row.get(
                            "Sumber Analisa",
                            ""
                        )
                    )

                    target_label = (
                        source_text
                        .replace(
                            "Titik Acuan (",
                            ""
                        )
                        .rstrip(")")
                    )

                    if target_label:

                        relation_map[
                            coord_key
                        ] = [
                            {
                                "target":
                                    target_label,
                                "distance":
                                    float(
                                        row.get(
                                            "Jarak (m)",
                                            0
                                        )
                                    )
                            }
                        ]


            # ==================================================
            # NEAREST COORDINATE SET
            # ==================================================

            nearest_coord_set = set()

            if processed_nearest > 0:

                for target in processed_targets:

                    distances = (
                        haversine_vectorized(
                            target["lat"],
                            target["lon"],
                            map_result_df[
                                "lat_val"
                            ].to_numpy(),
                            map_result_df[
                                "lon_val"
                            ].to_numpy()
                        )
                    )

                    valid_idx = np.where(
                        distances > 1.0
                    )[0]

                    if len(valid_idx) > 0:

                        sorted_idx = (
                            valid_idx[
                                np.argsort(
                                    distances[
                                        valid_idx
                                    ]
                                )
                            ][
                                :processed_nearest
                            ]
                        )

                        for idx in sorted_idx:

                            coord_key = (
                                round(
                                    float(
                                        map_result_df.iloc[
                                            idx
                                        ][
                                            "lat_val"
                                        ]
                                    ),
                                    7
                                ),
                                round(
                                    float(
                                        map_result_df.iloc[
                                            idx
                                        ][
                                            "lon_val"
                                        ]
                                    ),
                                    7
                                )
                            )

                            nearest_coord_set.add(
                                coord_key
                            )


            # ==================================================
            # PLOT RESULT
            # ==================================================

            for idx, row in map_result_df.iterrows():

                tower_lat = float(
                    row["lat_val"]
                )

                tower_lon = float(
                    row["lon_val"]
                )

                coord_key = (
                    round(
                        tower_lat,
                        7
                    ),
                    round(
                        tower_lon,
                        7
                    )
                )

                is_nearest = (
                    coord_key
                    in nearest_coord_set
                )

                relations = (
                    relation_map.get(
                        coord_key,
                        []
                    )
                )

                # ------------------------------------------------
                # SORT RELATIONS
                # ------------------------------------------------

                relations_sorted = sorted(
                    relations,
                    key=lambda x:
                    float(
                        x["distance"]
                    )
                )

                # ------------------------------------------------
                # PRIMARY RELATION
                # ------------------------------------------------

                if relations_sorted:

                    primary = (
                        relations_sorted[0]
                    )

                    primary_target = (
                        primary["target"]
                    )

                    primary_distance = float(
                        primary["distance"]
                    )

                    other_relations = (
                        relations_sorted[1:]
                    )

                else:

                    source_text = str(
                        row.get(
                            "Sumber Analisa",
                            ""
                        )
                    )

                    primary_target = (
                        source_text
                        .replace(
                            "Titik Acuan (",
                            ""
                        )
                        .rstrip(")")
                    )

                    primary_distance = float(
                        row.get(
                            "Jarak (m)",
                            0
                        )
                    )

                    other_relations = []


                # ==================================================
                # POPUP
                # ==================================================

                popup_html = (
                    build_relation_popup(
                        row,
                        c_name,
                        c_unique,
                        primary_target,
                        primary_distance,
                        other_relations,
                        is_nearest=is_nearest,
                        review_key=get_review(
                            row,
                            c_unique
                        )[0],
                        current_status=get_review(
                            row,
                            c_unique
                        )[1],
                        current_remark=get_review(
                            row,
                            c_unique
                        )[2],
                        map_js_name=map_js_name,
                        tower_lat=tower_lat,
                        tower_lon=tower_lon
                    )
                )

                popup_obj = folium.Popup(
                    popup_html,
                    max_width=540
                )

                # ------------------------------------------------
                # HOVER
                # ------------------------------------------------

                hover_text = str(
                    row[c_name]
                )

                # ==================================================
                # MARKER COLOR
                # ==================================================

                if is_nearest:

                    marker_color = "red"

                    fill_color = "red"

                    marker_radius = 7

                    marker_weight = 2

                else:

                    marker_color = "lime"

                    fill_color = "lime"

                    marker_radius = 6

                    marker_weight = 1


                # ==================================================
                # MARKER
                # ==================================================

                folium.CircleMarker(
                    location=(
                        tower_lat,
                        tower_lon
                    ),
                    radius=marker_radius,
                    color=marker_color,
                    fill=True,
                    fill_color=fill_color,
                    fill_opacity=0.85,
                    weight=marker_weight,
                    popup=popup_obj,
                    tooltip=hover_text
                ).add_to(m)


                # ==================================================
                # LINE TO PRIMARY TARGET
                # ==================================================

                primary_target_obj = next(
                    (
                        t
                        for t in processed_targets
                        if str(
                            t["label"]
                        )
                        ==
                        str(
                            primary_target
                        )
                    ),
                    None
                )

                if (
                    is_nearest
                    and primary_target_obj
                ):

                    folium.PolyLine(
                        [
                            (
                                primary_target_obj[
                                    "lat"
                                ],
                                primary_target_obj[
                                    "lon"
                                ]
                            ),
                            (
                                tower_lat,
                                tower_lon
                            )
                        ],
                        color="red",
                        weight=1.5,
                        dash_array="5,5",
                        opacity=0.6
                    ).add_to(m)


        # ==================================================
        # SHOW DATABASE TOWERS OVERLAY
        # ==================================================

        show_all_towers = st.sidebar.checkbox(
            "🌐 Tampilkan Tower Database (Overlay)",
            value=False,
            key="show_all_towers"
        )

        if (
            show_all_towers
            and not df.empty
        ):

            df_overlay = df.copy()

            if map_radius_filter_enabled:

                df_overlay = (
                    filter_dataframe_by_target_radius(
                        df_overlay,
                        map_filter_targets,
                        map_plot_radius
                    )
                )

            st.sidebar.caption(
                f"Overlay map: {len(df_overlay):,} tower"
            )

            for _, row in df_overlay.iterrows():

                review_key, review_status, review_remark = (
                    get_review(
                        row,
                        c_unique
                    )
                )

                popup_html = build_popup(
                    row,
                    c_name,
                    c_unique,
                    title_prefix="[DATABASE] ",
                    review_key=review_key,
                    current_status=review_status,
                    current_remark=review_remark,
                    map_js_name=map_js_name,
                    tower_lat=float(row["lat_val"]),
                    tower_lon=float(row["lon_val"])
                )

                folium.CircleMarker(
                    location=(
                        float(
                            row["lat_val"]
                        ),
                        float(
                            row["lon_val"]
                        )
                    ),
                    radius=3,
                    color="blue",
                    fill=True,
                    fill_color="blue",
                    fill_opacity=0.45,
                    weight=1,
                    popup=folium.Popup(
                        popup_html,
                        max_width=540
                    ),
                    tooltip=str(
                        row[c_name]
                    )
                ).add_to(m)


        # ==================================================
        # DRAWING ANALYSIS
        # ==================================================

        map_state = (
            st.session_state.get(
                "main_map",
                {}
            )
        )

        drawings = (
            map_state.get(
                "all_drawings",
                []
            )
        )

        drawing_results = []

        if drawings:

            drawn_areas = []

            drawn_markers = []

            # ==================================================
            # PARSE DRAWINGS
            # ==================================================

            for d in drawings:

                try:

                    props = d.get(
                        "properties",
                        {}
                    )

                    # ==============================================
                    # POPUP REVIEW ACTION
                    # ==============================================

                    if props.get(
                        "_review_action"
                    ):

                        action_id = str(
                            props.get(
                                "review_action_id",
                                ""
                            )
                        )

                        review_key = str(
                            props.get(
                                "review_key",
                                ""
                            )
                        )

                        review_status = str(
                            props.get(
                                "review_status",
                                ""
                            )
                        ).upper()

                        review_remark = str(
                            props.get(
                                "review_remark",
                                ""
                            )
                        ).strip()

                        if (
                            review_key
                            and review_status in {
                                "CONTINUE",
                                "HOLD",
                                "DROP"
                            }
                            and action_id
                            not in st.session_state.processed_review_actions
                        ):

                            st.session_state.tower_reviews[
                                review_key
                            ] = {
                                "status": review_status,
                                "remark": review_remark
                            }

                            st.session_state.processed_review_actions.add(
                                action_id
                            )

                            st.session_state.last_review_message = (
                                f"Status tower disimpan: {review_status}"
                            )

                            # Rerun agar warna/status popup dan resume tabel
                            # langsung membaca review terbaru.
                            st.rerun()

                        # Action review bukan drawing analisa spasial.
                        continue

                    geom_type = (
                        d[
                            "geometry"
                        ][
                            "type"
                        ]
                    )

                    # ------------------------------------------
                    # POLYGON
                    # ------------------------------------------

                    if geom_type == "Polygon":

                        drawn_areas.append(
                            {
                                "type":
                                    "POLYGON",
                                "shape":
                                    shape(
                                        d[
                                            "geometry"
                                        ]
                                    )
                            }
                        )

                    # ------------------------------------------
                    # LINE
                    # ------------------------------------------

                    elif geom_type == "LineString":

                        drawn_areas.append(
                            {
                                "type":
                                    "POLYLINE",
                                "shape":
                                    shape(
                                        d[
                                            "geometry"
                                        ]
                                    ).buffer(
                                        100 / 111000
                                    )
                            }
                        )

                    # ------------------------------------------
                    # POINT / CIRCLE
                    # ------------------------------------------

                    elif geom_type == "Point":

                        coords = (
                            d[
                                "geometry"
                            ][
                                "coordinates"
                            ]
                        )

                        rad = props.get(
                            "radius",
                            props.get(
                                "style",
                                {}
                            ).get(
                                "radius",
                                0
                            )
                        )

                        if rad > 0:

                            drawn_areas.append(
                                {
                                    "type":
                                        "CIRCLE",
                                    "center":
                                        coords,
                                    "radius":
                                        rad
                                }
                            )

                        else:

                            drawn_markers.append(
                                coords
                            )

                except Exception:

                    continue


            # ==================================================
            # CHECK DRAWING
            # ==================================================

            for area in drawn_areas:

                valid_marker = None

                # ----------------------------------------------
                # CHECK MARKER
                # ----------------------------------------------

                for mk in drawn_markers:

                    try:

                        if area["type"] in [
                            "POLYGON",
                            "POLYLINE"
                        ]:

                            is_inside = (
                                area["shape"]
                                .contains(
                                    Point(
                                        mk[0],
                                        mk[1]
                                    )
                                )
                            )

                        else:

                            is_inside = (
                                geodesic(
                                    (
                                        area[
                                            "center"
                                        ][1],
                                        area[
                                            "center"
                                        ][0]
                                    ),
                                    (
                                        mk[1],
                                        mk[0]
                                    )
                                ).meters
                                <=
                                area[
                                    "radius"
                                ]
                            )

                        if is_inside:

                            valid_marker = (
                                mk[1],
                                mk[0]
                            )

                            break

                    except Exception:

                        continue


                # ----------------------------------------------
                # CHECK TOWERS
                # ----------------------------------------------

                for _, row in df.iterrows():

                    tower_lat = float(
                        row[
                            "lat_val"
                        ]
                    )

                    tower_lon = float(
                        row[
                            "lon_val"
                        ]
                    )

                    try:

                        if area["type"] in [
                            "POLYGON",
                            "POLYLINE"
                        ]:

                            tower_inside = (
                                area[
                                    "shape"
                                ]
                                .contains(
                                    Point(
                                        tower_lon,
                                        tower_lat
                                    )
                                )
                            )

                        else:

                            tower_inside = (
                                geodesic(
                                    (
                                        area[
                                            "center"
                                        ][1],
                                        area[
                                            "center"
                                        ][0]
                                    ),
                                    (
                                        tower_lat,
                                        tower_lon
                                    )
                                ).meters
                                <=
                                area[
                                    "radius"
                                ]
                            )

                    except Exception:

                        continue

                    if tower_inside:

                        row_dict = (
                            row.to_dict()
                        )

                        row_dict[
                            "Sumber Analisa"
                        ] = (
                            "Gambar Manual"
                        )

                        row_dict[
                            "Objek Filter"
                        ] = area[
                            "type"
                        ]

                        if valid_marker:

                            row_dict[
                                "Jarak (m)"
                            ] = exact_distance(
                                valid_marker[0],
                                valid_marker[1],
                                tower_lat,
                                tower_lon
                            )

                        else:

                            row_dict[
                                "Jarak (m)"
                            ] = None

                        drawing_results.append(
                            row_dict
                        )


        # ==================================================
        # PLOT DRAWING RESULT
        # ==================================================

        if drawing_results:

            df_draw = pd.DataFrame(
                drawing_results
            )

            for _, row in df_draw.iterrows():

                review_key, review_status, review_remark = (
                    get_review(
                        row,
                        c_unique
                    )
                )

                popup_html = build_popup(
                    row,
                    c_name,
                    c_unique,
                    row.get(
                        "Jarak (m)"
                    ),
                    "[GAMBAR] ",
                    review_key=review_key,
                    current_status=review_status,
                    current_remark=review_remark,
                    map_js_name=map_js_name,
                    tower_lat=float(row["lat_val"]),
                    tower_lon=float(row["lon_val"])
                )

                folium.CircleMarker(
                    location=(
                        row["lat_val"],
                        row["lon_val"]
                    ),
                    radius=7,
                    color="darkred",
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.9,
                    weight=2,
                    popup=folium.Popup(
                        popup_html,
                        max_width=540
                    ),
                    tooltip=(
                        "[GAMBAR] "
                        +
                        str(
                            row[c_name]
                        )
                    )
                ).add_to(m)


        # ==================================================
        # MAP RETURN
        # ==================================================

        ret_objects = [
            "all_drawings",
            "last_object_clicked"
        ]

        output = st_folium(
            m,
            use_container_width=True,
            height=750,
            returned_objects=ret_objects,
            key="main_map"
        )


    # ======================================================
    # PHOTO PANEL
    # ======================================================

    if col_photo is not None:

        with col_photo:

            st.markdown(
                "### 🖼️ Data URL / Foto"
            )

            photo_col_exists = any(
                "last photo"
                in str(col).lower()
                for col in df.columns
            )

            if not photo_col_exists:

                st.warning(
                    "⚠️ Kolom 'last photo' "
                    "tidak ditemukan."
                )


            clicked_data = (
                output.get(
                    "last_object_clicked"
                )
                if output
                else None
            )

            valid_click = False

            row_data = None

            raw_url = None


            # ==================================================
            # CLICK RESULT
            # ==================================================

            if (
                clicked_data
                and result_df is not None
                and not result_df.empty
            ):

                clicked_lat = (
                    clicked_data.get(
                        "lat"
                    )
                )

                clicked_lon = (
                    clicked_data.get(
                        "lng"
                    )
                )

                if (
                    clicked_lat is not None
                    and clicked_lon is not None
                ):

                    raw_url, row_data = (
                        find_photo_url(
                            df,
                            clicked_lat,
                            clicked_lon,
                            "lat_val",
                            "lon_val"
                        )
                    )

                    if row_data is not None:

                        valid_click = True


            # ==================================================
            # SHOW PHOTO
            # ==================================================

            if (
                valid_click
                and row_data is not None
            ):

                st.success(
                    f"**Site:** "
                    f"{row_data[c_unique]}"
                )

                direct_url, original_url = (
                    format_image_link(
                        raw_url
                    )
                )

                if original_url:

                    if direct_url:

                        img_bytes = (
                            cached_download_image(
                                direct_url
                            )
                        )

                        if img_bytes:

                            b64_img = (
                                base64
                                .b64encode(
                                    img_bytes
                                )
                                .decode(
                                    "utf-8"
                                )
                            )

                            img_src = (
                                "data:image/jpeg;"
                                "base64,"
                                +
                                b64_img
                            )

                            html_code = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>

                            <style>

                            body {{
                                margin:0;
                                padding:0;
                                overflow:hidden;
                                background:#0e1117;
                                font-family:sans-serif;
                            }}

                            #container {{
                                width:100vw;
                                height:100vh;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                overflow:hidden;
                                cursor:grab;
                                position:relative;
                            }}

                            #container:active {{
                                cursor:grabbing;
                            }}

                            img {{
                                max-width:100%;
                                max-height:100%;
                                object-fit:contain;
                                transform-origin:center;
                                transition:
                                    transform 0.1s ease-out;
                                pointer-events:none;
                            }}

                            .hint {{
                                position:absolute;
                                bottom:10px;
                                left:10px;
                                color:
                                    rgba(255,255,255,0.7);
                                font-size:11px;
                                background:
                                    rgba(0,0,0,0.5);
                                padding:4px 8px;
                                border-radius:4px;
                            }}

                            </style>

                            </head>

                            <body>

                            <div id="container">

                                <img
                                    id="image"
                                    src="{img_src}"
                                    draggable="false"
                                >

                                <div class="hint">
                                    🖱️ Scroll: Zoom |
                                    Drag: Geser
                                </div>

                            </div>

                            <script>

                            const el =
                                document.getElementById(
                                    "image"
                                );

                            const container =
                                document.getElementById(
                                    "container"
                                );

                            let scale = 1;

                            let pointX = 0;
                            let pointY = 0;

                            let panning = false;

                            let startX = 0;
                            let startY = 0;

                            container.addEventListener(
                                "mousedown",
                                function(e) {{

                                    e.preventDefault();

                                    startX =
                                        e.clientX -
                                        pointX;

                                    startY =
                                        e.clientY -
                                        pointY;

                                    panning = true;
                                }}
                            );

                            window.addEventListener(
                                "mouseup",
                                function() {{
                                    panning = false;
                                }}
                            );

                            container.addEventListener(
                                "mousemove",
                                function(e) {{

                                    if (!panning)
                                        return;

                                    pointX =
                                        e.clientX -
                                        startX;

                                    pointY =
                                        e.clientY -
                                        startY;

                                    updateTransform();
                                }}
                            );

                            container.addEventListener(
                                "wheel",
                                function(e) {{

                                    e.preventDefault();

                                    const delta =
                                        Math.sign(
                                            e.deltaY
                                        ) * -0.15;

                                    scale =
                                        Math.min(
                                            Math.max(
                                                0.5,
                                                scale + delta
                                            ),
                                            15
                                        );

                                    updateTransform();
                                }},
                                {{ passive:false }}
                            );

                            function updateTransform() {{

                                el.style.transform =
                                    "translate(" +
                                    pointX + "px, " +
                                    pointY + "px) " +
                                    "scale(" +
                                    scale +
                                    ")";
                            }}

                            </script>

                            </body>
                            </html>
                            """

                            components.html(
                                html_code,
                                height=550
                            )

                        else:

                            st.info(
                                "⚠️ Gambar gagal "
                                "ditarik dari server."
                            )

                    st.markdown(
                        f"""
                        <a
                            href="{esc(original_url)}"
                            target="_blank"
                            style="
                                display:block;
                                width:100%;
                                text-align:center;
                                padding:12px;
                                background:#2980b9;
                                color:white;
                                border-radius:6px;
                                text-decoration:none;
                                font-weight:bold;
                                font-size:14px;
                                margin-top:15px;
                            "
                        >
                            Buka URL / Foto Asli ↗
                        </a>
                        """,
                        unsafe_allow_html=True
                    )

                else:

                    st.info(
                        "Tidak ada URL foto."
                    )

            else:

                st.markdown(
                    """
                    <div
                        style="
                            border:2px dashed #555;
                            padding:30px 15px;
                            text-align:center;
                            color:#888;
                            border-radius:10px;
                            margin-top:50px;
                        "
                    >

                    <div style="font-size:35px;">
                        🖼️
                    </div>

                    <br>

                    Klik salah satu tower
                    pada peta untuk melihat foto.

                    </div>
                    """,
                    unsafe_allow_html=True
                )


    # ======================================================
    # FINAL TABLE
    # ======================================================

    st.markdown("---")

    st.subheader(
        "📋 Tabel Hasil Analisis Terpadu"
    )


    # ======================================================
    # RESULT + DRAWING
    # ======================================================

    table_parts = []

    if (
        result_df is not None
        and not result_df.empty
    ):

        table_parts.append(
            result_df.copy()
        )

    if drawing_results:

        table_parts.append(
            pd.DataFrame(
                drawing_results
            )
        )


    # ======================================================
    # BUILD TABLE
    # ======================================================

    if table_parts:

        final_df = pd.concat(
            table_parts,
            ignore_index=True
        )


        # ==================================================
        # ATTACH REVIEW STATUS + REMARK
        # ==================================================

        review_values = final_df.apply(
            lambda row: get_review(
                row,
                c_unique
            ),
            axis=1
        )

        final_df[
            "Status Analisa"
        ] = review_values.apply(
            lambda x: x[1]
        )

        final_df[
            "Remark"
        ] = review_values.apply(
            lambda x: x[2]
        )


        # ==================================================
        # REMOVE INTERNAL
        # ==================================================

        remove_internal = [
            "display_name",
            "display_name_ext",
            "lat_val",
            "lon_val",
            "Jarak_Fast_Calc",
            "_nearest_key",
            "_coord_key",
            "_target_relations",
            "_relation_count",
            "Analisis_Type"
        ]


        # ==================================================
        # IMPORTANT COLUMNS
        # ==================================================

        important_columns = [
            "Sumber Analisa",
            "Objek Filter",
            c_unique,
            c_name,
            "Status Analisa",
            "Remark",
            "Jarak (m)",
            c_lat,
            c_lon
        ]

        important_columns = list(
            dict.fromkeys(
                important_columns
            )
        )


        # ==================================================
        # MAKE SURE EXISTS
        # ==================================================

        important_columns = [
            c
            for c in important_columns
            if c in final_df.columns
        ]


        # ==================================================
        # REMAINING
        # ==================================================

        remaining_columns = [
            c
            for c in final_df.columns
            if (
                c not in important_columns
                and c not in remove_internal
            )
        ]


        # ==================================================
        # FINAL COLUMNS
        # ==================================================

        final_columns = (
            important_columns
            +
            remaining_columns
        )

        final_df = final_df[
            final_columns
        ].copy()


        # ==================================================
        # SORT
        # ==================================================

        sort_columns = []

        if (
            "Sumber Analisa"
            in final_df.columns
        ):

            sort_columns.append(
                "Sumber Analisa"
            )

        if (
            "Jarak (m)"
            in final_df.columns
        ):

            sort_columns.append(
                "Jarak (m)"
            )

        if sort_columns:

            final_df = (
                final_df
                .sort_values(
                    by=sort_columns,
                    na_position="last"
                )
                .reset_index(
                    drop=True
                )
            )


        # ==================================================
        # STATUS SUMMARY
        # ==================================================

        status_order = [
            "CONTINUE",
            "HOLD",
            "DROP",
            "BELUM REVIEW"
        ]

        status_counts = (
            final_df[
                "Status Analisa"
            ]
            .value_counts()
            .reindex(
                status_order,
                fill_value=0
            )
        )

        s1, s2, s3, s4 = st.columns(
            4
        )

        with s1:
            st.metric(
                "Continue",
                int(status_counts["CONTINUE"])
            )

        with s2:
            st.metric(
                "Hold",
                int(status_counts["HOLD"])
            )

        with s3:
            st.metric(
                "Drop",
                int(status_counts["DROP"])
            )

        with s4:
            st.metric(
                "Belum Review",
                int(status_counts["BELUM REVIEW"])
            )

        with st.expander(
            "✅ Resume Hasil Analisa Berdasarkan Status",
            expanded=True
        ):

            resume_status_filter = st.multiselect(
                "Filter Status Resume",
                [
                    "CONTINUE",
                    "HOLD",
                    "DROP"
                ],
                default=[
                    "CONTINUE",
                    "HOLD",
                    "DROP"
                ],
                key="resume_status_filter"
            )

            if resume_status_filter:

                resume_review_df = final_df[
                    final_df[
                        "Status Analisa"
                    ].isin(
                        resume_status_filter
                    )
                ].copy()

            else:

                resume_review_df = final_df.iloc[
                    0:0
                ].copy()

            st.caption(
                f"Menampilkan **{len(resume_review_df):,} tower** "
                "sesuai status review yang dipilih."
            )

            st.dataframe(
                resume_review_df,
                use_container_width=True,
                hide_index=True,
                height=min(
                    400,
                    max(
                        120,
                        38 * (
                            len(resume_review_df)
                            + 1
                        )
                    )
                )
            )

        with st.expander(
            "📋 Detail Seluruh Hasil Analisis",
            expanded=False
        ):

            # ==============================================
            # RESULT INFO
            # ==============================================

            st.caption(
                f"Menampilkan "
                f"**{len(final_df):,} tower** "
                f"hasil analisis."
            )

            # ==============================================
            # DISPLAY
            # ==============================================

            st.dataframe(
                final_df,
                use_container_width=True,
                hide_index=True,
                height=500
            )


        # ==================================================
        # DOWNLOAD
        # ==================================================

        csv_final = (
            final_df
            .to_csv(
                index=False
            )
            .encode(
                "utf-8-sig"
            )
        )

        st.download_button(
            "📥 Download Tabel Analisis Terpadu (CSV)",
            data=csv_final,
            file_name=(
                "hasil_analisis_tower_dengan_status.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

    else:

        st.warning(
            "Belum ada tower yang terdeteksi "
            "sesuai filter analisis."
        )