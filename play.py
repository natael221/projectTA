from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyrebase

app = Flask(__name__)
app.secret_key = 'secretkey123'  # Ganti dengan string acak yang aman

from datetime import datetime

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Konfigurasi Firebase
firebase_config = {
    "apiKey": "AIzaSyBUAkLsqXNkZHctk-lfklxZKPSAqub76oo",
    "authDomain": "esp8226-sp.firebaseapp.com",
    "databaseURL": "https://esp8226-sp-default-rtdb.asia-southeast1.firebasedatabase.app",
    "storageBucket": "esp8226-sp.appspot.com"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

# Halaman login
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user['idToken']
            return redirect(url_for('dashboard'))
        except:
            error = "Login gagal. Periksa email dan password."
    return render_template('login.html', error=error)

# Halaman dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = db.child("Data").get(token=session['user']).val()
    users = db.child("Users").get(token=session['user']).val() or {}
    rows = []

    if data:
        for key, value in data.items():
            if isinstance(value, dict):
                id_rfid = value.get("idRfid", "-")
                name = users.get(id_rfid, {}).get("name", "-")
                row = {
                    "id": key,
                    "idRfid": id_rfid,
                    "name": name,
                    "waktu": value.get("Waktu", "-")
                }
                rows.append(row)
        rows.sort(key=lambda x: x['waktu'], reverse=True)

    return render_template('index.html', data=rows)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' not in session:
        return redirect(url_for('login'))

    message = None
    if request.method == 'POST':
        id_rfid = request.form.get('id_rfid')
        name = request.form.get('name')
        no_stnk = request.form.get('no_stnk')
        warna_motor = request.form.get('warna_motor')
        tanggal_daftar = get_current_time()

        if id_rfid and name:
            data = {
                "name": name,
                "no_stnk": no_stnk,
                "warna_motor": warna_motor,
                "tanggal_daftar": tanggal_daftar
            }
            db.child("Users").child(id_rfid).set(data, token=session['user'])
            message = f"Pengguna {name} berhasil didaftarkan."
        else:
            message = "Semua field wajib diisi."

    return render_template('register.html', message=message)
@app.route('/edit/<id_rfid>', methods=['GET', 'POST'])
def edit_user(id_rfid):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_data = db.child("Users").child(id_rfid).get(token=session['user']).val()

    if not user_data:
        return "Pengguna tidak ditemukan", 404

    message = None
    if request.method == 'POST':
        name = request.form.get('name')
        no_stnk = request.form.get('no_stnk')
        warna_motor = request.form.get('warna_motor')

        updated_data = {
            "name": name,
            "no_stnk": no_stnk,
            "warna_motor": warna_motor,
            "tanggal_daftar": user_data.get("tanggal_daftar", get_current_time())
        }

        db.child("Users").child(id_rfid).update(updated_data, token=session['user'])
        message = f"Data pengguna {name} berhasil diperbarui."

    return render_template("edit.html", user=user_data, id_rfid=id_rfid, message=message)
@app.route('/pengguna')
def pengguna_list():
    if 'user' not in session:
        return redirect(url_for('login'))

    users = db.child("Users").get(token=session['user']).val() or {}

    data = []
    for id_rfid, info in users.items():
        row = {
            "id_rfid": id_rfid,
            "name": info.get("name", "-"),
            "no_stnk": info.get("no_stnk", "-"),
            "warna_motor": info.get("warna_motor", "-"),
            "tanggal_daftar": info.get("tanggal_daftar", "-")
        }
        data.append(row)

    return render_template("pengguna.html", users=data)
@app.route('/live')
def live_view():
    return render_template('live.html')

@app.route('/get_latest_rfid')
def get_latest_rfid():
    if 'user' not in session:
        return jsonify({"idRfid": "-", "waktu": "-", "name": "-", "no_stnk": "-"})

    data = db.child("DataTerakhir").get(token=session['user']).val() or {}
    id_rfid = data.get("idRfid", "-")
    waktu = data.get("Waktu", "-")

    user_info = db.child("Users").child(id_rfid).get(token=session['user']).val() or {}

    return jsonify({
        "idRfid": id_rfid,
        "waktu": waktu,
        "name": user_info.get("name", "-"),
        "no_stnk": user_info.get("no_stnk", "-")
    })

@app.route('/cari', methods=['GET', 'POST'])
def cari_data():
    if 'user' not in session:
        return redirect(url_for('login'))

    hasil = []
    id_rfid = ""
    name = "-"

    if request.method == 'POST':
        id_rfid = request.form.get('id_rfid')
        if id_rfid:
            # Ambil nama pengguna
            user_info = db.child("Users").child(id_rfid).get(token=session['user']).val()
            name = user_info.get("name", "-") if user_info else "-"

            # Ambil semua histori data
            semua_data = db.child("Data").get(token=session['user']).val()
            if semua_data:
                for key, value in semua_data.items():
                    if isinstance(value, dict) and value.get("idRfid") == id_rfid:
                        hasil.append({
                            "id": key,
                            "idRfid": value.get("idRfid", "-"),
                            "waktu": value.get("Waktu", "-"),
                            "name": name
                        })
            hasil.sort(key=lambda x: x['waktu'], reverse=True)

        return render_template("hasil.html", data=hasil, id_rfid=id_rfid)

    return render_template("login_pengguna.html")


# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
