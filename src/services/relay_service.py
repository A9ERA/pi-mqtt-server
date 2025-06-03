"""
Relay Control Service
Handles communication with Arduino for relay control
"""

from typing import Optional, Dict, Tuple
import serial
import time
from ..utils.arduino_detector import find_arduino_port

class RelayService:
    def __init__(self):
        self.serial_port = None
        self.baud_rate = 9600
        self.is_connected = False
        self.relay_states = {
            "1": False,  # Relay 1 state
            "2": False   # Relay 2 state
        }

    def connect(self) -> bool:
        """Connect to Arduino"""
        try:
            if self.is_connected:
                return True

            port = find_arduino_port()
            if not port:
                print("❌ No Arduino found!")
                return False

            self.serial_port = serial.Serial(port, self.baud_rate, timeout=2)
            time.sleep(2)  # Wait for Arduino to reset
            self.is_connected = True
            print(f"✅ Connected to Arduino at {port}")
            return True

        except Exception as e:
            print(f"❌ Error connecting to Arduino: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from Arduino"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.is_connected = False
        print("🔌 Disconnected from Arduino")

    def _send_command(self, command: str) -> Tuple[bool, str]:
        """Send command to Arduino and get response"""
        if not self.is_connected and not self.connect():
            return False, "Not connected to Arduino"

        try:
            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'

            # Send command
            self.serial_port.write(command.encode('utf-8'))
            time.sleep(0.3)  # Wait for response

            # Read response
            if self.serial_port.in_waiting > 0:
                response = self.serial_port.readline().decode('utf-8').strip()
                return True, response
            return True, "No response from Arduino"

        except Exception as e:
            self.is_connected = False
            return False, f"Error: {str(e)}"

    def start_relay(self, relay_num: str) -> Tuple[bool, str]:
        """Start specified relay"""
        if relay_num not in ["1", "2"]:
            return False, "Invalid relay number"
        
        success, response = self._send_command(f"[control]:relay:start:{relay_num}")
        if success and "ON" in response:
            self.relay_states[relay_num] = True
        return success, response

    def stop_relay(self, relay_num: str) -> Tuple[bool, str]:
        """Stop specified relay"""
        if relay_num not in ["1", "2"]:
            return False, "Invalid relay number"
        
        success, response = self._send_command(f"[control]:relay:stop:{relay_num}")
        if success and "OFF" in response:
            self.relay_states[relay_num] = False
        return success, response

    def get_status(self) -> Tuple[bool, Dict[str, bool]]:
        """Get current status of all relays"""
        success, response = self._send_command("[control]:relay:status")
        if not success:
            return False, self.relay_states

        # Parse status response
        try:
            lines = response.split('\n')
            for line in lines:
                if "Relay 1:" in line:
                    self.relay_states["1"] = "ON" in line
                elif "Relay 2:" in line:
                    self.relay_states["2"] = "ON" in line
        except Exception:
            pass  # Keep existing states if parsing fails

        return True, self.relay_states

    def control_relay(self, action: str, relay_num: Optional[str] = None) -> Tuple[bool, str]:
        """
        Control relay with a single method
        action: 'start', 'stop', or 'status'
        relay_num: '1' or '2' (required for start/stop)
        """
        if action == "status":
            success, states = self.get_status()
            if success:
                status_str = "\n".join([f"Relay {k}: {'ON' if v else 'OFF'}" for k, v in states.items()])
                return True, f"📊 Relay Status:\n{status_str}"
            return False, "Failed to get status"

        if not relay_num or relay_num not in ["1", "2"]:
            return False, "Invalid relay number"

        if action == "start":
            return self.start_relay(relay_num)
        elif action == "stop":
            return self.stop_relay(relay_num)
        else:
            return False, f"Unknown action: {action}"

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.disconnect() 