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

def get_pdf_narration(score, avg_income, avg_expense, warnings, catatan_mingguan=None):
    """
    Membuat satu paragraf ulasan bulan ini untuk ditaruh di laporan PDF.
    """
    if not model:
        return "Capaian bulan ini sudah tercatat. Terus perhatikan tren perbandingan pemasukan dan pengeluaran Anda agar usaha selalu mencetak keuntungan bersih."

    try:
        str_warnings = ", ".join(warnings) if warnings else "Kondisi stabil, tidak ada peringatan kritis."
        catatan_text = ""
        if catatan_mingguan:
            catatan_text = "Catatan 7 hari terakhir: " + ", ".join(catatan_mingguan) + "\n"
        prompt = f"""
        Buat narasi evaluasi bisnis bulan ini dalam 1 paragraf (sekitar 40 kata). 
        Data: Skor: {score}. Rata-rata Masuk: Rp {avg_income}. Rata-rata Keluar: Rp {avg_expense}. Peringatan: {str_warnings}.
        {catatan_text}
        Ditujukan untuk dicetak di laporan PDF resmi UMKM. Nada bahasa: Memotivasi, profesional namun merakyat.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Capaian penjualan yang baik membutuhkan kehati-hatian dalam pengontrolan arus kas. Evaluasi berkala sangat dianjurkan untuk keberlangsungan usaha Anda."
