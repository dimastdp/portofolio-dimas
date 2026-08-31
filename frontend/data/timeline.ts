// =========================================================
// DATA FILE: timeline.ts
// =========================================================
// CARA EDIT: Tambah/ubah item di bawah. Urutkan dari terbaru ke lama.
// type: "work" = pekerjaan, "education" = pendidikan
// =========================================================

export interface TimelineItem {
  year: string;
  title: string;
  organization: string;
  location: string;
  description: string;
  type: "work" | "education";
  current?: boolean; // true jika ini posisi saat ini
}

export const timeline: TimelineItem[] = [
  // ── Pekerjaan (urutkan terbaru dulu) ──
  {
    year: "2023 – Sekarang",
    title: "Structural Engineer",
    organization: "PT. [Nama Perusahaan]",
    location: "Jakarta, Indonesia",
    description:
      "Analisis dan desain struktur tower telekomunikasi menggunakan MS Tower. " +
      "Mengembangkan tools Python untuk otomasi batch processing output analisis dan " +
      "visualisasi geometri tower 2D/3D.",
    type: "work",
    current: true,
  },
  {
    year: "2021 – 2023",
    title: "Junior Civil Engineer",
    organization: "PT. [Nama Perusahaan Sebelumnya]",
    location: "Jakarta, Indonesia",
    description:
      "Terlibat dalam desain pondasi dan struktur bangunan. " +
      "Mulai belajar otomasi laporan engineering dengan Python dan Excel VBA.",
    type: "work",
  },
  // ── Pendidikan ──
  {
    year: "2017 – 2021",
    title: "S1 Teknik Sipil",
    organization: "Universitas [Nama Universitas]",
    location: "Indonesia",
    description:
      "Jurusan Teknik Sipil dengan fokus pada struktur dan rekayasa geoteknik. " +
      "Skripsi: [Judul Skripsi Anda].",
    type: "education",
  },
];
