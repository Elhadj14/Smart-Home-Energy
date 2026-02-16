# Smart House Energy Management System
## Complete Integration Guide

This system integrates AI predictions, database storage, ESP32 control, and web visualization.

---

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SMART HOUSE SYSTEM                       │
└─────────────────────────────────────────────────────────────┘

┌───────────────┐       ┌──────────────┐       ┌─────────────┐
│  AI MODELS    │ ────> │   DATABASE   │ ────> │    ESP32    │
│  (Python)     │       │   (SQLite)   │       │   (C++)     │
└───────────────┘       └──────────────┘       └─────────────┘
       │                       │                       │
       │                       │                       │
       │                ┌──────▼────────┐             │
       │                │  API SERVER   │◄────────────┘
       │                │   (Flask)     │
       │                └──────┬────────┘
       │                       │
       └───────────────────────┼───────────────┐
                               │               │
                        ┌──────▼──────┐ ┌──────▼──────┐
                        │ WEB DASHBOARD│ │ESP32 WEBPAGE│
                        │  (Browser)   │ │  (Browser)  │
                        └─────────────┘ └─────────────┘
```

---

## 🚀 Quick Start (5 Steps)

### Step 1: Install Python Dependencies
```bash
pip install pandas numpy scikit-learn flask flask-cors
```

### Step 2: Generate AI Predictions and Database
```bash
python ai_predictions.py
```

This will:
- Generate sample training data (1 year of hourly data)
- Train PV power prediction model
- Train consumption prediction model
- Generate 24-hour predictions
- Save everything to `smart_house.db` database
- Create CSV export for ESP32

**Expected Output:**
```
INFO - Database initialized: smart_house.db
INFO - Generating sample training data...
INFO - Generated 8760 samples of training data
INFO - Training PV prediction model...
INFO - PV Model - Train R²: 0.9543, Test R²: 0.9421
INFO - Training consumption prediction model...
INFO - Consumption Model - Train R²: 0.9678, Test R²: 0.9512
INFO - Generating 24-hour predictions...
INFO - Saved 24 predictions to database
```

### Step 3: Start API Server
```bash
python api_server.py
```

This starts the Flask server that:
- Serves data to ESP32 via REST API
- Provides web dashboard
- Accepts status updates from ESP32

**Expected Output:**
```
============================================================
SMART HOUSE API SERVER
============================================================

Starting Flask server...
ESP32 API endpoint: http://localhost:5000/api/current_prediction
Web Dashboard: http://localhost:5000/

* Running on http://0.0.0.0:5000/
```

**Keep this terminal running!**

### Step 4: Configure ESP32
1. Open `Ems_integrated.cpp` in Arduino IDE
2. Update WiFi credentials:
   ```cpp
   const char* ssid = "YOUR_WIFI_NAME";
   const char* password = "YOUR_PASSWORD";
   ```
3. Update API server IP (find your computer's IP):
   ```cpp
   const char* API_SERVER = "http://192.168.1.100:5000";
   ```
4. Install required libraries:
   - WiFi (built-in)
   - WebServer (built-in)
   - HTTPClient (built-in)
   - ArduinoJson (Library Manager)

5. Upload to ESP32

### Step 5: Access Dashboards

**Web Dashboard (Computer):**
```
http://localhost:5000/
```

**ESP32 Dashboard:**
```
http://<ESP32_IP_ADDRESS>/
```
(Find ESP32 IP in Serial Monitor after upload)

---

## 📁 File Structure

```
smart-house/
├── ai_predictions.py          # AI models and prediction system
├── api_server.py              # Flask API server
├── Ems_integrated.cpp         # ESP32 firmware
├── smart_house.db            # SQLite database (auto-created)
├── pv_model.pkl              # Trained PV model (auto-created)
├── consumption_model.pkl      # Trained consumption model (auto-created)
└── esp32_data.csv            # CSV export for ESP32 (auto-created)
```

---

## 🔄 System Workflow

### 1. AI Prediction System (`ai_predictions.py`)

**What it does:**
- Trains machine learning models for PV power and consumption prediction
- Generates 24-hour ahead forecasts every hour
- Stores predictions in SQLite database
- Exports data for ESP32

**Key Functions:**
```python
predictor = SmartHousePredictor()

# Train models (first time only)
pv_data, consumption_data = predictor.generate_sample_training_data()
predictor.train_pv_model(pv_data)
predictor.train_consumption_model(consumption_data)

# Generate predictions
predictions = predictor.predict_next_24h()
predictor.save_predictions_to_db(predictions)

# Export for ESP32
predictor.export_for_esp32()
```

**Database Tables Created:**
- `pv_predictions` - PV power forecasts
- `consumption_predictions` - Consumption forecasts
- `energy_data` - Combined energy management data
- `device_status` - Device on/off status and power usage

### 2. API Server (`api_server.py`)

**Endpoints:**

| Endpoint | Method | Purpose | Used By |
|----------|--------|---------|---------|
| `/` | GET | Web dashboard | Browser |
| `/api/current_prediction` | GET | Get current hour data | ESP32 |
| `/api/forecast/24` | GET | Get 24h forecast | Web/ESP32 |
| `/api/update_status` | POST | Update system status | ESP32 |
| `/api/device_status` | GET | Get device states | Web |
| `/api/statistics` | GET | Get system stats | Web |

**Example API Call (from ESP32):**
```cpp
HTTPClient http;
http.begin("http://192.168.1.100:5000/api/current_prediction");
int httpCode = http.GET();
String payload = http.getString();
// Parse JSON and use data
```

### 3. ESP32 Firmware (`Ems_integrated.cpp`)

**What it does:**
- Fetches predictions from API server every minute
- Implements energy management algorithm
- Controls 6 devices + water heater via relays
- Manages battery charging/discharging
- Decides when to use grid power
- Provides web interface for monitoring
- Sends status updates back to database

**Energy Management Logic:**
```cpp
If (PV Power > Consumption):
    - Use PV directly (0% loss)
    - Charge battery (12% loss)
    - Turn on water heater if battery full
    - Grid OFF
Else:
    - Use remaining PV
    - Discharge battery (10% loss)
    - Use grid if battery < 20%
    - Turn off non-essential devices
```

**Device Priority:**
1. **Always ON:** Fridge, Router (critical)
2. **Time-based:** Lights (off during day)
3. **Load-based:** Heater, Washing Machine (when surplus)
4. **Battery-dependent:** AC (only if battery > 50%)

### 4. Web Dashboards

**Main Dashboard (Flask):**
- Real-time PV power, consumption, battery, grid status
- 24-hour forecast chart
- Device status cards
- Auto-refresh every 5 seconds

**ESP32 Dashboard:**
- Current system status
- All device states
- System efficiency
- Predictions vs actual

---

## 🔧 Configuration Options

### AI Predictions Configuration

**Modify prediction interval:**
```python
# In ai_predictions.py
def predict_next_24h(self, current_time=None, hours=24):
    # Change hours to 48 for 48-hour forecast
```

**Adjust model parameters:**
```python
self.pv_model = RandomForestRegressor(
    n_estimators=200,  # Increase for better accuracy (slower)
    max_depth=20,      # Increase for more complex patterns
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)
```

### ESP32 Configuration

**Change update frequency:**
```cpp
const unsigned long API_INTERVAL = 60000;  // milliseconds (60000 = 1 minute)
```

**Adjust battery parameters:**
```cpp
float batteryCapacity = 10000;      // Wh (10 kWh)
float maxBatteryPower = 3000;       // W (max charge/discharge)
float batterySOC = 70;              // % (starting state of charge)
```

**Modify device priorities:**
```cpp
// In applyDeviceControl()
devices[0] = true;   // Fridge - always on
devices[2] = !isDaytime();  // Lights - off during day

// Add custom logic:
if (batterySOC > 80 && availablePower > 2000) {
    devices[5] = true;  // Turn on AC only when conditions met
}
```

### API Server Configuration

**Change port:**
```python
# In api_server.py
app.run(host='0.0.0.0', port=8080, debug=True)
```

**Add authentication:**
```python
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if auth != 'Bearer YOUR_SECRET_TOKEN':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/current_prediction')
@require_auth
def get_current_prediction():
    # Your code here
```

---

## 📊 Database Schema

### Table: `energy_data`
```sql
CREATE TABLE energy_data (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL UNIQUE,
    pv_power REAL,              -- W
    consumption REAL,            -- W
    battery_soc REAL,           -- %
    grid_power INTEGER,         -- 0=OFF, 1=ON
    surplus REAL,               -- W
    deficit REAL,               -- W
    system_efficiency REAL      -- %
);
```

### Table: `device_status`
```sql
CREATE TABLE device_status (
    id INTEGER PRIMARY KEY,
    device_name TEXT NOT NULL,
    device_id INTEGER,
    status INTEGER,             -- 0=OFF, 1=ON
    power_consumption REAL,     -- W
    timestamp TEXT NOT NULL
);
```

---

## 🧪 Testing

### Test API Server
```bash
# Test current prediction endpoint
curl http://localhost:5000/api/current_prediction

# Test forecast endpoint
curl http://localhost:5000/api/forecast/24

# Test statistics
curl http://localhost:5000/api/statistics
```

### Test Database
```bash
# Query database directly
sqlite3 smart_house.db

# SQL queries:
SELECT * FROM energy_data ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM device_status ORDER BY timestamp DESC LIMIT 10;
SELECT AVG(system_efficiency) FROM energy_data;
```

### Test ESP32
```cpp
// In Serial Monitor, you should see:
===== ENERGY MANAGEMENT =====
PV Power: 2500.0 W
Total Load: 1800.0 W
Balance: 700.0 W
Battery SOC: 75.5%
MODE: Surplus - Charging Battery
Charging battery: +0.15% (700.0 W)
System Efficiency: 93.2%
============================
```

---

## 🐛 Troubleshooting

### Problem: ESP32 can't connect to API
**Solution:**
1. Check WiFi credentials in ESP32 code
2. Verify API server is running (`python api_server.py`)
3. Check firewall settings
4. Ping server IP from ESP32's network
5. Check API_SERVER URL in ESP32 code

### Problem: No predictions in database
**Solution:**
```bash
# Run prediction script
python ai_predictions.py

# Check database
sqlite3 smart_house.db
SELECT COUNT(*) FROM energy_data;
```

### Problem: Models not training properly
**Solution:**
1. Check if you have enough data
2. Verify feature columns match
3. Check for NaN values
4. Increase training data size

### Problem: Web dashboard shows no data
**Solution:**
1. Check browser console (F12) for errors
2. Verify API server is running
3. Check CORS settings
4. Test API endpoints directly with curl

---

## 📈 Performance Optimization

### Database Optimization
```sql
-- Add indexes for faster queries
CREATE INDEX idx_timestamp ON energy_data(timestamp);
CREATE INDEX idx_device_time ON device_status(device_name, timestamp);

-- Clean old data (older than 30 days)
DELETE FROM energy_data WHERE datetime(timestamp) < datetime('now', '-30 days');
DELETE FROM device_status WHERE datetime(timestamp) < datetime('now', '-30 days');
```

### API Server Optimization
```python
# Use connection pooling
from flask_sqlalchemy import SQLAlchemy

# Enable caching
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/statistics')
@cache.cached(timeout=60)  # Cache for 1 minute
def get_statistics():
    # Your code here
```

---

## 🔒 Security Best Practices

1. **Change default credentials:**
   - WiFi password
   - API authentication tokens

2. **Use HTTPS in production:**
   - Get SSL certificate
   - Configure Flask to use SSL

3. **Limit API access:**
   - Add IP whitelist
   - Implement rate limiting

4. **Secure database:**
   - Set proper file permissions
   - Regular backups
   - Encrypt sensitive data

---

## 📱 Mobile App Integration

The API is ready for mobile app integration:

```javascript
// React Native / Flutter example
fetch('http://YOUR_SERVER:5000/api/current_prediction')
  .then(response => response.json())
  .then(data => {
    console.log('PV Power:', data.pv_power);
    console.log('Consumption:', data.consumption);
    console.log('Battery:', data.battery_soc);
  });
```

---

## 🎓 Next Steps

### Enhancements to Consider:

1. **Weather API Integration:**
   - Fetch real weather data (OpenWeatherMap, etc.)
   - Improve prediction accuracy
   - Cloud cover forecasting

2. **Machine Learning Improvements:**
   - Use LSTM for time series prediction
   - Implement online learning (model updates)
   - Add more features (historical patterns)

3. **Advanced Energy Management:**
   - Dynamic pricing integration
   - Peak shaving optimization
   - Vehicle-to-grid (V2G) support

4. **User Interface:**
   - Mobile app (React Native/Flutter)
   - Voice control (Alexa/Google Home)
   - Push notifications

5. **Hardware Integration:**
   - Smart meter reading
   - Real solar inverter data
   - Battery management system (BMS)

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review code comments
3. Check Serial Monitor output (ESP32)
4. Test API endpoints individually
5. Check database contents

---

## 📄 License

This project is for educational and demonstration purposes.
Feel free to modify and extend for your needs.

---

**Version:** 1.0  
**Last Updated:** February 2026  
**Status:** Production Ready  

🏠⚡ Happy Smart Home Building! 🔋☀️
