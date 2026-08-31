// =========================================================
// DATA FILE: blog-posts.ts
// =========================================================
// CARA EDIT: Tambah artikel baru di array blogPosts.
// slug: URL-friendly ID unik (tanpa spasi, pakai tanda -)
// date: format YYYY-MM-DD
// readTime: estimasi menit baca
// content: isi artikel dalam format Markdown
//   - # = heading besar
//   - ## = heading sedang
//   - **teks** = bold
//   - `kode` = inline code
//   - ```python ... ``` = code block
// =========================================================

export interface BlogPost {
  slug: string;
  title: string;
  excerpt: string;
  date: string;
  readTime: number;
  tags: string[];
  content: string;
}

export const blogPosts: BlogPost[] = [
  {
    slug: "otomasi-laporan-mstower-python",
    title: "Otomasi Laporan MS Tower dengan Python: Dari Manual ke Batch Processing",
    excerpt:
      "Bagaimana saya membangun tool batch extractor untuk output MS Tower yang menghemat " +
      "puluhan jam kerja manual setiap bulannya.",
    date: "2024-12-01",
    readTime: 8,
    tags: ["Python", "MS Tower", "Automation", "Streamlit"],
    content: `# Otomasi Laporan MS Tower dengan Python

Sebagai structural engineer yang sering mengerjakan analisis tower, saya menemukan bahwa proses 
membaca dan merangkum hasil output MS Tower sangat memakan waktu. File .rpt dari MS Tower 
berisi ratusan halaman data — dan kita hanya butuh beberapa baris governing ratio!

## Masalah yang Dihadapi

Setiap analisis tower menghasilkan file output (.rpt) yang berisi:
- Governing member ratios (rasio tegangan tertinggi)
- Node displacements dan sway
- Support reactions
- Tower rotations

Memproses 10 file secara manual bisa memakan waktu 4-6 jam.

## Solusi: Python + Streamlit

Saya membangun **MS Tower Batch Extractor Pro** menggunakan:

- \`Python\` untuk parsing file .rpt
- \`Pandas\` untuk manipulasi data
- \`Streamlit\` untuk antarmuka web yang mudah digunakan
- \`OpenPyXL\` untuk export Excel yang rapi

\`\`\`python
def parse_governing_ratios(content: str) -> pd.DataFrame:
    """Extract governing member ratios dari output MS Tower."""
    # Logic parsing...
    pass
\`\`\`

## Hasil

Dengan tool ini, proses yang dulunya 4-6 jam kini selesai dalam **5-10 menit** 
dengan akurasi yang konsisten.

## Pelajaran

Sebagai engineer, skill programming adalah multiplier yang powerful. Tidak perlu 
menjadi programmer profesional — cukup tahu cara menyelesaikan masalah engineering 
dengan kode.
`,
  },
  {
    slug: "visualisasi-geometri-tower-3d",
    title: "Memvisualisasikan Geometri Tower 3D dari Input MSTower",
    excerpt:
      "MSTower geometry parser yang saya buat mampu merender model tower dalam tampilan " +
      "3D interaktif langsung dari file input, membantu QC desain sebelum analisis.",
    date: "2025-01-15",
    readTime: 6,
    tags: ["Python", "Plotly", "3D Visualization", "Tower Design"],
    content: `# Memvisualisasikan Geometri Tower 3D dari Input MSTower

Salah satu tantangan dalam desain tower adalah memverifikasi bahwa geometri yang 
diinput ke MSTower sudah benar sebelum menjalankan analisis penuh.

## Mengapa Ini Penting?

Kesalahan geometri yang tidak terdeteksi bisa mengakibatkan:
- Analisis yang salah dan tidak valid
- Waktu dan resource terbuang
- Dalam kasus ekstrem: desain yang tidak aman

## Solusi: Parser + 3D Renderer

Saya membangun parser yang membaca file input MSTower dan merender geometri dalam:

1. **2D Engineering View** — tampilan face, plan, dan hip section
2. **3D Interactive View** — model Plotly yang bisa dirotasi

\`\`\`python
geometry = build_tower_geometry(file_content)
fig = make_tower_3d_figure(geometry)
fig.show()
\`\`\`

## Teknologi

- **Parser**: Pure Python regex dan state machine
- **Renderer**: Plotly Go untuk 3D interaktif
- **UI**: Streamlit untuk kemudahan penggunaan

Tool ini sekarang menjadi bagian standar dari workflow QC sebelum setiap analisis tower.
`,
  },
];
