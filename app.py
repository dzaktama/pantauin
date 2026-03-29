# pyre-ignore-all-errors
import os
import csv
import io
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from config import Config
from models import db, User, Transaksi, BukuKas, ProfilPerusahaan, AktivitasLog, log_activity
from forms import LoginForm, RegisterForm, TransaksiForm, BukuKasForm, UploadCSVForm, ProfilPerusahaanForm
from flask_caching import Cache
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from calculator import hitung_health_score, analisis_tren_produk
import gemini_helper
from pdf_generator import generate_pdf_report

# Ekstensi
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        db.create_all()

    # --- ERROR HANDLERS ---
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', pesan="Halaman rute tidak ditemukan."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', pesan="Gagal memproses permintaan, server sedang sibuk."), 500

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Silakan masuk menggunakan akun Anda terlebih dahulu.", "warning")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.context_processor
    def inject_buku_kas():
        if 'user_id' in session:
            daftar_buku = BukuKas.query.filter_by(user_id=session['user_id']).order_by(BukuKas.created_at.asc()).all()
            # Set default session ID jika kosong namun user memiliki buku
            if 'buku_kas_id' not in session and daftar_buku:
                session['buku_kas_id'] = daftar_buku[0].id
            
            buku_aktif = next((b for b in daftar_buku if b.id == session.get('buku_kas_id')), None)
            return dict(daftar_buku=daftar_buku, buku_kas_aktif=buku_aktif)
        return dict(daftar_buku=[], buku_kas_aktif=None)

    # --- AUTH ROUTES ---
    @app.route('/', methods=['GET'])
    def index():
        if 'user_id' in session: return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        try:
            form = LoginForm()
            if form.validate_on_submit():
                user = User.query.filter_by(username=form.username.data).first()
                if user and user.check_password(form.password.data):
                    session['user_id'] = user.id
                    session['username'] = user.username
                    log_activity(user.id, session.get('buku_kas_id'), f"Pengguna {user.username} berhasil login.", "Auth", "info")
                    flash(f"Halo kembali, {user.username}!", "success")
                    return redirect(url_for('dashboard'))
                flash("Kredensial tidak cocok, silakan coba lagi.", "error")
            return render_template('login.html', form=form)
        except Exception:
            return render_template('error.html', pesan="Terjadi kesalahan saat masuk."), 500

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        try:
            form = RegisterForm()
            if form.validate_on_submit():
                if User.query.filter_by(username=form.username.data).first():
                    flash("Nama pengguna ini sudah dipakai.", "error")
                    return render_template('register.html', form=form)
                
                u = User(username=form.username.data)
                u.set_password(form.password.data)
                db.session.add(u)
                db.session.flush() # flush agar mendapatkan u.id

                # Buat Buku Kas Pertama Secara Otomatis
                bk = BukuKas(user_id=u.id, nama_buku="Buku Kas Utama")
                db.session.add(bk)
                
                db.session.commit()
                flash("Sukses mendaftar! Yuk mulai sesi barumu.", "success")
                return redirect(url_for('login'))
            return render_template('register.html', form=form)
        except Exception:
            db.session.rollback()
            return render_template('error.html', pesan="Permintaan ditolak."), 500

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        session.clear()
        return redirect(url_for('login'))

    # --- PROJECT (BUKU KAS) ROUTES ---
    @app.route('/buku-kas', methods=['GET', 'POST'])
    @login_required
    def buku_kas_manager():
        form = BukuKasForm()
        if form.validate_on_submit():
            bk = BukuKas(user_id=session['user_id'], nama_buku=form.nama_buku.data)
            db.session.add(bk)
            db.session.commit()
            log_activity(session['user_id'], bk.id, f"Membuat buku kas baru: '{bk.nama_buku}'.", "BukuKas", "tambah")
            flash(f"Buku Kas '{bk.nama_buku}' berhasil dibuat!", "success")
            return redirect(url_for('buku_kas_manager'))
            
        # Hitung statistik untuk masing-masing buku kas
        daftar_buku = BukuKas.query.filter_by(user_id=session['user_id']).all()
        stats = {}
        for bk in daftar_buku:
            transaksi = Transaksi.query.filter_by(buku_kas_id=bk.id).all()
            total_in = sum(t.pemasukan for t in transaksi)
            total_out = sum(t.pengeluaran for t in transaksi)
            margin = total_in - total_out
            stats[bk.id] = {
                'count': len(transaksi),
                'pemasukan': total_in,
                'pengeluaran': total_out,
                'margin': margin
            }
            
        return render_template('buku_kas.html', form=form, stats=stats)

    @app.route('/buku-kas/edit/<int:buku_id>', methods=['POST'])
    @login_required
    def edit_buku_kas(buku_id):
        bk = BukuKas.query.filter_by(id=buku_id, user_id=session['user_id']).first_or_404()
        new_name = request.form.get('nama_buku_baru')
        if new_name and new_name.strip():
            nama_lama = bk.nama_buku
            bk.nama_buku = new_name.strip()
            db.session.commit()
            log_activity(session['user_id'], bk.id, f"Mengubah nama buku kas dari '{nama_lama}' menjadi '{bk.nama_buku}'.", "BukuKas", "ubah")
            flash(f"Nama buku berhasil diubah menjadi '{bk.nama_buku}'.", "success")
        else:
            flash("Nama buku tidak boleh kosong.", "error")
        return redirect(url_for('buku_kas_manager'))

    @app.route('/buku-kas/delete/<int:buku_id>', methods=['POST'])
    @login_required
    def delete_buku_kas(buku_id):
        bk = BukuKas.query.filter_by(id=buku_id, user_id=session['user_id']).first_or_404()
        
        total_buku = BukuKas.query.filter_by(user_id=session['user_id']).count()
        if total_buku <= 1:
            flash("Gagal: Anda harus memiliki setidaknya satu Buku Kas.", "error")
            return redirect(url_for('buku_kas_manager'))
            
        nama_buku = bk.nama_buku
        db.session.delete(bk)
        db.session.commit()
        log_activity(session['user_id'], None, f"Menghapus secara permanen buku kas '{nama_buku}'.", "BukuKas", "hapus")
        
        if session.get('buku_kas_id') == buku_id:
            session.pop('buku_kas_id', None)
            cache.clear()
            
        flash(f"Buku Kas '{nama_buku}' berhasil dihapus permanen.", "success")
        return redirect(url_for('buku_kas_manager'))

    @app.route('/buku-kas/switch/<int:buku_id>', methods=['POST'])
    @login_required
    def switch_buku_kas(buku_id):
        bk = BukuKas.query.filter_by(id=buku_id, user_id=session['user_id']).first_or_404()
        session['buku_kas_id'] = bk.id
        
        # Tangkap parameter destinasi dari tombol yang diklik
        destination = request.form.get('destination', 'dashboard')
        flash(f"Berpindah ke proyek: {bk.nama_buku}", "info")
        
        if destination == 'input':
            return redirect(url_for('input_transaksi'))
        elif destination == 'riwayat':
            return redirect(url_for('riwayat_transaksi'))
        else:
            return redirect(url_for('dashboard'))

    @app.route('/buku-kas/reset/<int:buku_id>', methods=['POST'])
    @login_required
    def reset_buku_kas(buku_id):
        # Pastikan user pemilik asli buku kas
        bk = BukuKas.query.filter_by(id=buku_id, user_id=session['user_id']).first_or_404()
        
        try:
            # Hapus semua transaksi massal
            jumlah_dihapus = Transaksi.query.filter_by(buku_kas_id=bk.id).delete()
            db.session.commit()
            
            # Bersihkan cache kalkulator jika buku sedang aktif
            if session.get('buku_kas_id') == bk.id:
                cache.clear()
                
            flash(f"Data Transaksi pada Buku '{bk.nama_buku}' ({jumlah_dihapus} baris) berhasil dikosongkan. Profil Perusahaan tetap aman.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Gagal mengosongkan data transaksi: {str(e)}", "danger")
            
        return redirect(url_for('buku_kas_manager'))

    # --- CORE ROUTES ---
    @app.route('/panduan-metrik')
    @login_required
    def panduan_metrik():
        return render_template('panduan_metrik.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: 
                return redirect(url_for('buku_kas_manager'))
            
            # Wajib isi profil perusahaan jika belum
            profil = ProfilPerusahaan.query.filter_by(buku_kas_id=buku_kas_id).first()
            if not profil:
                flash("Isi profil perusahaan usahamu terlebih dahulu sebelum menjelajah dasbor.", "warning")
                return redirect(url_for('edit_profil_perusahaan'))
            
            # Filter Parameter Periode Dashboard
            periode = request.args.get('periode', 30, type=int)
            if periode not in [30, 60, 90, 0]:
                periode = 30
                
            cache_key = f"dashboard_bk_{buku_kas_id}_{periode}_{datetime.now().strftime('%Y%m%d')}_v3"
            data = cache.get(cache_key)
            saran_gemini = cache.get(f"saran_bk_{buku_kas_id}")

            if data is None or saran_gemini is None:
                transaksi_list = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                
                # Jika periode=0 (Semua), hitung jumlah hari dari transaksi pertama ke hari ini
                actual_periode = periode
                if periode == 0 and transaksi_list:
                    from datetime import date as date_cls
                    first_date = transaksi_list[0].tanggal
                    actual_periode = (date_cls.today() - first_date).days + 1
                elif periode == 0:
                    actual_periode = 30
                    
                data = hitung_health_score(transaksi_list, periode_grafik=actual_periode)

                # Panggil Gemini jika data valid
                if data['is_cukup']:
                    saran_gemini = gemini_helper.get_dashboard_suggestion(
                        data['skor'], data['total_pemasukan_minggu_ini'], 
                        data['total_pengeluaran_minggu_ini'], data['tren_status'],
                        data.get('catatan_mingguan', []),
                        data.get('data_produk'),
                        data.get('advanced_analytics')
                    )
                else:
                    saran_gemini = "Saran belum tersedia. Lengkapi pencatatan laporan buku ini setidaknya 14 hari."

                cache.set(cache_key, data)
                cache.set(f"saran_bk_{buku_kas_id}", saran_gemini)

            return render_template('dashboard.html', data=data, saran_gemini=saran_gemini, periode=periode)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template('error.html', pesan=f"Gagal merender dasbor analisis! Detail: {str(e)}"), 500

    @app.route('/profil-perusahaan', methods=['GET', 'POST'])
    @login_required
    def edit_profil_perusahaan():
        buku_kas_id = session.get('buku_kas_id')
        if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
        buku_aktif = BukuKas.query.get_or_404(buku_kas_id)
        profil = ProfilPerusahaan.query.filter_by(buku_kas_id=buku_kas_id).first()
        
        form = ProfilPerusahaanForm(obj=profil)
        
        if request.method == 'GET' and profil and profil.detil_industri:
            try:
                dt_extr = json.loads(profil.detil_industri)
                
                # Backward compatibility for jenis_produk
                if 'jenis_produk' in dt_extr and isinstance(dt_extr['jenis_produk'], str):
                    dt_extr['jenis_produk'] = [x.strip() for x in dt_extr['jenis_produk'].replace('\n', ',').split(',') if x.strip()]
                elif 'jenis_produk' not in dt_extr:
                    jp_temp = [dt_extr.get(f'jenis_produk_{i}') for i in range(1, 6) if dt_extr.get(f'jenis_produk_{i}')]
                    if jp_temp:
                        dt_extr['jenis_produk'] = jp_temp
                
                # Ijin Usaha & HAKI
                form.ijin_usaha_jenis.data = dt_extr.get('ijin_usaha_jenis', [])
                form.ijin_usaha_nomor.data = dt_extr.get('ijin_usaha_nomor', '')
                if dt_extr.get('ijin_usaha_tanggal'):
                    try:
                        form.ijin_usaha_tanggal.data = datetime.strptime(dt_extr.get('ijin_usaha_tanggal'), '%Y-%m-%d').date()
                    except: pass
                form.haki_jenis.data = dt_extr.get('haki_jenis', [])
                
                # Jenis Produk dinamis (tidak pakai form WTForms)
                
                form.kapasitas_produksi_jumlah.data = dt_extr.get('kapasitas_produksi_jumlah', '')
                form.kapasitas_produksi_waktu.data = dt_extr.get('kapasitas_produksi_waktu', '')
                form.omzet_usaha.data = dt_extr.get('omzet_usaha', '')
                
                form.teknologi_produksi.data = dt_extr.get('teknologi_produksi', '')
                form.teknologi_pengemasan.data = dt_extr.get('teknologi_pengemasan', '')
                
                form.bahan_baku_asal.data = dt_extr.get('bahan_baku_asal', '')
                form.bahan_baku_asal_lain.data = dt_extr.get('bahan_baku_asal_lain', '')
                form.bahan_baku_ketersediaan.data = dt_extr.get('bahan_baku_ketersediaan', '')
                
                form.desain_produk.data = dt_extr.get('desain_produk', '')
                
                form.kemasan_bahan.data = dt_extr.get('kemasan_bahan', [])
                form.kemasan_bahan_lain.data = dt_extr.get('kemasan_bahan_lain', '')
                form.kemasan_ketebalan.data = dt_extr.get('kemasan_ketebalan', '')
                form.kemasan_desain.data = dt_extr.get('kemasan_desain', '')
                
                form.segmen_atas.data = dt_extr.get('segmen_atas', 0)
                form.segmen_menengah.data = dt_extr.get('segmen_menengah', 0)
                form.segmen_bawah.data = dt_extr.get('segmen_bawah', 0)
                
                form.pemasaran_lokal.data = dt_extr.get('pemasaran_lokal', 0)
                form.pemasaran_regional.data = dt_extr.get('pemasaran_regional', 0)
                form.pemasaran_ekspor.data = dt_extr.get('pemasaran_ekspor', 0)
                
                form.wilayah_pemasaran.data = dt_extr.get('wilayah_pemasaran', '')
                
                form.sistem_retail.data = dt_extr.get('sistem_retail', False)
                form.sistem_distributor.data = dt_extr.get('sistem_distributor', False)
                form.sistem_lainnya.data = dt_extr.get('sistem_lainnya', '')
                
                form.komitmen_1.data = dt_extr.get('komitmen_1', False)
                form.komitmen_2.data = dt_extr.get('komitmen_2', False)
                form.komitmen_3.data = dt_extr.get('komitmen_3', False)
                form.komitmen_4.data = dt_extr.get('komitmen_4', False)
                form.komitmen_5.data = dt_extr.get('komitmen_5', False)
            except:
                dt_extr = {}
        else:
            dt_extr = {}

        if form.validate_on_submit():
            # Build ijin_usaha gabungan and haki gabungan for display purposes or backward compatibility
            ij_arr = form.ijin_usaha_jenis.data or []
            ij_str = " / ".join(ij_arr)
            ij_tgl = form.ijin_usaha_tanggal.data.strftime('%Y-%m-%d') if form.ijin_usaha_tanggal.data else ''
            ijin_usaha_gabungan = f"{ij_str}"
            if form.ijin_usaha_nomor.data:
                ijin_usaha_gabungan += f" No: {form.ijin_usaha_nomor.data}"
            if ij_tgl:
                ijin_usaha_gabungan += f" Tgl: {ij_tgl}"
            
            form.ijin_usaha.data = ijin_usaha_gabungan if ijin_usaha_gabungan.strip() else ""
            
            hk_arr = form.haki_jenis.data or []
            form.haki.data = " / ".join(hk_arr)
            
            dt_extr = {
                'ijin_usaha_jenis': form.ijin_usaha_jenis.data,
                'ijin_usaha_nomor': form.ijin_usaha_nomor.data,
                'ijin_usaha_tanggal': ij_tgl,
                'haki_jenis': form.haki_jenis.data,
                
                # jenis produk array dinamis diambil dari request
                'jenis_produk': [jp for jp in request.form.getlist('jenis_produk[]') if jp.strip()],
                
                'kapasitas_produksi_jumlah': form.kapasitas_produksi_jumlah.data,
                'kapasitas_produksi_waktu': form.kapasitas_produksi_waktu.data,
                'omzet_usaha': form.omzet_usaha.data,
                
                'teknologi_produksi': form.teknologi_produksi.data,
                'teknologi_pengemasan': form.teknologi_pengemasan.data,
                
                'bahan_baku_asal': form.bahan_baku_asal.data,
                'bahan_baku_asal_lain': form.bahan_baku_asal_lain.data,
                'bahan_baku_ketersediaan': form.bahan_baku_ketersediaan.data,
                
                'desain_produk': form.desain_produk.data,
                
                'kemasan_bahan': form.kemasan_bahan.data,
                'kemasan_bahan_lain': form.kemasan_bahan_lain.data,
                'kemasan_ketebalan': form.kemasan_ketebalan.data,
                'kemasan_desain': form.kemasan_desain.data,
                
                'segmen_atas': form.segmen_atas.data,
                'segmen_menengah': form.segmen_menengah.data,
                'segmen_bawah': form.segmen_bawah.data,
                
                'pemasaran_lokal': form.pemasaran_lokal.data,
                'pemasaran_regional': form.pemasaran_regional.data,
                'pemasaran_ekspor': form.pemasaran_ekspor.data,
                
                'wilayah_pemasaran': form.wilayah_pemasaran.data,
                
                'sistem_retail': form.sistem_retail.data,
                'sistem_distributor': form.sistem_distributor.data,
                'sistem_lainnya': form.sistem_lainnya.data,
                
                'komitmen_1': form.komitmen_1.data,
                'komitmen_2': form.komitmen_2.data,
                'komitmen_3': form.komitmen_3.data,
                'komitmen_4': form.komitmen_4.data,
                'komitmen_5': form.komitmen_5.data,
            }
            
            if not profil:
                profil = ProfilPerusahaan(buku_kas_id=buku_kas_id)
                db.session.add(profil)
            
            form.populate_obj(profil)
            profil.detil_industri = json.dumps(dt_extr)
            profil.buku_kas_id = buku_kas_id
            
            db.session.commit()
            flash("Profil Perusahaan berhasil disimpan!", "success")
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST' and not form.validate():
            # Jika ada error validasi di field tertentu
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Error pada {getattr(form, field).label.text}: {error}", "error")
            flash("Mohon periksa kembali form Anda. Beberapa data wajib belum diisi dengan benar.", "warning")

        return render_template('profil_perusahaan.html', form=form, nama_buku=buku_aktif.nama_buku, profil=profil, dt_extr=dt_extr)

    @app.route('/input', methods=['GET', 'POST'])
    @app.route('/input/<int:t_id>', methods=['GET', 'POST'])
    @login_required
    def input_transaksi(t_id=None):
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            form = TransaksiForm()
            t = None
            if t_id:
                t = Transaksi.query.filter_by(id=t_id, buku_kas_id=buku_kas_id).first_or_404()
            else:
                t = Transaksi(user_id=session['user_id'], buku_kas_id=buku_kas_id)
                
            if form.validate_on_submit():
                t.tanggal = form.tanggal.data
                t.kategori = form.kategori.data
                t.nama_produk = form.nama_produk.data if form.nama_produk.data else None
                t.kuantitas = form.kuantitas.data or 0
                t.harga_modal = float(form.harga_modal.data) if form.harga_modal.data is not None and str(form.harga_modal.data).strip() != "" else None
                t.jenis_pengeluaran = form.jenis_pengeluaran.data
                t.pemasukan = form.pemasukan.data or 0.0
                t.pengeluaran = form.pengeluaran.data or 0.0
                t.jumlah_pelanggan = form.jumlah_pelanggan.data or 0
                t.catatan = form.catatan.data if form.catatan.data else None
                
                if not t_id:
                    db.session.add(t)
                
                db.session.commit()
                nom = t.pemasukan if t.pemasukan > 0 else t.pengeluaran
                
                if not t_id:
                    log_activity(session['user_id'], buku_kas_id, f"Mencatat transaksi manual {t.kategori} sebesar Rp {nom:,.0f}.", "Transaksi", "tambah")
                    flash("Sip, Transaksi berhasil dicatat!", "success")
                else:
                    log_activity(session['user_id'], buku_kas_id, f"Mengubah transaksi {t.kategori} sebesar Rp {nom:,.0f}.", "Transaksi", "ubah")
                    flash("Transaksi berhasil diperbarui!", "success")
                    
                cache.clear()
                
                if t_id: # jika edit, kembalikan ke riwayat
                    return redirect(url_for('riwayat'))
                return redirect(url_for('input_transaksi'))
            elif request.method == 'POST':
                # tangkap error the form
                for field, errs in form.errors.items():
                    for err in errs:
                        flash(f"Mohon lengkapi {getattr(form, field).label.text}: {err}", "error")
            
            # GET mode
            if request.method == 'GET' and t_id:
                form.tanggal.data = t.tanggal
                form.kategori.data = t.kategori
                form.nama_produk.data = t.nama_produk
                form.kuantitas.data = t.kuantitas
                form.harga_modal.data = t.harga_modal
                form.jenis_pengeluaran.data = t.jenis_pengeluaran
                form.pemasukan.data = t.pemasukan
                form.pengeluaran.data = t.pengeluaran
                form.jumlah_pelanggan.data = t.jumlah_pelanggan
                form.catatan.data = t.catatan
            
            # Ambil seluruh transaksi untuk kalkulasi saldo berjalan
            semua_trx = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc(), Transaksi.id.asc()).all()
            
            saldo = 0
            hari_ini_in = 0
            hari_ini_out = 0
            sekarang = date.today()
            
            for tx in semua_trx:
                saldo += tx.pemasukan
                saldo -= tx.pengeluaran
                tx.saldo_berjalan = saldo  # type: ignore
                
                if tx.tanggal == sekarang:
                    hari_ini_in += tx.pemasukan
                    hari_ini_out += tx.pengeluaran
                
            # Ambil Riwayat 15 Transaksi Terakhir untuk Tabel Transparansi (urutan descending)
            riwayat_trx = list(reversed(semua_trx))[:15]
            
            delta_wib = timedelta(hours=7) # +7 utc ke wib manual
            
            return render_template('input.html', form=form, riwayat=riwayat_trx, edit_mode=bool(t_id), t_id=t_id, hari_ini_in=hari_ini_in, hari_ini_out=hari_ini_out, delta_wib=delta_wib)
        except Exception as e:
            db.session.rollback()
            print(f"Error input: {e}")
            return render_template('error.html', pesan="Gagal menyimpan/memuat transaksi manual."), 500

    @app.route('/api-fill-dummy', methods=['GET'])
    @login_required
    def api_generate_dummy_trx():
        buku_kas_id = session.get('buku_kas_id')
        if not buku_kas_id: return jsonify({'error': 'no_book'}), 400
        
        # Ambil variasi produk terbaru untuk insight SI AI
        riwayat_qs = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).filter(Transaksi.nama_produk != None).order_by(Transaksi.id.desc()).limit(30).all()
        
        riwayat_unik = {}
        for t in riwayat_qs:
            name = str(t.nama_produk).strip()
            if t.harga_modal and name and name not in riwayat_unik:
                riwayat_unik[name] = t.harga_modal
                if len(riwayat_unik) >= 5:
                    break
        
        riwayat_list = [(k, v) for k, v in riwayat_unik.items()]
        
        from gemini_helper import generate_dummy_transaction_ai
        hasil = generate_dummy_transaction_ai(riwayat_list)
        
        if hasil:
            return jsonify(hasil)
        return jsonify({'error': 'AI gagal membuat dummy'}), 500

    @app.route('/transaksi/delete/<int:t_id>', methods=['POST'])
    @login_required
    def hapus_transaksi(t_id):
        buku_kas_id = session.get('buku_kas_id')
        if not buku_kas_id: return jsonify({"error": "Pilih buku kas"}), 400
        
        t = Transaksi.query.filter_by(id=t_id, buku_kas_id=buku_kas_id).first_or_404()
        try:
            nom = t.pemasukan if t.pemasukan > 0 else t.pengeluaran
            kat = t.kategori
            db.session.delete(t)
            db.session.commit()
            log_activity(session['user_id'], buku_kas_id, f"Menghapus transaksi {kat} sebesar Rp {nom:,.0f}.", "Transaksi", "hapus")
            cache.clear()
            flash("Transaksi berhasil dihapus.", "success")
            return redirect(url_for('riwayat'))
        except Exception as e:
            db.session.rollback()
            flash("Gagal menghapus transaksi.", "error")
            return redirect(url_for('riwayat'))

    @app.route('/transaksi/delete_bulk', methods=['POST'])
    @login_required
    def transaksi_delete_bulk():
        buku_kas_id = session.get('buku_kas_id')
        if not buku_kas_id: return jsonify({"error": "Pilih buku kas"}), 400
        
        data = request.get_json()
        if not data or 'ids' not in data:
            return jsonify({"error": "Permintaan tidak valid"}), 400
            
        ids = data.get('ids', [])
        if not ids:
            return jsonify({"error": "Tidak ada ID yang dipilih"}), 400
            
        try:
            valid_ids = [int(i) for i in ids if str(i).isdigit()]
            if not valid_ids:
                return jsonify({"error": "Format ID tidak valid"}), 400
                
            trx_to_delete = Transaksi.query.filter(Transaksi.id.in_(valid_ids), Transaksi.buku_kas_id == buku_kas_id).all()
            deleted_count = len(trx_to_delete)
            
            if deleted_count == 0:
                return jsonify({"error": "Data tidak valid atau sudah dihapus"}), 404
                
            for t in trx_to_delete:
                db.session.delete(t)
                
            db.session.commit()
            
            log_activity(session['user_id'], buku_kas_id, f"Menghapus {deleted_count} transaksi secara bersamaan.", "Transaksi", "hapus")
            cache.clear()
            
            flash(f"{deleted_count} transaksi berhasil dihapus secara massal.", "success")
            return jsonify({"success": True})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/scan-struk', methods=['POST'])
    @login_required
    @limiter.limit("10 per minute")
    def api_scan_struk():
        # terima dari web lalu scan pakai ai flash vision
        try:
            if 'struk_img' not in request.files:
                return jsonify({"error": "tidak ada gambar struk yang dikirim"}), 400
                
            file = request.files['struk_img']
            if file.filename == '':
                return jsonify({"error": "gambar kosong"}), 400
                
            img_bytes = file.read()
            hasil = gemini_helper.ekstrak_struk_vision(img_bytes)
            
            if hasil:
                return jsonify(hasil)
            else:
                return jsonify({"error": "ai gagal mengekstrak teks dari gambar ini"}), 500
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route('/riwayat', methods=['GET'])
    @login_required
    def riwayat():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            q = request.args.get('q', '').strip()
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')
            jenis = request.args.get('jenis', '')
            
            query = Transaksi.query.filter_by(buku_kas_id=buku_kas_id)
            
            if start_date:
                query = query.filter(Transaksi.tanggal >= start_date)
            if end_date:
                query = query.filter(Transaksi.tanggal <= end_date)
            if jenis == 'masuk':
                query = query.filter(Transaksi.pemasukan > 0)
            elif jenis == 'keluar':
                query = query.filter(Transaksi.pengeluaran > 0)
                
            if q:
                query = query.filter(db.or_(
                    Transaksi.catatan.ilike(f"%{q}%"),
                    Transaksi.kategori.ilike(f"%{q}%"),
                    Transaksi.nama_produk.ilike(f"%{q}%")
                ))
            
            # For running balance, order ASC first
            trxs = query.order_by(Transaksi.tanggal.asc(), Transaksi.id.asc()).all()
            
            saldo = 0
            for t in trxs:
                saldo += t.pemasukan
                saldo -= t.pengeluaran
                t.saldo_berjalan = saldo
                
            # Reverse for display (Newest first)
            transaksi_list_tampil_all = list(reversed(trxs))

            # --- PAGINATION LOGIC ---
            per_page = request.args.get('per_page', 50, type=int)
            page = request.args.get('page', 1, type=int)
            
            total_items = len(transaksi_list_tampil_all)
            from math import ceil
            total_pages = ceil(total_items / per_page) if total_items > 0 else 1
            
            if page < 1: page = 1
            if page > total_pages: page = total_pages
            
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            transaksi_list_tampil = list(transaksi_list_tampil_all)[start_idx:end_idx]  # type: ignore
            
            page_range = range(max(1, page - 2), min(total_pages + 1, page + 3))

            cache_key = f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3"
            data = cache.get(cache_key)
            if data is None:
                transaksi_list_all = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                data = hitung_health_score(transaksi_list_all, periode_grafik=30)
                cache.set(cache_key, data)
            
            delta_wib = timedelta(hours=7)
            
            return render_template('riwayat.html', transaksi_list=transaksi_list_tampil, data=data,
                                   start_date=start_date, end_date=end_date, jenis=jenis, q=q,
                                   page=page, per_page=per_page, total_pages=total_pages, total_items=total_items, page_range=page_range, delta_wib=delta_wib)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template('error.html', pesan=f"Gagal memuat halaman master data. Detail: {str(e)}"), 500

    @app.route('/log-aktivitas', methods=['GET'])
    @login_required
    def log_aktivitas():
        try:
            buku_kas_id = session.get('buku_kas_id')
            query = AktivitasLog.query.filter_by(user_id=session['user_id'])
            if buku_kas_id:
                query = query.filter(db.or_(AktivitasLog.buku_kas_id == buku_kas_id, AktivitasLog.buku_kas_id == None))
            logs = query.order_by(AktivitasLog.waktu.desc()).limit(100).all()
            return render_template('log_aktivitas.html', logs=logs)
        except Exception as e:
            return render_template('error.html', pesan=f"Gagal memuat log aktivitas. {str(e)}"), 500

    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload_csv():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            form = UploadCSVForm()
            if form.validate_on_submit():
                # Dapatkan array multi-files dari input OS
                files = request.files.getlist(form.file_csv.name)
                sukses = 0
                
                for file in files:
                    if not file.filename.endswith('.csv'): continue
                    stream = io.StringIO(file.stream.read().decode('utf-8'))
                    reader = csv.DictReader(stream)
                    
                    # Validasi Kolom
                    k_wajib = {'tanggal', 'kategori', 'pemasukan', 'pengeluaran', 'jumlah_pelanggan'}
                    if not k_wajib.issubset(set(reader.fieldnames or [])):
                        flash(f"Kolom CSV '{file.filename}' tidak lengkap. Diabaikan.", "error")
                        continue

                    # Penggabungan Multiple CSV: Tidak Menghapus Transaksi Lama
                    gagal = []
                    baris_ke = 1
                    for row in reader:
                        baris_ke += 1
                        # Lewati baris kosong
                        if not row['tanggal']: continue
                        try:
                            raw_hpp = row.get('hpp', '').strip() if 'hpp' in row else row.get('harga_modal', '').strip()
                            parsed_hpp = float(raw_hpp) if raw_hpp != "" else None

                            t = Transaksi(
                                user_id=session['user_id'],
                                buku_kas_id=buku_kas_id,
                                tanggal=datetime.strptime(row['tanggal'], '%Y-%m-%d').date(),
                                kategori=row.get('kategori', 'Lainnya'),
                                nama_produk=row.get('nama_produk') or None,
                                kuantitas=int(row.get('kuantitas') or 0),
                                harga_modal=parsed_hpp,
                                jenis_pengeluaran=row.get('jenis_pengeluaran', 'operasional').lower() if row.get('jenis_pengeluaran') else 'operasional',
                                pemasukan=float(row.get('pemasukan') or 0),
                                pengeluaran=float(row.get('pengeluaran') or 0),
                                jumlah_pelanggan=int(row.get('jumlah_pelanggan') or 0),
                                catatan=row.get('catatan') or None
                            )
                            if t.jenis_pengeluaran not in ['operasional', 'modal']:
                                t.jenis_pengeluaran = 'operasional'
                            db.session.add(t)
                            sukses = int(sukses) + 1
                        except (ValueError, KeyError, TypeError):
                            # tampung baris yang datanya gak valid
                            gagal.append(str(baris_ke))
                        
                db.session.commit()
                cache.delete(f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"dashboard_bk_{buku_kas_id}_60_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"dashboard_bk_{buku_kas_id}_90_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"saran_bk_{buku_kas_id}")
                
                if gagal:
                    flash(f"Berhasil memuat {sukses} baris. Gagal pada baris: {', '.join(gagal)}", "warning")
                    log_activity(session['user_id'], buku_kas_id, f"Mengimpor CSV ({sukses} sukses, {len(gagal)} gagal).", "Transaksi", "tambah")
                else:
                    flash(f"Berhasil menggabungkan {sukses} baris transaksi ke Buku Kas ini.", "success")
                    log_activity(session['user_id'], buku_kas_id, f"Mengimpor CSV secara penuh ({sukses} baris).", "Transaksi", "tambah")
                return redirect(url_for('dashboard'))

            return render_template('upload.html', form=form)
        except Exception:
            db.session.rollback()
            return render_template('error.html', pesan="File CSV rusak atau berekstensi asing."), 500

    @app.route('/download-template', methods=['GET'])
    @login_required
    def download_template():
        content = "tanggal,kategori,nama_produk,kuantitas,hpp,pemasukan,pengeluaran,jenis_pengeluaran,jumlah_pelanggan,catatan\n" \
                  "2026-03-01,Makanan & Minuman,Nasi Goreng Spesial,20,15000,500000,0,operasional,15,Hari hujan rintik\n" \
                  "2026-03-02,Retail,Kaus Sablon,50,40000,1500000,0,operasional,5,Beli stok grosir\n" \
                  "2026-03-03,Jasa,Reparasi AC,2,0,1000000,0,operasional,4,Pelanggan baru membludak\n" \
                  "2026-03-04,Lainnya,,,0,0,50000,operasional,0,Bayar Listrik\n"
        return send_file(io.BytesIO(content.encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Template_PANTAUIN.csv')

    @app.route('/simulator', methods=['GET'])
    @login_required
    def simulator():
        buku_kas_id = session.get('buku_kas_id')
        if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
        
        cache_key = f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3"
        baseline = cache.get(cache_key)
        top_produk = []
        if baseline and baseline.get('data_produk') and baseline['data_produk'].get('top_3_terlaris'):
            top_produk = baseline['data_produk']['top_3_terlaris']
        
        # Cari tanggal transaksi pertama
        first_trx = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).first()
        tanggal_pertama = first_trx.tanggal.strftime('%Y-%m-%d') if first_trx else None
        
        # Hitung jumlah transaksi total
        jumlah_transaksi = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).count()
        
        # Semua nama produk unik untuk autosuggest
        all_produk_rows = db.session.query(Transaksi.nama_produk).filter(
            Transaksi.buku_kas_id == buku_kas_id,
            Transaksi.nama_produk.isnot(None),
            Transaksi.nama_produk != ''
        ).distinct().all()
        all_produk = sorted(set(r[0].strip() for r in all_produk_rows if r[0] and r[0].strip()))
        
        # Baseline data untuk tampilan perbandingan
        baseline_display = {}
        if baseline:
            baseline_display = {
                'pemasukan': baseline.get('total_pemasukan_minggu_ini', 0),
                'pengeluaran': baseline.get('total_pengeluaran_minggu_ini', 0),
                'saldo': baseline.get('saldo_minggu_ini', 0),
            }
            
        return render_template('simulator.html', 
            top_produk=top_produk, 
            tanggal_pertama=tanggal_pertama,
            jumlah_transaksi=jumlah_transaksi,
            baseline_display=baseline_display,
            all_produk=all_produk
        )

    # --- API ENDPOINTS (RATE LIMITED & CSRF PROTECTED) ---
    def _safe_float(val, default=0.0):
        # amankan float parsing dari error kalau inputnya aneh
        if val is None or val == '':
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @app.route('/api/simulator', methods=['POST'])
    @login_required
    @limiter.limit("30 per minute")
    def api_simulator():
        """Menghitung proyeksi berdasarkan periode & persen stress."""
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return jsonify({"error": "Pilih buku kas terlebih dahulu."}), 400
            
            req = request.get_json()
            persen_umum = min(max(_safe_float(req.get('perubahan_penjualan', 0)), -500), 500) / 100
            persen_hpp = min(max(_safe_float(req.get('perubahan_hpp', 0)), -100), 500) / 100
            persen_opex = min(max(_safe_float(req.get('perubahan_opex', 0)), -100), 500) / 100
            
            nominal_penjualan = _safe_float(req.get('nominal_penjualan', 0))
            nominal_hpp = _safe_float(req.get('nominal_hpp', 0))
            nominal_opex = _safe_float(req.get('nominal_opex', 0))
            
            periode_str = req.get('periode', '30')
            start_date_str = req.get('start_date', '')
            end_date_str = req.get('end_date', '')
            
            # --- Query transaksi sesuai periode ---
            sekarang = date.today()
            if str(periode_str).lower() == 'custom' and start_date_str and end_date_str:
                dt_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                dt_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                t_periode = Transaksi.query.filter(
                    Transaksi.buku_kas_id == buku_kas_id,
                    Transaksi.tanggal >= dt_start,
                    Transaksi.tanggal <= dt_end
                ).all()
                actual_days = (dt_end - dt_start).days + 1
                if actual_days <= 0: actual_days = 1
            else:
                periode = int(_safe_float(periode_str))
                if periode <= 0:
                    # Semua transaksi
                    t_periode = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).all()
                    first_trx = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).first()
                    actual_days = (sekarang - first_trx.tanggal).days + 1 if first_trx else 1
                else:
                    start_date = sekarang - timedelta(days=periode)
                    t_periode = Transaksi.query.filter(
                        Transaksi.buku_kas_id == buku_kas_id,
                        Transaksi.tanggal >= start_date
                    ).all()
                    actual_days = periode
            
            hari_aktif = len({t.tanggal for t in t_periode}) or 1
            jumlah_trx = len(t_periode)
            
            # --- Warning data terlalu sedikit ---
            warning = None
            if jumlah_trx == 0:
                return jsonify({
                    "pemasukan_baru": 0, "pengeluaran_baru": 0, "saldo_baru": 0,
                    "pemasukan_asli": 0, "pengeluaran_asli": 0, "saldo_asli": 0,
                    "gross_margin": 0, "rasio_opex": 0, "status_bisnis": "Tidak Ada Data",
                    "bep_persen": 0, "hari_bertahan": 0, "selisih_saldo": 0,
                    "hari_aktif": 0, "jumlah_trx": 0, "periode_hari": actual_days,
                    "saran": "Belum ada transaksi pada periode ini. Coba pilih periode yang lebih panjang.",
                    "warning": "Tidak ada data transaksi dalam periode yang dipilih."
                })
            if hari_aktif < 3:
                warning = f"Hanya {hari_aktif} hari data aktif. Hasil simulasi kurang akurat."
            
            # --- Hitung baseline asli ---
            total_pemasukan = sum(t.pemasukan for t in t_periode)
            total_operasional = sum(t.pengeluaran for t in t_periode if getattr(t, 'jenis_pengeluaran', 'operasional') == 'operasional')
            total_modal_hpp = sum((getattr(t, 'harga_modal', 0) or 0) * (t.kuantitas or 0) for t in t_periode)
            total_modal_pengeluaran = sum(t.pengeluaran for t in t_periode if getattr(t, 'jenis_pengeluaran', 'operasional') == 'modal')
            total_modal = total_modal_hpp if total_modal_hpp > 0 else total_modal_pengeluaran
            total_pengeluaran = total_operasional + total_modal
            saldo_asli = total_pemasukan - total_pengeluaran
            
            # Rata-rata per hari untuk kalkulasi bertahan
            avg_pengeluaran_harian = total_pengeluaran / hari_aktif if hari_aktif > 0 else 0

            # --- Kalkulasi Forecasting ---
            in_baru = total_pemasukan * (1 + persen_umum) + nominal_penjualan
            
            # Forecasting per produk
            for k, v in req.items():
                if k.startswith('persen_produk_'):
                    nama_produk = k.replace('persen_produk_', '').lower()
                    perubahan_persen = float(v) / 100.0
                    pemasukan_produk = sum(t.pemasukan for t in t_periode if t.nama_produk and t.nama_produk.lower() == nama_produk)
                    in_baru = float(in_baru) + float(pemasukan_produk * perubahan_persen)  # type: ignore
            
            in_baru = max(0.0, float(in_baru))
            
            modal_baru = max(0.0, float(total_modal * (1 + persen_hpp) + nominal_hpp))  # type: ignore
            opex_baru = max(0.0, float(total_operasional * (1 + persen_opex) + nominal_opex))  # type: ignore
            
            if total_pengeluaran == 0 and modal_baru == 0 and opex_baru == 0:
                out_baru = 0
            else:
                out_baru = modal_baru + opex_baru
            
            saldo_baru = in_baru - out_baru
            
            # --- Indikator Kelayakan ---
            gross_margin_baru = ((in_baru - modal_baru) / in_baru * 100) if in_baru > 0 else 0
            rasio_opex_baru = (opex_baru / in_baru * 100) if in_baru > 0 else (100 if opex_baru > 0 else 0)
            
            # hitung titik impas dari proyeksi pendapatan baru
            bep_persen = (out_baru / in_baru * 100) if in_baru > 0 else (100 if out_baru > 0 else 0)
            
            # Hari bertahan: jika pemasukan = 0
            avg_out_harian_baru = out_baru / hari_aktif if hari_aktif > 0 else 0
            hari_bertahan = int(max(0, saldo_asli) / avg_out_harian_baru) if avg_out_harian_baru > 0 else 999
            
            # Selisih vs normal
            selisih_saldo = saldo_baru - saldo_asli
            
            # --- Status ---
            status_bisnis = "Aman"
            if saldo_baru < 0:
                status_bisnis = "Kritis"
            elif gross_margin_baru < 20 or rasio_opex_baru > 70:
                status_bisnis = "Waspada"
            
            # --- Saran Kontekstual ---
            is_default = (persen_umum == 0 and persen_hpp == 0 and persen_opex == 0 and 
                          nominal_penjualan == 0 and nominal_hpp == 0 and nominal_opex == 0 and 
                          all(float(v) == 0 for k, v in req.items() if 'produk' in k))

            if is_default and saldo_asli >= 0:
                saran = f"Kondisi stabil berdasarkan {jumlah_trx} transaksi ({hari_aktif} hari aktif)."
            elif saldo_baru < 0:
                saran = f"Status {status_bisnis}. RUGI Rp {int(abs(saldo_baru)):,}! Dana cadangan riil bertahan ±{hari_bertahan} hari.".replace(',', '.')
            elif persen_umum <= -1.0 and nominal_penjualan <= 0:
                saran = "Anda mensimulasikan penutupan total penjualan (omzet 0)."
            elif persen_umum > 0.5 or (saldo_baru > saldo_asli * 1.5):
                saran = "Proyeksi Pertumbuhan! Pastikan kapasitas produksi dan bahan baku siap untuk lonjakan pesanan."
            else:
                saran = f"Status {status_bisnis}. Laba bersih Rp {int(saldo_baru):,}. BEP di {bep_persen:.0f}% kapasitas.".replace(',', '.')
            
            result = {
                "pemasukan_baru": round(in_baru),
                "pengeluaran_baru": round(out_baru),
                "saldo_baru": round(saldo_baru),
                "pemasukan_asli": round(total_pemasukan),
                "pengeluaran_asli": round(total_pengeluaran),
                "saldo_asli": round(saldo_asli),
                "gross_margin": round(gross_margin_baru, 1),
                "rasio_opex": round(rasio_opex_baru, 1),
                "status_bisnis": status_bisnis,
                "bep_persen": round(min(bep_persen, 999), 1),
                "hari_bertahan": min(hari_bertahan, 999),
                "selisih_saldo": round(selisih_saldo),
                "hari_aktif": hari_aktif,
                "jumlah_trx": jumlah_trx,
                "periode_hari": actual_days,
                "saran": saran
            }
            if warning:
                result["warning"] = warning
            return jsonify(result)
        except Exception:
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Gagal simulasi"}), 500

    @app.route('/api/simulator-ai', methods=['POST'])
    @login_required
    @limiter.limit("5 per minute")
    def api_simulator_ai():
        """Generate AI analysis for current stress test scenario."""
        try:
            req = request.get_json()
            data = req.get('data', {})
            penjualan_val = float(req.get('penurunan', 0))
            hpp_val = float(req.get('hpp_naik', 0))
            opex_val = float(req.get('opex_naik', 0))
            
            str_penj = f"Naik {penjualan_val}%" if penjualan_val > 0 else (f"Turun {abs(penjualan_val)}%" if penjualan_val < 0 else "Tetap")
            str_hpp = f"Naik {hpp_val}%" if hpp_val > 0 else (f"Turun {abs(hpp_val)}%" if hpp_val < 0 else "Tetap")
            str_opex = f"Naik {opex_val}%" if opex_val > 0 else (f"Turun {abs(opex_val)}%" if opex_val < 0 else "Tetap")
            
            jenis_skenario = "Kritis/Resesi" if penjualan_val < 0 or hpp_val > 0 or opex_val > 0 else "Pertumbuhan/Ekspansi"

            prompt = f"""Analisis singkat skenario proyeksi What-If bisnis UMKM ini dalam 3-4 kalimat:
- Skenario Utama: {jenis_skenario}
- Konfigurasi Simulasi: Penjualan {str_penj}, HPP {str_hpp}, Opex {str_opex}
- Laba Bersih Setelah Proyeksi: Rp {int(data.get('saldo_baru', 0)):,}
- Pemasukan Setelah Proyeksi: Rp {int(data.get('pemasukan_baru', 0)):,}
- Gross Margin Proyeksi: {data.get('gross_margin', 0)}%
- BEP Target: {data.get('bep_persen', 0)}%
- Hari bertahan kas riil: {data.get('hari_bertahan', 0)} hari
- Status Akhir: {data.get('status_bisnis', '-')}

Berikan analisis performa singkat dan sarankan strategi taktis pengembangan (jika skenario positif/untung besar beri solusi manajemen kapasitas & ekspansi, jika skenario negatif/rugi beri solusi ketahanan/survival).
PENTING: Buatlah khusus dalam bentuk tabel evaluasi taktis (Kolom 1: Area Fokus, Kolom 2: Analisis Saat Ini, Kolom 3: Tindakan/Solusi). Format harus pakai syntax Tabel Markdown yang rapi.
""".replace(',', '.')
            
            from gemini_helper import _chat, groq_client
            if not groq_client:
                return jsonify({"analisis": "AI tidak tersedia. Pastikan API key Groq telah dikonfigurasi."})
            
            analisis = _chat(prompt, max_tokens=300)
            return jsonify({"analisis": analisis})
        except Exception as e:
            return jsonify({"analisis": f"Gagal menganalisis: {str(e)}"}), 500

    @app.route('/api/simulator-chat', methods=['POST'])
    @login_required
    @limiter.limit("15 per minute")
    def api_simulator_chat():
        # rute khusus follow up dari tampilan simulator
        try:
            req = request.get_json()
            pesan_user = req.get('pesan_user', '')
            konteks = req.get('konteks_simulasi', {})
            
            from gemini_helper import get_simulator_chat_response
            reply = get_simulator_chat_response(pesan_user, konteks)
            return jsonify({"reply": reply})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"reply": f"wah error pas ngambil obrolan, ditunggu ya: {str(e)}"}), 500

    @app.route('/api/chatbot', methods=['POST'])
    @login_required
    @limiter.limit("15 per minute") 
    def api_chatbot():
        try:
            pesan_user = request.get_json().get('message', '')
            
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return jsonify({"reply": "Anda belum memilih Proyek/Buku Kas."})
            
            cache_key = f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3"
            konteks = cache.get(cache_key)
            if not konteks:
                t_list = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                konteks = hitung_health_score(t_list, periode_grafik=30)
                cache.set(cache_key, konteks)
            
            reply = gemini_helper.get_chatbot_response(pesan_user, konteks)
            return jsonify({"reply": reply})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"reply": f"AI Kelebihan beban detail: {str(e)}"}), 500

    @app.route('/unduh-laporan', methods=['GET', 'POST'])
    @login_required
    def download_report():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            # Wajib isi profil perusahaan jika belum (untuk dicetak)
            profil = ProfilPerusahaan.query.filter_by(buku_kas_id=buku_kas_id).first()
            if not profil:
                flash("Isi profil perusahaan usahamu terlebih dahulu sebelum mencetak Laporan Utama.", "warning")
                return redirect(url_for('edit_profil_perusahaan'))
                
            cache_key = f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3"
            data = cache.get(cache_key)
            if not data:
                t_list = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                data = hitung_health_score(t_list, periode_grafik=30)
                cache.set(cache_key, data)

            if not data.get('is_cukup'):
                flash("Anda belum memiliki cukup data transaksi untuk dicetak pada Buku Kas ini (minimal 14 hari).", "warning")
                return redirect(url_for('dashboard'))
                
            buku_aktif = BukuKas.query.get(buku_kas_id)
            nama_proyek = profil.nama_perusahaan if profil and profil.nama_perusahaan else (buku_aktif.nama_buku if buku_aktif else session['username'])
            
            # Ambil narasi AI dari cache yang pernah dirender dashboard
            saran_gemini = cache.get(f"saran_bk_{buku_kas_id}") or "Hasil analitik AI belum tesedia, silakan generate ulang dashboard."
            
            if request.method == 'POST':
                # Tangkap Opsi Kustomisasi
                teks_ai_diedit = request.form.get('narasi_ai', saran_gemini)
                lampir_profil = request.form.get('lampir_profil', 'off') == 'on'
                lampir_proyeksi = request.form.get('lampir_proyeksi', 'off') == 'on'
                
                base_dir = os.path.abspath(os.path.dirname(__file__))
                output_file = os.path.join(base_dir, f'Laporan_PANTAUIN_{int(datetime.now().timestamp())}.pdf')
                
                # Fetch Profil Detil untuk dilempar ke Generator bila lampir disetujui
                profil_dict = None
                if lampir_profil and profil:
                    try:
                        dt_ekstra = json.loads(profil.detil_industri) if profil.detil_industri else {}
                    except: dt_ekstra = {}
                    profil_dict = {
                        'entitas': profil.nama_perusahaan,
                        'contact_person': profil.contact_person,
                        'jabatan': profil.jabatan,
                        'bentuk_usaha': profil.bentuk_usaha,
                        'tahun_berdiri': profil.tahun_berdiri,
                        'alamat': f"{profil.alamat_jalan}, {profil.alamat_rtrw}, {profil.alamat_desa}, {profil.alamat_kecamatan}, {profil.alamat_kabkota}, {profil.alamat_provinsi} {profil.kode_pos}",
                        'kontak': f"{profil.no_telp} / {profil.email_web}",
                        'legalitas': f"Ijin: {profil.ijin_usaha} | HAKI: {profil.haki}",
                        'tk': f"Tetap: {profil.tk_tetap}, Tidak Tetap: {profil.tk_tidak_tetap}",
                        'kapasitas': dt_ekstra.get('kapasitas_produksi', '-'),
                        'omzet': dt_ekstra.get('omzet_usaha', '-'),
                        'bahan_baku': f"Asal: {dt_ekstra.get('bahan_baku_asal', '-')} ({dt_ekstra.get('bahan_baku_ketersediaan', '')})",
                        'pasar': dt_ekstra.get('segmen_pasar', '-'),
                        'wilayah': dt_ekstra.get('wilayah_pemasaran', '-')
                    }
                
                # Panggil fungsi report lab
                generate_pdf_report(
                    user_name=nama_proyek, 
                    score=data['skor'], 
                    avg_in=data['rata_pemasukan'], 
                    avg_out=data['rata_pengeluaran'], 
                    warnings=data['peringatan'], 
                    catatan_mingguan=data.get('catatan_mingguan', []), 
                    output_path=output_file,
                    breakdown=data.get('rincian_skor', {}),
                    stat_4_minggu=data.get('statistik_4_minggu', []),
                    proyeksi=data.get('grafik_proyeksi', []),
                    proyeksi_pengeluaran=data.get('proyeksi_pengeluaran', []),
                    tgl_cetak_dt=datetime.now(),
                    tgl_mulai_dt=date.today() - timedelta(days=30),
                    tgl_akhir_dt=date.today(),
                    # Parameter Argumen Kustom
                    kustom_teks_ai=teks_ai_diedit,
                    lampir_proyeksi=lampir_proyeksi,
                    profil_dict=profil_dict, # Jika None, generator akan skip bab Profil Perusahaan
                    data_produk=data.get('data_produk'),
                    risiko_dict=data.get('risiko'),
                    rekomendasi_list=data.get('rekomendasi'),
                    advanced_analytics=data.get('advanced_analytics')
                )
                action_type = request.form.get('action', 'download')
                
                if action_type == 'preview':
                    return send_file(output_file, as_attachment=False, mimetype='application/pdf')
                else:
                    return send_file(output_file, as_attachment=True, download_name=f"PANTAUIN_Kustom_{date.today()}_{nama_proyek.replace(' ', '_')}.pdf")
            
            # Jika GET -> Render Preview Halaman Customize
            return render_template('laporan_kustom.html', nama_buku=nama_proyek, teks_ai=saran_gemini)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template('error.html', pesan=f"Gagal memproses File Laporan: {str(e)}"), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5050)
