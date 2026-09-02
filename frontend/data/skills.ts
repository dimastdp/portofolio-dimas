// =========================================================
// DATA FILE: skills.ts
// =========================================================
// CARA EDIT: Tambah/hapus/ubah skill sesuai keahlian Anda.
// level: 1-5 (1=pemula, 5=ahli)
// category: "engineering" | "data" | "tools" | "soft"
// =========================================================

export interface Skill {
  name: string;
  level: number; // 1-5
  category: "engineering" | "data" | "tools" | "soft";
  icon: string; // emoji
}

export const skills: Skill[] = [
  // ── Civil & Telecom Engineering ──
  { name: "Structural & Tower Assessment", level: 5, category: "engineering", icon: "🏗️" }, // TIA-222-G, SST, Monopole
  { name: "Site Planning", level: 4, category: "engineering", icon: "🗺️" }, //
  { name: "MS Tower & tnxTower", level: 4, category: "engineering", icon: "🗼" },
  { name: "Tekla Structures", level: 4, category: "engineering", icon: "🏢" }, // Fabrikasi & detailing
  { name: "AutoCAD 2D & 3D", level: 4, category: "engineering", icon: "📏" }, //

  // ── Data & Programming ──
  { name: "Excel & Power Query", level: 5, category: "data", icon: "📊" }, // Otomatisasi data
  { name: "Python", level: 4, category: "data", icon: "🐍" }, // Analitik & Pandas
  { name: "VBA Macros", level: 4, category: "data", icon: "⚙️" }, //
  { name: "Data Visualization", level: 4, category: "data", icon: "📈" }, //

  // ── Tools & Automation ──
  { name: "Power Automate", level: 4, category: "tools", icon: "⚡" }, // Otomatisasi alur kerja
  { name: "PowerPoint", level: 5, category: "tools", icon: "📑" }, // Pelaporan visual
  { name: "Power BI & Looker", level: 4, category: "tools", icon: "📉" },
  { name: "Streamlit & Geospatial Apps", level: 4, category: "tools", icon: "🌐" },

  // ── Management & Soft Skills ──
  { name: "Asset & Operational Management", level: 5, category: "soft", icon: "🏢" }, //
  { name: "Project Management", level: 4, category: "soft", icon: "📅" }, //
  { name: "Technical Reporting", level: 5, category: "soft", icon: "📝" }, //
  { name: "Stakeholder Management", level: 4, category: "soft", icon: "🤝" }, //
];

export const skillCategories = [
  { key: "engineering", label: "Civil & Telecom Engineering", color: "#00D4FF" },
  { key: "data", label: "Data & Programming", color: "#7C3AED" },
  { key: "tools", label: "Tools & Automation", color: "#059669" },
  { key: "soft", label: "Management & Soft Skills", color: "#D97706" },
];
