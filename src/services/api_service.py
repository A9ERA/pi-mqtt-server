"""
Flask API service for handling sensor data requests and camera operations
"""
try:
    import json5  # Add json5 for JSONC support
    JSON5_AVAILABLE = True
except ImportError:
    JSON5_AVAILABLE = False
    import json  # Fallback to standard json

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

if not JSON5_AVAILABLE:
    logger.warning("json5 module not found. Using standard json instead.")

# Flask and CORS imports will be imported only when needed
FLASK_AVAILABLE = False
try:
    from flask import Flask, jsonify, Response, render_template, request
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    logger.warning("Flask or Flask-CORS not found. API server functionality will be disabled.")

class APIService:
    def __init__(self, host='0.0.0.0', port=5000, serial_service=None):
        """Initialize API Service"""
        if not FLASK_AVAILABLE:
            logger.warning("API Service initialized without Flask. API server functionality will be disabled.")
            return

        self.app = Flask(__name__, 
                        template_folder=Path(__file__).parent.parent / 'templates',
                        static_folder=Path(__file__).parent.parent.parent / 'static')
        # Enable CORS for all routes
        CORS(self.app)
        self.host = host
        self.port = port
        self.sensors_file = Path(__file__).parent.parent / 'data' / 'sensors_data.jsonc'
        self.start_time = time.time()
        
        # Initialize services only if Flask is available
        if FLASK_AVAILABLE:
            try:
                from .video_stream_service import VideoStreamService
                from .control_service import ControlService
                from .firebase_service import FirebaseService
                from .sensor_data_service import SensorDataService
                
                self.video_service = VideoStreamService()  # Initialize video service
                self.control_service = ControlService(serial_service)  # Initialize control service
                self.firebase_service = FirebaseService()  # Initialize Firebase service
                self.sensor_data_service = SensorDataService()  # Initialize sensor data service
                
                # Setup routes
                self._setup_routes()
            except ImportError as e:
                logger.error(f"Failed to initialize services: {e}")
                FLASK_AVAILABLE = False

    def _setup_routes(self):
        """Setup Flask routes"""
        if not FLASK_AVAILABLE:
            return

        # Health check route
        self.app.route('/')(self.index)
        self.app.route('/health')(self.health_check)

        # Sensor data routes
        self.app.route('/api/sensors/<sensor_name>')(self.get_sensor_data)
        self.app.route('/api/sensors')(self.get_all_sensors)
        self.app.route('/api/sensors/sync', methods=['POST'])(self.sync_sensors_to_firebase)
        
        # Camera routes
        self.app.route('/api/camera/video_feed')(self.video_feed)
        self.app.route('/api/camera/photo', methods=['POST'])(self.take_photo)
        self.app.route('/api/camera/record/start', methods=['POST'])(self.start_recording)
        self.app.route('/api/camera/record/stop', methods=['POST'])(self.stop_recording)
        self.app.route('/api/camera/audio/record', methods=['POST'])(self.record_audio)
        
        # Device control routes
        self.app.route('/api/control/blower', methods=['POST'])(self.control_blower)
        self.app.route('/api/control/actuator', methods=['POST'])(self.control_actuator_motor)

    def parse_json_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse JSON file with support for comments (JSONC)
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Dictionary containing parsed JSON data
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return {}
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if JSON5_AVAILABLE:
                return json5.loads(content)
            else:
                # Remove comments manually if using standard json
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Skip comment lines
                    if line.strip().startswith('//'):
                        continue
                    # Remove inline comments
                    if '//' in line:
                        line = line.split('//')[0]
                    cleaned_lines.append(line)
                cleaned_content = '\n'.join(cleaned_lines)
                return json.loads(cleaned_content)
                
        except Exception as e:
            logger.error(f"Error parsing JSON file: {str(e)}")
            return {}

    # Flask route handlers will only be defined if Flask is available
    if FLASK_AVAILABLE:
        def index(self):
            """Render the main video streaming page"""
            return render_template('index.html')

        def video_feed(self):
            """Video streaming endpoint"""
            return self.video_service.get_video_feed()

        def take_photo(self):
            """Take a photo and return the file path"""
            try:
                file_path = self.video_service.take_photo()
                return jsonify({
                    'status': 'success',
                    'message': 'Photo captured successfully',
                    'file_path': file_path
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to capture photo: {str(e)}'
                }), 500

        def start_recording(self):
            """Start video recording"""
            try:
                file_path = self.video_service.start_recording()
                return jsonify({
                    'status': 'success',
                    'message': 'Recording started',
                    'file_path': file_path
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to start recording: {str(e)}'
                }), 500

        def stop_recording(self):
            """Stop video recording"""
            try:
                self.video_service.stop_recording()
                return jsonify({
                    'status': 'success',
                    'message': 'Recording stopped'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to stop recording: {str(e)}'
                }), 500

        def record_audio(self):
            """Start audio recording"""
            try:
                duration = request.json.get('duration', 30) if request.is_json else 30
                file_path = self.video_service.record_audio(duration)
                return jsonify({
                    'status': 'success',
                    'message': f'Audio recording started for {duration} seconds',
                    'file_path': file_path
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to start audio recording: {str(e)}'
                }), 500

        def health_check(self):
            """Health check endpoint that returns API status and uptime"""
            try:
                # Try to read the sensors file as a basic health check
                with open(self.sensors_file, 'r') as f:
                    json5.loads(f.read())  # Use json5 instead of json for JSONC support
                    
                uptime_seconds = int(time.time() - self.start_time)
                hours, remainder = divmod(uptime_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                return jsonify({
                    'status': 'healthy',
                    'uptime': f'{hours}h {minutes}m {seconds}s',
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'version': '1.0.0'
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }), 503

        def get_sensor_data(self, sensor_name):
            """Get data for a specific sensor by name"""
            try:
                # Use sensor data service instead of reading file directly
                all_data = self.sensor_data_service.get_sensor_data()
                
                # Check if there's an error from sensor data service
                if 'error' in all_data:
                    return jsonify({
                        'error': f'Error retrieving sensor data: {all_data["error"]}'
                    }), 500
                    
                # Check if sensor exists
                if sensor_name not in all_data.get('sensors', {}):
                    return jsonify({
                        'error': f'Sensor {sensor_name} not found'
                    }), 404
                    
                return jsonify(all_data['sensors'][sensor_name])
                
            except Exception as e:
                return jsonify({
                    'error': f'Error retrieving sensor data: {str(e)}'
                }), 500

        def get_all_sensors(self):
            """Get list of all available sensors"""
            try:
                # Use sensor data service instead of reading file directly
                all_data = self.sensor_data_service.get_sensor_data()
                
                # Check if there's an error from sensor data service
                if 'error' in all_data:
                    return jsonify({
                        'error': f'Error retrieving sensors list: {all_data["error"]}'
                    }), 500
                    
                # Return just the sensor names and descriptions
                sensors = {
                    name: {'description': info.get('description', 'No description available')}
                    for name, info in all_data.get('sensors', {}).items()
                }
                
                return jsonify(sensors)
                
            except Exception as e:
                return jsonify({
                    'error': f'Error retrieving sensors list: {str(e)}'
                }), 500

        def control_blower(self):
            """Control blower device via API"""
            try:
                if not request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'Request must be JSON'
                    }), 400

                data = request.get_json()
                action = data.get('action')
                value = data.get('value')  # For speed setting

                if not action:
                    return jsonify({
                        'status': 'error',
                        'message': 'Action is required'
                    }), 400

                # Validate actions
                valid_actions = ['start', 'stop', 'speed', 'direction_reverse', 'direction_normal']
                if action not in valid_actions:
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid action {action}. Valid actions are: {", ".join(valid_actions)}'
                    }), 400

                # For speed action, validate value
                if action == 'speed':
                    if value is None:
                        return jsonify({
                            'status': 'error',
                            'message': 'Value is required for speed action'
                        }), 400
                    if not isinstance(value, int) or value < 0:
                        return jsonify({
                            'status': 'error',
                            'message': 'Speed value must be a positive integer'
                        }), 400

                # Send command via control service
                success = self.control_service.control_blower(action, value)

                if success:
                    message = f"Blower {action} command sent successfully"
                    if action == 'speed':
                        message = f"Blower speed set to {value}"
                    return jsonify({
                        'status': 'success',
                        'message': message
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to send command to device'
                    }), 500

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error controlling blower: {str(e)}'
                }), 500

        def control_actuator_motor(self):
            """Control actuator motor device via API"""
            try:
                if not request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'Request must be JSON'
                    }), 400

                data = request.get_json()
                action = data.get('action')

                if not action:
                    return jsonify({
                        'status': 'error',
                        'message': 'Action is required'
                    }), 400

                # Validate actions
                valid_actions = ['up', 'down', 'stop']
                if action not in valid_actions:
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid action. Valid actions are: {", ".join(valid_actions)}'
                    }), 400

                # Send command via control service
                success = self.control_service.control_actuator_motor(action)

                if success:
                    return jsonify({
                        'status': 'success',
                        'message': f"Actuator motor {action} command sent successfully"
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to send command to device'
                    }), 500

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error controlling actuator motor: {str(e)}'
                }), 500

        def sync_sensors_to_firebase(self):
            """Sync current sensor data to Firebase Realtime Database"""
            try:
                # Get current sensor data from local storage
                sensor_data = self.sensor_data_service.get_sensor_data()
                
                # Check if sensor data exists
                if 'error' in sensor_data:
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to read sensor data: {sensor_data["error"]}'
                    }), 500
                
                # Sync to Firebase
                success = self.firebase_service.sync_sensor_data(sensor_data)
                
                if success:
                    return jsonify({
                        'status': 'success',
                        'message': 'Sensor data synced to Firebase successfully',
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'synced_sensors': list(sensor_data.get('sensors', {}).keys())
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to sync sensor data to Firebase'
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error syncing sensor data: {str(e)}'
                }), 500

        def start(self):
            """Start the Flask server"""
            try:
                # Start Flask server
                self.app.run(host=self.host, port=self.port)
            finally:
                # Release video service resources
                if hasattr(self, 'video_service'):
                    self.video_service.release() 