# Task Strategy Service

**Versi aktif sudah berpindah ke MySQL/MariaDB. Ikuti [MYSQL.md](MYSQL.md) untuk konfigurasi, menjalankan aplikasi, dan pengujian. Penjelasan PostgreSQL di bawah adalah referensi implementasi lama.**

Contoh refactor backend task harian berbasis Python standar (tanpa dependensi eksternal).

## Database PostgreSQL

Skrip [db/init.sql](db/init.sql) menyiapkan tabel `users`, `tasks`, dan `task_runs`, beserta indeks dan fungsi `claim_task_run`. Jalankan setelah membuat database PostgreSQL 14:

```powershell
psql -U NAMA_USER -d NAMA_DATABASE -f db/init.sql
```

Fungsi `claim_task_run(task_id, scheduled_date)` merupakan titik aman yang perlu dipanggil worker sebelum menjalankan action: ia mengunci user, memeriksa kuota, mencegah run ganda, dan mencatat penolakan kuota secara atomik.

### Menghubungkan aplikasi

1. Instal driver: `python -m pip install -r requirements.txt`.
2. Isi `.env` berdasarkan `.env.example` dengan kredensial lokal; file tersebut tidak ikut Git. Aplikasi membaca file ini otomatis; environment variable yang sudah tersedia tetap diprioritaskan.
3. Gunakan Python 3.11 dalam `.venv` untuk integrasi PostgreSQL. Periksa koneksi tanpa menjalankan task dengan `.\.venv\Scripts\python.exe check_database.py`.
4. Sebagai alternatif `.env`, atur variabel lingkungan sebelum menjalankan worker:

```powershell
$env:DATABASE_URL = "postgresql://USERNAME:PASSWORD@localhost:5432/task_strattegy"
python main.py
```

Jika `DATABASE_URL` tersedia, `main.py` memakai scheduler PostgreSQL. Jika tidak, ia memakai contoh in-memory untuk demo.

## Struktur

- `task_service/models.py`: model `Task` dan hasil eksekusi; `Task.from_dict()` menerima konfigurasi dictionary.
- `task_service/users.py`: kuota per pengguna per hari, aman terhadap akses thread dalam satu proses.
- `task_service/actions.py`: strategi aksi yang dapat diperluas.
- `task_service/executor.py`: validasi kuota, dispatch aksi, dan logging/error handling.
- `task_service/scheduler.py`: polling task due dan deduplikasi eksekusi per hari.

Jalankan contoh dengan `python main.py`, lalu tes dengan `python -m unittest discover -v`. Tidak ada dependensi eksternal dan kode kompatibel dengan Python 3.6+.

## Catatan desain

`can_execute` mengonsumsi kuota sebelum aksi dimulai. Ini membuat pembatasan tegas terhadap percobaan eksekusi, termasuk task yang gagal. Jika kebutuhan bisnisnya adalah kuota hanya untuk eksekusi sukses, ubah menjadi reservasi/finalisasi atomik di repository transaksional.

Untuk skala puluhan ribu task per hari: simpan pengguna, task, dan riwayat run pada database; indeks waktu/status task; gunakan scheduler terdistribusi yang menerbitkan job ke antrean; jalankan worker idempoten; dan lakukan kuota atomik di Redis atau database. Logging sebaiknya dikirim sebagai log terstruktur ke observability platform.
