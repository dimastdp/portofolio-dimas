"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import styles from "./WebApps.module.css";
import { ExternalLink, Maximize2, Minimize2 } from "lucide-react";

export default function WebApps() {
  const [expandedApp, setExpandedApp] = useState<string | null>(null);

  const toggleExpand = (app: string) => {
    setExpandedApp((prev) => (prev === app ? null : app));
  };

  return (
    <section id="apps" className={`section ${styles.appsSection}`}>
      <div className="container">
        <div className="section-header">
          <span className="section-tag">Interactive</span>
          <h2 className="section-title">
            Python <span>Web Apps</span>
          </h2>
          <p className="section-subtitle">
            Beberapa aplikasi Streamlit yang saya kembangkan untuk memecahkan
            masalah engineering spesifik. Cobalah langsung di bawah ini.
          </p>
        </div>

        <div className={styles.grid}>

          {/* ── App 1: Extract SDA ── */}
          <motion.div
            className={`${styles.appContainer} ${
              expandedApp === "extract" ? styles.expanded : ""
            }`}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <div className={styles.appHeader}>
              <div className={styles.appTitle}>
                <span className={styles.icon}>📊</span>
                <div>
                  <h3>MS Tower Batch Extractor</h3>
                  <span className={styles.appBadge}>Extract SDA</span>
                </div>
              </div>
              <div className={styles.appControls}>
                <button
                  className={styles.controlBtn}
                  onClick={() => toggleExpand("extract")}
                  title={expandedApp === "extract" ? "Minimize" : "Expand"}
                >
                  {expandedApp === "extract" ? (
                    <Minimize2 size={18} />
                  ) : (
                    <Maximize2 size={18} />
                  )}
                </button>
                <a
                  href="/apps/extract-sda"
                  target="_blank"
                  rel="noreferrer"
                  className={styles.controlBtn}
                  title="Open in new tab"
                >
                  <ExternalLink size={18} />
                </a>
              </div>
            </div>
            <div className={styles.iframeWrapper}>
              <iframe
                src="/apps/extract-sda"
                className={styles.iframe}
                title="MS Tower Batch Extractor"
              />
            </div>
          </motion.div>

          {/* ── App 2: Geometry Viewer ── */}
          <motion.div
            className={`${styles.appContainer} ${
              expandedApp === "geometry" ? styles.expanded : ""
            }`}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.15, duration: 0.5 }}
          >
            <div className={styles.appHeader}>
              <div className={styles.appTitle}>
                <span className={styles.icon}>🗼</span>
                <div>
                  <h3>MSTower Geometry Viewer</h3>
                  <span className={styles.appBadge}>3D Visualization</span>
                </div>
              </div>
              <div className={styles.appControls}>
                <button
                  className={styles.controlBtn}
                  onClick={() => toggleExpand("geometry")}
                  title={expandedApp === "geometry" ? "Minimize" : "Expand"}
                >
                  {expandedApp === "geometry" ? (
                    <Minimize2 size={18} />
                  ) : (
                    <Maximize2 size={18} />
                  )}
                </button>
                <a
                  href="/apps/mstower"
                  target="_blank"
                  rel="noreferrer"
                  className={styles.controlBtn}
                  title="Open in new tab"
                >
                  <ExternalLink size={18} />
                </a>
              </div>
            </div>
            <div className={styles.iframeWrapper}>
              <iframe
                src="/apps/mstower"
                className={styles.iframe}
                title="MSTower Geometry Viewer"
              />
            </div>
          </motion.div>

          {/* ── App 3: Shifting Checker ── */}
          <motion.div
            className={`${styles.appContainer} ${
              expandedApp === "shifting" ? styles.expanded : ""
            }`}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3, duration: 0.5 }}
          >
            <div className={styles.appHeader}>
              <div className={styles.appTitle}>
                <span className={styles.icon}>🗺️</span>
                <div>
                  <h3>Geo-Mapper Pro</h3>
                  <span className={styles.appBadge}>Shifting Checker</span>
                </div>
              </div>
              <div className={styles.appControls}>
                <button
                  className={styles.controlBtn}
                  onClick={() => toggleExpand("shifting")}
                  title={expandedApp === "shifting" ? "Minimize" : "Expand"}
                >
                  {expandedApp === "shifting" ? (
                    <Minimize2 size={18} />
                  ) : (
                    <Maximize2 size={18} />
                  )}
                </button>
                <a
                  href="/apps/shifting-checker"
                  target="_blank"
                  rel="noreferrer"
                  className={styles.controlBtn}
                  title="Open in new tab"
                >
                  <ExternalLink size={18} />
                </a>
              </div>
            </div>
            <div className={styles.iframeWrapper}>
              <iframe
                src="/apps/shifting-checker"
                className={styles.iframe}
                title="Geo-Mapper Pro — Shifting Checker"
              />
            </div>
          </motion.div>

          {/* ── App 4: Auto-Signer ── */}
          <motion.div
            className={`${styles.appContainer} ${
              expandedApp === "autosigned" ? styles.expanded : ""
            }`}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.45, duration: 0.5 }}
          >
            <div className={styles.appHeader}>
              <div className={styles.appTitle}>
                <span className={styles.icon}>🖋️</span>
                <div>
                  <h3>PDF Auto-Signer</h3>
                  <span className={styles.appBadge}>Automation</span>
                </div>
              </div>
              <div className={styles.appControls}>
                <button
                  className={styles.controlBtn}
                  onClick={() => toggleExpand("autosigned")}
                  title={expandedApp === "autosigned" ? "Minimize" : "Expand"}
                >
                  {expandedApp === "autosigned" ? (
                    <Minimize2 size={18} />
                  ) : (
                    <Maximize2 size={18} />
                  )}
                </button>
                <a
                  href="/apps/auto-signed"
                  target="_blank"
                  rel="noreferrer"
                  className={styles.controlBtn}
                  title="Open in new tab"
                >
                  <ExternalLink size={18} />
                </a>
              </div>
            </div>
            <div className={styles.iframeWrapper}>
              <iframe
                src="/apps/auto-signed"
                className={styles.iframe}
                title="PDF Auto-Signer"
              />
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
}
