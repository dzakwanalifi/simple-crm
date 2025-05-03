import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import re
from supabase import create_client, Client

load_dotenv() # Memuat variabel lingkungan dari file .env

app = Flask(__name__)
# Kunci rahasia untuk keamanan sesi Flask, dihasilkan secara acak
app.config['SECRET_KEY'] = os.urandom(24)

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

try:
    supabase: Client = create_client(supabase_url, supabase_key)
    print("Berhasil terhubung ke Supabase.")
except Exception as e:
    print(f"Gagal terhubung ke Supabase: {e}")
    supabase = None

# Fungsi helper untuk validasi email
def is_valid_email(email):
    """Fungsi sederhana untuk validasi format email menggunakan regex."""
    if not email: # Email boleh kosong
        return True
    # Pola regex untuk validasi format email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.route('/')
def index():
    """Menampilkan halaman utama dengan daftar pelanggan."""
    if not supabase:
        flash("Koneksi ke database gagal.", "error")
        return render_template('index.html', pelanggan_list=[])

    try:
        # Ambil semua data dari tabel 'pelanggan', urutkan berdasarkan id
        response = supabase.table('pelanggan').select("*").order('id').execute()
        print("Data diterima dari Supabase:", response.data) # Log data

        if response.data:
            pelanggan = response.data
        else:
            pelanggan = []
            print("Tidak ada data pelanggan.") # Log jika kosong

    except Exception as e:
        print(f"Error saat mengambil data: {e}") # Log error
        flash(f"Terjadi error saat mengambil data: {e}", "error")
        pelanggan = []

    return render_template('index.html', pelanggan_list=pelanggan)

# Route untuk menampilkan form tambah (GET) dan memproses form (POST)
@app.route('/tambah', methods=['GET', 'POST'])
def tambah():
    """Menampilkan form tambah pelanggan (GET) atau memproses penambahan (POST)."""
    if request.method == 'POST':
        if not supabase:
            flash("Koneksi ke database gagal.", "error")
            return redirect(url_for('index'))

        nama = request.form.get('nama')
        email = request.form.get('email')
        telepon = request.form.get('telepon')

        # --- VALIDASI ---
        error = False
        if not nama:
            flash('Nama wajib diisi!', 'error')
            error = True
        if email and not is_valid_email(email):
            flash('Format email tidak valid!', 'error')
            error = True
        # TODO: Tambahkan validasi lain jika perlu (misal format telepon)

        if error:
            # Kembalikan ke form tambah dengan pesan error
            return render_template('tambah.html', nama=nama, email=email, telepon=telepon) # Kirim kembali input

        # --- Proses Insert ---
        try:
            # Data yang akan dimasukkan (sesuai nama kolom di Supabase)
            data_insert = {
                'nama': nama,
                'email': email,
                'telepon': telepon
                # 'tanggal_registrasi' akan otomatis diisi oleh Supabase (default now())
            }
            response = supabase.table('pelanggan').insert(data_insert).execute()

            # Cek hasil response
            if response.data:
                print("Data berhasil dimasukkan:", response.data) # Log sukses
                flash('Pelanggan baru berhasil ditambahkan!', 'success')
            else:
                 # Ini mungkin terjadi jika ada policy RLS atau trigger yg mencegah insert
                 # atau jika API tidak mengembalikan data by default.
                 print("Insert dieksekusi, tapi tidak ada data dikembalikan oleh API. Anggap sukses.") # Log info
                 flash('Pelanggan baru berhasil ditambahkan!', 'success') # Tetap anggap sukses

            return redirect(url_for('index'))

        except Exception as e:
            # Tangani error saat insert (misal: email unique constraint violation)
            error_message = str(e)
            print(f"Error saat insert data: {error_message}") # Log error
            # Cek spesifik error duplikat email
            if 'duplicate key value violates unique constraint' in error_message and 'pelanggan_email_key' in error_message:
                 flash('Gagal menambahkan pelanggan: Email sudah terdaftar.', 'error')
            else:
                 flash(f'Gagal menambahkan pelanggan: Terjadi error.', 'error') # Pesan generik
            # Kembalikan ke form tambah dengan data yang sudah diinput user
            return render_template('tambah.html', nama=nama, email=email, telepon=telepon)

    # Tampilkan form tambah jika method GET
    return render_template('tambah.html')


# Route untuk menampilkan form edit (GET) dan memproses update (POST)
@app.route('/edit/<int:id>', methods=['GET', 'POST']) # <int:id> menangkap ID dari URL
def edit(id):
    """Menampilkan form edit pelanggan (GET) atau memproses update (POST)."""
    if not supabase:
        flash("Koneksi ke database gagal.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # --- Proses Update Data ---
        nama_baru = request.form.get('nama')
        email_baru = request.form.get('email')
        telepon_baru = request.form.get('telepon')

        # --- VALIDASI ---
        error = False
        if not nama_baru:
            flash('Nama wajib diisi!', 'error')
            error = True
        if email_baru and not is_valid_email(email_baru):
            flash('Format email tidak valid!', 'error')
            error = True
        # TODO: Tambahkan validasi lain jika perlu

        if error:
            # Jika validasi gagal, tampilkan lagi form edit DENGAN DATA LAMA (yg gagal disimpan)
            # Kita perlu data lama untuk mengisi form lagi, tapi flash message sudah ada
            # Idealnya, kirim data BARU yg gagal divalidasi kembali ke template
            try:
                # Ambil data asli lagi untuk ditampilkan di form (meski validasi gagal)
                response_orig = supabase.table('pelanggan').select("*").eq('id', id).single().execute()
                if response_orig.data:
                    # Kirim data BARU yang gagal divalidasi ke template
                    pelanggan_gagal_validasi = {'id': id, 'nama': nama_baru, 'email': email_baru, 'telepon': telepon_baru, 'tanggal_registrasi': response_orig.data.get('tanggal_registrasi')}
                    return render_template('edit.html', pelanggan=pelanggan_gagal_validasi)
                else:
                     flash('Data pelanggan asli tidak ditemukan saat validasi gagal.', 'error')
                     return redirect(url_for('index'))
            except Exception as e:
                flash(f'Error saat mengambil data asli setelah validasi gagal: {e}', 'error')
                return redirect(url_for('index'))


        # --- Proses Update ---
        try:
            data_update = {
                'nama': nama_baru,
                'email': email_baru,
                'telepon': telepon_baru
                # 'tanggal_registrasi' tidak perlu diupdate
            }
            response = supabase.table('pelanggan').update(data_update).eq('id', id).execute()

            # API update Supabase biasanya mengembalikan data yang diupdate
            if response.data:
                print("Data berhasil diupdate:", response.data) # Log sukses
                flash('Data pelanggan berhasil diperbarui!', 'success')
            else:
                # Ini bisa terjadi jika RLS mencegah update atau ID tidak ditemukan
                print("Update dieksekusi, tapi tidak ada data dikembalikan. Cek RLS atau ID.") # Log info
                flash('Data pelanggan berhasil diperbarui!', 'warning') # Beri warning jika tidak ada data kembali

            return redirect(url_for('index'))

        except Exception as e:
            # Tangani error saat update (misal: email unique constraint violation)
            error_message = str(e)
            print(f"Error saat update data: {error_message}") # Log error
            if 'duplicate key value violates unique constraint' in error_message and 'pelanggan_email_key' in error_message:
                flash('Gagal memperbarui: Email sudah digunakan oleh pelanggan lain.', 'error')
            else:
                flash(f'Gagal memperbarui data: Terjadi error.', 'error') # Pesan generik

            # Kembalikan ke form edit dengan data LAMA jika gagal update
            try:
                response_err = supabase.table('pelanggan').select("*").eq('id', id).single().execute()
                if response_err.data:
                     # Kirim data LAMA (sebelum coba update) kembali ke form
                     return render_template('edit.html', pelanggan=response_err.data)
                else:
                     # Handle jika data tiba-tiba hilang saat user submit
                     flash('Data pelanggan asli tidak ditemukan saat terjadi error update.', 'error')
                     return redirect(url_for('index'))
            except Exception as e_inner:
                 flash(f'Error saat mengambil data asli setelah error update: {e_inner}', 'error')
                 return redirect(url_for('index'))


    else: # request.method == 'GET'
        # --- Tampilkan Form dengan Data Lama ---
        try:
            # Ambil data pelanggan spesifik berdasarkan id dari URL
            response = supabase.table('pelanggan').select("*").eq('id', id).single().execute()
             # .eq('id', id) : filter where id = <nilai_id>
             # .single() : ambil hanya satu baris hasil (jika tidak ada atau >1 akan error/beda)

            if response.data:
                pelanggan_data = response.data
                return render_template('edit.html', pelanggan=pelanggan_data)
            else:
                flash('Data pelanggan tidak ditemukan.', 'error')
                return redirect(url_for('index'))

        except Exception as e:
            print(f"Error saat mengambil data untuk diedit: {e}") # Log error
            flash(f"Terjadi error saat mengambil data: {e}", "error")
            return redirect(url_for('index'))

# Route untuk menghapus pelanggan (hanya handle POST)
@app.route('/hapus/<int:id>', methods=['POST'])
def hapus(id):
    """Menghapus data pelanggan berdasarkan ID."""
    if not supabase:
        flash("Koneksi ke database gagal.", "error")
        return redirect(url_for('index'))

    try:
        response = supabase.table('pelanggan').delete().eq('id', id).execute()

        # Cek hasil (Delete biasanya mengembalikan data yg dihapus jika berhasil)
        if response.data:
            print("Data berhasil dihapus:", response.data) # Log sukses
            flash('Pelanggan berhasil dihapus!', 'success')
        else:
            # Ini bisa terjadi jika ID tidak ditemukan saat delete atau RLS mencegah
            print("Delete dieksekusi, tapi tidak ada data dikembalikan. Mungkin ID tidak ditemukan?") # Log info
            flash('Pelanggan tidak ditemukan atau gagal dihapus.', 'warning')

    except Exception as e:
        print(f"Error saat hapus data: {e}") # Log error
        flash(f'Gagal menghapus pelanggan: Terjadi error.', 'error') # Pesan generik

    return redirect(url_for('index'))

# Menjalankan server development Flask
if __name__ == '__main__':
    # debug=True akan otomatis me-reload server jika ada perubahan kode
    # dan menampilkan halaman error yang lebih detail saat pengembangan.
    # host='0.0.0.0' membuat server dapat diakses dari luar localhost.
    app.run(host='0.0.0.0', port=5000, debug=True)