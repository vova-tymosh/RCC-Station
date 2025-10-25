# JMRI Web Integration for RCC MQTT Data Plotter

This folder contains the web-based integration of the RCC MQTT Data Plotter with JMRI's web server.

## Files

### Core Files

- **`RccMqttBridge.py`** - JMRI Python script that bridges MQTT data to JMRI memory variables
  - Connects to MQTT broker on localhost:1883
  - Subscribes to RCC heartbeat topics
  - Stores telemetry data in JMRI memory variables
  - Deploy to: `~/JMRI/jython/RccMqttBridge.py`

- **`rcc-plotter.html`** - Complete web interface with real-time charts
  - Beautiful UI with gradient header
  - Throttle, direction, and function controls
  - 4 real-time charts (Speed & Throttle, Battery & Current, Temperature, Pressure)
  - Multi-locomotive support with color coding
  - Responsive mobile layout
  - Deploy to: `~/JMRI/web/rcc-plotter.html`

### Documentation

- **`RCC_WEB_PLOTTER_GUIDE.md`** - Complete user guide
  - Quick start instructions
  - Architecture overview
  - Troubleshooting guide
  - API documentation

## Deployment

### To Raspberry Pi

```bash
# Deploy Python bridge
scp RccMqttBridge.py user@raspberry-pi:~/JMRI/jython/

# Deploy web interface
scp rcc-plotter.html user@raspberry-pi:~/JMRI/web/rcc-plotter.html

# Deploy guide
scp RCC_WEB_PLOTTER_GUIDE.md user@raspberry-pi:~/JMRI/
```

## Usage

1. **Start the bridge in JMRI:**
   - Scripting → Script Entry
   - Load: `~/JMRI/jython/RccMqttBridge.py`
   - Execute

2. **Open web interface:**
   - http://raspberry-pi:12080/web/rcc-plotter.html

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
- ✅ Throttle, direction, and function controls
- ✅ Multi-locomotive support
- ✅ Dynamic function buttons based on locomotive capabilities
- ✅ JMRI native integration
- ✅ No external dependencies
- ✅ Responsive mobile design
- ✅ Live data updates

## Related

This is the web-based version of the standalone Java application in the `JMRI/` folder. Both versions provide the same functionality but with different deployment models:

- **Standalone Java**: Desktop application, direct MQTT connection
- **Web Version**: Browser-based, uses JMRI memory variables

## Status

✅ **Deployed and operational** on Raspberry Pi