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
    tren_growth_1 = (in_minggu_ini - in_minggu_lalu) / in_minggu_lalu if in_minggu_lalu > 0 else 0
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
    margin_harian = [max(0, d['pemasukan'] - d['pengeluaran_op']) for d in data_harian]
    rata_margin = np.mean(margin_harian) if margin_harian else 0
    rata_pemasukan_harian = np.mean(pemasukan_harian) if pemasukan_harian else 0
    
    if rata_pemasukan_harian == 0:
        skor_gross_margin = 0
    else:
        gross_margin_pct = rata_margin / rata_pemasukan_harian
        skor_gross_margin = min(100, max(0, gross_margin_pct * 100 / 0.3)) # asumsi margin idaman 30%

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

    return {
        "is_cukup": True,
        "periode_grafik": periode_grafik,
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
        "rata_pengeluaran": round(np.mean([d['pengeluaran_op'] for d in data_harian]) if data_harian else 0),
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
            "nilai_margin_ops": margin,
            "nilai_tren_growth": tren_growth,
            "nilai_rasio_out": rasio_out if 'rasio_out' in locals() else 0,
            "nilai_gross_margin_pct": gross_margin_pct if 'gross_margin_pct' in locals() else 0,
            "nilai_cv_konsistensi": cv if 'cv' in locals() else 1
        },
        "statistik_4_minggu": statistik_4_minggu
    }

def _fallback_empty_data(periode_grafik=30):
    return {
        "is_cukup": False,
        "periode_grafik": periode_grafik,
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
