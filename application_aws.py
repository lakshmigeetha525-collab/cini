from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import boto3
import uuid
import datetime
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

application = Flask(__name__)
# It is better to use a random string for the secret key in production
application.secret_key = os.environ.get('SECRET_KEY', 'cine-booker-pangu-ultra-key')

# --- 1. AWS CONFIGURATION ---
REGION = 'us-east-1' 

# For local testing, you can pass keys here. 
# For Beanstalk/EC2, leave it as is and use IAM Roles.
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

users_table = dynamodb.Table('CineUsers')
bookings_table = dynamodb.Table('CineBookings')
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:535002883963:cine_booker' 

def send_notification(subject, message):
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    except Exception as e:
        print(f"SNS Error: {e}")

# --- 2. ROUTES ---

@application.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@application.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            res = users_table.get_item(Key={'email': email})
            if 'Item' in res:
                flash("Email already registered!")
                return redirect(url_for('register'))
            
            users_table.put_item(Item={
                'email': email, 'name': name, 'password': password
            })
            
            session['username'] = name
            session['email'] = email
            send_notification("New Signup", f"User {name} joined.")
            return redirect(url_for('dashboard'))
            
        except ClientError as e:
            # This captures AWS credential/permission errors specifically
            flash(f"AWS Error: {e.response['Error']['Message']}")
            return redirect(url_for('register'))
        except Exception as e:
            flash(f"Registration Error: {str(e)}")
            return redirect(url_for('register'))
            
    return render_template('register.html')

@application.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            res = users_table.get_item(Key={'email': email})
            if 'Item' in res and res['Item']['password'] == password:
                session['username'] = res['Item']['name']
                session['email'] = email
                send_notification("User Login", f"User {session['username']} logged in.")
            else:
                flash("Invalid Credentials!")
        except Exception as e:
            flash(f"Login Error: {str(e)}")
            
    return render_template('login.html')

@application.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    # Replace with your actual home.html
    return render_template('home.html', username=session['username'])

@application.route('/booking/<movie_name>')
def booking(movie_name):
    if 'username' not in session:
        return redirect(url_for('index'))
    
    theatre = request.args.get('theatre', 'Unknown Theatre')
    city = request.args.get('city', 'Unknown City')
    selected_time = request.args.get('time', '10:30 AM')
    
    d = datetime.date.today()
    selected_date = request.args.get('date', f"{d.day} {d.strftime('%b')}")

    booked_seats = {}
    try:
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

@application.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Session expired"})
        
    data = request.get_json()
    try:
        seats_list = []
        # Sir's Logic: UUID and Individual Put Item
        for seat in data.get('seats', []):
            booking_id = str(uuid.uuid4()) # Unique ID for each seat
            bookings_table.put_item(Item={
                'booking_id': booking_id,
                'user_email': session['email'],
                'movie': data.get('movie'),
                'seat_id': seat['id'],
                'gender': seat['gender'],
                'date': data.get('date'),
                'time': data.get('time'),
                'theatre': data.get('theatre'),
                'city': data.get('city')
            })
            seats_list.append(seat['id'])
            
        # Notify via SNS
        ticket_info = f"Movie: {data.get('movie')}\nTheatre: {data.get('theatre')}\nSeats: {', '.join(seats_list)}"
        send_notification("Booking Confirmed!", f"User {session['username']} booked tickets.\n{ticket_info}")
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@application.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5000, debug=True)
