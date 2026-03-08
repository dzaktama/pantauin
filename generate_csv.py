import csv
import random
from datetime import datetime, timedelta

# Data seed
kategori_list = ['Makanan & Minuman', 'Retail', 'Jasa', 'Lainnya']
jenis_pengeluaran_list = ['operasional', 'modal']
catatan_operasional = [
    "Ramai sekali", "Sepi karena hujan", "Event lari minggu pagi", 
    "Diskon 10% laku keras", "Orderan gofood banyak", 
    "Normal", "Cukup sibuk siang hari", "Banyak anak sekolah beli",
    "", "", "", "" # some empty notes
]
catatan_modal = [
    "Beli etalase baru", "Service mesin kopi", "Beli stok bahan sebulan", 
    "Perpanjang sewa lapak", "Beli seragam karyawan", "Modal iklan Instagram"
]

start_date = datetime(2025, 8, 20)

data = []
# Header
data.append(['tanggal', 'kategori', 'pemasukan', 'pengeluaran', 'jenis_pengeluaran', 'jumlah_pelanggan', 'catatan'])

for i in range(200):
    current_date = start_date + timedelta(days=i)
    
    # 85% operasional, 15% modal
    is_modal = random.random() < 0.15
    jenis = 'modal' if is_modal else 'operasional'
    
    # Kategori
    kategori = random.choice(kategori_list)
    
    # Pemasukan
    # Trend slowly increasing over time, with random daily fuzz
    base_income = 800000 + (i * 2000) 
    pemasukan = int(base_income * random.uniform(0.7, 1.3))
    
    # Pengeluaran
    if is_modal:
        pengeluaran = random.randint(1500000, 5000000)
        catatan = random.choice(catatan_modal)
    else:
        pengeluaran = int(pemasukan * random.uniform(0.3, 0.7)) # 30%-70% of income 
        catatan = random.choice(catatan_operasional)
        
    # Pelanggan
    pelanggan = int((pemasukan / 25000) * random.uniform(0.8, 1.2))
    
    data.append([
        current_date.strftime('%Y-%m-%d'),
        kategori,
        pemasukan,
        pengeluaran,
        jenis,
        pelanggan,
        catatan
    ])

with open(r'C:\laragon\www\PANTAUIN\Contoh_Transaksi_PANTAUIN.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(data)

print(f"Selesai me-generate {len(data)-1} baris CSV!")
