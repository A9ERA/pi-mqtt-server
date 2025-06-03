"""
Firebase Service for updating sensor data to Realtime Database
"""
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

import datetime
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from ..config.settings import FIREBASE_ADMIN_SDK_PATH, FIREBASE_DATABASE_URL, FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)

if not FIREBASE_AVAILABLE:
    logger.warning("firebase_admin module not found. Firebase functionality will be disabled.")

class FirebaseService:
    def __init__(self):
        if not FIREBASE_AVAILABLE:
            logger.warning("FirebaseService initialized without firebase_admin module. Firebase functionality will be disabled.")
            self.app = None
            self.database = None
            return

        self.app = None
        self.database = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        if not FIREBASE_AVAILABLE:
            logger.warning("Cannot initialize Firebase: firebase_admin module not available")
            return

        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # Path to service account key file
                cred_path = Path(FIREBASE_ADMIN_SDK_PATH)
                
                # Check if credential file exists
                if not cred_path.exists():
                    logger.error(f"Firebase credential file not found: {cred_path}")
                    raise FileNotFoundError(f"Firebase credential file not found: {cred_path}")
                
                # Initialize the app with a service account, granting admin privileges
                cred = credentials.Certificate(str(cred_path))
                self.app = firebase_admin.initialize_app(cred, {
                    'databaseURL': FIREBASE_DATABASE_URL,
                    'projectId': FIREBASE_PROJECT_ID
                })
                
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                # Use existing app
                self.app = firebase_admin.get_app()
                logger.info("Using existing Firebase app instance")
                
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise

    def sync_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        """
        Sync sensor data to Firebase Realtime Database
        
        Args:
            sensor_data: Dictionary containing sensor data to sync
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not FIREBASE_AVAILABLE:
            logger.warning("Cannot sync sensor data: firebase_admin module not available")
            return False

        try:
            # Get a database reference
            ref = db.reference('/')
            
            # Prepare data for Firebase
            firebase_data = {
                'sensors': sensor_data.get('sensors', {}),
                'last_updated': sensor_data.get('last_updated', datetime.datetime.now().isoformat()),
                'sync_timestamp': datetime.datetime.now().isoformat()
            }
            
            # Update data in Firebase
            ref.update(firebase_data)
            
            logger.info("Successfully synced sensor data to Firebase")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync sensor data to Firebase: {str(e)}")
            return False

    def update_specific_sensor(self, sensor_name: str, sensor_values: list) -> bool:
        """
        Update specific sensor data in Firebase
        
        Args:
            sensor_name: Name of the sensor
            sensor_values: List of sensor readings
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not FIREBASE_AVAILABLE:
            logger.warning("Cannot update sensor: firebase_admin module not available")
            return False

        try:
            # Get a database reference for the specific sensor
            ref = db.reference(f'/sensors/{sensor_name}')
            
            current_time = datetime.datetime.now().isoformat()
            
            sensor_data = {
                'last_updated': current_time,
                'description': f"Data from {sensor_name}",
                'values': sensor_values,
                'sync_timestamp': current_time
            }
            
            # Update sensor data
            ref.set(sensor_data)
            
            # Update global last_updated timestamp
            global_ref = db.reference('/last_updated')
            global_ref.set(current_time)
            
            logger.info(f"Successfully updated sensor '{sensor_name}' in Firebase")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update sensor '{sensor_name}' in Firebase: {str(e)}")
            return False

    def get_sensor_data_from_firebase(self, sensor_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sensor data from Firebase
        
        Args:
            sensor_name: Optional specific sensor name to retrieve
            
        Returns:
            Dictionary containing sensor data
        """
        if not FIREBASE_AVAILABLE:
            logger.warning("Cannot get sensor data: firebase_admin module not available")
            return {'error': 'firebase_admin module not available'}

        try:
            if sensor_name:
                ref = db.reference(f'/sensors/{sensor_name}')
            else:
                ref = db.reference('/')
                
            data = ref.get()
            
            if data:
                logger.info(f"Successfully retrieved sensor data from Firebase")
                return data
            else:
                logger.warning("No data found in Firebase")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to retrieve sensor data from Firebase: {str(e)}")
            return {'error': str(e)}

    def health_check(self) -> Dict[str, Any]:
        """
        Check Firebase connection health
        
        Returns:
            Dictionary containing health status
        """
        if not FIREBASE_AVAILABLE:
            return {
                'status': 'unhealthy',
                'firebase_connected': False,
                'error': 'firebase_admin module not available',
                'timestamp': datetime.datetime.now().isoformat()
            }

        try:
            # Try to read from Firebase
            ref = db.reference('/health_check')
            ref.set({
                'timestamp': datetime.datetime.now().isoformat(),
                'status': 'healthy'
            })
            
            return {
                'status': 'healthy',
                'firebase_connected': True,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'firebase_connected': False,
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            } 