import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from gemini_helper import get_pdf_narration

def format_tanggal_indonesia(dt):
    hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
             "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    return f"{hari[dt.weekday()]}, {dt.day} {bulan[dt.month]} {dt.year}"

def _fmt_rp(nilai):
    return f"Rp {int(nilai):,}".replace(",", ".")

def generate_pdf_report(user_name, score, avg_in, avg_out, warnings, catatan_mingguan, output_path, breakdown, stat_4_minggu, proyeksi, proyeksi_pengeluaran, tgl_cetak_dt, tgl_mulai_dt, tgl_akhir_dt, kustom_teks_ai=None, lampir_proyeksi=True, profil_dict=None):
    """
    Membuat laporan cetak evaluasi kesehatan bisnis 4 Halaman (Platypus ReportLab).
    Hadir dengan 5 Solusi: Format Angka/Tanggal Indonesia, Status murni, Numpy Polyfit Expense, Recomendation Rules, & 4-Paragraf AI.
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Warna Tema
    COLOR_PRIMARY = colors.HexColor('#1B2A6B')
    COLOR_SUCCESS = colors.HexColor('#27AE60')
    COLOR_WARNING = colors.HexColor('#F39C12')
    COLOR_DANGER = colors.HexColor('#E74C3C')
    COLOR_LIGHT = colors.whitesmoke
    COLOR_TXT = colors.HexColor('#333333')

    # Custom Styles
    style_title = ParagraphStyle('Title', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=28, textColor=COLOR_PRIMARY, alignment=1, spaceAfter=5)
    style_subtitle = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=14, textColor=colors.grey, alignment=1, spaceAfter=20)
    style_h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=16, textColor=COLOR_PRIMARY, spaceAfter=15, spaceBefore=20)
    style_normal = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Helvetica', fontSize=11, textColor=COLOR_TXT, leading=16, spaceAfter=10)
    style_normal_center = ParagraphStyle('NormalCenter', parent=style_normal, alignment=1)
    
    # Box Score Styles
    style_score_number = ParagraphStyle('ScoreNum', fontName='Helvetica-Bold', fontSize=48, textColor=colors.white, alignment=1, spaceAfter=5)
    style_score_label = ParagraphStyle('ScoreLbl', fontName='Helvetica-Bold', fontSize=16, textColor=colors.white, alignment=1, spaceAfter=2)
    style_score_desc = ParagraphStyle('ScoreDesc', fontName='Helvetica', fontSize=10, textColor=colors.white, alignment=1)

    elements = []

    # ==============================
    # HALAMAN 1: COVER & RINGKASAN
    # ==============================
    elements.append(Paragraph("PANTAUIN", style_title))
    elements.append(Paragraph("Laporan Kesehatan Bisnis", style_subtitle))
    
    elements.append(Paragraph(f"<b>{user_name}</b>", ParagraphStyle('BizName', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, alignment=1, spaceAfter=5)))
    
    tgl_cetak = format_tanggal_indonesia(tgl_cetak_dt)
    elements.append(Paragraph(f"{tgl_cetak}", style_normal_center))
    
    tgl_mulai_str = f"{tgl_mulai_dt.day} {['','Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'][tgl_mulai_dt.month]} {tgl_mulai_dt.year}"
    tgl_akhir_str = f"{tgl_akhir_dt.day} {['','Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'][tgl_akhir_dt.month]} {tgl_akhir_dt.year}"
    
    elements.append(Paragraph(f"Periode: {tgl_mulai_str} – {tgl_akhir_str}", ParagraphStyle('Period', parent=style_normal_center, spaceAfter=20)))
    
    # Garis pemisah
    elements.append(Table([['']], colWidths=[17*cm], style=[('LINEBELOW', (0,0), (-1,-1), 2, COLOR_PRIMARY), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    elements.append(Spacer(1, 30))

    # Kotak Skor
    if score > 70:
        bg_score = COLOR_SUCCESS
        lbl_score = "BISNIS SEHAT"
    elif score >= 40:
        bg_score = COLOR_WARNING
        lbl_score = "PERLU PERHATIAN"
    else:
        bg_score = COLOR_DANGER
        lbl_score = "KONDISI KRITIS"

    score_card = Table([
        [Paragraph(f"{score}", style_score_number)],
        [Paragraph(lbl_score, style_score_label)],
        [Paragraph("dari skala 0-100", style_score_desc)]
    ], colWidths=[12*cm], style=[
        ('BACKGROUND', (0,0), (-1,-1), bg_score),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
        ('ROUNDEDCORNERS', [10, 10, 10, 10])
    ])
    
    t_score_container = Table([[score_card]], colWidths=[17*cm], style=[('ALIGN', (0,0), (-1,-1), 'CENTER')])
    elements.append(t_score_container)
    elements.append(Spacer(1, 40))

    # Tabel Ringkasan
    val_in_30 = sum([s['pemasukan'] for s in stat_4_minggu]) if stat_4_minggu else 0
    val_op_30 = sum([s['pengeluaran_op'] for s in stat_4_minggu]) if stat_4_minggu else 0
    val_md_30 = (breakdown.get('total_pengeluaran_md_minggu_ini', 0) * 4) # Placeholder
    val_saldo_30 = sum([s['saldo'] for s in stat_4_minggu]) if stat_4_minggu else 0
    
    color_saldo = COLOR_SUCCESS if val_saldo_30 >= 0 else COLOR_DANGER
    
    # Get actual gross margin percentage properly
    gross_margin_pct = breakdown.get('nilai_gross_margin_pct', 0) * 100
    
    data_ringkasan = [
        ['Total Pemasukan 30 Hari:', _fmt_rp(val_in_30)],
        ['Total Pengeluaran Operasional 30 Hari:', _fmt_rp(val_op_30)],
        ['Total Pengeluaran Modal 30 Hari:', _fmt_rp(val_md_30)],
        ['Saldo Bersih 30 Hari:', Paragraph(f"<b>{_fmt_rp(val_saldo_30)}</b>", ParagraphStyle('Sld', fontName='Helvetica-Bold', textColor=color_saldo, alignment=2))],
        ['Rata-rata Pemasukan Harian:', _fmt_rp(avg_in)],
        ['Rata-rata Pengeluaran Operasional Harian:', _fmt_rp(avg_out)],
        ['Gross Margin Rata-rata:', f"{gross_margin_pct:.1f}%"]
    ]
    
    t_ringkasan = Table(data_ringkasan, colWidths=[10*cm, 7*cm], style=[
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ])
    elements.append(t_ringkasan)
    
    elements.append(PageBreak())

    elements.append(PageBreak())

    # ==============================
    # HALAMAN EKSTRA: PROFIL PERUSAHAAN 
    # ==============================
    if profil_dict:
        elements.append(Paragraph("Profil Lengkap UMKM", style_h2))
        
        prof_data = [
            ['Kategori', 'Detail Informasi'],
            ['Nama Entitas', profil_dict.get('entitas', '')],
            ['Penanggung Jawab', f"{profil_dict.get('contact_person', '')} ({profil_dict.get('jabatan', '')})"],
            ['Bentuk Hukum', profil_dict.get('bentuk_usaha', '')],
            ['Tahun Berdiri', profil_dict.get('tahun_berdiri', '')],
            ['Alamat Lengkap', profil_dict.get('alamat', '')],
            ['Kontak', profil_dict.get('kontak', '')],
            ['Legalitas & NIB', profil_dict.get('legalitas', '')],
            ['Jumlah Pekerja', profil_dict.get('tk', '')],
            ['Kapasitas Produksi', profil_dict.get('kapasitas', '')],
            ['Omzet Rata-rata', profil_dict.get('omzet', '')],
            ['Asal Bahan Baku', profil_dict.get('bahan_baku', '')],
            ['Segmen Konsumen', profil_dict.get('pasar', '')],
            ['Jangkauan Pasar', profil_dict.get('wilayah', '')],
        ]
        
        t_prof = Table(prof_data, colWidths=[5*cm, 12*cm], style=[
            ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])
        elements.append(t_prof)
        elements.append(PageBreak())

    # ==============================
    # HALAMAN BREAKDOWN & PERINGATAN
    # ==============================
    elements.append(Paragraph("Rincian Skor & Statistik", style_h2))
    
    def _get_status_label(skor_dapat):
        if skor_dapat > 70:
            return Paragraph("✓ Baik", ParagraphStyle('B', textColor=COLOR_SUCCESS, fontName='Helvetica'))
        elif skor_dapat >= 40:
            return Paragraph("⚠ Perlu Perhatian", ParagraphStyle('P', textColor=COLOR_WARNING, fontName='Helvetica'))
        return Paragraph("✗ Kritis", ParagraphStyle('K', textColor=COLOR_DANGER, fontName='Helvetica'))

    data_b_down = [
        ['Indikator', 'Bobot', 'Nilai Kamu', 'Skor', 'Status'],
        ['Stabilitas Cashflow', '25%', f"{breakdown.get('stabilitas',0)}", f"{breakdown.get('stabilitas',0)*0.25:.1f}/25", _get_status_label(breakdown.get('stabilitas',0))],
        ['Tren Penjualan', '25%', f"{breakdown.get('tren',0)}", f"{breakdown.get('tren',0)*0.25:.1f}/25", _get_status_label(breakdown.get('tren',0))],
        ['Rasio Pengeluaran Ops.', '20%', f"{breakdown.get('pengeluaran',0)}", f"{breakdown.get('pengeluaran',0)*0.20:.1f}/20", _get_status_label(breakdown.get('pengeluaran',0))],
        ['Gross Margin', '20%', f"{breakdown.get('gross_margin',0)}", f"{breakdown.get('gross_margin',0)*0.20:.1f}/20", _get_status_label(breakdown.get('gross_margin',0))],
        ['Konsistensi Pemasukan', '10%', f"{breakdown.get('konsistensi',0)}", f"{breakdown.get('konsistensi',0)*0.10:.1f}/10", _get_status_label(breakdown.get('konsistensi',0))],
        ['TOTAL', '100%', '—', f"{score}/100", '']
    ]
    
    t_b_down = Table(data_b_down, colWidths=[5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 3.5*cm], style=[
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 8),
    ])
    elements.append(t_b_down)
    elements.append(Spacer(1, 25))

    # Peringatan Aktif
    if warnings:
        warn_elements = [Paragraph("<b>⚠ Peringatan Aktif:</b>", ParagraphStyle('W_T', textColor=COLOR_DANGER, fontSize=12, spaceAfter=8))]
        for w in warnings:
            warn_elements.append(Paragraph(f"• {w}", ParagraphStyle('W_I', textColor=COLOR_DANGER, fontSize=11)))
            
        t_warn = Table([[warn_elements]], colWidths=[17*cm], style=[
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#FDEDEC')), # Red very light
            ('BOX', (0,0), (0,0), 1, COLOR_DANGER),
            ('PADDING', (0,0), (0,0), 15)
        ])
    else:
        t_warn = Table([[Paragraph("Tidak ada peringatan aktif saat ini ✓", ParagraphStyle('W_OK', textColor=COLOR_SUCCESS, fontName='Helvetica-Bold', alignment=1))]], colWidths=[17*cm], style=[
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#EAFAF1')),
            ('BOX', (0,0), (0,0), 1, COLOR_SUCCESS),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('PADDING', (0,0), (0,0), 15)
        ])
    elements.append(t_warn)
    elements.append(Spacer(1, 25))

    # Statistik 4 Minggu
    elements.append(Paragraph("Statistik 4 Minggu Terakhir", style_h2))
    
    data_stat = [['Minggu', 'Pemasukan', 'Pengeluaran Op.', 'Saldo Bersih', 'Tren']]
    if stat_4_minggu:
        for st in reversed(stat_4_minggu):
            color_tren = COLOR_SUCCESS if 'Naik' in st['tren'] else (COLOR_DANGER if 'Turun' in st['tren'] else colors.grey)
            color_s = COLOR_SUCCESS if st['saldo'] >= 0 else COLOR_DANGER
            
            data_stat.append([
                st['minggu'],
                _fmt_rp(st['pemasukan']),
                _fmt_rp(st['pengeluaran_op']),
                Paragraph(f"<b>{_fmt_rp(st['saldo'])}</b>", ParagraphStyle('sd1', textColor=color_s, alignment=2)),
                Paragraph(st['tren'], ParagraphStyle('tr', textColor=color_tren, fontName='Helvetica-Bold', alignment=1))
            ])
            
    t_stat = Table(data_stat, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3*cm], style=[
        ('BACKGROUND', (0,0), (-1,0), COLOR_LIGHT),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (3,-1), 'RIGHT'),
        ('ALIGN', (4,0), (4,-1), 'CENTER'),
    ])
    elements.append(t_stat)
    
    elements.append(PageBreak())

    elements.append(PageBreak())

    # ==============================
    # HALAMAN PROYEKSI & SIMULASI
    # ==============================
    if lampir_proyeksi:
        elements.append(Paragraph("Proyeksi 4 Minggu Depan", style_h2))
        
        data_proyeksi = [['Minggu Ke-', 'Proyeksi Pemasukan', 'Proyeksi Pengeluaran Op.', 'Proyeksi Saldo']]
        
        proy_arr = []
        if proyeksi and len(proyeksi) >= 28 and proyeksi_pengeluaran and len(proyeksi_pengeluaran) >= 28:
            p_m1 = sum(proyeksi[0:7]); p_m2 = sum(proyeksi[7:14]); p_m3 = sum(proyeksi[14:21]); p_m4 = sum(proyeksi[21:28])
            o_m1 = sum(proyeksi_pengeluaran[0:7]); o_m2 = sum(proyeksi_pengeluaran[7:14]); o_m3 = sum(proyeksi_pengeluaran[14:21]); o_m4 = sum(proyeksi_pengeluaran[21:28])
            
            proy_arr = [
                ("Minggu +1", p_m1, o_m1, p_m1 - o_m1),
                ("Minggu +2", p_m2, o_m2, p_m2 - o_m2),
                ("Minggu +3", p_m3, o_m3, p_m3 - o_m3),
                ("Minggu +4", p_m4, o_m4, p_m4 - o_m4),
            ]
            
            for p_lbl, p_in, p_out, p_sal in proy_arr:
                c_sal = COLOR_SUCCESS if p_sal >= 0 else COLOR_DANGER
                txt_sal = _fmt_rp(p_sal)
                if p_sal < 0: txt_sal = f"⚠ {txt_sal}"
                
                data_proyeksi.append([
                    p_lbl, _fmt_rp(p_in), _fmt_rp(p_out),
                    Paragraph(txt_sal, ParagraphStyle('sd', textColor=c_sal, fontName='Helvetica-Bold', alignment=2))
                ])
                
        t_proyeksi = Table(data_proyeksi, colWidths=[3.5*cm, 4.5*cm, 4.5*cm, 4.5*cm], style=[
            ('BACKGROUND', (0,0), (-1,0), COLOR_LIGHT),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('PADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ])
        elements.append(t_proyeksi)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<i>Proyeksi dihitung berdasarkan tren historis 30 hari terakhir.</i>", ParagraphStyle('I', fontName='Helvetica-Oblique', fontSize=9, textColor=colors.grey)))
        elements.append(Spacer(1, 25))
    
    elements.append(Spacer(1, 25))

    # Box Rekomendasi 
    elements.append(Paragraph("Rekomendasi Tindakan Cepat", style_h2))
    rekomendasi = []
    
    tren_penjualan = breakdown.get('tren', 0)
    rasio_pengeluaran = (breakdown.get('nilai_rasio_out', 0)) * 100
    konsistensi = breakdown.get('konsistensi', 0)
    avg_weekly_expense = avg_out * 7

    rekomendasi.append(f"Pertahankan gross margin di atas {gross_margin_pct:.1f}% dengan menjaga harga jual dan menekan biaya produksi.")
    rekomendasi.append("Catat transaksi setiap hari tanpa bolong agar analisis semakin akurat.")
    
    if tren_penjualan < 50:
        rekomendasi.append(f"Tren penjualan kamu sedang menurun. Coba buat promo mingguan atau program loyalitas pelanggan untuk mendorong pemasukan kembali naik.")
    
    if rasio_pengeluaran > 60:
        rekomendasi.append(f"Pengeluaran operasional kamu mencapai {rasio_pengeluaran:.0f}% dari pemasukan. Audit pos pengeluaran terbesar dan cari yang bisa dikurangi 10-15%.")
    
    if gross_margin_pct < 30:
        rekomendasi.append(f"Gross margin {gross_margin_pct:.1f}% terbilang rendah. Pertimbangkan menaikkan harga jual 5-10% atau negosiasi harga bahan baku dengan supplier.")
    
    if val_saldo_30 < (avg_weekly_expense * 2):
        rekomendasi.append(f"Saldo bersih 30 hari ({_fmt_rp(val_saldo_30)}) belum cukup untuk dana darurat 2 minggu operasional. Sisihkan minimal {_fmt_rp(avg_weekly_expense * 2)} sebagai cadangan.")
    
    weeks_until_negative = None
    for i, (_, p_in, p_out, p_sal) in enumerate(proy_arr):
        if p_sal < 0:
            weeks_until_negative = i + 1
            break
            
    if weeks_until_negative and weeks_until_negative <= 4:
        rekomendasi.append(f"Proyeksi menunjukkan cashflow bisa negatif dalam {weeks_until_negative} minggu. Tunda pengeluaran modal yang tidak mendesak.")
        
    if konsistensi < 60:
        rekomendasi.append("Pemasukan harian kamu tidak konsisten. Coba identifikasi hari-hari sepi dan buat strategi khusus untuk hari tersebut.")
    
    rekomendasi = rekomendasi[:6] # Ambil 6 saja agar dengan 1 di bawah menjadi genap 7.
    rekomendasi.append("Gunakan fitur Business Stress Simulator di PANTAUIN untuk mensimulasikan skenario sebelum membuat keputusan bisnis besar.")

    for i, rec in enumerate(rekomendasi):
        elements.append(Paragraph(f"{i+1}. {rec}", style_normal))
        
    elements.append(PageBreak())

    if lampir_proyeksi:
        proy_arr_temp = [] # Dummy or retrieve from above if already defined (which it is)
        
    elements.append(PageBreak())

    # ==============================
    # HALAMAN ANALISIS AI & PENUTUP
    # ==============================
    elements.append(Paragraph("Analisis & Saran dari AI (Gemini)", style_h2))
    
    if kustom_teks_ai:
        ai_text = kustom_teks_ai
    else:
        # Fallback to pure gemini regeneration if no custom text provided
        proy_arr_safe = proy_arr if 'proy_arr' in locals() else []
        ai_text = get_pdf_narration(
            nama_bisnis=user_name,
            skor=score,
            label_skor=lbl_score,
            total_pemasukan=val_in_30,
            total_pengeluaran_ops=val_op_30,
            saldo_bersih=val_saldo_30,
            avg_harian_masuk=avg_in,
            gross_margin=gross_margin_pct,
            tren_penjualan=tren_penjualan,
            stabilitas=breakdown.get('stabilitas',0),
            rasio_pengeluaran=rasio_pengeluaran,
            konsistensi=konsistensi,
            peringatan_list=warnings,
            proyeksi_pemasukan=sum(proyeksi) if proyeksi else 0,
            proyeksi_saldo=sum([p[3] for p in proy_arr_safe]) if proy_arr_safe else 0
        )
    
    for par in ai_text.split('\n'):
        if par.strip():
            elements.append(Paragraph(par.strip(), style_normal))

    elements.append(Spacer(1, 150))
    
    # Metodologi
    elements.append(Paragraph("<b>Catatan Metodologi:</b>", ParagraphStyle('MB', fontName='Helvetica-Bold', fontSize=9, textColor=colors.grey)))
    elements.append(Paragraph("• Business Health Score dihitung menggunakan Weighted Scoring Model dengan 5 indikator komprehensif.", ParagraphStyle('MN', fontName='Helvetica', fontSize=9, textColor=colors.grey)))
    elements.append(Paragraph("• Proyeksi menggunakan metode regresi linear berdasarkan data historis.", ParagraphStyle('MN', fontName='Helvetica', fontSize=9, textColor=colors.grey)))
    elements.append(Paragraph("• Laporan ini bersifat indikatif dan tidak menggantikan konsultasi keuangan profesional.", ParagraphStyle('MN', fontName='Helvetica', fontSize=9, textColor=colors.grey)))


    def footer_canvas_maker(canvas, _):
        canvas.saveState()
        canvas.setStrokeColor(colors.lightgrey)
        canvas.setLineWidth(1)
        canvas.line(2*cm, 2.5*cm, 19*cm, 2.5*cm)
        
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2*cm, 1.8*cm, "PANTAUIN — Platform Analitik Bisnis UMKM")
        
        str_right = f"Halaman {canvas.getPageNumber()} | Dicetak: {tgl_cetak}"
        canvas.drawRightString(19*cm, 1.8*cm, str_right)
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer_canvas_maker, onLaterPages=footer_canvas_maker)
