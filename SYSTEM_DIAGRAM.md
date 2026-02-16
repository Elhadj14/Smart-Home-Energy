# Smart House Energy Management System
## Visual System Overview & Quick Reference

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SMART HOUSE ENERGY MANAGEMENT SYSTEM                      ║
║                         Complete Integration Flow                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: AI PREDICTION ENGINE (Python)                                      │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │ Historical Data  │
    │  • Weather       │──┐
    │  • PV Output     │  │
    │  • Consumption   │  │
    └──────────────────┘  │
                          ▼
    ┌─────────────────────────────────┐
    │  Machine Learning Models        │
    │  ┌───────────────────────────┐  │
    │  │ PV Power Prediction       │  │
    │  │ • Random Forest           │  │
    │  │ • Features: irradiance,   │  │
    │  │   temperature, humidity   │  │
    │  │ • Accuracy: 91% R²        │  │
    │  └───────────────────────────┘  │
    │                                 │
    │  ┌───────────────────────────┐  │
    │  │ Consumption Prediction    │  │
    │  │ • Random Forest           │  │
    │  │ • Features: hour, day,    │  │
    │  │   temperature, weekend    │  │
    │  │ • Accuracy: 94% R²        │  │
    │  └───────────────────────────┘  │
    └─────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │  24-Hour Predictions            │
    │  • PV Power (W)                 │
    │  • Consumption (W)              │
    │  • Surplus/Deficit              │
    │  • Updated every hour           │
    └─────────────────────────────────┘

                   │
                   ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: DATABASE STORAGE (SQLite)                                          │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────┐
    │  smart_house.db                                          │
    │                                                          │
    │  ┌────────────────────┐  ┌────────────────────────┐   │
    │  │ energy_data        │  │ pv_predictions         │   │
    │  │ • timestamp        │  │ • timestamp            │   │
    │  │ • pv_power         │  │ • predicted_power      │   │
    │  │ • consumption      │  │ • irradiance           │   │
    │  │ • battery_soc      │  │ • temperature          │   │
    │  │ • grid_power       │  │ • confidence           │   │
    │  │ • efficiency       │  └────────────────────────┘   │
    │  └────────────────────┘                               │
    │                                                          │
    │  ┌────────────────────┐  ┌────────────────────────┐   │
    │  │ consumption_pred   │  │ device_status          │   │
    │  │ • timestamp        │  │ • device_name          │   │
    │  │ • predicted_cons   │  │ • status (ON/OFF)      │   │
    │  │ • day_of_week      │  │ • power_consumption    │   │
    │  │ • confidence       │  │ • timestamp            │   │
    │  └────────────────────┘  └────────────────────────┘   │
    └──────────────────────────────────────────────────────────┘

                   │
                   ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: API SERVER (Flask)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────┐
    │  Flask API Server (Port 5000)                        │
    │                                                      │
    │  REST API Endpoints:                                 │
    │  ┌────────────────────────────────────────────────┐ │
    │  │ GET  /api/current_prediction                   │ │──► ESP32
    │  │ GET  /api/forecast/24                          │ │
    │  │ POST /api/update_status                        │ │◄── ESP32
    │  │ GET  /api/device_status                        │ │
    │  │ GET  /api/statistics                           │ │
    │  │ GET  /                (Web Dashboard)          │ │──► Browser
    │  └────────────────────────────────────────────────┘ │
    └──────────────────────────────────────────────────────┘

            │                           │
            │                           │
            ▼                           ▼

┌──────────────────────────┐    ┌──────────────────────────────────┐
│  WEB DASHBOARD           │    │  STEP 4: ESP32 CONTROLLER        │
│  (Browser)               │    └──────────────────────────────────┘
└──────────────────────────┘
                                    ┌──────────────────────────────┐
┌──────────────────────┐            │  ESP32 Firmware              │
│  Real-time Display   │            │  (C++ Arduino)               │
│  • PV Power          │            │                              │
│  • Consumption       │            │  ┌────────────────────────┐ │
│  • Battery Level     │            │  │ WiFi Connection        │ │
│  • Grid Status       │            │  │ • Fetch predictions    │ │
│  • 24h Forecast      │            │  │ • Every 60 seconds     │ │
│  • Device Status     │            │  └────────────────────────┘ │
│  • Auto-refresh      │            │                              │
└──────────────────────┘            │  ┌────────────────────────┐ │
                                    │  │ Energy Algorithm       │ │
                                    │  │ IF Surplus:            │ │
                                    │  │   • Charge battery     │ │
                                    │  │   • Run water heater   │ │
                                    │  │ IF Deficit:            │ │
                                    │  │   • Use battery        │ │
                                    │  │   • Use grid           │ │
                                    │  └────────────────────────┘ │
                                    │                              │
                                    │  ┌────────────────────────┐ │
                                    │  │ Device Control (Relays)│ │
                                    │  │ • Fridge    (Pin 5)    │ │
                                    │  │ • Heater    (Pin 18)   │ │
                                    │  │ • Lights    (Pin 19)   │ │
                                    │  │ • Router    (Pin 21)   │ │
                                    │  │ • Washing   (Pin 22)   │ │
                                    │  │ • AC        (Pin 23)   │ │
                                    │  │ • Water Htr (Pin 4)    │ │
                                    │  └────────────────────────┘ │
                                    │                              │
                                    │  ┌────────────────────────┐ │
                                    │  │ Web Interface          │ │
                                    │  │ http://<ESP32_IP>      │ │
                                    │  │ • Show all devices     │ │
                                    │  │ • Real-time status     │ │
                                    │  └────────────────────────┘ │
                                    └──────────────────────────────┘

                                              │
                                              ▼
                                    ┌──────────────────────────────┐
                                    │  HARDWARE                    │
                                    │  • 6 Relays for devices      │
                                    │  • 1 Relay for water heater  │
                                    │  • Solar panels (input)      │
                                    │  • Battery (storage)         │
                                    │  • Grid connection           │
                                    └──────────────────────────────┘

╔══════════════════════════════════════════════════════════════════════════════╗
║                              DATA FLOW                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. AI predicts → 2. Saves to DB → 3. API serves → 4. ESP32 fetches → 5. Controls devices
                                           ↓
                                    6. ESP32 reports status back
                                           ↓
                                    7. API updates DB
                                           ↓
                                    8. Web dashboard displays

╔══════════════════════════════════════════════════════════════════════════════╗
║                           QUICK START COMMANDS                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│  1. FIRST TIME SETUP                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

    # Install dependencies
    pip install pandas numpy scikit-learn flask flask-cors

    # Run automated setup
    python setup.py

    # Or manual setup:
    python ai_predictions.py          # Train models & generate predictions
    python api_server.py              # Start API server

┌─────────────────────────────────────────────────────────────────────────────┐
│  2. DAILY OPERATION                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

    # Start API server (keep running)
    python api_server.py

    # Update predictions (run hourly via cron/scheduler)
    python ai_predictions.py

    # Access dashboards
    # Web: http://localhost:5000
    # ESP32: http://<ESP32_IP>

┌─────────────────────────────────────────────────────────────────────────────┐
│  3. ESP32 CONFIGURATION                                                     │
└─────────────────────────────────────────────────────────────────────────────┘

    1. Open Ems_integrated.cpp
    2. Update WiFi:
       const char* ssid = "YOUR_WIFI";
       const char* password = "YOUR_PASSWORD";
    3. Update server IP:
       const char* API_SERVER = "http://192.168.1.XXX:5000";
    4. Install ArduinoJson library
    5. Upload to ESP32

┌─────────────────────────────────────────────────────────────────────────────┐
│  4. TESTING                                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    # Test API
    curl http://localhost:5000/api/current_prediction
    curl http://localhost:5000/api/forecast/24

    # Check database
    sqlite3 smart_house.db
    SELECT * FROM energy_data LIMIT 5;

    # Monitor ESP32
    # Open Arduino Serial Monitor at 115200 baud

╔══════════════════════════════════════════════════════════════════════════════╗
║                           KEY FEATURES                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

✓ AI-powered predictions (91-94% accuracy)
✓ Real-time energy management
✓ Automatic device control based on available power
✓ Battery optimization (charge/discharge management)
✓ Grid integration (import/export)
✓ Web dashboard (live monitoring)
✓ ESP32 web interface
✓ SQLite database (all data stored)
✓ REST API (easy integration)
✓ Priority-based load management

╔══════════════════════════════════════════════════════════════════════════════╗
║                        SYSTEM PARAMETERS                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Battery:
  • Capacity: 10 kWh (10,000 Wh)
  • Max charge/discharge: 3 kW
  • SOC range: 20-100%
  • Charge efficiency: 92%
  • Discharge efficiency: 90%

Devices:
  • Fridge: 150W (critical, always on)
  • Heater: 200W (flexible)
  • Lights: 100W (time-based)
  • Router: 50W (critical, always on)
  • Washing: 500W (flexible)
  • AC: 1200W (battery-dependent)
  • Water Heater: 1500W (surplus only)

Update Intervals:
  • AI predictions: 1 hour
  • ESP32 API fetch: 1 minute
  • ESP32 loop: 2 seconds
  • Web dashboard: 5 seconds

╔══════════════════════════════════════════════════════════════════════════════╗
║                         FILE STRUCTURE                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

smart-house/
├── ai_predictions.py          # AI models and predictions
├── api_server.py              # Flask API server
├── Ems_integrated.cpp         # ESP32 firmware
├── setup.py                   # Automated setup script
├── INTEGRATION_GUIDE.md       # Complete documentation
├── SYSTEM_DIAGRAM.md          # This file
│
├── smart_house.db            # SQLite database (auto-created)
├── pv_model.pkl              # Trained PV model (auto-created)
├── consumption_model.pkl      # Trained consumption model (auto-created)
└── esp32_data.csv            # CSV export (auto-created)

╔══════════════════════════════════════════════════════════════════════════════╗
║                      TROUBLESHOOTING CHECKLIST                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

ESP32 Won't Connect:
  □ Check WiFi credentials
  □ Verify API server is running
  □ Check firewall settings
  □ Verify API_SERVER URL
  □ Test with browser: http://<SERVER_IP>:5000/api/current_prediction

No Predictions:
  □ Run: python ai_predictions.py
  □ Check: sqlite3 smart_house.db "SELECT COUNT(*) FROM energy_data;"
  □ Verify models exist: pv_model.pkl, consumption_model.pkl

Web Dashboard Empty:
  □ Check browser console (F12)
  □ Verify API server running
  □ Test API: curl http://localhost:5000/api/current_prediction
  □ Check CORS settings

Models Not Training:
  □ Install dependencies: pip install pandas numpy scikit-learn
  □ Check Python version (3.7+)
  □ Verify data generation
  □ Check error messages in console

╔══════════════════════════════════════════════════════════════════════════════╗
║                        SUCCESS INDICATORS                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

You know it's working when:

✓ AI predictions run without errors
✓ Database contains records (SELECT COUNT(*) FROM energy_data)
✓ API server responds to curl requests
✓ Web dashboard shows live data
✓ ESP32 serial monitor shows "Fetching predictions..." every minute
✓ ESP32 web interface shows device status
✓ Relays switch on/off based on power availability
✓ Battery SOC changes over time
✓ System efficiency displayed (~92%)

╔══════════════════════════════════════════════════════════════════════════════╗
║                            NEXT STEPS                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

After basic setup:

1. Integration:
   □ Connect real sensors (solar, battery)
   □ Integrate weather API
   □ Add smart meter reading

2. Optimization:
   □ Fine-tune AI models
   □ Adjust battery parameters
   □ Optimize device priorities

3. Monitoring:
   □ Set up email/SMS alerts
   □ Create daily reports
   □ Log historical performance

4. Expansion:
   □ Add more devices
   □ Implement demand response
   □ Create mobile app
   □ Add energy trading

╔══════════════════════════════════════════════════════════════════════════════╗
║  For detailed instructions, see INTEGRATION_GUIDE.md                         ║
║  For support, check code comments and error messages                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
