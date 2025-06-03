#!/usr/bin/env python3
"""
Test script for Actuator Control
Tests all actuator control functions and provides interactive testing mode
"""

import serial
import serial.tools.list_ports
import time
import sys
import os

# Add the src directory to the path so we can import our utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.arduino_detector import find_arduino_port, list_all_ports

def display_menu():
    """Display the test menu"""
    print("\n" + "=" * 50)
    print("🔌 Actuator Control Test Menu")
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

def send_command(ser, command):
    """Send a command to Arduino and show response"""
    print(f"\nSending: {command.strip()}")
    try:
        ser.write(command.encode('utf-8'))
        time.sleep(0.3)
        
        # Check for response
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"Arduino response: {response}")
            return True, response
        else:
            print("No response from Arduino")
            return True, "No response"
            
    except Exception as e:
        print(f"Error sending command: {e}")
        return False, str(e)

def run_full_test(ser):
    """Run a complete test sequence for actuator"""
    print("\n=== Running Full Actuator Test Sequence ===")
    
    test_sequence = [
        ("[control]:actuator:extend\n", "Extending actuator"),
        ("[control]:actuator:stop\n", "Stopping actuator"),
        ("[control]:actuator:retract\n", "Retracting actuator"),
        ("[control]:actuator:stop\n", "Stopping actuator"),
        ("[control]:status\n", "Checking final status")
    ]
    
    for command, description in test_sequence:
        print(f"\n{description}...")
        success, response = send_command(ser, command)
        print(f"Result: {'✅ Success' if success else '❌ Failed'}")
        print(f"Response: {response}")
        time.sleep(1)  # Wait between commands
    
    print("\n=== Test Sequence Completed ===")

def main():
    # Configuration
    BAUD_RATE = 9600
    
    print("🤖 Actuator Control Interactive Test")
    print("=" * 50)
    
    # Auto-detect Arduino port
    print("🔍 Searching for Arduino...")
    arduino_port = find_arduino_port()
    
    if not arduino_port:
        print("❌ No Arduino found!")
        print("\n📋 Available ports:")
        list_all_ports()
        print("💡 Please connect your Arduino and try again.")
        return
    
    print(f"✅ Using Arduino at: {arduino_port}")
    print(f"📊 Baud Rate: {BAUD_RATE}")
    print("🔌 Connecting to Arduino...")
    
    try:
        # Connect to Arduino
        ser = serial.Serial(arduino_port, BAUD_RATE, timeout=2)
        time.sleep(2)  # Wait for Arduino to reset
        print("✅ Connected successfully!")
        
        while True:
            display_menu()
            
            try:
                choice = input("\nEnter your choice (0-6): ").strip()
                
                if choice == "0":
                    print("👋 Exiting...")
                    break
                    
                elif choice == "1":
                    send_command(ser, "[control]:actuator:extend\n")
                    
                elif choice == "2":
                    send_command(ser, "[control]:actuator:retract\n")
                    
                elif choice == "3":
                    send_command(ser, "[control]:actuator:stop\n")
                    
                elif choice == "4":
                    send_command(ser, "[control]:status\n")
                    
                elif choice == "5":
                    run_full_test(ser)
                    
                elif choice == "6":
                    custom_command = input("Enter custom command: ")
                    if not custom_command.endswith('\n'):
                        custom_command += '\n'
                    send_command(ser, custom_command)
                    
                else:
                    print("❌ Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n⚠️  Returning to menu...")
                continue
                
    except serial.SerialException as e:
        print(f"❌ Error connecting to Arduino: {e}")
        print("💡 Make sure:")
        print("   • Arduino is connected")
        print("   • Arduino has actuator_control.ino uploaded")
        print("   • No other program is using the serial port")
    except KeyboardInterrupt:
        print("\n⚠️  Program interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("🔌 Serial connection closed")

if __name__ == "__main__":
    main() 