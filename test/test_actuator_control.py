#!/usr/bin/env python3
"""
Test script for Actuator Control
Tests all actuator control functions and provides interactive testing mode
Works with ActuatorSensor class on Arduino
"""

import serial
import serial.tools.list_ports
import time
import sys
import os
import json

# Add the src directory to the path so we can import our utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.arduino_detector import find_arduino_port, list_all_ports

def display_menu():
    """Display the test menu"""
    print("\n" + "=" * 50)
    print("🔌 Actuator Control Test Menu")
    print("=" * 50)
    print("ACTUATOR CONTROLS:")
    print("  1. Extend actuator (ดันออก)")
    print("  2. Retract actuator (ดึงกลับ)")
    print("  3. Stop actuator (หยุด)")
    print()
    print("STATUS & TESTING:")
    print("  4. Check actuator status (ตรวจสอบสถานะ)")
    print("  5. Run full test sequence (ทดสอบเต็มระบบ)")
    print("  6. Send custom command (ส่งคำสั่งเอง)")
    print()
    print("  0. Exit (ออก)")
    print("=" * 50)

def send_command(ser, command):
    """Send a command to Arduino and show response"""
    print(f"\nSending: {command.strip()}")
    try:
        ser.write(command.encode('utf-8'))
        time.sleep(0.3)  # รอ Arduino ประมวลผล
        
        # ตรวจสอบการตอบกลับ
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"Arduino response: {response}")
            
            # แปลงสถานะเป็นภาษาไทย
            status_map = {
                "OK:EXTENDED": "✅ ดันออกสุดแล้ว",
                "OK:RETRACTED": "✅ ดึงกลับสุดแล้ว",
                "OK:STOPPED": "✅ หยุดแล้ว",
                "OK:MOVING": "🔄 กำลังเคลื่อนที่",
                "ERROR:TIMEOUT": "❌ หมดเวลา",
                "ERROR:NO_POWER": "❌ ไม่มีไฟเลี้ยง",
                "ERROR:INVALID_COMMAND": "❌ คำสั่งไม่ถูกต้อง"
            }
            
            if response in status_map:
                print(f"Status: {status_map[response]}")
            
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
    print("ทดสอบระบบเต็มรูปแบบ")
    print("=" * 50)
    
    test_sequence = [
        ("[control]:actuator:extend\n", "กำลังดัน actuator ออก..."),
        ("[control]:actuator:stop\n", "กำลังหยุด actuator..."),
        ("[control]:actuator:retract\n", "กำลังดึง actuator กลับ..."),
        ("[control]:actuator:stop\n", "กำลังหยุด actuator..."),
        ("[control]:status\n", "กำลังตรวจสอบสถานะสุดท้าย...")
    ]
    
    for command, description in test_sequence:
        print(f"\n{description}")
        success, response = send_command(ser, command)
        print(f"Result: {'✅ สำเร็จ' if success else '❌ ล้มเหลว'}")
        print(f"Response: {response}")
        time.sleep(1)  # รอระหว่างคำสั่ง
    
    print("\n=== Test Sequence Completed ===")
    print("ทดสอบเสร็จสิ้น")

def main():
    # Configuration
    BAUD_RATE = 9600
    
    print("🤖 Actuator Control Interactive Test")
    print("ทดสอบการควบคุม Actuator แบบ Interactive")
    print("=" * 50)
    
    # Auto-detect Arduino port
    print("🔍 กำลังค้นหา Arduino...")
    arduino_port = find_arduino_port()
    
    if not arduino_port:
        print("❌ ไม่พบ Arduino!")
        print("\n📋 พอร์ตที่พบ:")
        list_all_ports()
        print("💡 กรุณาเชื่อมต่อ Arduino และลองอีกครั้ง")
        return
    
    print(f"✅ ใช้ Arduino ที่: {arduino_port}")
    print(f"📊 Baud Rate: {BAUD_RATE}")
    print("🔌 กำลังเชื่อมต่อกับ Arduino...")
    
    try:
        # Connect to Arduino
        ser = serial.Serial(arduino_port, BAUD_RATE, timeout=2)
        time.sleep(2)  # รอ Arduino รีเซ็ต
        print("✅ เชื่อมต่อสำเร็จ!")
        
        while True:
            display_menu()
            
            try:
                choice = input("\nเลือกตัวเลือก (0-6): ").strip()
                
                if choice == "0":
                    print("👋 ออกจากโปรแกรม...")
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
                    print("\nรูปแบบคำสั่งที่รองรับ:")
                    print("[control]:actuator:extend  - ดันออก")
                    print("[control]:actuator:retract - ดึงกลับ")
                    print("[control]:actuator:stop    - หยุด")
                    print("[control]:status          - ตรวจสอบสถานะ")
                    custom_command = input("\nป้อนคำสั่ง: ")
                    if not custom_command.endswith('\n'):
                        custom_command += '\n'
                    send_command(ser, custom_command)
                    
                else:
                    print("❌ ตัวเลือกไม่ถูกต้อง กรุณาลองอีกครั้ง")
                    
            except KeyboardInterrupt:
                print("\n⚠️ กลับไปที่เมนู...")
                continue
                
    except serial.SerialException as e:
        print(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ Arduino: {e}")
        print("💡 ตรวจสอบว่า:")
        print("   • Arduino เชื่อมต่ออยู่")
        print("   • อัพโหลด actuator_control.ino แล้ว")
        print("   • ไม่มีโปรแกรมอื่นใช้พอร์ตนี้อยู่")
    except KeyboardInterrupt:
        print("\n⚠️ ผู้ใช้ยกเลิกโปรแกรม")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("🔌 ปิดการเชื่อมต่อ Serial")

if __name__ == "__main__":
    main() 