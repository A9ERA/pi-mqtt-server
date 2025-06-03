#!/usr/bin/env python3
"""
Test script for Feeder Motor Control (ผ่าน L298N)
ทดสอบการควบคุมมอเตอร์เกลียวลำเลียงอาหารจาก Pi ไปยัง Arduino
"""

import serial
import serial.tools.list_ports
import time
import sys
import os

def display_menu():
    """แสดงเมนูควบคุม Feeder Motor"""
    print("\n" + "=" * 50)
    print("🔌 Feeder Motor Control Test Menu")
    print("=" * 50)
    print("  1. Forward (เดินหน้า)")
    print("  2. Backward (ถอยหลัง)")
    print("  3. Stop (หยุด)")
    print("  4. Status (สถานะ)")
    print("  5. Send custom command (ส่งคำสั่งเอง)")
    print("  0. Exit (ออก)")
    print("=" * 50)

def find_arduino_port():
    """ค้นหา Arduino port อัตโนมัติ"""
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description or "USB-SERIAL" in port.description:
            return port.device
    return None

def send_command(ser, command):
    """ส่งคำสั่งไปยัง Arduino และแสดงผลลัพธ์"""
    print(f"\nSending: {command.strip()}")
    try:
        ser.write(command.encode('utf-8'))
        time.sleep(0.3)
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

def main():
    BAUD_RATE = 9600
    print("🤖 Feeder Motor Control Interactive Test")
    print("=" * 50)
    print("🔍 กำลังค้นหา Arduino...")
    arduino_port = find_arduino_port()
    if not arduino_port:
        print("❌ ไม่พบ Arduino!")
        return
    print(f"✅ ใช้ Arduino ที่: {arduino_port}")
    print(f"📊 Baud Rate: {BAUD_RATE}")
    print("🔌 กำลังเชื่อมต่อกับ Arduino...")

    try:
        ser = serial.Serial(arduino_port, BAUD_RATE, timeout=2)
        time.sleep(2)
        print("✅ เชื่อมต่อสำเร็จ!")

        while True:
            display_menu()
            try:
                choice = input("\nเลือกตัวเลือก (0-5): ").strip()
                if choice == "0":
                    print("👋 ออกจากโปรแกรม...")
                    break
                elif choice == "1":
                    send_command(ser, "[control]:feeder:forward\n")
                elif choice == "2":
                    send_command(ser, "[control]:feeder:backward\n")
                elif choice == "3":
                    send_command(ser, "[control]:feeder:stop\n")
                elif choice == "4":
                    send_command(ser, "[control]:feeder:status\n")
                elif choice == "5":
                    print("\nรูปแบบคำสั่งที่รองรับ:")
                    print("[control]:feeder:forward   - เดินหน้า")
                    print("[control]:feeder:backward  - ถอยหลัง")
                    print("[control]:feeder:stop      - หยุด")
                    print("[control]:feeder:status    - สถานะ")
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