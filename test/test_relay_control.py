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
from services.relay_service import RelayService

def test_relay_control():
    """Test relay control functionality"""
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
    print("🔌 Connecting to Arduino...")
    
    try:
        # Initialize relay service
        relay_service = RelayService(arduino_port)
        print("✅ Connected successfully!")
        
        # Test relay control
        print("\n=== Testing Relay Control ===")
        
        # Test turning relay on
        print("\nTesting relay ON...")
        relay_service.turn_on()
        time.sleep(2)  # Wait for 2 seconds
        
        # Test turning relay off
        print("Testing relay OFF...")
        relay_service.turn_off()
        time.sleep(2)  # Wait for 2 seconds
        
        print("\n=== Test completed ===")
        
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
        if 'relay_service' in locals():
            relay_service.close()
            print("🔌 Serial connection closed")

if __name__ == "__main__":
    test_relay_control() 