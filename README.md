# Portfolio Dimas — Fullstack Web & Web Apps

Proyek ini adalah website portofolio fullstack yang menggabungkan website profil dengan aplikasi web Python interaktif (MS Tower tools). 

## 🚀 Stack Teknologi
- **Frontend**: Next.js 14, React, CSS Modules, Framer Motion
- **Web Apps**: Python, Streamlit, Pandas, Plotly
- **Infrastruktur**: Docker Compose, Nginx Reverse Proxy

---

## 📝 Cara Mengedit Konten (Tanpa Coding)

Semua konten profil dapat diedit dengan mudah melalui file di folder `frontend/data/`. Buka file menggunakan text editor (seperti VS Code atau Notepad).

1. **Biodata & Hero Section**
   - File: `frontend/data/profile.ts`
   - Edit: Nama, bio singkat, link sosmed, kontak.

2. **Keahlian (Skills)**
   - File: `frontend/data/skills.ts`
   - Edit: Tambah/hapus skill, ubah level (1-5), dan kategori.

3. **Perjalanan Karir/Pendidikan (Timeline)**
   - File: `frontend/data/timeline.ts`
   - Edit: Tambah riwayat pekerjaan atau pendidikan.

4. **Proyek (Portfolio)**
   - File: `frontend/data/projects.ts`
   - Edit: Tambah deskripsi proyek, tag teknologi, link demo/github.

5. **Artikel Blog**
   - File: `frontend/data/blog-posts.ts`
   - Edit: Artikel menggunakan format Markdown. Sangat mudah menulis dengan heading (`#`), bold (`**teks**`), dan kode.

**Catatan:** Setelah mengedit file, jika dijalankan secara lokal dengan `npm run dev`, perubahan akan langsung terlihat. Jika sudah di-deploy dengan Docker, Anda perlu build ulang (lihat bagian Deployment).

---

## 💻 Menjalankan di Komputer Lokal (Development)

### 1. Menjalankan Portfolio (Next.js)
```bash
cd frontend
npm install
npm run dev
# Buka http://localhost:3000
```

### 2. Menjalankan Python Apps (Streamlit)
```bash
# App 1: Extract SDA
cd apps/extract_sda
pip install -r requirements.txt
streamlit run extract_sda.py --server.port=8501

# App 2: MSTower Geometry
cd apps/mstower_geometry
pip install -r requirements.txt
streamlit run mstower_geometry_app.py --server.port=8502
```

---

## 🌍 Deployment ke VPS (1GB RAM)

Deployment diatur dengan **Docker Compose**, sehingga semua komponen (Next.js, 2 Streamlit App, Nginx) bisa berjalan dengan 1 perintah saja.

### Prasyarat di VPS:
- Docker & Docker Compose sudah terinstall
- Port 80 dan 443 terbuka (Firewall)
- RAM VPS minimal 1GB (sudah sangat cukup)

### Langkah Deploy:

1. **Upload kode ke VPS** (via Git atau FTP).
2. **Masuk ke folder proyek** di VPS.
3. **Jalankan perintah build & up**:
   ```bash
   # Build images dan jalankan di background (-d)
   docker-compose up --build -d
   ```
4. **Cek status container**:
   ```bash
   docker-compose ps
   ```
5. Akses IP VPS atau Domain Anda di browser.

### Konfigurasi Nginx & Domain:
Jika Anda sudah menyambungkan Domain ke IP VPS, Nginx akan otomatis merutekan:
- `namadomain.com/` → Portfolio Next.js
- `namadomain.com/apps/extract-sda/` → Streamlit App 1
- `namadomain.com/apps/mstower/` → Streamlit App 2

### SSL / HTTPS (Opsional tapi disarankan):
Anda bisa menggunakan Certbot (Let's Encrypt) di VPS Anda, dan mengupdate file `nginx/nginx.conf` untuk menggunakan sertifikat SSL tersebut.

### Update Web (Jika ada perubahan):
Jika Anda mengubah konten (misal menambah artikel blog), lakukan update dengan:
```bash
git pull origin main  # Jika pakai git
docker-compose up --build -d
```
Docker akan otomatis me-rebuild image yang berubah tanpa mematikan website selama proses build.
