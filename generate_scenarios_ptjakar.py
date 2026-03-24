import csv
import random
from datetime import date, timedelta

# Profil Perusahaan
PRODUK = ["Olah Balado", "Olah Original"]
KATEGORI_IN = ["Penjualan B2C", "Pesanan Grosir", "E-Commerce"]
KATEGORI_OUT = ["Bahan Kemasan (Pouch)", "Bahan Baku (Bogor)", "Listrik & Air", "Gaji Pegawai", "Iklan Olahh", "Lainnya"]

# Setup Waktu: 3 bulan terakhir (90 hari)
tanggal_akhir = date(2026, 3, 24)
tanggal_awal = tanggal_akhir - timedelta(days=90)
rentang_hari = (tanggal_akhir - tanggal_awal).days

def generate_csv(filename, scenario):
    # scenario: 'bagus', 'sedang', 'jelek'
    data = []
    
    # Tren paramerters
    # Bagus: Naik secara gradual
    # Sedang: Stabil atau fluktuatif stagnan
    # Jelek: Menurun drastis di 30 hari terakhir
    
    for i in range(rentang_hari + 1):
        hari_ini = tanggal_awal + timedelta(days=i)
        
        # Penjualan Harian
        if scenario == 'bagus':
            # Tren positif, makin hari makin banyak
            multiplier = 1.0 + (i / rentang_hari) * 0.8
            prob_jual = 0.95
            min_trx, max_trx = 2, 5
        elif scenario == 'sedang':
            # Tren stagnan
            multiplier = 1.0 + random.uniform(-0.1, 0.1)
            prob_jual = 0.75
            min_trx, max_trx = 1, 3
        else:
            # Tren negatif drastis di akhir
            multiplier = 1.5 - (i / rentang_hari) * 1.2
            prob_jual = 0.6 if i > 60 else 0.8
            min_trx, max_trx = 1, 4 if i <= 60 else 1
            
        # Pemasukan
        if random.random() < prob_jual:
            qty_trx = random.randint(min_trx, int(max_trx * multiplier)) if int(max_trx * multiplier) >= min_trx else min_trx
            for _ in range(qty_trx):
                prod = random.choice(PRODUK)
                qty = random.randint(1, 5) * random.randint(1, 3)
                harga_jual_satuan = 25000 if prod == "Olah Balado" else 20000
                harga_modal_satuan = 8000 if prod == "Olah Balado" else 7500
                total_in = qty * harga_jual_satuan
                data.append({
                    "tanggal": hari_ini.strftime("%Y-%m-%d"),
                    "kategori": random.choice(KATEGORI_IN),
                    "nama_produk": prod,
                    "kuantitas": qty,
                    "harga_modal": harga_modal_satuan * qty,
                    "pemasukan": total_in,
                    "pengeluaran": 0,
                    "jenis_pengeluaran": "",
                    "jumlah_pelanggan": random.randint(1, 3),
                    "catatan": "Sales E-Commerce" if random.random() > 0.5 else "Beli Langsung"
                })
        
        # Pengeluaran Operasional & Modal
        # Bagus: Opex kecil terukur (20% dari estimasi income)
        # Sedang: Opex lumayan besar (60% dari estimasi income)
        # Jelek: Opex barbar tiap hari (> 90% income)
        if scenario == 'bagus':
            prob_out = 0.2
            biaya_range = (50000, 150000)
        elif scenario == 'sedang':
            prob_out = 0.4
            biaya_range = (100000, 300000)
        else:
            prob_out = 0.7 if i > 60 else 0.4
            biaya_range = (250000, 600000)
            
        if random.random() < prob_out:
            kat_out = random.choice(KATEGORI_OUT)
            jns_out = "operasional" if kat_out not in ["Lainnya", "Izin Usaha"] else "lainnya"
            if kat_out == "Bahan Kemasan (Pouch)": jns_out = "modal"
            
            data.append({
                "tanggal": hari_ini.strftime("%Y-%m-%d"),
                "kategori": kat_out,
                "nama_produk": "",
                "kuantitas": 0,
                "harga_modal": 0,
                "pemasukan": 0,
                "pengeluaran": random.randint(*biaya_range),
                "jenis_pengeluaran": jns_out,
                "jumlah_pelanggan": 0,
                "catatan": f"Restok {kat_out}" if jns_out == "modal" else f"Bayar {kat_out}"
            })

    # Urutkan berdasarkan tanggal
    data.sort(key=lambda x: x['tanggal'])
    
    # Tulis ke CSV
    headers = ["tanggal", "kategori", "nama_produk", "kuantitas", "harga_modal", "pemasukan", "pengeluaran", "jenis_pengeluaran", "jumlah_pelanggan", "catatan"]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"File {filename} berhasil dibuat dengan {len(data)} baris.")

if __name__ == "__main__":
    generate_csv("PT_Jakar_Jaya_Skor_Bagus.csv", "bagus")
    generate_csv("PT_Jakar_Jaya_Skor_Sedang.csv", "sedang")
    generate_csv("PT_Jakar_Jaya_Skor_Jelek.csv", "jelek")
