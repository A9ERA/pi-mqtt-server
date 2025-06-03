#!/usr/bin/env python3
"""
Test script for Relay Control
Tests all relay control functions and provides interactive testing mode
"""

import sys
import os
import time

# Add the src directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from services.relay_service import RelayService

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

def run_full_test(relay_service):
    """Run a complete test sequence for both relays"""
    print("\n=== Running Full Relay Test Sequence ===")
    
    # Test sequence for each relay
    test_sequence = [
        ("1", "start", "Starting Relay 1"),
        ("1", "stop", "Stopping Relay 1"),
        ("2", "start", "Starting Relay 2"),
        ("2", "stop", "Stopping Relay 2")
    ]
    
    for relay_num, action, description in test_sequence:
        print(f"\n{description}...")
        success, response = relay_service.control_relay(action, relay_num)
        print(f"Result: {'✅ Success' if success else '❌ Failed'}")
        print(f"Response: {response}")
        time.sleep(1)  # Wait between commands
    
    # Final status check
    print("\nChecking final status...")
    success, response = relay_service.control_relay("status")
    print(f"Status: {response}")
    
    print("\n=== Test Sequence Completed ===")

def interactive_test():
    """Run interactive test mode"""
    print("🤖 Relay Control Interactive Test")
    print("=" * 50)
    
    # Initialize relay service
    relay_service = RelayService()
    
    # Try to connect
    print("🔍 Connecting to Arduino...")
    if not relay_service.connect():
        print("❌ Failed to connect to Arduino")
        print("💡 Please make sure:")
        print("   • Arduino is connected")
        print("   • Arduino has relay_control.ino uploaded")
        print("   • No other program is using the serial port")
        return
    
    print("✅ Connected successfully!")
    
    try:
        while True:
            display_menu()
            
            try:
                choice = input("\nEnter your choice (0-6): ").strip()
                
                if choice == "0":
                    print("👋 Exiting...")
                    break
                    
                elif choice == "1":
                    success, response = relay_service.control_relay("start", "1")
                    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
                    print(f"Response: {response}")
                    
                elif choice == "2":
                    success, response = relay_service.control_relay("stop", "1")
                    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
                    print(f"Response: {response}")
                    
                elif choice == "3":
                    success, response = relay_service.control_relay("start", "2")
                    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
                    print(f"Response: {response}")
                    
                elif choice == "4":
                    success, response = relay_service.control_relay("stop", "2")
                    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
                    print(f"Response: {response}")
                    
                elif choice == "5":
                    success, response = relay_service.control_relay("status")
                    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
                    print(f"Response: {response}")
                    
                elif choice == "6":
                    run_full_test(relay_service)
                    
                else:
                    print("❌ Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n⚠️  Returning to menu...")
                continue
                
    except KeyboardInterrupt:
        print("\n⚠️  Program interrupted by user")
    finally:
        relay_service.disconnect()
        print("🔌 Disconnected from Arduino")

if __name__ == "__main__":
    interactive_test() 