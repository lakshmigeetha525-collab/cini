from flask import Flask, render_template, redirect, url_for, request, jsonify, session
import sqlite3
import datetime

app = Flask(__name__)
app.secret_key = 'cine-booker-pangu-ultra-key'

# Updated Location Data with Chennai and Coimbatore
locations_data = {
    "Chennai": {
        "Velachery": {
            "AGS Cinemas": ["Amaran", "Pushpa 2", "Vidaamuyarchi", "Kanguva"],
        },
        "Anna Nagar": {
            "PVR Cinemas": ["Amaran", "Kanguva"]
        }
    },
    "Coimbatore": {
        "RS Puram": {
            "Brookefields PVR": ["Amaran", "Pushpa 2", "Vidaamuyarchi"],
        },
        "Avinashi Road": {
            "Broadway Cinemas": ["Pushpa 2", "Kanguva"]
        }
    }
}

movie_images = {
    "Amaran": "static/images/amaran.jpg",
    "Pushpa 2": "static/images/pushpa2.jpg",
    "Vidaamuyarchi": "static/images/vidamuyarchi.jpg",
    "Kanguva": "static/images/kanguva.jpg"
}

# Database connection
def get_db():
    conn = sqlite3.connect('cinebooker.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Database Initialization
with get_db() as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, movie TEXT, seat_id TEXT, 
                     gender TEXT, date TEXT, time TEXT, theatre TEXT, city TEXT)''')
    conn.commit()

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
    return render_template('home.html', 
                           user_name=session['user_name'], 
                           locations=locations_data, 
                           movie_imgs=movie_images)

@app.route('/booking/<movie_name>')
def booking(movie_name):
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    # Getting details from URL parameters (sent from home.html)
    theatre = request.args.get('theatre', 'Unknown Theatre')
    city = request.args.get('city', 'Unknown City')
    selected_date = request.args.get('date')
    selected_time = request.args.get('time', '10:30 AM')

    if not selected_date:
        d = datetime.date.today()
        selected_date = f"{d.day} {d.strftime('%b')}"

    # Fetch booked seats for this specific show
    booked_seats = {}
    with get_db() as conn:
        rows = conn.execute("""SELECT seat_id, gender FROM bookings 
                               WHERE movie=? AND date=? AND time=? AND theatre=?""", 
                            (movie_name, selected_date, selected_time, theatre)).fetchall()
        for row in rows:
            booked_seats[row['seat_id']] = row['gender']

    return render_template('booking.html', 
                           movie_name=movie_name, 
                           theatre=theatre, 
                           city=city,
                           booked_seats=booked_seats,
                           selected_date=selected_date,
                           selected_time=selected_time)

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    data = request.get_json()
    movie = data.get('movie')
    seats = data.get('seats')
    date = data.get('date')
    time = data.get('time')
    theatre = data.get('theatre', 'N/A')
    city = data.get('city', 'N/A')

    try:
        with get_db() as conn:
            for seat in seats:
                conn.execute("""INSERT INTO bookings (movie, seat_id, gender, date, time, theatre, city) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                             (movie, seat['id'], seat['gender'], date, time, theatre, city))
            conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)