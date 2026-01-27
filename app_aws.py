from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import boto3
import uuid
from werkzeug.utils import secure_filename
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# --- AWS Configuration (Teacher's Platform Setup) ---
REGION = 'us-east-1' 
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

# DynamoDB Tables (Sir's suggested tables)
users_table = dynamodb.Table('Users')
admin_users_table = dynamodb.Table('AdminUsers')
projects_table = dynamodb.Table('Projects')
enrollments_table = dynamodb.Table('Enrollments')

# SNS Topic ARN 
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:604665149129:aws_capstone_topic' 

def send_notification(subject, message):
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    except ClientError as e:
        print(f"Error sending notification: {e}")

# --- Admin/Platform Logic (Sir's Original Code) ---
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    users = users_table.scan().get('Items', [])
    projects = projects_table.scan().get('Items', [])
    enrollments = enrollments_table.scan().get('Items', [])
    
    enrollments_dict = {item['username']: item['project_ids'] for item in enrollments}
    users_dict = {u['username']: u['password'] for u in users}

    return render_template('admin_dashboard.html', 
                           username=session['admin'], 
                           projects=projects, 
                           users=users_dict, 
                           enrollments=enrollments_dict)

# Add other admin/project routes from sir's code here...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)