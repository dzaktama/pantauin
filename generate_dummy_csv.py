import csv
from datetime import date, timedelta
import random

header = ['tanggal', 'kategori', 'nama_produk', 'kuantitas', 'pemasukan', 'pengeluaran', 'jenis_pengeluaran', 'jumlah_pelanggan', 'catatan']
kategori_produk = {
    'Makanan & Minuman': [
        ('Nasi Goreng Spesial', 20000, 10000), 
        ('Es Teh Manis', 5000, 2000), 
        ('Ayam Geprek', 18000, 10000),
        ('Ayam Bakar Madu', 25000, 15000),
        ('Es Jeruk', 6000, 3000)
    ],
    'Retail': [
        ('Kaus Sablon', 50000, 30000),
        ('Jaket Denim', 150000, 100000)
    ],
    'Jasa': [
        ('Reparasi AC', 150000, 20000),
        ('Cuci Motor', 15000, 2000)
    ]
}

# Mulai dari pertengahan Januari 2026 agar mencakup 45-60 hari penuh hingga Maret 2026
start_date = date(2026, 1, 15) 
days = 60

data = []

for i in range(200):
    kategori = random.choices(['Makanan & Minuman', 'Retail', 'Jasa'], weights=[70, 20, 10])[0]
    produk, harga_jual, harga_modal = random.choice(kategori_produk[kategori])
    
    # Memanipulasi data agar AI menghasilkan rekomendasi menarik
    if produk == 'Nasi Goreng Spesial' or produk == 'Es Teh Manis':
        kuantitas = random.randint(15, 40) # Laris manis
    elif produk == 'Ayam Bakar Madu' or produk == 'Jaket Denim':
        kuantitas = random.randint(1, 3) # Dead stock / kurang laku
    else:
        kuantitas = random.randint(3, 10) # Rata-rata
        
    pemasukan = kuantitas * harga_jual
    pengeluaran = kuantitas * harga_modal
    
    # Overhead harian acak
    jenis_pengeluaran = 'operasional'
    if random.random() < 0.3:
        pengeluaran += random.randint(20000, 50000)
        
    # Kadang ada pembelian modal besar
    if random.random() < 0.05:
        pengeluaran += random.randint(500000, 1500000)
        jenis_pengeluaran = 'modal'

    tanggal_transaksi = start_date + timedelta(days=random.randint(0, days))
    jumlah_pelanggan = kuantitas if kategori == 'Makanan & Minuman' else random.randint(1, max(1, kuantitas))
    
    catatan_opsi = ['', '', '', 'Ramai pelanggan rombongan', 'Cuaca mendukung jualan', 'Cuaca buruk jadi sepi', 'Beli stok bahan', 'Pesanan online membludak']
    catatan = random.choice(catatan_opsi)
    
    data.append([
        tanggal_transaksi.strftime('%Y-%m-%d'),
        kategori,
        produk,
        kuantitas,
        pemasukan,
        pengeluaran,
        jenis_pengeluaran,
        jumlah_pelanggan,
        catatan
    ])

# Urutkan berdasarkan tanggal terlama ke terbaru
data.sort(key=lambda x: x[0])

# Simpan jadi CSV
with open('laporan_dummy_200.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(data)

print("Berhasil membuat file laporan_dummy_200.csv di dalam folder PANTAUIN")
