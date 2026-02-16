#!/usr/bin/env python3
"""
Smart House Energy Management System - Setup Script
Automated setup for AI predictions, database, and API server
"""

import os
import sys
import subprocess
import sqlite3
from datetime import datetime


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def print_step(step_num, text):
    """Print step information"""
    print(f"\n[Step {step_num}] {text}")
    print("-" * 70)


def check_dependencies():
    """Check if required Python packages are installed"""
    print_step(1, "Checking Dependencies")
    
    required = ['pandas', 'numpy', 'sklearn', 'flask', 'flask_cors']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} NOT installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        
        response = input("\nInstall now? (y/n): ").lower()
        if response == 'y':
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
                print("\n✓ All dependencies installed successfully!")
            except subprocess.CalledProcessError:
                print("\n✗ Installation failed. Please install manually.")
                return False
        else:
            print("\n✗ Please install dependencies manually and run setup again.")
            return False
    else:
        print("\n✓ All dependencies satisfied!")
    
    return True


def initialize_database():
    """Initialize SQLite database"""
    print_step(2, "Initializing Database")
    
    db_path = "smart_house.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        print("Creating tables...")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pv_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hour INTEGER,
                irradiance REAL,
                temperature REAL,
                humidity REAL,
                wind_speed REAL,
                predicted_power REAL,
                confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  ✓ pv_predictions table created")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consumption_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hour INTEGER,
                day_of_week INTEGER,
                temperature REAL,
                is_weekend INTEGER,
                predicted_consumption REAL,
                confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  ✓ consumption_predictions table created")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pv_power REAL,
                consumption REAL,
                battery_soc REAL,
                grid_power INTEGER,
                surplus REAL,
                deficit REAL,
                system_efficiency REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp)
            )
        ''')
        print("  ✓ energy_data table created")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                device_id INTEGER,
                status INTEGER,
                power_consumption REAL,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  ✓ device_status table created")
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy_timestamp ON energy_data(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_time ON device_status(device_name, timestamp)')
        print("  ✓ Indexes created")
        
        conn.commit()
        conn.close()
        
        print(f"\n✓ Database initialized: {db_path}")
        return True
        
    except Exception as e:
        print(f"\n✗ Database initialization failed: {e}")
        return False


def train_models():
    """Train AI models"""
    print_step(3, "Training AI Models")
    
    try:
        print("Importing prediction system...")
        from ai_predictions import SmartHousePredictor
        
        predictor = SmartHousePredictor()
        
        print("\nGenerating training data...")
        pv_data, consumption_data = predictor.generate_sample_training_data()
        print(f"  Generated {len(pv_data)} samples")
        
        print("\nTraining PV power prediction model...")
        predictor.train_pv_model(pv_data)
        print("  ✓ PV model trained and saved")
        
        print("\nTraining consumption prediction model...")
        predictor.train_consumption_model(consumption_data)
        print("  ✓ Consumption model trained and saved")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Model training failed: {e}")
        return False


def generate_predictions():
    """Generate initial predictions"""
    print_step(4, "Generating Predictions")
    
    try:
        from ai_predictions import SmartHousePredictor
        
        predictor = SmartHousePredictor()
        
        print("Loading models...")
        predictor.load_models()
        
        print("Generating 24-hour predictions...")
        predictions = predictor.predict_next_24h()
        
        print(f"  Generated {len(predictions)} hourly predictions")
        
        print("Saving to database...")
        predictor.save_predictions_to_db(predictions)
        
        print("Exporting for ESP32...")
        csv_file = predictor.export_for_esp32()
        
        print(f"\n✓ Predictions generated and saved")
        print(f"  Database: smart_house.db")
        print(f"  CSV Export: {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Prediction generation failed: {e}")
        return False


def verify_setup():
    """Verify the setup"""
    print_step(5, "Verifying Setup")
    
    errors = []
    
    # Check files
    required_files = [
        'smart_house.db',
        'pv_model.pkl',
        'consumption_model.pkl',
        'ai_predictions.py',
        'api_server.py'
    ]
    
    print("Checking files...")
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} NOT FOUND")
            errors.append(f"Missing file: {file}")
    
    # Check database
    print("\nChecking database...")
    try:
        conn = sqlite3.connect('smart_house.db')
        cursor = conn.cursor()
        
        # Check record counts
        tables = ['energy_data', 'pv_predictions', 'consumption_predictions']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"  ✓ {table}: {count} records")
            
            if count == 0:
                errors.append(f"No data in {table}")
        
        conn.close()
        
    except Exception as e:
        print(f"  ✗ Database check failed: {e}")
        errors.append(f"Database error: {e}")
    
    if errors:
        print("\n⚠️  Setup completed with warnings:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✓ All checks passed!")
        return True


def print_next_steps():
    """Print next steps for user"""
    print_header("SETUP COMPLETE! 🎉")
    
    print("Your Smart House Energy Management System is ready!")
    print("\nNext Steps:")
    print("\n1. START API SERVER:")
    print("   python api_server.py")
    print("   Then open: http://localhost:5000")
    
    print("\n2. CONFIGURE ESP32:")
    print("   - Open Ems_integrated.cpp in Arduino IDE")
    print("   - Update WiFi credentials:")
    print('     const char* ssid = "YOUR_WIFI_NAME";')
    print('     const char* password = "YOUR_PASSWORD";')
    print("   - Update API server IP:")
    print('     const char* API_SERVER = "http://YOUR_IP:5000";')
    print("   - Install ArduinoJson library")
    print("   - Upload to ESP32")
    
    print("\n3. ACCESS DASHBOARDS:")
    print("   - Web Dashboard: http://localhost:5000")
    print("   - ESP32 Dashboard: http://<ESP32_IP>/")
    
    print("\n4. MONITOR SYSTEM:")
    print("   - Check Serial Monitor for ESP32 logs")
    print("   - Watch web dashboard update every 5 seconds")
    print("   - View predictions in database")
    
    print("\n5. SCHEDULE PREDICTIONS:")
    print("   - Run ai_predictions.py hourly via cron/task scheduler")
    print("   - Linux: crontab -e")
    print("     0 * * * * /path/to/python /path/to/ai_predictions.py")
    print("   - Windows: Task Scheduler")
    
    print("\n" + "="*70)
    print("For detailed instructions, see INTEGRATION_GUIDE.md")
    print("="*70 + "\n")


def main():
    """Main setup routine"""
    print_header("SMART HOUSE ENERGY MANAGEMENT SYSTEM - SETUP")
    
    print("This script will set up your Smart House system:")
    print("  • Install dependencies")
    print("  • Initialize database")
    print("  • Train AI models")
    print("  • Generate predictions")
    print("  • Verify installation")
    
    response = input("\nContinue? (y/n): ").lower()
    if response != 'y':
        print("\nSetup cancelled.")
        return
    
    # Run setup steps
    steps = [
        check_dependencies,
        initialize_database,
        train_models,
        generate_predictions,
        verify_setup
    ]
    
    for step in steps:
        if not step():
            print("\n⚠️  Setup encountered errors.")
            print("Please check the error messages above and try again.")
            return
    
    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
