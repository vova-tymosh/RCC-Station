# RCC MQTT Data Plotter

A real-time locomotive telemetry visualization tool for RCC model locomotive decoders via MQTT.

## Features

- **6 Real-time Charts**: Speed, Throttle, Battery, Current, Temperature, Pressure
- **Multi-locomotive Support**: Auto-discovery and color-coded tracking
- **MQTT Integration**: Native RCC heartbeat protocol support
- **Distance Tracking**: Live distance monitoring per locomotive
- **Clean Interface**: No legends, optimized layout for maximum data visibility
- **DecoderPro Integration**: Easy launch from desktop or JMRI scripts

## Quick Start

### Launch the Data Plotter
1. **Desktop Shortcut**: Double-click "RCC MQTT Data Plotter" icon
2. **From Terminal**: `~/JMRI/launch-rcc-plotter.sh`
3. **From DecoderPro**: Scripting → Script Entry → Load `RccPlotterLauncher.py` → Execute

### Configuration
Edit `~/JMRI/config.properties`:
```properties
mqtt.broker=tcp://192.168.20.62:1883
mqtt.topic=cab/+/heartbeat/values
chart.height=120
window.width=1000
window.height=700
auto.connect=true
```

## Project Structure

```
├── src/main/java/jmri/jmrix/rcc/
│   └── RccMqttDataPlotterStandalone.java    # Main application
├── build/
│   ├── jars/                                # Built JAR files
│   ├── scripts/                             # Build and deployment scripts
│   ├── python/                              # JMRI Python integration
│   └── packages/                            # Deployment packages
├── build.sh                                 # Master build script
├── config.properties                        # Configuration
├── SPECIFICATIONS.md                        # Complete feature specs
└── DECODERPRO_INTEGRATION.md               # Integration guide
```

## RCC Data Format

Supports RCC TransportMQ.h heartbeat CSV format:
- **Topic**: `cab/{locoId}/heartbeat/values`
- **Data**: `Time,Distance,Bitstate,Speed,Lost,Throttle,ThrOut,Battery,Temp,Psi,Current`
- **Example**: `"10217,1016,1073741824,30,20,50,0,10,30,20,40"`

## Build & Deploy

```bash
# Master build (recommended)
./build.sh

# Individual operations
./build/scripts/build-standalone.sh                    # Build JAR
./build/scripts/create-deployment-package-simple.sh    # Create deployment package
./build/scripts/deploy-to-decoderpro.sh               # Deploy to local JMRI
./build/scripts/clean.sh                              # Clean build artifacts

# Test standalone
java -jar build/jars/rcc-mqtt-plotter-standalone.jar
```

## Status: ✅ Fully Operational

Currently receiving live data from locomotives 3 and 7 with real-time visualization of all telemetry channels.