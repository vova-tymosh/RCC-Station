#!/bin/bash

# Master build script for RCC MQTT Data Plotter
echo "🚀 RCC MQTT Data Plotter - Master Build Script"
echo "=============================================="

# Ensure build directory structure exists
mkdir -p build/{scripts,jars,packages,python,temp}

# Run the build
echo ""
echo "📦 Building standalone JAR..."
./build/scripts/build-standalone.sh

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "📁 Build artifacts:"
    echo "- JAR: build/jars/rcc-mqtt-plotter-standalone.jar"
    echo "- Scripts: build/scripts/"
    echo "- Python: build/python/"
    echo "- Packages: build/packages/"
    echo ""
    echo "🚀 Next steps:"
    echo "1. Create deployment package: ./build/scripts/create-deployment-package-simple.sh"
    echo "2. Deploy to DecoderPro: ./build/scripts/deploy-to-decoderpro.sh"
    echo "3. Test standalone: java -jar build/jars/rcc-mqtt-plotter-standalone.jar"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi