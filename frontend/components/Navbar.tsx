"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTheme } from "@/components/ThemeProvider";
import { profile } from "@/data/profile";
import styles from "./Navbar.module.css";

const navLinks = [
  { href: "/#about", label: "About" },
  { href: "/#skills", label: "Skills" },
  { href: "/#timeline", label: "Timeline" },
  { href: "/#projects", label: "Projects" },
  { href: "/#apps", label: "Web Apps" },
  { href: "/blog", label: "Blog" },
  { href: "/#contact", label: "Contact" },
];

export default function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className={`${styles.nav} ${scrolled ? styles.scrolled : ""}`}>
      <div className={`container ${styles.inner}`}>
        {/* Logo */}
        <Link href="/" className={styles.logo}>
          <span className={styles.logoIcon}>⟨/⟩</span>
          <span className={styles.logoName}>{profile.name}</span>
        </Link>

        {/* Desktop Links */}
        <ul className={styles.links}>
          {navLinks.map((link) => (
            <li key={link.href}>
              <a href={link.href} className={styles.link}>
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        {/* Right controls */}
        <div className={styles.controls}>
          {/* Theme toggle */}
          <button
            id="theme-toggle"
            onClick={toggleTheme}
            className={styles.themeBtn}
            aria-label="Toggle theme"
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>


          {/* Hamburger */}
          <button
            className={`${styles.hamburger} ${menuOpen ? styles.open : ""}`}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
            id="hamburger-menu"
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className={styles.mobileMenu}>
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className={styles.mobileLink}
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
            </a>
          ))}
        </div>
      )}
    </nav>
  );
}
