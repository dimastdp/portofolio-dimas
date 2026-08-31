"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { skills, skillCategories } from "@/data/skills";
import styles from "./Skills.module.css";

export default function Skills() {
  const [activeCategory, setActiveCategory] = useState<string>("all");

  const filtered = activeCategory === "all"
    ? skills
    : skills.filter((s) => s.category === activeCategory);

  return (
    <section id="skills" className={`section ${styles.skills}`}>
      <div className="container">
        <div className="section-header">
          <span className="section-tag">Expertise</span>
          <h2 className="section-title">
            Skills & <span>Tools</span>
          </h2>
          <p className="section-subtitle">
            Kombinasi keahlian engineering tradisional dan teknologi modern.
          </p>
        </div>

        {/* Category filter */}
        <div className={styles.filters}>
          <button
            id="filter-all"
            className={`${styles.filterBtn} ${activeCategory === "all" ? styles.active : ""}`}
            onClick={() => setActiveCategory("all")}
          >
            All
          </button>
          {skillCategories.map((cat) => (
            <button
              key={cat.key}
              id={`filter-${cat.key}`}
              className={`${styles.filterBtn} ${activeCategory === cat.key ? styles.active : ""}`}
              onClick={() => setActiveCategory(cat.key)}
              style={{ "--cat-color": cat.color } as React.CSSProperties}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Skills grid */}
        <div className={styles.grid}>
          {filtered.map((skill, i) => {
            const cat = skillCategories.find((c) => c.key === skill.category);
            return (
              <motion.div
                key={skill.name}
                className={`card ${styles.card}`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.04, duration: 0.4 }}
              >
                <div className={styles.cardTop}>
                  <span className={styles.icon}>{skill.icon}</span>
                  <span className={styles.skillName}>{skill.name}</span>
                </div>

                {/* Level bar */}
                <div className={styles.levelBar}>
                  <div
                    className={styles.levelFill}
                    style={{
                      width: `${(skill.level / 5) * 100}%`,
                      background: cat?.color ?? "var(--accent-cyan)",
                    }}
                  />
                </div>
                <div className={styles.levelText}>
                  {["", "Beginner", "Familiar", "Proficient", "Advanced", "Expert"][skill.level]}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
