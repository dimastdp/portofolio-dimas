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
import base64

# ==========================================================
# CONFIG
# ==========================================================

st.set_page_config(
    page_title="Geo-Mapper Pro",
    layout="wide"
)

# ==========================================================
# CSS
# ==========================================================

st.markdown(
    """
    <style>
    .dummy {
        background-color: transparent !important;
        border: none !important;
    }

    .stFolium {
        width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

@st.cache_data
def load_and_clean_data(source, filename=""):
    if not source:
        return None

    try:

        # --------------------------------------------------
        # SOURCE STRING
        # --------------------------------------------------

        if isinstance(source, str):

            df = pd.read_csv(
                io.StringIO(source),
                sep=None,
                engine="python",
                dtype=str,
                on_bad_lines="skip"
            )

        # --------------------------------------------------
        # EXCEL
        # --------------------------------------------------

        elif filename.lower().endswith((".xls", ".xlsx")):

            df = pd.read_excel(
                source,
                dtype=str
            )

        # --------------------------------------------------
        # CSV FILE
        # --------------------------------------------------

        else:

            content = source.read()
            source.seek(0)

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

                    df = pd.read_csv(
                        io.StringIO(
                            content.decode(enc)
                        ),
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
                    "Format encoding file tidak didukung."
                )

        # --------------------------------------------------
        # CLEAN HEADER
        # --------------------------------------------------

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
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
    for i, col in enumerate(options):

        if any(
                k in col.lower()
                for k in primary_keys
        ):
            return i

    for i, col in enumerate(options):

        if any(
                k in col.lower()
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

    # Handle decimal comma
    s = s.str.replace(
        ",",
        ".",
        regex=False
    )

    # Remove spaces
    s = s.str.replace(
        " ",
        "",
        regex=False
    )

    return pd.to_numeric(
        s,
        errors="coerce"
    )


# ==========================================================
# HAVERSINE
# ==========================================================

def haversine_vectorized(
        lat1,
        lon1,
        lat2,
        lon2
):
    lat1, lon1, lat2, lon2 = map(
        np.radians,
        [
            lat1,
            lon1,
            lat2,
            lon2
        ]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
            np.sin(dlat / 2.0) ** 2
            +
            np.cos(lat1)
            *
            np.cos(lat2)
            *
            np.sin(dlon / 2.0) ** 2
    )

    return (
            6371000
            *
            (
                    2
                    *
                    np.arcsin(
                        np.sqrt(a)
                    )
            )
    )


# ==========================================================
# POPUP
# ==========================================================

def build_popup(
        row,
        c_name_col,
        c_unique_col,
        jarak_m=None,
        title_prefix=""
):
    html = (
        "<div "
        "style='font-family: sans-serif; "
        "min-width: 500px; "
        "max-width: 700px;'>"
    )

    html += (
        "<div "
        "style='background-color: #2C3E50; "
        "color: white; "
        "padding: 10px; "
        "margin-bottom: 10px; "
        "border-radius: 4px;'>"
    )

    html += (
        f"<b style='font-size:14px;'>"
        f"{title_prefix}"
        f"ID: {row[c_unique_col]} | "
        f"{row[c_name_col]}"
        f"</b><br>"
    )

    if pd.notna(jarak_m):
        html += (
            "<span "
            "style='font-size:12px; "
            "color:#f1c40f;'>"
            "Jarak: "
            f"<b>{round(float(jarak_m), 2)} meter</b>"
            "</span>"
        )

    html += "</div>"

    exclude_cols = [
        "display_name",
        "display_name_ext",
        "lat_val",
        "lon_val",
        "Jarak_Fast_Calc",
        "Jarak (m)",
        "Sumber Analisa",
        "Objek Filter",
        "geometry",
        "_nearest_key"
    ]

    valid_items = {
        k: v
        for k, v in row.items()
        if (
                k not in exclude_cols
                and pd.notna(v)
                and str(v).strip() != ""
        )
    }

    html += (
        "<div "
        "style='display:flex; "
        "flex-wrap:wrap; "
        "font-size:11px;'>"
    )

    for k, v in valid_items.items():

        val_str = str(v).strip()

        is_url = False
        href = val_str

        if (
                val_str.startswith("http://")
                or val_str.startswith("https://")
        ):

            is_url = True

        elif val_str.startswith("www."):

            is_url = True
            href = "https://" + val_str

        display_str = val_str

        if len(display_str) > 40:
            display_str = (
                    display_str[:37]
                    + "..."
            )

        if is_url:

            final_val = (
                f"<a href='{href}' "
                f"target='_blank' "
                f"style='color:#2980b9; "
                f"text-decoration:underline;' "
                f"title='{val_str}'>"
                f"{display_str}"
                f"</a>"
            )

        else:

            final_val = display_str

        html += (
            "<div "
            "style='width:33%; "
            "box-sizing:border-box; "
            "padding:4px; "
            "border-bottom:1px solid #eee;'>"
        )

        html += (
            "<div "
            "style='color:#7f8c8d; "
            "font-weight:bold; "
            "font-size:9px; "
            "text-transform:uppercase;'>"
            f"{k}"
            "</div>"
        )

        html += (
            "<div "
            "style='color:#2c3e50; "
            "overflow-wrap:break-word;'>"
            f"{final_val}"
            "</div>"
        )

        html += "</div>"

    html += "</div></div>"

    return html


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
    tolerance = 0.0005

    match = df[
        (
                abs(
                    df[c_lat] - lat
                ) < tolerance
        )
        &
        (
                abs(
                    df[c_lon] - lon
                ) < tolerance
        )
        ]

    photo_col = next(
        (
            col
            for col in df.columns
            if "last photo" in col.lower()
        ),
        None
    )

    if (
            not match.empty
            and photo_col
    ):

        url = match.iloc[0][photo_col]

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
# FORMAT IMAGE LINK
# ==========================================================

def format_image_link(raw_url):
    if not isinstance(raw_url, str):
        return None, None

    url = raw_url.strip()

    if (
            url == ""
            or url.lower() == "nan"
    ):
        return None, None

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

    if not url.startswith("http"):

        if (
                url.startswith("www.")
                or url.startswith("drive.")
                or url.startswith("servpinisi.")
        ):

            url = "https://" + url

        else:

            return None, None

    gdrive_match = re.search(
        r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
        url
    )

    if gdrive_match:
        file_id = gdrive_match.group(1)

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
# CACHE IMAGE
# ==========================================================

@st.cache_data(
    show_spinner=False
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
    uploaded_file = (
        st.sidebar.file_uploader(
            "Upload Data Utama",
            type=[
                "csv",
                "xlsx",
                "xls"
            ]
        )
    )

    csv_input_text = (
        st.sidebar.text_area(
            "Atau Tempel Data (CSV format)"
        )
    )

file_name_main = (
    uploaded_file.name
    if uploaded_file
    else ""
)

df_main_raw = load_and_clean_data(
    uploaded_file
    if uploaded_file
    else csv_input_text,
    file_name_main
)

if df_main_raw is not None:

    # ======================================================
    # CLEAN DUPLICATE COLUMNS
    # ======================================================

    df_main_raw = (
        df_main_raw
        .loc[
        :,
        ~df_main_raw.columns.duplicated()
        ]
        .copy()
    )

    all_cols = (
        df_main_raw
        .columns
        .tolist()
    )

    # ======================================================
    # COLUMN MAPPING
    # ======================================================

    st.sidebar.markdown(
        "### 🔍 Mapping Database"
    )

    c_name = st.sidebar.selectbox(
        "Nama Site",
        all_cols,
        index=smart_detect(
            all_cols,
            ["site", "name"],
            ["actual"],
            0
        )
    )

    c_unique = st.sidebar.selectbox(
        "Kode Unik",
        all_cols,
        index=(
            1
            if len(all_cols) > 1
            else 0
        )
    )

    c_lat = st.sidebar.selectbox(
        "Latitude",
        all_cols,
        index=smart_detect(
            all_cols,
            ["lat"],
            [],
            1
        )
    )

    c_lon = st.sidebar.selectbox(
        "Longitude",
        all_cols,
        index=smart_detect(
            all_cols,
            ["lon", "long"],
            [],
            2
        )
    )

    # ======================================================
    # MAIN DATA
    # ======================================================

    df = df_main_raw.copy()

    df[c_lat] = safe_to_float(
        df[c_lat]
    )

    df[c_lon] = safe_to_float(
        df[c_lon]
    )

    # ======================================================
    # VALID COORDINATE
    # ======================================================

    df = df[
        (
            df[c_lat].notnull()
        )
        &
        (
            df[c_lon].notnull()
        )
        &
        (
                df[c_lat] != 0
        )
        ]

    df = df[
        (
            df[c_lat].between(
                -90,
                90
            )
        )
        &
        (
            df[c_lon].between(
                -180,
                180
            )
        )
        ].reset_index(drop=True)

    # ======================================================
    # COLUMN FILTERING
    # ======================================================

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 1.5. Filter Data Utama")

    filter_col = st.sidebar.selectbox(
        "Pilih Kolom Filter",
        ["-- TIDAK ADA --"] + list(df.columns)
    )

    if filter_col != "-- TIDAK ADA --":
        unique_vals = df[filter_col].dropna().unique().tolist()
        filter_vals = st.sidebar.multiselect(
            f"Pilih Value '{filter_col}'",
            unique_vals
        )

        if filter_vals:
            df = df[df[filter_col].isin(filter_vals)].reset_index(drop=True)

    # ======================================================
    # DISPLAY NAME
    # ======================================================

    df["display_name"] = (
            df[c_name].astype(str)
            + " ["
            + df[c_unique].astype(str)
            + "]"
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
        horizontal=True
    )

    df_ext_final = pd.DataFrame()

    if ext_mode != "Tidak Ada":

        if ext_mode == "Upload File":

            ext_src = (
                st.sidebar.file_uploader(
                    "Upload Data Luar",
                    type=[
                        "csv",
                        "xlsx",
                        "xls"
                    ]
                )
            )

            ext_file_name = (
                ext_src.name
                if ext_src
                else ""
            )

        else:

            ext_src = (
                st.sidebar.text_area(
                    "Tempel Data Luar"
                )
            )

            ext_file_name = ""

        df_ext_raw = load_and_clean_data(
            ext_src,
            ext_file_name
        )

        if df_ext_raw is not None:
            df_ext_raw = (
                df_ext_raw
                .loc[
                :,
                ~df_ext_raw.columns.duplicated()
                ]
                .copy()
            )

            ext_cols = (
                df_ext_raw
                .columns
                .tolist()
            )

            r_name = st.sidebar.selectbox(
                "Nama (Luar)",
                ext_cols
            )

            r_lat = st.sidebar.selectbox(
                "Lat (Luar)",
                ext_cols
            )

            r_lon = st.sidebar.selectbox(
                "Lon (Luar)",
                ext_cols
            )

            df_ext_temp = (
                df_ext_raw.copy()
            )

            df_ext_temp["lat_val"] = (
                safe_to_float(
                    df_ext_temp[r_lat]
                )
            )

            df_ext_temp["lon_val"] = (
                safe_to_float(
                    df_ext_temp[r_lon]
                )
            )

            df_ext_final = (
                df_ext_temp[
                    (
                        df_ext_temp["lat_val"]
                        .between(-90, 90)
                    )
                    &
                    (
                        df_ext_temp["lon_val"]
                        .between(-180, 180)
                    )
                    ]
                .copy()
            )

            df_ext_final[
                "display_name_ext"
            ] = (
                    df_ext_final[r_name]
                    .astype(str)
                    + " (Luar)"
            )

    # ======================================================
    # REFERENCE POINT
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "📍 3. Pilih Titik Acuan (Untuk Radius)"
    )

    use_manual = (
        st.sidebar.checkbox(
            "Gunakan Input Manual (Lat, Lon)"
        )
    )

    if use_manual:

        manual_lat = (
            st.sidebar.number_input(
                "Latitude Acuan",
                format="%.6f",
                value=0.0
            )
        )

        manual_lon = (
            st.sidebar.number_input(
                "Longitude Acuan",
                format="%.6f",
                value=0.0
            )
        )

    else:

        manual_lat = 0.0
        manual_lon = 0.0

    # ======================================================
    # SELECT INTERNAL
    # ======================================================

    options_int = (
        df["display_name"]
        .astype(str)
        .unique()
        .tolist()
    )

    pick_int = st.sidebar.multiselect(
        "Data Utama",
        ["-- PILIH SEMUA --"] + options_int,
        default=["-- PILIH SEMUA --"]
    )

    selected_internal = (
        options_int
        if "-- PILIH SEMUA --"
           in pick_int
        else pick_int
    )

    # ======================================================
    # SELECT EXTERNAL
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
            ["-- PILIH SEMUA --"] + options_ext,
            default=["-- PILIH SEMUA --"]
        )

        selected_external = (
            options_ext
            if "-- PILIH SEMUA --"
               in pick_ext
            else pick_ext
        )

    # ======================================================
    # FINAL TARGETS
    # ======================================================

    final_targets = []

    if (
            use_manual
            and manual_lat != 0
    ):
        final_targets.append(
            {
                "label":
                    "Manual Point Acuan",

                "lat":
                    manual_lat,

                "lon":
                    manual_lon
            }
        )

    for s in selected_internal:

        rows = df[
            df["display_name"] == s
            ]

        if not rows.empty:
            final_targets.append(
                {
                    "label": s,
                    "lat": rows.iloc[0][c_lat],
                    "lon": rows.iloc[0][c_lon]
                }
            )

    for s in selected_external:

        rows = df_ext_final[
            df_ext_final[
                "display_name_ext"
            ] == s
            ]

        if not rows.empty:
            final_targets.append(
                {
                    "label": s,
                    "lat":
                        rows.iloc[0]["lat_val"],
                    "lon":
                        rows.iloc[0]["lon_val"]
                }
            )

    # ======================================================
    # SETTINGS
    # ======================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "🎬 4. Settings"
    )

    plot_all_points = (
        st.sidebar.checkbox(
            "📍 Tampilkan SEMUA Titik di Peta (Abaikan Radius)",
            value=False
        )
    )

    tampilkan_foto = (
        st.sidebar.checkbox(
            "🖼️ Proses & Tampilkan Foto",
            value=True,
            help="Uncheck jika ingin peta berjalan lebih cepat tanpa fitur foto."
        )
    )

    # ======================================================
    # FIX: MAKE SURE ALL POINTS ARE IN FOCUS DROPDOWN
    # ======================================================
    focus_options = ["--- Fokus Otomatis ---"]

    if plot_all_points or not df.empty:
        focus_options.append("--- Fokus Semua Titik ---")

    # Tambahkan titik dari input custom/manual/luar (jika ada)
    custom_labels = [t["label"] for t in final_targets if t["label"] not in df["display_name"].values]
    focus_options.extend(custom_labels)

    # Tambahkan semua titik internal yang lolos filter
    if not df.empty:
        focus_options.extend(df["display_name"].tolist())

    selected_focus = (
        st.sidebar.selectbox(
            "Fokus Peta Ke:",
            focus_options
        )
    )

    rad_m = (
        st.sidebar.number_input(
            "Radius Analisis (Meter)",
            min_value=1,
            max_value=50000,
            value=2000
        )
    )

    n_nearest = (
        st.sidebar.number_input(
            "Tampilkan N Tower Terdekat",
            min_value=0,
            max_value=50,
            value=4,
            step=1
        )
    )

    st.sidebar.markdown("---")

    preload_photos = (
        st.sidebar.checkbox(
            "📥 Preload/Cache Foto (Anti Loading)",
            value=False
        )
    )

    # ======================================================
    # TITLE
    # ======================================================

    st.title(
        "📍 Tower Geo-Analysis Pro"
    )

    # ======================================================
    # PRELOAD PHOTO
    # ======================================================

    photo_col_name = next(
        (
            col
            for col in df.columns
            if "last photo"
               in col.lower()
        ),
        None
    )

    if (
            tampilkan_foto
            and preload_photos
            and photo_col_name
    ):

        with st.spinner(
                "🔄 Sedang menyimpan foto "
                "ke memori..."
        ):

            for val in (
                    df[
                        photo_col_name
                    ]
                            .dropna()
            ):

                direct_u, _ = (
                    format_image_link(
                        str(val)
                    )
                )

                if direct_u:
                    cached_download_image(
                        direct_u
                    )

    # ======================================================
    # LAYOUT
    # ======================================================

    if tampilkan_foto:
        col_map, col_photo = st.columns([7, 3])
    else:
        col_map = st.container()
        col_photo = None

    # ======================================================
    # MAP
    # ======================================================

    with col_map:

        fit_all_bounds = False

        if selected_focus == "--- Fokus Semua Titik ---":
            if not df.empty:
                m_center = [
                    df[c_lat].mean(),
                    df[c_lon].mean()
                ]
                m_zoom = 6
                fit_all_bounds = True
            else:
                m_center = [0, 0]
                m_zoom = 2

        elif selected_focus != "--- Fokus Otomatis ---":

            # Cari di df filter
            match_df = df[df["display_name"] == selected_focus]

            if not match_df.empty:
                m_center = [match_df.iloc[0][c_lat], match_df.iloc[0][c_lon]]
                m_zoom = 15
            else:
                # Cari di target acuan (seperti manual input)
                f_data = next((t for t in final_targets if t["label"] == selected_focus), None)
                if f_data:
                    m_center = [f_data["lat"], f_data["lon"]]
                    m_zoom = 15
                else:
                    m_center = [df.iloc[0][c_lat], df.iloc[0][c_lon]]
                    m_zoom = 12

        elif not df.empty:

            m_center = [
                df.iloc[0][c_lat],
                df.iloc[0][c_lon]
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
            control_scale=True
        )

        if fit_all_bounds and not df.empty:
            m.fit_bounds(
                [
                    [df[c_lat].min(), df[c_lon].min()],
                    [df[c_lat].max(), df[c_lon].max()]
                ]
            )

        Fullscreen(
            position="topright",
            title="Full Screen",
            title_cancel="Exit Full Screen"
        ).add_to(m)

        m.add_child(
            MeasureControl(
                position="topleft"
            )
        )

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
        # ANALYSIS STORAGE
        # ==================================================

        master_analysis_list = []

        plot_df_all = pd.DataFrame()

        # ==================================================
        # PLOT ALL POINTS IF CHECKED
        # ==================================================
        if plot_all_points and not df.empty:
            for _, row in df.iterrows():
                tower_lat = row[c_lat]
                tower_lon = row[c_lon]

                popup_html = build_popup(
                    row,
                    c_name,
                    c_unique,
                    jarak_m=None
                )

                popup_obj = folium.Popup(popup_html, max_width=750)
                hover_text = str(row[c_name])

                folium.CircleMarker(
                    location=(tower_lat, tower_lon),
                    radius=4,
                    color="blue",  # Warna menjadi biru
                    fill=True,
                    fill_color="blue",
                    fill_opacity=0.6,
                    weight=1,
                    popup=popup_obj,
                    tooltip=hover_text
                ).add_to(m)

        # ==================================================
        # PROCESS EACH TARGET
        # ==================================================

        for target in final_targets:

            acuan_pt = (
                target["lat"],
                target["lon"]
            )

            # ==================================================
            # CALCULATE DISTANCE
            # ==================================================

            df_calc = df.copy()

            df_calc[
                "Jarak_Fast_Calc"
            ] = haversine_vectorized(
                target["lat"],
                target["lon"],
                df_calc[c_lat],
                df_calc[c_lon]
            )

            # ==================================================
            # RADIUS
            # ==================================================

            in_radius_df = (
                df_calc[
                    df_calc[
                        "Jarak_Fast_Calc"
                    ]
                    <= rad_m
                    ]
                .copy()
            )

            # ==================================================
            # NEAREST TOWER
            # ==================================================

            if n_nearest > 0:

                nearest_candidates = (
                    df_calc[
                        df_calc[
                            "Jarak_Fast_Calc"
                        ]
                        > 1.0
                        ]
                    .copy()
                )

                nearest_df = (
                    nearest_candidates
                    .sort_values(
                        by="Jarak_Fast_Calc",
                        ascending=True
                    )
                    .head(
                        int(n_nearest)
                    )
                    .copy()
                )

            else:

                nearest_df = (
                    pd.DataFrame()
                )

            # ==================================================
            # CREATE COORDINATE KEY
            # ==================================================

            if not nearest_df.empty:
                nearest_df[
                    "_nearest_key"
                ] = (
                        nearest_df[c_lat]
                        .round(7)
                        .astype(str)
                        + "_"
                        +
                        nearest_df[c_lon]
                        .round(7)
                        .astype(str)
                )

            # ==================================================
            # MERGE RADIUS + NEAREST
            # ==================================================

            to_plot_df = pd.concat(
                [
                    in_radius_df,
                    nearest_df
                ],
                ignore_index=True
            )

            # ==================================================
            # REMOVE DUPLICATE COORDINATES
            # ==================================================

            if not to_plot_df.empty:
                to_plot_df[
                    "_coord_key"
                ] = (
                        to_plot_df[c_lat]
                        .round(7)
                        .astype(str)
                        + "_"
                        +
                        to_plot_df[c_lon]
                        .round(7)
                        .astype(str)
                )

                to_plot_df = (
                    to_plot_df
                    .drop_duplicates(
                        subset=[
                            "_coord_key"
                        ]
                    )
                    .copy()
                )

            # ==================================================
            # PRECISE GEODESIC DISTANCE
            # ==================================================

            exact_match_row = None

            if not to_plot_df.empty:

                to_plot_df[
                    "Jarak (m)"
                ] = to_plot_df.apply(
                    lambda r:
                    round(
                        geodesic(
                            acuan_pt,
                            (
                                r[c_lat],
                                r[c_lon]
                            )
                        ).meters,
                        2
                    ),
                    axis=1
                )

                # ==============================================
                # EXACT ACUAN
                # ==============================================

                exact_matches = (
                    to_plot_df[
                        to_plot_df[
                            "Jarak (m)"
                        ]
                        < 1.0
                        ]
                )

                if not exact_matches.empty:
                    exact_match_row = (
                        exact_matches
                        .iloc[0]
                    )

                # ==============================================
                # ANALYSIS INFO
                # ==============================================

                to_plot_df[
                    "Sumber Analisa"
                ] = (
                        "Titik Acuan ("
                        + target["label"]
                        + ")"
                )

                to_plot_df[
                    "Objek Filter"
                ] = (
                    f"Radius {rad_m}m / "
                    f"{int(n_nearest)} Terdekat"
                )

                master_analysis_list.append(
                    to_plot_df
                )

                plot_df_all = pd.concat(
                    [
                        plot_df_all,
                        to_plot_df
                    ],
                    ignore_index=True
                )

            # ==================================================
            # ACUAN MARKER
            # ==================================================

            if exact_match_row is not None:

                popup_html = build_popup(
                    exact_match_row,
                    c_name,
                    c_unique,
                    jarak_m=0.0,
                    title_prefix="[ACUAN] "
                )

                popup_obj = folium.Popup(
                    popup_html,
                    max_width=750
                )

                hover_text = (
                        "[ACUAN] "
                        +
                        str(
                            exact_match_row[
                                c_name
                            ]
                        )
                )

                folium.Marker(
                    acuan_pt,
                    icon=folium.Icon(
                        color="orange",
                        icon="star"
                    ),
                    popup=popup_obj,
                    tooltip=hover_text
                ).add_to(m)


            else:

                folium.Marker(
                    acuan_pt,
                    icon=folium.Icon(
                        color="orange",
                        icon="star"
                    ),
                    popup=folium.Popup(
                        (
                                "<b>ACUAN:</b><br>"
                                + target["label"]
                        ),
                        max_width=300
                    ),
                    tooltip=(
                            "ACUAN: "
                            + target["label"]
                    )
                ).add_to(m)

            # ==================================================
            # RADIUS CIRCLE
            # ==================================================

            folium.Circle(
                acuan_pt,
                radius=rad_m,
                color="blue",
                fill=True,
                fill_opacity=0.05,
                weight=1
            ).add_to(m)

            # ==================================================
            # PLOT TOWERS
            # ==================================================

            if not to_plot_df.empty:

                # ----------------------------------------------
                # NEAREST COORDINATE SET
                # ----------------------------------------------

                nearest_coords = set()

                if not nearest_df.empty:
                    nearest_coords = set(
                        zip(
                            nearest_df[
                                c_lat
                            ].round(7),
                            nearest_df[
                                c_lon
                            ].round(7)
                        )
                    )

                # ----------------------------------------------
                # LOOP TOWER
                # ----------------------------------------------

                for _, row in (
                        to_plot_df.iterrows()
                ):

                    tower_lat = (
                        row[c_lat]
                    )

                    tower_lon = (
                        row[c_lon]
                    )

                    tower_pt = (
                        tower_lat,
                        tower_lon
                    )

                    # ==========================================
                    # CHECK NEAREST
                    # ==========================================

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
                            in nearest_coords
                    )

                    # ==========================================
                    # POPUP
                    # ==========================================

                    popup_html = build_popup(
                        row,
                        c_name,
                        c_unique,
                        row["Jarak (m)"]
                    )

                    popup_obj = folium.Popup(
                        popup_html,
                        max_width=750
                    )

                    hover_text = str(
                        row[c_name]
                    )

                    # ==========================================
                    # MARKER
                    # ==========================================

                    folium.CircleMarker(
                        location=tower_pt,
                        radius=7
                        if is_nearest
                        else 6,
                        color=(
                            "red"
                            if is_nearest
                            else "lime"
                        ),
                        fill=True,
                        fill_color=(
                            "red"
                            if is_nearest
                            else "lime"
                        ),
                        fill_opacity=0.85,
                        weight=2
                        if is_nearest
                        else 1,
                        popup=popup_obj,
                        tooltip=hover_text
                    ).add_to(m)

                    # ==========================================
                    # LINE TO NEAREST
                    # ==========================================

                    if is_nearest:
                        folium.PolyLine(
                            [
                                acuan_pt,
                                tower_pt
                            ],
                            color="red",
                            weight=1.5,
                            dash_array="5,5",
                            opacity=0.6
                        ).add_to(m)

            # ==================================================
            # DEBUG INFO
            # ==================================================

            st.sidebar.markdown(
                "---"
            )

            st.sidebar.write(
                f"📍 **{target['label']}**"
            )

            st.sidebar.write(
                f"🔵 Radius: "
                f"{len(in_radius_df)} tower"
            )

            st.sidebar.write(
                f"🔴 Nearest: "
                f"{len(nearest_df)} tower"
            )

            if not nearest_df.empty:
                debug_nearest = (
                    nearest_df[
                        [
                            c_unique,
                            c_name,
                            c_lat,
                            c_lon,
                            "Jarak_Fast_Calc"
                        ]
                    ]
                    .copy()
                )

                debug_nearest[
                    "Jarak (m)"
                ] = (
                    debug_nearest[
                        "Jarak_Fast_Calc"
                    ]
                    .round(2)
                )

                with st.sidebar.expander(
                        "🔎 Detail Nearest",
                        expanded=False
                ):
                    st.dataframe(
                        debug_nearest[
                            [
                                c_unique,
                                c_name,
                                c_lat,
                                c_lon,
                                "Jarak (m)"
                            ]
                        ],
                        hide_index=True
                    )

        # ======================================================
        # DRAWING ANALYSIS
        # ======================================================

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

        if drawings:

            drawn_areas = []
            drawn_markers = []

            for d in drawings:

                geom_type = (
                    d["geometry"]["type"]
                )

                props = d.get(
                    "properties",
                    {}
                )

                # ----------------------------------------------
                # POLYGON
                # ----------------------------------------------

                if geom_type == "Polygon":

                    drawn_areas.append(
                        {
                            "type":
                                "POLYGON",
                            "shape":
                                shape(
                                    d["geometry"]
                                )
                        }
                    )


                # ----------------------------------------------
                # POLYLINE
                # ----------------------------------------------

                elif geom_type == "LineString":

                    drawn_areas.append(
                        {
                            "type":
                                "POLYLINE",
                            "shape":
                                shape(
                                    d["geometry"]
                                ).buffer(
                                    100 / 111000
                                )
                        }
                    )


                # ----------------------------------------------
                # POINT / CIRCLE
                # ----------------------------------------------

                elif geom_type == "Point":

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
                                    d[
                                        "geometry"
                                    ][
                                        "coordinates"
                                    ],
                                "radius":
                                    rad
                            }
                        )

                    else:

                        drawn_markers.append(
                            d[
                                "geometry"
                            ][
                                "coordinates"
                            ]
                        )

            # ==================================================
            # CHECK SHAPES
            # ==================================================

            in_shape_list = []

            for area in drawn_areas:

                valid_marker_latlon = None

                # ----------------------------------------------
                # MARKER INSIDE AREA
                # ----------------------------------------------

                if drawn_markers:

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
                                        <= area[
                                            "radius"
                                        ]
                                )

                            if is_inside:
                                valid_marker_latlon = (
                                    mk[1],
                                    mk[0]
                                )

                                break


                        except ValueError:

                            pass

                # ----------------------------------------------
                # CHECK TOWER
                # ----------------------------------------------

                for _, row in df.iterrows():

                    tower_lon = (
                        row[c_lon]
                    )

                    tower_lat = (
                        row[c_lat]
                    )

                    try:

                        if area["type"] in [
                            "POLYGON",
                            "POLYLINE"
                        ]:

                            tower_inside = (
                                area["shape"]
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
                                    <= area[
                                        "radius"
                                    ]
                            )


                    except ValueError:

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
                        ] = area["type"]

                        if (
                                valid_marker_latlon
                        ):

                            row_dict[
                                "Jarak (m)"
                            ] = round(
                                geodesic(
                                    valid_marker_latlon,
                                    (
                                        tower_lat,
                                        tower_lon
                                    )
                                ).meters,
                                2
                            )

                        else:

                            row_dict[
                                "Jarak (m)"
                            ] = None

                        in_shape_list.append(
                            row_dict
                        )

            # ==================================================
            # DRAWING RESULT
            # ==================================================

            if in_shape_list:

                df_area = (
                    pd.DataFrame(
                        in_shape_list
                    )
                    .drop_duplicates(
                        subset=[
                            c_lat,
                            c_lon
                        ]
                    )
                )

                master_analysis_list.append(
                    df_area
                )

                plot_df_all = pd.concat(
                    [
                        plot_df_all,
                        df_area
                    ],
                    ignore_index=True
                )

                for _, row in (
                        df_area.iterrows()
                ):
                    popup_html = build_popup(
                        row,
                        c_name,
                        c_unique,
                        row["Jarak (m)"],
                        title_prefix="[GAMBAR] "
                    )

                    popup_obj = folium.Popup(
                        popup_html,
                        max_width=750
                    )

                    hover_text = (
                            "[GAMBAR] "
                            + str(
                        row[c_name]
                    )
                    )

                    folium.CircleMarker(
                        location=(
                            row[c_lat],
                            row[c_lon]
                        ),
                        radius=7,
                        color="darkred",
                        fill=True,
                        fill_color="red",
                        fill_opacity=0.9,
                        weight=2,
                        popup=popup_obj,
                        tooltip=hover_text
                    ).add_to(m)

        # ======================================================
        # FIX: CONDITIONAL RETURNED OBJECTS TO PREVENT RERUN
        # ======================================================

        # Jika tampilkan_foto dicentang -> tangkap klik titik
        # Jika tidak dicentang -> abaikan klik (sehingga app tidak reload saat klik popup)
        ret_objs = ["all_drawings"]
        if tampilkan_foto:
            ret_objs.append("last_object_clicked")

        output = st_folium(
            m,
            use_container_width=True,
            height=750,
            returned_objects=ret_objs,
            key="main_map"
        )

    # ======================================================
    # PHOTO PANEL
    # ======================================================

    if col_photo is not None:
        with col_photo:

            st.markdown(
                "### 🔗 Data URL/Foto"
            )

            photo_col_exists = any(
                "last photo"
                in col.lower()
                for col in df.columns
            )

            if not photo_col_exists:
                st.warning(
                    "⚠️ Kolom dengan nama "
                    "'last photo' tidak ditemukan."
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

            if (
                    clicked_data
                    and not plot_df_all.empty
            ):

                clicked_lat = (
                    clicked_data.get("lat")
                )

                clicked_lon = (
                    clicked_data.get("lng")
                )

                if (
                        clicked_lat is not None
                        and clicked_lon is not None
                ):

                    raw_url, row_data = (
                        find_photo_url(
                            plot_df_all,
                            clicked_lat,
                            clicked_lon,
                            c_lat,
                            c_lon
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
                                .decode("utf-8")
                            )

                            img_src = (
                                    "data:image/jpeg;"
                                    "base64,"
                                    + b64_img
                            )

                            html_code = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                            <style>

                            body {{
                                margin: 0;
                                padding: 0;
                                overflow: hidden;
                                background-color: #0e1117;
                                border-radius: 8px;
                                font-family: sans-serif;
                            }}

                            #container {{
                                width: 100vw;
                                height: 100vh;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                overflow: hidden;
                                cursor: grab;
                                position: relative;
                            }}

                            #container:active {{
                                cursor: grabbing;
                            }}

                            img {{
                                max-width: 100%;
                                max-height: 100%;
                                object-fit: contain;
                                transform-origin: center;
                                transition:
                                    transform 0.1s ease-out;
                                pointer-events: none;
                            }}

                            .hint {{
                                position: absolute;
                                bottom: 10px;
                                left: 10px;
                                color:
                                    rgba(255,255,255,0.7);
                                font-size: 11px;
                                background:
                                    rgba(0,0,0,0.5);
                                padding: 4px 8px;
                                border-radius: 4px;
                                pointer-events: none;
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
                                    'image'
                                );

                            const container =
                                document.getElementById(
                                    'container'
                                );

                            let scale = 1;

                            let panning = false;

                            let pointX = 0;
                            let pointY = 0;

                            let startX = 0;
                            let startY = 0;


                            container.addEventListener(
                                'mousedown',
                                (e) => {{

                                    e.preventDefault();

                                    startX =
                                        e.clientX
                                        - pointX;

                                    startY =
                                        e.clientY
                                        - pointY;

                                    panning = true;
                                }}
                            );


                            window.addEventListener(
                                'mouseup',
                                () => {{
                                    panning = false;
                                }}
                            );


                            window.addEventListener(
                                'mouseleave',
                                () => {{
                                    panning = false;
                                }}
                            );


                            container.addEventListener(
                                'mousemove',
                                (e) => {{

                                    e.preventDefault();

                                    if (!panning)
                                        return;

                                    pointX =
                                        e.clientX
                                        - startX;

                                    pointY =
                                        e.clientY
                                        - startY;

                                    el.style.transform =
                                        `translate(
                                            ${{pointX}}px,
                                            ${{pointY}}px
                                        )
                                        scale(
                                            ${{scale}}
                                        )`;
                                }}
                            );


                            container.addEventListener(
                                'wheel',
                                (e) => {{

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

                                    el.style.transform =
                                        `translate(
                                            ${{pointX}}px,
                                            ${{pointY}}px
                                        )
                                        scale(
                                            ${{scale}}
                                        )`;
                                }}
                            );

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
                                "ditarik dari server asal."
                            )

                    st.markdown(
                        f"""
                        <a
                            href="{original_url}"
                            target="_blank"
                            style="
                                display:block;
                                width:100%;
                                text-align:center;
                                padding:12px;
                                background-color:#2980b9;
                                color:white;
                                border-radius:6px;
                                text-decoration:none;
                                font-weight:bold;
                                font-size:14px;
                                margin-top:15px;
                            "
                        >
                            Buka URL / Foto Asli
                            di Tab Baru ↗
                        </a>
                        """,
                        unsafe_allow_html=True
                    )


                else:

                    st.info(
                        "Tidak ada data link foto."
                    )


            else:

                st.markdown(
                    """
                    <div
                        style="
                            border:2px dashed #ccc;
                            padding:20px;
                            text-align:center;
                            color:#777;
                            border-radius:10px;
                            margin-top:50px;
                        "
                    >

                    Tabel data berada di dalam
                    <b>Popup Peta</b>.

                    <br><br>

                    Silakan
                    <b>klik salah satu titik tower</b>
                    di peta.

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

    if master_analysis_list:

        final_df = pd.concat(
            master_analysis_list,
            ignore_index=True
        )

        # ==================================================
        # REMOVE INTERNAL COLUMNS
        # ==================================================

        remove_internal = [
            "display_name",
            "display_name_ext",
            "lat_val",
            "lon_val",
            "Jarak_Fast_Calc",
            "_nearest_key",
            "_coord_key"
        ]

        kolom_penting_raw = [
            "Sumber Analisa",
            "Objek Filter",
            c_unique,
            c_name,
            "Jarak (m)",
            c_lat,
            c_lon
        ]

        kolom_penting = list(
            dict.fromkeys(
                kolom_penting_raw
            )
        )

        kolom_sisa = [
            c
            for c in final_df.columns
            if (
                    c not in kolom_penting
                    and c not in remove_internal
            )
        ]

        final_df = (
            final_df[
                kolom_penting
                + kolom_sisa
                ]
            .sort_values(
                by=[
                    "Sumber Analisa",
                    "Jarak (m)"
                ],
                na_position="last"
            )
            .reset_index(drop=True)
        )

        # ==================================================
        # DISPLAY TABLE
        # ==================================================

        st.dataframe(
            final_df,
            use_container_width=True
        )

        # ==================================================
        # CSV DOWNLOAD
        # ==================================================

        csv_final = (
            final_df
            .to_csv(
                index=False
            )
            .encode("utf-8-sig")
        )

        st.download_button(
            "📥 Download Tabel Analisis Terpadu (CSV)",
            data=csv_final,
            file_name=(
                "hasil_analisis_tower.csv"
            ),
            mime="text/csv"
        )


    else:

        st.warning(
            "Belum ada tower yang terdeteksi dalam area analisis."
        )