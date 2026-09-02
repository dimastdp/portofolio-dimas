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
    year: "Januari 2026 – Sekarang", //[cite: 1]
    title: "Officer 2 - Asset Productivity", //[cite: 1]
    organization: "PT Dayamitra Telekomunikasi Tbk", //[cite: 1]
    location: "Jakarta, Indonesia", //[cite: 1]
    description:
      "Melakukan penilaian struktural dan teknis untuk menara SST dan Monopole berdasarkan standar TIA-222-G guna mendukung proyek B2S dan Kolokasi.[cite: 1] " +
      "Mengelola data kapasitas untuk lebih dari 40.000 situs aktif serta mengoptimalkan desain pondasi yang berkontribusi pada pengurangan biaya konstruksi hingga 5%.[cite: 1] " +
      "Mengembangkan solusi Python dan Power Query untuk mengotomatisasi pemrosesan data, mempercepat waktu pelaporan dari mingguan menjadi harian.[cite: 1]",
    type: "work",
    current: true,
  },
  {
    year: "Januari 2025 – Desember 2025", //[cite: 1]
    title: "Site Management Coordinator", //[cite: 1]
    organization: "PT Dayamitra Telekomunikasi Tbk", //[cite: 1]
    location: "Makassar, Indonesia", //[cite: 1]
    description:
      "Bertanggung jawab atas kinerja operasional lebih dari 2.000 menara di Makassar.[cite: 1] " +
      "Mengelola tim manajemen situs dan vendor pemeliharaan, serta berkoordinasi dengan tim lapangan untuk menyelesaikan masalah (trouble tickets) secara efisien.[cite: 1] " +
      "Menyusun dan mempresentasikan laporan kinerja mingguan yang berisi wawasan dan rekomendasi strategis.[cite: 1]",
    type: "work",
  },
  {
    year: "April 2024 – Desember 2024", //[cite: 1]
    title: "Customer Relationship Officer", //[cite: 1]
    organization: "PT Dayamitra Telekomunikasi Tbk", //[cite: 1]
    location: "Makassar, Indonesia", //[cite: 1]
    description:
      "Menganalisis data dan menyusun laporan visualisasi menggunakan tingkat mahir Excel dan PowerPoint untuk menghasilkan wawasan bisnis.[cite: 1] " +
      "Memantau kemajuan pekerjaan CRM dan melakukan evaluasi untuk mendukung inisiatif strategis perusahaan menggunakan alat analitik dan dasar Python.[cite: 1]",
    type: "work",
  },
  {
    year: "Januari 2023 – April 2024", //[cite: 1]
    title: "Management Trainee (Operation & Maintenance / Asset Management)", //[cite: 1]
    organization: "PT Dayamitra Telekomunikasi Tbk", //[cite: 1]
    location: "Jayapura, Papua", //[cite: 1]
    description:
      "Mengawasi kinerja operasional 1.440 menara di Papua dan mengelola vendor pemeliharaan.[cite: 1] " +
      "Menegosiasikan perpanjangan sewa lahan menara untuk regional Papua dan Maluku.[cite: 1] " +
      "Mengembangkan dasbor pemantauan keberlanjutan aset dan formulir VBA untuk mengotomatisasi pembuatan dokumen perjanjian dan negosiasi.[cite: 1]",
    type: "work",
  },
  {
    year: "September 2021 – Januari 2023", //[cite: 1]
    title: "Junior Steel Detailer", //[cite: 1]
    organization: "PT. Seacad Service", //[cite: 1]
    location: "Jakarta, Indonesia", //[cite: 1]
    description:
      "Membuat gambar detail fabrikasi untuk struktur bangunan dan jembatan bagi klien internasional menggunakan perangkat lunak Tekla Structures.[cite: 1] " +
      "Terlibat dalam pengerjaan proyek berskala global, termasuk Wilson Academy of Applied Technology (AS), Databank IAD3, dan LIRR Mainline 1 & 3.[cite: 1]",
    type: "work",
  },

  // ── Pendidikan ──
  {
    year: "Desember 2020 – September 2022", //[cite: 1]
    title: "Sarjana Terapan Teknik (D4) - Rekayasa Pemeliharaan dan Perbaikan Gedung", //[cite: 1]
    organization: "Politeknik Negeri Bandung", //[cite: 1]
    location: "Bandung, Indonesia",
    description:
      "Lulus dengan IPK 3.44/4.00.[cite: 1] Fokus pada teknik sipil tingkat lanjut dan perbaikan struktur.",
    type: "education",
  },
  {
    year: "September 2017 – Desember 2020", //[cite: 1]
    title: "Diploma III (D3) - Teknik Konstruksi Gedung", //[cite: 1]
    organization: "Politeknik Negeri Bandung", //[cite: 1]
    location: "Bandung, Indonesia",
    description:
      "Lulus dengan IPK 3.41/4.00.[cite: 1] Mempelajari fundamental konstruksi dan rekayasa sipil.",
    type: "education",
  },
];