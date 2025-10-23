#!/bin/bash

# Deploy RCC MQTT Data Plotter to DecoderPro
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
./build-standalone.sh

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
cat > "$JMRI_HOME/launch-rcc-plotter.sh" << 'EOF'
#!/bin/bash
# RCC MQTT Data Plotter Launcher
cd ~/JMRI
DISPLAY=:0 java -jar lib/rcc-mqtt-plotter.jar &
echo "RCC MQTT Data Plotter launched"
EOF

chmod +x "$JMRI_HOME/launch-rcc-plotter.sh"

# Create a desktop shortcut
echo "Creating desktop shortcut..."
mkdir -p "$HOME/Desktop"
cat > "$HOME/Desktop/RCC-MQTT-Plotter.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=RCC MQTT Data Plotter
Comment=Real-time locomotive telemetry visualization
Exec=/home/vova/JMRI/launch-rcc-plotter.sh
Icon=applications-engineering
Terminal=false
Categories=Application;Engineering;
EOF

chmod +x "$HOME/Desktop/RCC-MQTT-Plotter.desktop"

# Create DecoderPro button integration
echo "Creating DecoderPro button integration..."
mkdir -p "$JMRI_HOME/jython"

# Copy the button integration script
cp build/python/RccMqttPlotterButton.py "$JMRI_HOME/jython/"

# Create a simple launcher script for manual use
cat > "$JMRI_HOME/jython/RccPlotterLauncher.py" << 'EOF'
# RCC MQTT Data Plotter Launcher for DecoderPro
# Run this script from JMRI Script Entry to launch the plotter

import subprocess
import os

def launchRccPlotter():
    try:
        jmri_home = os.path.expanduser("~/JMRI")
        launcher_script = os.path.join(jmri_home, "launch-rcc-plotter.sh")
        
        # Launch the plotter
        subprocess.Popen([launcher_script], shell=True)
        print("RCC MQTT Data Plotter launched successfully!")
        
    except Exception as e:
        print("Error launching RCC MQTT Data Plotter: " + str(e))

# Call the function
launchRccPlotter()
EOF

# Create startup action to automatically add the button
echo "Creating automatic button integration..."
cat > "$JMRI_HOME/jython/RccPlotterStartup.py" << 'EOF'
# RCC MQTT Data Plotter Startup Integration
# This script automatically adds a button to DecoderPro when JMRI starts

# Import the button integration
execfile(jmri.util.FileUtil.getExternalFilename("program:jython/RccMqttPlotterButton.py"))
EOF

echo "Deployment complete!"
echo ""
echo "Integration Summary:"
echo "- JAR: $JMRI_HOME/lib/rcc-mqtt-plotter.jar"
echo "- Config: $JMRI_HOME/config.properties"
echo "- Launcher: $JMRI_HOME/launch-rcc-plotter.sh"
echo "- Desktop shortcut: ~/Desktop/RCC-MQTT-Plotter.desktop"
echo "- Button integration: $JMRI_HOME/jython/RccMqttPlotterButton.py"
echo "- Startup script: $JMRI_HOME/jython/RccPlotterStartup.py"
echo "- Manual script: $JMRI_HOME/jython/RccPlotterLauncher.py"
echo ""
echo "How to launch:"
echo "1. DecoderPro Button: Look for 'RCC MQTT Plotter' button in main window (auto-added)"
echo "2. Desktop shortcut: Double-click 'RCC MQTT Data Plotter' icon"
echo "3. Terminal: ~/JMRI/launch-rcc-plotter.sh"
echo "4. JMRI Script: Scripting → Script Entry → Load RccPlotterLauncher.py → Execute"
echo ""
echo "To activate the DecoderPro button:"
echo "1. Restart DecoderPro (button will be added automatically)"
echo "2. OR manually run: Scripting → Script Entry → Load RccMqttPlotterButton.py → Execute"