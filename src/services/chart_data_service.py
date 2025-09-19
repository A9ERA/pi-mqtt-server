"""
Chart Data Service for handling power flow and battery monitoring data
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

class ChartDataService:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / 'data' / 'history' / 'sensors' / 'power-monitor'
        # Base directory where SensorHistoryService stores per-sensor CSVs
        self.sensors_history_base = Path(__file__).parent.parent / 'data' / 'history' / 'sensors'
        
    def get_power_flow_data(self, date_str):
        """
        Get power flow data for a specific date
        Args:
            date_str: Date in format 'YYYY-MM-DD'
        Returns:
            List of hourly power data with solar generation and feeder consumption
        """
        try:
            # Convert date format from YYYY-MM-DD to DD-MM-YYYY (CSV filename format)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            filename = f"power-monitor_{date_obj.strftime('%d-%m-%Y')}.csv"
            csv_path = self.data_dir / filename
            
            if not csv_path.exists():
                return {
                    'error': f'No data found for date {date_str}',
                    'data': []
                }
            
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calculate solar power (watts) = solarVoltage_V * solarCurrent_A
            df['solarGeneration'] = df['solarVoltage_V']
            
            # Calculate feeder consumption (watts) = loadVoltage_V * loadCurrent_A
            # df['feederConsumption'] = df['loadVoltage_V'] * df['loadCurrent_A']
            
            # Group by hour and take average values
            df['hour'] = df['timestamp'].dt.hour
            hourly_data = df.groupby('hour').agg({
                'solarGeneration': 'mean',
                # 'feederConsumption': 'mean'
            }).reset_index()
            
            # Determine max hour to show
            today = datetime.now().date()
            selected_date = date_obj.date()
            
            # If selected date is today, only show up to current hour
            if selected_date == today:
                max_hour = datetime.now().hour
            else:
                max_hour = 23
            
            # Create hourly data array (up to max_hour)
            result = []
            for hour in range(max_hour + 1):
                time_str = f"{hour:02d}:00"
                
                # Find data for this hour
                hour_data = hourly_data[hourly_data['hour'] == hour]
                
                if not hour_data.empty:
                    solar_gen = round(hour_data.iloc[0]['solarGeneration'], 2)
                    # feeder_cons = round(hour_data.iloc[0]['feederConsumption'], 2)
                else:
                    # No data for this hour, use default values
                    solar_gen = 0.0
                    feeder_cons = 0.0
                
                result.append({
                    'time': time_str,
                    'solarGeneration': solar_gen,
                    # 'feederConsumption': feeder_cons
                })
            
            return {
                'error': None,
                'data': result,
                'date': date_str,
                'total_records': len(df)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'data': []
            }
    
    def get_battery_data(self, date_str):
        """
        Get battery level data for a specific date
        Args:
            date_str: Date in format 'YYYY-MM-DD'
        Returns:
            List of hourly battery percentage data
        """
        try:
            # Convert date format from YYYY-MM-DD to DD-MM-YYYY (CSV filename format)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            filename = f"power-monitor_{date_obj.strftime('%d-%m-%Y')}.csv"
            csv_path = self.data_dir / filename
            
            if not csv_path.exists():
                return {
                    'error': f'No data found for date {date_str}',
                    'data': []
                }
            
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Group by hour and take average battery percentage
            df['hour'] = df['timestamp'].dt.hour
            hourly_data = df.groupby('hour').agg({
                'batteryPercentage_%': 'mean'
            }).reset_index()
            
            # Determine max hour to show
            today = datetime.now().date()
            selected_date = date_obj.date()
            
            # If selected date is today, only show up to current hour
            if selected_date == today:
                max_hour = datetime.now().hour
            else:
                max_hour = 23
            
            # Create hourly data array (up to max_hour)
            result = []
            for hour in range(max_hour + 1):
                time_str = f"{hour:02d}:00"
                
                # Find data for this hour
                hour_data = hourly_data[hourly_data['hour'] == hour]
                
                if not hour_data.empty:
                    battery_level = round(hour_data.iloc[0]['batteryPercentage_%'], 1)
                else:
                    # No data for this hour, use previous hour's data or default
                    if result:
                        battery_level = result[-1]['batteryLevel']
                    else:
                        battery_level = 50.0  # Default value
                
                result.append({
                    'time': time_str,
                    'batteryLevel': battery_level
                })
            
            return {
                'error': None,
                'data': result,
                'date': date_str,
                'total_records': len(df)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'data': []
            }

    def get_sensor_metric_data(self, metric_key: str, date_str: str):
        """
        Get hourly-aggregated metric data for a given metric key and date.

        Args:
            metric_key: One of predefined metric keys
            date_str: Date in format 'YYYY-MM-DD'

        Returns:
            Dict with date, data list [{ time: 'HH:00', value: number }], total_records
        """
        try:
            # Map metric key to sensor dir and CSV column
            metric_map = {
                # Temperatures & humidity
                'feederTemp': {
                    'sensor_dir': 'dht22-feeder',
                    'column': 'temperature_C',
                    'label': 'Feeder Temp',
                },
                'feederHumi': {
                    'sensor_dir': 'dht22-feeder',
                    'column': 'humidity_%',
                    'label': 'Feeder Humidity',
                },
                'systemTemp': {
                    'sensor_dir': 'dht22-system',
                    'column': 'temperature_C',
                    'label': 'System Temp',
                },
                'systemHumi': {
                    'sensor_dir': 'dht22-system',
                    'column': 'humidity_%',
                    'label': 'System Humidity',
                },
                # Food
                'foodMoisture': {
                    'sensor_dir': 'soil-moisture',
                    'column': 'soil_moisture_%',
                    'label': 'Food Moisture',
                },
                'foodWeight': {
                    'sensor_dir': 'hx711-feeder',
                    'column': 'weight_kg',
                    'label': 'Food Weight',
                },
                # Power monitor
                'systemVoltage': {
                    'sensor_dir': 'power-monitor',
                    'column': 'loadVoltage_V',
                    'label': 'System Voltage',
                },
                'systemCurrent': {
                    'sensor_dir': 'power-monitor',
                    'column': 'loadCurrent_A',
                    'label': 'System Current',
                },
                'battery': {
                    'sensor_dir': 'power-monitor',
                    'column': 'batteryPercentage_%',
                    'label': 'Battery',
                },
                'solarVoltage': {
                    'sensor_dir': 'power-monitor',
                    'column': 'solarVoltage_V',
                    'label': 'Solar Voltage',
                },
                'solarCurrent': {
                    'sensor_dir': 'power-monitor',
                    'column': 'solarCurrent_A',
                    'label': 'Solar Current',
                },
            }

            if metric_key not in metric_map:
                return {
                    'error': f'Unsupported metric key: {metric_key}',
                    'data': []
                }

            # Convert date format and build path
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_filename = date_obj.strftime('%d-%m-%Y')
            sensor_dir = self.sensors_history_base / metric_map[metric_key]['sensor_dir']
            csv_filename = f"{metric_map[metric_key]['sensor_dir']}_{date_filename}.csv"
            csv_path = sensor_dir / csv_filename

            if not csv_path.exists():
                return {
                    'error': f'No data found for date {date_str}',
                    'data': []
                }

            # Read CSV
            df = pd.read_csv(csv_path)

            # Require the column to exist
            metric_column = metric_map[metric_key]['column']
            if metric_column not in df.columns:
                return {
                    'error': f'Metric column not found: {metric_column}',
                    'data': []
                }

            # Convert timestamp and aggregate hourly average
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            hourly_data = df.groupby('hour').agg({ metric_column: 'mean' }).reset_index()

            # Limit hours if selected date is today
            today = datetime.now().date()
            selected_date = date_obj.date()
            if selected_date == today:
                max_hour = datetime.now().hour
            else:
                max_hour = 23

            # Build result with continuous hours
            result = []
            for hour in range(max_hour + 1):
                time_str = f"{hour:02d}:00"
                hour_row = hourly_data[hourly_data['hour'] == hour]
                if not hour_row.empty:
                    value = round(float(hour_row.iloc[0][metric_column]), 3)
                else:
                    if result:
                        value = result[-1]['value']
                    else:
                        # Default baseline when no prior value
                        value = 0.0

                result.append({
                    'time': time_str,
                    'value': value
                })

            return {
                'error': None,
                'data': result,
                'date': date_str,
                'total_records': len(df)
            }

        except Exception as e:
            return {
                'error': str(e),
                'data': []
            }
    
    def get_available_dates(self):
        """
        Get list of available dates that have data
        Returns:
            List of available dates in YYYY-MM-DD format
        """
        try:
            dates = []
            for csv_file in self.data_dir.glob('power-monitor_*.csv'):
                # Extract date from filename (power-monitor_DD-MM-YYYY.csv)
                filename = csv_file.stem
                date_part = filename.replace('power-monitor_', '')
                
                # Convert DD-MM-YYYY to YYYY-MM-DD
                try:
                    date_obj = datetime.strptime(date_part, '%d-%m-%Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    dates.append(formatted_date)
                except ValueError:
                    continue
            
            # Sort dates in descending order (newest first)
            dates.sort(reverse=True)
            
            return {
                'error': None,
                'dates': dates
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'dates': []
            } 