#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

// ===== WiFi Configuration =====
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_PASSWORD";

// ===== Database API Configuration =====
// You'll need to run a Python server that serves the database data
const char* API_SERVER = "http://192.168.1.100:5000";  // Change to your server IP

WebServer server(80);

// ===== Relay Pins =====
int relayPins[6] = {5, 18, 19, 21, 22, 23};
int waterHeaterPin = 4;

// Device names
const char* deviceNames[6] = {"Fridge", "Heater", "Light", "Router", "Washing", "AC"};

// Device states
bool devices[6];
bool waterHeater = false;
bool gridPower = false;

// Device loads (Watts)
float deviceLoad[6] = {150, 200, 100, 50, 500, 1200};
float waterHeaterLoad = 1500;

// System data from AI predictions
float predictedPvPower = 0;
float predictedConsumption = 0;
float currentPvPower = 0;
float totalLoad = 0;
float batterySOC = 70;
float batteryCapacity = 10000;  // 10 kWh in Wh
float maxBatteryPower = 3000;   // Max charge/discharge rate in W

bool autoMode = true;
unsigned long lastApiCall = 0;
const unsigned long API_INTERVAL = 60000;  // Update every 1 minute

// Statistics
float dailyPvGeneration = 0;
float dailyConsumption = 0;
float dailyGridImport = 0;
float systemEfficiency = 92.0;

// ===== Time Configuration =====
void initTime() {
  configTime(0, 0, "pool.ntp.org");
  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    Serial.println("Time synchronized");
  }
}

// ===== Get current hour =====
int getCurrentHour() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return 12;
  return timeinfo.tm_hour;
}

// ===== Check if it's daytime =====
bool isDaytime() {
  int hour = getCurrentHour();
  return (hour >= 6 && hour <= 18);
}

// ===== Fetch predictions from database API =====
bool fetchPredictions() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return false;
  }

  HTTPClient http;
  String url = String(API_SERVER) + "/api/current_prediction";
  
  Serial.println("Fetching predictions from: " + url);
  http.begin(url);
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    Serial.println("Received: " + payload);
    
    // Parse JSON
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, payload);
    
    if (error) {
      Serial.println("JSON parsing failed");
      http.end();
      return false;
    }
    
    // Extract data
    predictedPvPower = doc["pv_power"] | 0;
    predictedConsumption = doc["consumption"] | 0;
    batterySOC = doc["battery_soc"] | 70;
    
    Serial.printf("Predicted PV: %.1f W, Consumption: %.1f W, Battery: %.1f%%\n", 
                  predictedPvPower, predictedConsumption, batterySOC);
    
    http.end();
    return true;
  } else {
    Serial.printf("HTTP Error: %d\n", httpCode);
    http.end();
    return false;
  }
}

// ===== Send status to database =====
void sendStatusToDatabase() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String(API_SERVER) + "/api/update_status";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  DynamicJsonDocument doc(1024);
  doc["pv_power"] = currentPvPower;
  doc["consumption"] = totalLoad;
  doc["battery_soc"] = batterySOC;
  doc["grid_power"] = gridPower;
  doc["efficiency"] = systemEfficiency;
  
  JsonArray devicesArray = doc.createNestedArray("devices");
  for (int i = 0; i < 6; i++) {
    JsonObject device = devicesArray.createNestedObject();
    device["name"] = deviceNames[i];
    device["status"] = devices[i];
    device["power"] = devices[i] ? deviceLoad[i] : 0;
  }
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == 200) {
    Serial.println("Status updated successfully");
  } else {
    Serial.printf("Status update failed: %d\n", httpCode);
  }
  
  http.end();
}

// ===== Calculate system efficiency =====
float calculateEfficiency() {
  if (totalLoad == 0) return 100.0;
  
  float usedPower = totalLoad;
  float totalAvailable = currentPvPower + (gridPower ? 5000 : 0);
  
  if (totalAvailable == 0) return 0;
  
  float efficiency = (usedPower / totalAvailable) * 100.0;
  return constrain(efficiency, 0, 100);
}

// ===== Energy Management Algorithm =====
void manageEnergy() {
  // Use AI prediction for current PV (or measure actual)
  currentPvPower = predictedPvPower;
  
  // Calculate total load
  totalLoad = 0;
  for (int i = 0; i < 6; i++) {
    if (devices[i]) {
      totalLoad += deviceLoad[i];
    }
  }
  if (waterHeater) {
    totalLoad += waterHeaterLoad;
  }
  
  float powerBalance = currentPvPower - totalLoad;
  
  Serial.println("\n===== ENERGY MANAGEMENT =====");
  Serial.printf("PV Power: %.1f W\n", currentPvPower);
  Serial.printf("Total Load: %.1f W\n", totalLoad);
  Serial.printf("Balance: %.1f W\n", powerBalance);
  Serial.printf("Battery SOC: %.1f%%\n", batterySOC);
  
  // ===== CASE 1: Surplus Power (Generation > Consumption) =====
  if (powerBalance > 0) {
    Serial.println("MODE: Surplus - Charging Battery");
    
    // Charge battery if not full
    if (batterySOC < 100) {
      float chargeRate = min(powerBalance, maxBatteryPower);
      float chargeEfficiency = 0.92;  // 92% charging efficiency
      float energyStored = (chargeRate * chargeEfficiency / batteryCapacity) * 100;  // % per second
      
      batterySOC += energyStored;
      if (batterySOC > 100) batterySOC = 100;
      
      powerBalance -= chargeRate;
      gridPower = false;
      
      Serial.printf("Charging battery: +%.2f%% (%.1f W)\n", energyStored, chargeRate);
    }
    
    // If battery full and still surplus, turn on water heater
    if (batterySOC >= 95 && powerBalance > waterHeaterLoad * 0.8) {
      waterHeater = true;
      Serial.println("Water heater: ON (using excess power)");
    } else {
      waterHeater = false;
    }
    
    gridPower = false;
  }
  
  // ===== CASE 2: Deficit Power (Consumption > Generation) =====
  else {
    float deficit = abs(powerBalance);
    Serial.println("MODE: Deficit - Using Battery/Grid");
    
    // Try to use battery first
    if (batterySOC > 20) {  // Keep 20% reserve
      float dischargeRate = min(deficit, maxBatteryPower);
      float dischargeEfficiency = 0.90;  // 90% discharge efficiency
      float energyUsed = (dischargeRate / (dischargeEfficiency * batteryCapacity)) * 100;
      
      batterySOC -= energyUsed;
      if (batterySOC < 0) batterySOC = 0;
      
      deficit -= dischargeRate;
      Serial.printf("Discharging battery: -%.2f%% (%.1f W)\n", energyUsed, dischargeRate);
    }
    
    // If battery low or can't cover deficit, use grid
    if (batterySOC <= 20 || deficit > 100) {
      gridPower = true;
      Serial.printf("Grid power: ON (covering %.1f W)\n", deficit);
    } else {
      gridPower = false;
    }
    
    // Turn off water heater during deficit
    waterHeater = false;
  }
  
  // Load shedding if critical
  if (batterySOC < 10 && gridPower == false) {
    Serial.println("CRITICAL: Load shedding activated");
    // Turn off non-essential loads
    devices[1] = false;  // Heater
    devices[4] = false;  // Washing machine
    devices[5] = false;  // AC
  }
  
  systemEfficiency = calculateEfficiency();
  Serial.printf("System Efficiency: %.1f%%\n", systemEfficiency);
  Serial.println("============================\n");
}

// ===== Apply priority-based device control =====
void applyDeviceControl() {
  // Always-on devices
  devices[0] = true;   // Fridge (critical)
  devices[3] = true;   // Router (critical)
  
  // Lights based on time
  devices[2] = !isDaytime();
  
  // Smart control for other devices based on power availability
  float availablePower = currentPvPower + (batterySOC > 30 ? maxBatteryPower : 0);
  
  if (availablePower > totalLoad + 200) {
    devices[1] = true;  // Heater
  }
  
  if (availablePower > totalLoad + 500) {
    devices[4] = true;  // Washing machine
  }
  
  if (availablePower > totalLoad + 1200 && batterySOC > 50) {
    devices[5] = true;  // AC
  } else if (batterySOC < 30) {
    devices[5] = false;  // Turn off AC if battery low
  }
}

// ===== Update relay outputs =====
void updateRelays() {
  for (int i = 0; i < 6; i++) {
    digitalWrite(relayPins[i], devices[i] ? HIGH : LOW);
  }
  digitalWrite(waterHeaterPin, waterHeater ? HIGH : LOW);
}

// ===== Web Interface - Dashboard =====
void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta charset='UTF-8'>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  html += "<title>Smart House Energy Management</title>";
  html += "<style>";
  html += "body { font-family: Arial; margin: 20px; background: #f0f0f0; }";
  html += ".container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }";
  html += "h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }";
  html += ".status { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }";
  html += ".card { background: #ecf0f1; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; }";
  html += ".card h3 { margin: 0 0 10px 0; color: #2c3e50; }";
  html += ".value { font-size: 24px; font-weight: bold; color: #27ae60; }";
  html += ".device { background: #fff; padding: 12px; margin: 8px 0; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }";
  html += ".device-on { border-left: 4px solid #27ae60; }";
  html += ".device-off { border-left: 4px solid #e74c3c; }";
  html += ".badge { padding: 5px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }";
  html += ".badge-on { background: #27ae60; color: white; }";
  html += ".badge-off { background: #e74c3c; color: white; }";
  html += ".refresh { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }";
  html += ".refresh:hover { background: #2980b9; }";
  html += "</style>";
  html += "</head><body>";
  
  html += "<div class='container'>";
  html += "<h1>🏠 Smart House Energy Management</h1>";
  
  // Status cards
  html += "<div class='status'>";
  
  html += "<div class='card'>";
  html += "<h3>☀️ PV Power</h3>";
  html += "<div class='value'>" + String(currentPvPower, 1) + " W</div>";
  html += "</div>";
  
  html += "<div class='card'>";
  html += "<h3>⚡ Consumption</h3>";
  html += "<div class='value'>" + String(totalLoad, 1) + " W</div>";
  html += "</div>";
  
  html += "<div class='card'>";
  html += "<h3>🔋 Battery</h3>";
  html += "<div class='value'>" + String(batterySOC, 1) + " %</div>";
  html += "</div>";
  
  html += "<div class='card'>";
  html += "<h3>🔌 Grid</h3>";
  html += "<div class='value'>" + String(gridPower ? "ON" : "OFF") + "</div>";
  html += "</div>";
  
  html += "</div>";
  
  // Devices
  html += "<h2>Device Status</h2>";
  for (int i = 0; i < 6; i++) {
    html += "<div class='device " + String(devices[i] ? "device-on" : "device-off") + "'>";
    html += "<span>" + String(deviceNames[i]) + " (" + String(deviceLoad[i], 0) + " W)</span>";
    html += "<span class='badge " + String(devices[i] ? "badge-on" : "badge-off") + "'>" + String(devices[i] ? "ON" : "OFF") + "</span>";
    html += "</div>";
  }
  
  html += "<div class='device " + String(waterHeater ? "device-on" : "device-off") + "'>";
  html += "<span>Water Heater (" + String(waterHeaterLoad, 0) + " W)</span>";
  html += "<span class='badge " + String(waterHeater ? "badge-on" : "badge-off") + "'>" + String(waterHeater ? "ON" : "OFF") + "</span>";
  html += "</div>";
  
  // System info
  html += "<h2>System Information</h2>";
  html += "<div class='card'>";
  html += "<p><strong>System Efficiency:</strong> " + String(systemEfficiency, 1) + "%</p>";
  html += "<p><strong>Mode:</strong> " + String(autoMode ? "Automatic" : "Manual") + "</p>";
  html += "<p><strong>Predicted PV:</strong> " + String(predictedPvPower, 1) + " W</p>";
  html += "<p><strong>Predicted Consumption:</strong> " + String(predictedConsumption, 1) + " W</p>";
  html += "</div>";
  
  html += "<button class='refresh' onclick='location.reload()'>🔄 Refresh</button>";
  html += "</div>";
  
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

// ===== API endpoint for JSON data =====
void handleApiData() {
  DynamicJsonDocument doc(1024);
  
  doc["pv_power"] = currentPvPower;
  doc["consumption"] = totalLoad;
  doc["battery_soc"] = batterySOC;
  doc["grid_power"] = gridPower;
  doc["efficiency"] = systemEfficiency;
  
  JsonArray devicesArray = doc.createNestedArray("devices");
  for (int i = 0; i < 6; i++) {
    JsonObject device = devicesArray.createNestedObject();
    device["name"] = deviceNames[i];
    device["status"] = devices[i];
    device["power"] = devices[i] ? deviceLoad[i] : 0;
  }
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  server.send(200, "application/json", jsonString);
}

// ===== Setup =====
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n===== SMART HOUSE ENERGY MANAGEMENT SYSTEM =====");
  
  // Initialize relay pins
  for (int i = 0; i < 6; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW);
  }
  pinMode(waterHeaterPin, OUTPUT);
  digitalWrite(waterHeaterPin, LOW);
  
  // Connect to WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // Initialize time
  initTime();
  
  // Setup web server
  server.on("/", handleRoot);
  server.on("/api/data", handleApiData);
  server.begin();
  Serial.println("Web server started");
  
  // Fetch initial predictions
  fetchPredictions();
  
  Serial.println("\nSystem ready!");
  Serial.println("Access dashboard at: http://" + WiFi.localIP().toString());
}

// ===== Main Loop =====
void loop() {
  // Handle web requests
  server.handleClient();
  
  // Fetch predictions periodically
  unsigned long currentMillis = millis();
  if (currentMillis - lastApiCall >= API_INTERVAL) {
    lastApiCall = currentMillis;
    fetchPredictions();
    sendStatusToDatabase();
  }
  
  // Apply device control based on available power
  if (autoMode) {
    applyDeviceControl();
  }
  
  // Run energy management algorithm
  manageEnergy();
  
  // Update relay outputs
  updateRelays();
  
  // Small delay
  delay(2000);
}
