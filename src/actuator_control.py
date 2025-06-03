#!/usr/bin/env python3
"""
Actuator Control Module
Handles MQTT communication for actuator control and serial communication with Arduino
Provides both interactive and MQTT control modes
"""

import os
import sys
import time
import json
import serial
import paho.mqtt.client as mqtt
import serial.tools.list_ports
from typing import Optional, Tuple

# Add the src directory to the path so we can import our utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.arduino_detector import find_arduino_port, list_all_ports

class ActuatorController:
    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883,
                 serial_port: Optional[str] = None, baud_rate: int = 9600,
                 interactive_mode: bool = False):
        """Initialize the actuator controller with MQTT and Serial connections"""
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.baud_rate = baud_rate
        self.serial_port = serial_port
        self.ser: Optional[serial.Serial] = None
        self.mqtt_client: Optional[mqtt.Client] = None
        self.connected = False
        self.interactive_mode = interactive_mode
        
        # MQTT Topics
        self.topics = {
            'extend': '[control]/actuator/extend',
            'retract': '[control]/actuator/retract',
            'stop': '[control]/actuator/stop',
            'status': '[control]/status',
            'response': '[response]/actuator/status'
        }
        
        # Initialize connections
        self._setup_serial()
        if not interactive_mode:
            self._setup_mqtt()

    def _setup_mqtt(self):
        """Setup MQTT client and connect to broker"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            print(f"🔌 Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}...")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
        except Exception as e:
            print(f"❌ Error setting up MQTT: {e}")
            raise

    def _setup_serial(self):
        """Setup serial connection to Arduino"""
        try:
            if not self.serial_port:
                print("🔍 Searching for Arduino...")
                self.serial_port = find_arduino_port()
                
            if not self.serial_port:
                print("❌ No Arduino found!")
                print("\n📋 Available ports:")
                list_all_ports()
                raise ConnectionError("No Arduino device found")
            
            print(f"🔌 Connecting to Arduino at {self.serial_port}...")
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=2)
            time.sleep(2)  # Wait for Arduino to reset
            print("✅ Arduino connected successfully!")
            
        except Exception as e:
            print(f"❌ Error setting up Serial connection: {e}")
            raise

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print("✅ Connected to MQTT broker!")
            self.connected = True
            
            # Subscribe to all control topics
            for topic in [self.topics['extend'], self.topics['retract'], 
                         self.topics['stop'], self.topics['status']]:
                client.subscribe(topic)
                print(f"📡 Subscribed to {topic}")
        else:
            print(f"❌ Failed to connect to MQTT broker, return code: {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            print(f"⚠️ Unexpected MQTT disconnection, return code: {rc}")
        else:
            print("ℹ️ Disconnected from MQTT broker")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            print(f"📥 Received message on {topic}: {payload}")
            
            # Convert MQTT topic to Arduino command
            if topic == self.topics['extend']:
                self._send_arduino_command("[control]:actuator:extend")
            elif topic == self.topics['retract']:
                self._send_arduino_command("[control]:actuator:retract")
            elif topic == self.topics['stop']:
                self._send_arduino_command("[control]:actuator:stop")
            elif topic == self.topics['status']:
                self._send_arduino_command("[control]:status")
                
        except Exception as e:
            print(f"❌ Error processing MQTT message: {e}")

    def _send_arduino_command(self, command: str) -> Tuple[bool, str]:
        """Send command to Arduino and get response"""
        if not self.ser or not self.ser.is_open:
            print("❌ Serial port not connected")
            return False, "Serial port not connected"
            
        try:
            print(f"📤 Sending to Arduino: {command}")
            self.ser.write(f"{command}\n".encode('utf-8'))
            time.sleep(0.3)  # Short delay for Arduino processing
            
            if self.ser.in_waiting > 0:
                response = self.ser.readline().decode('utf-8').strip()
                print(f"📥 Arduino response: {response}")
                
                # Publish response to MQTT if not in interactive mode
                if not self.interactive_mode and self.mqtt_client and self.connected:
                    self.mqtt_client.publish(self.topics['response'], response)
                
                return True, response
            else:
                print("⚠️ No response from Arduino")
                return True, "No response"
                
        except Exception as e:
            error_msg = f"Error sending command: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def display_menu(self):
        """Display the interactive menu"""
        print("\n" + "=" * 50)
        print("Actuator Control - Interactive Mode")
        print("=" * 50)
        print("ACTUATOR CONTROLS:")
        print("  1. Extend actuator")
        print("  2. Retract actuator")
        print("  3. Stop actuator")
        print()
        print("STATUS & TESTING:")
        print("  4. Check actuator status")
        print("  5. Run full test sequence")
        print("  6. Send custom command")
        print()
        print("  0. Exit")
        print("=" * 50)

    def run_full_test(self):
        """Run a complete test sequence"""
        print("\n=== Running Full Actuator Test Sequence ===")
        
        test_sequence = [
            ("[control]:actuator:extend", "Extending actuator"),
            ("[control]:actuator:stop", "Stopping actuator"),
            ("[control]:actuator:retract", "Retracting actuator"),
            ("[control]:actuator:stop", "Stopping actuator"),
            ("[control]:status", "Checking final status")
        ]
        
        for command, description in test_sequence:
            print(f"\n{description}...")
            success, response = self._send_arduino_command(command)
            print(f"Result: {'✅ Success' if success else '❌ Failed'}")
            print(f"Response: {response}")
            time.sleep(1)  # Wait between commands
        
        print("\n=== Test Sequence Completed ===")

    def start_interactive(self):
        """Start interactive control mode"""
        try:
            print("🚀 Starting Actuator Controller in Interactive Mode...")
            
            while True:
                self.display_menu()
                
                try:
                    choice = input("\nEnter your choice (0-6): ").strip()
                    
                    if choice == "0":
                        print("👋 Exiting...")
                        break
                        
                    elif choice == "1":
                        self._send_arduino_command("[control]:actuator:extend")
                        
                    elif choice == "2":
                        self._send_arduino_command("[control]:actuator:retract")
                        
                    elif choice == "3":
                        self._send_arduino_command("[control]:actuator:stop")
                        
                    elif choice == "4":
                        self._send_arduino_command("[control]:status")
                        
                    elif choice == "5":
                        self.run_full_test()
                        
                    elif choice == "6":
                        custom_command = input("Enter custom command: ")
                        if not custom_command.endswith('\n'):
                            custom_command += '\n'
                        self._send_arduino_command(custom_command.strip())
                        
                    else:
                        print("❌ Invalid choice. Please try again.")
                        
                except KeyboardInterrupt:
                    print("\n⚠️  Returning to menu...")
                    continue
                    
        except KeyboardInterrupt:
            print("\n⚠️  Shutting down...")
        finally:
            self.cleanup()

    def start(self):
        """Start the actuator controller"""
        try:
            if self.interactive_mode:
                self.start_interactive()
            else:
                print("🚀 Starting Actuator Controller in MQTT Mode...")
                while True:
                    time.sleep(1)  # Keep the main thread alive
                    
        except KeyboardInterrupt:
            print("\n⚠️  Shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup connections"""
        print("🧹 Cleaning up connections...")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("✅ MQTT connection closed")
            
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✅ Serial connection closed")

def main():
    """Main entry point"""
    try:
        # Check if interactive mode is requested
        interactive_mode = "--interactive" in sys.argv
        
        # Create and start the controller
        controller = ActuatorController(interactive_mode=interactive_mode)
        controller.start()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 