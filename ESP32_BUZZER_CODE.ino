// ============================================================================
// ESP32 BUZZER QUICK START - Copy & Paste Ready
// ============================================================================
// This is a complete, working example to get your ESP32 buzzing in 5 minutes!
// ============================================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============================================================================
// CONFIGURATION - UPDATE THESE FOR YOUR SETUP
// ============================================================================

// WiFi Settings
const char* SSID = "YourWiFiSSID";           // Change this!
const char* PASSWORD = "YourWiFiPassword";   // Change this!

// API Settings
const char* API_URL = "http://192.168.1.100:8000/api/incidents/buzzer-status/";
const char* BEACON_ID = "ab907856-3412-3412-3412-341278563412";  // Your beacon ID

// Hardware Settings
const int BUZZER_PIN = 26;        // GPIO pin connected to buzzer
const int POLL_INTERVAL_MS = 10000; // Poll every 10 seconds

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

WiFiClient wifiClient;
HTTPClient http;
bool lastBuzzerState = false;

// ============================================================================
// SETUP - Runs once at startup
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Initialize buzzer pin
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);  // Start silent
  
  Serial.println("\n\n");
  Serial.println("╔════════════════════════════════════════════════════════╗");
  Serial.println("║        🔔 ESP32 BUZZER - INITIALIZING 🔔              ║");
  Serial.println("╚════════════════════════════════════════════════════════╝");
  
  // Connect to WiFi
  Serial.print("\n📡 Connecting to WiFi: ");
  Serial.println(SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected!");
    Serial.print("  IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ WiFi connection failed!");
    Serial.println("  Check SSID and password!");
  }
  
  Serial.print("\n🎯 Beacon ID: ");
  Serial.println(BEACON_ID);
  Serial.print("📍 API URL: ");
  Serial.println(API_URL);
  Serial.println("\n⏳ Starting to poll... (waiting 5 seconds)\n");
  
  delay(5000);
}

// ============================================================================
// MAIN LOOP - Runs continuously
// ============================================================================

void loop() {
  // 1. Make API request
  String response = pollBuzzerStatus();
  
  // 2. Parse response
  BuzzerData buzzer = parseBuzzerResponse(response);
  
  // 3. Control buzzer based on response
  controlBuzzer(buzzer);
  
  // 4. Display status
  displayStatus(buzzer);
  
  // 5. Wait before next poll
  delay(POLL_INTERVAL_MS);
}

// ============================================================================
// FUNCTION: Poll the buzzer status API
// ============================================================================

String pollBuzzerStatus() {
  // Build URL with beacon_id parameter
  String url = String(API_URL) + "?beacon_id=" + BEACON_ID;
  
  // Make HTTP GET request
  http.begin(wifiClient, url);
  http.addHeader("Content-Type", "application/json");
  http.setConnectTimeout(5000);  // 5 second timeout
  http.setTimeout(5000);
  
  int httpCode = http.GET();
  String response = "";
  
  if (httpCode > 0) {
    response = http.getString();
  } else {
    Serial.print("✗ HTTP Error: ");
    Serial.println(httpCode);
  }
  
  http.end();
  return response;
}

// ============================================================================
// DATA STRUCTURE for parsed buzzer status
// ============================================================================

struct BuzzerData {
  bool incident_active;
  String buzzer_status;
  String incident_id;
  int priority;
  bool valid;
};

// ============================================================================
// FUNCTION: Parse API JSON response
// ============================================================================

BuzzerData parseBuzzerResponse(String jsonStr) {
  BuzzerData data = {false, "ERROR", "", 0, false};
  
  if (jsonStr.length() == 0) {
    return data;
  }
  
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, jsonStr);
  
  if (error) {
    Serial.print("✗ JSON Parse Error: ");
    Serial.println(error.c_str());
    return data;
  }
  
  // Extract values from JSON
  data.incident_active = doc["incident_active"] | false;
  data.buzzer_status = doc["buzzer_status"].as<String>();
  data.incident_id = doc["incident_id"].as<String>();
  data.priority = doc["priority"] | 0;
  data.valid = true;
  
  return data;
}

// ============================================================================
// FUNCTION: Control the buzzer
// ============================================================================

void controlBuzzer(BuzzerData buzzer) {
  bool shouldBuzz = buzzer.valid && buzzer.incident_active;
  
  // Only update if state changed
  if (shouldBuzz != lastBuzzerState) {
    digitalWrite(BUZZER_PIN, shouldBuzz ? HIGH : LOW);
    lastBuzzerState = shouldBuzz;
    
    if (shouldBuzz) {
      Serial.println("🔴 🔔 BUZZER ON");
    } else {
      Serial.println("🔇 BUZZER OFF");
    }
  }
}

// ============================================================================
// FUNCTION: Display status information
// ============================================================================

void displayStatus(BuzzerData buzzer) {
  Serial.println("\n" + String(10, '─'));
  Serial.print("⏰ ");
  Serial.println(getCurrentTime());
  
  if (!buzzer.valid) {
    Serial.println("⚠️  Invalid response from API");
    Serial.println("(Will retry in " + String(POLL_INTERVAL_MS/1000) + " seconds)");
  } else {
    // Buzzer status
    Serial.print("🔔 Buzzer: ");
    if (buzzer.incident_active) {
      Serial.println("ON 🔴");
    } else {
      Serial.println("OFF 🔇");
    }
    
    // Incident status
    Serial.print("📊 Status: ");
    Serial.println(buzzer.buzzer_status);
    
    // Incident ID
    if (buzzer.incident_id != "null" && buzzer.incident_id.length() > 0) {
      Serial.print("🆔 Incident: ");
      Serial.println(buzzer.incident_id.substring(0, 8) + "...");
    } else {
      Serial.println("🆔 Incident: None");
    }
    
    // Priority
    if (buzzer.priority > 0) {
      Serial.print("⚡ Priority: ");
      Serial.println(buzzer.priority);
    }
  }
  
  Serial.println("─" + String(9, '─'));
}

// ============================================================================
// HELPER: Get current time (for logging)
// ============================================================================

String getCurrentTime() {
  time_t now = time(nullptr);
  struct tm* timeinfo = localtime(&now);
  char buffer[20];
  strftime(buffer, sizeof(buffer), "%H:%M:%S", timeinfo);
  return String(buffer);
}

// ============================================================================
// SUCCESS INDICATORS
// ============================================================================

/*
  If everything works, you should see:

  ⏳ Starting to poll... (waiting 5 seconds)

  ──────────────
  ⏰ 14:35:22
  🔇 Buzzer: OFF 🔇
  📊 Status: INACTIVE
  🆔 Incident: None
  ──────────────

  [Repeat every 10 seconds]

  When an incident occurs:

  ──────────────
  ⏰ 14:36:45
  🔴 🔔 BUZZER ON
  📊 Status: PENDING
  🆔 Incident: abc-123d...
  ⚡ Priority: 3
  ──────────────
*/

// ============================================================================
// TROUBLESHOOTING
// ============================================================================

/*
  Problem: WiFi not connecting
  Solution:
  - Check SSID and PASSWORD are correct
  - Try putting them in quotes with escape characters
  - Check 2.4GHz (5GHz may not work on ESP32)

  Problem: "HTTP Error: -1" messages
  Solution:
  - Check API_URL is correct (http not https)
  - Check your network can reach the server
  - Try pinging the server from your computer first

  Problem: "JSON Parse Error"
  Solution:
  - The API might be returning an error page
  - Check API is running (curl the URL first)
  - Check beacon_id parameter is valid

  Problem: Buzzer not connected
  Solution:
  - Check BUZZER_PIN is correct (GPIO 26)
  - Check buzzer circuit (GND and GPIO pin)
  - Try adding a simple test: digitalWrite(BUZZER_PIN, HIGH);

  Problem: Endpoint returns 404
  Solution:
  - Check beacon_id exists in database
  - Check beacon is_active=True in admin panel
  - Use /api/beacons/ to list all valid beacons
*/

// ============================================================================
// OPTIONAL: Add these for more features
// ============================================================================

/*
  // Option 1: Add WIFI indicator LED
  const int LED_PIN = 25;
  
  void setup() {
    pinMode(LED_PIN, OUTPUT);
  }
  
  void loop() {
    if (WiFi.status() == WL_CONNECTED) {
      digitalWrite(LED_PIN, HIGH);  // Connected
    } else {
      digitalWrite(LED_PIN, LOW);   // Disconnected
    }
    // ... rest of code
  }

  // Option 2: Pulse buzzer instead of continuous
  void controlBuzzerWithPulse(BuzzerData buzzer) {
    if (buzzer.incident_active) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(500);
      digitalWrite(BUZZER_PIN, LOW);
      delay(500);
    }
  }

  // Option 3: Different buzzer patterns based on priority
  void buzzerPattern(int priority) {
    switch(priority) {
      case 4: // CRITICAL
        for(int i=0; i<5; i++) { beep(200); delay(100); }
        break;
      case 3: // HIGH
        for(int i=0; i<3; i++) { beep(300); delay(200); }
        break;
      case 2: // MEDIUM
        beep(500);
        break;
      case 1: // LOW
        beep(1000);
        break;
    }
  }

  void beep(int duration) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(duration);
    digitalWrite(BUZZER_PIN, LOW);
  }
*/

// ============================================================================
// END OF CODE
// ============================================================================
