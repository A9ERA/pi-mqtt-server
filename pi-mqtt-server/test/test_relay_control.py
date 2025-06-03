#!/usr/bin/env python3
"""
Test script for Relay Control
Tests all relay control functions and provides interactive testing mode
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
    print("🔌 Relay Control Test Menu")
    print("=" * 50)
    print("RELAY 1 CONTROLS:")
    print("  1. Start Relay 1")
    print("  2. Stop Relay 1")
    print()
    print("RELAY 2 CONTROLS:")
    print("  3. Start Relay 2")
    print("  4. Stop Relay 2")
    print()
    print("STATUS & TESTING:")
    print("  5. Check Relay Status")
    print("  6. Run Full Test Sequence")
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
    """Run a complete test sequence for both relays"""
    print("\n=== Running Full Relay Test Sequence ===")
    
    # Test sequence for each relay
    test_sequence = [
        ("[control]:relay:start:1\n", "Starting Relay 1"),
        ("[control]:relay:stop:1\n", "Stopping Relay 1"),
        ("[control]:relay:start:2\n", "Starting Relay 2"),
        ("[control]:relay:stop:2\n", "Stopping Relay 2")
    ]
    
    for command, description in test_sequence:
        print(f"\n{description}...")
        success, response = send_command(ser, command)
        print(f"Result: {'✅ Success' if success else '❌ Failed'}")
        print(f"Response: {response}")
        time.sleep(1)  # Wait between commands
    
    # Final status check
    print("\nChecking final status...")
    success, response = send_command(ser, "[control]:relay:status\n")
    print(f"Status: {response}")
    
    print("\n=== Test Sequence Completed ===")

def main():
    # Configuration
    BAUD_RATE = 9600
    
    print("🤖 Relay Control Interactive Test")
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
                    send_command(ser, "[control]:relay:start:1\n")
                    
                elif choice == "2":
                    send_command(ser, "[control]:relay:stop:1\n")
                    
                elif choice == "3":
                    send_command(ser, "[control]:relay:start:2\n")
                    
                elif choice == "4":
                    send_command(ser, "[control]:relay:stop:2\n")
                    
                elif choice == "5":
                    send_command(ser, "[control]:relay:status\n")
                    
                elif choice == "6":
                    run_full_test(ser)
                    
                else:
                    print("❌ Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n⚠️  Returning to menu...")
                continue
                
    except serial.SerialException as e:
        print(f"❌ Error connecting to Arduino: {e}")
        print("💡 Make sure:")
        print("   • Arduino is connected")
        print("   • Arduino has relay_control.ino uploaded")
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