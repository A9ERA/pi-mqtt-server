"""
Enhanced Serial Service for handling USB serial communication with Arduino
Supports multiple message types: SEND, STATUS, HEARTBEAT, ERROR, CMD_ACK
"""
import serial
import serial.tools.list_ports
import json
import threading
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from src.services.sensor_data_service import SensorDataService
from src.config.settings import BAUD_RATE

class SerialService:
    def __init__(self, port: str = None, baud_rate: int = BAUD_RATE):
        """
        Initialize Enhanced Serial Service
        
        Args:
            port: Serial port (if None, will auto-detect Arduino)
            baud_rate: Baud rate for serial communication (default from settings)
        """
        self.port = port or self.find_arduino_port()
        self.baud_rate = baud_rate
        self.serial = None
        self.is_running = False
        self._stop_event = threading.Event()
        self.sensor_data_service = SensorDataService()
        self.read_thread = None
        
        # Message handlers
        self.message_handlers = {
            'SEND': self._handle_sensor_data,
            'STATUS': self._handle_system_status,
            'HEARTBEAT': self._handle_heartbeat,
            'ERROR': self._handle_error,
            'CMD_ACK': self._handle_command_ack,
            'SENSOR_ERRORS': self._handle_sensor_errors
        }
        
        # System status tracking
        self.arduino_status = {
            'connected': False,
            'system_ready': False,
            'last_heartbeat': None,
            'uptime': 0,
            'free_memory': 0,
            'error_count': 0,
            'sensor_errors': {}
        }
        
        # Command callback for acknowledgments
        self.command_callbacks = {}

    def find_arduino_port(self) -> Optional[str]:
        """
        Automatically find Arduino port by checking connected devices
        
        Returns:
            str: Arduino port device path if found, None otherwise
        """
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Check for common Arduino identifiers
            if ("Arduino" in port.description or 
                "CH340" in port.description or 
                "ttyUSB" in port.device or
                "ttyACM" in port.device or
                "FT232" in port.description or
                "CP210" in port.description or
                "2560" in port.description):  # Arduino Mega 2560
                print(f"✅ Arduino found at {port.device} ({port.description})")
                return port.device
        
        print("❌ No Arduino device found")
        return None

    def list_available_ports(self):
        """List all available serial ports for debugging"""
        ports = serial.tools.list_ports.comports()
        print("\n📋 Available serial ports:")
        if not ports:
            print("  No serial ports found")
        else:
            for port in ports:
                print(f"  • {port.device} - {port.description}")
        print()

    def connect(self) -> bool:
        """
        Connect to the serial port with retry logic
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        max_retries = 3
        for attempt in range(max_retries):
            if self._try_connect(self.port):
                self.arduino_status['connected'] = True
                return True
            
            if attempt < max_retries - 1:
                print(f"Retrying connection in 2 seconds... (attempt {attempt + 2}/{max_retries})")
                time.sleep(2)
                # Try to find Arduino port again
                new_port = self.find_arduino_port()
                if new_port and new_port != self.port:
                    self.port = new_port
        
        return False

    def _try_connect(self, port: str) -> bool:
        """
        Try to connect to a specific port
        
        Args:
            port: Serial port to connect to
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.serial = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                timeout=1,
                write_timeout=1
            )
            # Wait for Arduino to initialize
            time.sleep(2)
            print(f"✅ Connected to {port} at {self.baud_rate} baud")
            return True
        except Exception as e:
            print(f"❌ Serial connection error on {port}: {e}")
            return False

    def disconnect(self):
        """Disconnect from the serial port"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.arduino_status['connected'] = False
            print("Disconnected from serial port")

    def send_command(self, device: str, action: str, callback: Callable = None) -> bool:
        """
        Send command to Arduino
        
        Args:
            device: Device name (blower, relay, actuatormotor)
            action: Action to perform
            callback: Optional callback for command acknowledgment
            
        Returns:
            bool: True if command sent successfully
        """
        if not self.serial or not self.serial.is_open:
            print("❌ Serial connection not available")
            return False
        
        try:
            command = f"[control]:{device}:{action}\n"
            self.serial.write(command.encode('utf-8'))
            
            # Store callback for acknowledgment
            if callback:
                command_id = f"{device}:{action}"
                self.command_callbacks[command_id] = callback
            
            print(f"📤 Command sent: {command.strip()}")
            return True
        except Exception as e:
            print(f"❌ Error sending command: {e}")
            return False

    def read_serial_data(self):
        """Read data from serial port in a loop with enhanced message parsing"""
        buffer = ""
        
        while not self._stop_event.is_set():
            if self.serial and self.serial.is_open:
                try:
                    if self.serial.in_waiting:
                        data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                        buffer += data
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line:
                                self._process_message(line)
                                
                except Exception as e:
                    print(f"❌ Error reading serial data: {e}")
                    # Try to reconnect
                    if not self._try_reconnect():
                        break
            else:
                time.sleep(0.1)

    def _try_reconnect(self) -> bool:
        """Try to reconnect to Arduino"""
        print("🔄 Attempting to reconnect...")
        self.disconnect()
        time.sleep(1)
        return self.connect()

    def _process_message(self, message: str):
        """
        Process received message based on its type
        
        Args:
            message: Raw message from Arduino
        """
        try:
            # Parse message format: [TYPE] - data
            if ' - ' in message:
                parts = message.split(' - ', 1)
                if len(parts) == 2:
                    message_type = parts[0].strip('[]')
                    data = parts[1]
                    
                    if message_type in self.message_handlers:
                        self.message_handlers[message_type](data)
                    else:
                        print(f"🔍 Unknown message type: {message_type}")
                        print(f"📝 Raw message: {message}")
            else:
                # Handle messages without type prefix (legacy support)
                print(f"📝 Raw Arduino message: {message}")
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            print(f"📝 Raw message: {message}")

    def _handle_sensor_data(self, data: str):
        """Handle sensor data messages"""
        try:
            data_dict = json.loads(data)
            sensor_name = data_dict.get('name', 'unknown')
            sensor_type = data_dict.get('sensor_type', sensor_name)
            timestamp = data_dict.get('timestamp', 0)
            
            print(f"📊 Sensor data from {sensor_type}: {sensor_name}")
            self.sensor_data_service.update_sensor_data(sensor_name, data_dict.get('value', []))
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in sensor data: {e}")
        except Exception as e:
            print(f"❌ Error handling sensor data: {e}")

    def _handle_system_status(self, data: str):
        """Handle system status messages"""
        try:
            status_dict = json.loads(data)
            self.arduino_status.update({
                'system_ready': status_dict.get('system_ready', False),
                'error_count': status_dict.get('error_count', 0),
                'uptime': status_dict.get('uptime', 0)
            })
            print(f"🔧 System status: Ready={self.arduino_status['system_ready']}, Errors={self.arduino_status['error_count']}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in status data: {e}")

    def _handle_heartbeat(self, data: str):
        """Handle heartbeat messages"""
        try:
            heartbeat_dict = json.loads(data)
            self.arduino_status.update({
                'last_heartbeat': datetime.now(),
                'uptime': heartbeat_dict.get('uptime', 0),
                'free_memory': heartbeat_dict.get('free_memory', 0),
                'system_ready': heartbeat_dict.get('system_ready', False)
            })
            print(f"💓 Heartbeat: Uptime={self.arduino_status['uptime']}ms, Memory={self.arduino_status['free_memory']}B")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in heartbeat data: {e}")

    def _handle_error(self, data: str):
        """Handle error messages"""
        print(f"⚠️  Arduino Error: {data}")

    def _handle_command_ack(self, data: str):
        """Handle command acknowledgment messages"""
        try:
            ack_dict = json.loads(data)
            device = ack_dict.get('device', '')
            action = ack_dict.get('action', '')
            status = ack_dict.get('status', 'unknown')
            
            command_id = f"{device}:{action}"
            print(f"✅ Command ACK: {command_id} - {status}")
            
            # Call callback if exists
            if command_id in self.command_callbacks:
                callback = self.command_callbacks.pop(command_id)
                callback(status == 'success', ack_dict)
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in command ACK: {e}")

    def _handle_sensor_errors(self, data: str):
        """Handle sensor error summary messages"""
        try:
            error_dict = json.loads(data)
            self.arduino_status['sensor_errors'] = error_dict
            print(f"⚠️  Sensor errors detected: {error_dict}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in sensor errors: {e}")

    def get_arduino_status(self) -> Dict[str, Any]:
        """Get current Arduino system status"""
        return self.arduino_status.copy()

    def is_arduino_healthy(self) -> bool:
        """Check if Arduino is healthy based on heartbeat and status"""
        if not self.arduino_status['connected']:
            return False
        
        last_heartbeat = self.arduino_status.get('last_heartbeat')
        if last_heartbeat:
            time_since_heartbeat = (datetime.now() - last_heartbeat).total_seconds()
            return time_since_heartbeat < 60  # Consider healthy if heartbeat within 60 seconds
        
        return False

    def start(self):
        """Start the enhanced serial service"""
        print("🚀 Starting Enhanced Serial Service...")
        print(f"🎯 Target port: {self.port}")
        print(f"📡 Baud rate: {self.baud_rate}")
        
        if not self.connect():
            print("❌ Failed to establish serial connection")
            self.list_available_ports()
            print("💡 Please check:")
            print("   • Arduino is connected via USB")
            print("   • Arduino drivers are installed")
            print("   • No other application is using the port")
            print("   • Arduino is running the fish-feeder firmware")
            return False

        self._stop_event.clear()
        self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        self.read_thread.start()
        self.is_running = True
        print("✅ Enhanced Serial service started successfully")
        return True

    def stop(self):
        """Stop the serial service"""
        self.is_running = False
        self._stop_event.set()
        if self.read_thread:
            self.read_thread.join(timeout=5)
        self.disconnect()
        print("🛑 Serial service stopped") 