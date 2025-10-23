#!/bin/bash

# Deploy RCC MQTT Data Plotter to DecoderPro (Simplified - No Button Integration)
echo "Deploying RCC MQTT Data Plotter to DecoderPro..."

JMRI_HOME="$HOME/JMRI"
EXTENSION_DIR="$HOME/jmri-rcc-extension"

# Check if JMRI is installed
if [ ! -d "$JMRI_HOME" ]; then
    echo "Error: JMRI not found at $JMRI_HOME"
    exit 1
fi

# Build the extension
echo "Building extension..."
cd "$EXTENSION_DIR"
./build/scripts/build-standalone.sh

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

# Copy the JAR to JMRI lib directory
echo "Copying JAR to JMRI lib directory..."
cp build/jars/rcc-mqtt-plotter-standalone.jar "$JMRI_HOME/lib/rcc-mqtt-plotter.jar"

# Copy configuration file
echo "Copying configuration..."
cp config.properties "$JMRI_HOME/"

# Create a simple launcher script
echo "Creating launcher script..."
cat > "$JMRI_HOME/launch-rcc-plotter.sh" << 'LAUNCHER_EOF'
#!/bin/bash
# RCC MQTT Data Plotter Launcher
cd ~/JMRI
DISPLAY=:0 java -jar lib/rcc-mqtt-plotter.jar &
echo "RCC MQTT Data Plotter launched"
LAUNCHER_EOF

chmod +x "$JMRI_HOME/launch-rcc-plotter.sh"

# Create a desktop shortcut
echo "Creating desktop shortcut..."
mkdir -p "$HOME/Desktop"
cat > "$HOME/Desktop/RCC-MQTT-Plotter.desktop" << 'DESKTOP_EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=RCC MQTT Data Plotter
Comment=Real-time locomotive telemetry visualization
Exec=/home/vova/JMRI/launch-rcc-plotter.sh
Icon=applications-engineering
Terminal=false
Categories=Application;Engineering;
DESKTOP_EOF

chmod +x "$HOME/Desktop/RCC-MQTT-Plotter.desktop"

echo "Deployment complete!"
echo ""
echo "Integration Summary:"
echo "- JAR: $JMRI_HOME/lib/rcc-mqtt-plotter.jar"
echo "- Config: $JMRI_HOME/config.properties"
echo "- Launcher: $JMRI_HOME/launch-rcc-plotter.sh"
echo "- Desktop shortcut: ~/Desktop/RCC-MQTT-Plotter.desktop"
echo ""
echo "How to launch:"
echo "1. Desktop shortcut: Double-click 'RCC MQTT Data Plotter' icon"
echo "2. Terminal: ~/JMRI/launch-rcc-plotter.sh"
echo "3. Direct: java -jar ~/JMRI/lib/rcc-mqtt-plotter.jar"
echo ""
echo "Configuration: Edit ~/JMRI/config.properties to change MQTT broker settings"
