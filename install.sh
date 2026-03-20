cat > install.sh << 'ENDOFINSTALL'
#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
   print_error "Run as root: sudo bash install.sh"
   exit 1
fi

clear
echo "======================================================"
echo "   MTProtoMax Metrics Viewer - Installer v1.0"
echo "======================================================"
echo ""

print_info "Checking metrics endpoint..."
if curl -s --max-time 5 http://localhost:9090/metrics > /dev/null 2>&1; then
    print_success "Metrics endpoint is accessible"
else
    print_warning "Cannot reach http://localhost:9090/metrics"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

print_info "Installing system dependencies..."
apt update -qq
apt install -y python3 python3-pip python3-venv curl > /dev/null 2>&1
print_success "Dependencies installed"

INSTALL_DIR="/root/Metrics"

if [ -d "$INSTALL_DIR" ]; then
    print_warning "Directory $INSTALL_DIR already exists"
    read -p "Remove and reinstall? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        exit 1
    fi
fi

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

print_info "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet requests rich
deactivate
print_success "Virtual environment ready"

print_info "Creating metrics_viewer.py..."

cat > "$INSTALL_DIR/metrics_viewer.py" << 'ENDVIEWER'
#!/usr/bin/env python3
import requests
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from collections import defaultdict
import sys
import argparse

METRICS_URL = "http://localhost:9090/metrics"
console = Console()

def fetch_metrics(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

def parse_metrics(text):
    metrics = {}
    help_texts = {}
    types = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('# HELP'):
            match = re.match(r'# HELP (\S+) (.+)', line)
            if match:
                help_texts[match.group(1)] = match.group(2)
        elif line.startswith('# TYPE'):
            match = re.match(r'# TYPE (\S+) (\S+)', line)
            if match:
                types[match.group(1)] = match.group(2)
        elif not line.startswith('#'):
            match = re.match(r'(\S+?)\{(.+?)\}\s+(.+)', line)
            if match:
                name, labels, value = match.groups()
                if name not in metrics:
                    metrics[name] = []
                metrics[name].append({
                    'labels': dict(re.findall(r'(\w+)="([^"]*)"', labels)),
                    'value': value
                })
            else:
                match = re.match(r'(\S+)\s+(.+)', line)
                if match:
                    name, value = match.groups()
                    if name not in metrics:
                        metrics[name] = []
                    metrics[name].append({'labels': {}, 'value': value})
    return metrics, help_texts, types

def format_value(value):
    try:
        num = float(value)
        if num == int(num):
            return f"{int(num):,}".replace(',', ' ')
        return f"{num:,.2f}".replace(',', ' ')
    except:
        return value

def format_bytes(value):
    try:
        num = float(value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(num) < 1024:
                return f"{num:.2f} {unit}"
            num /= 1024
        return f"{num:.2f} PB"
    except:
        return value

def format_uptime(seconds):
    try:
        sec = float(seconds)
        days = int(sec // 86400)
        hours = int((sec % 86400) // 3600)
        mins = int((sec % 3600) // 60)
        secs = int(sec % 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0:
            parts.append(f"{mins}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        return ' '.join(parts)
    except:
        return seconds

def get_val(metrics, name, default='0'):
    if name in metrics and metrics[name]:
        return metrics[name][0]['value']
    return default

def create_header():
    return Panel.fit(
        "[bold cyan]PROMETHEUS METRICS VIEWER[/bold cyan]\n"
        "[dim]MTProtoMax proxy metrics dashboard[/dim]",
        border_style="blue",
        padding=(1, 2)
    )

def create_status_panel(metrics):
    uptime = format_uptime(get_val(metrics, 'telemt_uptime_seconds'))
    total = int(float(get_val(metrics, 'telemt_connections_total')))
    bad = int(float(get_val(metrics, 'telemt_connections_bad_total')))
    good = total - bad
    
    up_total = int(float(get_val(metrics, 'telemt_upstream_connect_attempt_total')))
    up_ok = int(float(get_val(metrics, 'telemt_upstream_connect_success_total')))
    up_rate = (up_ok / up_total * 100) if up_total > 0 else 0
    
    auth_rate = (good / total * 100) if total > 0 else 0
    
    if up_rate > 95:
        status_emoji = "[green]OK[/green]"
        status_text = "EXCELLENT"
        status_color = "green"
    elif up_rate > 80:
        status_emoji = "[yellow]WARN[/yellow]"
        status_text = "WARNING"
        status_color = "yellow"
    else:
        status_emoji = "[red]CRIT[/red]"
        status_text = "CRITICAL"
        status_color = "red"
    
    content = f"""[bold]Status:[/bold] {status_emoji} {status_text}
[bold]Uptime:[/bold] [cyan]{uptime}[/cyan]

[bold]Connections:[/bold]
  Total:        {format_value(str(total))}
  Authorized:   [green]{format_value(str(good))}[/green] ({auth_rate:.1f}%)
  Rejected:     [red]{format_value(str(bad))}[/red] (no valid secret)

[bold]Upstream:[/bold]
  Attempts:     {format_value(str(up_total))}
  Success:      [green]{format_value(str(up_ok))}[/green]
  Failed:       [red]{format_value(str(up_total - up_ok))}[/red]
  Success rate: [{status_color}]{up_rate:.1f}%[/{status_color}]"""
    
    return Panel(content, title="Summary", border_style=status_color, padding=(1, 2))

def create_main_table(metrics, help_texts):
    table = Table(
        title="System Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Metric", style="green", min_width=45)
    table.add_column("Value", style="yellow", justify="right", min_width=15)
    table.add_column("Description", style="dim")
    
    items = [
        ('telemt_uptime_seconds', lambda v: format_uptime(v)),
        ('telemt_connections_total', None),
        ('telemt_connections_bad_total', None),
        ('telemt_handshake_timeouts_total', None),
        ('telemt_upstream_connect_attempt_total', None),
        ('telemt_upstream_connect_success_total', None),
        ('telemt_upstream_connect_fail_total', None)
    ]
    
    for name, fmt in items:
        if name in metrics and metrics[name]:
            v = metrics[name][0]['value']
            dv = fmt(v) if fmt else format_value(v)
            desc = help_texts.get(name, '')[:60]
            table.add_row(name, dv, desc)
    
    return table

def create_upstream_table(metrics):
    table = Table(
        title="Upstream Connection Duration",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold blue"
    )
    table.add_column("Range", style="cyan", min_width=15)
    table.add_column("Success", justify="right", style="green", min_width=12)
    table.add_column("Failed", justify="right", style="red", min_width=12)
    table.add_column("% OK", justify="right", style="yellow", min_width=10)
    
    buckets = ['le_100ms', '101_500ms', '501_1000ms', 'gt_1000ms']
    labels = {
        'le_100ms': '<= 100ms',
        '101_500ms': '101-500ms',
        '501_1000ms': '501-1000ms',
        'gt_1000ms': '> 1000ms'
    }
    
    success_data = {}
    fail_data = {}
    
    if 'telemt_upstream_connect_duration_success_total' in metrics:
        for item in metrics['telemt_upstream_connect_duration_success_total']:
            bucket = item['labels'].get('bucket', '')
            success_data[bucket] = int(float(item['value']))
    
    if 'telemt_upstream_connect_duration_fail_total' in metrics:
        for item in metrics['telemt_upstream_connect_duration_fail_total']:
            bucket = item['labels'].get('bucket', '')
            fail_data[bucket] = int(float(item['value']))
    
    for bucket in buckets:
        s = success_data.get(bucket, 0)
        f = fail_data.get(bucket, 0)
        total = s + f
        percent = (s / total * 100) if total > 0 else 0
        table.add_row(
            labels.get(bucket, bucket),
            format_value(str(s)),
            format_value(str(f)),
            f"{percent:.1f}%"
        )
    
    return table

def create_me_table(metrics):
    table = Table(
        title="ME Statistics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold yellow"
    )
    table.add_column("Metric", style="green", min_width=50)
    table.add_column("Value", style="yellow", justify="right", min_width=15)
    
    items = [
        ('telemt_me_reconnect_attempts_total', 'Reconnect attempts'),
        ('telemt_me_reconnect_success_total', 'Reconnect success'),
        ('telemt_me_handshake_reject_total', 'Handshake rejected'),
        ('telemt_me_reader_eof_total', 'Reader EOF'),
        ('telemt_me_idle_close_by_peer_total', 'Closed by peer'),
        ('telemt_me_crc_mismatch_total', 'CRC mismatch'),
        ('telemt_me_seq_mismatch_total', 'Sequence mismatch'),
        ('telemt_me_route_drop_no_conn_total', 'Drop: no connection'),
        ('telemt_me_route_drop_channel_closed_total', 'Drop: channel closed'),
        ('telemt_me_route_drop_queue_full_total', 'Drop: queue full'),
        ('telemt_me_endpoint_quarantine_total', 'Endpoint quarantine'),
        ('telemt_me_writer_removed_unexpected_total', 'Writer removed'),
        ('telemt_me_writer_restored_same_endpoint_total', 'Restored same'),
        ('telemt_me_writer_restored_fallback_total', 'Restored fallback'),
        ('telemt_me_refill_failed_total', 'Refill failed')
    ]
    
    for name, label in items:
        if name in metrics and metrics[name]:
            table.add_row(label, format_value(metrics[name][0]['value']))
    
    return table

def create_writer_table(metrics):
    table = Table(
        title="Writer Pick (p2c mode)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold green"
    )
    table.add_column("Result", style="cyan", min_width=20)
    table.add_column("Count", justify="right", style="yellow", min_width=15)
    
    if 'telemt_me_writer_pick_total' in metrics:
        for item in metrics['telemt_me_writer_pick_total']:
            if item['labels'].get('mode', '') == 'p2c':
                result = item['labels'].get('result', '')
                table.add_row(result, format_value(item['value']))
    
    return table

def create_users_table(metrics):
    table = Table(
        title="User Statistics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("User", style="cyan", min_width=15)
    table.add_column("Total Conn", justify="right", style="green", min_width=12)
    table.add_column("Active", justify="right", style="yellow", min_width=10)
    table.add_column("RX", justify="right", style="blue", min_width=15)
    table.add_column("TX", justify="right", style="blue", min_width=15)
    table.add_column("Msgs In", justify="right", style="dim", min_width=10)
    table.add_column("Msgs Out", justify="right", style="dim", min_width=10)
    
    users = defaultdict(dict)
    
    for metric_name in [
        'telemt_user_connections_total',
        'telemt_user_connections_current',
        'telemt_user_octets_from_client',
        'telemt_user_octets_to_client',
        'telemt_user_msgs_from_client',
        'telemt_user_msgs_to_client'
    ]:
        if metric_name in metrics:
            for item in metrics[metric_name]:
                user = item['labels'].get('user', 'unknown')
                users[user][metric_name] = item['value']
    
    sorted_users = sorted(
        users.items(),
        key=lambda x: int(float(x[1].get('telemt_user_connections_total', '0'))),
        reverse=True
    )
    
    for user, data in sorted_users:
        table.add_row(
            user,
            format_value(data.get('telemt_user_connections_total', '0')),
            format_value(data.get('telemt_user_connections_current', '0')),
            format_bytes(data.get('telemt_user_octets_from_client', '0')),
            format_bytes(data.get('telemt_user_octets_to_client', '0')),
            format_value(data.get('telemt_user_msgs_from_client', '0')),
            format_value(data.get('telemt_user_msgs_to_client', '0'))
        )
    
    return table

def create_socks_table(metrics):
    table = Table(
        title="SOCKS KDF Policy",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold red"
    )
    table.add_column("Policy", style="cyan", min_width=15)
    table.add_column("Result", style="yellow", min_width=15)
    table.add_column("Count", justify="right", style="red", min_width=15)
    
    if 'telemt_me_socks_kdf_policy_total' in metrics:
        for item in metrics['telemt_me_socks_kdf_policy_total']:
            policy = item['labels'].get('policy', '')
            outcome = item['labels'].get('outcome', '')
            table.add_row(policy, outcome, format_value(item['value']))
    
    return table

def create_pool_table(metrics):
    table = Table(
        title="Pool Management",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Metric", style="green", min_width=40)
    table.add_column("Value", style="yellow", justify="right", min_width=15)
    
    items = [
        ('telemt_pool_swap_total', 'Pool swap'),
        ('telemt_pool_drain_active', 'Draining'),
        ('telemt_pool_force_close_total', 'Force close'),
        ('telemt_pool_stale_pick_total', 'Stale pick')
    ]
    
    for name, label in items:
        table.add_row(label, format_value(get_val(metrics, name)))
    
    return table

def main():
    parser = argparse.ArgumentParser(description='MTProtoMax Metrics Viewer')
    parser.add_argument('--url', default=METRICS_URL, help='Metrics URL')
    parser.add_argument(
        '--section',
        choices=['all', 'status', 'main', 'upstream', 'me', 'users', 'socks', 'pool'],
        default='all'
    )
    args = parser.parse_args()
    
    console.clear()
    console.print("[bold blue]Loading metrics...[/bold blue]")
    
    raw = fetch_metrics(args.url)
    m, h, t = parse_metrics(raw)
    
    console.clear()
    console.print(create_header())
    console.print()
    
    if args.section in ['all', 'status']:
        console.print(create_status_panel(m))
        console.print()
    
    if args.section in ['all', 'main']:
        console.print(create_main_table(m, h))
        console.print()
    
    if args.section in ['all', 'upstream']:
        console.print(create_upstream_table(m))
        console.print()
    
    if args.section in ['all', 'me']:
        console.print(create_me_table(m))
        console.print()
        console.print(create_writer_table(m))
        console.print()
    
    if args.section in ['all', 'socks']:
        console.print(create_socks_table(m))
        console.print()
    
    if args.section in ['all', 'pool']:
        console.print(create_pool_table(m))
        console.print()
    
    if args.section in ['all', 'users']:
        console.print(create_users_table(m))
        console.print()
    
    console.print(f"[dim]Source: {args.url}[/dim]")
    console.print(f"[dim]Use --section for specific section[/dim]")

if __name__ == "__main__":
    main()
ENDVIEWER

chmod +x "$INSTALL_DIR/metrics_viewer.py"
print_success "metrics_viewer.py created"

print_info "Creating metrics_live.py..."

cat > "$INSTALL_DIR/metrics_live.py" << 'ENDLIVE'
#!/usr/bin/env python3
import requests
import re
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box
from collections import defaultdict
from datetime import datetime

METRICS_URL = "http://localhost:9090/metrics"
REFRESH_INTERVAL = 5
console = Console()

def fetch_metrics(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except:
        return None

def parse_metrics(text):
    if not text:
        return {}, {}, {}
    
    metrics = {}
    help_texts = {}
    types = {}
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('# HELP'):
            m = re.match(r'# HELP (\S+) (.+)', line)
            if m:
                help_texts[m.group(1)] = m.group(2)
        elif line.startswith('# TYPE'):
            m = re.match(r'# TYPE (\S+) (\S+)', line)
            if m:
                types[m.group(1)] = m.group(2)
        elif not line.startswith('#'):
            m = re.match(r'(\S+?)\{(.+?)\}\s+(.+)', line)
            if m:
                name, labels, value = m.groups()
                if name not in metrics:
                    metrics[name] = []
                metrics[name].append({
                    'labels': dict(re.findall(r'(\w+)="([^"]*)"', labels)),
                    'value': value
                })
            else:
                m = re.match(r'(\S+)\s+(.+)', line)
                if m:
                    name, value = m.groups()
                    if name not in metrics:
                        metrics[name] = []
                    metrics[name].append({'labels': {}, 'value': value})
    
    return metrics, help_texts, types

def fv(value):
    try:
        n = float(value)
        if n == int(n):
            return f"{int(n):,}".replace(',', ' ')
        return f"{n:,.2f}".replace(',', ' ')
    except:
        return value

def fb(value):
    try:
        n = float(value)
        for u in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(n) < 1024:
                return f"{n:.1f}{u}"
            n /= 1024
    except:
        pass
    return value

def fu(seconds):
    try:
        s = float(seconds)
        d = int(s // 86400)
        h = int((s % 86400) // 3600)
        m = int((s % 3600) // 60)
        return f"{d}d {h}h {m}m"
    except:
        return seconds

def gv(metrics, name, default='0'):
    if name in metrics and metrics[name]:
        return metrics[name][0]['value']
    return default

def generate_dashboard(metrics, help_texts):
    uptime = fu(gv(metrics, 'telemt_uptime_seconds'))
    
    total = int(float(gv(metrics, 'telemt_connections_total')))
    bad = int(float(gv(metrics, 'telemt_connections_bad_total')))
    good = total - bad
    ar = (good / total * 100) if total > 0 else 0
    
    ut = int(float(gv(metrics, 'telemt_upstream_connect_attempt_total')))
    us = int(float(gv(metrics, 'telemt_upstream_connect_success_total')))
    uf = int(float(gv(metrics, 'telemt_upstream_connect_fail_total')))
    ur = (us / ut * 100) if ut > 0 else 0
    
    mr = int(float(gv(metrics, 'telemt_me_reconnect_attempts_total')))
    ms = int(float(gv(metrics, 'telemt_me_reconnect_success_total')))
    mrr = (ms / mr * 100) if mr > 0 else 0
    
    sc = "green" if ur > 95 else "yellow" if ur > 80 else "red"
    se = f"[{sc}]{'OK' if ur > 95 else 'WARN' if ur > 80 else 'CRIT'}[/{sc}]"
    
    mt = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", expand=True)
    mt.add_column("Metric", style="green")
    mt.add_column("Value", justify="right", style="yellow")
    
    mt.add_row("Uptime", uptime)
    mt.add_row("", "")
    mt.add_row("[bold]-- Connections --[/bold]", "")
    mt.add_row("Total", fv(str(total)))
    mt.add_row("Authorized", f"[green]{fv(str(good))}[/green] ({ar:.1f}%)")
    mt.add_row("Rejected (no secret)", f"[red]{fv(str(bad))}[/red]")
    mt.add_row("", "")
    mt.add_row("[bold]-- Upstream --[/bold]", "")
    mt.add_row("Attempts", fv(str(ut)))
    mt.add_row("Success", f"[green]{fv(str(us))}[/green]")
    mt.add_row("Failed", f"[red]{fv(str(uf))}[/red]")
    mt.add_row("Success rate", f"[{sc}]{ur:.1f}%[/{sc}]")
    mt.add_row("", "")
    mt.add_row("[bold]-- ME Reconnect --[/bold]", "")
    mt.add_row("Attempts", fv(str(mr)))
    mt.add_row("Success", f"[green]{fv(str(ms))}[/green]")
    mt.add_row("Rate", f"[magenta]{mrr:.1f}%[/magenta]")
    
    ut2 = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta", expand=True)
    ut2.add_column("User", style="cyan")
    ut2.add_column("Conn", justify="right")
    ut2.add_column("Active", justify="right", style="green")
    ut2.add_column("RX", justify="right", style="blue")
    ut2.add_column("TX", justify="right", style="blue")
    
    users = defaultdict(dict)
    for mn in [
        'telemt_user_connections_total',
        'telemt_user_connections_current',
        'telemt_user_octets_from_client',
        'telemt_user_octets_to_client'
    ]:
        if mn in metrics:
            for i in metrics[mn]:
                u = i['labels'].get('user', 'unknown')
                users[u][mn] = i['value']
    
    for u, d in sorted(users.items()):
        ut2.add_row(
            u[:12],
            fv(d.get('telemt_user_connections_total', '0')),
            fv(d.get('telemt_user_connections_current', '0')),
            fb(d.get('telemt_user_octets_from_client', '0')),
            fb(d.get('telemt_user_octets_to_client', '0'))
        )
    
    dt = Table(box=box.SIMPLE, show_header=True, header_style="bold blue")
    dt.add_column("Duration", style="cyan")
    dt.add_column("OK", justify="right", style="green")
    dt.add_column("FAIL", justify="right", style="red")
    dt.add_column("%", justify="right", style="yellow")
    
    bks = ['le_100ms', '101_500ms', '501_1000ms', 'gt_1000ms']
    bns = ['<=100ms', '101-500ms', '501-1s', '>1s']
    
    sd = {}
    fd = {}
    
    if 'telemt_upstream_connect_duration_success_total' in metrics:
        for i in metrics['telemt_upstream_connect_duration_success_total']:
            sd[i['labels'].get('bucket', '')] = int(float(i['value']))
    
    if 'telemt_upstream_connect_duration_fail_total' in metrics:
        for i in metrics['telemt_upstream_connect_duration_fail_total']:
            fd[i['labels'].get('bucket', '')] = int(float(i['value']))
    
    for b, n in zip(bks, bns):
        ok = sd.get(b, 0)
        fail = fd.get(b, 0)
        total_dur = ok + fail
        percent = (ok / total_dur * 100) if total_dur > 0 else 0
        dt.add_row(n, fv(str(ok)), fv(str(fail)), f"{percent:.0f}%")
    
    now = datetime.now().strftime("%H:%M:%S")
    
    header = Panel(
        f"[bold white]{se} MTPROTOMAX METRICS LIVE[/bold white]  |  "
        f"Uptime: [cyan]{uptime}[/cyan]  |  "
        f"Upstream: [{sc}]{ur:.1f}%[/{sc}]  |  "
        f"[dim]{now}[/dim]",
        box=box.ROUNDED,
        border_style="blue"
    )
    
    lp = Panel(mt, title="System", border_style="green")
    rp = Panel(ut2, title="Users", border_style="magenta")
    bp = Panel(dt, title="Upstream Duration", border_style="blue")
    
    final = Table.grid(expand=True)
    final.add_row(header)
    
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1)
    mid.add_column(ratio=1)
    mid.add_row(lp, rp)
    
    final.add_row(mid)
    final.add_row(bp)
    final.add_row(
        Text(
            f"Source: {METRICS_URL} | Refresh: {REFRESH_INTERVAL}s | Ctrl+C to exit",
            style="dim"
        )
    )
    
    return final

def main():
    console.print("[bold blue]Starting live metrics...[/bold blue]")
    time.sleep(1)
    
    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            try:
                raw = fetch_metrics(METRICS_URL)
                m, h, t = parse_metrics(raw)
                
                if m:
                    live.update(generate_dashboard(m, h))
                else:
                    live.update(Panel("[red]Cannot fetch metrics[/red]", title="Error"))
                
                time.sleep(REFRESH_INTERVAL)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Exiting...[/yellow]")
                break
            except Exception as e:
                live.update(Panel(f"[red]Error: {e}[/red]"))
                time.sleep(REFRESH_INTERVAL)

if __name__ == "__main__":
    main()
ENDLIVE

chmod +x "$INSTALL_DIR/metrics_live.py"
print_success "metrics_live.py created"

print_info "Creating wrapper scripts..."

cat > "$INSTALL_DIR/metrics" << 'ENDWRAP1'
#!/bin/bash
cd /root/Metrics
source venv/bin/activate
python3 metrics_viewer.py "$@"
deactivate
ENDWRAP1
chmod +x "$INSTALL_DIR/metrics"

cat > "$INSTALL_DIR/metrics-live" << 'ENDWRAP2'
#!/bin/bash
cd /root/Metrics
source venv/bin/activate
python3 metrics_live.py
deactivate
ENDWRAP2
chmod +x "$INSTALL_DIR/metrics-live"

print_info "Creating global symlinks..."
ln -sf "$INSTALL_DIR/metrics" /usr/local/bin/metrics
ln -sf "$INSTALL_DIR/metrics-live" /usr/local/bin/metrics-live

print_success "Installation complete!"
echo ""
echo "======================================================"
echo "   Installation completed successfully!"
echo "======================================================"
echo ""
echo "Commands:"
echo "  metrics           - View all metrics"
echo "  metrics-live      - Live auto-refresh mode"
echo "  metrics --section status  - Status only"
echo "  metrics --section users   - Users only"
echo ""
echo "Press Ctrl+C to exit live mode"
echo ""
ENDOFINSTALL

chmod +x install.sh
