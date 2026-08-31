"""
MStower Geometry Viewer — Streamlit App Wrapper
================================================
App sederhana untuk memvisualisasikan geometri tower dari MStower.
Upload file input MStower Anda untuk mendapatkan 2D dan 3D view.
"""

import streamlit as st



from mstower_geometry import (
    build_tower_geometry,
    geometry_members_dataframe,
    geometry_panels_dataframe,
    material_schedule_dataframe,
    geometry_validation_dataframe,
    geometry_validation_summary,
    make_engineering_2d_figure,
    make_material_elevation_figure,
    make_tower_3d_figure,
)

st.title("🗼 MSTower Geometry Viewer")
st.markdown(
    "Upload file geometri MSTower Anda untuk menampilkan visualisasi 2D dan 3D."
)

uploaded_file = st.file_uploader(
    "Upload MSTower Input File (.txt / .inp)",
    type=["txt", "inp"],
    help="File input MSTower yang berisi data geometri tower.",
)

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8", errors="replace")
    with st.spinner("Memproses geometri tower..."):
        try:
            geometry = build_tower_geometry(content)
            st.success(f"✅ Tower berhasil diproses: {geometry.title_1}")

            tab1, tab2, tab3, tab4 = st.tabs(
                ["🏗️ 3D View", "📐 2D Engineering", "📊 Members", "✅ Validation"]
            )

            with tab1:
                fig3d = make_tower_3d_figure(geometry)
                st.plotly_chart(fig3d, use_container_width=True)

            with tab2:
                fig2d = make_engineering_2d_figure(geometry)
                st.plotly_chart(fig2d, use_container_width=True)

            with tab3:
                df_members = geometry_members_dataframe(geometry)
                df_panels = geometry_panels_dataframe(geometry)
                st.subheader("Members")
                st.dataframe(df_members, use_container_width=True)
                st.subheader("Panels")
                st.dataframe(df_panels, use_container_width=True)

            with tab4:
                df_validation = geometry_validation_dataframe(geometry)
                summary = geometry_validation_summary(geometry)
                st.markdown(summary)
                st.dataframe(df_validation, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error memproses file: {e}")
else:
    st.info(
        "👆 Upload file input MSTower di atas untuk memulai visualisasi.",
        icon="ℹ️",
    )
