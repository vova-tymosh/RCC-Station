# RCC MQTT Data Plotter - DecoderPro Integration

## ✅ Simple DecoderPro Integration

The RCC MQTT Data Plotter integrates with JMRI/DecoderPro as a standalone application that can be launched alongside your JMRI environment.

## 🚀 **Launch Methods**

### **Method 1: Desktop Shortcut (Recommended)**
- Double-click the "RCC MQTT Data Plotter" desktop icon
- Automatically created during deployment

### **Method 2: Terminal Launch**
```bash
~/JMRI/launch-rcc-plotter.sh
```

### **Method 3: Direct Java Launch**
```bash
java -jar ~/JMRI/lib/rcc-mqtt-plotter.jar
```

## 📦 **Deployment Process**

### **Automatic Deployment**
```bash
./build/scripts/deploy-to-decoderpro.sh
```

**What it installs:**
- JAR file: `~/JMRI/lib/rcc-mqtt-plotter.jar`
- Configuration: `~/JMRI/config.properties`
- Launcher script: `~/JMRI/launch-rcc-plotter.sh`
- Desktop shortcut: `~/Desktop/RCC-MQTT-Plotter.desktop`

## ⚙️ **Configuration**

Edit `~/JMRI/config.properties`:
```properties
# MQTT Broker Configuration
mqtt.broker=tcp://192.168.20.62:1883
mqtt.topic=cab/+/heartbeat/values
auto.connect=true

# UI Configuration
chart.height=120
window.width=1000
window.height=700
```

## �� **Integration Benefits**

- **Standalone Operation**: Runs independently of JMRI processes
- **Shared Configuration**: Uses JMRI directory for consistent setup
- **Easy Access**: Desktop shortcut and launcher script
- **No Dependencies**: Self-contained JAR with all libraries

## 📊 **Usage Workflow**

1. **Start JMRI/DecoderPro** for locomotive control
2. **Launch RCC Plotter** via desktop shortcut
3. **Monitor telemetry** in real-time while operating trains
4. **Configure MQTT broker** as needed in config file

## ✅ **Status: Production Ready**

The integration provides a clean, simple way to run the RCC MQTT Data Plotter alongside JMRI without complex button integrations or startup dependencies.
