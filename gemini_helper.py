import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

# Inisialisasi Model AI dengan penanganan error jika tidak ada kunci
try:
    if API_KEY and API_KEY != "AIzaSyDQFy1EZ_rfylTE-ke1cP0BQlugvAKIyzs":
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
    else:
        model = None
except Exception as e:
    model = None

def get_dashboard_suggestion(health_score, total_income, total_expense, trend_status, catatan_mingguan=None, data_produk=None, advanced_analytics=None):
    """
    bikin saran untuk dashboard yang bahas strategi bisnis dan stok produk
    """
    if not model:
        # Fallback statis ISO 25010 (Reliability)
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
            
            adv_text += f"\nData Lanjutan (PENTING):\n"
            if cc:
                adv_text += f"- Produk Cash Cow (Margin Kotor Tertinggi): {cc.get('nama')} dengan total margin Rp{format_rp(cc.get('margin_kotor', 0))}\n"
            if restok:
                r_list = [f"{r.get('nama')} (Rp{format_rp(r.get('estimasi_dana', 0))})" for r in restok]
                adv_text += f"- Prediksi Siap Dana Restok (Kenaikan >20%): {', '.join(r_list)}\n"
            if sentimen:
                s_list = [s.get('keyword') for s in sentimen]
                adv_text += f"- Pola Sentimen/Catatan: Muncul kata {', '.join(s_list)} yang berkorelasi dengan naik turunnya performa.\n"

        prompt = f"""
        Anda adalah asisten keuangan UMKM Indonesia yang bijaksana dan ramah.
        Kondisi bisnis minggu ini:
        - Skor Kesehatan (0-100): {health_score}
        - Pemasukan: Rp {total_income}
        - Pengeluaran: Rp {total_expense}
        - Tren Penjualan: {trend_status}
        {catatan_text}
        {data_produk_text}
        {adv_text}
        Berikan saran tindakan nyata dalam MAKSIMAL 3 KALIMAT singkat untuk pedagang atau pemilik warung. 
        Berikan saran strategis berdasarkan data lanjutan tersebut secara spesifik (contoh: "Siapkan dana RpXYZ untuk restok produk A" atau "Fokus jualan produk B karena untungnya paling besar").
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

def get_pdf_narration(nama_bisnis, skor, label_skor, total_pemasukan, total_pengeluaran_ops, saldo_bersih, avg_harian_masuk, gross_margin, tren_penjualan, stabilitas, rasio_pengeluaran, konsistensi, peringatan_list, proyeksi_pemasukan, proyeksi_saldo, data_produk=None, advanced_analytics=None):
    """
    bikin narasi laporan pdf yang memuat angka performa dan rekomendasi taktis tentang produk
    """
    if not model:
        return "Capaian bulan ini sudah tercatat. Terus perhatikan tren perbandingan pemasukan dan pengeluaran Anda.\nFokuslah pada pencatatan harian yang konsisten untuk analisis yang lebih baik.\nManajemen arus kas yang ketat akan memuluskan langkah bisnis.\nSimpan sebagian laba sebagai dana darurat setidaknya 2 minggu operasional."

    try:
        peringatan_str = ", ".join(peringatan_list) if peringatan_list else "Tidak ada"
        
        data_produk_text = ""
        if data_produk:
            top_3 = ", ".join([f"{p['nama']} ({p['total']} terjual)" for p in data_produk.get('top_3_terlaris', [])])
            bottom_3 = ", ".join([f"{p['nama']} ({p['total']} terjual)" for p in data_produk.get('bottom_3_menurun', [])])
            if top_3 or bottom_3:
                data_produk_text = f"Data Produk Terlaris: {top_3}. Produk Kurang Laris (Dead Stock): {bottom_3}."

        adv_text = ""
        if advanced_analytics:
            cc = advanced_analytics.get('cash_cow', {})
            restok = advanced_analytics.get('prediksi_restok', [])
            sentimen = advanced_analytics.get('korelasi_catatan', [])
            if cc:
                adv_text += f"\n- Cash Cow Margin Utama: {cc.get('nama')}"
            if restok:
                r_list = [str(r.get('nama')) for r in restok]
                adv_text += f"\n- Alarm Restok Mendesak: {', '.join(r_list)}"
            if sentimen:
                s_list = [str(s.get('keyword')) for s in sentimen]
                adv_text += f"\n- Sentimen Pasar: {', '.join(s_list)}"

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
        - Catatan Performa Produk: {data_produk_text} {adv_text}

        Tulis analisis dalam TEPAT 4 paragraf pendek, masing-masing 3-4 kalimat. Gunakan bahasa yang mudah dipahami pemilik warung atau pedagang pasar — hindari istilah keuangan yang terlalu teknis. Sebut nama bisnis "{nama_bisnis}" minimal sekali. Sebut angka spesifik dari data di atas.

        Paragraf 1 — KONDISI SAAT INI: Jelaskan kondisi bisnis secara keseluruhan. Sebutkan skor dan apa artinya. Sebutkan angka pemasukan dan gross margin.

        Paragraf 2 — YANG SUDAH BAGUS: Sebutkan 1-2 indikator dengan nilai terbaik dan jelaskan kenapa itu penting untuk bisnis.

        Paragraf 3 — YANG PERLU DIPERBAIKI: Sebutkan 1-2 indikator dengan nilai terendah. Jelaskan risiko konkretnya jika dibiarkan. Sebut angka spesifik.

        Paragraf 4 — LANGKAH SELANJUTNYA: Berikan tindakan konkret yang bisa dilakukan minggu ini berkaitan dengan nama-nama produk yang laku dan yang tidak laku berdasarkan Catatan Performa Produk di atas. Beri rekomendasi taktis (misal penyesuaian stok, bundel promosi, dll) yang menyebut langsung nama produk tersebut.

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

def ekstrak_struk_vision(image_bytes):
    """
    baca foto struk dan ekstrak isinya ke format json
    """
    if not model:
        return None
        
    try:
        prompt_vision = '''
        baca struk belanja ini dan temukan barang yang terjual.
        kalau ada banyak barang, pilih satu produk utama yang paling merepresentasikan transaksi ini atau gabungkan namanya secara padat (maks 100 karakter).
        keluarkan data persis dengan format JSON murni ini saja, jangan ada teks pembuka atau penutup:
        {
            "nama_produk": "nama barang",
            "kuantitas": jumlah angka total barang (integer),
            "pemasukan": total harga akhir rupiah di struk (float),
            "kategori": "Makanan & Minuman" // pilih salah satu yang paling masuk akal: Makanan & Minuman, Retail, Jasa, atau Lainnya
        }
        '''
        
        vision_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }
        
        response = model.generate_content([prompt_vision, vision_part])
        hasil_teks = response.text.replace("```json", "").replace("```", "").strip()
        import json
        return json.loads(hasil_teks)
    except Exception as e:
        print(f"gagal ekstrak visi: {e}")
        return None
