import os
import json
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

SYSTEM_INSTRUCTION = """
Kamu adalah asisten keuangan khusus untuk UMKM Indonesia bernama PANTAUIN.
Kamu HANYA boleh menjawab pertanyaan yang berkaitan dengan:
- Keuangan bisnis (pemasukan, pengeluaran, laba, arus kas)
- Manajemen stok dan produk
- Strategi penjualan dan promosi UMKM
- Analisis laporan keuangan sederhana
- Saran operasional untuk usaha kecil/menengah

Jika pengguna meminta saran strategi, analisis risiko, atau rekomendasi taktis bisnis, kamu WAJIB menyajikannya dalam format Tabel Markdown yang rapi. Gunakan struktur tabel: Kolom 1 (Area Fokus / Masalah), Kolom 2 (Kondisi Saat Ini), Kolom 3 (Solusi Taktis / Tindakan).
Jika obrolan hanya berupa sapaan atau tanya jawab ringan, jawab dengan teks biasa.

Gunakan bahasa Indonesia yang santai sehari-hari ala ngobrol bareng partner bisnis. HINDARI bahasa kaku atau baku.
"""

GROQ_MODEL = "llama-3.3-70b-versatile"

# Inisialisasi Groq (chat & analisis)
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("Groq berhasil diinisialisasi")
    except Exception as e:
        print(f"❌ Gagal inisialisasi Groq: {e}")
        groq_client = None
else:
    print(" GROQ_API_KEY tidak ditemukan di .env, fitur AI chat dinonaktifkan.")
    groq_client = None

# Inisialisasi Gemini (khusus vision/scan struk)
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_vision = genai.GenerativeModel("gemini-1.5-flash")
        print("Gemini Vision berhasil diinisialisasi")
    except Exception as e:
        print(f"Gagal inisialisasi Gemini Vision: {e}")
        gemini_vision = None
else:
    print(" GOOGLE_API_KEY tidak ditemukan di .env, fitur scan struk dinonaktifkan.")
    gemini_vision = None


def _chat(prompt: str, max_tokens: int = 512) -> str:
    """Helper internal: kirim prompt ke Groq."""
    if not groq_client:
        return "Fitur AI belum tersedia. Pastikan GROQ_API_KEY sudah dikonfigurasi di file .env."
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_str = str(e)
        if '401' in error_str or 'invalid_api_key' in error_str or 'Invalid API Key' in error_str:
            return "API Key Groq tidak valid atau sudah kadaluarsa. Silakan perbarui GROQ_API_KEY di file .env."
        raise


def format_rp(nilai):
    return f"{int(nilai):,}".replace(",", ".")


def get_dashboard_suggestion(health_score, total_income, total_expense, trend_status,
                              catatan_mingguan=None, data_produk=None, advanced_analytics=None):
    if not groq_client:
        return "Pertahankan pencatatan rutin. Cek grafik tren untuk memantau waktu penjualan terbaikmu minggu ini."
    try:
        catatan_text = ""
        if catatan_mingguan:
            catatan_text = "Catatan 7 hari terakhir: " + ", ".join(catatan_mingguan) + "\n"

        data_produk_text = ""
        if data_produk:
            top_3 = ", ".join([f"{p['nama']} ({p['total']} terjual)" for p in data_produk.get('top_3_terlaris', [])])
            bottom_3 = ", ".join([f"{p['nama']} ({p['total']} terjual)" for p in data_produk.get('bottom_3_menurun', [])])
            if top_3 or bottom_3:
                data_produk_text = f"Data Produk Terlaris: {top_3}. Produk Kurang Laris (Dead Stock): {bottom_3}.\n"

        adv_text = ""
        if advanced_analytics:
            cc = advanced_analytics.get('cash_cow', {})
            restok = advanced_analytics.get('prediksi_restok', [])
            sentimen = advanced_analytics.get('korelasi_catatan', [])
            adv_text += "\nData Lanjutan (PENTING):\n"
            if cc:
                adv_text += f"- Produk Cash Cow: {cc.get('nama')} margin Rp{format_rp(cc.get('margin_kotor', 0))}\n"
            if restok:
                r_list = [f"{r.get('nama')} (Rp{format_rp(r.get('estimasi_dana', 0))})" for r in restok]
                adv_text += f"- Prediksi Restok: {', '.join(r_list)}\n"
            if sentimen:
                s_list = [s.get('keyword') for s in sentimen]
                adv_text += f"- Pola Sentimen: {', '.join(s_list)}\n"

        prompt = f"""
Kondisi bisnis minggu ini:
- Skor Kesehatan (0-100): {health_score}
- Pemasukan: Rp {total_income}
- Pengeluaran: Rp {total_expense}
- Tren Penjualan: {trend_status}
{catatan_text}{data_produk_text}{adv_text}
Berikan saran tindakan nyata dalam MAKSIMAL 3 KALIMAT singkat untuk pedagang atau pemilik warung.
Jangan beri sambutan, langsung pada poin saran. Gunakan Bahasa Indonesia informal namun sopan.
        """
        return _chat(prompt, max_tokens=256)
    except Exception as e:
        return "Server AI sedang sibuk. Fokus menjaga agar pengeluaran tidak lebih besar dari pemasukan hari ini."


def get_chatbot_response(user_message, context_data):
    if not groq_client:
        return "Halo! Chatbot AI saat ini belum aktif. Tetap semangat berjualan ya!"
    try:
        prompt = f"""
Konteks Bisnis Pengguna:
- Skor saat ini: {context_data.get('skor', 0)}
- Pemasukan rata-rata harian: Rp {context_data.get('rata_pemasukan', 0)}
- Pengeluaran rata-rata harian: Rp {context_data.get('rata_pengeluaran', 0)}
- Peringatan aktif: {', '.join(context_data.get('peringatan', [])) if context_data.get('peringatan') else 'Tidak ada'}

Pertanyaan Pengguna: "{user_message}"

Jawab dalam 2-4 kalimat sederhana sesuai konteks bisnis pengguna.
Jika pertanyaan tidak berkaitan dengan bisnis atau keuangan UMKM, tolak sopan dan arahkan balik.
        """
        return _chat(prompt, max_tokens=256)
    except Exception as e:
        return "Maaf, sistem AI lambat merespons. Bisa tanyakan kembali nanti ya."


def get_pdf_narration(nama_bisnis, skor, label_skor, total_pemasukan, total_pengeluaran_ops,
                      saldo_bersih, avg_harian_masuk, gross_margin, tren_penjualan, stabilitas,
                      rasio_pengeluaran, konsistensi, peringatan_list, proyeksi_pemasukan,
                      proyeksi_saldo, data_produk=None, advanced_analytics=None):
    if not groq_client:
        return ("Capaian bulan ini sudah tercatat. Terus perhatikan tren perbandingan pemasukan dan pengeluaran Anda.\n"
                "Fokuslah pada pencatatan harian yang konsisten untuk analisis yang lebih baik.\n"
                "Manajemen arus kas yang ketat akan memuluskan langkah bisnis.\n"
                "Simpan sebagian laba sebagai dana darurat setidaknya 2 minggu operasional.")
    try:
        peringatan_str = ", ".join(peringatan_list) if peringatan_list else "Tidak ada"

        data_produk_text = ""
        if data_produk:
            top_3 = ", ".join([f"{p['nama']} ({p['total']} terjual)" for p in data_produk.get('top_3_terlaris', [])])
            bottom_3 = ", ".join([f"{p['nama']} ({p['total']} terjual)" for p in data_produk.get('bottom_3_menurun', [])])
            if top_3 or bottom_3:
                data_produk_text = f"Terlaris: {top_3}. Dead Stock: {bottom_3}."

        adv_text = ""
        if advanced_analytics:
            cc = advanced_analytics.get('cash_cow', {})
            restok = advanced_analytics.get('prediksi_restok', [])
            sentimen = advanced_analytics.get('korelasi_catatan', [])
            if cc:
                adv_text += f"\n- Cash Cow: {cc.get('nama')}"
            if restok:
                adv_text += f"\n- Restok Mendesak: {', '.join([str(r.get('nama')) for r in restok])}"
            if sentimen:
                adv_text += f"\n- Sentimen: {', '.join([str(s.get('keyword')) for s in sentimen])}"

        prompt = f"""
Tulis laporan bisnis untuk pemilik UMKM "{nama_bisnis}" dalam TEPAT 4 paragraf pendek (3-4 kalimat per paragraf).

Data 30 hari terakhir:
- Health Score: {skor}/100 ({label_skor})
- Total pemasukan: Rp {format_rp(total_pemasukan)}
- Total pengeluaran: Rp {format_rp(total_pengeluaran_ops)}
- Saldo bersih: Rp {format_rp(saldo_bersih)}
- Rata-rata harian: Rp {format_rp(avg_harian_masuk)}
- Gross margin: {gross_margin:.1f}%
- Tren penjualan: {tren_penjualan}
- Stabilitas cashflow: {stabilitas}
- Rasio pengeluaran: {rasio_pengeluaran:.1f}%
- Konsistensi: {konsistensi}
- Peringatan: {peringatan_str}
- Proyeksi pemasukan 4 minggu: Rp {format_rp(proyeksi_pemasukan)}
- Proyeksi saldo 4 minggu: Rp {format_rp(proyeksi_saldo)}
- Performa Produk: {data_produk_text} {adv_text}

Paragraf 1 — KONDISI SAAT INI
Paragraf 2 — YANG SUDAH BAGUS
Paragraf 3 — YANG PERLU DIPERBAIKI
Paragraf 4 — LANGKAH SELANJUTNYA (sebut nama produk spesifik)

Bahasa sederhana, jangan bullet point, maksimal 250 kata.
        """
        teks_keluar = _chat(prompt, max_tokens=600)
        teks_keluar = teks_keluar.replace('*', '').strip()
        if teks_keluar.count("\n\n") < 3:
            # potong teks pakai spasi baris biar singkatan berakhiran titik aman
            kalimat = teks_keluar.split('\n')
            kalimat = [k.strip() for k in kalimat if k.strip()]
            chunks = []
            for k in kalimat:
                if len(chunks) < 4:
                    chunks.append(k)
                else:
                    chunks[-1] += ' ' + k
            teks_keluar = "\n\n".join(chunks)
        return teks_keluar
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ("Pendapatan dan pengeluaran tampaknya sudah mulai terekam dengan baik.\n"
                "Tetap konsisten dalam pencatatan transaksi masuk dan keluar.\n"
                "Periksa saldo kas riil mingguan agar tidak kecolongan.\n"
                "Simpan sebagian laba sebagai dana darurat rutinitas.")


def ekstrak_struk_vision(image_bytes):
    """Baca foto struk pakai Gemini Vision dan ekstrak ke format JSON."""
    if not gemini_vision:
        print(" Gemini Vision tidak tersedia.")
        return None
    try:
        prompt_vision = '''
Ekstrak informasi dari struk atau nota ini untuk form pencatatan penjualan UMKM.
Kalau ada banyak barang, gabungkan nama-namanya secara singkat (maks 100 karakter), atau pilih satu yang paling mewakili.
Keluarkan data HANYA dalam format JSON murni persis dengan struktur ini, tanpa markdown ```json atau teks lainnya:
{
    "tanggal": "tanggal di struk jika ada dalam format YYYY-MM-DD",
    "nama_produk": "nama barang",
    "kuantitas": jumlah total item kuantitas barang (integer),
    "pemasukan": total harga akhir rupiah (float, contoh 48000),
    "kategori": "Pilih salah satu: Makanan & Minuman, Retail, Jasa, atau Lainnya",
    "catatan": "keterangan tambahan seperti nama toko, nama kasir, atau pelanggan (maksimal 150 karakter)"
}
'''
        vision_part = {"mime_type": "image/jpeg", "data": image_bytes}
        response = gemini_vision.generate_content([prompt_vision, vision_part])
        
        import re
        raw = response.text
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            # jaga-jaga kalau gemini ngga ngerespon format json sama sekali
            return None
        return json.loads(match.group())
    except Exception as e:
        print(f"Gagal ekstrak struk vision: {e}")
        return None

def get_simulator_chat_response(pesan_user, data):
    # buat nanggepin chat lanjutan dari user soal risiko bisnis
    if not groq_client:
        return "maaf ya, sistem ai nya belum aktif karena kuncinya belum dipasang"
    try:
        penjualan_val = float(data.get('penurunan', 0))
        hpp_val = float(data.get('hpp_naik', 0))
        opex_val = float(data.get('opex_naik', 0))
        
        str_penj = f"Naik {penjualan_val}%" if penjualan_val > 0 else (f"Turun {abs(penjualan_val)}%" if penjualan_val < 0 else "Tetap")
        str_hpp = f"Naik {hpp_val}%" if hpp_val > 0 else (f"Turun {abs(hpp_val)}%" if hpp_val < 0 else "Tetap")
        str_opex = f"Naik {opex_val}%" if opex_val > 0 else (f"Turun {abs(opex_val)}%" if opex_val < 0 else "Tetap")
        
        jenis_skenario = "Kritis/Resesi" if penjualan_val < 0 or hpp_val > 0 or opex_val > 0 else "Pertumbuhan Ekspansif"

        prompt = f"""
Jawab pertanyaan lanjutan dari user ini berdasarkan hasil simulasi proyeksi bisnis ({jenis_skenario}) berikut:
- Konfigurasi Simulasi: Penjualan {str_penj}, HPP {str_hpp}, Opex {str_opex}
- Pemasukan Baru Proyeksi: Rp {format_rp(data.get('data', {}).get('pemasukan_baru', 0))}
- Pengeluaran Baru Proyeksi: Rp {format_rp(data.get('data', {}).get('pengeluaran_baru', 0))}
- Saldo Laba Bersih Baru: Rp {format_rp(data.get('data', {}).get('saldo_baru', 0))}
- Status Bisnis: {data.get('data', {}).get('status_bisnis', '-')}
- Gross Margin: {data.get('data', {}).get('gross_margin', 0)}%
- Ketahanan Kas Riil: {data.get('data', {}).get('hari_bertahan', 0)} hari

Pertanyaan user: "{pesan_user}"

PENTING: Jika pengguna meminta saran atau strategi operasional lanjutan, sajikan dalam format Tabel Markdown dengan 3 kolom: Area Fokus, Kondisi Saat Ini, dan Solusi Taktis. Jika simulasi berstatus Pertumbuhan Ekspansif, berikan solusi manajemen kapasitas, investasi, dan kelola operasional tambahan, bukan mode bertahan hidup.
        """
        return _chat(prompt, max_tokens=600)
    except Exception as e:
        return "aduh server lagi pusing ngeproses pertanyaannya, sabar sebentar ya"