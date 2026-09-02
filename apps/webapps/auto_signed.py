import streamlit as st
import fitz  # PyMuPDF
import os
import time
import re
import subprocess
import io
import pandas as pd
from PIL import Image
from pathlib import Path
import pytesseract
import difflib  # Toleransi Typo (Fuzzy Matching)

import platform

# --- KONFIGURASI TESSERACT OCR ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Jika di Linux (Docker), biarkan menggunakan PATH default


# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PDF Auto-Signer", page_icon="🖋️", layout="wide")

# --- INISIALISASI SESSION STATE ---
if "preview_idx" not in st.session_state: st.session_state.preview_idx = 0
if "select_all" not in st.session_state: st.session_state.select_all = False
if "anchor_idx" not in st.session_state: st.session_state.anchor_idx = 1
if "saved_cx" not in st.session_state: st.session_state.saved_cx = None
if "saved_cy" not in st.session_state: st.session_state.saved_cy = None
if "use_template_mode" not in st.session_state: st.session_state.use_template_mode = False
if "use_ocr" not in st.session_state: st.session_state.use_ocr = False

default_settings = {
    "prot": 0, "px": 0, "py": 40, "pw": 100, "ph": 50,
    "lrot": 0, "lx": 0, "ly": 40, "lw": 100, "lh": 50
}
for k, v in default_settings.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.title("🖋️ PDF Auto-Signer")
st.markdown("**Alat otomasi tanda tangan digital (Optimasi Kecepatan, Anti Gagal, Template Mode & OCR)**")

# ==========================================
# NOTIFIKASI & TABEL HASIL (DENGAN EXPORT)
# ==========================================
if "run_summary" in st.session_state:
    summary = st.session_state.pop("run_summary")
    count_success = summary["count_success"]
    count_skipped = summary["count_skipped"]
    count_failed = summary["count_failed"]

    if count_success:
        st.success(f"✅ Berhasil menandatangani {count_success} file!")
        st.balloons()
    if count_skipped:
        st.warning(f"⚠️ {count_skipped} file DILEWATI (Teks acuan tidak ditemukan / Gagal mode manual).")
    if count_failed:
        st.error(f"❌ {count_failed} file gagal diproses karena error sistem/SharePoint.")

    if summary["results"]:
        df_log = pd.DataFrame(summary["results"])
        st.markdown("##### 📊 Laporan Execution Terakhir")
        st.dataframe(df_log, width='stretch', hide_index=True)

        # Tombol Download ke CSV
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Laporan (CSV)",
            data=csv,
            file_name="Laporan_Auto_Signer.csv",
            mime="text/csv",
            type="primary"
        )
    st.markdown("---")


# ==========================================
# CACHING & UTILITIES
# ==========================================
@st.cache_data
def get_all_pdf_paths_cached(directory_path):
    if not os.path.exists(directory_path): return []
    paths = [str(p) for p in Path(directory_path).rglob("*.pdf") if not p.name.startswith(("Signed_", "temp_"))]
    paths.sort()
    return paths


@st.cache_data
def rotate_image_bytes(img_bytes, angle):
    if angle == 0: return img_bytes
    try:
        image = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        rotated = image.rotate(-angle, expand=True)
        out_io = io.BytesIO()
        rotated.save(out_io, format="PNG")
        return out_io.getvalue()
    except Exception:
        return img_bytes


def get_safe_path(file_path):
    abs_path = os.path.abspath(str(file_path))
    if os.name == 'nt' and not abs_path.startswith("\\\\?\\"):
        return "\\\\?\\" + abs_path
    return abs_path


def ensure_file_downloaded(file_path, timeout=45):
    path_obj = Path(file_path)
    start_time = time.time()
    try:
        subprocess.run(['attrib', '-U', str(path_obj)], capture_output=True, timeout=2)
    except:
        pass

    while time.time() - start_time < timeout:
        try:
            safe_path = get_safe_path(path_obj)
            with open(safe_path, 'rb') as f:
                f.read(1)
            time.sleep(0.5)
            return True
        except (PermissionError, OSError):
            time.sleep(1.5)

    try:
        safe_path = get_safe_path(path_obj)
        return os.path.exists(safe_path) and os.path.getsize(safe_path) > 0
    except:
        return False


# ==========================================
# ROBUST SEARCH & OCR ENGINE
# ==========================================
def robust_search(page, text, use_ocr=False):
    instances = page.search_for(text, quads=True)
    if instances: return instances

    clean_text = " ".join(text.replace("_", " ").split())
    instances = page.search_for(clean_text, quads=True)
    if instances: return instances

    words = page.get_text("words")
    if words:
        words = sorted(words, key=lambda w: (round(w[1] / 10), w[0]))
        full_string = ""
        word_boxes = []
        for w in words:
            word_clean = re.sub(r'[^a-zA-Z0-9]', '', w[4]).lower()
            if word_clean:
                full_string += word_clean
                word_boxes.append({"text": word_clean, "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3]})

        target_clean = re.sub(r'[^a-zA-Z0-9]', '', text).lower()
        if target_clean and target_clean in full_string:
            start_idx = full_string.find(target_clean)
            end_idx = start_idx + len(target_clean)
            curr_idx = 0
            matched_boxes = []

            for box in word_boxes:
                word_len = len(box["text"])
                if curr_idx < end_idx and (curr_idx + word_len) > start_idx:
                    matched_boxes.append(box)
                curr_idx += word_len

            if matched_boxes:
                x0 = min(b["x0"] for b in matched_boxes)
                y0 = min(b["y0"] for b in matched_boxes)
                x1 = max(b["x1"] for b in matched_boxes)
                y1 = max(b["y1"] for b in matched_boxes)
                return [fitz.Rect(x0, y0, x1, y1).quad]

    if use_ocr:
        try:
            zoom = 4.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("jpeg")))

            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            target_words_list = [re.sub(r'[^a-z0-9]', '', w.lower()) for w in text.split()]
            target_words_list = [w for w in target_words_list if len(w) >= 3]

            if target_words_list:
                for i in range(len(ocr_data['text'])):
                    word = str(ocr_data['text'][i]).lower().strip()
                    word_clean = re.sub(r'[^a-z0-9]', '', word)

                    if len(word_clean) >= 3:
                        for tw in target_words_list:
                            sim_ratio = difflib.SequenceMatcher(None, tw, word_clean).ratio()
                            if sim_ratio >= 0.75 or tw in word_clean or word_clean in tw:
                                px, py = ocr_data['left'][i], ocr_data['top'][i]
                                pw, ph = ocr_data['width'][i], ocr_data['height'][i]
                                pdf_x0, pdf_y0 = px / zoom, py / zoom
                                pdf_x1, pdf_y1 = (px + pw) / zoom, (py + ph) / zoom
                                return [fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1).quad]
        except Exception as e:
            print(f"OCR Fallback Error: {e}")

    return []


# ==========================================
# KOLOM KIRI: KONTROL & FILTER
# ==========================================
col_left, col_right = st.columns([1.2, 2.5], gap="large")

with col_left:
    with st.container(border=True):
        st.markdown("#### 📁 Directory Setup")
        base_dir_input = st.text_input("Local SharePoint Path",
                                       value=r"C:\Users\tgrdi\OneDrive - PT. DAYAMITRA TELEKOMUNIKASI TBK\ASSET_HQ\Result_SES\SDA Done")
        if st.button("🔄 Refresh Folder", use_container_width=True):
            get_all_pdf_paths_cached.clear()
            st.rerun()

    with st.container(border=True):
        st.markdown("#### 📄 Document Type")
        doc_type_label = st.selectbox("Select Target Document Protocol",
                                      ["SDA (Standard Delivery Agreement)", "APD (Approval Design)",
                                       "BOQ (Bill of Quantity)"])
        doc_type = doc_type_label.split(" ")[0].lower()
        use_landscape_settings = (doc_type == "apd")

    with st.container(border=True):
        st.markdown("#### ✍️ Signature Setup")
        signature_file = st.file_uploader("Upload Tanda Tangan (PNG Transparan):", type=["png"])
        anchor_text = st.text_input("Nama / Teks Acuan Posisi TTD", value="DIMAS TEGAR")
        st.number_input("Pilih Target Teks Ke- (Jika nama ganda):", min_value=1, max_value=10, key="anchor_idx")

        st.markdown("---")
        st.checkbox("🔍 Aktifkan Fallback OCR (Jika teks tidak terdeteksi. Proses akan lebih lambat)",
                    key="use_ocr")
        st.checkbox("🎯 Mode Template (Gunakan posisi TTD terakhir yang ditemukan - HANYA Hal 1)",
                    key="use_template_mode")

        if st.session_state.use_template_mode and st.session_state.saved_cx is not None:
            st.success(f"📌 Koordinat template terkunci! (X: {st.session_state.saved_cx:.1f})")

        with st.expander("⚙️ Atur Posisi & Ukuran (Interaktif)", expanded=True):
            st.info(f"💡 Setting: **{'Landscape (APD)' if use_landscape_settings else 'Portrait (SDA/BOQ)'}**")
            tab_port, tab_land = st.tabs(["📄 Portrait", "🖥️ Landscape"])

            with tab_port:
                st.selectbox("Rotasi (Portrait):", [0, 90, 180, 270], key="prot")
                cp1, cp2 = st.columns(2)
                cp1.number_input("Geser X (Kanan/Kiri):", min_value=-1000, max_value=1000, key="px")
                cp2.number_input("Geser Y (Atas/Bawah):", min_value=-1000, max_value=1000, key="py")
                c1, c2 = st.columns(2)
                c1.number_input("Lebar TTD:", key="pw", min_value=10, max_value=800)
                c2.number_input("Tinggi TTD:", key="ph", min_value=10, max_value=800)

            with tab_land:
                st.selectbox("Rotasi (Landscape):", [0, 90, 180, 270], key="lrot")
                cl1, cl2 = st.columns(2)
                cl1.number_input("Geser X (Kanan/Kiri):", min_value=-1000, max_value=1000, key="lx")
                cl2.number_input("Geser Y (Atas/Bawah):", min_value=-1000, max_value=1000, key="ly")
                c3, c4 = st.columns(2)
                c3.number_input("Lebar TTD:", key="lw", min_value=10, max_value=800)
                c4.number_input("Tinggi TTD:", key="lh", min_value=10, max_value=800)

    with st.container(border=True):
        st.markdown("#### 🔍 File Selection")
        tab_search, tab_pid = st.tabs(["Search Filename", "PID List"])

        with tab_search:
            search_query = st.text_input("Cari nama file...").lower()
        with tab_pid:
            site_ids_input = st.text_area("Paste PID List", height=100)
            target_sites = [s.strip().lower() for s in re.split(r'[,\n;\s]+', site_ids_input) if s.strip()]

        filtered_files = []
        is_filter_active = bool(search_query.strip() or target_sites)

        if not is_filter_active:
            st.info("👈 Masukkan **PID** atau **Nama File** pada kolom di atas.")
        else:
            all_cached_paths = get_all_pdf_paths_cached(base_dir_input)
            if target_sites:
                for site in target_sites:
                    for pdf_str in all_cached_paths:
                        pdf_name = os.path.basename(pdf_str).lower()
                        if doc_type not in pdf_name: continue
                        if search_query and search_query not in pdf_name: continue
                        if site in pdf_name:
                            pdf = Path(pdf_str)
                            if pdf not in filtered_files: filtered_files.append(pdf)
            else:
                for pdf_str in all_cached_paths:
                    pdf_name = os.path.basename(pdf_str).lower()
                    if doc_type not in pdf_name: continue
                    if search_query and search_query not in pdf_name: continue
                    filtered_files.append(Path(pdf_str))

            if filtered_files:
                st.success(f"✅ Ditemukan **{len(filtered_files)}** file.")
                for f in filtered_files:
                    if str(f) not in st.session_state: st.session_state[str(f)] = False


                def toggle_select_all():
                    val = st.session_state.select_all_cb
                    for file in filtered_files: st.session_state[str(file)] = val


                st.checkbox("Select All Files", key="select_all_cb", on_change=toggle_select_all)
                with st.container(height=250):
                    for f in filtered_files: st.checkbox(f.name, key=str(f))
            else:
                st.warning("Tidak menemukan file PDF yang cocok.")

    if filtered_files:
        with st.container(border=True):
            st.markdown("#### ☁️ Siapkan Dokumen")
            st.checkbox("⏳ Beri waktu lebih lama? (Internet lambat)", key="slow_internet_cb")
            if st.button("⬇️ Download File Terpilih", width='stretch'):
                sel_dl = [f for f in filtered_files if st.session_state.get(str(f))]
                if sel_dl:
                    prog = st.progress(0, text="Mengunduh...")
                    succ, fail = [], []
                    timeout_limit = 90 if st.session_state.slow_internet_cb else 45
                    for i, f in enumerate(sel_dl):
                        prog.progress(i / len(sel_dl), text=f"Unduh: {f.name}")
                        if ensure_file_downloaded(f, timeout=timeout_limit):
                            succ.append(f)
                        else:
                            fail.append(f)
                    prog.empty()
                    if succ: st.success(f"✅ {len(succ)} file siap diproses.")
                    if fail: st.error(f"❌ {len(fail)} file gagal disiapkan.")
                else:
                    st.warning("Pilih minimal 1 file!")

# ==========================================
# KOLOM KANAN: PREVIEW & RUN
# ==========================================
with col_right:
    if not filtered_files:
        with st.container(border=True):
            st.info("👁️ Preview dokumen akan muncul di sini.")
    else:
        def change_preview(dir_val, max_v):
            if dir_val == "next" and st.session_state.preview_idx < max_v - 1:
                st.session_state.preview_idx += 1
            elif dir_val == "prev" and st.session_state.preview_idx > 0:
                st.session_state.preview_idx -= 1


        if st.session_state.preview_idx >= len(filtered_files): st.session_state.preview_idx = 0
        curr_file = filtered_files[st.session_state.preview_idx]

        c1, c2, c3 = st.columns([1, 1, 3])
        c1.button("⬅️ Prev", width='stretch', on_click=change_preview, args=("prev", len(filtered_files)),
                  disabled=(st.session_state.preview_idx == 0))
        c2.button("Next ➡️", width='stretch', on_click=change_preview, args=("next", len(filtered_files)),
                  disabled=(st.session_state.preview_idx >= len(filtered_files) - 1))

        with c3:
            f_opts = [f"[{i + 1}/{len(filtered_files)}] {f.name}" for i, f in enumerate(filtered_files)]


            def jump_file(): st.session_state.preview_idx = f_opts.index(st.session_state.file_jumper)


            st.selectbox("Lompat ke File", options=f_opts, index=st.session_state.preview_idx, key="file_jumper",
                         on_change=jump_file, label_visibility="collapsed")

        # --- PREVIEW RENDER ---
        try:
            ensure_file_downloaded(curr_file, timeout=45)
            safe_curr_file = get_safe_path(curr_file)
            temp_doc = fitz.open(safe_curr_file)
            is_found_anywhere = False

            with st.container(height=650):
                for page_num in range(len(temp_doc)):
                    page = temp_doc[page_num]

                    shift_x = st.session_state.lx if use_landscape_settings else st.session_state.px
                    shift_y = st.session_state.ly if use_landscape_settings else st.session_state.py
                    w = st.session_state.lw if use_landscape_settings else st.session_state.pw
                    h = st.session_state.lh if use_landscape_settings else st.session_state.ph
                    rot = st.session_state.lrot if use_landscape_settings else st.session_state.prot
                    v_w, v_h = (h, w) if rot in [90, 270] else (w, h)

                    if st.session_state.use_template_mode:
                        if page_num == 0:
                            is_found_anywhere = True
                            base_cx = st.session_state.saved_cx if st.session_state.saved_cx else (page.rect.width / 2)
                            base_cy = st.session_state.saved_cy if st.session_state.saved_cy else (page.rect.height / 2)
                            cx, cy = base_cx + shift_x, base_cy - shift_y

                            target_v_rect = fitz.Rect(cx - v_w / 2, cy - v_h / 2, cx + v_w / 2, cy + v_h / 2)
                            i_rect = target_v_rect * page.derotation_matrix
                            final_img_rot = (rot - page.rotation) % 360

                            page.draw_rect(i_rect, color=(0, 0, 1), fill=(0, 0, 1), fill_opacity=0.2, width=1)
                            if signature_file:
                                rotated_bytes = rotate_image_bytes(signature_file.getvalue(), final_img_rot)
                                page.insert_image(i_rect, stream=rotated_bytes, overlay=True)
                    else:
                        instances = robust_search(page, anchor_text, use_ocr=st.session_state.use_ocr)
                        if instances:
                            is_found_anywhere = True
                            idx = min(st.session_state.anchor_idx - 1, len(instances) - 1)
                            quad = instances[idx]
                            v_rect = (quad * page.rotation_matrix).rect

                            st.session_state.saved_cx = (v_rect.x0 + v_rect.x1) / 2
                            st.session_state.saved_cy = (v_rect.y0 + v_rect.y1) / 2
                            cx = st.session_state.saved_cx + shift_x
                            cy = st.session_state.saved_cy - shift_y

                            target_v_rect = fitz.Rect(cx - v_w / 2, cy - v_h / 2, cx + v_w / 2, cy + v_h / 2)
                            i_rect = target_v_rect * page.derotation_matrix
                            final_img_rot = (rot - page.rotation) % 360

                            page.draw_quad(quad, color=(1, 0, 0), width=1.5)
                            page.draw_rect(i_rect, color=(0, 0, 1), fill=(0, 0, 1), fill_opacity=0.2, width=1)
                            if signature_file:
                                rotated_bytes = rotate_image_bytes(signature_file.getvalue(), final_img_rot)
                                page.insert_image(i_rect, stream=rotated_bytes, overlay=True)

                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    st.image(pix.tobytes("jpeg"), width='stretch')
                    st.markdown("---")
            temp_doc.close()

            if is_found_anywhere:
                if st.session_state.use_template_mode:
                    st.caption("✅ **Mode Template Aktif.** TTD ditempatkan berdasarkan posisi terkunci di Halaman 1.")
                else:
                    st.caption("✅ Teks ditemukan. Geser X (Kiri/Kanan), Geser Y (Atas/Bawah).")
            else:
                if st.session_state.use_template_mode:
                    st.error(
                        "⚠️ Mode Template aktif, tapi koordinat belum terkunci (buka file yang teksnya terdeteksi dulu).")
                else:
                    st.error("⚠️ Nama TIDAK DITEMUKAN. (Pastikan 🔍 Fallback OCR dicentang atau geser manual).")
        except Exception as e:
            st.error(f"Gagal memuat preview: {e}")

    # ==========================================
    # EXECUTION BLOCK (DENGAN EKSTRAKSI PID & REPORTING)
    # ==========================================
    if st.button("🚀 JALANKAN PROSES SIGNING", type="primary", width='stretch'):
        if not signature_file: st.error("Upload TTD dulu!"); st.stop()

        files_to_process = [f for f in filtered_files if st.session_state.get(str(f))]
        if not files_to_process: st.warning("Pilih minimal 1 file!"); st.stop()

        results = []
        count_success = count_skipped = count_failed = 0
        prog_bar = st.progress(0, text="Memulai proses...")
        timeout_limit = 90 if st.session_state.get("slow_internet_cb", False) else 45


        # Fungsi untuk mengekstrak PID dan Tipe Dokumen dari nama file
        def get_file_info(fname):
            pid = "-"
            # 1. Cari berdasarkan PID yang di-paste user
            if target_sites:
                for s in target_sites:
                    if s in fname.lower():
                        pid = s.upper()
                        break
            # 2. Fallback: Cari string yang mirip PID (kombinasi huruf & angka 5-15 karakter)
            if pid == "-":
                clean_name = re.sub(r'\.pdf$', '', fname, flags=re.IGNORECASE)
                m = re.search(r'([A-Z0-9]{5,15})', clean_name.replace("_", "").upper())
                if m: pid = m.group(1)

            dt = doc_type_label.split(" ")[0].upper()  # SDA, APD, BOQ
            return pid, dt


        for i, f in enumerate(files_to_process):
            prog_bar.progress(i / len(files_to_process), text=f"Memproses: {f.name}")

            pid, dt = get_file_info(f.name)

            if not ensure_file_downloaded(f, timeout=timeout_limit):
                count_failed += 1
                results.append({"PID": pid, "Document Type": dt, "Nama File": f.name, "Status": "❌ Gagal",
                                "Keterangan": "Gagal mengunduh file"})
                continue

            try:
                safe_f = get_safe_path(f)
                doc = fitz.open(safe_f)
                found = False

                for page_num in range(len(doc)):
                    page = doc[page_num]

                    shift_x = st.session_state.lx if use_landscape_settings else st.session_state.px
                    shift_y = st.session_state.ly if use_landscape_settings else st.session_state.py
                    w = st.session_state.lw if use_landscape_settings else st.session_state.pw
                    h = st.session_state.lh if use_landscape_settings else st.session_state.ph
                    rot = st.session_state.lrot if use_landscape_settings else st.session_state.prot
                    v_w, v_h = (h, w) if rot in [90, 270] else (w, h)

                    if st.session_state.use_template_mode:
                        if page_num == 0:
                            base_cx = st.session_state.saved_cx if st.session_state.saved_cx else (page.rect.width / 2)
                            base_cy = st.session_state.saved_cy if st.session_state.saved_cy else (page.rect.height / 2)
                            cx, cy = base_cx + shift_x, base_cy - shift_y
                            target_v_rect = fitz.Rect(cx - v_w / 2, cy - v_h / 2, cx + v_w / 2, cy + v_h / 2)
                            i_rect = target_v_rect * page.derotation_matrix
                            final_img_rot = (rot - page.rotation) % 360

                            rotated_bytes = rotate_image_bytes(signature_file.getvalue(), final_img_rot)
                            page.insert_image(i_rect, stream=rotated_bytes, overlay=True)
                            found = True
                    else:
                        instances = robust_search(page, anchor_text, use_ocr=st.session_state.use_ocr)
                        if instances:
                            idx = min(st.session_state.anchor_idx - 1, len(instances) - 1)
                            quad = instances[idx]
                            v_rect = (quad * page.rotation_matrix).rect
                            cx = (v_rect.x0 + v_rect.x1) / 2 + shift_x
                            cy = (v_rect.y0 + v_rect.y1) / 2 - shift_y
                            target_v_rect = fitz.Rect(cx - v_w / 2, cy - v_h / 2, cx + v_w / 2, cy + v_h / 2)
                            i_rect = target_v_rect * page.derotation_matrix
                            final_img_rot = (rot - page.rotation) % 360

                            rotated_bytes = rotate_image_bytes(signature_file.getvalue(), final_img_rot)
                            page.insert_image(i_rect, stream=rotated_bytes, overlay=True)
                            found = True

                if found:
                    temp = f.with_name(f"temp_{f.name}")
                    safe_temp = get_safe_path(temp)
                    doc.save(safe_temp)
                    doc.close()
                    for _ in range(4):
                        try:
                            time.sleep(0.3)
                            os.replace(safe_temp, safe_f)
                            count_success += 1
                            results.append(
                                {"PID": pid, "Document Type": dt, "Nama File": f.name, "Status": "✅ Berhasil",
                                 "Keterangan": "-"})
                            break
                        except Exception:
                            time.sleep(0.5)
                    else:
                        count_failed += 1
                        results.append({"PID": pid, "Document Type": dt, "Nama File": f.name, "Status": "❌ Gagal",
                                        "Keterangan": "Gagal overwrite file"})
                else:
                    count_skipped += 1
                    results.append({"PID": pid, "Document Type": dt, "Nama File": f.name, "Status": "⚠️ Dilewati",
                                    "Keterangan": "Teks tidak terdeteksi"})
                    doc.close()
            except Exception as str_err:
                count_failed += 1
                results.append({"PID": pid, "Document Type": dt, "Nama File": f.name, "Status": "❌ Gagal",
                                "Keterangan": f"Error File: {str(str_err)[:30]}"})

        prog_bar.progress(1.0, text="Selesai!")
        st.session_state.run_summary = {
            "results": results,
            "count_success": count_success,
            "count_skipped": count_skipped,
            "count_failed": count_failed
        }
        get_all_pdf_paths_cached.clear()
        st.rerun()