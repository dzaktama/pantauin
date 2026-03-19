import os
import json
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_INSTRUCTION = """
Kamu adalah asisten keuangan khusus untuk UMKM Indonesia bernama PANTAUIN.
Kamu HANYA boleh menjawab pertanyaan yang berkaitan dengan:
- Keuangan bisnis (pemasukan, pengeluaran, laba, arus kas)
- Manajemen stok dan produk
- Strategi penjualan dan promosi UMKM
- Analisis laporan keuangan sederhana
- Saran operasional untuk usaha kecil/menengah

Jika pengguna bertanya di luar topik tersebut (misalnya politik, hiburan, teknologi umum, dll),
tolak dengan sopan dan arahkan kembali ke topik bisnis UMKM.
Gunakan Bahasa Indonesia yang ramah dan mudah dipahami pedagang atau pemilik warung.
"""

GROQ_MODEL = "llama-3.3-70b-versatile"

# Inisialisasi Groq (chat & analisis)
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq berhasil diinisialisasi")
except Exception as e:
    print(f"❌ Gagal inisialisasi Groq: {e}")
    groq_client = None

# Inisialisasi Gemini (khusus vision/scan struk)
try:
    genai.configure(api_key=GROQ_API_KEY)
    gemini_vision = genai.GenerativeModel("gemini-1.5-flash")
    print("✅ Gemini Vision berhasil diinisialisasi")
except Exception as e:
    print(f"❌ Gagal inisialisasi Gemini Vision: {e}")
    gemini_vision = None


def _chat(prompt: str, max_tokens: int = 512) -> str:
    """Helper internal: kirim prompt ke Groq."""
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
            teks_keluar = "\n\n".join(teks_keluar.split('. ', 3))
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
        print("⚠️ Gemini Vision tidak tersedia.")
        return None
    try:
        prompt_vision = '''
Baca struk belanja ini dan temukan barang yang terjual.
Kalau ada banyak barang, pilih satu produk utama yang paling merepresentasikan transaksi ini
atau gabungkan namanya secara padat (maks 100 karakter).
Keluarkan data persis dengan format JSON murni ini saja, jangan ada teks pembuka atau penutup:
{
    "nama_produk": "nama barang",
    "kuantitas": jumlah angka total barang (integer),
    "pemasukan": total harga akhir rupiah di struk (float),
    "kategori": "Makanan & Minuman"
}
Pilihan kategori: Makanan & Minuman, Retail, Jasa, atau Lainnya.
        '''
        vision_part = {"mime_type": "image/jpeg", "data": image_bytes}
        response = gemini_vision.generate_content([prompt_vision, vision_part])
        hasil_teks = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(hasil_teks)
    except Exception as e:
        print(f"❌ Gagal ekstrak struk vision: {e}")
        return None