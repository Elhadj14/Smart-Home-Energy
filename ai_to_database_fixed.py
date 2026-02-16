"""
Complete Integration System - FIXED VERSION
============================================
Handles different model formats (dict, sklearn model, etc.)
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os

# ============================================================================
# STEP 1: ضع مسار نماذجك هنا
# ============================================================================

PV_MODEL_PATH = 'pv_power_model_ultra.pkl'
CONSUMPTION_MODEL_PATH = 'consumption_hourly_model.pkl'
DATABASE_PATH = 'smart_house.db'

# ============================================================================


class AIModelIntegration:
    """ربط نماذج الذكاء الاصطناعي مع قاعدة البيانات"""
    
    def __init__(self, pv_model_path, consumption_model_path, db_path):
        self.pv_model_path = pv_model_path
        self.consumption_model_path = consumption_model_path
        self.db_path = db_path
        
        # تحميل النماذج
        print("="*70)
        print("STEP 1: Loading AI Models")
        print("="*70)
        self.pv_model = self._load_model(pv_model_path, "PV Power Model")
        self.consumption_model = self._load_model(consumption_model_path, "Consumption Model")
        
        # إنشاء قاعدة البيانات
        print("\n" + "="*70)
        print("STEP 2: Creating Database")
        print("="*70)
        self._create_database()
    
    def _load_model(self, path, name):
        """تحميل نموذج من ملف"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ Model not found: {path}")
        
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"\n✅ {name}")
        print(f"   Path: {path}")
        print(f"   Size: {size_mb:.1f} MB")
        
        model_data = joblib.load(path)
        
        # التعامل مع أنواع مختلفة من النماذج
        if isinstance(model_data, dict):
            print(f"   Type: Dictionary (extracting model)")
            print(f"   Keys found: {list(model_data.keys())}")
            
            # إذا كان dictionary، ابحث عن النموذج داخله
            if 'model' in model_data:
                model = model_data['model']
            elif 'models' in model_data:
                # إذا كان ensemble من نماذج متعددة
                models = model_data['models']
                if isinstance(models, dict):
                    # استخدم أفضل نموذج إذا كان محدد
                    if 'best_model_name' in model_data and model_data['best_model_name'] in models:
                        model = models[model_data['best_model_name']]
                        print(f"   Using best model: {model_data['best_model_name']}")
                    else:
                        # استخدم أول نموذج
                        model = list(models.values())[0]
                        print(f"   Using first model: {list(models.keys())[0]}")
                elif isinstance(models, list):
                    model = models[0]
                else:
                    model = models
            elif 'estimator' in model_data:
                model = model_data['estimator']
            else:
                # استخدم أول قيمة تبدو أنها نموذج
                for key, value in model_data.items():
                    if hasattr(value, 'predict'):
                        model = value
                        break
                else:
                    raise ValueError(f"Could not find model in dictionary. Keys: {list(model_data.keys())}")
        else:
            model = model_data
        
        # تحقق من أن النموذج يعمل
        if not hasattr(model, 'predict'):
            raise ValueError(f"Loaded object does not have 'predict' method. Type: {type(model)}")
        
        print(f"   Status: Loaded successfully")
        print(f"   Model Type: {type(model).__name__}")
        
        return model
    
    def _create_database(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL UNIQUE,
                hour INTEGER,
                pv_power REAL,
                consumption REAL,
                surplus REAL,
                deficit REAL,
                battery_soc REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS current_data (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                pv_power REAL,
                consumption REAL,
                battery_soc REAL,
                grid_power INTEGER,
                system_efficiency REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT,
                status INTEGER,
                power_consumption REAL,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Database created: {self.db_path}")
        print("   Tables: predictions, current_data, devices")
    
    def predict_next_hours(self, hours=24):
        """توليد التوقعات"""
        print("\n" + "="*70)
        print(f"STEP 3: Generating {hours} Hour Predictions")
        print("="*70)
        
        predictions = []
        current_time = datetime.now()
        
        for hour_offset in range(hours):
            pred_time = current_time + timedelta(hours=hour_offset)
            hour = pred_time.hour
            dayofyear = pred_time.timetuple().tm_yday
            day_of_week = pred_time.weekday()
            month = pred_time.month
            is_weekend = 1 if day_of_week >= 5 else 0
            
            # توليد بيانات الطقس (في الإنتاج: استخدم Weather API)
            if 6 <= hour <= 18:
                irradiance = 800 * np.sin((hour - 6) * np.pi / 12)
                irradiance = max(0, irradiance + np.random.uniform(-50, 50))
            else:
                irradiance = 0
            
            temperature = 20 + 10 * np.sin(2 * np.pi * dayofyear / 365)
            temperature += np.random.uniform(-2, 2)
            humidity = np.random.uniform(40, 70)
            wind_speed = np.random.uniform(1, 5)
            
            # ===== PV Prediction =====
            try:
                pv_features = pd.DataFrame([[
                    irradiance, temperature, humidity, wind_speed, hour, dayofyear
                ]], columns=['irradiance', 'temperature', 'humidity', 'wind_speed', 'hour', 'dayofyear'])
                
                pv_power = self.pv_model.predict(pv_features)[0]
                pv_power = max(0, float(pv_power))
            except Exception as e:
                print(f"   ⚠️  PV prediction error (hour {hour}): {e}")
                pv_power = 0
            
            # ===== Consumption Prediction =====
            try:
                cons_features = pd.DataFrame([[
                    hour, day_of_week, month, is_weekend, temperature
                ]], columns=['hour', 'day_of_week', 'month', 'is_weekend', 'temperature'])
                
                consumption = self.consumption_model.predict(cons_features)[0]
                consumption = max(150, float(consumption))
            except Exception as e:
                print(f"   ⚠️  Consumption prediction error (hour {hour}): {e}")
                consumption = 200
            
            # حساب الفائض/العجز
            surplus = max(0, pv_power - consumption)
            deficit = max(0, consumption - pv_power)
            
            predictions.append({
                'timestamp': pred_time.strftime('%Y-%m-%d %H:%M:%S'),
                'hour': hour,
                'pv_power': round(pv_power, 2),
                'consumption': round(consumption, 2),
                'surplus': round(surplus, 2),
                'deficit': round(deficit, 2)
            })
        
        print(f"✅ Generated {len(predictions)} predictions")
        return predictions
    
    def save_to_database(self, predictions):
        """حفظ التوقعات في قاعدة البيانات"""
        print("\n" + "="*70)
        print("STEP 4: Saving to Database")
        print("="*70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        for pred in predictions:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO predictions
                    (timestamp, hour, pv_power, consumption, surplus, deficit, battery_soc)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pred['timestamp'],
                    pred['hour'],
                    pred['pv_power'],
                    pred['consumption'],
                    pred['surplus'],
                    pred['deficit'],
                    70.0
                ))
                saved += 1
            except Exception as e:
                print(f"    ⚠️  Error saving: {e}")
        
        # حفظ البيانات الحالية
        current = predictions[0]
        cursor.execute('''
            INSERT OR REPLACE INTO current_data
            (id, timestamp, pv_power, consumption, battery_soc, grid_power, system_efficiency)
            VALUES (1, ?, ?, ?, ?, ?, ?)
        ''', (
            current['timestamp'],
            current['pv_power'],
            current['consumption'],
            70.0,
            0,
            92.0
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Saved {saved} predictions to database")
        print(f"✅ Updated current data for API")
    
    def display_summary(self, predictions):
        """عرض ملخص"""
        print("\n" + "="*70)
        print("STEP 5: Summary (First 12 Hours)")
        print("="*70)
        print(f"\n{'Time':<20} {'PV (W)':<12} {'Consumption (W)':<18} {'Net (W)':<12}")
        print("-"*70)
        
        for pred in predictions[:12]:
            net = pred['pv_power'] - pred['consumption']
            status = "SURPLUS" if net > 0 else "DEFICIT"
            print(f"{pred['timestamp']:<20} {pred['pv_power']:<12.1f} {pred['consumption']:<18.1f} {net:<12.1f} {status}")
    
    def get_data_for_api(self):
        """الحصول على البيانات للـ API"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM current_data WHERE id = 1')
        current = cursor.fetchone()
        
        cursor.execute('''
            SELECT timestamp, pv_power, consumption, surplus, deficit
            FROM predictions
            ORDER BY timestamp DESC
            LIMIT 24
        ''')
        forecast = cursor.fetchall()
        
        conn.close()
        
        return {
            'current': {
                'timestamp': current[1],
                'pv_power': current[2],
                'consumption': current[3],
                'battery_soc': current[4],
                'grid_power': current[5],
                'efficiency': current[6]
            },
            'forecast': [
                {
                    'timestamp': row[0],
                    'pv_power': row[1],
                    'consumption': row[2],
                    'surplus': row[3],
                    'deficit': row[4]
                }
                for row in forecast
            ]
        }
    
    def run_integration(self):
        """تشغيل العملية الكاملة"""
        # التنبؤ
        predictions = self.predict_next_hours(hours=24)
        
        # الحفظ
        self.save_to_database(predictions)
        
        # العرض
        self.display_summary(predictions)
        
        # البيانات للـ API
        api_data = self.get_data_for_api()
        
        print("\n" + "="*70)
        print("✅ INTEGRATION COMPLETE")
        print("="*70)
        print(f"\n📊 Current Data for API:")
        print(f"   PV Power: {api_data['current']['pv_power']:.1f} W")
        print(f"   Consumption: {api_data['current']['consumption']:.1f} W")
        print(f"   Battery: {api_data['current']['battery_soc']:.1f}%")
        print(f"   Efficiency: {api_data['current']['efficiency']:.1f}%")
        
        print(f"\n📁 Database: {self.db_path}")
        print(f"   - predictions table: 24 rows")
        print(f"   - current_data table: 1 row (for API)")
        
        print("\n🚀 Next Steps:")
        print("   1. Run API server: python api_server_integrated.py")
        print("   2. Open browser: http://localhost:5000")
        print("   3. ESP32 will fetch from API automatically")
        
        return api_data


def main():
    """البرنامج الرئيسي"""
    print("\n" + "="*70)
    print("AI MODELS → DATABASE → API INTEGRATION")
    print("="*70)
    print("\nModels:")
    print(f"  PV: {PV_MODEL_PATH}")
    print(f"  Consumption: {CONSUMPTION_MODEL_PATH}")
    print(f"\nDatabase: {DATABASE_PATH}")
    print("="*70)
    
    # إنشاء النظام
    integration = AIModelIntegration(
        pv_model_path=PV_MODEL_PATH,
        consumption_model_path=CONSUMPTION_MODEL_PATH,
        db_path=DATABASE_PATH
    )
    
    # تشغيل
    integration.run_integration()


if __name__ == "__main__":
    main()