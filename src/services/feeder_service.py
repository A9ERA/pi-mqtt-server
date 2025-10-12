"""
Feeder Service for controlling feeding process sequence
"""
import time
import datetime
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from .control_service import ControlService
from .feeder_history_service import FeederHistoryService
from .video_stream_service_usb import VideoStreamService
from .sensor_data_service import SensorDataService

class FeederService:
    def __init__(self, control_service: Optional[ControlService] = None, video_service: Optional[VideoStreamService] = None, sensor_data_service: Optional[SensorDataService] = None):
        """
        Initialize Feeder Service
        
        Args:
            control_service: ControlService instance for device control
            video_service: VideoStreamService instance for video recording
        """
        self.control_service = control_service
        self.history_service = FeederHistoryService()
        # Only create VideoStreamService if not provided (avoid multiple camera instances)
        if video_service is not None:
            self.video_service = video_service
        else:
            self.video_service = VideoStreamService()
        self._lock = threading.Lock()
        self.is_running = False
        self.sensor_data_service = sensor_data_service

    def _snapshot_sensor_values(self) -> Dict[str, Any]:
        """Capture snapshot of relevant sensor values at the time of logging."""
        result: Dict[str, Any] = {
            'feeder_humi': None,
            'food_moisture': None,
            'food_weight_kg': None,
            'battery_percentage': None,
        }
        try:
            if not self.sensor_data_service:
                return result
            data = self.sensor_data_service.get_sensor_data()
            sensors = data.get('sensors', {}) if isinstance(data, dict) else {}

            def get_value(sensor_name: str, value_type: str) -> Optional[float]:
                sensor = sensors.get(sensor_name, {})
                values = sensor.get('values', [])
                for v in values:
                    if v.get('type') == value_type:
                        try:
                            return float(v.get('value'))
                        except Exception:
                            return None
                return None

            feeder_humi = get_value('DHT22_FEEDER', 'humidity')
            food_moisture = get_value('SOIL_MOISTURE', 'soil_moisture')
            food_weight_kg = get_value('HX711_FEEDER', 'weight')
            if food_weight_kg is not None:
                try:
                    food_weight_kg = abs(float(food_weight_kg))
                except Exception:
                    pass
            battery_percentage = get_value('POWER_MONITOR', 'batteryPercentage')

            result['feeder_humi'] = feeder_humi
            result['food_moisture'] = food_moisture
            result['food_weight_kg'] = food_weight_kg
            result['battery_percentage'] = battery_percentage
        except Exception:
            # Keep defaults (None) on any error
            pass
        return result

    def start(self, feed_size: int, blower_duration: int) -> dict:
        """
        Start the feeding process sequence
        
        Args:
            feed_size: Feed size in grams (for reference/logging)
            blower_duration: Duration in seconds for blower operation
            
        Returns:
            dict: Status and result of the feeding process
        """
        if not self.control_service:
            return {
                'status': 'error',
                'message': 'Control service not available'
            }

        with self._lock:
            if self.is_running:
                return {
                    'status': 'error',
                    'message': 'Feeding process is already running'
                }
            
            self.is_running = True

        video_file = None
        led_turned_on_for_night = False
        try:
            print(f"[Feeder Service] Starting feeding process...")
            print(f"Feed size: {feed_size}g, Blower duration: {blower_duration}s")
            print(f"Note: Using weight-based control - feeder motor open until {feed_size}g weight reduction")

            # Night time LED control: 18:00 - 06:00 turn on LED during feeding
            try:
                now = datetime.datetime.now()
                is_night_time = (now.hour >= 18 or now.hour < 6)
                if is_night_time:
                    if self.control_service:
                        self.control_service.relay_led_on()
                        led_turned_on_for_night = True
                        print("[Feeder Service] Night time detected (18:00-06:00). LED turned ON for feeding.")
            except Exception as led_err:
                print(f"[Feeder Service] Warning: Failed to control LED for night feeding: {led_err}")

            # Start video recording
            try:
                video_file = self.video_service.start_feeder_recording()
                print(f"[Feeder Service] Video recording started: {video_file}")
            except Exception as video_error:
                print(f"[Feeder Service] Warning: Failed to start video recording: {video_error}")

            # Try fetch weight tolerance from Firebase app_setting and include as optional param
            weight_tolerance = 5  # Default to 5g if Firebase not available
            try:
                from firebase_admin import db  # Lazy import to avoid hard dependency when not configured
                ref = db.reference('/app_setting/feeder/weight_tolerance')
                wt = ref.get()
                if wt is not None:
                    weight_tolerance = int(float(wt))
            except Exception:
                # Ignore firebase errors silently; keep default
                pass

            # Send feeder start command to Arduino with parameters (feed_size, blower_duration, weight_tolerance)
            feeder_params = f"{feed_size},{blower_duration},{weight_tolerance}"
            command = f"feeder:start:{feeder_params}"
            
            print(f"[Feeder Service] Sending command to Arduino: [control]:{command}")
            if not self.control_service._send_command(command):
                raise Exception("Failed to send feeder start command to Arduino")
            
            # Calculate total estimated duration (with some buffer)
            # Using weight-based control: no fixed time for feeder motor open, only close=12s
            feedermotor_close = 12
            # Estimate feeder motor open time based on feed size (rough estimate: 1g per second)
            estimated_feedermotor_open = min(feed_size, 30)  # Cap at 30 seconds max
            total_duration = estimated_feedermotor_open + feedermotor_close + blower_duration
            buffer_time = 5  # Extra 5 seconds buffer
            estimated_duration = total_duration + buffer_time
            
            print(f"[Feeder Service] Feeding process initiated on Arduino. Estimated duration: {estimated_duration}s")
            
            # Wait for the estimated duration
            time.sleep(estimated_duration)

            # Stop video recording
            final_video_file = None
            try:
                if video_file:
                    final_video_file = self.video_service.stop_feeder_recording()
                    if final_video_file:
                        print(f"[Feeder Service] Video recording stopped: {final_video_file}")
                    else:
                        print(f"[Feeder Service] Warning: Video file was not created or is empty")
            except Exception as video_error:
                print(f"[Feeder Service] Warning: Failed to stop video recording: {video_error}")

            print(f"[Feeder Service] Feeding process completed successfully!")
            
            # Log successful feed operation
            # Extract only filename from full path for CSV storage (only if file exists)
            video_filename = Path(final_video_file).name if final_video_file else ""
            snapshot = self._snapshot_sensor_values()
            self.history_service.log_feed_operation(
                feed_size=feed_size,
                feedermotor_open=estimated_feedermotor_open,  # Estimated time
                feedermotor_close=feedermotor_close,
                blower_duration=blower_duration,
                status='success',
                message='Feeding process completed successfully (Arduino controlled)',
                video_file=video_filename,
                feeder_humi=snapshot.get('feeder_humi'),
                food_moisture=snapshot.get('food_moisture'),
                food_weight_kg=snapshot.get('food_weight_kg'),
                battery_percentage=snapshot.get('battery_percentage'),
            )
            
            return {
                'status': 'success',
                'message': 'Feeding process completed successfully (Arduino controlled)',
                'feed_size': feed_size,
                'video_file': final_video_file,
                'total_duration': estimated_duration,
                'steps_completed': [
                    f"Arduino controlled sequence:",
                    f"  - Feeder motor open: until {feed_size}g weight reduction (weight-based)",
                    f"  - Feeder motor close: {feedermotor_close}s (fixed)",
                    f"  - Blower: {blower_duration}s"
                ]
            }

        except Exception as e:
            error_msg = f"Feeding process failed: {str(e)}"
            print(f"[Feeder Service] Error: {error_msg}")
            
            # Stop video recording on error
            try:
                if video_file:
                    self.video_service.stop_feeder_recording()
                    print(f"[Feeder Service] Video recording stopped due to error")
            except Exception as video_error:
                print(f"[Feeder Service] Warning: Failed to stop video recording on error: {video_error}")
            
            # Send emergency stop command to Arduino
            try:
                print(f"[Feeder Service] Sending emergency stop command to Arduino")
                self.control_service._send_command("feeder:stop")
            except:
                print(f"[Feeder Service] Failed to send emergency stop command to Arduino")
            
            # Log failed feed operation (use fixed feeder motor values for logging)
            # Extract only filename from full path for CSV storage
            video_filename = Path(video_file).name if video_file else ""
            snapshot = self._snapshot_sensor_values()
            self.history_service.log_feed_operation(
                feed_size=feed_size,
                feedermotor_open=5,  # Fixed value
                feedermotor_close=12,  # Fixed value
                blower_duration=blower_duration,
                status='error',
                message=error_msg,
                video_file=video_filename,
                feeder_humi=snapshot.get('feeder_humi'),
                food_moisture=snapshot.get('food_moisture'),
                food_weight_kg=snapshot.get('food_weight_kg'),
                battery_percentage=snapshot.get('battery_percentage'),
            )

            return {
                'status': 'error',
                'message': error_msg,
                'video_file': video_file
            }
        
        finally:
            # Ensure LED is OFF after each feeding when we turned it on for night time
            try:
                if led_turned_on_for_night and self.control_service:
                    self.control_service.relay_led_off()
                    print("[Feeder Service] LED turned OFF after feeding (night mode).")
            except Exception as led_err:
                print(f"[Feeder Service] Warning: Failed to turn OFF LED after feeding: {led_err}")

            self.is_running = False

    def stop_all(self) -> dict:
        """
        Emergency stop all devices
        
        Returns:
            dict: Status of the stop operation
        """
        if not self.control_service:
            return {
                'status': 'error',
                'message': 'Control service not available'
            }

        try:
            print(f"[Feeder Service] Emergency stop initiated")
            
            # Send emergency stop command to Arduino
            self.control_service._send_command("feeder:stop")
            # Ensure LED is OFF on emergency stop
            try:
                self.control_service.relay_led_off()
            except Exception as led_err:
                print(f"[Feeder Service] Warning: Failed to turn OFF LED on emergency stop: {led_err}")
            
            self.is_running = False
            
            return {
                'status': 'success',
                'message': 'Emergency stop command sent to Arduino'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to send stop command: {str(e)}'
            }

    def get_status(self) -> dict:
        """
        Get current feeding process status
        
        Returns:
            dict: Current status information
        """
        return {
            'is_running': self.is_running,
            'control_service_available': self.control_service is not None
        } 