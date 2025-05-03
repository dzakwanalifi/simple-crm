import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import re # Import modul regex
from supabase import create_client, Client

load_dotenv() # Memuat variabel dari .env

app = Flask(__name__)
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
    if not email: # Boleh kosong jika email tidak wajib
        return True
    # Pola regex sederhana untuk format email dasar
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.route('/')
def index():
    if not supabase:
        flash("Koneksi ke database gagal.", "error")
        return render_template('index.html', pelanggan_list=[]) # Kirim list kosong jika gagal

    try:
        # Ambil semua data dari tabel 'pelanggan', urutkan berdasarkan id
        response = supabase.table('pelanggan').select("*").order('id').execute()
        print("Data diterima dari Supabase:", response.data) # Debugging

        # Cek jika ada data
        if response.data:
            pelanggan = response.data
        else:
            pelanggan = []
            print("Tidak ada data pelanggan.") # Debugging

    except Exception as e:
        print(f"Error saat mengambil data: {e}") # Debugging
        flash(f"Terjadi error saat mengambil data: {e}", "error")
        pelanggan = []

    # Kirim data pelanggan ke template index.html
    return render_template('index.html', pelanggan_list=pelanggan)

# Route untuk menampilkan form tambah (GET) dan memproses form (POST)
@app.route('/tambah', methods=['GET', 'POST']) # Tambahkan 'POST' ke methods
def tambah():
    if request.method == 'POST':
        # Proses data dari form jika method adalah POST
        if not supabase:
            flash("Koneksi ke database gagal.", "error")
            return redirect(url_for('index')) # Kembali ke index jika DB down

        nama = request.form.get('nama')
        email = request.form.get('email')
        telepon = request.form.get('telepon')

        # --- VALIDASI ---
        error = False # Flag untuk menandai jika ada error
        if not nama:
            flash('Nama wajib diisi!', 'error')
            error = True
        if email and not is_valid_email(email): # Cek jika email diisi dan formatnya salah
            flash('Format email tidak valid!', 'error')
            error = True
        # (Tambahkan validasi lain jika perlu, misal panjang telepon)

        if error:
            # Kembalikan ke form dengan pesan error
            # Di pengembangan lanjut, kirim kembali input user ke template
            return render_template('tambah.html')

        # --- Proses Insert (jika tidak ada error validasi) ---
        try:
            # Data yang akan dimasukkan (sesuai nama kolom di Supabase)
            data_insert = {
                'nama': nama,
                'email': email,
                'telepon': telepon
                # 'tanggal_registrasi' akan otomatis diisi oleh Supabase (default now())
            }
            # Eksekusi perintah insert
            response = supabase.table('pelanggan').insert(data_insert).execute()

            # Cek hasil response (opsional tapi bagus untuk debugging)
            # Supabase API V2 (supabase-py >= 2.0) biasanya tidak error jika data ada,
            # tapi kita bisa cek apakah ada data yang dikembalikan atau tidak
            if response.data:
                print("Data berhasil dimasukkan:", response.data) # Debugging
                flash('Pelanggan baru berhasil ditambahkan!', 'success')
            else:
                 # Ini mungkin terjadi jika ada policy RLS atau trigger yg mencegah insert
                 # atau jika API tidak mengembalikan data by default
                 # Untuk insert standar tanpa RLS aktif, ini seharusnya sukses
                 print("Insert dieksekusi, tapi tidak ada data dikembalikan oleh API. Anggap sukses.") # Debugging
                 flash('Pelanggan baru berhasil ditambahkan! (No data returned)', 'success')


            # Redirect ke halaman utama setelah berhasil
            return redirect(url_for('index'))

        except Exception as e:
            # Tangani error jika terjadi (misal: email unique constraint violation)
            error_message = str(e)
            print(f"Error saat insert data: {error_message}") # Debugging
            # Cek apakah error karena email duplikat (pesan error bisa bervariasi)
            if 'duplicate key value violates unique constraint' in error_message and 'pelanggan_email_key' in error_message:
                 flash('Gagal menambahkan pelanggan: Email sudah terdaftar.', 'error')
            else:
                 flash(f'Gagal menambahkan pelanggan: {error_message}', 'error')
            # Kembalikan ke form tambah lagi jika gagal insert
            return render_template('tambah.html')


    # Jika method adalah GET, tampilkan form tambah
    return render_template('tambah.html')

# (Di bawah fungsi tambah() atau di tempat lain yang logis)

# Route untuk menampilkan form edit (GET) dan memproses update (POST)
@app.route('/edit/<int:id>', methods=['GET', 'POST']) # <int:id> menangkap ID dari URL
def edit(id):
    if not supabase:
        flash("Koneksi ke database gagal.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # --- Proses Update Data (Method POST) ---
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

        if error:
            # Jika validasi gagal, tampilkan lagi form edit DENGAN DATA LAMA
            try:
                response = supabase.table('pelanggan').select("*").eq('id', id).single().execute()
                if response.data:
                    # Tetap tampilkan data lama saat validasi gagal
                    return render_template('edit.html', pelanggan=response.data)
                else:
                     flash('Data pelanggan tidak ditemukan untuk diedit ulang.', 'error')
                     return redirect(url_for('index'))
            except Exception as e:
                flash(f'Error saat mengambil data untuk edit ulang: {e}', 'error')
                return redirect(url_for('index'))

        # --- Proses Update (jika tidak ada error validasi) ---
        try:
            data_update = {
                'nama': nama_baru,
                'email': email_baru,
                'telepon': telepon_baru
                # 'tanggal_registrasi' tidak perlu diupdate
            }
            # Eksekusi perintah update berdasarkan id
            response = supabase.table('pelanggan').update(data_update).eq('id', id).execute()

            # Cek hasil (Mirip dengan insert)
            # API update Supabase biasanya mengembalikan data yang diupdate
            if response.data:
                print("Data berhasil diupdate:", response.data) # Debugging
                flash('Data pelanggan berhasil diperbarui!', 'success')
            else:
                # Ini bisa terjadi jika RLS mencegah update atau ID tidak ditemukan
                # (meskipun kita ambil datanya dulu di GET)
                print("Update dieksekusi, tapi tidak ada data dikembalikan. Cek RLS atau ID.") # Debugging
                flash('Data pelanggan berhasil diperbarui! (No data returned)', 'warning')

            # Redirect ke halaman utama setelah berhasil
            return redirect(url_for('index'))

        except Exception as e:
            # Tangani error (misal: email unique constraint violation lagi)
            error_message = str(e)
            print(f"Error saat update data: {error_message}") # Debugging
            if 'duplicate key value violates unique constraint' in error_message and 'pelanggan_email_key' in error_message:
                flash('Gagal memperbarui: Email sudah digunakan oleh pelanggan lain.', 'error')
            else:
                flash(f'Gagal memperbarui data: {error_message}', 'error')

            # Kembalikan ke form edit dengan data LAMA jika gagal update
            # (karena data baru gagal disimpan)
            try:
                response_err = supabase.table('pelanggan').select("*").eq('id', id).single().execute()
                if response_err.data:
                     return render_template('edit.html', pelanggan=response_err.data)
                else:
                     # Handle jika data tiba-tiba hilang saat user submit
                     flash('Data pelanggan asli tidak ditemukan saat terjadi error update.', 'error')
                     return redirect(url_for('index'))
            except Exception as e_inner:
                 flash(f'Error saat mengambil data asli setelah error update: {e_inner}', 'error')
                 return redirect(url_for('index'))


    else: # request.method == 'GET'
        # --- Tampilkan Form dengan Data Lama (Method GET) ---
        try:
            # Ambil data pelanggan spesifik berdasarkan id dari URL
            response = supabase.table('pelanggan').select("*").eq('id', id).single().execute()
             # .eq('id', id) : filter where id = <nilai_id>
             # .single() : ambil hanya satu baris hasil (jika tidak ada atau >1 akan error/beda)

            if response.data:
                pelanggan_data = response.data
                # Kirim data pelanggan ini ke template edit.html
                return render_template('edit.html', pelanggan=pelanggan_data)
            else:
                # Jika ID tidak ditemukan di database
                flash('Data pelanggan tidak ditemukan.', 'error')
                return redirect(url_for('index')) # Kembali ke halaman utama

        except Exception as e:
            print(f"Error saat mengambil data untuk diedit: {e}") # Debugging
            flash(f"Terjadi error saat mengambil data: {e}", "error")
            return redirect(url_for('index'))
        
# (Di bawah fungsi edit() atau di tempat lain yang logis)

# Route untuk menghapus pelanggan (hanya handle POST)
@app.route('/hapus/<int:id>', methods=['POST']) # Hanya menerima POST
def hapus(id):
    if not supabase:
        flash("Koneksi ke database gagal.", "error")
        return redirect(url_for('index'))

    try:
        # Eksekusi perintah delete berdasarkan id
        response = supabase.table('pelanggan').delete().eq('id', id).execute()

        # Cek hasil (Delete biasanya mengembalikan data yg dihapus jika berhasil)
        if response.data:
            print("Data berhasil dihapus:", response.data) # Debugging
            flash('Pelanggan berhasil dihapus!', 'success')
        else:
            # Ini bisa terjadi jika ID tidak ditemukan saat delete (misal user buka 2 tab)
            # atau jika ada RLS/constraint yang mencegah delete
            print("Delete dieksekusi, tapi tidak ada data dikembalikan. Mungkin ID tidak ditemukan?") # Debugging
            flash('Pelanggan tidak ditemukan atau gagal dihapus.', 'warning')

    except Exception as e:
        print(f"Error saat hapus data: {e}") # Debugging
        flash(f'Gagal menghapus pelanggan: {e}', 'error')

    # Selalu redirect kembali ke halaman utama setelah mencoba hapus
    return redirect(url_for('index'))

# Menjalankan server development Flask
if __name__ == '__main__':
    # debug=True akan otomatis me-reload server jika ada perubahan kode
    # dan menampilkan halaman error yang lebih detail
    app.run(host='0.0.0.0', port=5000, debug=True)