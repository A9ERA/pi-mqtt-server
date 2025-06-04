"""
Application settings and configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Serial Configuration
BAUD_RATE = int(os.getenv('BAUD_RATE', '115200'))

# Application Configuration
APP_NAME = "FISH FEEDER - Pi Serial Server"
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Firebase Configuration
FIREBASE_ADMIN_SDK_PATH = os.getenv('FIREBASE_ADMIN_SDK_PATH', 'fish-feeder-test-1-firebase-adminsdk-fbsvc-5e2b64dd1c.json')
FIREBASE_DATABASE_URL = os.getenv('FIREBASE_DATABASE_URL', 'https://fish-feeder-test-1-default-rtdb.asia-southeast1.firebasedatabase.app/')
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'fish-feeder-test-1') 