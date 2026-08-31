"use client";

import { motion } from "framer-motion";
import { timeline } from "@/data/timeline";
import styles from "./Timeline.module.css";

export default function Timeline() {
  return (
    <section id="timeline" className={`section ${styles.timelineSection}`}>
      <div className="container">
        <div className="section-header">
          <span className="section-tag">Journey</span>
          <h2 className="section-title">
            Career & <span>Education</span>
          </h2>
          <p className="section-subtitle">
            Jejak langkah profesional dan latar belakang akademis saya.
          </p>
        </div>

        <div className={styles.timeline}>
          {timeline.map((item, i) => (
            <motion.div
              key={i}
              className={styles.item}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              {/* Timeline dot & line */}
              <div className={styles.lineIndicator}>
                <div className={`${styles.dot} ${item.current ? styles.dotActive : ""}`} />
                {i !== timeline.length - 1 && <div className={styles.line} />}
              </div>

              {/* Content */}
              <div className={styles.content}>
                <div className={styles.meta}>
                  <span className={styles.year}>{item.year}</span>
                  <span className={styles.type}>
                    {item.type === "work" ? "💼 Experience" : "🎓 Education"}
                  </span>
                </div>
                <h3 className={styles.title}>{item.title}</h3>
                <div className={styles.orgInfo}>
                  <span className={styles.org}>{item.organization}</span>
                  <span className={styles.dotSeparator}>•</span>
                  <span className={styles.location}>{item.location}</span>
                </div>
                <p className={styles.desc}>{item.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
