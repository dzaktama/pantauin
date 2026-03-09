import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Inisialisasi Model AI dengan penanganan error jika tidak ada kunci
try:
    if API_KEY and API_KEY != "AIzaSyDQFy1EZ_rfylTE-ke1cP0BQlugvAKIyzs":
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
    else:
        model = None
except Exception as e:
    model = None

def get_dashboard_suggestion(health_score, total_income, total_expense, trend_status, catatan_mingguan=None):
    """
    Menghasilkan saran tingkat dashboard berdasarkan kondisi bisnis ringkas.
    Menggunakan Gemini 1.5 Flash. Memiliki perlindungan fallback teks statis.
    """
    if not model:
        # Fallback statis ISO 25010 (Reliability)
        return "Pertahankan pencatatan rutin. Cek grafik tren untuk memantau waktu penjualan terbaikmu minggu ini."
        
    try:
        catatan_text = ""
        if catatan_mingguan:
            catatan_text = "Catatan 7 hari terakhir: " + ", ".join(catatan_mingguan) + "\n"
        prompt = f"""
        Anda adalah asisten keuangan UMKM Indonesia yang bijaksana dan ramah.
        Kondisi bisnis minggu ini:
        - Skor Kesehatan (0-100): {health_score}
        - Pemasukan: Rp {total_income}
        - Pengeluaran: Rp {total_expense}
        - Tren Penjualan: {trend_status}
        {catatan_text}
        Berikan saran tindakan nyata dalam MAKSIMAL 3 KALIMAT singkat untuk pedagang atau pemilik warung. 
        Jangan beri sambutan, langsung pada poin saran. Gunakan Bahasa Indonesia informal namun sopan.
        """
        response = model.generate_content(prompt)
        return response.text.replace('*', '').strip()
    except Exception as e:
        return "Server AI sedang sibuk. Fokus menjaga agar pengeluaran tidak lebih besar dari pemasukan hari ini."

def get_chatbot_response(user_message, context_data):
    """
    Menjawab pertanyaan spesifik dari user melalui widget chatbot.
    """
    if not model:
        return "Halo! Chatbot AI saat ini belum aktif (API tidak tersedia). Tetap semangat berjualan ya!"
        
    try:
        prompt = f"""
        Konteks Bisnis Pengguna:
        Skor saat ini: {context_data.get('skor', 0)}
        Pemasukan rata-rata harian: Rp {context_data.get('rata_pemasukan', 0)}
        Pengeluaran rata-rata harian: Rp {context_data.get('rata_pengeluaran', 0)}
        Peringatan aktif: {', '.join(context_data.get('peringatan', [])) if context_data.get('peringatan') else 'Tidak ada'}
        
        Pertanyaan Pengguna: "{user_message}"
        
        Anda adalah AI Asisten PANTAUIN. Jawab dalam 2-4 kalimat sederhana. Berbicaralah seolah kepada pemilik UMKM secara personal. Jangan gunakan istilah rumit.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Maaf, sistem AI lambat merespons. Bisa tanyakan kembali nanti ya."

def format_rp(nilai):
    return f"{int(nilai):,}".replace(",", ".")

def get_pdf_narration(nama_bisnis, skor, label_skor, total_pemasukan, total_pengeluaran_ops, saldo_bersih, avg_harian_masuk, gross_margin, tren_penjualan, stabilitas, rasio_pengeluaran, konsistensi, peringatan_list, proyeksi_pemasukan, proyeksi_saldo):
    """
    Membuat analisis empat paragraf untuk PDF berdasarkan instruksi konsultan UMKM.
    """
    if not model:
        return "Capaian bulan ini sudah tercatat. Terus perhatikan tren perbandingan pemasukan dan pengeluaran Anda.\nFokuslah pada pencatatan harian yang konsisten untuk analisis yang lebih baik.\nManajemen arus kas yang ketat akan memuluskan langkah bisnis.\nSimpan sebagian laba sebagai dana darurat setidaknya 2 minggu operasional."

    try:
        peringatan_str = ", ".join(peringatan_list) if peringatan_list else "Tidak ada"
        prompt = f"""
        Kamu adalah konsultan bisnis berpengalaman yang sedang menulis laporan untuk pemilik UMKM bernama "{nama_bisnis}".

        Data bisnis mereka 30 hari terakhir:
        - Business Health Score: {skor}/100 ({label_skor})
        - Total pemasukan: Rp {format_rp(total_pemasukan)}
        - Total pengeluaran operasional: Rp {format_rp(total_pengeluaran_ops)}
        - Saldo bersih: Rp {format_rp(saldo_bersih)}
        - Rata-rata pemasukan harian: Rp {format_rp(avg_harian_masuk)}
        - Gross margin rata-rata: {gross_margin:.1f}%
        - Tren penjualan (indikator 0-100): {tren_penjualan}
        - Stabilitas cashflow (indikator 0-100): {stabilitas}
        - Rasio pengeluaran operasional: {rasio_pengeluaran:.1f}%
        - Konsistensi pemasukan: {konsistensi}
        - Peringatan aktif: {peringatan_str}
        - Proyeksi pemasukan 4 minggu ke depan: Rp {format_rp(proyeksi_pemasukan)}
        - Proyeksi saldo 4 minggu ke depan: Rp {format_rp(proyeksi_saldo)}

        Tulis analisis dalam TEPAT 4 paragraf pendek, masing-masing 3-4 kalimat. Gunakan bahasa yang mudah dipahami pemilik warung atau pedagang pasar — hindari istilah keuangan yang terlalu teknis. Sebut nama bisnis "{nama_bisnis}" minimal sekali. Sebut angka spesifik dari data di atas.

        Paragraf 1 — KONDISI SAAT INI: Jelaskan kondisi bisnis secara keseluruhan. Sebutkan skor dan apa artinya. Sebutkan angka pemasukan dan gross margin.

        Paragraf 2 — YANG SUDAH BAGUS: Sebutkan 1-2 indikator dengan nilai terbaik dan jelaskan kenapa itu penting untuk bisnis.

        Paragraf 3 — YANG PERLU DIPERBAIKI: Sebutkan 1-2 indikator dengan nilai terendah. Jelaskan risiko konkretnya jika dibiarkan. Sebut angka spesifik.

        Paragraf 4 — LANGKAH SELANJUTNYA: Berikan 2-3 tindakan konkret yang bisa dilakukan minggu ini. Spesifik dan actionable, bukan saran umum.

        Jangan gunakan bullet point. Tulis dalam paragraf mengalir. Maksimal 250 kata total.
        """
        response = model.generate_content(prompt)
        teks_keluar = response.text.replace('*', '').strip()
        
        # Fallback split
        if teks_keluar.count("\n\n") < 3:
             teks_keluar = "\n\n".join(teks_keluar.split('. ', 3))
        return teks_keluar
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "Pendapatan dan pengeluaran tampaknya sudah mulai terekam dengan baik.\nTetap konsisten dalam pencatatan transaksi masuk dan keluar.\nMeskipun begitu, Anda dihimbau memeriksa saldo kas riil mingguan agar tidak kecolongan.\nSimpan sebagian laba sebagai dana darurat rutinitas."
