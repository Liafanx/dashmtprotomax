# MTProxyMax Metrics Viewer

> 🌍 **Translations:** [English](README.md) | [Русский](README_RU.md)

Beautiful terminal dashboard for monitoring [MTProxyMax](https://github.com/SamNet-dev/MTProxyMax) Telegram proxy with Prometheus metrics.

[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/Liafanx/mtproxymax-metrics)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MTProxyMax](https://img.shields.io/badge/MTProxyMax-required-orange.svg)](https://github.com/SamNet-dev/MTProxyMax)

## 📋 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Reinstall](#-reinstall)
- [Uninstall](#-uninstall)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Screenshots](#-screenshots)
- [Metrics Reference](#-metrics-reference)
- [License](#-license)
- [Related Projects](#-related-projects)
- [Support](#-support)
- [Important Notes](#-important-notes)
- [Changelog](#-changelog)

## ✨ Features

- 📊 **Real-time metrics visualization** - Beautiful terminal UI with colors and tables
- 👥 **User statistics** - Monitor connections, traffic, and messages per user
- 🔼 **Upstream monitoring** - Track connection success rates and duration
- 🔄 **ME statistics** - Multiplexed Endpoint performance metrics
- 🎯 **SOCKS KDF Policy** - Monitor authentication and policy enforcement
- ⚡ **Live mode** - Auto-refresh dashboard every 5 seconds
- 🎨 **Rich terminal UI** - Powered by Python Rich library

## 📦 Requirements

> ⚠️ **Important:** This tool requires [MTProxyMax](https://github.com/SamNet-dev/MTProxyMax) to be installed and running with Prometheus metrics enabled.

### System Requirements

- **Operating System:** Ubuntu 22.04/24.04 or Debian 11/12
- **Python:** 3.10 or higher
- **Access:** Root/sudo privileges
- **MTProxyMax:** [Install MTProxyMax first](https://github.com/SamNet-dev/MTProxyMax)

### Check if MTProxyMax metrics are available

```bash
curl http://localhost:9090/metrics
```

If you see metrics output, you're ready to install the viewer.

## 🚀 Installation

### Quick Install

Install with reinstall (recommended):

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/install.sh)"
```

Or using wget:

```bash
sudo bash -c "$(wget -qO- https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/install.sh)"
```

### Install via Git

```bash
git clone https://github.com/Liafanx/mtproxymax-metrics.git
cd mtproxymax-metrics
sudo bash install.sh
```

## 📖 Usage

### Basic Commands

#### View All Metrics (Static)

```bash
metrics
```

This displays a comprehensive snapshot of all metrics including:
- System status and uptime
- Connection statistics
- Upstream performance
- ME statistics
- User statistics
- Pool management
- SOCKS KDF policy

#### Live Auto-Refresh Mode

```bash
metrics-live
```

Real-time dashboard that updates every 5 seconds. Press `Ctrl+C` to exit.

### View Specific Sections

```bash
# Status summary only
metrics --section status

# User statistics only
metrics --section users

# Upstream connection stats
metrics --section upstream

# ME (Multiplexed Endpoint) stats
metrics --section me

# Pool management stats
metrics --section pool

# SOCKS KDF policy stats
metrics --section socks

# System metrics table
metrics --section main
```

### Custom Metrics URL

If your MTProxyMax metrics are on a different host/port:

```bash
metrics --url http://your-server:9090/metrics
```

## 🔄 Reinstall

To reinstall or update to the latest version:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/install.sh)" -- --auto
```

This will automatically remove the old installation and install fresh.

## 🗑️ Uninstall

### Quick Uninstall

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/uninstall.sh)"
```

### Manual Uninstall

```bash
sudo rm -rf /root/Metrics
sudo rm -f /usr/local/bin/metrics
sudo rm -f /usr/local/bin/metrics-live
```

## ⚙️ Configuration

### Change Metrics URL

Edit the configuration files:

**For static viewer:**
```bash
sudo nano /root/Metrics/metrics_viewer.py
```

**For live viewer:**
```bash
sudo nano /root/Metrics/metrics_live.py
```

Change line 11:
```python
METRICS_URL = "http://localhost:9090/metrics"
```

### Change Live Mode Refresh Interval

Edit `/root/Metrics/metrics_live.py` line 12:
```python
REFRESH_INTERVAL = 5  # seconds
```

### Installed Files

```
/root/Metrics/
├── venv/                    # Python virtual environment
├── metrics_viewer.py        # Main viewer script
├── metrics_live.py          # Live viewer script
├── metrics                  # Wrapper script
└── metrics-live             # Live mode wrapper

/usr/local/bin/
├── metrics -> /root/Metrics/metrics
└── metrics-live -> /root/Metrics/metrics-live
```

## 🔧 Troubleshooting

### Metrics endpoint not accessible

**Problem:** `Error fetching metrics: Connection refused`

**Solution:**

1. Verify metrics endpoint:
   ```bash
   curl http://localhost:9090/metrics
   ```

2. Check MTProxyMax configuration for metrics port

### Python dependencies error

**Problem:** `ModuleNotFoundError: No module named 'rich'`

**Solution:**

Reinstall dependencies:
```bash
cd /root/Metrics
source venv/bin/activate
pip install --upgrade requests rich
deactivate
```

### Command not found

**Problem:** `bash: metrics: command not found`

**Solution:**

Recreate symlinks:
```bash
sudo ln -sf /root/Metrics/metrics /usr/local/bin/metrics
sudo ln -sf /root/Metrics/metrics-live /usr/local/bin/metrics-live
```

### Permissions error

**Problem:** `Permission denied`

**Solution:**

Ensure you're running as root:
```bash
sudo metrics
sudo metrics-live
```

Or fix permissions:
```bash
sudo chmod +x /root/Metrics/metrics*
```

## 📊 Screenshots

### Status Dashboard

```
================================================
  PROMETHEUS METRICS VIEWER
  MTProxyMax proxy metrics dashboard
================================================

┌─ Summary ──────────────────────────────────┐
│ Status: OK EXCELLENT                       │
│ Uptime: 2d 15h 42m                         │
│                                            │
│ Connections:                               │
│   Total:      45,892                       │
│   Authorized: 8,234 (17.9%)                │
│   Rejected:   37,658 (no valid secret)     │
│                                            │
│ Upstream:                                  │
│   Attempts: 125,678                        │
│   Success:  124,890                        │
│   Failed:   788                            │
│   Rate:     99.4%                          │
└────────────────────────────────────────────┘

┌─ User Statistics ──────────────────────────┐
│ User    │ Connections │ Active │ RX       │
├─────────┼─────────────┼────────┼──────────┤
│ admin   │ 25,234      │ 15     │ 45.2 GB  │
│ user1   │ 18,456      │ 8      │ 32.1 GB  │
│ user2   │ 12,890      │ 3      │ 18.5 GB  │
└─────────┴─────────────┴────────┴──────────┘
```

### Live Mode

Real-time auto-refreshing dashboard with color-coded status indicators.

## 📚 Metrics Reference

| Metric | Description |
|--------|-------------|
| `telemt_uptime_seconds` | Proxy server uptime in seconds |
| `telemt_connections_total` | Total number of accepted connections |
| `telemt_connections_bad_total` | Rejected connections without valid secret |
| `telemt_upstream_connect_attempt_total` | Total upstream connection attempts |
| `telemt_upstream_connect_success_total` | Successful upstream connections |
| `telemt_upstream_connect_fail_total` | Failed upstream connections |
| `telemt_me_reconnect_attempts_total` | ME reconnection attempts |
| `telemt_me_reconnect_success_total` | Successful ME reconnections |
| `telemt_user_connections_total` | Connections per user |
| `telemt_user_octets_from_client` | Bytes received from client per user |
| `telemt_user_octets_to_client` | Bytes sent to client per user |
| `telemt_user_msgs_from_client` | Messages received per user |
| `telemt_user_msgs_to_client` | Messages sent per user |

For complete metrics documentation, see [MTProxyMax Documentation](https://github.com/SamNet-dev/MTProxyMax).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- **[MTProxyMax](https://github.com/SamNet-dev/MTProxyMax)** - Fast and secure MTProto proxy (Required)
- **[Prometheus](https://prometheus.io/)** - Monitoring and alerting toolkit

## 💬 Support

- 🐛 **Bug reports:** [Open an issue](https://github.com/Liafanx/mtproxymax-metrics/issues)
- 💡 **Feature requests:** [Open an issue](https://github.com/Liafanx/mtproxymax-metrics/issues)
- 📖 **Documentation:** [Wiki](https://github.com/Liafanx/mtproxymax-metrics/wiki)
- ⭐ **Star this repo** if you find it useful!

## ⚠️ Important Notes

1. **MTProxyMax Required:** This viewer only works with [MTProxyMax](https://github.com/SamNet-dev/MTProxyMax). Install it first.
2. **Metrics must be enabled:** Ensure Prometheus metrics are enabled in MTProxyMax configuration.
3. **Default port 9090:** If you changed the metrics port, use `--url` flag.
4. **Root access:** Installation requires root/sudo privileges.

## 📝 Changelog

### v1.1.1 (23.03.2026)

- 👥 **Users table:** added TCP Limit column (loaded from API `/v1/users`)
- 🔗 **API integration:** `--api` flag to specify Control API URL for user limits
- 🔧 **Fallback:** shows `-` when API is unavailable
- ⚡ Smart dependency check: system packages (python3, curl, etc.) are only installed if missing
- 🚀 Faster reinstalls: skips unnecessary apt-get update when all dependencies present
- 🐛 Bugfix: fixed typo in install directory check

### v1.1.0 (23.03.2026)

#### metrics_viewer.py
- 📊 **Status panel:** added active/ME/direct connections breakdown
- 📈 **System Metrics:** added relay adaptive, reconnect evict/stale, failfast metrics
- 🆕 **New section: Upstream Attempts** - attempts per request distribution
- 🔄 **ME Statistics:** added KDF drift, async recovery, writers active/warm, uncompensated removals
- 🆕 **New section: ME Keepalive** - sent/failed/pong/timeout
- 🆕 **New section: Single-Endpoint Outage** - outage enter/exit, shadow rotations
- 🎯 **Writer Pick:** added Mode column with result descriptions
- 🆕 **New section: Adaptive Floor** - CPU cores, caps, target writers, blocks
- 🔧 **Pool Management:** added soft evict, close signal drops, reap progress
- 🆕 **New section: Security/Desync** - padding, desync, suppressed
- 🆕 **New section: Relay Adaptive** - promotions/demotions
- 👥 **Users:** added IPs and IP Limit columns
- 🔐 **SOCKS KDF:** added descriptions for each policy outcome
- ⚙️ **New --section options:** `floor`, `outage`, `security`, `relay`

#### metrics_live.py
- 📊 **Header bar:** added active connections count and writers active/warm
- 🔄 **System panel:** active connections with ME/Direct split, writers count, quarantine counter
- 👥 **Users panel:** added unique active IPs column

#### install.sh
- 🔍 **Version checking:** compares local vs remote version before install
- 🔄 **Update prompt:** shows "Update available: X -> Y" when new version exists
- ⚡ **Auto mode:** `--auto` flag skips all prompts for CI/scripted usage
- 📄 **Version file:** saves installed version to `/root/Metrics/.version`

### v1.0.0 (20.03.2026)

- ✨ Initial release
- 📊 Static metrics viewer
- ⚡ Live auto-refresh mode
- 👥 User statistics
- 🔼 Upstream connection stats
- 🔄 ME statistics
- 🎯 SOCKS KDF policy
- 🔧 Pool management stats
  
## 👤 Author

Created for the MTProxyMax community.

## 🌟 Show Your Support

If this project helped you, please consider:

- ⭐ **Starring** this repository

---

**Made with ❤️ for the Telegram MTProxyMax**

🌍 **Available in:** [English](README.md) | [Русский](README_RU.md)

[🔝 Back to top](#mtproxymax-metrics-viewer)
```
