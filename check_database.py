"""Periksa koneksi tanpa menjalankan task atau mengubah data database."""

import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from task_service.mysql import MySQLConnectionFactory


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env.mysql", override=False)
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    database_url = os.getenv("MYSQL_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not database_url or "USERNAME:PASSWORD" in database_url:
        print("Isi MYSQL_DATABASE_URL di .env.mysql dengan kredensial MySQL Anda.")
        return 1
    connection = None
    try:
        with MySQLConnectionFactory(database_url).transaction() as db:
            with db.cursor() as cursor:
                cursor.execute('SELECT DATABASE() AS db, CURRENT_USER() AS user, VERSION() AS version')
                print('Terhubung: database={db}, user={user}, versi={version}'.format(**cursor.fetchone()))
                cursor.execute('SHOW TABLES')
                tables = {next(iter(row.values())) for row in cursor.fetchall()}
                missing = {'users', 'tasks', 'task_runs'} - tables
                if missing:
                    print('Tabel belum tersedia: ' + ', '.join(sorted(missing)))
                    return 1
                print('Ketiga tabel tersedia.')
        return 0
    except pymysql.MySQLError as error:
        # Jangan mencetak DSN atau pesan exception yang berpotensi berisi kredensial.
        code = error.args[0] if error.args else 'unknown'
        reasons = {1045: 'Username/password ditolak.', 1049: 'Database belum dibuat; jalankan db/mysql_init.sql.',
                   2003: 'Server tidak terjangkau; nyalakan MySQL dan periksa host/port.'}
        print('Koneksi gagal ({}): {}'.format(code, reasons.get(code, 'Periksa konfigurasi MySQL.')))
        return 1
    except ValueError:
        print('Format MYSQL_DATABASE_URL tidak valid; gunakan mysql://USER:PASSWORD@HOST:3306/task_strattegy')
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
