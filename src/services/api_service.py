"""
Enhanced Flask API service for handling sensor data requests, camera operations, and Arduino control
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
        """Initialize Enhanced API Service"""
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
        self.serial_service = serial_service  # Store serial service reference
        
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

        # Arduino status routes
        self.app.route('/api/arduino/status')(self.get_arduino_status)
        self.app.route('/api/arduino/health')(self.check_arduino_health)

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
        
        # Enhanced device control routes
        self.app.route('/api/control/blower', methods=['POST'])(self.control_blower)
        self.app.route('/api/control/actuator', methods=['POST'])(self.control_actuator_motor)
        self.app.route('/api/control/relay', methods=['POST'])(self.control_relay)
        self.app.route('/api/control/command', methods=['POST'])(self.send_custom_command)
        
        # New enhanced sensor monitoring routes
        self.app.route('/api/sensors/summary')(self.get_sensors_summary)
        self.app.route('/api/sensors/solar')(self.get_solar_data)
        self.app.route('/api/sensors/battery')(self.get_battery_data)
        self.app.route('/api/sensors/load')(self.get_load_data)
        self.app.route('/api/sensors/environmental')(self.get_environmental_data)
        self.app.route('/api/sensors/power')(self.get_power_data)

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
            """Enhanced health check endpoint that includes Arduino status"""
            try:
                # Basic API health check
                with open(self.sensors_file, 'r') as f:
                    json5.loads(f.read())  # Use json5 instead of json for JSONC support
                    
                uptime_seconds = int(time.time() - self.start_time)
                hours, remainder = divmod(uptime_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                # Include Arduino health status
                arduino_healthy = False
                arduino_status = {}
                if self.serial_service:
                    arduino_healthy = self.serial_service.is_arduino_healthy()
                    arduino_status = self.serial_service.get_arduino_status()
                
                return jsonify({
                    'status': 'healthy',
                    'uptime': f'{hours}h {minutes}m {seconds}s',
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'version': '2.0.0',
                    'arduino': {
                        'healthy': arduino_healthy,
                        'connected': arduino_status.get('connected', False),
                        'system_ready': arduino_status.get('system_ready', False)
                    }
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }), 503

        def get_arduino_status(self):
            """Get detailed Arduino system status"""
            try:
                if not self.serial_service:
                    return jsonify({
                        'error': 'Serial service not available'
                    }), 503
                
                status = self.serial_service.get_arduino_status()
                return jsonify({
                    'status': 'success',
                    'arduino_status': status,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error getting Arduino status: {str(e)}'
                }), 500

        def check_arduino_health(self):
            """Check Arduino health status"""
            try:
                if not self.serial_service:
                    return jsonify({
                        'healthy': False,
                        'reason': 'Serial service not available'
                    })
                
                healthy = self.serial_service.is_arduino_healthy()
                status = self.serial_service.get_arduino_status()
                
                return jsonify({
                    'healthy': healthy,
                    'connected': status.get('connected', False),
                    'system_ready': status.get('system_ready', False),
                    'last_heartbeat': status.get('last_heartbeat').isoformat() if status.get('last_heartbeat') else None,
                    'uptime': status.get('uptime', 0),
                    'free_memory': status.get('free_memory', 0),
                    'error_count': status.get('error_count', 0),
                    'sensor_errors': status.get('sensor_errors', {}),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                return jsonify({
                    'healthy': False,
                    'error': str(e)
                }), 500

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
            """Get list of all available sensors with enhanced information"""
            try:
                # Use sensor data service instead of reading file directly
                all_data = self.sensor_data_service.get_sensor_data()
                
                # Check if there's an error from sensor data service
                if 'error' in all_data:
                    return jsonify({
                        'error': f'Error retrieving sensors list: {all_data["error"]}'
                    }), 500
                
                # Include Arduino status in response
                arduino_status = {}
                if self.serial_service:
                    arduino_status = self.serial_service.get_arduino_status()
                
                return jsonify({
                    'sensors': all_data.get('sensors', {}),
                    'arduino_status': arduino_status,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                return jsonify({
                    'error': f'Error retrieving sensors list: {str(e)}'
                }), 500

        def control_blower(self):
            """Enhanced blower control with command acknowledgment"""
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
                valid_actions = ['start', 'stop', 'speed', 'direction']
                if action not in valid_actions:
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid action {action}. Valid actions are: {", ".join(valid_actions)}'
                    }), 400

                # Build command string
                if action == 'speed':
                    if value is None or not isinstance(value, int) or value < 0 or value > 255:
                        return jsonify({
                            'status': 'error',
                            'message': 'Speed value must be an integer between 0 and 255'
                        }), 400
                    command = f"speed:{value}"
                elif action == 'direction':
                    direction = data.get('direction', 'normal')
                    if direction not in ['normal', 'reverse']:
                        return jsonify({
                            'status': 'error',
                            'message': 'Direction must be "normal" or "reverse"'
                        }), 400
                    command = f"direction:{direction}"
                else:
                    command = action

                # Send command via serial service
                if self.serial_service:
                    success = self.serial_service.send_command('blower', command)
                    if success:
                        return jsonify({
                            'status': 'success',
                            'message': f'Blower {action} command sent successfully',
                            'command': command
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to send command to Arduino'
                        }), 500
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Serial service not available'
                    }), 503

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error controlling blower: {str(e)}'
                }), 500

        def control_actuator_motor(self):
            """Enhanced actuator motor control"""
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

                # Send command via serial service
                if self.serial_service:
                    success = self.serial_service.send_command('actuatormotor', action)
                    if success:
                        return jsonify({
                            'status': 'success',
                            'message': f'Actuator motor {action} command sent successfully'
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to send command to Arduino'
                        }), 500
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Serial service not available'
                    }), 503

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error controlling actuator motor: {str(e)}'
                }), 500

        def control_relay(self):
            """Control relay devices"""
            try:
                if not request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'Request must be JSON'
                    }), 400

                data = request.get_json()
                relay_id = data.get('relay_id')
                action = data.get('action')

                if not relay_id or not action:
                    return jsonify({
                        'status': 'error',
                        'message': 'Both relay_id and action are required'
                    }), 400

                # Validate actions
                valid_actions = ['on', 'off', 'toggle']
                if action not in valid_actions:
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid action. Valid actions are: {", ".join(valid_actions)}'
                    }), 400

                # Send command via serial service
                if self.serial_service:
                    command = f"{relay_id}:{action}"
                    success = self.serial_service.send_command('relay', command)
                    if success:
                        return jsonify({
                            'status': 'success',
                            'message': f'Relay {relay_id} {action} command sent successfully'
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to send command to Arduino'
                        }), 500
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Serial service not available'
                    }), 503

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error controlling relay: {str(e)}'
                }), 500

        def send_custom_command(self):
            """Send custom command to Arduino"""
            try:
                if not request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'Request must be JSON'
                    }), 400

                data = request.get_json()
                device = data.get('device')
                action = data.get('action')

                if not device or not action:
                    return jsonify({
                        'status': 'error',
                        'message': 'Both device and action are required'
                    }), 400

                # Send command via serial service
                if self.serial_service:
                    success = self.serial_service.send_command(device, action)
                    if success:
                        return jsonify({
                            'status': 'success',
                            'message': f'Custom command sent: {device}:{action}'
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to send command to Arduino'
                        }), 500
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Serial service not available'
                    }), 503

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Error sending custom command: {str(e)}'
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
                
                # Include Arduino status in sync
                if self.serial_service:
                    arduino_status = self.serial_service.get_arduino_status()
                    sensor_data['arduino_status'] = arduino_status
                
                # Sync to Firebase
                success = self.firebase_service.sync_sensor_data(sensor_data)
                
                if success:
                    return jsonify({
                        'status': 'success',
                        'message': 'Sensor data synced to Firebase successfully',
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'synced_sensors': list(sensor_data.get('sensors', {}).keys()),
                        'arduino_status_included': bool(self.serial_service)
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

        def get_sensors_summary(self):
            """Get summary of all sensor data with categorization"""
            try:
                all_data = self.sensor_data_service.get_sensor_data()
                
                if 'error' in all_data:
                    return jsonify({
                        'error': f'Error retrieving sensor data: {all_data["error"]}'
                    }), 500
                
                sensors = all_data.get('sensors', {})
                
                # Categorize sensors
                environmental = {}
                power_system = {}
                actuators = {}
                
                for sensor_name, sensor_data in sensors.items():
                    if any(keyword in sensor_name.lower() for keyword in ['dht', 'soil', 'water_temp', 'weight']):
                        environmental[sensor_name] = sensor_data
                    elif any(keyword in sensor_name.lower() for keyword in ['solar', 'battery', 'load', 'voltage', 'current']):
                        power_system[sensor_name] = sensor_data
                    elif any(keyword in sensor_name.lower() for keyword in ['actuator', 'blower', 'relay']):
                        actuators[sensor_name] = sensor_data
                
                # Include Arduino status
                arduino_status = {}
                if self.serial_service:
                    arduino_status = self.serial_service.get_arduino_status()
                
                return jsonify({
                    'summary': {
                        'environmental': environmental,
                        'power_system': power_system,
                        'actuators': actuators
                    },
                    'arduino_status': arduino_status,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_sensors': len(sensors)
                })
                
            except Exception as e:
                return jsonify({
                    'error': f'Error getting sensors summary: {str(e)}'
                }), 500

        def get_solar_data(self):
            """Get solar panel monitoring data"""
            try:
                all_data = self.sensor_data_service.get_sensor_data()
                sensors = all_data.get('sensors', {})
                
                solar_data = sensors.get('SOLAR_MONITOR', {})
                if not solar_data:
                    return jsonify({
                        'error': 'Solar monitor data not available'
                    }), 404
                
                return jsonify({
                    'solar_data': solar_data,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                return jsonify({
                    'error': f'Error getting solar data: {str(e)}'
                }), 500

        def get_battery_data(self):
            """Get battery monitoring data"""
            try:
                all_data = self.sensor_data_service.get_sensor_data()
                sensors = all_data.get('sensors', {})
                
                battery_data = sensors.get('BATTERY_MONITOR', {})
                if not battery_data:
                    return jsonify({
                        'error': 'Battery monitor data not available'
                    }), 404
                
                return jsonify({
                    'battery_data': battery_data,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                return jsonify({
                    'error': f'Error getting battery data: {str(e)}'
                }), 500

        def get_load_data(self):
            """Get load monitoring data"""
            try:
                all_data = self.sensor_data_service.get_sensor_data()
                sensors = all_data.get('sensors', {})
                
                load_data = sensors.get('LOAD_MONITOR', {})
                if not load_data:
                    return jsonify({
                        'error': 'Load monitor data not available'
                    }), 404
                
                return jsonify({
                    'load_data': load_data,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                return jsonify({
                    'error': f'Error getting load data: {str(e)}'
                }), 500

        def get_environmental_data(self):
            """Get environmental sensor data (DHT, soil, water temp, weight)"""
            try:
                all_data = self.sensor_data_service.get_sensor_data()
                sensors = all_data.get('sensors', {})
                
                environmental_sensors = [
                    'DHT22_SYSTEM', 'DHT22_FEEDER', 
                    'SOIL_SENSOR', 'WATER_TEMP_SENSOR', 'WEIGHT_SENSOR'
                ]
                
                environmental_data = {}
                for sensor_name in environmental_sensors:
                    if sensor_name in sensors:
                        environmental_data[sensor_name] = sensors[sensor_name]
                
                return jsonify({
                    'environmental_data': environmental_data,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'sensor_count': len(environmental_data)
                })
                
            except Exception as e:
                return jsonify({
                    'error': f'Error getting environmental data: {str(e)}'
                }), 500

        def get_power_data(self):
            """Get complete power system data (solar, battery, load, voltage, current)"""
            try:
                all_data = self.sensor_data_service.get_sensor_data()
                sensors = all_data.get('sensors', {})
                
                power_sensors = [
                    'SOLAR_MONITOR', 'BATTERY_MONITOR', 'LOAD_MONITOR',
                    'VOLTAGE_SENSOR', 'CURRENT_SENSOR'
                ]
                
                power_data = {}
                for sensor_name in power_sensors:
                    if sensor_name in sensors:
                        power_data[sensor_name] = sensors[sensor_name]
                
                # Calculate total power consumption and generation
                summary = {
                    'solar_power': 0,
                    'load_power': 0,
                    'battery_voltage': 0,
                    'battery_percentage': 0,
                    'system_status': 'unknown'
                }
                
                # Extract power values if available
                if 'SOLAR_MONITOR' in power_data:
                    for value in power_data['SOLAR_MONITOR'].get('value', []):
                        if value.get('type') == 'power':
                            summary['solar_power'] = value.get('value', 0)
                
                if 'LOAD_MONITOR' in power_data:
                    for value in power_data['LOAD_MONITOR'].get('value', []):
                        if value.get('type') == 'power':
                            summary['load_power'] = value.get('value', 0)
                
                if 'BATTERY_MONITOR' in power_data:
                    for value in power_data['BATTERY_MONITOR'].get('value', []):
                        if value.get('type') == 'voltage':
                            summary['battery_voltage'] = value.get('value', 0)
                        elif value.get('type') == 'percentage':
                            summary['battery_percentage'] = value.get('value', 0)
                        elif value.get('type') == 'status':
                            summary['system_status'] = value.get('value', 'unknown')
                
                return jsonify({
                    'power_data': power_data,
                    'summary': summary,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'sensor_count': len(power_data)
                })
                
            except Exception as e:
                return jsonify({
                    'error': f'Error getting power data: {str(e)}'
                }), 500

        def start(self):
            """Start the Flask server"""
            try:
                print("🌐 Enhanced API Service starting...")
                print(f"📡 Serial service: {'Connected' if self.serial_service and self.serial_service.is_running else 'Not available'}")
                print("📋 Available endpoints:")
                print("  🏥 Health & Status:")
                print("    - GET  /health                    - Health check with Arduino status")
                print("    - GET  /api/arduino/status        - Detailed Arduino status")
                print("    - GET  /api/arduino/health        - Arduino health check")
                print("\n  📊 Sensor Data:")
                print("    - GET  /api/sensors               - Get all sensors with Arduino status")
                print("    - GET  /api/sensors/<name>        - Get specific sensor")
                print("    - GET  /api/sensors/summary       - Get categorized sensor summary")
                print("    - GET  /api/sensors/solar         - Get solar panel data")
                print("    - GET  /api/sensors/battery       - Get battery data")
                print("    - GET  /api/sensors/load          - Get load monitoring data")
                print("    - GET  /api/sensors/environmental - Get environmental sensors")
                print("    - GET  /api/sensors/power         - Get complete power system data")
                print("    - POST /api/sensors/sync          - Sync to Firebase")
                print("\n  🎮 Device Control:")
                print("    - POST /api/control/blower        - Control blower motor")
                print("    - POST /api/control/actuator      - Control actuator motor")
                print("    - POST /api/control/relay         - Control relay devices")
                print("    - POST /api/control/command       - Send custom commands")
                print("\n  📹 Camera & Media:")
                print("    - GET  /api/camera/video_feed     - Live video stream")
                print("    - POST /api/camera/photo          - Take photo")
                print("    - POST /api/camera/record/start   - Start video recording")
                print("    - POST /api/camera/record/stop    - Stop video recording")
                
                print("\n🔥 Firebase sync: POST /api/sensors/sync")
                print("💡 Test commands:")
                print("   curl -X GET http://localhost:5000/api/sensors/summary")
                print("   curl -X GET http://localhost:5000/api/sensors/power")
                print("   curl -X POST http://localhost:5000/api/sensors/sync")
                print("   curl -X POST -H 'Content-Type: application/json' \\")
                print("        -d '{\"action\":\"start\"}' http://localhost:5000/api/control/blower")
                print("   curl -X POST -H 'Content-Type: application/json' \\")
                print("        -d '{\"action\":\"up\"}' http://localhost:5000/api/control/actuator")
                print("   curl -X POST -H 'Content-Type: application/json' \\")
                print("        -d '{\"relay_id\":\"1\",\"action\":\"on\"}' http://localhost:5000/api/control/relay")
                
                print("\n" + "="*60)
                
                # Start Flask server
                self.app.run(host=self.host, port=self.port)
            finally:
                # Release video service resources
                if hasattr(self, 'video_service'):
                    self.video_service.release() 