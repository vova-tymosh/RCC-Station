#!/bin/bash

# Build script for standalone RCC MQTT Data Plotter
echo "Building RCC MQTT Data Plotter (Standalone)..."

# Create build directory
mkdir -p build/classes
mkdir -p build/lib

# Download dependencies
echo "Downloading dependencies..."
cd build/lib

# MQTT Client
if [ ! -f "org.eclipse.paho.client.mqttv3-1.2.5.jar" ]; then
    curl -s -L -o "org.eclipse.paho.client.mqttv3-1.2.5.jar" https://repo1.maven.org/maven2/org/eclipse/paho/org.eclipse.paho.client.mqttv3/1.2.5/org.eclipse.paho.client.mqttv3-1.2.5.jar
fi

# JFreeChart
if [ ! -f "jfreechart-1.5.3.jar" ]; then
    curl -s -L -o "jfreechart-1.5.3.jar" https://repo1.maven.org/maven2/org/jfree/jfreechart/1.5.3/jfreechart-1.5.3.jar
fi

# JSON
if [ ! -f "json-20230227.jar" ]; then
    curl -s -L -o "json-20230227.jar" https://repo1.maven.org/maven2/org/json/json/20230227/json-20230227.jar
fi

cd ../..

# Compile only the standalone version
echo "Compiling standalone version..."
javac -cp "build/lib/*" -d build/classes src/main/java/jmri/jmrix/rcc/RccMqttDataPlotterStandalone.java

if [ $? -eq 0 ]; then
    echo "Compilation successful!"
    
    # Create fat JAR
    echo "Creating executable JAR..."
    cd build
    mkdir -p temp
    cd temp
    
    # Extract all dependency JARs
    for jar in ../lib/*.jar; do
        jar xf "$jar"
    done
    
    # Add our classes
    cp -r ../classes/* .
    
    # Create manifest
    echo "Main-Class: jmri.jmrix.rcc.RccMqttDataPlotterStandalone" > manifest.txt
    
    # Create final executable JAR
    jar cfm ../jars/rcc-mqtt-plotter-standalone.jar manifest.txt .
    
    cd ../..
    
    echo "Build complete!"
    echo "Executable JAR: build/jars/rcc-mqtt-plotter-standalone.jar"
    ls -la build/jars/rcc-mqtt-plotter-standalone.jar
else
    echo "Compilation failed!"
    exit 1
fi