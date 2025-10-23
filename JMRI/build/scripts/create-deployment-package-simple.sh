#!/bin/bash

# Simple deployment package creator for RCC MQTT Data Plotter
echo "Creating RCC MQTT Data Plotter deployment package..."

PACKAGE_NAME="rcc-mqtt-plotter-deployment-$(date +%Y%m%d)"

# Create package directory
mkdir -p "$PACKAGE_NAME"

# Copy essential files
echo "Copying files..."
cp build/jars/rcc-mqtt-plotter-standalone.jar "$PACKAGE_NAME/"
cp config.properties "$PACKAGE_NAME/"
cp build/python/*.py "$PACKAGE_NAME/" 2>/dev/null || true
cp DEPLOYMENT_GUIDE.md "$PACKAGE_NAME/"
cp DECODERPRO_INTEGRATION.md "$PACKAGE_NAME/"
cp SPECIFICATIONS.md "$PACKAGE_NAME/"

# Create simple deployment script
cat > "$PACKAGE_NAME/deploy.sh" << 'EOF'
#!/bin/bash
# RCC MQTT Data Plotter Deployment Script

echo "Deploying RCC MQTT Data Plotter..."

# Check JMRI installation
if [ ! -d "$HOME/JMRI" ]; then
    echo "Error: JMRI not found at $HOME/JMRI"
    echo "Please install JMRI first"
    exit 1
fi

# Create directories
mkdir -p "$HOME/JMRI/lib"
mkdir -p "$HOME/JMRI/jython"

# Deploy files
echo "Installing JAR..."
cp rcc-mqtt-plotter-standalone.jar "$HOME/JMRI/lib/rcc-mqtt-plotter.jar"

echo "Installing configuration..."
cp config.properties "$HOME/JMRI/"

echo "Installing Python scripts..."
cp *.py "$HOME/JMRI/jython/" 2>/dev/null || true

# Create launcher
echo "Creating launcher script..."
cat > "$HOME/JMRI/launch-rcc-plotter.sh" << 'LAUNCHER_EOF'
#!/bin/bash
cd ~/JMRI
DISPLAY=${DISPLAY:-:0} java -jar lib/rcc-mqtt-plotter.jar &
echo "RCC MQTT Data Plotter launched"
LAUNCHER_EOF

chmod +x "$HOME/JMRI/launch-rcc-plotter.sh"

# Create desktop shortcut
echo "Creating desktop shortcut..."
mkdir -p "$HOME/Desktop"
cat > "$HOME/Desktop/RCC-MQTT-Plotter.desktop" << 'DESKTOP_EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=RCC MQTT Data Plotter
Comment=Real-time locomotive telemetry visualization
Exec=EXEC_PATH_PLACEHOLDER
Icon=applications-engineering
Terminal=false
Categories=Application;Engineering;
DESKTOP_EOF

# Replace placeholder with actual path
sed -i "s|EXEC_PATH_PLACEHOLDER|$HOME/JMRI/launch-rcc-plotter.sh|g" "$HOME/Desktop/RCC-MQTT-Plotter.desktop"
chmod +x "$HOME/Desktop/RCC-MQTT-Plotter.desktop"

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "Installed files:"
echo "- JAR: $HOME/JMRI/lib/rcc-mqtt-plotter.jar"
echo "- Config: $HOME/JMRI/config.properties"
echo "- Launcher: $HOME/JMRI/launch-rcc-plotter.sh"
echo "- Desktop shortcut: $HOME/Desktop/RCC-MQTT-Plotter.desktop"
echo "- Python scripts: $HOME/JMRI/jython/*.py"
echo ""
echo "🚀 How to launch:"
echo "1. Double-click desktop shortcut: 'RCC MQTT Data Plotter'"
echo "2. Terminal: ~/JMRI/launch-rcc-plotter.sh"
echo "3. DecoderPro button: Scripting → Script Entry → Load TestRccButton.py → Execute"
echo ""
echo "⚙️ Configuration:"
echo "Edit $HOME/JMRI/config.properties to change MQTT broker settings"
echo ""
echo "📊 The plotter will show 6 real-time charts for locomotive telemetry data"
EOF

chmod +x "$PACKAGE_NAME/deploy.sh"

# Create README for the package
cat > "$PACKAGE_NAME/README.md" << 'EOF'
# RCC MQTT Data Plotter - Deployment Package

## Quick Start

1. **Extract this package** to any directory
2. **Run the deployment script**: `./deploy.sh`
3. **Edit configuration** (if needed): `~/JMRI/config.properties`
4. **Launch**: Double-click desktop shortcut or run `~/JMRI/launch-rcc-plotter.sh`

## What This Package Contains

- **rcc-mqtt-plotter-standalone.jar** - The main application (1.9MB)
- **config.properties** - Configuration file (MQTT broker, UI settings)
- **TestRccButton.py** - Creates a launch button in JMRI
- **deploy.sh** - Automated deployment script
- **Documentation** - Complete guides and specifications

## Requirements

- **Java 11+** (check with `java -version`)
- **JMRI 5.0+** installed at `~/JMRI/`
- **Network access** to MQTT broker
- **Display capability** (local display, X11, or VNC)

## Features

- **6 Real-time Charts**: Speed, Throttle, Battery, Current, Temperature, Pressure
- **Multi-locomotive Support**: Auto-discovery and color-coded tracking
- **MQTT Integration**: Native RCC heartbeat protocol support
- **Distance Tracking**: Live distance monitoring per locomotive
- **DecoderPro Integration**: Button integration for easy access

## Configuration

Edit `~/JMRI/config.properties` after deployment:

```properties
# Change this to your MQTT broker IP
mqtt.broker=tcp://192.168.20.62:1883
mqtt.topic=cab/+/heartbeat/values
auto.connect=true
```

## Support

See the included documentation files for detailed information:
- **DEPLOYMENT_GUIDE.md** - Detailed deployment instructions
- **DECODERPRO_INTEGRATION.md** - JMRI integration guide
- **SPECIFICATIONS.md** - Complete feature specifications

## Status

This is a fully functional, production-ready locomotive telemetry visualization tool.
EOF

# Create the compressed package
echo "Creating compressed package..."
tar -czf "build/packages/${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME/"
mv "$PACKAGE_NAME/" "build/packages/"

echo ""
echo "✅ Deployment package created!"
echo ""
echo "📦 Package: build/packages/${PACKAGE_NAME}.tar.gz"
echo "📁 Directory: build/packages/$PACKAGE_NAME/"
echo ""
echo "🚀 To deploy to a third-party machine:"
echo "1. Transfer: scp build/packages/${PACKAGE_NAME}.tar.gz user@target-machine:~/"
echo "2. Extract: tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "3. Deploy: cd $PACKAGE_NAME && ./deploy.sh"
echo "4. Configure: Edit ~/JMRI/config.properties (set MQTT broker IP)"
echo "5. Launch: ~/JMRI/launch-rcc-plotter.sh"