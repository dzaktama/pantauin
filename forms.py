from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, FloatField, SelectField, IntegerField, RadioField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp
from flask_wtf.file import FileField, FileRequired, FileAllowed
from datetime import date

class LoginForm(FlaskForm):
    """Form Login Pengguna UMKM."""
    username = StringField('Nama Pengguna', validators=[
        DataRequired(message="Nama pengguna tidak boleh kosong.")
    ])
    password = PasswordField('Kata Sandi', validators=[
        DataRequired(message="Kata sandi tidak boleh kosong.")
    ])
    submit = SubmitField('Masuk ke Akun Saya')

class RegisterForm(FlaskForm):
    """Form Pendaftaran Pengguna UMKM Baru yang aman."""
    username = StringField('Nama Pengguna Terdaftar', validators=[
        DataRequired(message="Nama pengguna tidak boleh kosong."),
        Length(min=4, max=50, message="Nama pengguna harus 4-50 karakter."),
        Regexp(r'^\w+$', message="Gunakan hanya huruf, angka, atau garis bawah.")
    ])
    password = PasswordField('Kata Sandi Baru', validators=[
        DataRequired(message="Kata sandi tidak boleh kosong."),
        Length(min=6, message="Kata sandi minimal 6 karakter demi keamanan.")
    ])
    confirm_password = PasswordField('Ulangi Kata Sandi', validators=[
        DataRequired(message="Ulangi kembali kata sandi di atas."),
        EqualTo('password', message="Kata sandi yang Anda masukkan tidak cocok.")
    ])
    submit = SubmitField('Daftar Akun Baru')

class TransaksiForm(FlaskForm):
    """Form Pencatatan Transaksi Manual."""
    tanggal = DateField('Tanggal', format='%Y-%m-%d', default=date.today, validators=[DataRequired("Tanggal tidak boleh kosong.")])
    kategori = SelectField('Kategori Penjualan', choices=[
        ('Makanan & Minuman', 'Makanan & Minuman'),
        ('Retail', 'Retail (Barang Jadi)'),
        ('Jasa', 'Layanan Jasa'),
        ('Lainnya', 'Lainnya')
    ], validators=[DataRequired("Kategori wajib dipilih.")])
    # Menggunakan FloatField yang akan dimanipulasi di JS untuk mask rupiah
    pemasukan = FloatField('Total Pemasukan (Rp)', default=0, validators=[DataRequired("Harus mengisi pemasukan. Isi 0 jika nihil.")])
    pengeluaran = FloatField('Total Pengeluaran (Rp)', default=0, validators=[DataRequired("Harus mengisi pengeluaran. Isi 0 jika nihil.")])
    jenis_pengeluaran = RadioField('Jenis Pengeluaran', choices=[('operasional', 'Operasional'), ('modal', 'Modal')], default='operasional')
    jumlah_pelanggan = IntegerField('Jumlah Pelanggan', default=0)
    catatan = TextAreaField('Catatan Hari Ini (Opsional)', validators=[Length(max=200, message="Maksimal 200 karakter.")])
    submit = SubmitField('Simpan Transaksi')

class UploadCSVForm(FlaskForm):
    """Form Pengunggahan Laporan CSV."""
    file_csv = FileField('Pilih File Laporan (.csv)', validators=[
        FileRequired(message="Anda belum memilih file CSV."),
        FileAllowed(['csv'], message="Mohon pastikan format file yang diunggah adalah .csv")
    ])
    submit = SubmitField('Unggah File Ini')

class BukuKasForm(FlaskForm):
    """Form untuk Membuat / Mengelola Pemisahan File Laporan Proyek."""
    nama_buku = StringField('Nama Buku Kas Baru', validators=[
        DataRequired(message="Nama buku kas tidak boleh kosong."),
        Length(max=100, message="Nama buku kas maksimal 100 karakter.")
    ])
    submit = SubmitField('Buat Buku Kas')

class ProfilPerusahaanForm(FlaskForm):
    """Form 3 Halaman Profil Perusahaan Lengkap"""
    # BAGIAN 1: Identitas
    nama_perusahaan = StringField('Nama Perusahaan', validators=[DataRequired(), Length(max=150)])
    contact_person = StringField('Contact Person', validators=[DataRequired(), Length(max=100)])
    jabatan = StringField('Jabatan', validators=[Length(max=50)])
    bentuk_usaha = SelectField('Bentuk Perusahaan', choices=[
        ('PT', 'PT'), ('CV', 'CV'), ('Firma', 'Firma'), ('PD', 'PD'),
        ('UD', 'UD'), ('PIRT', 'PIRT'), ('IRT', 'IRT'), ('Lainnya', 'Lain-lain')
    ], validators=[DataRequired()])
    jenis_usaha = StringField('Jenis Usaha', validators=[DataRequired(), Length(max=150)])
    tahun_berdiri = StringField('Lama Usaha (tahun berdiri)', validators=[Length(max=10)])
    
    # BAGIAN 1: Alamat
    alamat_jalan = StringField('Jalan', validators=[Length(max=255)])
    alamat_rtrw = StringField('RT/RW', validators=[Length(max=50)])
    alamat_desa = StringField('Desa / Kelurahan', validators=[Length(max=100)])
    alamat_kecamatan = StringField('Kecamatan', validators=[Length(max=100)])
    alamat_kabkota = StringField('Kab / Kota', validators=[DataRequired(), Length(max=100)])
    alamat_provinsi = StringField('Provinsi', validators=[DataRequired(), Length(max=100)])
    kode_pos = StringField('Kode Pos', validators=[Length(max=20)])
    
    # BAGIAN 1: Kontak
    no_telp = StringField('No Telephone / Hand Phone', validators=[DataRequired(), Length(max=50)])
    email_web = StringField('Web / E-mail / Blog', validators=[Length(max=100)])
    
    # BAGIAN 1: Legalitas
    ijin_usaha = StringField('Ijin Usaha (SIUP/TDP/Akte dll)', validators=[Length(max=255)])
    haki = StringField('Sertifikasi HAKI/HALAL', validators=[Length(max=255)])
    merk_dagang = StringField('Merk Dagang', validators=[Length(max=100)])
    
    # BAGIAN 1: Tenaga Kerja
    tk_tetap = IntegerField('Jumlah Tenaga Kerja Tetap', default=0)
    tk_tidak_tetap = IntegerField('Jumlah Tenaga Kerja Tidak Tetap', default=0)
    
    # BAGIAN 2: Data Produksi & Pemasaran (JSON-destined)
    jenis_produk = TextAreaField('Jenis-jenis produk yang dihasilkan (1 - 5)')
    kapasitas_produksi = StringField('Kapasitas Produksi & Waktu')
    omzet_usaha = StringField('Omzet Usaha (Rp/bln/tahun)')
    
    teknologi_produksi = SelectField('Teknologi Produksi', choices=[('Tradisional', 'Tradisional'), ('Tepat Guna', 'Tepat Guna'), ('Modern', 'Modern'), ('', '- Bebas -')], default='')
    teknologi_pengemasan = SelectField('Teknologi Pengemasan', choices=[('Tradisional', 'Tradisional'), ('Tepat Guna', 'Tepat Guna'), ('Modern', 'Modern'), ('', '- Bebas -')], default='')
    
    bahan_baku_asal = StringField('Asal bahan baku')
    bahan_baku_ketersediaan = SelectField('Ketersediaan bahan baku', choices=[('Kurang', 'Kurang'), ('Cukup', 'Cukup'), ('Melimpah', 'Melimpah'), ('', '- Bebas -')], default='')
    
    desain_produk = SelectField('Desain Produk', choices=[('Marketable', 'Marketable'), ('Tidak Marketable', 'Tidak Marketable'), ('', '- Bebas -')], default='')
    kemasan_bahan = StringField('Bahan Kemasan (Plastik/Mika/dll)')
    kemasan_desain = SelectField('Desain Kemasan', choices=[('Menarik', 'Menarik'), ('Tidak Menarik', 'Tidak Menarik'), ('', '- Bebas -')], default='')
    
    segmen_pasar = StringField('Segmen Target Pasar Utama (Atas %, Menengah %, Bawah %)')
    daerah_pemasaran = StringField('Daerah Pemasaran Lokal, Regional, Ekspor (%)')
    wilayah_pemasaran = TextAreaField('Sebutkan Wilayah Pemasaran secara spesifik')
    sistem_penjualan = StringField('Sistem Penjualan (Retail/Distributor dll)')
    
    # BAGIAN 3: Komitmen
    komitmen = TextAreaField('Kesediaan / Komitmen yang tersedia diberikan (pisahkan dengan koma)')
    
    submit = SubmitField('Simpan Profil Perusahaan')
