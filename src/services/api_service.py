"""
Flask API service for handling sensor data requests and camera operations
"""
import json5  # Add json5 for JSONC support
from flask import Flask, jsonify, Response, render_template, request
from flask_cors import CORS
from pathlib import Path
import time
from .video_stream_service import VideoStreamService

class APIService:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__, 
                        template_folder=Path(__file__).parent.parent / 'templates',
                        static_folder=Path(__file__).parent.parent.parent / 'static')
        # Enable CORS for all routes
        CORS(self.app)
        self.host = host
        self.port = port
        self.sensors_file = Path(__file__).parent.parent / 'data' / 'sensors_data.jsonc'
        self.start_time = time.time()
        self.video_service = VideoStreamService()  # Initialize video service
        
        # Register routes
        self.app.route('/api/sensors/<sensor_name>')(self.get_sensor_data)
        self.app.route('/api/sensors')(self.get_all_sensors)
        self.app.route('/health')(self.health_check)
        self.app.route('/video_feed')(self.video_feed)
        self.app.route('/')(self.index)
        
        # Camera control routes
        self.app.route('/api/camera/photo', methods=['POST'])(self.take_photo)
        self.app.route('/api/camera/record/start', methods=['POST'])(self.start_recording)
        self.app.route('/api/camera/record/stop', methods=['POST'])(self.stop_recording)
        self.app.route('/api/camera/audio/record', methods=['POST'])(self.record_audio)

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
            with open(self.sensors_file, 'r') as f:
                data = json5.loads(f.read())  # Use json5 instead of json for JSONC support
                
            if sensor_name not in data['sensors']:
                return jsonify({
                    'error': f'Sensor {sensor_name} not found'
                }), 404
                
            return jsonify(data['sensors'][sensor_name])
            
        except Exception as e:
            return jsonify({
                'error': f'Error retrieving sensor data: {str(e)}'
            }), 500

    def get_all_sensors(self):
        """Get list of all available sensors"""
        try:
            with open(self.sensors_file, 'r') as f:
                data = json5.loads(f.read())  # Use json5 instead of json for JSONC support
                
            # Return just the sensor names and descriptions
            sensors = {
                name: {'description': info['description']}
                for name, info in data['sensors'].items()
            }
            
            return jsonify(sensors)
            
        except Exception as e:
            return jsonify({
                'error': f'Error retrieving sensors list: {str(e)}'
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