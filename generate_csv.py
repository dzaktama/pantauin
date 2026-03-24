import csv
import random
from datetime import datetime, timedelta

# === SEED DATA ===
kategori_produk = {
    'Makanan & Minuman': {
        'produk': [
            ('Nasi Goreng Spesial', 15000, 8000),
            ('Mie Ayam Bakso', 12000, 6000),
            ('Es Teh Manis', 5000, 1500),
            ('Kopi Susu Gula Aren', 18000, 7000),
            ('Ayam Geprek', 15000, 7500),
            ('Soto Ayam', 13000, 6500),
            ('Bakso Urat', 15000, 8000),
            ('Es Jeruk Segar', 7000, 2500),
            ('Roti Bakar Coklat', 10000, 4000),
            ('Jus Alpukat', 12000, 5000),
            ('Nasi Uduk Komplit', 12000, 5500),
            ('Gorengan Campur', 5000, 2000),
            ('Pisang Goreng Keju', 8000, 3000),
            ('Indomie Telur', 8000, 3500),
            ('Teh Tarik', 10000, 3500),
        ],
        'catatan_ops': [
            "Ramai sekali hari ini", "Sepi karena hujan deras", "Orderan GoFood membludak",
            "Diskon 10% untuk pelanggan setia", "Banyak anak sekolah beli",
            "Normal seperti biasa", "Cukup sibuk siang hari", "Stok hampir habis",
            "Cuaca cerah pelanggan ramai", "Ada acara kantor pesan banyak",
            "", "", "",
        ],
        'catatan_modal': [
            "Beli etalase baru", "Service kompor gas", "Beli stok bahan sebulan",
            "Beli freezer bekas", "Renovasi dapur kecil", "Beli blender baru",
        ]
    },
    'Retail': {
        'produk': [
            ('Kaus Polos', 35000, 18000),
            ('Kaus Sablon Custom', 55000, 25000),
            ('Celana Jeans', 120000, 65000),
            ('Topi Snapback', 45000, 20000),
            ('Sandal Jepit Premium', 25000, 12000),
            ('Tas Selempang', 75000, 35000),
            ('Sarung Tangan Motor', 30000, 15000),
            ('Masker Kain 3 Ply', 10000, 3500),
            ('Kaos Kaki Panjang', 15000, 6000),
            ('Dompet Kulit Sintetis', 50000, 22000),
        ],
        'catatan_ops': [
            "Weekend laku keras", "Sepi hari kerja", "Ada bazaar kampus",
            "Promo beli 2 gratis 1", "Stok model baru datang",
            "Normal penjualan", "Pelanggan banyak tanya online",
            "", "", "",
        ],
        'catatan_modal': [
            "Beli stok grosir Tanah Abang", "Sewa lapak baru di pasar",
            "Beli rak display", "Modal iklan Instagram", "Beli mannequin display",
        ]
    },
    'Jasa': {
        'produk': [
            ('Reparasi AC', 150000, 50000),
            ('Service Motor Ringan', 75000, 25000),
            ('Cuci Motor', 20000, 5000),
            ('Cuci Mobil', 50000, 15000),
            ('Potong Rambut Pria', 25000, 5000),
            ('Jahit Baju', 50000, 15000),
            ('Print Dokumen', 5000, 2000),
            ('Fotocopy', 500, 200),
            ('Laundry Kiloan', 7000, 3000),
            ('Service HP', 100000, 30000),
        ],
        'catatan_ops': [
            "Pelanggan baru datang", "Repeat order dari langganan",
            "Banyak service hari ini", "Hujan jadi sepi", "Normal biasa",
            "Ada promo khusus member", "Weekend ramai sekali",
            "", "", "",
        ],
        'catatan_modal': [
            "Beli alat service baru", "Perpanjang sewa tempat",
            "Beli mesin cuci baru", "Upgrade peralatan", "Service mesin utama",
        ]
    },
    'Lainnya': {
        'produk': [
            ('Pulsa Elektrik', 0, 0),
            ('Token Listrik', 0, 0),
            ('Isi Ulang Air Galon', 6000, 3000),
            ('Gas Elpiji 3kg', 20000, 16000),
            ('Rokok Eceran', 3000, 2500),
            ('Bensin Eceran', 10000, 8500),
        ],
        'catatan_ops': [
            "Normal seperti biasa", "Banyak yang beli pulsa",
            "Stok gas habis siang", "Hari biasa", "",
            "", "",
        ],
        'catatan_modal': [
            "Beli stok gas sebulan", "Modal tambahan pulsa", "Beli etalase kecil",
        ]
    }
}

jenis_pengeluaran_list = ['operasional', 'modal']

# Mulai dari 6 bulan lalu agar data realistis
start_date = datetime(2025, 9, 20)

data = []
# Header sesuai template download PANTAUIN
data.append([
    'tanggal', 'kategori', 'nama_produk', 'kuantitas', 'harga_modal',
    'pemasukan', 'pengeluaran', 'jenis_pengeluaran', 'jumlah_pelanggan', 'catatan'
])

for i in range(200):
    current_date = start_date + timedelta(days=i)
    
    # 85% operasional, 15% modal
    is_modal = random.random() < 0.15
    jenis = 'modal' if is_modal else 'operasional'
    
    # Pilih kategori
    kategori = random.choice(list(kategori_produk.keys()))
    kat_data = kategori_produk[kategori]
    
    # Pilih produk random dari kategori
    produk_nama, harga_jual, harga_modal_satuan = random.choice(kat_data['produk'])
    
    # Kuantitas berdasarkan jenis usaha
    if kategori == 'Makanan & Minuman':
        kuantitas = random.randint(5, 50)
    elif kategori == 'Retail':
        kuantitas = random.randint(1, 15)
    elif kategori == 'Jasa':
        kuantitas = random.randint(1, 10)
    else:
        kuantitas = random.randint(2, 20)
    
    # Harga modal per unit (dengan sedikit variasi)
    harga_modal = int(harga_modal_satuan * random.uniform(0.9, 1.1)) if harga_modal_satuan > 0 else 0
    
    # Pemasukan = harga jual * kuantitas (dengan variasi)
    if harga_jual > 0:
        pemasukan = int(harga_jual * kuantitas * random.uniform(0.85, 1.15))
    else:
        # Untuk pulsa/token, margin tipis
        pemasukan = random.randint(50000, 300000)
    
    # Pengeluaran
    if is_modal:
        pengeluaran = random.randint(500000, 5000000)
        catatan = random.choice(kat_data['catatan_modal'])
    else:
        # Operasional: 20-50% dari pemasukan
        pengeluaran = int(pemasukan * random.uniform(0.2, 0.5))
        catatan = random.choice(kat_data['catatan_ops'])
    
    # Jumlah pelanggan
    pelanggan = max(1, int(kuantitas * random.uniform(0.5, 1.0)))
    
    data.append([
        current_date.strftime('%Y-%m-%d'),
        kategori,
        produk_nama,
        kuantitas,
        harga_modal,
        pemasukan,
        pengeluaran,
        jenis,
        pelanggan,
        catatan
    ])

output_path = r'C:\laragon\www\PANTAUIN\Contoh_200_Transaksi_PANTAUIN.csv'
with open(output_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(data)

print(f"✅ Selesai! {len(data)-1} baris transaksi disimpan ke: {output_path}")
