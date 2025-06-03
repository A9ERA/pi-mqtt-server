#!/usr/bin/env python3
"""
Test script for relay control functionality
"""

import sys
import os
import time
import serial
import serial.tools.list_ports

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.arduino_detector import find_arduino_port, list_all_ports

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
        else:
            print("No response from Arduino")
            
        print("Command sent successfully!")
        
    except Exception as e:
        print(f"Error sending command: {e}")

def display_menu():
    """Display the command menu"""
    print("\n" + "=" * 50)
    print("Relay Control - Interactive Mode")
    print("=" * 50)
    print("RELAY CONTROLS:")
    print("  1. Turn relay ON")
    print("  2. Turn relay OFF")
    print()
    print("TESTING:")
    print("  3. Run full test sequence")
    print("  4. Send custom command")
    print()
    print("  0. Exit")
    print("=" * 50)

def run_full_test(ser):
    """Run a complete test sequence for relay"""
    print("\n=== Running Full Relay Test Sequence ===")
    
    commands = [
        "[control]:relay:on\n",
        "[control]:relay:off\n"
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\nStep {i}/{len(commands)}: {cmd.strip()}")
        send_command(ser, cmd)
        time.sleep(1)
    
    print("\n=== Test sequence completed ===")

def main():
    # Configuration
    BAUD_RATE = 9600
    
    print("🤖 Relay Control Test")
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
                choice = input("\nEnter your choice (0-4): ").strip()
                
                if choice == "0":
                    print("👋 Exiting...")
                    break
                    
                elif choice == "1":
                    send_command(ser, "[control]:relay:on\n")
                    
                elif choice == "2":
                    send_command(ser, "[control]:relay:off\n")
                    
                elif choice == "3":
                    run_full_test(ser)
                    
                elif choice == "4":
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
        print("   • Arduino drivers are installed")
        print("   • Arduino is not being used by another application")
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