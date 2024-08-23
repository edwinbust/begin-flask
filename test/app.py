from flask import render_template
from flask import Flask
from flask import request
from flask import jsonify
import mariadb
from flask_mail import Mail, Message
import pyotp
import redis
import hashlib
import base64
import os
from datetime import datetime
from datetime import timedelta

app = Flask(__name__)

# Configuración de MariaDB
app.config['MARIADB_HOST'] = 'localhost'
app.config['MARIADB_USER'] = 'root'
app.config['MARIADB_PASSWORD'] = 'AxmE1mdb'
app.config['MARIADB_DB'] = 'beginflask'

# Conexión a la base de datos
def get_db_connection():
    try:
        conn = mariadb.connect(
            host=app.config['MARIADB_HOST'],
            user=app.config['MARIADB_USER'],
            password=app.config['MARIADB_PASSWORD'],
            database=app.config['MARIADB_DB']
        )
        return conn
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return None

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'ewb2021@gmail.com'
app.config['MAIL_PASSWORD'] = 'unddouviubiudaxd'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# Configuración de Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Generación de OTP basado en tiempo
def generate_otp(secret):
    totp = pyotp.TOTP(secret, interval=300)
    return totp.now()

@app.route('/request-otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    email = data['email']

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if user:
        user_id = user[0]
       # secret = hashlib.sha256(os.urandom(32)).hexdigest()
        secret = '234567abcdefg'
        otp = generate_otp(secret)

        # Almacenar OTP en Redis
        redis_client.setex(f'otp:{user_id}', timedelta(minutes=5), otp)

        # Enviar OTP por correo
        msg = Message('Your OTP Code', sender='noreply@example.com', recipients=[email])
        msg.body = f'Your OTP code is {otp}'
        mail.send(msg)

        cur.close()
        conn.close()

        return jsonify({'success': True})
    else:
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data['email']
    otp = data['otp']

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if user:
        user_id = user[0]
        stored_otp = redis_client.get(f'otp:{user_id}')

        if stored_otp and stored_otp.decode() == otp:
            cur.close()
            conn.close()
            return jsonify({'success': True})
        else:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 401
    else:
        cur.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
