import streamlit as st

st.set_page_config(
    page_title="Engineering Web Apps",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ Engineering Web Apps")
st.markdown("""
<a href="/" target="_self" style="text-decoration: none; font-weight: bold; color: #00D4FF;">← Kembali ke Portfolio</a>
""", unsafe_allow_html=True)

st.markdown("""
Selamat datang di portal Web Apps Engineering.
Silakan pilih aplikasi dari sidebar di sebelah kiri:

1. **Extract SDA**: Alat bantu batch extractor untuk MS Tower.
2. **Geometry Viewer**: Visualisasi model 3D dan 2D dari MSTower.
3. **Shifting Checker (Geo-Mapper Pro)**: Tool pengecekan shifting site berbasis peta interaktif.
""")
