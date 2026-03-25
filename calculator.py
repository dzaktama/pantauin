import numpy as np
import pandas as pd
from datetime import timedelta, date
from collections import defaultdict

# KONSTANTA BOBOT BUSINESS HEALTH SCORE
BOBOT_STABILITAS = 0.25
BOBOT_TREN = 0.25
BOBOT_RASIO_OP = 0.20
BOBOT_GROSS_MARGIN = 0.20
BOBOT_KONSISTENSI = 0.10

# AMBANG BATAS PESAN
THRESHOLD_WARNING_RASIO_PENGELUARAN = 0.8  # Jika pengeluaran operasional >= 80% pemasukan

def get_operational_expense(user_id, days):
    """Mendapatkan total pengeluaran operasional n hari terakhir."""
    from models import Transaksi
    sekarang = date.today()
    start_date = sekarang - timedelta(days=days)
    transaksi_list = Transaksi.query.filter(Transaksi.user_id == user_id, Transaksi.tanggal >= start_date).all()
    return sum(t.pengeluaran for t in transaksi_list if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional')

def get_capital_expense(user_id, days):
    """Mendapatkan total pengeluaran modal n hari terakhir."""
    from models import Transaksi
    sekarang = date.today()
    start_date = sekarang - timedelta(days=days)
    transaksi_list = Transaksi.query.filter(Transaksi.user_id == user_id, Transaksi.tanggal >= start_date).all()
    return sum(t.pengeluaran for t in transaksi_list if getattr(t, 'jenis_pengeluaran', 'operasional') == 'modal')

def periksa_kecukupan_data(transaksi_list):
    """Mengecek minimal data 14 hari transaksi unik tersedia (Reliability)."""
    if not transaksi_list:
        return False
    tanggal_unik = {t.tanggal for t in transaksi_list}
    return len(tanggal_unik) >= 14

def _agregasi_per_hari(transaksi_list):
    """Mengelompokkan transaksi menjadi harian."""
    harian = defaultdict(lambda: {'pemasukan': 0.0, 'pengeluaran_op': 0.0, 'pengeluaran_md': 0.0})
    for t in transaksi_list:
        harian[t.tanggal]['pemasukan'] += t.pemasukan
        if getattr(t, 'jenis_pengeluaran', 'operasional') == 'modal':
            harian[t.tanggal]['pengeluaran_md'] += t.pengeluaran
        else:
            harian[t.tanggal]['pengeluaran_op'] += t.pengeluaran
    
    # Sorting berdasarkan tanggal ascending
    sorted_dates = sorted(harian.keys())
    return {d: harian[d] for d in sorted_dates}

def hitung_health_score(transaksi_list, periode_grafik=30):
    """
    Fungsi utama perhitungan Business Health Score dan proyeksi linear.
    Semua logika diisolasi di sini. Dibungkus try-except di pemanggil `app.py`.
    """
    if not periksa_kecukupan_data(transaksi_list):
        return _fallback_empty_data(periode_grafik)

    # Hitung data mingguan terakhir (7 hari) vs minggu sebelumnya
    sekarang = date.today()
    minggu_ini = [t for t in transaksi_list if (sekarang - t.tanggal).days <= 7]
    minggu_lalu = [t for t in transaksi_list if 7 < (sekarang - t.tanggal).days <= 14]

    in_minggu_ini = sum((t.pemasukan for t in minggu_ini), 0)
    out_op_minggu_ini = sum((t.pengeluaran for t in minggu_ini if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional'), 0)
    out_md_minggu_ini = sum((t.pengeluaran for t in minggu_ini if getattr(t, 'jenis_pengeluaran', 'operasional') == 'modal'), 0)
    
    out_minggu_ini = out_op_minggu_ini + out_md_minggu_ini
    in_minggu_lalu = sum((t.pemasukan for t in minggu_lalu), 0)
    
    # Kebutuhan Rule Penurunan Beruntun (Minggu ke-3 / minggu_lalu_2)
    minggu_lalu_2 = [t for t in transaksi_list if 14 < (sekarang - t.tanggal).days <= 21]
    in_minggu_lalu_2 = sum((t.pemasukan for t in minggu_lalu_2), 0)
    out_minggu_lalu_2 = sum((t.pengeluaran for t in minggu_lalu_2), 0)
    out_op_minggu_lalu_2 = sum((t.pengeluaran for t in minggu_lalu_2 if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional'), 0)
    
    minggu_lalu_3 = [t for t in transaksi_list if 21 < (sekarang - t.tanggal).days <= 28]
    in_minggu_lalu_3 = sum((t.pemasukan for t in minggu_lalu_3), 0)
    out_minggu_lalu_3 = sum((t.pengeluaran for t in minggu_lalu_3), 0)
    out_op_minggu_lalu_3 = sum((t.pengeluaran for t in minggu_lalu_3 if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional'), 0)
    
    minggu_lalu_4 = [t for t in transaksi_list if 28 < (sekarang - t.tanggal).days <= 35]
    in_minggu_lalu_4 = sum((t.pemasukan for t in minggu_lalu_4), 0)
    out_minggu_lalu_4 = sum((t.pengeluaran for t in minggu_lalu_4), 0)
    out_op_minggu_lalu_4 = sum((t.pengeluaran for t in minggu_lalu_4 if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional'), 0)
    
    out_minggu_lalu = sum((t.pengeluaran for t in minggu_lalu), 0)
    out_op_minggu_lalu = sum((t.pengeluaran for t in minggu_lalu if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional'), 0)
    
    saldo_minggu_ini = in_minggu_ini - out_minggu_ini
    saldo_operasional_minggu_ini = in_minggu_ini - out_op_minggu_ini

    # 1. Stabilitas Cashflow (0 - 100) Menggunakan Margin Operasional
    margin = 0 if in_minggu_ini == 0 else (saldo_operasional_minggu_ini / in_minggu_ini)
    skor_stabilitas = 100 if margin >= 0.2 else (max(0, margin) / 0.2 * 100)

    # 2. Tren Penjualan (0 - 100)
    if in_minggu_lalu > 0:
        tren_growth_1 = (in_minggu_ini - in_minggu_lalu) / in_minggu_lalu
    elif in_minggu_ini > 0:
        tren_growth_1 = 1.0
    else:
        tren_growth_1 = 0
        
    tren_growth_2 = (in_minggu_lalu - in_minggu_lalu_2) / in_minggu_lalu_2 if in_minggu_lalu_2 > 0 else 0
    
    # Tren yang dipakai untuk pembobotan skor adalah tren_growth langsung (minggu ini vs minggu lalu)
    tren_growth = tren_growth_1
    skor_tren = min(100, max(0, (tren_growth + 0.5) * 100)) # Netral jika -0.5, 100 jika >= 0.5

    # 3. Rasio Pengeluaran Operasional (0 - 100)
    if in_minggu_ini == 0:
        skor_pengeluaran = 0
    else:
        rasio_out = out_op_minggu_ini / in_minggu_ini
        skor_pengeluaran = min(100, max(0, (1 - rasio_out) * 100))

    # 4. Gross Margin Harian (0 - 100)
    data_harian = list(_agregasi_per_hari(transaksi_list).values())
    pemasukan_harian = [d['pemasukan'] for d in data_harian]
    margin_harian = [max(0, d['pemasukan'] - d['pengeluaran_md']) for d in data_harian]
    rata_margin = np.mean(margin_harian) if margin_harian else 0
    rata_pemasukan_harian = np.mean(pemasukan_harian) if pemasukan_harian else 0
    
    if rata_pemasukan_harian == 0:
        skor_gross_margin = 0
        gross_margin_pct = 0
    else:
        gross_margin_pct = (rata_margin / rata_pemasukan_harian) * 100
        skor_gross_margin = min(100, max(0, gross_margin_pct / 0.3)) # asumsi margin idaman 30%

    # 5. Konsistensi Pemasukan (Standard Deviasi) (0 - 100)
    rata_harian = rata_pemasukan_harian
    std_harian = np.std(pemasukan_harian) if len(pemasukan_harian) > 1 else 0
    cv = (std_harian / rata_harian) if rata_harian > 0 else 1
    skor_konsistensi = max(0, (1 - cv) * 100)

    # TOTAL SCORE 0-100
    skor_total = (
        (skor_stabilitas * BOBOT_STABILITAS) +
        (skor_tren * BOBOT_TREN) +
        (skor_pengeluaran * BOBOT_RASIO_OP) +
        (skor_gross_margin * BOBOT_GROSS_MARGIN) +
        (skor_konsistensi * BOBOT_KONSISTENSI)
    )
    skor_total = round(skor_total)

    # limit point ampe 45 aja kalau kas nya tekor
    val_saldo_30_awal = (in_minggu_ini - out_minggu_ini) + (in_minggu_lalu - out_minggu_lalu) + (in_minggu_lalu_2 - out_minggu_lalu_2) + (in_minggu_lalu_3 - out_minggu_lalu_3)
    if saldo_operasional_minggu_ini < 0 or val_saldo_30_awal < 0:
        skor_total = min(skor_total, 45)

    # Labeling & Warning (Sesuai Sinkronisasi Proposal: Rule Peringatan Dini)
    peringatan = []
    if skor_total >= 80:
        label = "Bisnis Sehat"
        warna = "hijau" # Hijau  #27AE60 (CSS)
    elif skor_total >= 60:
        label = "Perlu Perhatian"
        warna = "kuning" # Kuning #F39C12
    else:
        label = "Kondisi Kritis"
        warna = "merah" # Merah #E74C3C
    
    if out_op_minggu_ini > (in_minggu_ini * 0.85):
        peringatan.append("Biaya operasional melampaui 85% dari pemasukan. Pangkas biaya overhead yang tidak esensial segera.")
    elif tren_growth_1 < -0.2 and tren_growth_2 < -0.2:
        peringatan.append(f"Penjualan kamu turun drastis terus-menerus selama dua minggu beruntun (>-20%). Evaluasi strategi promosi atau produk!")

    catatan_mingguan = [f"{t.tanggal.strftime('%d %b')}: {t.catatan}" for t in minggu_ini if getattr(t, 'catatan', None)]

    # Statistik 4 Minggu
    def _status_tren(in_now, in_prev):
        if in_now > in_prev * 1.05: return "↑ Naik"
        elif in_now < in_prev * 0.95: return "↓ Turun"
        return "→ Stabil"

    statistik_4_minggu = [
        {"minggu": "Minggu Ini", "pemasukan": in_minggu_ini, "pengeluaran_op": out_op_minggu_ini, "saldo": in_minggu_ini - out_minggu_ini, "tren": _status_tren(in_minggu_ini, in_minggu_lalu)},
        {"minggu": "Minggu Lalu", "pemasukan": in_minggu_lalu, "pengeluaran_op": out_op_minggu_lalu, "saldo": in_minggu_lalu - out_minggu_lalu, "tren": _status_tren(in_minggu_lalu, in_minggu_lalu_2)},
        {"minggu": "2 Minggu Lalu", "pemasukan": in_minggu_lalu_2, "pengeluaran_op": out_op_minggu_lalu_2, "saldo": in_minggu_lalu_2 - out_minggu_lalu_2, "tren": _status_tren(in_minggu_lalu_2, in_minggu_lalu_3)},
        {"minggu": "3 Minggu Lalu", "pemasukan": in_minggu_lalu_3, "pengeluaran_op": out_op_minggu_lalu_3, "saldo": in_minggu_lalu_3 - out_minggu_lalu_3, "tren": _status_tren(in_minggu_lalu_3, in_minggu_lalu_4)}
    ]

    # Proyeksi Linear Numpy API Polyfit 4 Minggu Mendatang
    # Implementasi Pandas Moving Average untuk visualisasi kurva (Sync Proposal)
    df_chart = pd.DataFrame({'pemasukan': [d['pemasukan'] for d in data_harian]})
    ma_7 = df_chart['pemasukan'].rolling(window=7, min_periods=1).mean().tolist()
    ma_30 = df_chart['pemasukan'].rolling(window=30, min_periods=1).mean().tolist()
    
    Y_trend = df_chart['pemasukan'].tolist()[-periode_grafik:]
    Y_ma7 = ma_7[-periode_grafik:]
    Y_ma30 = ma_30[-periode_grafik:]
    
    X_trend_full = np.arange(len(df_chart))
    proyeksi_list = []
    proyeksi_pengeluaran_list = []
    if len(df_chart) > 5:
        Y_trend_in = df_chart['pemasukan'].tolist()[-30:]
        Y_trend_out = [d['pengeluaran_op'] for d in data_harian][-30:]
        X_trend_30 = X_trend_full[-30:]
        
        z_in = np.polyfit(X_trend_30, Y_trend_in, 1) # Proyeksi linear best-fit line based on 30 last days
        p_in = np.poly1d(z_in)
        z_out = np.polyfit(X_trend_30, Y_trend_out, 1)
        p_out = np.poly1d(z_out)
        
        hari_depan = np.arange(len(X_trend_full), len(X_trend_full) + 28) # 4 minggu
        proyeksi_list_mentah_in = p_in(hari_depan)
        proyeksi_list = [max(0, float(val)) for val in proyeksi_list_mentah_in] # Tidak boleh minus
        
        proyeksi_list_mentah_out = p_out(hari_depan)
        out_mean = np.mean(Y_trend_out)
        out_std = np.std(Y_trend_out)
        
        for val in proyeksi_list_mentah_out:
            base_val = max(0, float(val))
            if out_mean > 0 and (out_std / out_mean) < 0.1:
                # Variasi kecil ±2-5% agar terlihat realistis
                base_val = base_val * np.random.uniform(0.95, 1.05)
            proyeksi_pengeluaran_list.append(base_val)

    t_list_30 = [t for t in transaksi_list if (sekarang - t.tanggal).days <= 30]
    data_produk = analisis_tren_produk(t_list_30)
    advanced_analytics = data_produk.pop('advanced_analytics', None)

    val_in_30 = sum(s["pemasukan"] for s in statistik_4_minggu)
    val_op_30 = sum(s["pengeluaran_op"] for s in statistik_4_minggu)
    val_saldo_30 = sum(s["saldo"] for s in statistik_4_minggu)

    proy_arr = []
    if proyeksi_list and len(proyeksi_list)>=28 and proyeksi_pengeluaran_list and len(proyeksi_pengeluaran_list)>=28:
        for i, lbl in enumerate(["Minggu +1","Minggu +2","Minggu +3","Minggu +4"]):
            sl = slice(i*7, i*7+7)
            pi = sum(proyeksi_list[sl])
            po = sum(proyeksi_pengeluaran_list[sl])
            proy_arr.append({"label": lbl, "pemasukan": pi, "pengeluaran": po, "saldo": pi-po})

    risiko = _hitung_risiko(
        skor_total, 
        {"stabilitas": skor_stabilitas, "tren": skor_tren, "pengeluaran": skor_pengeluaran, "gross_margin": skor_gross_margin, "konsistensi": skor_konsistensi}, 
        val_in_30, val_op_30, val_saldo_30,
        round(rata_harian), 
        round(np.mean([d['pengeluaran_op'] for d in data_harian]) if data_harian else 0), 
        gross_margin_pct if 'gross_margin_pct' in locals() else 0, 
        peringatan, 
        proy_arr
    )

    rekomendasi = generate_rekomendasi(
        val_saldo_30, 
        round(np.mean([d['pengeluaran_op'] for d in data_harian]) if data_harian else 0), 
        gross_margin_pct if 'gross_margin_pct' in locals() else 0, 
        skor_tren, 
        (rasio_out * 100) if 'rasio_out' in locals() else 0, 
        proy_arr, 
        skor_konsistensi
    )

    ringkasan_30_hari = {
        "total_pemasukan": val_in_30,
        "total_pengeluaran_op": val_op_30,
        "saldo_bersih": val_saldo_30,
        "rata_pemasukan": round(rata_harian),
        "rata_pengeluaran": round(np.mean([d['pengeluaran_op'] + d['pengeluaran_md'] for d in data_harian]) if data_harian else 0),
        "gross_margin": gross_margin_pct if 'gross_margin_pct' in locals() else 0,
    }

    # Ringkasan Kustom berdasarkan periode yang dipilih user
    t_kustom = [t for t in transaksi_list if (sekarang - t.tanggal).days <= periode_grafik]
    kustom_in = sum(t.pemasukan for t in t_kustom)
    kustom_out_op = sum(t.pengeluaran for t in t_kustom if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional')
    kustom_out_md = sum(t.pengeluaran for t in t_kustom if getattr(t, 'jenis_pengeluaran', 'operasional') == 'modal')
    kustom_out_total = kustom_out_op + kustom_out_md
    
    # cari modal total barang yang laku pakai hpp asli baris transaksi
    kustom_hpp = sum((getattr(t, 'harga_modal', 0.0) or 0.0) * (getattr(t, 'kuantitas', 0) or 0) for t in t_kustom)
    
    if kustom_hpp > 0:
        kustom_gm = ((kustom_in - kustom_hpp) / kustom_in * 100) if kustom_in > 0 else 0
    else:
        kustom_gm = ((kustom_in - kustom_out_md) / kustom_in * 100) if kustom_in > 0 else 0
        
    kustom_saldo = kustom_in - kustom_out_total
    hari_kustom = len({t.tanggal for t in t_kustom}) or 1

    kustom_pelanggan = sum(getattr(t, 'jumlah_pelanggan', 0) or 0 for t in t_kustom)
    kustom_aov = round(kustom_in / kustom_pelanggan) if kustom_pelanggan > 0 else 0
    kustom_pengeluaran_kategori = defaultdict(float)
    for t in t_kustom:
        if t.pengeluaran > 0:
            kat = str(getattr(t, 'kategori', '') or '').strip()
            if not kat:
                kat = 'Lainnya'
            kustom_pengeluaran_kategori[kat] += t.pengeluaran

    # Gabung kategori "Lainnya" bawaan data dgn "Lainnya" dari tail data
    lainnya_val = kustom_pengeluaran_kategori.pop('Lainnya', 0)
    
    sorted_kat = sorted(kustom_pengeluaran_kategori.items(), key=lambda x: x[1], reverse=True)
    pie_labels = [k[0] for k in sorted_kat[:5]]
    pie_data = [k[1] for k in sorted_kat[:5]]
    
    sisa_val = sum(k[1] for k in sorted_kat[5:])
    total_lainnya = float(sisa_val) + float(lainnya_val)
    
    if total_lainnya > 0:
        pie_labels.append("Lainnya")
        pie_data.append(total_lainnya)

    ringkasan_kustom = {
        "periode_hari": periode_grafik,
        "total_pemasukan": kustom_in,
        "total_pengeluaran_op": kustom_out_op,
        "total_pengeluaran_md": kustom_out_md,
        "total_pengeluaran": kustom_out_total,
        "saldo_bersih": kustom_saldo,
        "rata_pemasukan": round(float(kustom_in) / float(max(1, hari_kustom))),
        "rata_pengeluaran": round(float(kustom_out_total) / float(max(1, hari_kustom))),
        "gross_margin": round(float(kustom_gm), 1),
        "jumlah_transaksi": len(t_kustom),
        "jumlah_hari_aktif": hari_kustom,
        "jumlah_pelanggan": kustom_pelanggan,
        "aov": kustom_aov,
        "pie_labels": pie_labels,
        "pie_data": pie_data,
    }

    return {
        "is_cukup": True,
        "periode_grafik": periode_grafik,
        "data_produk": data_produk,
        "advanced_analytics": advanced_analytics,
        "risiko": risiko,
        "rekomendasi": rekomendasi,
        "proyeksi_tabel": proy_arr,
        "ringkasan_30_hari": ringkasan_30_hari,
        "ringkasan_kustom": ringkasan_kustom,
        "skor": skor_total,
        "label": label,
        "warna": warna,
        "peringatan": peringatan,
        "total_pemasukan_minggu_ini": in_minggu_ini,
        "total_pengeluaran_op_minggu_ini": out_op_minggu_ini,
        "total_pengeluaran_md_minggu_ini": out_md_minggu_ini,
        "total_pengeluaran_minggu_ini": out_minggu_ini,
        "saldo_minggu_ini": saldo_minggu_ini,
        "rata_pemasukan": round(rata_harian),
        "rata_pengeluaran": round(np.mean([d['pengeluaran_op'] + d['pengeluaran_md'] for d in data_harian]) if data_harian else 0),
        "tren_status": "naik" if tren_growth >= 0 else "turun",
        "grafik_aktual": Y_trend, # Array 1D pemasukan harian
        "grafik_ma7": Y_ma7,
        "grafik_ma30": Y_ma30,
        "grafik_op_aktual": [d['pengeluaran_op'] for d in data_harian][-periode_grafik:],
        "grafik_md_aktual": [d['pengeluaran_md'] for d in data_harian][-periode_grafik:],
        "grafik_proyeksi": proyeksi_list, # Array 1D proyeksi harian ke depan
        "proyeksi_pengeluaran": proyeksi_pengeluaran_list, 
        "catatan_mingguan": catatan_mingguan,
        "rincian_skor": {
            "stabilitas": round(skor_stabilitas),
            "tren": round(skor_tren),
            "pengeluaran": round(skor_pengeluaran),
            "gross_margin": round(skor_gross_margin),
            "konsistensi": round(skor_konsistensi),
            "nilai_margin_ops": float(margin) * 100.0,
            "nilai_tren_growth": float(tren_growth) * 100.0,
            "nilai_rasio_out": (float(rasio_out) * 100.0) if 'rasio_out' in locals() else 0.0,
            "nilai_gross_margin_pct": float(gross_margin_pct) if 'gross_margin_pct' in locals() else 0.0,
            "nilai_cv_konsistensi": float(cv) if 'cv' in locals() else 1.0
        },
        "statistik_4_minggu": statistik_4_minggu
    }

def _fallback_empty_data(periode_grafik=30):
    return {
        "is_cukup": False,
        "periode_grafik": periode_grafik,
        "data_produk": None,
        "advanced_analytics": None,
        "risiko": None,
        "rekomendasi": [],
        "proyeksi_tabel": [],
        "ringkasan_30_hari": {},
        "skor": 0,
        "label": "Data Belum Cukup",
        "warna": "kuning",
        "peringatan": ["Sistem butuh minimal data 14 hari aktivitas untuk dianalisa. Mulai dengan mencatat transaksi pertamamu!"],
        "total_pemasukan_minggu_ini": 0,
        "total_pengeluaran_op_minggu_ini": 0,
        "total_pengeluaran_md_minggu_ini": 0,
        "total_pengeluaran_minggu_ini": 0,
        "saldo_minggu_ini": 0,
        "rata_pemasukan": 0,
        "rata_pengeluaran": 0,
        "tren_status": "stabil",
        "grafik_aktual": [],
        "grafik_ma7": [],
        "grafik_ma30": [],
        "grafik_op_aktual": [],
        "grafik_md_aktual": [],
        "grafik_proyeksi": [],
        "proyeksi_pengeluaran": [],
        "catatan_mingguan": [],
        "rincian_skor": {
            "stabilitas": 0, "tren": 0, "pengeluaran": 0, "gross_margin": 0, "konsistensi": 0,
            "nilai_margin_ops": 0, "nilai_tren_growth": 0, "nilai_rasio_out": 0, "nilai_gross_margin_pct": 0, "nilai_cv_konsistensi": 0
        },
        "statistik_4_minggu": []
    }

def analisis_tren_produk(transaksi_list):
    """
    bantu cari tahu produk mana yang paling banyak terjual dan mana yang kurang laris dari riwayat transaksi.
    juga menghitung cash cow margin, prediksi dana restok top produk, dan sentimen catatan.
    """
    produk_agregat = defaultdict(int)
    profit_agregat = defaultdict(float)
    mingguan_kuantitas = defaultdict(lambda: defaultdict(int))
    
    keywords = ['hujan', 'sepi', 'ramai', 'promo', 'diskon', 'panas', 'libur', 'gajian']
    keyword_counts = defaultdict(int)
    sekarang = date.today()

    for t in transaksi_list:
        if getattr(t, 'nama_produk', None) and getattr(t, 'kuantitas', 0) > 0:
            nama = str(t.nama_produk).strip().lower()
            produk_agregat[nama] += t.kuantitas
            
            hpp_total = getattr(t, 'harga_modal', 0.0) * t.kuantitas
            margin = t.pemasukan - hpp_total
            profit_agregat[nama] += margin
            
            minggu_ke = (sekarang - t.tanggal).days // 7
            mingguan_kuantitas[nama][minggu_ke] += t.kuantitas
            
        catatan = getattr(t, 'catatan', '') or ''
        catatan_lower = str(catatan).lower()
        if catatan_lower:
            for kw in keywords:
                if kw in catatan_lower:
                    keyword_counts[kw] += 1
            
    sorted_produk = sorted(produk_agregat.items(), key=lambda x: x[1], reverse=True)
    top_3_terlaris = [{"nama": p[0].title(), "total": p[1]} for p in sorted_produk[:3]]
    bottom_3_menurun = [{"nama": p[0].title(), "total": p[1]} for p in sorted_produk[-3:]] if len(sorted_produk) >= 3 else []
    
    sorted_profit = sorted(profit_agregat.items(), key=lambda x: x[1], reverse=True)
    cash_cow = None
    if sorted_profit and sorted_profit[0][1] > 0:
        cash_cow = {"nama": sorted_profit[0][0].title(), "margin_kotor": sorted_profit[0][1]}
        
    prediksi_restok = []
    for p in sorted_produk[:3]:
        nama = p[0]
        qty_m0 = mingguan_kuantitas[nama].get(0, 0)
        qty_m1 = mingguan_kuantitas[nama].get(1, 0)
        
        if qty_m1 > 0 and qty_m0 > (qty_m1 * 1.2):
            hpp_list = [getattr(t, 'harga_modal', 0.0) for t in transaksi_list if str(getattr(t, 'nama_produk', '')).lower() == nama and getattr(t, 'harga_modal', 0.0) > 0]
            avg_hpp = sum(hpp_list) / len(hpp_list) if hpp_list else 0
            
            avg_weekly = sum(mingguan_kuantitas[nama].values()) / max(len(mingguan_kuantitas[nama]), 1)
            
            # siapin perbekalan buat 3 hari ke depan
            estimasi_dana = avg_hpp * (avg_weekly / 7) * 3
            
            if estimasi_dana > 0:
                prediksi_restok.append({
                    "nama": nama.title(),
                    "estimasi_dana": estimasi_dana
                })
                
    sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    korelasi_catatan = [{"keyword": k[0]} for k in sorted_keywords[:2]]
    
    advanced_analytics = {
        "cash_cow": cash_cow,
        "prediksi_restok": prediksi_restok,
        "korelasi_catatan": korelasi_catatan
    }
    
    return {
        "semua_produk": [{"nama": p[0].title(), "total": p[1]} for p in sorted_produk],
        "top_3_terlaris": top_3_terlaris,
        "bottom_3_menurun": bottom_3_menurun,
        "advanced_analytics": advanced_analytics
    }

def format_rp(nilai):
    return f"Rp {int(nilai):,}".replace(",",".")

def _hitung_risiko(score, breakdown, val_in_30, val_op_30, val_saldo_30,
                   avg_in, avg_out, gross_margin_pct, warnings, proy_arr):
    risiko = {}  # type: ignore

    dana_darurat_ideal = avg_out * 14
    coverage           = val_saldo_30 / dana_darurat_ideal if dana_darurat_ideal > 0 else 0
    if   coverage >= 2.0: r_liq = 1
    elif coverage >= 1.0: r_liq = 2
    elif coverage >= 0.5: r_liq = 3
    elif coverage >= 0.0: r_liq = 4
    else:                 r_liq = 5
    risiko["likuiditas"] = {
        "skor": r_liq,
        "coverage": coverage,
        "dana_tersedia": val_saldo_30,
        "dana_ideal": dana_darurat_ideal,
        "keterangan": _liq_ket(r_liq, coverage, val_saldo_30, dana_darurat_ideal)
    }

    rasio_op = (val_op_30 / val_in_30 * 100) if val_in_30 > 0 else 100
    if   gross_margin_pct >= 50 and rasio_op <= 50: r_profit = 1
    elif gross_margin_pct >= 35 and rasio_op <= 65: r_profit = 2
    elif gross_margin_pct >= 20 and rasio_op <= 80: r_profit = 3
    elif gross_margin_pct >= 10:                    r_profit = 4
    else:                                           r_profit = 5
    risiko["profitabilitas"] = {
        "skor": r_profit,
        "gross_margin": gross_margin_pct,
        "rasio_operasional": rasio_op,
        "keterangan": _profit_ket(r_profit, gross_margin_pct, rasio_op)
    }

    tren  = breakdown.get("tren", 0)
    stab  = breakdown.get("stabilitas", 0)
    kons  = breakdown.get("konsistensi", 0)
    avg_cf = (tren + stab + kons) / 3
    if   avg_cf >= 80: r_cf = 1
    elif avg_cf >= 65: r_cf = 2
    elif avg_cf >= 50: r_cf = 3
    elif avg_cf >= 35: r_cf = 4
    else:              r_cf = 5
    risiko["arus_kas"] = {
        "skor": r_cf,
        "stabilitas": stab,
        "tren": tren,
        "konsistensi": kons,
        "keterangan": _cf_ket(r_cf, avg_cf)
    }

    neg_weeks = sum(1 for p in proy_arr if p['saldo'] < 0)
    if   neg_weeks == 0: r_proj = 1
    elif neg_weeks == 1: r_proj = 2
    elif neg_weeks == 2: r_proj = 3
    elif neg_weeks == 3: r_proj = 4
    else:                r_proj = 5
    risiko["proyeksi"] = {
        "skor": r_proj,
        "minggu_negatif": neg_weeks,
        "keterangan": _proj_ket(r_proj, neg_weeks)
    }

    n_warn = len(warnings)
    if   n_warn == 0: r_data = 1
    elif n_warn == 1: r_data = 2
    elif n_warn <= 3: r_data = 3
    elif n_warn <= 5: r_data = 4
    else:             r_data = 5
    risiko["kepatuhan"] = {
        "skor": r_data,
        "jumlah_peringatan": n_warn,
        "keterangan": _data_ket(r_data, n_warn)
    }

    bobot = {"likuiditas":0.30,"profitabilitas":0.25,"arus_kas":0.25, "proyeksi":0.15,"kepatuhan":0.05}
    composite = sum(risiko[k]["skor"] * bobot[k] for k in bobot)
    if   composite <= 1.5: label, warna = "SANGAT RENDAH", "AAA"
    elif composite <= 2.2: label, warna = "RENDAH",        "AA"
    elif composite <= 3.0: label, warna = "MODERAT",       "BBB"
    elif composite <= 3.8: label, warna = "TINGGI",        "BB"
    else:                  label, warna = "SANGAT TINGGI", "CCC"

    risiko["composite"] = {
        "skor": round(composite, 2),
        "label": label,
        "rating": warna
    }
    return risiko

def _liq_ket(r, cov, ada, ideal):
    if r == 1: return f"Dana operasional sangat mencukupi ({cov:.1f}x dari kebutuhan cadangan ideal)."
    if r == 2: return f"Dana cadangan memadai, menutup {cov:.1f}x kebutuhan operasional 2 minggu."
    if r == 3: return f"Dana cadangan terbatas, hanya {cov:.1f}x kebutuhan minimum. Perlu penguatan."
    if r == 4: return f"Dana cadangan di bawah standar minimum. Rentan terhadap gangguan operasional."
    return        f"Dana cadangan tidak mencukupi. Risiko gagal bayar kewajiban."

def _profit_ket(r, gm, ro):
    if r == 1: return f"Profitabilitas sangat baik. Gross margin {gm:.1f}%, rasio beban operasional {ro:.1f}%."
    if r == 2: return f"Profitabilitas baik. Gross margin {gm:.1f}%, pengendalian biaya cukup efisien."
    if r == 3: return f"Profitabilitas moderat. Gross margin {gm:.1f}% perlu ditingkatkan."
    if r == 4: return f"Profitabilitas rendah. Gross margin {gm:.1f}%. Tekanan margin tinggi."
    return        f"Profitabilitas sangat rendah. Risiko kerugian finansial."

def _cf_ket(r, avg):
    if r == 1: return "Arus kas sangat stabil dan konsisten. Mencerminkan kualitas manajemen yang baik."
    if r == 2: return "Arus kas stabil dengan variasi minor yang dapat diterima."
    if r == 3: return "Arus kas cukup stabil namun ada volatilitas yang perlu dipantau."
    if r == 4: return "Arus kas tidak stabil berisiko mengganggu kemampuan membayar kewajiban."
    return        "Arus kas sangat tidak stabil. Risiko tinggi."

def _proj_ket(r, neg):
    if r == 1: return "Proyeksi 4 minggu ke depan seluruhnya positif."
    if r == 2: return f"Proyeksi menunjukkan {neg} minggu arus kas negatif. Perlu dinormalkan."
    if r == 3: return f"Proyeksi menunjukkan {neg} minggu negatif. Risiko operasional menengah."
    if r == 4: return f"Proyeksi menunjukkan {neg} minggu negatif. Risiko likuiditas signifikan."
    return        "Seluruh proyeksi negatif. Sangat kritis."

def _data_ket(r, n):
    if r == 1: return "Tidak ada anomali data."
    if r == 2: return f"Ada {n} peringatan minor."
    if r == 3: return f"Ditemukan {n} peringatan menengah."
    if r == 4: return f"Ditemukan {n} peringatan serius. Validasi data dibutuhkan."
    return        f"Ditemukan {n} peringatan akut. Sangat berisiko data palsu."

def generate_rekomendasi(val_saldo_30, avg_out, gross_margin_pct, tren_penjualan, rasio_pengeluaran, proy_arr, konsistensi):
    rekomendasi = []
    dana_darurat_ideal = avg_out * 14

    rekomendasi.append({
        "aspek": "Pengelolaan Margin",
        "tindakan": f"Pertahankan gross margin di atas {gross_margin_pct:.1f}% dengan optimasi harga jual."
    })
    rekomendasi.append({
        "aspek": "Pencatatan Keuangan",
        "tindakan": "Lakukan pencatatan transaksi konsisten setiap hari untuk meningkatkan akurasi."
    })
    if tren_penjualan < 50:
        rekomendasi.append({
            "aspek": "Peningkatan Penjualan",
            "tindakan": "Tren penjualan turun. Disarankan promosi terstruktur demi mendorong efisiensi stok."
        })
    if rasio_pengeluaran > 60:
        rekomendasi.append({
            "aspek": "Efisiensi Operasional",
            "tindakan": f"Rasio pengeluaran melampaui standar sehat ({rasio_pengeluaran:.1f}%). Audit pengeluaran kembali."
        })
    if gross_margin_pct < 30:
        rekomendasi.append({
            "aspek": "Perbaikan Margin",
            "tindakan": f"Gross margin {gross_margin_pct:.1f}% berada di bawah standar sektor (>30%)."
        })
    if val_saldo_30 < dana_darurat_ideal:
        rekomendasi.append({
            "aspek": "Pembentukan Dana Cadangan",
            "tindakan": f"Saldo saat ini ({format_rp(val_saldo_30)}) belum optimal melawan ketahanan ekstrim."
        })
    neg_in = sum(1 for p in proy_arr if p['saldo'] < 0)
    if neg_in > 0:
        rekomendasi.append({
            "aspek": "Antisipasi Cashflow Negatif",
            "tindakan": f"Proyeksi menunjukkan potensi kas negatif dalam {neg_in} minggu ke depan."
        })
    if konsistensi < 60:
        rekomendasi.append({
            "aspek": "Konsistensi Pendapatan",
            "tindakan": "Fluktuasi harian sangat tinggi. Kembangkan strategi stabilitas."
        })
    return rekomendasi[:7]
