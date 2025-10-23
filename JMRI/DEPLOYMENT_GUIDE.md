# RCC MQTT Data Plotter - Third-Party Deployment Guide

## 📦 **Deploying to Any Machine**

This guide covers how to deploy the RCC MQTT Data Plotter to any third-party machine with JMRI installed.

## 🔧 **Prerequisites**

### **Required Software**
- **Java 11+** (OpenJDK or Oracle JDK)
- **JMRI 5.0+** installed
- **Network access** to MQTT broker
- **Display capability** (X11, VNC, or local display)

### **Check Prerequisites**
```bash
# Check Java version
java -version

# Check JMRI installation
ls ~/JMRI/jmri.jar

# Check network connectivity to MQTT broker
ping 192.168.20.62
```

## 📁 **Deployment Methods**

### **Method 1: Complete Project Deployment**

**Step 1: Transfer Project Files**
```bash
# From source machine, create deployment package
tar -czf rcc-mqtt-plotter.tar.gz \
    src/ \
    build-standalone.sh \
    deploy-to-decoderpro.sh \
    config.properties \
    *.md \
    *.py

# Transfer to target machine
scp rcc-mqtt-plotter.tar.gz user@target-machine:~/

# On target machine, extract
cd ~
tar -xzf rcc-mqtt-plotter.tar.gz
cd rcc-mqtt-plotter/
```

**Step 2: Build and Deploy**
```bash
# Make scripts executable
chmod +x *.sh

# Build the extension
./build-standalone.sh

# Deploy to JMRI
./deploy-to-decoderpro.sh
```

### **Method 2: Pre-built JAR Deployment**

**Step 1: Build JAR on Source Machine**
```bash
# On source machine (where it's already working)
cd ~/jmri-rcc-extension-clean
./build-standalone.sh

# Create deployment package with pre-built JAR
tar -czf rcc-mqtt-plotter-prebuilt.tar.gz \
    build/rcc-mqtt-plotter-standalone.jar \
    config.properties \
    deploy-to-decoderpro.sh \
    *.py \
    DECODERPRO_INTEGRATION.md
```

**Step 2: Deploy Pre-built Package**
```bash
# Transfer to target machine
scp rcc-mqtt-plotter-prebuilt.tar.gz user@target-machine:~/

# On target machine
cd ~
tar -xzf rcc-mqtt-plotter-prebuilt.tar.gz
cd rcc-mqtt-plotter/

# Manual deployment (since we have pre-built JAR)
cp build/rcc-mqtt-plotter-standalone.jar ~/JMRI/lib/rcc-mqtt-plotter.jar
cp config.properties ~/JMRI/
cp *.py ~/JMRI/jython/

# Create launcher script
cat > ~/JMRI/launch-rcc-plotter.sh << 'EOF'
#!/bin/bash
cd ~/JMRI
DISPLAY=${DISPLAY:-:0} java -jar lib/rcc-mqtt-plotter.jar &
echo "RCC MQTT Data Plotter launched"
EOF
chmod +x ~/JMRI/launch-rcc-plotter.sh

# Create desktop shortcut
mkdir -p ~/Desktop
cat > ~/Desktop/RCC-MQTT-Plotter.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=RCC MQTT Data Plotter
Comment=Real-time locomotive telemetry visualization
Exec=/home/$(whoami)/JMRI/launch-rcc-plotter.sh
Icon=applications-engineering
Terminal=false
Categories=Application;Engineering;
EOF
chmod +x ~/Desktop/RCC-MQTT-Plotter.desktop
```

### **Method 3: Minimal Manual Deployment**

**For systems where you only need the core functionality:**

```bash
# 1. Copy just the JAR file
scp ~/JMRI/lib/rcc-mqtt-plotter.jar user@target-machine:~/JMRI/lib/

# 2. Copy configuration
scp ~/JMRI/config.properties user@target-machine:~/JMRI/

# 3. Create simple launcher on target machine
ssh user@target-machine "cat > ~/JMRI/launch-rcc-plotter.sh << 'EOF'
#!/bin/bash
cd ~/JMRI
java -jar lib/rcc-mqtt-plotter.jar
EOF"

ssh user@target-machine "chmod +x ~/JMRI/launch-rcc-plotter.sh"
```

## ⚙️ **Configuration for Third-Party Deployment**

### **Update MQTT Broker Settings**
Edit `config.properties` on the target machine:

```properties
# Update broker IP to match your network
mqtt.broker=tcp://YOUR_MQTT_BROKER_IP:1883
mqtt.topic=cab/+/heartbeat/values
mqtt.client.id=RCC_MQTT_Plotter_TARGET_MACHINE

# Adjust display settings if needed
window.width=1000
window.height=700
auto.connect=true
```

### **Network Configuration**
```bash
# Ensure MQTT broker is accessible
telnet YOUR_MQTT_BROKER_IP 1883

# If using firewall, open MQTT port
sudo ufw allow 1883/tcp

# For VNC/remote display
export DISPLAY=:0  # or appropriate display number
```

## 🖥️ **Platform-Specific Notes**

### **Linux (Ubuntu/Debian)**
```bash
# Install Java if needed
sudo apt update
sudo apt install openjdk-17-jdk

# For headless systems with VNC
sudo apt install xvfb
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &
```

### **macOS**
```bash
# Install Java if needed
brew install openjdk@17

# JMRI typically installed in /Applications/JMRI/
# Adjust paths accordingly in deployment scripts
```

### **Windows**
```powershell
# Ensure Java is installed and in PATH
java -version

# JMRI typically in C:\Program Files\JMRI\
# Use PowerShell or Git Bash for deployment
```

## 🔍 **Troubleshooting Third-Party Deployment**

### **Common Issues and Solutions**

**Java Version Issues**:
```bash
# Check Java version
java -version
# Should be 11 or higher

# If wrong version, update JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

**MQTT Connection Issues**:
```bash
# Test MQTT connectivity
mosquitto_sub -h YOUR_BROKER_IP -t "cab/+/heartbeat/values" -C 5

# Check firewall
sudo netstat -tlnp | grep 1883
```

**Display Issues**:
```bash
# For headless systems
export DISPLAY=:0
# or
export DISPLAY=localhost:10.0  # for SSH X11 forwarding
```

**JMRI Integration Issues**:
```bash
# Verify JMRI installation
ls ~/JMRI/jmri.jar ~/JMRI/lib/

# Check Python script permissions
ls -la ~/JMRI/jython/*.py
```

## 📋 **Deployment Checklist**

- [ ] Java 11+ installed and working
- [ ] JMRI 5.0+ installed and tested
- [ ] Network connectivity to MQTT broker verified
- [ ] Display environment configured (DISPLAY variable set)
- [ ] JAR file copied to `~/JMRI/lib/rcc-mqtt-plotter.jar`
- [ ] Configuration file at `~/JMRI/config.properties`
- [ ] Launcher script at `~/JMRI/launch-rcc-plotter.sh`
- [ ] Python scripts in `~/JMRI/jython/` (for button integration)
- [ ] Desktop shortcut created (optional)
- [ ] Test launch: `~/JMRI/launch-rcc-plotter.sh`

## 🚀 **Quick Deployment Script**

For automated deployment to multiple machines:

```bash
#!/bin/bash
# quick-deploy.sh - Deploy RCC MQTT Plotter to remote machine

TARGET_HOST="$1"
TARGET_USER="$2"

if [ -z "$TARGET_HOST" ] || [ -z "$TARGET_USER" ]; then
    echo "Usage: $0 <target-host> <target-user>"
    echo "Example: $0 192.168.1.100 jmri"
    exit 1
fi

echo "Deploying RCC MQTT Plotter to $TARGET_USER@$TARGET_HOST..."

# Copy files
scp ~/JMRI/lib/rcc-mqtt-plotter.jar $TARGET_USER@$TARGET_HOST:~/JMRI/lib/
scp ~/JMRI/config.properties $TARGET_USER@$TARGET_HOST:~/JMRI/
scp ~/JMRI/launch-rcc-plotter.sh $TARGET_USER@$TARGET_HOST:~/JMRI/
scp ~/JMRI/jython/Test*.py $TARGET_USER@$TARGET_HOST:~/JMRI/jython/

# Set permissions
ssh $TARGET_USER@$TARGET_HOST "chmod +x ~/JMRI/launch-rcc-plotter.sh"

echo "Deployment complete! Test with: ssh $TARGET_USER@$TARGET_HOST '~/JMRI/launch-rcc-plotter.sh'"
```

## ✅ **Verification**

After deployment, verify everything works:

```bash
# Test JAR execution
cd ~/JMRI && java -jar lib/rcc-mqtt-plotter.jar

# Test launcher script
~/JMRI/launch-rcc-plotter.sh

# Test JMRI button integration
# In JMRI: Scripting → Script Entry → Load TestRccButton.py → Execute
```

The RCC MQTT Data Plotter is designed to be highly portable and should work on any system with Java 11+ and JMRI 5.0+. The main considerations are network connectivity to your MQTT broker and proper display configuration for the GUI.