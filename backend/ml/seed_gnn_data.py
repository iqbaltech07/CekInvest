"""
Seed module for GNN training data in CekInvest.
Populates UserReports with diverse, realistic Indonesian financial messages
including both scam reports (label=1) and legitimate financial communications (label=0).
Also establishes interconnected graph entities (shared banks, phones, domains)
and seeds community databases (PhoneReport, BankAccountReport).

Run with: python -m ml.seed_gnn_data
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma import Prisma
from prisma.enums import InputType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── 1. Interconnected Scam Entities ──────────────────────────────────────────
SCAM_SHARED_BANKS = [
    ("BCA", "8830192841", "PT Cuan Digital Makmur (Akun Penampung Robot Trading)"),
    ("Mandiri", "1370019284711", "Rekening Sindikat Titip Dana Crypto"),
    ("BRI", "020601002948501", "Penampung Fee Pencairan Pinjol Ilegal"),
    ("BNI", "0819283746", "Rekening Sindikat Task Scam Like Shopee"),
    ("BSI", "7192837465", "Penampung Arisan Online & Skema Ponzi"),
    ("Jago", "10928374619", "Akun Penampung Phishing APK Undangan"),
]

SCAM_SHARED_PHONES = [
    ("081298765432", "CS Robot Trading Palsu Bandung"),
    ("085712345678", "Admin Tugas Freelance Like Video Shopee"),
    ("087899887766", "Marketing Kripto Token Presale Surabaya"),
    ("081388776655", "Penipu Phishing Pembaharuan Tarif Bank"),
    ("089655443322", "Debt Collector & Agen Pinjol Ilegal Jakarta"),
]

SCAM_SHARED_DOMAINS = [
    "cuan-autopilot.pro",
    "profit-harian-vip.com",
    "ojk-verifikasi-dana.net",
    "token-presale-cuan.xyz",
    "undangan-pernikahan-digital.apk-download.biz",
    "bca-tarif-baru.info",
    "shopee-freelance-task.vip",
]

# ── 2. Scam Reports Data (label = True) ──────────────────────────────────────
SCAM_SAMPLES = [
    # ── Robot Trading & Titip Dana (Bandung & Surabaya syndicate)
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Robot Trading Palsu",
        "rawInput": "Halo kak! Kami dari tim Autopilot Trading Gold. Modal mulai Rp 500.000 profit konsisten 15% per hari tanpa ribet analisa. Dana dijamin garansi modal 100%. Silakan transfer ke BCA 8830192841 an PT Cuan Digital Makmur dan hubungi admin di 081298765432. Info lengkap: https://cuan-autopilot.pro",
        "notes": "Menjanjikan fixed return tidak realistis 15% per hari dengan garansi modal.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": "cuan-autopilot.pro", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Robot Trading Palsu",
        "rawInput": "Selamat siang, slot VIP robot trading tinggal 3 orang saja hari ini! Bukti withdraw sudah ribuan member. Transfer segera deposit awal Rp 1.000.000 ke BCA 8830192841 an PT Cuan Digital Makmur, konfirmasi via WA 081298765432. Cek dashboard kita di https://cuan-autopilot.pro/login",
        "notes": "Sindikat yang sama dengan akun BCA 8830192841, memakai urgensi slot terbatas.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": "cuan-autopilot.pro", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Robot Trading Palsu",
        "rawInput": "Peluang passive income dari rumah! Bot AI Trading Forex otomatis cuan tiap minggu 50%. Titip dana mulai 2 juta langsung terima profit harian. Kontak konsultan kami di WA 081298765432. Kunjungi situs resmi https://profit-harian-vip.com",
        "notes": "Klaim bot AI trading otomatis dengan return bombastis.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": "profit-harian-vip.com", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Robot Trading Palsu",
        "rawInput": "Program titip dana trading terpercaya amanah. Paket Bronze 1jt dapat 3jt dalam 3 hari, Paket Silver 5jt dapat 15jt dalam 7 hari. Tanpa resiko loss karena ada insurance fund. Hubungi CS di 085712345678 atau transfer Mandiri 1370019284711 an Rendy. Web: https://profit-harian-vip.com/daftar",
        "notes": "Skema titip dana gandakan uang berkedok trading forex.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "085712345678", "domain": "profit-harian-vip.com", "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Robot Trading Palsu",
        "rawInput": "Investasi bot trading emas anti-margin call. Dikelola trader berpengalaman. Cukup deposit ke Mandiri 1370019284711 an Rendy dan kirim bukti transfer ke WA 087899887766. Profit dibagikan setiap jam 8 malam langsung masuk rekening anda.",
        "notes": "Janji profit dibagikan harian tanpa risiko.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": None, "city": "Surabaya", "province": "Jawa Timur"
    },

    # ── Skema Ponzi / Piramida & Komisi Berlevel
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Ponzi",
        "rawInput": "Komunitas Sahabat Finansial Sejahtera! Bonus referral 20% setiap rekrut downline baru. Cukup ajak 5 orang passive income mengalir tiap bulan tanpa kerja. Biaya member Rp 250.000 ke BSI 7192837465 an Komunitas Berkah. Info WA 087899887766.",
        "notes": "Skema piramida klasik mengandalkan uang pendaftaran member baru.",
        "bankName": "BSI", "bankAccount": "7192837465", "phoneNumber": "087899887766", "domain": None, "city": "Semarang", "province": "Jawa Tengah"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Ponzi",
        "rawInput": "Arisan online get duar kelipatan 5x lipat! Bayar 500rb get 2.500.000 dalam 10 hari. Sudah berbadan hukum legal. Kuota kloter 12 tinggal 2 nama. Minat chat admin 087899887766 atau transfer slot ke BSI 7192837465 sekarang juga!",
        "notes": "Arisan online bodong dengan skema ponzi get berlipat ganda.",
        "bankName": "BSI", "bankAccount": "7192837465", "phoneNumber": "087899887766", "domain": None, "city": "Solo", "province": "Jawa Tengah"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Ponzi",
        "rawInput": "Bisnis affiliate revolusioner sistem binary. Bonus pasangan 100rb per pasang, reward mobil Avanza setelah capai 50 downline aktif. Pendaftaran kirim ke BSI 7192837465 dan aktivasi akun di https://profit-harian-vip.com/member",
        "notes": "Money game berkedok affiliate marketing sistem binary.",
        "bankName": "BSI", "bankAccount": "7192837465", "phoneNumber": "087899887766", "domain": "profit-harian-vip.com", "city": "Yogyakarta", "province": "DIY"
    },

    # ── Crypto Scam, Fake Token & Rug Pull
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Scam Kripto",
        "rawInput": "Presale token $GARUDA gem 100x moonshot! Listing di Indodax & Binance minggu depan. Harga presale hanya Rp 10 per koin. Beli sekarang sebelum harga terbang di https://token-presale-cuan.xyz atau kirim dana ke Mandiri 1370019284711. Konsultasi WA: 087899887766",
        "notes": "Fake token presale rug pull mengklaim listing di exchange ternama.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": "token-presale-cuan.xyz", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Scam Kripto",
        "rawInput": "Airdrop gratis 1.000 USDT dari Binance Indonesia! Cukup hubungkan dompet Trust Wallet atau MetaMask anda dan masukkan 12 kata kunci (seed phrase) pemulihan di https://token-presale-cuan.xyz/claim. Kuota terbatas 500 wallet tercepat.",
        "notes": "Phishing crypto menguras dompet korban dengan meminta seed phrase.",
        "bankName": None, "bankAccount": None, "phoneNumber": "087899887766", "domain": "token-presale-cuan.xyz", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Scam Kripto",
        "rawInput": "Mining bitcoin cloud hash rate tinggi tanpa alat. Profit harian 0.05 BTC langsung cair. Modal sewa mesin slot 1jt kirim ke Mandiri 1370019284711. Kontak admin kripto di Telegram @cuan_btc atau WA 087899887766.",
        "notes": "Fake cloud mining scam dengan rekening Mandiri sindikat Surabaya.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": None, "city": "Surabaya", "province": "Jawa Timur"
    },

    # ── Task Scam / Lowongan Kerja Freelance Palsu
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Palsu",
        "rawInput": "Lowongan kerja paruh waktu online dari rumah (WFH). Tugas hanya like dan follow akun video Shopee & TikTok. Komisi Rp 15.000 - Rp 50.000 per tugas. Gaji harian Rp 300.000 - Rp 800.000. Hubungi admin HRD di WhatsApp 085712345678 atau daftar di https://shopee-freelance-task.vip",
        "notes": "Task scam pancingan awal komisi kecil lalu suruh deposit bertingkat.",
        "bankName": None, "bankAccount": None, "phoneNumber": "085712345678", "domain": "shopee-freelance-task.vip", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Palsu",
        "rawInput": "Selamat! Anda telah menyelesaikan 3 tugas percobaan dan berhak naik ke level VIP. Untuk mencairkan reward Rp 2.400.000, silakan top up deposit saldo tugas sebesar Rp 750.000 ke BNI 0819283746 an PT Kreasi Media Digital. Kirim bukti ke WA 085712345678.",
        "notes": "Korban dipaksa deposit uang jika ingin menarik komisi yang diklaim didapat.",
        "bankName": "BNI", "bankAccount": "0819283746", "phoneNumber": "085712345678", "domain": "shopee-freelance-task.vip", "city": "Bekasi", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Palsu",
        "rawInput": "Tugas akhir order pesanan merchant Lazada! Dana deposit sebelumnya Rp 1.500.000 tertahan di sistem karena salah input kode pesanan. Agar saldo bisa ditarik total Rp 6.000.000, wajib transfer penalti Rp 1.500.000 lagi ke BNI 0819283746 an PT Kreasi Media. Hubungi mentor di 085712345678 sekarang.",
        "notes": "Sunk cost trap pada task scam memeras korban dengan alasan salah kode tugas.",
        "bankName": "BNI", "bankAccount": "0819283746", "phoneNumber": "085712345678", "domain": None, "city": "Tangerang", "province": "Banten"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Palsu",
        "rawInput": "Dibutuhkan 15 staf review produk e-commerce. Gaji harian Rp 500.000 dibayar langsung. Tanpa pengalaman dan tanpa wawancara. Daftar sekarang melalui situs mitra kami https://shopee-freelance-task.vip/join atau hubungi 085712345678.",
        "notes": "Penipuan lowongan kerja freelance dengan iming-iming gaji harian tinggi.",
        "bankName": None, "bankAccount": None, "phoneNumber": "085712345678", "domain": "shopee-freelance-task.vip", "city": "Jakarta", "province": "DKI Jakarta"
    },

    # ── Phishing Perbankan & APK Undangan
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "PEMBERITAHUAN RESMI BANK BCA: Nasabah Yth, per 1 Juni akan diberlakukan kenaikan tarif transaksi antar bank menjadi Rp 150.000/bulan. Jika Anda setuju dengan tarif lama Rp 6.500, segera konfirmasi pembatalan tarif baru melalui tautan resmi kami di https://bca-tarif-baru.info/konfirmasi atau hubungi halo BCA di 081388776655.",
        "notes": "Phishing perubahan tarif BCA yang meminta korban login dan input OTP.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": "081388776655", "domain": "bca-tarif-baru.info", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Akun Rekening Anda Terindikasi Mencurigakan! Demi keamanan saldo, akun dibekukan sementara. Segera lakukan verifikasi ulang identitas dan nomor kartu debit anda di portal pemulihan https://bca-tarif-baru.info/auth atau hubungi customer service di 081388776655.",
        "notes": "Social engineering menakut-nakuti akun dibekukan agar korban panik memasukkan data rahasia.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081388776655", "domain": "bca-tarif-baru.info", "city": "Depok", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Kepada Yth Bapak/Ibu, Kami mengundang untuk hadir pada pesta pernikahan kami. Mohon doa restu dan kehadiran. Surat Undangan Pernikahan Digital kami kirimkan dalam format aplikasi, silakan unduh di https://undangan-pernikahan-digital.apk-download.biz/SuratUndangan.apk. Terima kasih. Kontak pengantin: 081388776655.",
        "notes": "Modus malware APK undangan pernikahan pencuri SMS OTP perbankan.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081388776655", "domain": "undangan-pernikahan-digital.apk-download.biz", "city": "Medan", "province": "Sumatera Utara"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Peringatan Pemutusan Listrik PLN! Tagihan listrik anda tertunggak 2 bulan sebesar Rp 450.000. Untuk pembatalan pemutusan segera transfer ke rekening Jago 10928374619 an Petugas Penagihan PLN atau unduh rincian surat tugas di https://undangan-pernikahan-digital.apk-download.biz/SuratTugas.apk. WA CS: 081388776655.",
        "notes": "Malware APK berkedok tagihan PLN dengan penampung bank Jago sindikat.",
        "bankName": "Jago", "bankAccount": "10928374619", "phoneNumber": "081388776655", "domain": "undangan-pernikahan-digital.apk-download.biz", "city": "Palembang", "province": "Sumatera Selatan"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Paket J&T Express Anda tertahan di gudang pusat karena nomor resi tidak terbaca. Mohon cek foto paket dan verifikasi alamat penerima pada aplikasi resi resmi kami: https://undangan-pernikahan-digital.apk-download.biz/LihatFotoPaket.apk. Konfirmasi via kurir 081388776655.",
        "notes": "Modus pencurian OTP lewat malware APK kurir ekspedisi.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081388776655", "domain": "undangan-pernikahan-digital.apk-download.biz", "city": "Makassar", "province": "Sulawesi Selatan"
    },

    # ── Pinjol Ilegal & Gestun
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Pinjol Ilegal",
        "rawInput": "Dana Cepat Kilat langsung cair 5 menit tanpa jaminan! Pinjaman dana 5 juta sampai 100 juta bunga 0% tenor hingga 3 tahun. Cukup KTP saja tanpa BI checking. Hubungi admin pencairan di WhatsApp 089655443322 sekarang juga!",
        "notes": "Pinjol ilegal pemeras data kontak dengan klaim bunga 0% tanpa syarat.",
        "bankName": None, "bankAccount": None, "phoneNumber": "089655443322", "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Pinjol Ilegal",
        "rawInput": "Pengajuan pinjaman Anda disetujui Rp 20.000.000! Untuk proses aktivasi pencairan dana ke rekening Anda, diwajibkan membayar biaya provisi dan administrasi sebesar Rp 450.000 ke BRI 020601002948501 an Hendra Saputra. Hubungi debt collector / agen 089655443322.",
        "notes": "Scam pinjol meminta uang muka administrasi sebelum dana dicairkan.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Pinjol Ilegal",
        "rawInput": "Jasa Gestun Paylater & Kartu Kredit aman dan terpercaya. Cairkan limit Spaylater, Akulaku, Kredivo, Gopaylater rate termurah 5%. Uang cair ke rekening dalam 10 menit. Fee admin ditransfer ke BRI 020601002948501 an Hendra Saputra. Chat WA 089655443322.",
        "notes": "Jasa gesek tunai ilegal berpotensi penggelapan limit kredit.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": None, "city": "Bandung", "province": "Jawa Barat"
    },

    # ── Investasi Bodong Berlisensi OJK Palsu
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Investasi Bodong Berlisensi Palsu",
        "rawInput": "Investasi Aman Terpercaya 100% Legal diawasi OJK dan Bappebti. Dapatkan bagi hasil dividen syariah 25% setiap minggu. Modal minimal Rp 500.000. Cek sertifikat izin kami di https://ojk-verifikasi-dana.net. Konfirmasi ke WA 081298765432 atau transfer ke BCA 8830192841 an PT Cuan Digital Makmur.",
        "notes": "Mencatut logo OJK dan membuat domain tiruan untuk menipu masyarakat.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": "ojk-verifikasi-dana.net", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Investasi Bodong Berlisensi Palsu",
        "rawInput": "Layanan Bantuan Pengembalian Dana Korban Investasi Bodong! Satgas Waspada Investasi bekerjasama dengan kepolisian membantu mencairkan aset Anda yang tertahan. Biaya administrasi verifikasi berkas Rp 600.000 ditransfer ke BRI 020601002948501 an Hendra Saputra. Cek data di https://ojk-verifikasi-dana.net/klaim atau hubungi 089655443322.",
        "notes": "Recovery room scam: penipu kedua yang memangsa korban penipuan sebelumnya.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": "ojk-verifikasi-dana.net", "city": "Jakarta", "province": "DKI Jakarta"
    },

    # ── Variasi Tambahan Kasus Riil Indonesia (Entity expansion)
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Hadiah Gebyar Undian Simpedes BRI! Selamat nomor rekening anda terpilih memenangkan Mobil Honda Brio. Biaya pengurusan BPKB & STNK sebesar Rp 1.750.000 dikirim ke BRI 020601002948501 an Hendra Saputra. Hubungi panitia undian di 089655443322.",
        "notes": "Penipuan undian palsu meminta tebusan pajak hadiah.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": None, "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Scam Kripto",
        "rawInput": "Trading sinyal VIP crypto akurasi 98%. Profit puluhan persen tiap open posisi. Biaya membership seumur hidup 1.5 juta ke Mandiri 1370019284711 an Rendy. Bergabung sekarang di channel https://profit-harian-vip.com/crypto atau chat admin 087899887766.",
        "notes": "Grup sinyal trading berbayar abal-abal.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": "profit-harian-vip.com", "city": "Medan", "province": "Sumatera Utara"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Robot Trading Palsu",
        "rawInput": "Pensiun dini dengan passive income robot trading emas gold. Garansi anti loss, profit 10% per minggu. Gabung segera deposit awal transfer ke BCA 8830192841 an PT Cuan Digital Makmur. Hubungi leader di 081298765432.",
        "notes": "Janji pensiun dini dan anti loss robot trading emas.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": "cuan-autopilot.pro", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Palsu",
        "rawInput": "Kerja sampingan tekan like video youtube! 1 like dibayar Rp 10.000. Hari ini butuh 20 orang. Uang langsung masuk rekening. Daftar sekarang ke admin WA 085712345678 atau kunjungi https://shopee-freelance-task.vip.",
        "notes": "Pancingan task scam like video youtube berhadiah uang cepat.",
        "bankName": None, "bankAccount": None, "phoneNumber": "085712345678", "domain": "shopee-freelance-task.vip", "city": "Semarang", "province": "Jawa Tengah"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Info Bank BRI: Segera perbarui aplikasi BRImo anda ke versi 3.0 untuk menghindari pemblokiran transaksi. Unduh update resmi melalui https://bca-tarif-baru.info/brimo-update.apk atau hubungi call center 081388776655.",
        "notes": "Phishing mengatasnamakan update BRImo dengan menyebarkan malware APK.",
        "bankName": "BRI", "bankAccount": None, "phoneNumber": "081388776655", "domain": "bca-tarif-baru.info", "city": "Yogyakarta", "province": "DIY"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Ponzi",
        "rawInput": "Investasi ternak lele modern sistem syariah. Modal Rp 1.000.000 bagi hasil Rp 300.000 tiap bulan selama 1 tahun. Modal kembali 100% saat panen. Setoran dana kirim ke BSI 7192837465 an Komunitas Berkah. Info: 087899887766.",
        "notes": "Investasi fiktif ternak lele berkedok syariah.",
        "bankName": "BSI", "bankAccount": "7192837465", "phoneNumber": "087899887766", "domain": None, "city": "Bogor", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Peringatan Bank Jago: Transaksi transfer keluar Rp 3.500.000 terdeteksi dari akun Anda. Jika bukan Anda yang melakukan, batalkan segera di tautan https://bca-tarif-baru.info/jago atau kontak petugas di 081388776655.",
        "notes": "Fake transaction notification memancing korban panik mengklik link phishing.",
        "bankName": "Jago", "bankAccount": "10928374619", "phoneNumber": "081388776655", "domain": "bca-tarif-baru.info", "city": "Jakarta", "province": "DKI Jakarta"
    },
    # ── Additional Diverse Scam Samples (Cross-connected)
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Jastip Tiket Konser Palsu",
        "rawInput": "Jastip tiket konser Coldplay CAT 1 ready 2 tiket! Butuh cepat karena ga jadi nonton. Harga normal tanpa markup. Minat langsung transfer DP 50% ke BCA 8830192841 an PT Cuan Digital Makmur dan hubungi WA 081298765432. Bukti e-ticket dikirim via email.",
        "notes": "Penipuan tiket konser online meminta uang muka.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Giveaway Palsu",
        "rawInput": "SELAMAT! Nomor WhatsApp Anda terpilih mendapatkan Hadiah Uang Tunai Rp 50.000.000 dari Giveaway Baim Wong & Paula. Untuk klaim hadiah silakan bayar biaya administrasi pencairan dan pajak pemenang sebesar Rp 350.000 ke BRI 020601002948501 an Hendra Saputra. Konfirmasi WA 089655443322.",
        "notes": "Modus tebus pajak hadiah giveaway artis fiktif.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": None, "city": "Medan", "province": "Sumatera Utara"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Love Scam / Catfishing",
        "rawInput": "Sayang, koper dan hadiah jam tangan mewah yang kukirim dari London saat ini tertahan di Bea Cukai Bandara Soekarno Hatta. Petugas meminta pembayaran bea masuk darurat Rp 2.500.000 ke Mandiri 1370019284711 an Rendy. Tolong bayarkan dulu ya, nanti kuganti saat tiba di Jakarta. Hubungi petugas di 087899887766.",
        "notes": "Love scam paket hadiah tertahan bea cukai.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": None, "city": "Tangerang", "province": "Banten"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lelang Pegadaian Palsu",
        "rawInput": "LELANG TERTUTUP PEGADAIAN SYARIAH: iPhone 15 Pro Max 256GB barang sitaan lelang resmi negara harga Rp 4.500.000 kondisi segel. Hanya untuk 5 pemenang pertama. Uang jaminan lelang ditransfer ke BSI 7192837465 an Komunitas Berkah. Info panitia lelang di 087899887766 atau https://ojk-verifikasi-dana.net/lelang.",
        "notes": "Lelang barang sitaan fiktif harga murah tidak masuk akal.",
        "bankName": "BSI", "bankAccount": "7192837465", "phoneNumber": "087899887766", "domain": "ojk-verifikasi-dana.net", "city": "Makassar", "province": "Sulawesi Selatan"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "KEPOLISIAN NEGARA REPUBLIK INDONESIA: Pemberitahuan Surat Tilang Elektronik (ETLE). Kendaraan Anda tertangkap kamera melanggar marka jalan. Silakan buka dan instal dokumen surat tilang resmi berikut di https://undangan-pernikahan-digital.apk-download.biz/SuratTilang.apk untuk melihat foto bukti dan jadwal sidang. Kontak penyidik: 081388776655.",
        "notes": "Malware APK tilang elektronik palsu pencuri SMS perbankan.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081388776655", "domain": "undangan-pernikahan-digital.apk-download.biz", "city": "Semarang", "province": "Jawa Tengah"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Mama Minta Pulsa",
        "rawInput": "Halo nak, ini nomor baru mama. Hp mama yang lama rusak. Tolong transferkan uang belanja 750 ribu ke rekening teman mama di BCA 8830192841 an PT Cuan Digital Makmur sekarang ya, mama lagi di pasar. Nanti mama telpon balik ke 081298765432.",
        "notes": "Penipuan berpura-pura menjadi anggota keluarga mendesak transfer uang.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": None, "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Investasi Bodong",
        "rawInput": "Peluang investasi sektor migas bagi hasil mingguan 30%. Dikelola tim ahli perminyakan. Modal 5 juta hasil 1.5 juta per minggu. Transfer pendaftaran ke Mandiri 1370019284711 an Rendy. Website: https://profit-harian-vip.com/oil.",
        "notes": "Investasi fiktif sektor migas hasil mingguan tidak wajar.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": "profit-harian-vip.com", "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Palsu",
        "rawInput": "Komisi harian like & komentar video TikTok artis! 1 tugas Rp 20.000. Cukup sediakan waktu 15 menit sehari. Pendaftaran gratis dan langsung dapat bonus saldo Rp 50.000. Gabung grup tugas telegram di https://shopee-freelance-task.vip/tiktok atau hubungi admin di WA 085712345678.",
        "notes": "Task scam video tiktok dengan iming-iming bonus instan.",
        "bankName": None, "bankAccount": None, "phoneNumber": "085712345678", "domain": "shopee-freelance-task.vip", "city": "Yogyakarta", "province": "DIY"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Scam Kripto",
        "rawInput": "Bot mining crypto otomatis menghasilkan 50 DOGE per jam. Withdraw instan tanpa deposit awal untuk tier standar. Upgrade ke VIP bot hanya Rp 500.000 ke BNI 0819283746 an PT Kreasi Media. Hubungi developer di 085712345678 atau kunjungi https://token-presale-cuan.xyz/bot.",
        "notes": "Fake crypto bot scam memungut biaya upgrade VIP bot.",
        "bankName": "BNI", "bankAccount": "0819283746", "phoneNumber": "085712345678", "domain": "token-presale-cuan.xyz", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Finansial",
        "rawInput": "Akun DANA Anda terpilih mendapatkan upgrade DANA Kaget Rp 2.000.000. Klik tautan verifikasi akun https://bca-tarif-baru.info/dana dan masukkan nomor HP serta PIN akun dompet digital Anda. Kontak support WA 081388776655.",
        "notes": "Phishing akun DANA meminta PIN dompet digital.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081388776655", "domain": "bca-tarif-baru.info", "city": "Depok", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Pinjol Ilegal",
        "rawInput": "Cairkan limit Paylater Shopee, Kredivo, Indodana, Akulaku langsung cair ke rekening bank Anda. Fee hanya 4%. Proses 5 menit. Hubungi agen pencairan cepat di WA 089655443322. Biaya admin kirim ke BRI 020601002948501 an Hendra Saputra.",
        "notes": "Jasa gestun paylater berisiko penggelapan dan pencurian akun.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": None, "city": "Bekasi", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Franchise Bodong",
        "rawInput": "Franchise Kopi Kekinian modal 3 juta jaminan omset 15 juta per bulan tanpa repot kelola gerai (sistem autopilot bagi hasil). Dana investasi ditampung di BCA 8830192841 an PT Cuan Digital Makmur. Brosur lengkap hubungi 081298765432.",
        "notes": "Franchise minuman fiktif janji pasif income autopilot.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Game",
        "rawInput": "Promo topup diamond Mobile Legends 5000 diamond hanya Rp 100.000. Legal 100% via login moonton. Masukkan email dan password akun game anda di https://shopee-freelance-task.vip/topup atau transfer ke BNI 0819283746. Admin WA 085712345678.",
        "notes": "Phishing pencurian akun game online dan transfer bodong.",
        "bankName": "BNI", "bankAccount": "0819283746", "phoneNumber": "085712345678", "domain": "shopee-freelance-task.vip", "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Sewa Villa Palsu",
        "rawInput": "Sewa Villa Private Pool Seminyak Bali promo weekend hanya 1.5 juta/malam (harga normal 5 juta). Booking tanggal sekarang DP 50% kirim ke Mandiri 1370019284711 an Rendy. Kontak marketing via WA 087899887766.",
        "notes": "Penipuan sewa villa fiktif di Bali.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": None, "city": "Denpasar", "province": "Bali"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Palsu BUMN",
        "rawInput": "Panggilan Tes Wawancara Kerja PT Pertamina (Persero) di Jakarta. Seluruh akomodasi tiket pesawat dan hotel wajib dipesan melalui biro travel rekanan. Transfer biaya reservasi tiket Rp 1.850.000 ke BRI 020601002948501 an Hendra Saputra. Info panitia: 089655443322.",
        "notes": "Penipuan rekrutmen BUMN mewajibkan beli tiket pesawat rekanan.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Saham Pre-IPO Palsu",
        "rawInput": "Penawaran eksklusif saham pre-IPO perusahaan unicorn teknologi sebelum melantai di Bursa Efek Indonesia. Target return 300% saat listing. Minimal investasi 10 juta ke rekening penampung BSI 7192837465 an Komunitas Berkah. Info broker: 087899887766.",
        "notes": "Penipuan saham pra-IPO tanpa izin bursa/OJK.",
        "bankName": "BSI", "bankAccount": "7192837465", "phoneNumber": "087899887766", "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lowongan Kerja Luar Negeri Palsu",
        "rawInput": "Kerja di perkebunan Australia gaji 40 juta per bulan. Biaya visa dan paspor kerja disubsidi, cukup bayar biaya medical check up Rp 850.000 ke Jago 10928374619. Kontak agensi di 081388776655.",
        "notes": "Penipuan pekerja migran luar negeri tanpa agen PJTKI resmi.",
        "bankName": "Jago", "bankAccount": "10928374619", "phoneNumber": "081388776655", "domain": None, "city": "Kupang", "province": "NTT"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Phishing Akun E-Commerce",
        "rawInput": "Tokopedia Security Alert: Akun Anda sedang login di perangkat tidak dikenal dari Singapura. Segera amankan akun dan ganti kata sandi di https://bca-tarif-baru.info/tokopedia atau hubungi tim keamanan di 081388776655.",
        "notes": "Phishing mengatasnamakan Tokopedia alert.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081388776655", "domain": "bca-tarif-baru.info", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Modus Salah Transfer",
        "rawInput": "Selamat siang, saya tidak sengaja salah transfer uang Rp 3.000.000 ke rekening Anda. Mohon kerjasamanya tolong segera kembalikan dana tersebut ke rekening BRI 020601002948501 an Hendra Saputra. Konfirmasi di 089655443322.",
        "notes": "Modus pura-pura salah transfer dana pinjol ilegal.",
        "bankName": "BRI", "bankAccount": "020601002948501", "phoneNumber": "089655443322", "domain": None, "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Lelang Mobil Tarikan Leasing",
        "rawInput": "Lelang kilat tarikan leasing Toyota Innova Reborn tahun 2022 harga Rp 110.000.000 surat lengkap STNK BPKB. Tanda jadi booking unit 5 juta transfer ke BCA 8830192841 an PT Cuan Digital Makmur. Hubungi sales leasing di 081298765432.",
        "notes": "Penipuan jual beli mobil tarikan leasing fiktif.",
        "bankName": "BCA", "bankAccount": "8830192841", "phoneNumber": "081298765432", "domain": None, "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Arisan Bodong",
        "rawInput": "Arisan emas batangan Antam 10 gram kocokan tiap tanggal 1. Iuran per bulan hanya 250 ribu. Tersedia 10 slot. Pembayaran iuran ke BSI 7192837465 an Komunitas Berkah. Hubungi ketua arisan di 087899887766.",
        "notes": "Arisan online emas batangan skema ponzi.",
        "bankName": "BSI", "bankAccount": "7192837465", "phoneNumber": "087899887766", "domain": None, "city": "Solo", "province": "Jawa Tengah"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Jasa Pembersihan BI Checking",
        "rawInput": "Biro jasa pembersihan nama blacklist BI Checking dan SLIK OJK kilat 1 hari bersih. Melayani skor kredit macet agar bisa ajukan KPR dan pinjaman bank. Biaya jasa Rp 1.200.000 ke Mandiri 1370019284711 an Rendy. Konsultasi WA: 087899887766.",
        "notes": "Klaim palsu menghapus catatan kredit macet BI Checking.",
        "bankName": "Mandiri", "bankAccount": "1370019284711", "phoneNumber": "087899887766", "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Trading Kripto Arbitrase",
        "rawInput": "Platform arbitrase kripto otomatis membeli di harga rendah dan menjual di harga tinggi lintas exchange. Profit bersih 3% per transaksi. Join pool dana di https://cuan-autopilot.pro/arbitrage atau hubungi WA 081298765432.",
        "notes": "Investasi arbitrase kripto fiktif.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081298765432", "domain": "cuan-autopilot.pro", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Undian Belanja Palsu",
        "rawInput": "Selamat Anda mendapatkan Voucher Belanja Gratis Alfamart Rp 1.500.000 dalam rangka HUT ke-25. Untuk aktivasi kode voucher kirim pulsa 50rb ke 089655443322 atau verifikasi data di https://bca-tarif-baru.info/alfamart.",
        "notes": "Penipuan voucher belanja minta pulsa tebusan.",
        "bankName": None, "bankAccount": None, "phoneNumber": "089655443322", "domain": "bca-tarif-baru.info", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": True,
        "scamCategory": "Jasa Medsos Palsu",
        "rawInput": "Jasa centang biru verified Instagram dan tambah 50.000 followers aktif Indonesia hanya Rp 750.000. Bayar DP ke BNI 0819283746 an PT Kreasi Media. Hubungi CS di 085712345678.",
        "notes": "Jasa centang biru instagram bodong.",
        "bankName": "BNI", "bankAccount": "0819283746", "phoneNumber": "085712345678", "domain": None, "city": "Malang", "province": "Jawa Timur"
    },
]

# ── 3. Legitimate Financial Samples (label = False) ──────────────────────────
LEGITIMATE_SAMPLES = [
    # ── Official Bank Transfer Notifications
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "M-TRANSFER: BERHASIL. Tgl: 15/09 10:24:12. Transfer ke BCA 5220394812 an AHMAD FAUZI sebesar Rp 500.000,00. No Ref: 202609151024128912. Hubungi HaloBCA 1500888 jika butuh bantuan. Simpan bukti transfer ini sebagai referensi sah.",
        "notes": "Format resmi bukti transfer m-BCA.",
        "bankName": "BCA", "bankAccount": "5220394812", "phoneNumber": None, "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "LIVIN' BY MANDIRI: Transaksi BI-FAST berhasil. Sumber: Tabungan Mandiri 1230009876543. Tujuan: BRI 011101002345501 an SITI RAHMAWATI. Nominal: Rp 1.250.000,00. Biaya admin: Rp 2.500. ID Transaksi: MBF20260915091244. Mandiri Call 14000.",
        "notes": "Notifikasi transaksi transfer BI-FAST resmi Livin by Mandiri.",
        "bankName": "Mandiri", "bankAccount": "1230009876543", "phoneNumber": None, "domain": None, "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "BRIMO NOTIFIKASI: Transfer sesama BRI berhasil pada 15/09/2026 14:05 WIB. Dari Rekening 020601009876509 ke 034101004567503 an BUDI SANTOSO. Jumlah: Rp 2.000.000. Ref: TRF98124019284. Call BRI 1500017.",
        "notes": "Notifikasi resmi transaksi transfer BRImo.",
        "bankName": "BRI", "bankAccount": "020601009876509", "phoneNumber": None, "domain": None, "city": "Semarang", "province": "Jawa Tengah"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "BNI Mobile Banking: Pembayaran QRIS sebesar Rp 75.000 ke KOPI KENANGAN berhasil pada 15/09/2026 12:30. Sisa saldo rekening BNI 0451234567 Anda adalah Rp 3.420.000. BNI Call 1500046. https://bni.co.id",
        "notes": "Notifikasi pembayaran QRIS resmi BNI Mobile.",
        "bankName": "BNI", "bankAccount": "0451234567", "phoneNumber": None, "domain": "bni.co.id", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "Bank Syariah Indonesia: Pembelian pulsa Telkomsel Rp 100.000 berhasil didebit dari rekening BSI 7012345678. Saldo akhir Rp 1.850.000. Hubungi BSI Call 14040 atau kunjungi https://bankbsi.co.id",
        "notes": "Notifikasi resmi transaksi BSI Mobile.",
        "bankName": "BSI", "bankAccount": "7012345678", "phoneNumber": None, "domain": "bankbsi.co.id", "city": "Banda Aceh", "province": "Aceh"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "Bank Jago: Anda menerima transfer dana masuk sebesar Rp 350.000 dari KANTOOR DIGITAL ke Kantong Utama Jago 10123456789. Saldo Anda telah diperbarui. Info lebih lanjut buka aplikasi Jago atau kunjungi https://jago.com",
        "notes": "Notifikasi penerimaan transfer resmi Bank Jago.",
        "bankName": "Jago", "bankAccount": "10123456789", "phoneNumber": None, "domain": "jago.com", "city": "Jakarta", "province": "DKI Jakarta"
    },

    # ── Official OJK Regulated Investments (Bibit, Bareksa, Stockbit, IPOT)
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "Bibit: Pembelian Reksa Dana Pasar Uang Sucorinvest Money Market Fund sebesar Rp 1.000.000 telah berhasil diverifikasi oleh Bank Kustodian. Portofolio Anda kini tercatat di KSEI. PT Bibit Tumbuh Bersama berizin dan diawasi OJK. Cek rincian di aplikasi Bibit atau https://bibit.id",
        "notes": "Konfirmasi resmi pembelian reksa dana platform Bibit berizin OJK.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "bibit.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "Bareksa: Investasi Surat Berharga Negara (SBN) seri ORI025 telah terbit. Imbal hasil kupon 6.25% p.a dijamin penuh oleh Undang-Undang Republik Indonesia. PT Bareksa Portal Investasi adalah mitra distribusi resmi Kementerian Keuangan dan diawasi OJK. Kunjungi https://bareksa.com/sbn",
        "notes": "Penerbitan SBN resmi mitra Kementerian Keuangan bergaransi negara.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "bareksa.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "Stockbit Sekuritas: Order BELI 10 lot saham BBCA pada harga Rp 10.200 telah match (terpenuhi). RDN BCA Anda terdebit Rp 10.215.300 termasuk fee broker. Laporan konfirmasi perdagangan (Trade Confirmation) telah dikirim ke email terdaftar. PT Stockbit Sekuritas berizin OJK. Web: https://stockbit.com",
        "notes": "Konfirmasi transaksi jual-beli saham resmi dari broker Stockbit Sekuritas.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": None, "domain": "stockbit.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "IPOT Indo Premier: Dividen tunai dari emiten TLKM sebesar Rp 150.000 telah efektif masuk ke Rekening Dana Nasabah (RDN) Mandiri Anda. Tidak ada potongan biaya tambahan selain pajak dividen 10%. Layanan nasabah IPOT: 02150887200. Web: https://indopremier.com",
        "notes": "Pemberitahuan dividen tunai saham resmi dari Indo Premier Sekuritas.",
        "bankName": "Mandiri", "bankAccount": None, "phoneNumber": None, "domain": "indopremier.com", "city": "Jakarta", "province": "DKI Jakarta"
    },

    # ── Official Security Warnings & OTP Alerts (Bank Notifications)
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Security Alert",
        "rawInput": "WASPADA PENIPUAN DARI BANK MANDIRI: Bank Mandiri TIDAK PERNAH meminta nomor OTP, PIN, password, nomor CVV/CVC kartu kredit, atau meminta nasabah mengklik tautan tidak resmi melalui WhatsApp/SMS. Jangan pernah membagikan kode OTP kepada siapapun termasuk petugas bank. Info resmi hanya di https://bankmandiri.co.id atau Mandiri Call 14000.",
        "notes": "Edukasi keamanan resmi dari perbankan mengingatkan nasabah menjaga kerahasiaan OTP.",
        "bankName": "Mandiri", "bankAccount": None, "phoneNumber": None, "domain": "bankmandiri.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Security Alert",
        "rawInput": "KODE OTP BCA Anda adalah 849201 untuk otorisasi pendaftaran fitur debit online. RAHASIA! JANGAN BERIKAN KODE INI KEPADA SIAPAPUN TERMASUK PIHAK BCA. Waspadai modus penipuan undian atau pembaharuan tarif. HaloBCA 1500888.",
        "notes": "SMS OTP transaksi resmi dengan peringatan keras kerahasiaan.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": None, "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Security Alert",
        "rawInput": "PERINGATAN RESMI OTORITAS JASA KEUANGAN (OJK): Masyarakat diimbau untuk selalu memeriksa legalitas entitas penawaran investasi sebelum menempatkan dana melalui Kontak OJK 157, WhatsApp resmi OJK 081157157157, atau email konsumen@ojk.go.id. Hindari tawaran imbal hasil pasti di luar batas wajar. Situs resmi: https://ojk.go.id",
        "notes": "Peringatan edukasi resmi dari Satgas OJK kepada masyarakat.",
        "bankName": None, "bankAccount": None, "phoneNumber": "081157157157", "domain": "ojk.go.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "Halo Kak, terima kasih telah menghubungi Customer Care Bank BCA melalui Halo BCA resmi. Mengenai keluhan kartu debit Anda yang tertelan di mesin ATM, pemblokiran darurat telah berhasil kami proses. Silakan kunjungi kantor cabang BCA terdekat dengan membawa e-KTP untuk penggantian kartu baru. Web: https://bca.co.id",
        "notes": "Respon resmi layanan bantuan nasabah Halo BCA.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": None, "domain": "bca.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking",
        "rawInput": "Tagihan Kartu Kredit CIMB Niaga Anda untuk periode September 2026 telah terbit dengan total Rp 1.450.000. Tanggal jatuh tempo 28 September 2026. Pembayaran dapat dilakukan melalui OCTO Mobile atau transfer antar bank. CIMB 14041. Web: https://cimbniaga.co.id",
        "notes": "E-statement tagihan kartu kredit resmi perbankan.",
        "bankName": "CIMB", "bankAccount": None, "phoneNumber": None, "domain": "cimbniaga.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    # ── Additional Official Financial Communications (Receipts, Payroll, E-commerce)
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official E-Commerce Receipt",
        "rawInput": "Pembayaran Tokopedia Berhasil: Transaksi pesanan #INV/20260915/MPL/39201928 senilai Rp 342.000 menggunakan Saldo GoPay telah selesai. Rincian pesanan dapat dilihat di aplikasi Tokopedia atau https://tokopedia.com. Terima kasih telah berbelanja.",
        "notes": "Notifikasi resmi pembayaran marketplace Tokopedia.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "tokopedia.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official E-Commerce Receipt",
        "rawInput": "Pesanan 260915A89JK20 telah berhasil dibayar via ShopeePay sebesar Rp 189.500. Penjual telah diberitahukan untuk segera mengirimkan pesanan Anda. Lacak pengiriman di aplikasi Shopee atau https://shopee.co.id.",
        "notes": "Notifikasi resmi pembayaran pesanan Shopee.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "shopee.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Payroll",
        "rawInput": "KREDIT OTOMATIS: Rekening BCA 5220394812 Anda menerima dana penggajian (Payroll) dari PT TEKNOLOGI NUSANTARA sebesar Rp 8.750.000. Keterangan: Gaji September 2026. Saldo efektif telah bertambah. Info resmi: https://bca.co.id.",
        "notes": "Notifikasi penggajian resmi BCA Payroll.",
        "bankName": "BCA", "bankAccount": "5220394812", "phoneNumber": None, "domain": "bca.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Payroll",
        "rawInput": "Kredit Payroll: Gaji bulanan sebesar Rp 9.200.000 dari PT SUMBER MAKMUR ABADI telah masuk ke rekening Tabungan Mandiri 1230009876543. Cek mutasi dan kelola keuangan di aplikasi Livin' by Mandiri. Mandiri Call 14000.",
        "notes": "Notifikasi payroll gaji bulanan Livin Mandiri.",
        "bankName": "Mandiri", "bankAccount": "1230009876543", "phoneNumber": None, "domain": None, "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Utility Receipt",
        "rawInput": "PLN MOBILE: Pembayaran tagihan listrik pascabayar untuk ID Pelanggan 532100982341 sebesar Rp 385.200 telah berhasil dibayar lunas melalui Virtual Account BCA pada 15/09/2026. Strum listrik dan nomor referensi tersimpan di aplikasi PLN Mobile https://pln.co.id.",
        "notes": "Bukti pembayaran resmi tagihan listrik PLN Mobile.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": None, "domain": "pln.co.id", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Utility Receipt",
        "rawInput": "Autodebit BPJS Kesehatan berhasil didebit dari rekening BRI 020601009876509 untuk 3 anggota keluarga sebesar Rp 105.000 (Kelas 3). Status kepesertaan Anda aktif. Cek status di aplikasi Mobile JKN atau Call Center BPJS 165.",
        "notes": "Notifikasi autodebit BPJS Kesehatan resmi.",
        "bankName": "BRI", "bankAccount": "020601009876509", "phoneNumber": None, "domain": None, "city": "Semarang", "province": "Jawa Tengah"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "Bareksa: Transaksi subscription Reksa Dana Pendapatan Tetap Syariah Manulife senilai Rp 2.500.000 berhasil dialokasikan pada NAB 1.420,15. Unit penyertaan: 1.760,3774 unit. PT Bareksa Portal Investasi berizin dan diawasi OJK. Rincian: https://bareksa.com.",
        "notes": "Alokasi pembelian reksa dana resmi di Bareksa.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "bareksa.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "Bibit: Pembelian Obligasi Negara Ritel SR020 senilai Rp 5.000.000 telah terverifikasi Kemenkeu. Kupon tetap 6.40% p.a akan ditransfer setiap bulan ke rekening RDN Anda. Bibit diawasi OJK. Rincian di https://bibit.id.",
        "notes": "Pembelian obligasi ritel negara resmi di Bibit.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "bibit.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Telco Receipt",
        "rawInput": "Telkom Indonesia: Pembayaran tagihan IndiHome internet nomor pelanggan 122409182390 sebesar Rp 415.000 melalui autodebit Bank BNI 0451234567 telah berhasil. Terima kasih atas kepercayaan Anda. https://telkom.co.id.",
        "notes": "Bukti autodebit tagihan internet resmi Telkom.",
        "bankName": "BNI", "bankAccount": "0451234567", "phoneNumber": None, "domain": "telkom.co.id", "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Investment Receipt",
        "rawInput": "Tabungan Emas Pegadaian: Pembelian saldo emas seberat 1.0000 gram senilai Rp 1.250.000 di Galeri 24 berhasil diproses. Saldo emas Anda kini 5.4200 gram. Pegadaian berizin dan diawasi OJK. Unduh aplikasi Pegadaian Digital di https://pegadaian.co.id.",
        "notes": "Transaksi resmi tabungan emas fisik Pegadaian.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "pegadaian.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Fintech Transfer",
        "rawInput": "Flip: Transaksi transfer dana Rp 1.500.000 ke Bank Mandiri an RINA KUSUMA telah sukses diproses tanpa biaya admin (gratis). ID Transaksi: FLP92019482. PT Fliptech Lentera Inspirasi Pertiwi berizin Bank Indonesia. Cek di https://flip.id.",
        "notes": "Konfirmasi transfer dana resmi aplikasi Flip.",
        "bankName": "Mandiri", "bankAccount": None, "phoneNumber": None, "domain": "flip.id", "city": "Depok", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Fintech Transfer",
        "rawInput": "OY! Indonesia: Transfer dana Rp 750.000 ke rekening BCA 5220394812 sukses terkirim. Waktu proses: 15/09/2026 11:20 WIB. OY! berlisensi resmi Bank Indonesia sebagai Penyelenggara Transfer Dana. Web: https://oyindonesia.com.",
        "notes": "Bukti transfer dana resmi OY! Indonesia.",
        "bankName": "BCA", "bankAccount": "5220394812", "phoneNumber": None, "domain": "oyindonesia.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Fuel Receipt",
        "rawInput": "MyPertamina: Pembayaran BBM Pertamax senilai Rp 150.000 di SPBU 31.12401 menggunakan LinkAja berhasil. Poin MyPertamina Anda bertambah 15 poin. Kunjungi https://mypertamina.id.",
        "notes": "Resi pembayaran BBM resmi MyPertamina.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "mypertamina.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Insurance Receipt",
        "rawInput": "Prudential Indonesia: Pembayaran premi asuransi polis nomor 09283741 sebesar Rp 650.000 telah berhasil didebit dari kartu kredit Mandiri Anda. Terima kasih atas perlindungan proteksi keluarga Anda. https://prudential.co.id.",
        "notes": "Konfirmasi pembayaran premi asuransi resmi Prudential.",
        "bankName": "Mandiri", "bankAccount": None, "phoneNumber": None, "domain": "prudential.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Merchant Settlement",
        "rawInput": "QRIS Merchant BCA: Transaksi terima pembayaran QRIS dari pembeli sebesar Rp 85.000 telah masuk ke rekening usaha BCA 5220394812 Anda. Settlement dana otomatis masuk pada pukul 23.00 WIB. Info: https://bca.co.id.",
        "notes": "Laporan resmi penerimaan transaksi QRIS merchant bank.",
        "bankName": "BCA", "bankAccount": "5220394812", "phoneNumber": None, "domain": "bca.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Security Alert",
        "rawInput": "myBCA Notifikasi Keamanan: Akun myBCA Anda baru saja diakses dari perangkat iPhone 14 di Jakarta pada 15/09 09:15 WIB. Jika ini adalah Anda, abaikan pesan ini. Jika mencurigakan segera hubungi Halo BCA 1500888.",
        "notes": "Notifikasi login perangkat baru resmi myBCA.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": None, "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Security Alert",
        "rawInput": "BRImo Security: Pendaftaran perangkat baru untuk username 'irwansyah' berhasil diaktivasi menggunakan verifikasi biometrik wajah. Jangan bagikan SMS kode token kepada siapa pun. Contact BRI 1500017.",
        "notes": "Notifikasi keamanan aktivasi perangkat baru BRImo.",
        "bankName": "BRI", "bankAccount": None, "phoneNumber": None, "domain": None, "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking Cash Deposit",
        "rawInput": "BCA CRM: Setoran tunai Rp 1.000.000 pada mesin CRM ATM BCA KCU Sudirman ke rekening 5220394812 telah berhasil. Saldo otomatis bertambah. Simpan struk setoran tunai ini sebagai bukti sah. https://bca.co.id.",
        "notes": "Bukti transaksi setoran tunai mesin CRM BCA.",
        "bankName": "BCA", "bankAccount": "5220394812", "phoneNumber": None, "domain": "bca.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Banking Cash Withdrawal",
        "rawInput": "Mandiri SMS Banking: Penarikan uang tunai sebesar Rp 500.000 di ATM Mandiri pada 15/09 13:45 berhasil dari rekening 1230009876543. Sisa saldo Rp 4.250.000. Mandiri Call 14000.",
        "notes": "Notifikasi penarikan tunai ATM Mandiri.",
        "bankName": "Mandiri", "bankAccount": "1230009876543", "phoneNumber": None, "domain": None, "city": "Surabaya", "province": "Jawa Timur"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "Modalku: Pendanaan invoice financing PT Berkah Logistik sebesar Rp 2.000.000 telah berhasil disalurkan dengan proyeksi bunga 14% p.a. PT Mitrausaha Indonesia Grup berizin OJK. Cek portofolio Anda di https://modalku.co.id.",
        "notes": "Penyaluran pendanaan P2P lending resmi berizin OJK.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "modalku.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Topup",
        "rawInput": "BCA m-Banking: Top Up GoPay sebesar Rp 200.000 ke nomor 081234567890 an RYAN HIDAYAT berhasil pada 15/09 15:20. Biaya admin Rp 1.000. No Ref: 20260915002910. https://bca.co.id.",
        "notes": "Notifikasi top up e-wallet resmi dari m-BCA.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": "081234567890", "domain": "bca.co.id", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Topup",
        "rawInput": "Mandiri Livin: Top Up OVO Rp 150.000 ke 081345678901 berhasil. Debit dari rekening 1230009876543. Simpan resi ini sebagai bukti transaksi yang sah. Mandiri Call 14000.",
        "notes": "Notifikasi top up OVO via Livin Mandiri.",
        "bankName": "Mandiri", "bankAccount": "1230009876543", "phoneNumber": "081345678901", "domain": None, "city": "Bandung", "province": "Jawa Barat"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Investasi Resmi OJK",
        "rawInput": "Bareksa: Pembagian dividen tunai bulanan Reksa Dana Pendapatan Tetap Syariah sebesar Rp 87.500 telah ditransfer ke saldo dompet RDN Anda. Dana dapat dicairkan kapan saja ke rekening bank. Info: https://bareksa.com.",
        "notes": "Dividen tunai bulanan reksa dana pendapatan tetap Bareksa.",
        "bankName": None, "bankAccount": None, "phoneNumber": None, "domain": "bareksa.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official Telco Receipt",
        "rawInput": "MyTelkomsel: Pembayaran paket internet Super Seru 50GB Rp 120.000 berhasil menggunakan BCA Virtual Account. Paket aktif s.d 15/10/2026. Cek kuota di aplikasi MyTelkomsel atau https://telkomsel.com.",
        "notes": "Konfirmasi pembelian kuota data MyTelkomsel.",
        "bankName": "BCA", "bankAccount": None, "phoneNumber": None, "domain": "telkomsel.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
    {
        "inputType": InputType.CHAT,
        "isScam": False,
        "scamCategory": "Official E-Commerce Refund",
        "rawInput": "Tokopedia Care: Pengembalian dana pembatalan pesanan sebesar Rp 275.000 telah berhasil dikembalikan ke limit Kartu Kredit BNI Anda dalam 1x24 jam kerja. Detail transaksi di https://tokopedia.com.",
        "notes": "Notifikasi pengembalian dana resmi dari Tokopedia Care.",
        "bankName": "BNI", "bankAccount": None, "phoneNumber": None, "domain": "tokopedia.com", "city": "Jakarta", "province": "DKI Jakarta"
    },
]


async def seed_gnn_dataset():
    """Seed comprehensive GNN training dataset into Prisma Postgres."""
    db = Prisma()
    await db.connect()

    logger.info("=" * 60)
    logger.info("SEEDING GNN TRAINING DATASET (INDONESIAN SCAM & LEGITIMATE)")
    logger.info("=" * 60)

    # 1. Seed Community Known Scam Entities
    logger.info("Seeding community known scam bank accounts...")
    for bank_name, account_num, notes in SCAM_SHARED_BANKS:
        await db.bankaccountreport.upsert(
            where={
                "bankName_accountNumber": {
                    "bankName": bank_name,
                    "accountNumber": account_num,
                }
            },
            data={
                "create": {
                    "bankName": bank_name,
                    "accountNumber": account_num,
                    "reportCount": 25,
                    "notes": notes,
                },
                "update": {
                    "reportCount": 25,
                    "notes": notes,
                },
            },
        )
    logger.info("  ✅ Community scam bank accounts seeded.")

    logger.info("Seeding community known scam phone numbers...")
    for phone_num, notes in SCAM_SHARED_PHONES:
        await db.phonereport.upsert(
            where={"phoneNumber": phone_num},
            data={
                "create": {
                    "phoneNumber": phone_num,
                    "reportCount": 18,
                    "notes": notes,
                },
                "update": {
                    "reportCount": 18,
                    "notes": notes,
                },
            },
        )
    logger.info("  ✅ Community scam phone numbers seeded.")

    # 2. Seed UserReports
    all_reports = SCAM_SAMPLES + LEGITIMATE_SAMPLES
    logger.info(f"Seeding {len(all_reports)} UserReports ({len(SCAM_SAMPLES)} scams, {len(LEGITIMATE_SAMPLES)} legitimate)...")

    created_count = 0
    updated_count = 0

    for item in all_reports:
        # Check if identical rawInput exists to avoid duplicates
        existing = await db.userreport.find_first(
            where={"rawInput": item["rawInput"]}
        )
        if existing:
            await db.userreport.update(
                where={"id": existing.id},
                data={
                    "isScam": item["isScam"],
                    "scamCategory": item["scamCategory"],
                    "bankName": item.get("bankName"),
                    "bankAccount": item.get("bankAccount"),
                    "phoneNumber": item.get("phoneNumber"),
                    "domain": item.get("domain"),
                    "city": item.get("city"),
                    "province": item.get("province"),
                    "notes": item.get("notes"),
                },
            )
            updated_count += 1
        else:
            await db.userreport.create(
                data={
                    "inputType": item["inputType"],
                    "rawInput": item["rawInput"],
                    "isScam": item["isScam"],
                    "scamCategory": item["scamCategory"],
                    "bankName": item.get("bankName"),
                    "bankAccount": item.get("bankAccount"),
                    "phoneNumber": item.get("phoneNumber"),
                    "domain": item.get("domain"),
                    "city": item.get("city"),
                    "province": item.get("province"),
                    "notes": item.get("notes"),
                }
            )
            created_count += 1

    logger.info(f"  ✅ Seeded UserReports: {created_count} created, {updated_count} updated.")

    total = await db.userreport.count()
    scams = await db.userreport.count(where={"isScam": True})
    legit = await db.userreport.count(where={"isScam": False})

    logger.info(f"\n[CURRENT DATABASE STATUS]")
    logger.info(f"  Total UserReports : {total}")
    logger.info(f"  Scam Reports (y=1): {scams} ({scams/total*100:.1f}%)")
    logger.info(f"  Legitimate (y=0)  : {legit} ({legit/total*100:.1f}%)")
    logger.info("=" * 60)

    await db.disconnect()
    logger.info("✅ GNN Data Seed Completed Successfully.")


if __name__ == "__main__":
    asyncio.run(seed_gnn_dataset())
