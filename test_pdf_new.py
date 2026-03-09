import traceback
from datetime import date, timedelta, datetime
from pdf_generator import generate_pdf_report

score = 85
avg_in = 500000
avg_out = 300000
warnings = ["Perhatikan pengeluaran ATK bulan depan"]
catatan_mingguan = ["Sabtu: Restock bahan baku"]

breakdown = {
    'stabilitas': 75,
    'tren': 80,
    'pengeluaran': 85,
    'gross_margin': 65,
    'konsistensi': 70,
    'nilai_tren_growth': 0.1,
    'nilai_rasio_out': 0.6,
    'nilai_gross_margin_pct': 0.35,
}

stat_4_minggu = [
    {"minggu": "Minggu Ini", "pemasukan": 3500000, "pengeluaran_op": 2000000, "saldo": 1500000, "tren": "↑ Naik"},
    {"minggu": "Minggu Lalu", "pemasukan": 3200000, "pengeluaran_op": 1900000, "saldo": 1300000, "tren": "→ Stabil"}
]

proyeksi = [500000] * 28
proyeksi_pengeluaran = [300000] * 28

try:
    generate_pdf_report(
        user_name="Toko Sejahtera Tes",
        score=score,
        avg_in=avg_in,
        avg_out=avg_out,
        warnings=warnings,
        catatan_mingguan=catatan_mingguan,
        output_path="test_mock.pdf",
        breakdown=breakdown,
        stat_4_minggu=stat_4_minggu,
        proyeksi=proyeksi,
        proyeksi_pengeluaran=proyeksi_pengeluaran,
        tgl_cetak_dt=datetime.now(),
        tgl_mulai_dt=date.today() - timedelta(days=30),
        tgl_akhir_dt=date.today()
    )
    print("TEST REPORTLAB BERHASIL")
except Exception as e:
    traceback.print_exc()
