import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function WebAppsFallback() {
  return (
    <div style={{ paddingTop: "10rem", minHeight: "100vh", textAlign: "center", padding: "10rem 2rem 5rem" }}>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🚧 Web Apps Server Offline 🚧</h1>
      <p style={{ color: "var(--text-secondary)", maxWidth: "600px", margin: "0 auto 2rem", lineHeight: "1.6" }}>
        Saat ini Anda sedang menjalankan <strong>Next.js Development Server</strong> (Port 3000) secara mandiri. <br /><br />
        Dalam konfigurasi *production* yang sudah kita buat, rute <code>/webapps</code> tidak ditangani oleh Next.js, 
        melainkan akan di-<em>intercept</em> oleh <strong>Nginx</strong> dan diteruskan langsung ke server <strong>Python Streamlit</strong>. <br /><br />
        Karena Nginx dan Streamlit belum menyala di laptop Anda (membutuhkan Docker), maka halaman ini muncul sebagai <em>fallback</em> sementara.
      </p>
      
      <div style={{ padding: "1.5rem", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "1rem", display: "inline-block", textAlign: "left", marginBottom: "2rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Cara Menampilkan Web Apps Lokal:</h3>
        <ul style={{ color: "var(--text-secondary)", marginLeft: "1.5rem" }}>
          <li>Pastikan <strong>Docker</strong> sudah terinstall.</li>
          <li>Buka terminal baru di root folder proyek ini.</li>
          <li>Jalankan perintah: <code style={{ color: "var(--accent-cyan)" }}>docker-compose up -d --build</code></li>
          <li>Buka browser ke: <a href="http://localhost/webapps" style={{ color: "var(--accent-cyan)", fontWeight: "bold" }}>http://localhost/webapps</a> (tanpa port 3000)</li>
        </ul>
      </div>

      <div>
        <Link href="/" className="btn btn-primary" style={{ display: "inline-flex" }}>
          <ArrowLeft size={18} style={{ marginRight: "0.5rem" }} /> Kembali ke Beranda
        </Link>
      </div>
    </div>
  );
}
