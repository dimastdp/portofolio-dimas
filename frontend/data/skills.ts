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
  // ── Civil & Structural Engineering ──
  { name: "Structural Analysis", level: 5, category: "engineering", icon: "🏗️" },
  { name: "MS Tower", level: 5, category: "engineering", icon: "🗼" },
  { name: "Tower Design", level: 5, category: "engineering", icon: "📐" },
  { name: "Foundation Design", level: 4, category: "engineering", icon: "⚓" },
  { name: "AutoCAD", level: 4, category: "engineering", icon: "📏" },
  { name: "STAAD Pro", level: 3, category: "engineering", icon: "🔩" },

  // ── Data & Programming ──
  { name: "Python", level: 4, category: "data", icon: "🐍" },
  { name: "Pandas / NumPy", level: 4, category: "data", icon: "📊" },
  { name: "Plotly / Data Viz", level: 4, category: "data", icon: "📈" },
  { name: "Streamlit", level: 4, category: "data", icon: "⚡" },
  { name: "Excel / VBA", level: 4, category: "data", icon: "📋" },
  { name: "SQL", level: 3, category: "data", icon: "🗄️" },

  // ── Tools ──
  { name: "Docker", level: 3, category: "tools", icon: "🐳" },
  { name: "Git / GitHub", level: 3, category: "tools", icon: "🔀" },
  { name: "Linux / VPS", level: 3, category: "tools", icon: "🖥️" },
  { name: "VS Code", level: 5, category: "tools", icon: "💻" },

  // ── Soft Skills ──
  { name: "Engineering Report", level: 5, category: "soft", icon: "📝" },
  { name: "Problem Solving", level: 5, category: "soft", icon: "🧠" },
  { name: "Project Management", level: 4, category: "soft", icon: "📅" },
];

export const skillCategories = [
  { key: "engineering", label: "Civil Engineering", color: "#00D4FF" },
  { key: "data", label: "Data & Programming", color: "#7C3AED" },
  { key: "tools", label: "Tools & DevOps", color: "#059669" },
  { key: "soft", label: "Soft Skills", color: "#D97706" },
];
