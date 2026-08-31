"use client";

import { profile } from "@/data/profile";
import styles from "./Footer.module.css";
import { ArrowUp } from "lucide-react";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.container}`}>
        <div className={styles.top}>
          <div className={styles.brand}>
            <span className={styles.logoIcon}>⟨/⟩</span>
            <span className={styles.name}>{profile.name} {profile.surname}</span>
            <p className={styles.tagline}>{profile.title}</p>
          </div>

          <div className={styles.socials}>
            {profile.linkedin && (
              <a href={profile.linkedin} target="_blank" rel="noreferrer">LinkedIn</a>
            )}
            {profile.github && (
              <a href={profile.github} target="_blank" rel="noreferrer">GitHub</a>
            )}
            <a href={`mailto:${profile.email}`}>Email</a>
          </div>

          <button onClick={scrollToTop} className={styles.scrollTop} aria-label="Scroll to top">
            <ArrowUp size={20} />
          </button>
        </div>

        <div className={styles.bottom}>
          <p>&copy; {currentYear} {profile.name} {profile.surname}. All rights reserved.</p>
          <p>
            Built with Next.js & Python. Designed with <span className={styles.heart}>♥</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
