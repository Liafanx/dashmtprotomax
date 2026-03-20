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
    echo "  Existing installation found!"
    echo "================================================"
    echo ""
    echo "Directory: $INSTALL_DIR"
    echo ""
    
    # Проверяем, есть ли интерактивный терминал
    if [ ! -t 0 ]; then
        # Если запущено ��ерез pipe - автоматически переустанавливаем
        echo "Auto-reinstalling (non-interactive mode)..."
        rm -rf "$INSTALL_DIR"
        rm -f /usr/local/bin/metrics
        rm -f /usr/local/bin/metrics-live
        echo "Old installation removed"
    else
        # Если интерактивный режим - спрашиваем
        echo "Options:"
        echo "  1) Remove and reinstall (recommended)"
        echo "  2) Cancel installation"
        echo ""
        read -p "Your choice (1 or 2): " choice
        
        case $choice in
            1)
                echo ""
                echo "Removing old installation..."
                rm -rf "$INSTALL_DIR"
                rm -f /usr/local/bin/metrics
                rm -f /usr/local/bin/metrics-live
                echo "Done"
                ;;
            2)
                echo ""
                echo "Installation cancelled"
                exit 0
                ;;
            *)
                echo ""
                echo "Invalid choice. Installation cancelled"
                exit 1
                ;;
        esac
    fi
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
echo "  Installation completed successfully!"
echo "================================================"
echo ""
echo "Available commands:"
echo "  metrics              - View all metrics"
echo "  metrics-live         - Live auto-refresh mode"
echo ""
echo "Usage examples:"
echo "  metrics"
echo "  metrics --section status"
echo "  metrics --section users"
echo "  metrics-live"
echo ""
echo "Documentation:"
echo "  https://github.com/Liafanx/mtproxymax-metrics"
echo ""
