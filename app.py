from flask import Flask, render_template, redirect, url_for, request, jsonify, send_file
import sqlite3
from PIL import Image, ImageDraw, ImageFont 
import io

app = Flask(__name__)

# --- DATA (Your Original Logic) ---
locations_data = {
    "Chennai": {
        "Velachery": {
            "AGS Cinemas": ["Amaran", "Pushpa 2", "Vidaamuyarchi", "Kanguva"],
            "PVR Grand Mall": ["Greatest of All Time", "Amaran", "Leo", "Jailer"]
        }
    },
    "Coimbatore": {
        "Gandhipuram": {
            "KG Cinemas": ["Pushpa 2", "Leo", "Vikram", "Kanguva"],
            "Cinepolis": ["Amaran", "Jailer", "Baahubali", "Vidaamuyarchi"]
        }
    }
}

movie_images = {
    "Amaran": "static/images/amaran.jpg", "Pushpa 2": "static/images/pushpa2.jpg",
    "Vidaamuyarchi": "static/images/vidamuyarchi.jpg", "Kanguva": "static/images/kanguva.jpg",
    "Greatest of All Time": "static/images/goat.jpg", "Leo": "static/images/leo.jpg",
    "Jailer": "static/images/jailer.jpg", "Baahubali": "static/images/baahubali.jpg",
    "Vikram": "static/images/vikram.jpg"
}

def init_db():
    conn = sqlite3.connect('cinebooker.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS bookings
                       (movie_name TEXT, seat_id TEXT, gender TEXT,
                        show_date TEXT, show_time TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', locations=locations_data, movie_imgs=movie_images)

@app.route('/booking/<movie_name>')
def booking(movie_name):
    dist = request.args.get('dist', 'N/A')
    city = request.args.get('city', 'N/A')
    theatre = request.args.get('theatre', 'N/A')
    selected_date = request.args.get('date', 'Today')
    selected_time = request.args.get('time', '10:30 AM')
    
    conn = sqlite3.connect('cinebooker.db')
    cursor = conn.cursor()
    cursor.execute("""SELECT seat_id, gender FROM bookings
                       WHERE movie_name=? AND show_date=? AND show_time=?""",
                    (movie_name, selected_date, selected_time))
    booked_data = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    
    return render_template('booking.html',
                            movie_name=movie_name, booked_seats=booked_data,
                            dist=dist, city=city, theatre=theatre,
                            selected_date=selected_date, selected_time=selected_time)

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    data = request.json
    movie = data.get('movie')
    seats = data.get('seats')
    s_date = data.get('date')
    s_time = data.get('time')
    
    conn = sqlite3.connect('cinebooker.db')
    cursor = conn.cursor()
    for s in seats:
        cursor.execute("INSERT INTO bookings VALUES (?, ?, ?, ?, ?)",
                        (movie, s['id'], s['gender'], s_date, s_time))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/download_ticket_direct/<tid>')
def download_ticket_direct(tid):
    date = request.args.get('date', 'N/A')
    time = request.args.get('time', 'N/A')
    seats = request.args.get('seats', 'N/A')
    movie = request.args.get('movie', 'MOVIE')
    theatre = request.args.get('theatre', 'Theatre')
    
    img = Image.new('RGB', (500, 750), color='#ffffff')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 500, 100], fill="#e50914")
    draw.text((160, 40), "BOOKING CONFIRMED", fill="white")
    
    y = 150
    details = [
        (f"ID: {tid}", "black"), (f"MOVIE: {movie}", "black"),
        (f"THEATRE: {theatre}", "black"), (f"DATE: {date}", "red"),
        (f"TIME: {time}", "red"), (f"SEATS: {seats}", "black")
    ]
    for text, color in details:
        draw.text((50, y), text, fill=color)
        y += 70
        
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png', as_attachment=True, download_name=f'Ticket_{tid}.png')

if __name__ == '__main__':
    app.run(debug=True)