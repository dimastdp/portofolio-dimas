import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function ExtractSDAFallback() {
  return (
    <div
      style={{
        minHeight: "100vh",
        textAlign: "center",
        padding: "10rem 2rem 5rem",
      }}
    >
      <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>
        📊 MS Tower Batch Extractor
      </h1>
      <p
        style={{
          color: "var(--text-secondary)",
          maxWidth: "600px",
          margin: "0 auto 2rem",
          lineHeight: "1.6",
        }}
      >
        Saat ini Anda sedang menjalankan{" "}
        <strong>Next.js Development Server</strong> (Port 3000) secara mandiri.{" "}
        <br />
        <br />
        Dalam konfigurasi <em>production</em>, rute <code>/apps/extract-sda</code>{" "}
        akan di-<em>redirect</em> oleh <strong>Nginx</strong> langsung ke halaman
        Streamlit <strong>1_Extract_SDA</strong>. <br />
        <br />
        Karena Nginx dan Streamlit belum menyala (membutuhkan Docker), maka
        halaman ini muncul sebagai <em>fallback</em>.
      </p>

      <div
        style={{
          padding: "1.5rem",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "1rem",
          display: "inline-block",
          textAlign: "left",
          marginBottom: "2rem",
        }}
      >
        <h3 style={{ marginBottom: "0.5rem" }}>Cara Menampilkan App Lokal:</h3>
        <ul style={{ color: "var(--text-secondary)", marginLeft: "1.5rem" }}>
          <li>
            Pastikan <strong>Docker</strong> sudah terinstall.
          </li>
          <li>Buka terminal baru di root folder proyek ini.</li>
          <li>
            Jalankan:{" "}
            <code style={{ color: "var(--accent-cyan)" }}>
              docker-compose up -d --build
            </code>
          </li>
          <li>
            Buka browser ke:{" "}
            <a
              href="http://localhost/apps/extract-sda"
              style={{ color: "var(--accent-cyan)", fontWeight: "bold" }}
            >
              http://localhost/apps/extract-sda
            </a>
          </li>
        </ul>
      </div>

      <div>
        <Link
          href="/#apps"
          className="btn btn-primary"
          style={{ display: "inline-flex" }}
        >
          <ArrowLeft size={18} style={{ marginRight: "0.5rem" }} /> Kembali ke
          Web Apps
        </Link>
      </div>
    </div>
  );
}
