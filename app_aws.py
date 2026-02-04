from flask import Flask, render_template, redirect, url_for, request, jsonify, session
import os
import boto3
import datetime
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cine-booker-pangu-ultra-key')

# 1. AWS CONFIGURATION
REGION = 'us-east-1'
dynamodb = boto3.resource('dynamodb', region_name=REGION)

# DynamoDB Tables (Make sure these names match your AWS Console)
users_table = dynamodb.Table('CineUsers')
bookings_table = dynamodb.Table('CineBookings')

# 2. DATA (Static data stays as it is)
locations_data = {
    "Chennai": {
        "Velachery": {"AGS Cinemas": ["Amaran", "Pushpa 2", "Vidaamuyarchi", "Kanguva"]},
        "Anna Nagar": {"PVR Cinemas": ["Amaran", "Kanguva"]}
    },
    "Coimbatore": {
        "RS Puram": {"Brookefields PVR": ["Amaran", "Pushpa 2", "Vidaamuyarchi"]},
        "Avinashi Road": {"Broadway Cinemas": ["Pushpa 2", "Kanguva"]}
    }
}

movie_images = {
    "Amaran": "static/images/amaran.jpg",
    "Pushpa 2": "static/images/pushpa2.jpg",
    "Vidaamuyarchi": "static/images/vidamuyarchi.jpg",
    "Kanguva": "static/images/kanguva.jpg"
}

# 3. ROUTES
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
            # DynamoDB Check if user exists
            res = users_table.get_item(Key={'email': data['email']})
            if 'Item' in res:
                return jsonify({"status": "error", "message": "Email already registered!"})
            
            # Insert new user
            users_table.put_item(Item={
                'email': data['email'],
                'name': data['name'],
                'password': data['password']
            })
            session['user_name'] = data['name']
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    try:
        res = users_table.get_item(Key={'email': data['email']})
        if 'Item' in res and res['Item']['password'] == data['password']:
            session['user_name'] = res['Item']['name']
            return jsonify({"status": "success"})
    except Exception:
        pass
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
    
    theatre = request.args.get('theatre', 'Unknown Theatre')
    city = request.args.get('city', 'Unknown City')
    selected_time = request.args.get('time', '10:30 AM')
    
    # Date logic
    d = datetime.date.today()
    selected_date = request.args.get('date', f"{d.day} {d.strftime('%b')}")

    # Fetch booked seats from DynamoDB
    booked_seats = {}
    try:
        # Scanning bookings (For small apps scan is okay, for large apps use GSI)
        response = bookings_table.scan(
            FilterExpression=Attr('movie').eq(movie_name) & 
                             Attr('date').eq(selected_date) & 
                             Attr('time').eq(selected_time) & 
                             Attr('theatre').eq(theatre)
        )
        for item in response.get('Items', []):
            booked_seats[item['seat_id']] = item['gender']
    except Exception as e:
        print(f"Error fetching seats: {e}")

    return render_template('booking.html', 
                           movie_name=movie_name, theatre=theatre, city=city,
                           booked_seats=booked_seats, selected_date=selected_date,
                           selected_time=selected_time)

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    data = request.get_json()
    try:
        # Batch writing to DynamoDB for multiple seats
        with bookings_table.batch_writer() as batch:
            for seat in data.get('seats', []):
                booking_id = f"{data.get('movie')}_{seat['id']}_{data.get('date')}_{data.get('time')}"
                batch.put_item(Item={
                    'booking_id': booking_id, # Partition Key
                    'movie': data.get('movie'),
                    'seat_id': seat['id'],
                    'gender': seat['gender'],
                    'date': data.get('date'),
                    'time': data.get('time'),
                    'theatre': data.get('theatre'),
                    'city': data.get('city')
                })
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Standard AWS Port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)