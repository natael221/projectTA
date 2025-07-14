# Tambahkan setelah inisialisasi app
def get_profile_data():
    role = session.get('role')
    id_rfid = session.get('id_rfid')
    user_data = None
    if role == 'pengguna' and id_rfid:
        # Ambil data tanpa token untuk pengguna (karena token bukan idToken Firebase)
        user_data = db.child('Users').child(id_rfid).get().val() or {}
        user_data['id_rfid'] = id_rfid
    elif role in ['admin', 'petugas']:
        users = db.child('Users').get(token=session['user']).val() or {}
        for k, v in users.items():
            if v.get('role') == role:
                user_data = v.copy()
                user_data['id_rfid'] = k
                break
    if not user_data:
        user_data = {'id_rfid': '-', 'name': '-', 'no_stnk': '-', 'warna_motor': '-', 'tanggal_daftar': '-', 'role': role or '-'}
    return user_data

# ...existing code...

# ...existing code...
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyrebase
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secretkey123'

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

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_user_role(user_token, email=None, id_rfid=None):
    users = db.child("Users").get(token=user_token).val() or {}
    if email:
        for key, val in users.items():
            if val.get("email") == email:
                return val.get("role", "pengguna"), key
    elif id_rfid:
        user = users.get(id_rfid)
        if user:
            return user.get("role", "pengguna"), id_rfid
    return "pengguna", id_rfid or "-"

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_type = request.form.get('login_type', 'admin')
        identifier = request.form['email']
        password = request.form['password']
        if login_type == 'admin':
            # Login admin/petugas/pengguna via email
            try:
                user = auth.sign_in_with_email_and_password(identifier, password)
                session['user'] = user['idToken']
                # Ambil data Users pakai token
                all_users = db.child("Users").get(token=user['idToken']).val() or {}
                role, id_rfid = get_user_role(user['idToken'], email=identifier)
                session['role'] = role
                session['id_rfid'] = id_rfid if role == 'pengguna' else None
                return redirect(url_for('dashboard'))
            except:
                error = "Email atau password salah."
        elif login_type == 'user':
            # Login user via id_rfid/email
            all_users = db.child("Users").get().val() or {}
            is_email = "@" in identifier
            user_data = None
            role = "pengguna"
            id_rfid = None
            if is_email:
                for k, v in all_users.items():
                    if v.get("email") == identifier:
                        user_data = v
                        id_rfid = k
                        role = v.get("role", "pengguna")
                        break
                if not user_data:
                    error = "Email tidak ditemukan."
                elif role != 'pengguna':
                    error = "Email hanya untuk login pengguna."
                else:
                    # Boleh password kosong jika belum diatur
                    if password == "" or password == user_data.get("password", ""):
                        session['user'] = id_rfid + "_token"
                        session['role'] = "pengguna"
                        session['id_rfid'] = id_rfid
                        return redirect(url_for('dashboard'))
                    else:
                        error = "Password salah atau belum diatur."
            else:
                # Login dengan id_rfid
                if identifier in all_users:
                    user_data = all_users[identifier]
                    role = user_data.get("role", "pengguna")
                    if role != "pengguna":
                        error = "ID RFID hanya untuk login pengguna."
                    else:
                        if password == "" or password == user_data.get("password", ""):
                            session['user'] = identifier + "_token"
                            session['role'] = "pengguna"
                            session['id_rfid'] = identifier
                            return redirect(url_for('dashboard'))
                        else:
                            error = "Password salah atau belum diatur."
                else:
                    error = "ID tidak ditemukan."
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session or 'role' not in session:
        return redirect(url_for('login'))

    role = session['role']
    id_rfid = session.get('id_rfid')
    token = session['user']

    # Jika pengguna login RFID (token bukan idToken Firebase), ambil data tanpa token
    if role == "pengguna" and (not token or token.endswith("_token")):
        data = db.child("Data").get().val()
        users = db.child("Users").get().val() or {}
    else:
        data = db.child("Data").get(token=token).val()
        users = db.child("Users").get(token=token).val() or {}
    rows = []

    if data:
        for key, value in data.items():
            if isinstance(value, dict):
                data_id = value.get("idRfid", "-")
                waktu = value.get("Waktu", "-")
                name = users.get(data_id, {}).get("name", "-")
                # Hanya tampilkan log milik user sendiri jika role pengguna
                if role == "pengguna":
                    if data_id != id_rfid:
                        continue
                row = {
                    "id": key,
                    "idRfid": data_id,
                    "name": name,
                    "waktu": waktu,
                    "status": "Masuk" if "masuk" in key.lower() else "Keluar"
                }
                rows.append(row)
        rows.sort(key=lambda x: x['waktu'], reverse=True)

    return render_template('index.html', data=rows, role=role)

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
                "tanggal_daftar": tanggal_daftar,
                "role": "pengguna"
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
    if session['role'] == "pengguna" and session['id_rfid'] != id_rfid:
        return "Tidak diizinkan mengedit data pengguna lain.", 403
    if session.get('role') == 'pengguna':
        user_data = db.child("Users").child(id_rfid).get().val()
    else:
        user_data = db.child("Users").child(id_rfid).get(token=session['user']).val()
    if not user_data:
        return "Pengguna tidak ditemukan", 404
    message = None
    if request.method == 'POST':
        name = request.form.get('name')
        no_stnk = request.form.get('no_stnk')
        warna_motor = request.form.get('warna_motor')
        if name and no_stnk and warna_motor:
            updated_data = {
                "name": name,
                "no_stnk": no_stnk,
                "warna_motor": warna_motor,
                "tanggal_daftar": user_data.get("tanggal_daftar", get_current_time())
            }
            if session.get('role') == 'pengguna':
                db.child("Users").child(id_rfid).update(updated_data)
            else:
                db.child("Users").child(id_rfid).update(updated_data, token=session['user'])
            message = f"Data pengguna {name} berhasil diperbarui."
        else:
            message = "Semua field wajib diisi."
    return render_template("edit.html", user=user_data, id_rfid=id_rfid, message=message)

@app.route('/pengguna')
def pengguna_list():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'pengguna':
        users = db.child("Users").get().val() or {}
    else:
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
    if session.get('role') == 'pengguna':
        data = db.child("DataTerakhir").get().val() or {}
        id_rfid = data.get("idRfid", "-")
        waktu = data.get("Waktu", "-")
        user_info = db.child("Users").child(id_rfid).get().val() or {}
    else:
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
            if session.get('role') == 'pengguna':
                user_info = db.child("Users").child(id_rfid).get().val()
                name = user_info.get("name", "-") if user_info else "-"
                semua_data = db.child("Data").get().val()
            else:
                user_info = db.child("Users").child(id_rfid).get(token=session['user']).val()
                name = user_info.get("name", "-") if user_info else "-"
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

@app.route('/set_password', methods=['GET', 'POST'])
def set_password():
    if 'role' not in session or session['role'] != "pengguna":
        return redirect(url_for('dashboard'))
    message = ""
    if request.method == 'POST':
        password = request.form.get('password')
        if password:
            id_rfid = session['id_rfid']
            # Untuk pengguna, update tanpa token
            if session.get('role') == 'pengguna':
                db.child("Users").child(id_rfid).update({"password": password})
            else:
                db.child("Users").child(id_rfid).update({"password": password}, token=session['user'])
            message = "Password berhasil disimpan."
        else:
            message = "Password tidak boleh kosong."
    return render_template("set_password.html", message=message)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

    

# Profile page with password logic
@app.route('/profile', methods=['GET'])
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_data = get_profile_data()
    # Ambil password jika pengguna
    if session.get('role') == 'pengguna' and user_data.get('id_rfid'):
        user_db = db.child('Users').child(user_data['id_rfid']).get().val() or {}
        user_data['password'] = user_db.get('password')
    return render_template('profile.html', user=user_data)

# Edit password modal POST
@app.route('/edit_password', methods=['POST'])
def edit_password():
    if 'user' not in session or session.get('role') != 'pengguna':
        return redirect(url_for('login'))
    id_rfid = session.get('id_rfid')
    new_password = request.form.get('password')
    if id_rfid and new_password:
        # Untuk pengguna, update tanpa token
        if session.get('role') == 'pengguna':
            db.child('Users').child(id_rfid).update({'password': new_password})
        else:
            db.child('Users').child(id_rfid).update({'password': new_password}, token=session['user'])
    return redirect(url_for('profile'))


if __name__ == '__main__':
    app.run(debug=True)
