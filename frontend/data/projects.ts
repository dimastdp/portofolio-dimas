// =========================================================
// DATA FILE: projects.ts
// =========================================================
// CARA EDIT: Tambah/ubah proyek Anda di sini.
// tags: array kata kunci yang muncul sebagai badge
// imageUrl: URL gambar proyek (atau kosongkan untuk placeholder)
// liveUrl: link demo/live (kosongkan "" jika tidak ada)
// githubUrl: link GitHub (kosongkan "" jika tidak ada)
// =========================================================

export interface Project {
  id: string;
  title: string;
  description: string;
  longDescription?: string;
  tags: string[];
  imageUrl?: string;
  liveUrl?: string;
  githubUrl?: string;
  featured?: boolean;
}

export const projects: Project[] = [
  {
    id: "mstower-extractor",
    title: "MS Tower Batch Extractor Pro",
    description:
      "Tool batch processing untuk output MS Tower. Mengekstrak governing ratio, " +
      "displacement, sway/twist, dan support reaction dari multiple file sekaligus " +
      "dengan export Excel yang terformat rapi.",
    tags: ["Python", "Streamlit", "Pandas", "MS Tower", "Structural Engineering"],
    featured: true,
    liveUrl: "/apps/extract-sda",
  },
  {
    id: "mstower-geometry",
    title: "MSTower Geometry Viewer",
    description:
      "Visualizer 2D dan 3D interaktif untuk geometri tower dari input MSTower. " +
      "Menampilkan member schedule, panel geometry, dan validasi model secara visual.",
    tags: ["Python", "Streamlit", "Plotly", "3D Visualization", "Tower Design"],
    featured: true,
    liveUrl: "/apps/mstower",
  },
  {
    id: "shifting-checker",
    title: "Geo-Mapper Pro (Shifting Checker)",
    description:
      "Aplikasi berbasis peta interaktif untuk mengecek pergeseran (shifting) koordinat site. " +
      "Menggunakan Folium dan Geopy untuk visualisasi radius dan pengukuran jarak antar site secara akurat.",
    tags: ["Python", "Streamlit", "Folium", "Geospatial", "Data Mapping"],
    featured: true,
    liveUrl: "/apps/shifting-checker",
  },
  {
    id: "auto-signed",
    title: "PDF Auto-Signer",
    description:
      "Alat otomasi tanda tangan digital pada dokumen PDF dengan presisi. " +
      "Menggunakan OCR (Tesseract) untuk mendeteksi area tanda tangan atau mode template untuk posisi absolut.",
    tags: ["Python", "Streamlit", "PyMuPDF", "OCR", "Automation"],
    featured: true,
    liveUrl: "/apps/auto-signed",
  },
];
