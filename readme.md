# Pi Server - Fish Feeder Project

A Raspberry Pi server application for managing sensor data, device control, and Firebase integration.

## Features

- **Sensor Data Management**: Read and store sensor data locally
- **Firebase Integration**: Sync sensor data to Firebase Realtime Database
- **Device Control**: Control blower and actuator motor via API
- **Video Streaming**: Live camera feed and recording capabilities
- **RESTful API**: Complete API endpoints for web integration

## Firebase Setup

1. Place your Firebase Admin SDK JSON file in the project root
2. Copy `env.example` to `.env` and configure your Firebase settings:
   ```
   FIREBASE_ADMIN_SDK_PATH=your-firebase-admin-sdk-file.json
   FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com/
   FIREBASE_PROJECT_ID=your-project-id
   ```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables (copy from `env.example`)

## API Endpoints

### Sensor Data
- `GET /api/sensors` - Get all sensors list
- `GET /api/sensors/<sensor_name>` - Get specific sensor data
- `POST /api/sensors/sync` - Sync current sensor data to Firebase

### Device Control
- `POST /api/control/blower` - Control blower device
- `POST /api/control/actuator` - Control actuator motor

### Camera
- `GET /api/camera/video_feed` - Live video stream
- `POST /api/camera/photo` - Take a photo
- `POST /api/camera/record/start` - Start video recording
- `POST /api/camera/record/stop` - Stop video recording

### System
- `GET /health` - Health check endpoint

## Firebase Sync Usage

To sync sensor data to Firebase, send a POST request to `/api/sensors/sync`:

```bash
curl -X POST http://localhost:5000/api/sensors/sync
```

Response:
```json
{
  "status": "success",
  "message": "Sensor data synced to Firebase successfully",
  "timestamp": "2024-01-01 12:00:00",
  "synced_sensors": ["sensor1", "sensor2"]
}
```

## Project Structure

```
pi-server/
├── src/
│   ├── config/          # Configuration files
│   ├── services/        # Core services
│   │   ├── api_service.py
│   │   ├── firebase_service.py
│   │   ├── sensor_data_service.py
│   │   └── ...
│   ├── data/           # Local data storage
│   └── templates/      # HTML templates
├── test/               # Test files
└── requirements.txt    # Python dependencies
```

Install Mosquitto on pi

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

Install ngrok CLI
```bash
sudo apt install unzip
wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip
unzip ngrok-stable-linux-arm.zip
sudo mv ngrok /usr/local/bin
```

Setup ngrok
```bash
ngrok config add-authtoken < token >
```

To monitor a serial port
```bash
screen /dev/ttyUSB0 9600
```

# Pi-MQTT-Server & Fish-Feeder-Arduino

## โครงสร้างโปรเจกต์

- `fish-feeder-arduino/` : โค้ดฝั่ง Arduino (PlatformIO)
  - `src/services/blower_sensor.h/cpp` : ควบคุม Blower Motor (Pin 50, 5, 6)
  - `src/services/relay_sensor.h/cpp` : ควบคุม Relay (Pin 50, 52)
  - `src/services/actuator_sensor.h/cpp` : ควบคุม Actuator & Feeder Motor (Pin 8,9,10,11,12,13)
- `test/` : สคริปต์ Python สำหรับทดสอบแต่ละอุปกรณ์บน Pi
  - `test_blower_control.py` : ทดสอบ Blower
  - `test_actuator_control.py` : ทดสอบ Actuator

## Pin Mapping หลัก (ตามเอกสาร)
- Blower: 50 (Relay), 5 (PWM_R), 6 (PWM_L)
- Relay: 50, 52
- Actuator: 11 (ENA), 12 (IN1), 13 (IN2)
- Feeder: 8 (ENA), 9 (IN1), 10 (IN2)

## วิธีใช้งาน
1. อัพโหลดโค้ด Arduino ด้วย PlatformIO
2. รันสคริปต์ Python ที่ Pi (เช่น `python3 test/test_blower_control.py`)
3. เลือกเมนูเพื่อสั่งงานอุปกรณ์

## Serial Command Format
- `[control]:blower:on` / `off` / `status`
- `[control]:relay:on` / `off` / `status`
- `[control]:actuator:extend` / `retract` / `stop` / `status`

## หมายเหตุ
- ตรวจสอบ serial port ให้ตรงกับที่เชื่อมต่อ Arduino
- หากมี error หรืออุปกรณ์ไม่ตอบสนอง ให้ตรวจสอบ pin mapping และอัปโหลดโค้ดล่าสุด