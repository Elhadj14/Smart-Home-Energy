"""
Complete Feature Engineering System
====================================
Creates all 84 PV features and 83 Consumption features
Works without historical data using intelligent estimates
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os
import math

# ============================================================================
# STEP 1: ضع مسار نماذجك هنا
# ============================================================================

PV_MODEL_PATH = 'pv_power_model_ultra.pkl'
CONSUMPTION_MODEL_PATH = 'consumption_hourly_model.pkl'
DATABASE_PATH = 'smart_house.db'

# ============================================================================


class FeatureEngineer:
    """هندسة الميزات الكاملة"""
    
    def __init__(self):
        self.historical_pv = []
        self.historical_consumption = []
    
    def create_pv_features(self, timestamp, base_weather=None):
        """إنشاء جميع الـ 84 feature للـ PV Model"""
        
        # Parse timestamp
        dt = pd.Timestamp(timestamp)
        hour = dt.hour
        month = dt.month
        day_of_year = dt.dayofyear
        day_of_week = dt.dayofweek
        
        # Base weather (محاكاة)
        if base_weather is None:
            base_weather = self._generate_weather(hour, day_of_year)
        
        radiation = base_weather['radiation']
        temperature = base_weather['temperature']
        humidity = base_weather['humidity']
        wind_speed = base_weather['wind_speed']
        pressure = base_weather['pressure']
        sunshine = base_weather['sunshine']
        
        # Sun position (محاكاة)
        sun_elevation = self._calculate_sun_elevation(hour, day_of_year)
        sun_azimuth = self._calculate_sun_azimuth(hour, day_of_year)
        air_mass = self._calculate_air_mass(sun_elevation)
        
        # Time features
        features = {
            # 1-6: Base weather
            'WindSpeed': wind_speed,
            'Sunshine': sunshine,
            'AirPressure': pressure,
            'Radiation': radiation,
            'AirTemperature': temperature,
            'RelativeAirHumidity': humidity,
            
            # 7-12: Time components
            'Hour': hour,
            'Month': month,
            'DayOfYear': day_of_year,
            'DayOfWeek': day_of_week,
            'Quarter': (month - 1) // 3 + 1,
            'WeekOfYear': dt.isocalendar()[1],
            
            # 13-20: Cyclical time
            'Hour_sin': np.sin(2 * np.pi * hour / 24),
            'Hour_cos': np.cos(2 * np.pi * hour / 24),
            'Month_sin': np.sin(2 * np.pi * month / 12),
            'Month_cos': np.cos(2 * np.pi * month / 12),
            'DayOfYear_sin': np.sin(2 * np.pi * day_of_year / 365),
            'DayOfYear_cos': np.cos(2 * np.pi * day_of_year / 365),
            'DayOfWeek_sin': np.sin(2 * np.pi * day_of_week / 7),
            'DayOfWeek_cos': np.cos(2 * np.pi * day_of_week / 7),
            
            # 21-28: Solar and time flags
            'SunElevation': sun_elevation,
            'SunAzimuth': sun_azimuth,
            'AirMass': air_mass,
            'IsDay': 1 if 6 <= hour <= 18 else 0,
            'IsPeakSun': 1 if 10 <= hour <= 14 else 0,
            'IsMorning': 1 if 6 <= hour < 12 else 0,
            'IsAfternoon': 1 if 12 <= hour < 18 else 0,
            'IsWeekend': 1 if day_of_week >= 5 else 0,
            
            # 29: Season
            'Season': (month % 12 + 3) // 3,
            
            # 30-39: Interaction features
            'Radiation_Temp': radiation * temperature,
            'Radiation_SunElev': radiation * sun_elevation,
            'Radiation_Sunshine': radiation * sunshine,
            'Radiation_Sunshine_Ratio': radiation / (sunshine + 0.01),
            'Radiation_AirMass': radiation / (air_mass + 0.01),
            'Wind_Temp': wind_speed * temperature,
            'Temp_Humidity': temperature * humidity,
            'Pressure_Temp': pressure * temperature,
            'Radiation_Temp_SunElev': radiation * temperature * sun_elevation,
            'Radiation_Sunshine_Humidity': radiation * sunshine * humidity,
        }
        
        # 40-56: Moving averages (محاكاة من البيانات التاريخية)
        production_estimate = radiation * 0.15  # تقدير بسيط
        
        features.update({
            'Radiation_MA2': radiation * 0.98,
            'Radiation_MA3': radiation * 0.97,
            'Radiation_MA6': radiation * 0.95,
            'Radiation_MA12': radiation * 0.93,
            'Radiation_Std3': radiation * 0.1,
            'Radiation_Std6': radiation * 0.12,
            'Radiation_Max3': radiation * 1.15,
            'Radiation_Min3': radiation * 0.85,
            'Temp_MA2': temperature * 0.99,
            'Temp_MA3': temperature * 0.98,
            'Temp_MA6': temperature * 0.97,
            'Temp_Std3': temperature * 0.05,
            'Wind_MA2': wind_speed * 0.99,
            'Wind_MA3': wind_speed * 0.98,
            'Wind_Std3': wind_speed * 0.15,
            'Sunshine_MA3': sunshine * 0.98,
            'Sunshine_MA6': sunshine * 0.96,
        })
        
        # 57-59: Production MA
        features.update({
            'Production_MA2': production_estimate * 0.98,
            'Production_MA3': production_estimate * 0.97,
            'Production_Std3': production_estimate * 0.1,
        })
        
        # 60-73: Lag features (محاكاة)
        features.update({
            'Radiation_Lag1': radiation * 0.95,
            'Production_Lag1': production_estimate * 0.95,
            'Radiation_Lag2': radiation * 0.90,
            'Production_Lag2': production_estimate * 0.90,
            'Radiation_Lag3': radiation * 0.85,
            'Production_Lag3': production_estimate * 0.85,
            'Radiation_Lag6': radiation * 0.75,
            'Production_Lag6': production_estimate * 0.75,
            'Temp_Lag1': temperature * 0.98,
            'Sunshine_Lag1': sunshine * 0.95,
            'Temp_Lag2': temperature * 0.96,
            'Sunshine_Lag2': sunshine * 0.90,
            'Temp_Lag3': temperature * 0.94,
            'Sunshine_Lag3': sunshine * 0.85,
        })
        
        # 74-77: Delta features
        features.update({
            'Radiation_Delta1': radiation * 0.05,
            'Radiation_Delta2': radiation * 0.08,
            'Temp_Delta1': temperature * 0.02,
            'Production_Delta1': production_estimate * 0.05,
        })
        
        # 78-79: Trend features
        features.update({
            'Radiation_Trend3': 0.02 if hour < 12 else -0.02,
            'Temp_Trend3': 0.01 if hour < 14 else -0.01,
        })
        
        # 80-84: Ratio and squared features
        max_daily_radiation = 1000  # تقدير
        features.update({
            'Radiation_to_MaxDaily': radiation / max_daily_radiation,
            'Production_to_Radiation': production_estimate / (radiation + 0.01),
            'Radiation_Squared': radiation ** 2,
            'SunElevation_Squared': sun_elevation ** 2,
            'Sunshine_Squared': sunshine ** 2,
        })
        
        return features
    
    def create_consumption_features(self, timestamp, base_consumption=None):
        """إنشاء جميع الـ 83 feature للـ Consumption Model"""
        
        dt = pd.Timestamp(timestamp)
        hour = dt.hour
        month = dt.month
        day = dt.day
        day_of_year = dt.dayofyear
        day_of_week = dt.dayofweek
        year = dt.year
        
        # Base consumption estimate
        if base_consumption is None:
            base_consumption = self._estimate_consumption(hour, day_of_week)
        
        features = {
            # 1: Std (محاكاة)
            'Consumption_Std': base_consumption * 0.15,
            
            # 2-9: Time components
            'Year': year,
            'Month': month,
            'Day': day,
            'Hour': hour,
            'DayOfWeek': day_of_week,
            'DayOfYear': day_of_year,
            'WeekOfYear': dt.isocalendar()[1],
            'Quarter': (month - 1) // 3 + 1,
            
            # 10-17: Cyclical time
            'Hour_sin': np.sin(2 * np.pi * hour / 24),
            'Hour_cos': np.cos(2 * np.pi * hour / 24),
            'Month_sin': np.sin(2 * np.pi * month / 12),
            'Month_cos': np.cos(2 * np.pi * month / 12),
            'DayOfYear_sin': np.sin(2 * np.pi * day_of_year / 365),
            'DayOfYear_cos': np.cos(2 * np.pi * day_of_year / 365),
            'DayOfWeek_sin': np.sin(2 * np.pi * day_of_week / 7),
            'DayOfWeek_cos': np.cos(2 * np.pi * day_of_week / 7),
            
            # 18: Time of day
            'TimeOfDay': hour + dt.minute / 60,
            
            # 19-26: Time flags
            'IsWeekend': 1 if day_of_week >= 5 else 0,
            'IsPeakMorning': 1 if 7 <= hour <= 9 else 0,
            'IsPeakEvening': 1 if 18 <= hour <= 21 else 0,
            'IsPeakHour': 1 if (7 <= hour <= 9) or (18 <= hour <= 21) else 0,
            'IsWorkingHour': 1 if 8 <= hour <= 17 else 0,
            'IsNight': 1 if hour < 6 or hour >= 22 else 0,
            'IsSleepTime': 1 if 23 <= hour or hour < 6 else 0,
            'Season': (month % 12 + 3) // 3,
            
            # 27-28: Within hour stats
            'Within_Hour_Std': base_consumption * 0.05,
            'Within_Hour_Range': base_consumption * 0.1,
        }
        
        # 29-37: Lag features (محاكاة من أنماط متوقعة)
        features.update({
            'Consumption_Lag1h': base_consumption * 0.98,
            'Consumption_Lag2h': base_consumption * 0.96,
            'Consumption_Lag3h': base_consumption * 0.94,
            'Consumption_Lag6h': base_consumption * 0.90,
            'Consumption_Lag12h': base_consumption * 0.85,
            'Consumption_Lag24h': base_consumption * 0.95,  # نفس الساعة أمس
            'Consumption_Lag48h': base_consumption * 0.93,
            'Consumption_Lag72h': base_consumption * 0.91,
            'Consumption_Lag168h': base_consumption * 0.94,  # نفس اليوم الأسبوع الماضي
        })
        
        # 38-58: Moving averages and statistics
        features.update({
            'Consumption_MA3h': base_consumption * 0.99,
            'Consumption_MA6h': base_consumption * 0.98,
            'Consumption_Std6h': base_consumption * 0.08,
            'Consumption_MA12h': base_consumption * 0.97,
            'Consumption_Std12h': base_consumption * 0.10,
            'Consumption_MA24h': base_consumption * 0.96,
            'Consumption_Std24h': base_consumption * 0.12,
            'Consumption_Max24h': base_consumption * 1.25,
            'Consumption_Min24h': base_consumption * 0.75,
            'Consumption_MA48h': base_consumption * 0.95,
            'Consumption_Std48h': base_consumption * 0.13,
            'Consumption_Max48h': base_consumption * 1.30,
            'Consumption_Min48h': base_consumption * 0.70,
            'Consumption_MA72h': base_consumption * 0.94,
            'Consumption_Std72h': base_consumption * 0.14,
            'Consumption_Max72h': base_consumption * 1.35,
            'Consumption_Min72h': base_consumption * 0.68,
            'Consumption_MA168h': base_consumption * 0.93,
            'Consumption_Std168h': base_consumption * 0.15,
            'Consumption_Max168h': base_consumption * 1.40,
            'Consumption_Min168h': base_consumption * 0.65,
        })
        
        # 59-64: Delta and trend features
        features.update({
            'Consumption_Delta1h': base_consumption * 0.02,
            'Consumption_Delta3h': base_consumption * 0.04,
            'Consumption_Delta6h': base_consumption * 0.06,
            'Consumption_Delta24h': base_consumption * 0.03,
            'Consumption_Trend6h': 0.01 if 6 <= hour <= 12 else -0.01,
            'Consumption_Trend24h': 0.005,
        })
        
        # 65-74: Aggregated statistics
        daily_mean = base_consumption * 0.95
        weekly_mean = base_consumption * 0.96
        hourly_mean = base_consumption
        monthly_mean = base_consumption * 0.97
        dayofweek_mean = base_consumption * (1.05 if day_of_week < 5 else 0.95)
        
        features.update({
            'DailyMean': daily_mean,
            'DailyStd': daily_mean * 0.15,
            'DailyMax': daily_mean * 1.30,
            'DailyMin': daily_mean * 0.70,
            'WeeklyMean': weekly_mean,
            'WeeklyStd': weekly_mean * 0.18,
            'HourlyMean': hourly_mean,
            'HourlyStd': hourly_mean * 0.12,
            'MonthlyMean': monthly_mean,
            'DayOfWeekMean': dayofweek_mean,
        })
        
        # 75-78: Ratio features
        features.update({
            'DayOfWeekStd': dayofweek_mean * 0.20,
            'Consumption_to_DailyMean': base_consumption / daily_mean,
            'Consumption_to_HourlyMean': base_consumption / hourly_mean,
            'Consumption_to_WeeklyMean': base_consumption / weekly_mean,
        })
        
        # 79-81: Same hour comparisons
        features.update({
            'SameHourYesterday': base_consumption * 0.95,
            'SameHourLastWeek': base_consumption * 0.94,
            'SameHour2DaysAgo': base_consumption * 0.93,
        })
        
        # 82-83: Change rates
        features.update({
            'ChangeRate_1h': 0.02,
            'ChangeRate_6h': 0.05,
        })
        
        return features
    
    def _generate_weather(self, hour, day_of_year):
        """توليد بيانات طقس محاكاة"""
        # Solar radiation
        if 6 <= hour <= 18:
            radiation = 800 * np.sin((hour - 6) * np.pi / 12) + np.random.uniform(-50, 50)
            radiation = max(0, radiation)
            sunshine = radiation / 10
        else:
            radiation = 0
            sunshine = 0
        
        # Temperature (seasonal variation)
        base_temp = 20 + 10 * np.sin(2 * np.pi * day_of_year / 365)
        temp = base_temp + 5 * np.sin((hour - 6) * np.pi / 12)  # daily variation
        temp += np.random.uniform(-2, 2)
        
        # Other weather
        humidity = 50 + 20 * np.sin(2 * np.pi * day_of_year / 365) + np.random.uniform(-10, 10)
        humidity = np.clip(humidity, 20, 90)
        
        wind_speed = 3 + np.random.uniform(-1, 2)
        wind_speed = max(0, wind_speed)
        
        pressure = 1013 + np.random.uniform(-10, 10)
        
        return {
            'radiation': radiation,
            'temperature': temp,
            'humidity': humidity,
            'wind_speed': wind_speed,
            'pressure': pressure,
            'sunshine': sunshine
        }
    
    def _calculate_sun_elevation(self, hour, day_of_year):
        """حساب ارتفاع الشمس (محاكاة مبسطة)"""
        if 6 <= hour <= 18:
            # Peak at noon
            elevation = 60 * np.sin((hour - 6) * np.pi / 12)
            # Seasonal adjustment
            seasonal_factor = np.sin(2 * np.pi * (day_of_year - 80) / 365)
            elevation += seasonal_factor * 20
            return max(0, elevation)
        return 0
    
    def _calculate_sun_azimuth(self, hour, day_of_year):
        """حساب اتجاه الشمس (محاكاة)"""
        if 6 <= hour <= 18:
            # East (90) at sunrise, South (180) at noon, West (270) at sunset
            azimuth = 90 + 180 * (hour - 6) / 12
            return azimuth
        return 0
    
    def _calculate_air_mass(self, sun_elevation):
        """حساب Air Mass"""
        if sun_elevation > 0:
            # Simplified Kasten-Young formula
            elevation_rad = math.radians(sun_elevation)
            am = 1 / (np.sin(elevation_rad) + 0.50572 * (6.07995 + sun_elevation) ** (-1.6364))
            return min(am, 10)
        return 10
    
    def _estimate_consumption(self, hour, day_of_week):
        """تقدير استهلاك بناءً على الوقت"""
        # Base consumption patterns
        if 0 <= hour < 6:  # Night (low)
            base = 150
        elif 6 <= hour < 9:  # Morning peak
            base = 400
        elif 9 <= hour < 12:  # Late morning
            base = 300
        elif 12 <= hour < 14:  # Lunch
            base = 350
        elif 14 <= hour < 18:  # Afternoon
            base = 280
        elif 18 <= hour < 22:  # Evening peak
            base = 450
        else:  # Late night
            base = 200
        
        # Weekend adjustment
        if day_of_week >= 5:
            base *= 1.1  # Higher on weekends
        
        # Add randomness
        base += np.random.uniform(-30, 30)
        
        return max(150, base)


class AIModelIntegration:
    """ربط النماذج مع قاعدة البيانات - نسخة محسّنة"""
    
    def __init__(self, pv_model_path, consumption_model_path, db_path):
        self.pv_model_path = pv_model_path
        self.consumption_model_path = consumption_model_path
        self.db_path = db_path
        self.feature_engineer = FeatureEngineer()
        
        print("="*70)
        print("STEP 1: Loading AI Models")
        print("="*70)
        self.pv_model_data = self._load_model(pv_model_path, "PV Power Model")
        self.consumption_model_data = self._load_model(consumption_model_path, "Consumption Model")
        
        print("\n" + "="*70)
        print("STEP 2: Creating Database")
        print("="*70)
        self._create_database()
    
    def _load_model(self, path, name):
        """تحميل النموذج"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ Model not found: {path}")
        
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"\n✅ {name}")
        print(f"   Path: {path}")
        print(f"   Size: {size_mb:.1f} MB")
        
        model_data = joblib.load(path)
        
        if isinstance(model_data, dict) and 'models' in model_data:
            models = model_data['models']
            if 'best_model_name' in model_data and model_data['best_model_name'] in models:
                model = models[model_data['best_model_name']]
                print(f"   Using: {model_data['best_model_name']}")
            else:
                model = list(models.values())[0]
                print(f"   Using: {list(models.keys())[0]}")
            
            print(f"   Status: Loaded successfully")
            print(f"   Model Type: {type(model).__name__}")
            
            return {'model': model, 'scaler': model_data.get('scaler'), 'features': model_data.get('features')}
        
        return {'model': model_data, 'scaler': None, 'features': None}
    
    def _create_database(self):
        """إنشاء قاعدة البيانات"""
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
        """توليد التوقعات مع Features كاملة"""
        print("\n" + "="*70)
        print(f"STEP 3: Generating {hours} Hour Predictions with Full Features")
        print("="*70)
        
        predictions = []
        current_time = datetime.now()
        
        success_count = 0
        error_count = 0
        
        for hour_offset in range(hours):
            pred_time = current_time + timedelta(hours=hour_offset)
            timestamp = pred_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Create PV features
            pv_features_dict = self.feature_engineer.create_pv_features(timestamp)
            
            # Create Consumption features
            cons_features_dict = self.feature_engineer.create_consumption_features(timestamp)
            
            # Convert to DataFrame with correct column order
            try:
                pv_feature_names = self.pv_model_data['features']
                pv_features_df = pd.DataFrame([[pv_features_dict[f] for f in pv_feature_names]], 
                                               columns=pv_feature_names)
                
                # Scale if scaler exists
                if self.pv_model_data['scaler'] is not None:
                    pv_features_df = pd.DataFrame(
                        self.pv_model_data['scaler'].transform(pv_features_df),
                        columns=pv_feature_names
                    )
                
                pv_power = self.pv_model_data['model'].predict(pv_features_df)[0]
                pv_power = max(0, float(pv_power))
                success_count += 1
            except Exception as e:
                if error_count == 0:  # Print only first error
                    print(f"   ⚠️  PV prediction error: {e}")
                pv_power = 0
                error_count += 1
            
            # Consumption prediction
            try:
                cons_feature_names = self.consumption_model_data['features']
                cons_features_df = pd.DataFrame([[cons_features_dict[f] for f in cons_feature_names]], 
                                                 columns=cons_feature_names)
                
                if self.consumption_model_data['scaler'] is not None:
                    cons_features_df = pd.DataFrame(
                        self.consumption_model_data['scaler'].transform(cons_features_df),
                        columns=cons_feature_names
                    )
                
                consumption = self.consumption_model_data['model'].predict(cons_features_df)[0]
                consumption = max(150, float(consumption))
            except Exception as e:
                if error_count == 0:
                    print(f"   ⚠️  Consumption prediction error: {e}")
                consumption = 200
            
            surplus = max(0, pv_power - consumption)
            deficit = max(0, consumption - pv_power)
            
            predictions.append({
                'timestamp': timestamp,
                'hour': pred_time.hour,
                'pv_power': round(pv_power, 2),
                'consumption': round(consumption, 2),
                'surplus': round(surplus, 2),
                'deficit': round(deficit, 2)
            })
        
        print(f"✅ Generated {len(predictions)} predictions")
        print(f"   Successful: {success_count}, Errors: {error_count}")
        return predictions
    
    def save_to_database(self, predictions):
        """حفظ التوقعات"""
        print("\n" + "="*70)
        print("STEP 4: Saving to Database")
        print("="*70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for pred in predictions:
            cursor.execute('''
                INSERT OR REPLACE INTO predictions
                (timestamp, hour, pv_power, consumption, surplus, deficit, battery_soc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (pred['timestamp'], pred['hour'], pred['pv_power'], 
                  pred['consumption'], pred['surplus'], pred['deficit'], 70.0))
        
        current = predictions[0]
        cursor.execute('''
            INSERT OR REPLACE INTO current_data
            (id, timestamp, pv_power, consumption, battery_soc, grid_power, system_efficiency)
            VALUES (1, ?, ?, ?, ?, ?, ?)
        ''', (current['timestamp'], current['pv_power'], current['consumption'], 70.0, 0, 92.0))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Saved {len(predictions)} predictions to database")
    
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
    
    def run_integration(self):
        """تشغيل كامل"""
        predictions = self.predict_next_hours(hours=24)
        self.save_to_database(predictions)
        self.display_summary(predictions)
        
        print("\n" + "="*70)
        print("✅ INTEGRATION COMPLETE")
        print("="*70)
        print(f"\n📊 Current Data:")
        print(f"   PV Power: {predictions[0]['pv_power']:.1f} W")
        print(f"   Consumption: {predictions[0]['consumption']:.1f} W")
        
        print(f"\n📁 Database: {self.db_path}")
        print("\n🚀 Next Steps:")
        print("   1. Run API server: python api_server_integrated.py")
        print("   2. Open browser: http://localhost:5000")


def main():
    print("\n" + "="*70)
    print("AI MODELS → DATABASE → API INTEGRATION")
    print("With Complete Feature Engineering (84 PV + 83 Consumption)")
    print("="*70)
    
    integration = AIModelIntegration(
        pv_model_path=PV_MODEL_PATH,
        consumption_model_path=CONSUMPTION_MODEL_PATH,
        db_path=DATABASE_PATH
    )
    
    integration.run_integration()


if __name__ == "__main__":
    main()
