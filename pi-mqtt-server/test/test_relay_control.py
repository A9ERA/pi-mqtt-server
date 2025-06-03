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
# Import RelayService directly from the file
from services.relay_service import RelayService

def display_menu():
    """Display the test menu"""
    # ... rest of the existing code ... 