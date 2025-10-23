#!/bin/bash

# Clean build artifacts
echo "🧹 Cleaning build artifacts..."

# Remove build outputs
rm -rf build/classes
rm -rf build/lib
rm -rf build/temp
rm -f build/jars/*.jar
rm -f build/packages/*.tar.gz
rm -rf build/packages/rcc-mqtt-plotter-deployment*

echo "✅ Build artifacts cleaned!"
echo ""
echo "Remaining structure:"
ls -la build/