# Menjalankan versi MySQL / MariaDB

Gunakan Python 3.11 di `.venv`. Entry point sekarang memakai MySQL.

1. Nyalakan MySQL di XAMPP.
2. Bila database belum dibuat, jalankan `db/mysql_init.sql` melalui phpMyAdmin.
3. Sesuaikan `.env.mysql` (otomatis dibaca):

```dotenv
MYSQL_DATABASE_URL=mysql://root@localhost:3306/task_strattegy
```

Contoh di atas untuk akun lokal tanpa password. Jika memakai password:
`mysql://USERNAME:PASSWORD@localhost:3306/task_strattegy`. URL-encode karakter khusus.
Environment variable yang sudah ada diprioritaskan atas file. Gunakan akun aplikasi
terbatas untuk deployment; root tanpa password hanya konfigurasi uji lokal.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_database.py
.\.venv\Scripts\python.exe main.py
```

`check_database.py` hanya membaca koneksi dan tabel. `main.py` menjalankan satu
putaran task due; sync/backup/delete masih simulasi. Jadwal menggunakan WIB.

```powershell
$env:TEST_MYSQL = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tes integrasi membuat baris ber-ID unik dan membersihkan hanya data tes tersebut.
Klaim mengunci user dan langsung menyimpan status running dalam satu transaksi,
sehingga hanya satu pemanggil mendapatkan hak eksekusi. Kuota menghitung percobaan,
termasuk task gagal. Run yang tertinggal ketika worker mati perlu rekonsiliasi manual.
Belum ada API/login, polling kontinu, atau retry otomatis.

Kode PostgreSQL lama disimpan sebagai referensi dan tidak dipakai oleh main.py.
Data PostgreSQL tidak otomatis disalin atau dihapus.
