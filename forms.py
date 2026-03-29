# pyre-ignore-all-errors
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, FloatField, SelectField, IntegerField, RadioField, TextAreaField, SelectMultipleField, BooleanField, widgets
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, Optional, InputRequired
from flask_wtf.file import FileField, FileRequired, FileAllowed
from datetime import date

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

# MultiCheckboxField class is used for multi-select
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
    nama_produk = StringField('Nama Produk (Opsional)', validators=[Length(max=100, message="Maksimal 100 karakter.")])
    kuantitas = IntegerField('Kuantitas (Opsional)', default=0)
    harga_modal = FloatField('Harga Modal/HPP (Per Unit)', default=0.0)
    # Menggunakan FloatField yang akan dimanipulasi di JS untuk mask rupiah
    pemasukan = FloatField('Total Pemasukan (Rp)', default=0, validators=[InputRequired("Harus mengisi pemasukan. Isi 0 jika nihil.")])
    pengeluaran = FloatField('Total Pengeluaran (Rp)', default=0, validators=[InputRequired("Harus mengisi pengeluaran. Isi 0 jika nihil.")])
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
    ijin_usaha_jenis = MultiCheckboxField('Ijin Usaha yang dimiliki', choices=[
        ('SIUP', 'SIUP'), ('TDP', 'TDP'), ('HO', 'HO'),
        ('SPTIK', 'SPTIK'), ('AKTE', 'AKTE'), ('PIRT', 'PIRT')
    ])
    ijin_usaha_nomor = StringField('Nomor Ijin Usaha', validators=[Length(max=100)])
    ijin_usaha_tanggal = DateField('Tanggal Ijin Usaha (Opsional)', format='%Y-%m-%d', validators=[Optional()])
    ijin_usaha = StringField('Ijin Usaha Gabungan (Hidden)', validators=[Length(max=255)])
    
    haki_jenis = MultiCheckboxField('Perlindungan HAKI & Sertifikasi HALAL', choices=[
        ('Merk', 'Merk'), ('Cipta', 'Cipta'), ('Paten', 'Paten'), ('Halal', 'Halal')
    ])
    haki = StringField('HAKI Gabungan (Hidden)', validators=[Length(max=255)])
    merk_dagang = StringField('Merk Dagang', validators=[Length(max=100)])
    
    # BAGIAN 1: Tenaga Kerja
    tk_tetap = IntegerField('Jumlah Tenaga Kerja Tetap', default=0, validators=[Optional()])
    tk_tidak_tetap = IntegerField('Jumlah Tenaga Kerja Tidak Tetap', default=0, validators=[Optional()])
    
    # BAGIAN 2: Data Produksi & Pemasaran (JSON-destined)
    # Jenis Produk sekarang ditangani dinamis dari template (array HTML: jenis_produk[])
    
    kapasitas_produksi_jumlah = StringField('Kapasitas Produksi per (unit/kg/ton/liter)')
    kapasitas_produksi_waktu = StringField('Waktu Produksi (hari/bulan/tahun)')
    omzet_usaha = StringField('Omzet Usaha (Rp/hari/bulan/tahun)')
    
    teknologi_produksi = RadioField('Teknologi Produksi', choices=[('Tradisional', 'Tradisional'), ('Tepat guna', 'Tepat guna'), ('Modern', 'Modern')], default='')
    teknologi_pengemasan = RadioField('Teknologi Pengemasan', choices=[('Tradisional', 'Tradisional'), ('Tepat guna', 'Tepat guna'), ('Modern', 'Modern')], default='')
    
    bahan_baku_asal = RadioField('Asal bahan baku', choices=[('Lokal', 'Lokal'), ('Lain daerah', 'Lain daerah')], default='')
    bahan_baku_asal_lain = StringField('Sebutkan daerah asal bahan baku')
    bahan_baku_ketersediaan = RadioField('Ketersediaan bahan baku', choices=[('Kurang', 'Kurang'), ('Cukup', 'Cukup'), ('Melimpah', 'Melimpah')], default='')
    
    desain_produk = RadioField('Desain Produk', choices=[('Marketable', 'Marketable'), ('Tidak marketable', 'Tidak marketable')], default='')
    
    kemasan_bahan = MultiCheckboxField('Bahan Kemasan', choices=[('Plastik', 'Plastik'), ('Stereoform', 'Stereoform'), ('Kardus', 'Kardus'), ('Mika', 'Mika'), ('Lainnya', 'Lainnya')])
    kemasan_bahan_lain = StringField('Bahan kemasan lainnya')
    kemasan_ketebalan = StringField('Ketebalan bahan (mm)')
    kemasan_desain = RadioField('Desain Kemasan', choices=[('Menarik', 'Menarik'), ('Tidak menarik', 'Tidak menarik')], default='')
    
    segmen_atas = IntegerField('Segmen konsumen atas (%)', default=0, validators=[Optional()])
    segmen_menengah = IntegerField('Segmen konsumen menengah (%)', default=0, validators=[Optional()])
    segmen_bawah = IntegerField('Segmen konsumen bawah (%)', default=0, validators=[Optional()])
    
    pemasaran_lokal = IntegerField('Lokal (%)', default=0, validators=[Optional()])
    pemasaran_regional = IntegerField('Regional (%)', default=0, validators=[Optional()])
    pemasaran_ekspor = IntegerField('Ekspor (%)', default=0, validators=[Optional()])
    
    wilayah_pemasaran = TextAreaField('Sebutkan daerah pemasaran selama ini (1, 2, 3...)')
    
    sistem_retail = BooleanField('Retail')
    sistem_distributor = BooleanField('Distributor')
    sistem_lainnya = StringField('Sistem penjualan lainnya')
    
    # BAGIAN 3: Komitmen
    komitmen_1 = BooleanField('Mengirim profil perusahaan')
    komitmen_2 = BooleanField('Mengirim daftar jenis produk')
    komitmen_3 = BooleanField('Mengirim E-Digital Produk')
    komitmen_4 = BooleanField('Mengirimkan Sample Produk')
    komitmen_5 = BooleanField('Mengikuti pameran yang difasilitasi ITPC')
    
    submit = SubmitField('Simpan Profil Perusahaan')
