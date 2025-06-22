#!/bin/bash
# Script to run the GUI proof of concept

echo "WireGuard Visual Configuration Editor - Proof of Concept"
echo "========================================================"
echo ""

# Check if NiceGUI is installed
if ! python -c "import nicegui" 2>/dev/null; then
    echo "Error: NiceGUI is not installed"
    echo "Installing NiceGUI..."
    pip install nicegui
fi

# Run the POC
echo "Starting POC application..."
echo "Open your browser to: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")/.."
python -m wg_mesh_gen.gui.poc_app