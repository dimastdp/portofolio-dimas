"use client";

import { motion } from "framer-motion";
import { profile } from "@/data/profile";
import styles from "./About.module.css";

const highlights = [
  { icon: "🏗️", label: "Structural Engineering" },
  { icon: "🐍", label: "Python Development" },
  { icon: "📊", label: "Data Analysis" },
  { icon: "🗼", label: "Tower Design" },
];

export default function About() {
  return (
    <section id="about" className={`section ${styles.about}`}>
      <div className="container">
        <div className={styles.grid}>
          {/* Avatar column */}
          <motion.div
            className={styles.avatarCol}
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <div className={styles.avatarWrapper}>
              <div className={styles.avatar}>
                <span className={styles.avatarInitials}>
                  {profile.name.charAt(0)}
                  {profile.surname.charAt(0)}
                </span>
              </div>
              {/* Decorative rings */}
              <div className={styles.ring1} />
              <div className={styles.ring2} />
            </div>

            {/* Info card */}
            <div className={`card ${styles.infoCard}`}>
              {[
                { icon: "📍", label: profile.location },
                { icon: "📧", label: profile.email },
                { icon: "📞", label: profile.phone },
              ].map((item) => (
                <div key={item.label} className={styles.infoRow}>
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Content column */}
          <motion.div
            className={styles.content}
            initial={{ opacity: 0, x: 40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div className="section-header" style={{ textAlign: "left", marginBottom: "1.5rem" }}>
              <span className="section-tag">About Me</span>
              <h2 className="section-title">
                Civil Engineer
              </h2>
            </div>

            <p className={styles.bio}>{profile.bio}</p>

            {/* Highlights */}
            <div className={styles.highlights}>
              {highlights.map((h, i) => (
                <motion.div
                  key={h.label}
                  className={styles.highlight}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                >
                  <span className={styles.highlightIcon}>{h.icon}</span>
                  <span className={styles.highlightLabel}>{h.label}</span>
                </motion.div>
              ))}
            </div>

            {/* Social links */}
            <div className={styles.socials}>
              {profile.linkedin && (
                <a href={profile.linkedin} target="_blank" rel="noopener noreferrer" className={styles.social}>
                  <span>LinkedIn</span> ↗
                </a>
              )}
              {profile.github && (
                <a href={profile.github} target="_blank" rel="noopener noreferrer" className={styles.social}>
                  <span>GitHub</span> ↗
                </a>
              )}
              <a href={`mailto:${profile.email}`} className={styles.social}>
                <span>Email</span> ✉
              </a>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
