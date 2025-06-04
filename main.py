#!/usr/bin/env python3
"""
Enhanced Main entry point for Pi Server with improved Arduino integration
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.services.api_service import APIService
from src.services.firebase_service import FirebaseService
from src.services.serial_service import SerialService

def main():
    """Main function to start the enhanced server"""
    print("🚀 Starting Enhanced Fish Feeder Pi Server...")
    print("=" * 60)
    
    try:
        # Initialize services
        print("🔧 Initializing services...")
        
        # Initialize Serial service first with enhanced features
        print("📡 Starting Enhanced Serial Service...")
        serial_service = SerialService()
        
        if not serial_service.start():
            print("⚠️  Failed to start Serial service. Please check your USB connection.")
            print("💡 Server will continue without serial communication.")
            print("🔍 Available options:")
            print("   1. Check Arduino connection and restart")
            print("   2. Continue without Arduino (limited functionality)")
            
            user_choice = input("Continue without Arduino? (y/N): ").lower().strip()
            if user_choice != 'y':
                print("🛑 Exiting. Please connect Arduino and restart.")
                sys.exit(1)
            
            serial_service = None
        else:
            print("✅ Enhanced Serial service started successfully")
            
            # Wait a moment for Arduino to send initial status
            import time
            time.sleep(3)
            
            # Check Arduino health
            if serial_service.is_arduino_healthy():
                print("💚 Arduino is healthy and ready")
                status = serial_service.get_arduino_status()
                print(f"🔧 System ready: {status.get('system_ready', False)}")
                print(f"⚡ Free memory: {status.get('free_memory', 0)} bytes")
            else:
                print("⚠️  Arduino connection established but health check failed")
        
        # Test Firebase connection
        print("🔥 Testing Firebase connection...")
        firebase_service = FirebaseService()
        health = firebase_service.health_check()
        if health['status'] == 'healthy':
            print("✅ Firebase connection successful")
        else:
            print(f"⚠️  Firebase connection issue: {health.get('error', 'Unknown error')}")
        
        # Initialize Enhanced API service with serial service
        print("🌐 Initializing Enhanced API Service...")
        api_service = APIService(host='0.0.0.0', port=5000, serial_service=serial_service)
        
        print("\n🎉 Server initialization complete!")
        print("🌐 Server starting on http://0.0.0.0:5000")
        print("\n📋 Enhanced API endpoints:")
        print("  🏥 Health & Status:")
        print("    - GET  /health                    - Health check with Arduino status")
        print("    - GET  /api/arduino/status        - Detailed Arduino system status")
        print("    - GET  /api/arduino/health        - Arduino health check")
        print("\n  📊 Sensor Data:")
        print("    - GET  /api/sensors               - Get all sensors with Arduino status")
        print("    - GET  /api/sensors/<name>        - Get specific sensor data")
        print("    - GET  /api/sensors/summary       - Get categorized sensor summary")
        print("    - GET  /api/sensors/solar         - Get solar panel monitoring data")
        print("    - GET  /api/sensors/battery       - Get battery monitoring data")
        print("    - GET  /api/sensors/load          - Get load monitoring data")
        print("    - GET  /api/sensors/environmental - Get environmental sensors (DHT, soil, etc.)")
        print("    - GET  /api/sensors/power         - Get complete power system data")
        print("    - POST /api/sensors/sync          - Sync sensor data to Firebase")
        print("\n  🎮 Device Control:")
        print("    - POST /api/control/blower        - Control blower motor")
        print("    - POST /api/control/actuator      - Control actuator motor")
        print("    - POST /api/control/relay         - Control relay devices")
        print("    - POST /api/control/command       - Send custom commands")
        print("\n  📹 Camera & Media:")
        print("    - GET  /api/camera/video_feed     - Live video stream")
        print("    - POST /api/camera/photo          - Take photo")
        print("    - POST /api/camera/record/start   - Start video recording")
        print("    - POST /api/camera/record/stop    - Stop video recording")
        
        print("\n🔥 Firebase sync: POST /api/sensors/sync")
        print("💡 Test commands:")
        print("   📊 Sensor Data:")
        print("   curl -X GET http://localhost:5000/api/sensors/summary")
        print("   curl -X GET http://localhost:5000/api/sensors/power")
        print("   curl -X GET http://localhost:5000/api/sensors/environmental")
        print("   curl -X POST http://localhost:5000/api/sensors/sync")
        print("\n   🎮 Device Control:")
        print("   curl -X POST -H 'Content-Type: application/json' \\")
        print("        -d '{\"action\":\"start\"}' http://localhost:5000/api/control/blower")
        print("   curl -X POST -H 'Content-Type: application/json' \\")
        print("        -d '{\"action\":\"up\"}' http://localhost:5000/api/control/actuator")
        print("   curl -X POST -H 'Content-Type: application/json' \\")
        print("        -d '{\"relay_id\":\"1\",\"action\":\"on\"}' http://localhost:5000/api/control/relay")
        print("\n   ☀️🔋 Power System Examples:")
        print("   curl -X GET http://localhost:5000/api/sensors/solar")
        print("   curl -X GET http://localhost:5000/api/sensors/battery") 
        print("   curl -X GET http://localhost:5000/api/sensors/load")
        
        print("\n" + "="*60)
        print("🚀 Starting server... Press Ctrl+C to stop")
        
        # Start the server
        api_service.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        if 'serial_service' in locals() and serial_service:
            print("📡 Stopping serial service...")
            serial_service.stop()
    except Exception as e:
        print(f"❌ Error starting server: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'serial_service' in locals() and serial_service:
            serial_service.stop()
        sys.exit(1)

if __name__ == "__main__":
    main() 