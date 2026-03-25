import csv
import random
from datetime import date, timedelta

# Profil Perusahaan
PRODUK_INFO = {
    "Keripik Singkong Balado": {"jual": 15000, "modal": 8000},
    "Keripik Singkong Original": {"jual": 15000, "modal": 8000},
    "Basreng Pedas Daun Jeruk": {"jual": 20000, "modal": 12000},
    "Basreng Original Gurih": {"jual": 20000, "modal": 12000},
    "Makaroni Bantet Balado": {"jual": 12000, "modal": 6000},
    "Makaroni Keju Premium": {"jual": 15000, "modal": 7500},
    "Keripik Kaca Pedas Nampol": {"jual": 18000, "modal": 10000},
    "Keripik Kaca Original": {"jual": 18000, "modal": 10000},
    "Usus Crispy Balado": {"jual": 22000, "modal": 14000},
    "Usus Crispy Original": {"jual": 22000, "modal": 14000},
    "Mie Lidi Pedas Level 5": {"jual": 10000, "modal": 5000},
    "Mie Lidi Jagung Bakar": {"jual": 10000, "modal": 5000},
    "Seblak Kering Pedas": {"jual": 16000, "modal": 8500},
    "Seblak Kering Original": {"jual": 16000, "modal": 8500},
    "Pilus Cikur Pedas": {"jual": 14000, "modal": 7000},
    "Sus Kering Cokelat Lumer": {"jual": 25000, "modal": 15000},
    "Kacang Umpet Karamel": {"jual": 20000, "modal": 11000},
    "Stik Keju Premium": {"jual": 24000, "modal": 13000},
    "Emping Pedas Manis": {"jual": 30000, "modal": 18000},
    "Peyek Kacang Mini": {"jual": 15000, "modal": 8000}
}
PRODUK = list(PRODUK_INFO.keys())

KATEGORI_IN = ["Penjualan B2C", "Pesanan Grosir", "E-Commerce"]
KATEGORI_OUT = ["Bahan Kemasan (Pouch)", "Bahan Baku (Bogor)", "Listrik & Air", "Gaji Pegawai", "Iklan Olahh", "Lainnya"]

# Setup Waktu: 3 bulan terakhir (90 hari)
tanggal_akhir = date.today()
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
                harga_jual_satuan = PRODUK_INFO[prod]['jual']
                harga_modal_satuan = PRODUK_INFO[prod]['modal']
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
