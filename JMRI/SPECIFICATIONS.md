# RCC MQTT Data Plotter - Complete Specifications

## Overview
A JMRI extension that provides real-time visualization of telemetry data from RCC model locomotive decoders via MQTT protocol.

## Core Features

### 📡 MQTT Integration
- **Auto-connect**: Automatically connects to MQTT broker on startup
- **Broker**: Configurable via `config.properties` (default: tcp://192.168.20.62:1883)
- **Topics**: 
  - `cab/+/heartbeat/values` - Real-time telemetry data
  - `cab/+/heartbeat/keys` - Field name mappings
  - `cab/+/intro` - Locomotive introduction messages
- **Auto-reconnect**: 5-second delay reconnection on connection loss
- **Message Format**: CSV data parsing from RCC TransportMQ.h heartbeat implementation

### 🚂 Multi-Locomotive Support
- **Auto-discovery**: Locomotives automatically appear when sending heartbeat data
- **Individual selection**: Checkbox-based locomotive selection/deselection
- **Color coding**: Each locomotive assigned unique color (10 colors available)
- **Activity indicators**: Green text for active, gray for inactive locomotives
- **Distance tracking**: Real-time distance traveled display

### 📊 Real-Time Charts (6 Total)
**Chart Order (Top to Bottom):**
1. **Speed** - Locomotive speed values
2. **Throttle** - Throttle position data
3. **Battery** - Battery level monitoring
4. **Current** - Current consumption tracking
5. **Temp** - Temperature readings
6. **Psi** - Pressure measurements

**Chart Features:**
- **No legends**: Clean display without chart legends
- **No titles**: Minimal labeling (Y-axis labels only)
- **Color consistency**: Same locomotive color across all charts
- **Data retention**: 1000 points per locomotive per chart
- **Real-time updates**: Live data visualization

### 🎨 User Interface
- **Locomotive Selection Panel**: 
  - Color indicators (● symbols) matching chart colors
  - Locomotive info: "Loco: RCC (Addr: 3, Version: 0.8) - Distance: 123.4"
  - Always visible distance (updates only when selected)
- **Clean Layout**: No connection panels, auto-managed MQTT
- **Compact Design**: 120px height per chart, optimized for 6 charts
- **Window Size**: 1000x700 pixels (configurable)

### ⚙️ Configuration System
**File**: `config.properties`
```properties
mqtt.broker=tcp://192.168.20.62:1883
mqtt.topic=cab/+/heartbeat/values
mqtt.client.id=RCC_MQTT_Plotter
mqtt.timeout=10
mqtt.keepalive=20
chart.max.points=1000
chart.height=120
window.width=1000
window.height=700
auto.connect=true
```

### 📈 Data Processing
**RCC Heartbeat Format**: CSV values corresponding to keys
- **Default Keys**: Time,Distance,Bitstate,Speed,Lost,Throttle,ThrOut,Battery,Temp,Psi,Current
- **Example Values**: "3968,386,1073741824,69,20,50,0,89,109,99,119"
- **Locomotive ID**: Extracted from MQTT topic `cab/{locoId}/heartbeat/values`
- **Intro Messages**: "L,3,RCC,0.8,BIIIHBBBBBBB" format for locomotive identification

### 🔧 Technical Architecture
- **Language**: Java 17
- **Dependencies**: 
  - Eclipse Paho MQTT Client 1.2.5
  - JFreeChart 1.5.3
  - JSON processing 20230227
- **Build System**: Maven + Gradle support
- **Deployment**: Standalone JAR with embedded dependencies

## Performance Characteristics
- **Memory Management**: Automatic data point limiting (1000 per series)
- **UI Updates**: Only selected locomotives trigger UI refreshes
- **Data Storage**: All locomotive data stored regardless of selection
- **Color Management**: Efficient color application across 6 charts
- **Real-time Processing**: Live MQTT message processing with EDT updates

## Operational Features
- **Headless Compatible**: Runs on Raspberry Pi with VNC
- **Auto-start**: Configurable auto-connect on application launch
- **Error Handling**: Graceful MQTT connection failure handling
- **Logging**: Console output for monitoring and debugging
- **Process Management**: Clean shutdown and resource cleanup

## Integration Points
- **JMRI Compatible**: Designed for integration with JMRI 5.0+
- **Menu Integration**: Tools → RCC → MQTT Data Plotter
- **Service Provider**: Proper JMRI service registration
- **Configuration**: External config file for easy customization

## Current Deployment
- **Platform**: Raspberry Pi (192.168.20.62)
- **Display**: VNC (DISPLAY=:0)
- **Status**: Fully operational, receiving data from locomotives 3 and 7
- **Performance**: Real-time updates, stable operation