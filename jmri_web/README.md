# JMRI Web Integration for RCC MQTT Data Plotter

This folder contains the web-based integration of the RCC MQTT Data Plotter with JMRI's web server.

## Files

### Core Files

- **`RccMqttBridge.py`** - JMRI Python script that bridges MQTT data to JMRI memory variables
  - Connects to MQTT broker on localhost:1883
  - Subscribes to RCC heartbeat topics
  - Stores telemetry data in JMRI memory variables
  - Deploy to: `~/JMRI/jython/RccMqttBridge.py`

- **`rcc-plotter-full.html`** - Complete web interface with real-time charts
  - Beautiful UI with gradient header
  - 6 real-time charts (Speed, Throttle, Battery, Current, Temperature, Pressure)
  - Multi-locomotive support with color coding
  - Live data log
  - Deploy to: `~/JMRI/web/rcc-plotter.html`

### Testing & Documentation

- **`rcc-plotter-minimal.html`** - Minimal test page for verifying JMRI API connectivity
  - Tests JMRI JSON API connection
  - Tests Memory API access
  - Tests Roster API access
  - Useful for troubleshooting

- **`RCC_WEB_PLOTTER_GUIDE.md`** - Complete user guide
  - Quick start instructions
  - Architecture overview
  - Troubleshooting guide
  - API documentation

## Deployment

### To Raspberry Pi (192.168.20.62)

```bash
# Deploy Python bridge
scp RccMqttBridge.py vova@192.168.20.62:~/JMRI/jython/

# Deploy web interface
scp rcc-plotter-full.html vova@192.168.20.62:~/JMRI/web/rcc-plotter.html

# Deploy guide
scp RCC_WEB_PLOTTER_GUIDE.md vova@192.168.20.62:~/JMRI/
```

## Usage

1. **Start the bridge in JMRI:**
   - Scripting → Script Entry
   - Load: `~/JMRI/jython/RccMqttBridge.py`
   - Execute

2. **Open web interface:**
   - http://192.168.20.62:12080/web/rcc-plotter.html

## Architecture

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

## Features

- ✅ Real-time telemetry visualization
- ✅ Multi-locomotive support
- ✅ Color-coded charts
- ✅ JMRI native integration
- ✅ No external dependencies
- ✅ Responsive design
- ✅ Live data logging

## Related

This is the web-based version of the standalone Java application in the `JMRI/` folder. Both versions provide the same functionality but with different deployment models:

- **Standalone Java**: Desktop application, direct MQTT connection
- **Web Version**: Browser-based, uses JMRI memory variables

## Status

✅ **Deployed and operational** on Raspberry Pi 192.168.20.62