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
    year: "Januari 2026 – Sekarang", //
    title: "Officer 2 - Asset Productivity", //
    organization: "PT Dayamitra Telekomunikasi Tbk", //
    location: "Jakarta, Indonesia", //
    description:
      "Melakukan penilaian struktural dan teknis untuk menara SST dan Monopole berdasarkan standar TIA-222-G guna mendukung proyek B2S dan Kolokasi." +
      "Mengelola data kapasitas untuk lebih dari 40.000 situs aktif serta mengoptimalkan desain pondasi yang berkontribusi pada pengurangan biaya konstruksi hingga 5%." +
      "Mengembangkan solusi Python dan Power Query untuk mengotomatisasi pemrosesan data, mempercepat waktu pelaporan dari mingguan menjadi harian.",
    type: "work",
    current: true,
  },
  {
    year: "Januari 2025 – Desember 2025", //
    title: "Site Management Coordinator", //
    organization: "PT Dayamitra Telekomunikasi Tbk", //
    location: "Makassar, Indonesia", //
    description:
      "Bertanggung jawab atas kinerja operasional lebih dari 2.000 menara di Makassar." +
      "Mengelola tim manajemen situs dan vendor pemeliharaan, serta berkoordinasi dengan tim lapangan untuk menyelesaikan masalah (trouble tickets) secara efisien." +
      "Menyusun dan mempresentasikan laporan kinerja mingguan yang berisi wawasan dan rekomendasi strategis.",
    type: "work",
  },
  {
    year: "April 2024 – Desember 2024", //
    title: "Customer Relationship Officer", //
    organization: "PT Dayamitra Telekomunikasi Tbk", //
    location: "Makassar, Indonesia", //
    description:
      "Menganalisis data dan menyusun laporan visualisasi menggunakan tingkat mahir Excel dan PowerPoint untuk menghasilkan wawasan bisnis." +
      "Memantau kemajuan pekerjaan CRM dan melakukan evaluasi untuk mendukung inisiatif strategis perusahaan menggunakan alat analitik dan dasar Python.",
    type: "work",
  },
  {
    year: "Januari 2023 – April 2024", //
    title: "Management Trainee (Operation & Maintenance / Asset Management)", //
    organization: "PT Dayamitra Telekomunikasi Tbk", //
    location: "Jayapura, Papua", //
    description:
      "Mengawasi kinerja operasional 1.440 menara di Papua dan mengelola vendor pemeliharaan." +
      "Menegosiasikan perpanjangan sewa lahan menara untuk regional Papua dan Maluku." +
      "Mengembangkan dasbor pemantauan keberlanjutan aset dan formulir VBA untuk mengotomatisasi pembuatan dokumen perjanjian dan negosiasi.",
    type: "work",
  },
  {
    year: "September 2021 – Januari 2023", //
    title: "Junior Steel Detailer", //
    organization: "PT. Seacad Service", //
    location: "Jakarta, Indonesia", //
    description:
      "Membuat gambar detail fabrikasi untuk struktur bangunan dan jembatan bagi klien internasional menggunakan perangkat lunak Tekla Structures." +
      "Terlibat dalam pengerjaan proyek berskala global, termasuk Wilson Academy of Applied Technology (AS), Databank IAD3, dan LIRR Mainline 1 & 3.",
    type: "work",
  },

  // ── Pendidikan ──
  {
    year: "Desember 2020 – September 2022", //
    title: "Sarjana Terapan Teknik (D4) - Rekayasa Pemeliharaan dan Perbaikan Gedung", //
    organization: "Politeknik Negeri Bandung", //
    location: "Bandung, Indonesia",
    description:
      "Lulus dengan IPK 3.44/4.00.Fokus pada teknik sipil tingkat lanjut dan perbaikan struktur.",
    type: "education",
  },
  {
    year: "September 2017 – Desember 2020", //
    title: "Diploma III (D3) - Teknik Konstruksi Gedung", //
    organization: "Politeknik Negeri Bandung", //
    location: "Bandung, Indonesia",
    description:
      "Lulus dengan IPK 3.41/4.00.Mempelajari fundamental konstruksi dan rekayasa sipil.",
    type: "education",
  },
];
