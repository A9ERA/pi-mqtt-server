#!/usr/bin/env python3
"""
Test script for ActuatorController
Tests MQTT and Serial communication for actuator control
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch
import paho.mqtt.client as mqtt
import serial

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from actuator_control import ActuatorController

class TestActuatorController(unittest.TestCase):
    """Test cases for ActuatorController"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock MQTT client
        self.mqtt_patcher = patch('paho.mqtt.client.Client')
        self.mock_mqtt = self.mqtt_patcher.start()
        self.mock_mqtt_instance = MagicMock()
        self.mock_mqtt.return_value = self.mock_mqtt_instance
        
        # Mock Serial
        self.serial_patcher = patch('serial.Serial')
        self.mock_serial = self.serial_patcher.start()
        self.mock_serial_instance = MagicMock()
        self.mock_serial.return_value = self.mock_serial_instance
        
        # Create controller instance
        self.controller = ActuatorController(
            mqtt_broker="localhost",
            mqtt_port=1883,
            serial_port="COM3",  # Mock port
            baud_rate=9600
        )
        
    def tearDown(self):
        """Clean up test fixtures"""
        self.mqtt_patcher.stop()
        self.serial_patcher.stop()
        if hasattr(self, 'controller'):
            self.controller.cleanup()
    
    def test_initialization(self):
        """Test controller initialization"""
        self.assertEqual(self.controller.mqtt_broker, "localhost")
        self.assertEqual(self.controller.mqtt_port, 1883)
        self.assertEqual(self.controller.serial_port, "COM3")
        self.assertEqual(self.controller.baud_rate, 9600)
        
        # Check if MQTT client was created
        self.mock_mqtt.assert_called_once()
        
        # Check if Serial was created
        self.mock_serial.assert_called_once_with(
            "COM3", 9600, timeout=2
        )
    
    def test_mqtt_connect(self):
        """Test MQTT connection"""
        # Simulate successful connection
        self.controller._on_mqtt_connect(None, None, None, 0)
        
        # Check if subscribed to all topics
        expected_topics = [
            '[control]/actuator/extend',
            '[control]/actuator/retract',
            '[control]/actuator/stop',
            '[control]/status'
        ]
        
        for topic in expected_topics:
            self.mock_mqtt_instance.subscribe.assert_any_call(topic)
        
        self.assertTrue(self.controller.connected)
    
    def test_mqtt_disconnect(self):
        """Test MQTT disconnection"""
        # Simulate disconnection
        self.controller._on_mqtt_disconnect(None, None, 0)
        self.assertFalse(self.controller.connected)
    
    def test_mqtt_message_handling(self):
        """Test MQTT message handling"""
        # Test extend command
        msg = MagicMock()
        msg.topic = '[control]/actuator/extend'
        msg.payload = b'1'
        self.controller._on_mqtt_message(None, None, msg)
        self.mock_serial_instance.write.assert_called_with(
            b'[control]:actuator:extend\n'
        )
        
        # Test retract command
        msg.topic = '[control]/actuator/retract'
        self.controller._on_mqtt_message(None, None, msg)
        self.mock_serial_instance.write.assert_called_with(
            b'[control]:actuator:retract\n'
        )
        
        # Test stop command
        msg.topic = '[control]/actuator/stop'
        self.controller._on_mqtt_message(None, None, msg)
        self.mock_serial_instance.write.assert_called_with(
            b'[control]:actuator:stop\n'
        )
        
        # Test status command
        msg.topic = '[control]/status'
        self.controller._on_mqtt_message(None, None, msg)
        self.mock_serial_instance.write.assert_called_with(
            b'[control]:status\n'
        )
    
    def test_arduino_command_sending(self):
        """Test sending commands to Arduino"""
        # Mock Arduino response
        self.mock_serial_instance.in_waiting = 1
        self.mock_serial_instance.readline.return_value = b'OK\n'
        
        # Test sending command
        success, response = self.controller._send_arduino_command(
            "[control]:actuator:extend"
        )
        
        self.assertTrue(success)
        self.assertEqual(response, "OK")
        self.mock_serial_instance.write.assert_called_with(
            b'[control]:actuator:extend\n'
        )
        
        # Test publishing response to MQTT
        self.mock_mqtt_instance.publish.assert_called_with(
            '[response]/actuator/status', 'OK'
        )
    
    def test_arduino_no_response(self):
        """Test handling no response from Arduino"""
        # Mock no response
        self.mock_serial_instance.in_waiting = 0
        
        success, response = self.controller._send_arduino_command(
            "[control]:actuator:extend"
        )
        
        self.assertTrue(success)
        self.assertEqual(response, "No response")
    
    def test_serial_error_handling(self):
        """Test handling serial communication errors"""
        # Mock serial error
        self.mock_serial_instance.write.side_effect = serial.SerialException(
            "Test error"
        )
        
        success, response = self.controller._send_arduino_command(
            "[control]:actuator:extend"
        )
        
        self.assertFalse(success)
        self.assertIn("Test error", response)
    
    def test_cleanup(self):
        """Test cleanup of connections"""
        self.controller.cleanup()
        
        # Check if MQTT was cleaned up
        self.mock_mqtt_instance.loop_stop.assert_called_once()
        self.mock_mqtt_instance.disconnect.assert_called_once()
        
        # Check if Serial was cleaned up
        self.mock_serial_instance.close.assert_called_once()

def run_tests():
    """Run the test suite"""
    print("🧪 Running ActuatorController Tests...")
    unittest.main(verbosity=2)

if __name__ == '__main__':
    run_tests() 