#!/usr/bin/env bash
set -e

echo "================================================"
echo "  MTProtoMax Metrics Viewer - Installer v1.0"
echo "================================================"
echo ""

if [ "$EUID" -ne 0 ]; then
   echo "ERROR: Please run as root"
   echo "Usage: sudo bash install.sh"
   exit 1
fi

echo "[1/6] Installing system dependencies..."
apt-get update -qq > /dev/null 2>&1
apt-get install -y python3 python3-pip python3-venv curl wget > /dev/null 2>&1
echo "       OK"

INSTALL_DIR="/root/Metrics"

if [ -d "$INSTALL_DIR" ]; then
    echo ""
    echo "================================================"
    echo "  Existing installation found at:"
    echo "  $INSTALL_DIR"
    echo "================================================"
    echo ""
    
    while true; do
        read -p "Remove and reinstall? (y/n): " yn < /dev/tty
        case $yn in
            [Yy]* )
                echo ""
                echo "Removing old installation..."
                rm -rf "$INSTALL_DIR"
                rm -f /usr/local/bin/metrics
                rm -f /usr/local/bin/metrics-live
                echo "Done"
                break
                ;;
            [Nn]* )
                echo ""
                echo "Installation cancelled"
                exit 0
                ;;
            * )
                echo "Please answer y or n"
                ;;
        esac
    done
fi

echo ""
echo "[2/6] Creating directory structure..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "       OK"

echo "[3/6] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet requests rich
deactivate
echo "       OK"

echo "[4/6] Downloading viewer scripts..."
curl -sSL -o "$INSTALL_DIR/metrics_viewer.py" https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/src/metrics_viewer.py
curl -sSL -o "$INSTALL_DIR/metrics_live.py" https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/src/metrics_live.py

if [ ! -f "$INSTALL_DIR/metrics_viewer.py" ]; then
    echo "ERROR: Failed to download metrics_viewer.py"
    exit 1
fi

if [ ! -f "$INSTALL_DIR/metrics_live.py" ]; then
    echo "ERROR: Failed to download metrics_live.py"
    exit 1
fi

chmod +x "$INSTALL_DIR/metrics_viewer.py"
chmod +x "$INSTALL_DIR/metrics_live.py"
echo "       OK"

echo "[5/6] Creating wrapper scripts..."

echo '#!/bin/bash' > "$INSTALL_DIR/metrics"
echo 'cd /root/Metrics' >> "$INSTALL_DIR/metrics"
echo 'source venv/bin/activate' >> "$INSTALL_DIR/metrics"
echo 'python3 metrics_viewer.py "$@"' >> "$INSTALL_DIR/metrics"
echo 'deactivate' >> "$INSTALL_DIR/metrics"
chmod +x "$INSTALL_DIR/metrics"

echo '#!/bin/bash' > "$INSTALL_DIR/metrics-live"
echo 'cd /root/Metrics' >> "$INSTALL_DIR/metrics-live"
echo 'source venv/bin/activate' >> "$INSTALL_DIR/metrics-live"
echo 'python3 metrics_live.py' >> "$INSTALL_DIR/metrics-live"
echo 'deactivate' >> "$INSTALL_DIR/metrics-live"
chmod +x "$INSTALL_DIR/metrics-live"

echo "       OK"

echo "[6/6] Creating global commands..."
ln -sf "$INSTALL_DIR/metrics" /usr/local/bin/metrics
ln -sf "$INSTALL_DIR/metrics-live" /usr/local/bin/metrics-live
echo "       OK"

echo ""
echo "================================================"
echo "  Installation completed!"
echo "================================================"
echo ""
echo "Quick start:"
echo "  metrics         - view metrics"
echo "  metrics-live    - live mode"
echo ""
echo "More info: github.com/Liafanx/mtproxymax-metrics"
echo ""
