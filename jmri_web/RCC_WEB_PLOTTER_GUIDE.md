# RCC MQTT Data Plotter - Web Interface

## 🎉 Complete Integration with JMRI Web Server

### Quick Start

**Step 1: Start the MQTT Bridge in JMRI**

1. Open JMRI (DecoderPro3 is already running on your Raspberry Pi)
2. Go to: **Scripting → Script Entry**
3. Click **"Load"** and navigate to: `~/JMRI/jython/RccMqttBridge.py`
4. Click **"Execute"**
5. You should see output like:
   ```
   ============================================================
   RCC MQTT Bridge for JMRI
   ============================================================
   ✓ Connected to MQTT broker
   ✓ Subscribed to RCC topics
   ```

**Step 2: Open the Web Interface**

Open your browser and go to:
```
http://192.168.20.62:12080/web/rcc-plotter.html
```

That's it! You should now see:
- Real-time charts for Speed, Throttle, Battery, Current, Temperature, Pressure
- Discovered locomotives with color coding
- Live data log
- Connection status

---

## 📊 Features

### Real-Time Visualization
- **6 Live Charts**: Speed & Throttle, Battery & Current, Temperature, Pressure
- **Multi-Locomotive Support**: Automatically discovers and tracks all RCC locomotives
- **Color Coding**: Each locomotive gets a unique color across all charts
- **60-Second History**: Shows the last 60 seconds of data

### Integration
- **JMRI Native**: Runs within JMRI's web server (port 12080)
- **Memory Variables**: Uses JMRI's memory system for data storage
- **JSON API**: Accessible via JMRI's standard `/json/memory/` endpoints
- **No External Dependencies**: Everything runs on the Raspberry Pi

### Data Sources
- **MQTT Topics**: 
  - `cab/+/heartbeat/values` - Telemetry data
  - `cab/+/heartbeat/keys` - Field mappings
  - `cab/+/intro` - Locomotive identification
- **Update Rate**: 1 second polling interval
- **Data Points**: Speed, Throttle, Battery, Current, Temperature, Pressure, Distance

---

## 🔧 How It Works

### Architecture

```
RCC Locomotives (MQTT)
         ↓
   MQTT Broker (port 1883)
         ↓
RccMqttBridge.py (JMRI Script)
         ↓
JMRI Memory Variables
         ↓
JMRI JSON API (port 12080)
         ↓
Web Interface (Browser)
```

### Memory Variables Created

The bridge creates these memory variables in JMRI:

- `RCC_STATUS` - Connection status (CONNECTED/DISCONNECTED)
- `RCC_LOCO_LIST` - JSON array of discovered locomotives
- `RCC_3_SPEED` - Speed value for locomotive 3
- `RCC_3_THROTTLE` - Throttle value for locomotive 3
- `RCC_3_BATTERY` - Battery level for locomotive 3
- `RCC_3_CURRENT` - Current draw for locomotive 3
- `RCC_3_TEMP` - Temperature for locomotive 3
- `RCC_3_PSI` - Pressure for locomotive 3
- `RCC_3_DISTANCE` - Distance traveled for locomotive 3
- (Same pattern for locomotive 4, 7, etc.)

### API Endpoints

You can access the data via JMRI's JSON API:

```bash
# Check connection status
curl http://192.168.20.62:12080/json/memory/RCC_STATUS

# Get locomotive list
curl http://192.168.20.62:12080/json/memory/RCC_LOCO_LIST

# Get specific telemetry value
curl http://192.168.20.62:12080/json/memory/RCC_3_SPEED
```

---

## 🚀 Advanced Usage

### Running the Bridge Automatically

To start the bridge automatically when JMRI starts:

1. In JMRI, go to: **Edit → Preferences → Start Up**
2. Click **"Add ▼"** → **"Run Script"**
3. Select: `~/JMRI/jython/RccMqttBridge.py`
4. Click **"Save"** and restart JMRI

### Stopping the Bridge

If you need to stop the bridge:

1. Go to: **Scripting → Script Entry**
2. In the script input area, type: `stop_bridge()`
3. Click **"Execute"**

### Restarting the Bridge

To restart without reloading JMRI:

1. Stop the bridge: `stop_bridge()`
2. Start it again: `start_bridge()`

---

## 🐛 Troubleshooting

### "Bridge not running" message

**Solution**: Run the RccMqttBridge.py script in JMRI (see Step 1 above)

### "MQTT Disconnected" status

**Possible causes**:
- MQTT broker (Mosquitto) is not running
- Network connectivity issue
- Wrong broker address in script

**Check MQTT broker**:
```bash
ssh vova@192.168.20.62
ps aux | grep mosquitto
```

### No locomotives appearing

**Possible causes**:
- Locomotives are not sending MQTT data
- MQTT topics don't match (check topic names)
- Bridge script not running

**Check MQTT traffic**:
```bash
ssh vova@192.168.20.62
mosquitto_sub -t "cab/+/heartbeat/values" -C 5
```

### Charts not updating

**Solution**: 
- Refresh the browser page
- Check browser console for errors (F12)
- Verify memory variables exist in JMRI: **Tools → Tables → Memory**

---

## 📝 Files Deployed

### On Raspberry Pi

- **Bridge Script**: `~/JMRI/jython/RccMqttBridge.py`
- **Web Interface**: `~/JMRI/web/rcc-plotter.html`

### URLs

- **Web Plotter**: http://192.168.20.62:12080/web/rcc-plotter.html
- **JMRI Home**: http://192.168.20.62:12080/
- **JSON Console**: http://192.168.20.62:12080/json/
- **Memory Tables**: http://192.168.20.62:12080/tables/memory

---

## ✅ Success Indicators

When everything is working correctly, you should see:

1. **In JMRI Script Output**:
   ```
   ✓ Connected to MQTT broker
   ✓ Subscribed to RCC topics
   Loco 3 introduced: RCC
   ```

2. **In Web Interface**:
   - Green "Connected to MQTT" badge
   - Locomotives listed with colors
   - Charts showing live data
   - Data log updating every second

3. **In JMRI Memory Table**:
   - Memory variables starting with "RCC_" visible
   - Values updating in real-time

---

## 🎨 Customization

### Change Update Rate

Edit `rcc-plotter.html`, find this line:
```javascript
setInterval(() => this.pollData(), 1000);  // 1000 = 1 second
```

Change `1000` to your desired interval in milliseconds.

### Change Chart History Length

Edit `rcc-plotter.html`, find this line:
```javascript
const maxPoints = 60;  // 60 seconds of history
```

Change `60` to your desired number of data points.

### Change Colors

Edit `rcc-plotter.html`, find this line:
```javascript
this.colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#feca57'];
```

Replace with your preferred hex colors.

---

## 📞 Support

If you encounter issues:

1. Check the JMRI console output for error messages
2. Verify MQTT broker is running and accessible
3. Check browser console (F12) for JavaScript errors
4. Verify memory variables exist in JMRI

---

**Enjoy your real-time locomotive telemetry visualization! 🚂📊**