import os
import boto3
from moto import mock_aws
from flask import Flask, render_template, redirect, url_for, request, jsonify, session
import sqlite3
import datetime

# --- AWS MOCK SETUP (Sir's Requirement) ---
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

mock = mock_aws()
mock.start()

app = Flask(__name__)
app.secret_key = 'cine-booker-pangu-ultra-key'

# Sir's DynamoDB Tables Setup
def setup_aws_mock():
    db = boto3.resource('dynamodb', region_name='us-east-1')
    tables = ['Users', 'AdminUsers', 'Projects', 'Enrollments']
    for table_name in tables:
        key = 'username' if table_name != 'Projects' else 'id'
        db.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': key, 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': key, 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
    print(">>> Moto AWS Tables Ready!")

# --- YOUR ORIGINAL DATA ---
locations_data = {
    "Chennai": {
        "Velachery": { "AGS Cinemas": ["Amaran", "Pushpa 2", "Vidaamuyarchi", "Kanguva"] },
        "Anna Nagar": { "PVR Cinemas": ["Amaran", "Kanguva"] }
    },
    "Coimbatore": {
        "RS Puram": { "Brookefields PVR": ["Amaran", "Pushpa 2", "Vidaamuyarchi"] },
        "Avinashi Road": { "Broadway Cinemas": ["Pushpa 2", "Kanguva"] }
    }
}

movie_images = {
    "Amaran": "static/images/amaran.jpg",
    "Pushpa 2": "static/images/pushpa2.jpg",
    "Vidaamuyarchi": "static/images/vidamuyarchi.jpg",
    "Kanguva": "static/images/kanguva.jpg"
}

# --- DATABASE LOGIC ---
def get_db():
    conn = sqlite3.connect('cinebooker.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Init DB
with get_db() as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, movie TEXT, seat_id TEXT, gender TEXT, date TEXT, time TEXT, theatre TEXT, city TEXT)')
    conn.commit()

# --- ROUTES ---

@app.route('/')
def index():
    if 'user_name' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", 
                             (data['name'], data['email'], data['password']))
                conn.commit()
            session['user_name'] = data['name']
            return jsonify({"status": "success"})
        except sqlite3.IntegrityError:
            return jsonify({"status": "error", "message": "Email already registered!"})
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    with get_db() as conn:
        user = conn.execute("SELECT name FROM users WHERE email=? AND password=?", 
                            (data['email'], data['password'])).fetchone()
    if user:
        session['user_name'] = user['name']
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid Login!"})

@app.route('/dashboard')
@app.route('/home')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('index'))
    return render_template('home.html', user_name=session['user_name'], locations=locations_data, movie_imgs=movie_images)

@app.route('/booking/<movie_name>')
def booking(movie_name):
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    theatre = request.args.get('theatre', 'Unknown Theatre')
    city = request.args.get('city', 'Unknown City')
    selected_date = request.args.get('date')
    selected_time = request.args.get('time', '10:30 AM')

    # DATE FIX: Date illana default dates anuppurom
    available_dates = ["4 Feb", "5 Feb", "6 Feb"]
    if not selected_date:
        selected_date = available_dates[0]

    # JSON FIX: 'movie_details' and 'theatre_details' variables required by booking.html
    m_details = {
        "name": movie_name,
        "timings": ["10:30 AM", "02:45 PM", "06:15 PM"],
        "available_dates": available_dates
    }

    booked_seats = {}
    with get_db() as conn:
        rows = conn.execute("SELECT seat_id, gender FROM bookings WHERE movie=? AND date=? AND time=? AND theatre=?", 
                            (movie_name, selected_date, selected_time, theatre)).fetchall()
        for row in rows:
            booked_seats[row['seat_id']] = row['gender']

    return render_template('booking.html', 
                           movie_name=movie_name, theatre=theatre, city=city,
                           booked_seats=booked_seats, selected_date=selected_date,
                           selected_time=selected_time, movie_details=m_details,
                           theatre_details={"name": theatre, "total_seats": 50},
                           user_name=session.get('user_name'))

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    data = request.get_json()
    try:
        with get_db() as conn:
            for seat in data.get('seats', []):
                conn.execute("INSERT INTO bookings (movie, seat_id, gender, date, time, theatre, city) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (data.get('movie'), seat['id'], seat['gender'], data.get('date'), data.get('time'), data.get('theatre'), data.get('city')))
            conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    try:
        setup_aws_mock()
        # Port 5001-la run pannuvom, neenga use pannura maari
        app.run(debug=True, port=5001, use_reloader=False)
    finally:
        mock.stop()