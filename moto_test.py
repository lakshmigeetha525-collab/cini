import os
import sys
import boto3
import sqlite3
from moto import mock_aws

# 1. MOCK AWS CREDENTIALS
# Real AWS account block aagama irukka indha dummy keys romba mukkiyam
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'ap-south-1'  # Unga app.py-la irukura same region

# 2. START MOTO MOCK (AWS Services-ah intercept pannum)
mock = mock_aws()
mock.start()

# 3. IMPORT YOUR APP
# Unga file peru 'app.py' nu irundha idha use pannunga
try:
    from app import app
except ImportError:
    print("Error: 'app.py' file-ah kandupudikka mudiyala. File name check pannunga!")
    sys.exit(1)

def setup_test_env():
    print(">>> [MOTO] Mock AWS Environment Starting...")
    
    # SNS Client-ah mock environment-la create pannudhu
    sns = boto3.client('sns', region_name='ap-south-1')
    
    # Dummy Topic create pannudhu (Internal logic-kaaga)
    sns.create_topic(Name='CineBooker_Mock_Topic')
    
    print(">>> [MOTO] SNS Mocking Ready. Real SMS anupama test pannalam.")
    
    # Database check (SQLite file create aagi irukka nu pakkum)
    if not os.path.exists('cinebooker.db'):
        print(">>> [DB] Initializing SQLite database 'cinebooker.db'...")
    else:
        print(">>> [DB] Using existing SQLite database.")

if __name__ == '__main__':
    try:
        setup_test_env()
        
        print("\n" + "="*50)
        print("CINEBOOKER TEST SERVER IS RUNNING")
        print(f"URL: http://localhost:5000")
        print(f"Network Access: http://0.0.0.0:5000") # Moto phone-la check panna idhu help aagum
        print("="*50 + "\n")
        
        # use_reloader=False kandippa venum, illana Moto mock state reset aayidum
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        
    except Exception as e:
        print(f"Server Error: {e}")
    finally:
        # Mock-ah stop pannuvom
        print("\n>>> Stopping Mock Environment...")
        mock.stop()