#!/usr/bin/env bash
set -e

CURRENT_VERSION="1.1.0"
VERSION_URL="https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/VERSION"
REPO_URL="https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main"
INSTALL_DIR="/root/Metrics"
VERSION_FILE="$INSTALL_DIR/.version"

echo "================================================"
echo " MTProxyMax Metrics Viewer - Installer v${CURRENT_VERSION}"
echo "================================================"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root"
    echo "Usage: sudo bash install.sh"
    exit 1
fi

# Check for --auto flag
AUTO_MODE=false
for arg in "$@"; do
    if [ "$arg" = "--auto" ]; then
        AUTO_MODE=true
    fi
done

echo "[1/7] Checking system dependencies..."

# Функция для проверки наличия пакета
check_package_installed() {
    dpkg -s "$1" &> /dev/null
    return $?
}

# Список необходимых пакетов
REQUIRED_PACKAGES="python3 python3-pip python3-venv curl wget"
PACKAGES_TO_INSTALL=""

# Проверяем каждый пакет
for pkg in $REQUIRED_PACKAGES; do
    if ! check_package_installed "$pkg"; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $pkg"
    fi
done

# Устанавливаем только отсутствующие пакеты
if [ -n "$PACKAGES_TO_INSTALL" ]; then
    echo "       Installing missing packages:$PACKAGES_TO_INSTALL"
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y $PACKAGES_TO_INSTALL > /dev/null 2>&1
    echo "       ✓ Packages installed"
else
    echo "       ✓ All dependencies already installed"
fi

echo "[2/7] Checking version..."

REMOTE_VERSION=$(curl -sSL "$VERSION_URL" 2>/dev/null | tr -d '[:space:]')

if [ -z "$REMOTE_VERSION" ]; then
    echo "       Could not fetch remote version, continuing with install..."
    REMOTE_VERSION="$CURRENT_VERSION"
fi

# ИСПРАВЛЕНО: была опечатка "INSTALL_DIR" вместо "$INSTALL_DIR"
if [ -d "$INSTALL_DIR" ] && [ -f "$VERSION_FILE" ]; then
    LOCAL_VERSION=$(cat "$VERSION_FILE" 2>/dev/null | tr -d '[:space:]')

    if [ -z "$LOCAL_VERSION" ]; then
        LOCAL_VERSION="unknown"
    fi

    echo "       Installed version: $LOCAL_VERSION"
    echo "       Latest version:    $REMOTE_VERSION"
    echo ""

    if [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ]; then
        echo "================================================"
        echo "  You already have the latest version!"
        echo "================================================"
        echo ""
        
        if [ "$AUTO_MODE" = true ]; then
            echo "Auto mode: reinstalling anyway..."
            rm -rf "$INSTALL_DIR"
            rm -f /usr/local/bin/metrics
            rm -f /usr/local/bin/metrics-live
        else
            echo "Options:"
            echo "  1) Reinstall anyway"
            echo "  2) Cancel"
            echo ""
            read -p "Your choice (1 or 2): " choice < /dev/tty 2>/dev/null || choice="1"
            
            case $choice in
                1)
                    echo ""
                    echo "Reinstalling..."
                    rm -rf "$INSTALL_DIR"
                    rm -f /usr/local/bin/metrics
                    rm -f /usr/local/bin/metrics-live
                    ;;
                *)
                    echo ""
                    echo "Installation cancelled"
                    exit 0
                    ;;
            esac
        fi
    else
        echo "================================================"
        echo "  Update available!"
        echo "  $LOCAL_VERSION -> $REMOTE_VERSION"
        echo "================================================"
        echo ""
        
        if [ "$AUTO_MODE" = true ]; then
            echo "Auto mode: updating..."
            rm -rf "$INSTALL_DIR"
            rm -f /usr/local/bin/metrics
            rm -f /usr/local/bin/metrics-live
        else
            echo "Options:"
            echo "  1) Update to $REMOTE_VERSION (recommended)"
            echo "  2) Cancel"
            echo ""
            read -p "Your choice (1 or 2): " choice < /dev/tty 2>/dev/null || choice="1"
            
            case $choice in
                1)
                    echo ""
                    echo "Updating..."
                    rm -rf "$INSTALL_DIR"
                    rm -f /usr/local/bin/metrics
                    rm -f /usr/local/bin/metrics-live
                    ;;
                *)
                    echo ""
                    echo "Update cancelled"
                    exit 0
                    ;;
            esac
        fi
    fi

elif [ -d "$INSTALL_DIR" ]; then
    echo "       Installed version: unknown (no version file)"
    echo "       Latest version:    $REMOTE_VERSION"
    echo ""

    if [ "$AUTO_MODE" = true ]; then
        echo "Auto mode: reinstalling..."
        rm -rf "$INSTALL_DIR"
        rm -f /usr/local/bin/metrics
        rm -f /usr/local/bin/metrics-live
    else
        echo "Existing installation found without version info."
        echo ""
        echo "Options:"
        echo "  1) Remove and install $REMOTE_VERSION (recommended)"
        echo "  2) Cancel"
        echo ""
        read -p "Your choice (1 or 2): " choice < /dev/tty 2>/dev/null || choice="1"
        
        case $choice in
            1)
                echo ""
                echo "Removing old installation..."
                rm -rf "$INSTALL_DIR"
                rm -f /usr/local/bin/metrics
                rm -f /usr/local/bin/metrics-live
                ;;
            *)
                echo ""
                echo "Installation cancelled"
                exit 0
                ;;
        esac
    fi
else
    echo "       Fresh install: $REMOTE_VERSION"
fi

echo ""
echo "[3/7] Creating directory structure..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "       ✓ OK"

echo "[4/7] Setting up Python virtual environment..."

# Проверяем, существует ли уже venv и работает ли он
VENV_OK=false
if [ -d "$INSTALL_DIR/venv" ] && [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
    # Проверяем работоспособность venv
    if source "$INSTALL_DIR/venv/bin/activate" 2>/dev/null; then
        # Проверяем наличие необходимых пакетов
        if python3 -c "import requests; import rich" 2>/dev/null; then
            VENV_OK=true
            echo "       ✓ Virtual environment already configured"
            deactivate
        else
            deactivate
        fi
    fi
fi

if [ "$VENV_OK" = false ]; then
    echo "       Creating virtual environment..."
    rm -rf "$INSTALL_DIR/venv" 2>/dev/null || true
    python3 -m venv venv
    source venv/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet requests rich
    deactivate
    echo "       ✓ Virtual environment created"
fi

echo "[5/7] Downloading viewer scripts..."
curl -sSL -o "$INSTALL_DIR/metrics_viewer.py" "$REPO_URL/src/metrics_viewer.py"
curl -sSL -o "$INSTALL_DIR/metrics_live.py" "$REPO_URL/src/metrics_live.py"

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
echo "       ✓ OK"

echo "[6/7] Creating wrapper scripts..."

cat > "$INSTALL_DIR/metrics" << 'EOF'
#!/bin/bash
cd /root/Metrics
source venv/bin/activate
python3 metrics_viewer.py "$@"
deactivate
EOF
chmod +x "$INSTALL_DIR/metrics"

cat > "$INSTALL_DIR/metrics-live" << 'EOF'
#!/bin/bash
cd /root/Metrics
source venv/bin/activate
python3 metrics_live.py
deactivate
EOF
chmod +x "$INSTALL_DIR/metrics-live"

echo "       ✓ OK"

echo "[7/7] Finalizing installation..."
ln -sf "$INSTALL_DIR/metrics" /usr/local/bin/metrics
ln -sf "$INSTALL_DIR/metrics-live" /usr/local/bin/metrics-live
echo "$REMOTE_VERSION" > "$VERSION_FILE"
echo "       ✓ OK"

echo ""
echo "================================================"
echo " Installation completed successfully!"
echo " Version: $REMOTE_VERSION"
echo "================================================"
echo ""
echo "Available commands:"
echo "  metrics      - View all metrics"
echo "  metrics-live - Live auto-refresh mode"
echo ""
echo "Usage examples:"
echo "  metrics"
echo "  metrics --section status"
echo "  metrics --section users"
echo "  metrics --section me"
echo "  metrics --section upstream"
echo "  metrics --section floor"
echo "  metrics --section outage"
echo "  metrics --section pool"
echo "  metrics --section security"
echo "  metrics --section socks"
echo "  metrics --section relay"
echo "  metrics-live"
echo ""
echo "Check for updates:"
echo "  sudo bash -c \"\$(curl -fsSL $REPO_URL/install.sh)\""
echo ""
echo "Documentation:"
echo "  https://github.com/Liafanx/mtproxymax-metrics"
echo ""
