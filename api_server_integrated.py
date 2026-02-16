"""
Integrated API Server
=====================
يقرأ من قاعدة البيانات ويخدم ESP32 والويب

Endpoints:
- GET  /                      : Web dashboard
- GET  /api/current           : Current data for ESP32
- GET  /api/forecast          : 24-hour forecast
- POST /api/update_device     : Update device status
"""

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE_PATH = 'smart_house.db'


def get_db():
    """الاتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def dashboard():
    """لوحة التحكم على الويب"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart House Energy Management</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        h1 { color: #2c3e50; margin-bottom: 10px; }
        .subtitle { color: #7f8c8d; font-size: 14px; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            position: relative;
            overflow: hidden;
        }
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
        }
        .stat-card.solar::before { background: #f39c12; }
        .stat-card.consumption::before { background: #e74c3c; }
        .stat-card.battery::before { background: #27ae60; }
        .stat-card.efficiency::before { background: #3498db; }
        .stat-label {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-unit {
            font-size: 18px;
            color: #95a5a6;
            margin-left: 5px;
        }
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .chart-title {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        .update-time {
            text-align: center;
            color: white;
            font-size: 14px;
            margin-top: 20px;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 10px;
        }
        .status-online {
            background: #27ae60;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Smart House Energy Management</h1>
            <p class="subtitle">AI-Powered Energy Optimization System</p>
            <span class="status-badge status-online">● System Online</span>
        </div>

        <div class="stats">
            <div class="stat-card solar">
                <div class="stat-label">☀️ Solar Power</div>
                <div class="stat-value" id="solarPower">0<span class="stat-unit">W</span></div>
            </div>
            <div class="stat-card consumption">
                <div class="stat-label">⚡ Consumption</div>
                <div class="stat-value" id="consumption">0<span class="stat-unit">W</span></div>
            </div>
            <div class="stat-card battery">
                <div class="stat-label">🔋 Battery</div>
                <div class="stat-value" id="battery">0<span class="stat-unit">%</span></div>
            </div>
            <div class="stat-card efficiency">
                <div class="stat-label">📈 Efficiency</div>
                <div class="stat-value" id="efficiency">0<span class="stat-unit">%</span></div>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">24-Hour Energy Forecast</div>
            <canvas id="forecastChart"></canvas>
        </div>

        <div class="update-time" id="updateTime"></div>
    </div>

    <script>
        let chart;

        async function fetchData() {
            try {
                // Fetch current data
                const currentRes = await fetch('/api/current');
                const current = await currentRes.json();

                // Update stats
                document.getElementById('solarPower').innerHTML = 
                    current.pv_power.toFixed(0) + '<span class="stat-unit">W</span>';
                document.getElementById('consumption').innerHTML = 
                    current.consumption.toFixed(0) + '<span class="stat-unit">W</span>';
                document.getElementById('battery').innerHTML = 
                    current.battery_soc.toFixed(1) + '<span class="stat-unit">%</span>';
                document.getElementById('efficiency').innerHTML = 
                    current.efficiency.toFixed(1) + '<span class="stat-unit">%</span>';

                // Fetch forecast
                const forecastRes = await fetch('/api/forecast');
                const forecast = await forecastRes.json();

                updateChart(forecast);

                // Update timestamp
                document.getElementById('updateTime').textContent = 
                    'Last updated: ' + new Date().toLocaleTimeString();

            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        function updateChart(data) {
            const ctx = document.getElementById('forecastChart').getContext('2d');
            
            if (chart) chart.destroy();

            const labels = data.map(d => {
                const date = new Date(d.timestamp);
                return date.getHours() + ':00';
            });

            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'PV Generation (W)',
                            data: data.map(d => d.pv_power),
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Consumption (W)',
                            data: data.map(d => d.consumption),
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'top' }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Power (W)' }
                        }
                    }
                }
            });
        }

        // Initial fetch
        fetchData();

        // Update every 5 seconds
        setInterval(fetchData, 5000);
    </script>
</body>
</html>
    """
    return render_template_string(html)


@app.route('/api/current', methods=['GET'])
def get_current_data():
    """
    البيانات الحالية للـ ESP32
    
    Returns:
    --------
    JSON:
        {
            "timestamp": "2026-02-15 20:00:00",
            "pv_power": 2500.0,
            "consumption": 1800.0,
            "battery_soc": 70.0,
            "grid_power": 0,
            "efficiency": 92.0
        }
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM current_data WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'timestamp': row['timestamp'],
                'pv_power': float(row['pv_power']),
                'consumption': float(row['consumption']),
                'battery_soc': float(row['battery_soc']),
                'grid_power': int(row['grid_power']),
                'efficiency': float(row['system_efficiency'])
            })
        else:
            return jsonify({
                'error': 'No data available',
                'pv_power': 0,
                'consumption': 0,
                'battery_soc': 70,
                'grid_power': 0,
                'efficiency': 0
            }), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    """
    توقعات 24 ساعة
    
    Returns:
    --------
    JSON: Array of predictions
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, pv_power, consumption, surplus, deficit
            FROM predictions
            ORDER BY timestamp ASC
            LIMIT 24
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        forecast = []
        for row in rows:
            forecast.append({
                'timestamp': row['timestamp'],
                'pv_power': float(row['pv_power']),
                'consumption': float(row['consumption']),
                'surplus': float(row['surplus']),
                'deficit': float(row['deficit'])
            })
        
        return jsonify(forecast)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update_device', methods=['POST'])
def update_device():
    """
    تحديث حالة جهاز من ESP32
    
    Body:
    -----
    {
        "device_name": "Fridge",
        "status": 1,
        "power_consumption": 150.0
    }
    """
    try:
        data = request.json
        
        conn = get_db()
        cursor = conn.cursor()
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO devices (device_name, status, power_consumption, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (
            data.get('device_name'),
            data.get('status'),
            data.get('power_consumption'),
            timestamp
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Device updated'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """الحصول على حالة جميع الأجهزة"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_name, status, power_consumption, MAX(timestamp) as latest
            FROM devices
            GROUP BY device_name
            ORDER BY device_name
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        devices = []
        for row in rows:
            devices.append({
                'device_name': row['device_name'],
                'status': bool(row['status']),
                'power_consumption': float(row['power_consumption']),
                'timestamp': row['latest']
            })
        
        return jsonify({'devices': devices})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """إحصائيات النظام"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # معدل آخر 24 ساعة
        cursor.execute('''
            SELECT 
                AVG(pv_power) as avg_pv,
                AVG(consumption) as avg_consumption,
                AVG(surplus) as avg_surplus
            FROM predictions
            LIMIT 24
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'avg_pv_power': float(row['avg_pv']) if row['avg_pv'] else 0,
            'avg_consumption': float(row['avg_consumption']) if row['avg_consumption'] else 0,
            'avg_surplus': float(row['avg_surplus']) if row['avg_surplus'] else 0,
            'efficiency': 92.0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SMART HOUSE API SERVER")
    print("="*70)
    print("\nEndpoints:")
    print("  Web Dashboard:    http://localhost:5000/")
    print("  Current Data:     http://localhost:5000/api/current")
    print("  Forecast:         http://localhost:5000/api/forecast")
    print("  Devices:          http://localhost:5000/api/devices")
    print("  Statistics:       http://localhost:5000/api/stats")
    print("\nESP32 Configuration:")
    print("  API_SERVER = \"http://YOUR_IP:5000\"")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
