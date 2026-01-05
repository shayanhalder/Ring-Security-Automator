#!/bin/bash
# Quick start script for the server
# Run this on your home server laptop

echo "===== Ring Security Automator - Server Setup ====="
echo ""

# Check if required files exist
echo "Checking required files..."
REQUIRED_FILES=("setup.py" "security_api.py" "face_encodings.npy" "yolo11n_ncnn_model" "models")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -e "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "ERROR: Missing required files/directories:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "Please copy these files from the Raspberry Pi to the server."
    exit 1
fi

echo "✓ All required files found"
echo ""

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import flask, cv2, numpy, insightface, ultralytics" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Missing Python dependencies. Installing..."
    pip install flask opencv-python numpy ultralytics insightface
else
    echo "✓ All dependencies installed"
fi

echo ""
echo "Getting server IP address..."
if command -v hostname &> /dev/null; then
    IP=$(hostname -I | awk '{print $1}')
    echo "Server IP: $IP"
    echo ""
    echo "On the Raspberry Pi, edit tripwire_client.py and set:"
    echo "  SERVER_URL = \"http://$IP:5000\""
fi

echo ""
echo "Starting Flask server on port 5000..."
echo "Press Ctrl+C to stop"
echo ""

python3 server.py
