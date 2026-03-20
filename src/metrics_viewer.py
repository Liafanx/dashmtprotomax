cat > src/metrics_viewer.py << 'PYEOF'
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
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('# HELP'):
            match = re.match(r'# HELP (\S+) (.+)', line)
            if match:
                help_texts[match.group(1)] = match.group(2)
        elif not line.startswith('#'):
            match = re.match(r'(\S+?)\{(.+?)\}\s+(.+)', line)
            if match:
                name, labels, value = match.groups()
                if name not in metrics:
                    metrics[name] = []
                metrics[name].append({'labels': dict(re.findall(r'(\w+)="([^"]*)"', labels)), 'value': value})
            else:
                match = re.match(r'(\S+)\s+(.+)', line)
                if match:
                    name, value = match.groups()
                    if name not in metrics:
                        metrics[name] = []
                    metrics[name].append({'labels': {}, 'value': value})
    return metrics, help_texts

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
    except:
        pass
    return value

def format_uptime(seconds):
    try:
        sec = float(seconds)
        days = int(sec // 86400)
        hours = int((sec % 86400) // 3600)
        mins = int((sec % 3600) // 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0:
            parts.append(f"{mins}m")
        return ' '.join(parts) if parts else '0m'
    except:
        return seconds

def get_val(metrics, name, default='0'):
    if name in metrics and metrics[name]:
        return metrics[name][0]['value']
    return default

def create_header():
    return Panel.fit(
        "[bold cyan]PROMETHEUS METRICS VIEWER[/bold cyan]\n[dim]MTProtoMax metrics dashboard[/dim]",
        border_style="blue", padding=(1, 2)
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
        se, st, sc = "[green]OK[/green]", "EXCELLENT", "green"
    elif up_rate > 80:
        se, st, sc = "[yellow]WARN[/yellow]", "WARNING", "yellow"
    else:
        se, st, sc = "[red]CRIT[/red]", "CRITICAL", "red"
    
    content = f"""[bold]Status:[/bold] {se} {st}
[bold]Uptime:[/bold] [cyan]{uptime}[/cyan]

[bold]Connections:[/bold]
  Total:      {format_value(str(total))}
  Authorized: [green]{format_value(str(good))}[/green] ({auth_rate:.1f}%)
  Rejected:   [red]{format_value(str(bad))}[/red] (no secret)

[bold]Upstream:[/bold]
  Attempts: {format_value(str(up_total))}
  Success:  [green]{format_value(str(up_ok))}[/green]
  Failed:   [red]{format_value(str(up_total - up_ok))}[/red]
  Rate:     [{sc}]{up_rate:.1f}%[/{sc}]"""
    
    return Panel(content, title="Summary", border_style=sc, padding=(1, 2))

def create_users_table(metrics):
    table = Table(title="User Statistics", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("User", style="cyan", min_width=15)
    table.add_column("Connections", justify="right", style="green")
    table.add_column("Active", justify="right", style="yellow")
    table.add_column("RX", justify="right", style="blue")
    table.add_column("TX", justify="right", style="blue")
    
    users = defaultdict(dict)
    for mn in ['telemt_user_connections_total', 'telemt_user_connections_current', 'telemt_user_octets_from_client', 'telemt_user_octets_to_client']:
        if mn in metrics:
            for item in metrics[mn]:
                user = item['labels'].get('user', 'unknown')
                users[user][mn] = item['value']
    
    for user, data in sorted(users.items(), key=lambda x: int(float(x[1].get('telemt_user_connections_total', '0'))), reverse=True):
        table.add_row(
            user,
            format_value(data.get('telemt_user_connections_total', '0')),
            format_value(data.get('telemt_user_connections_current', '0')),
            format_bytes(data.get('telemt_user_octets_from_client', '0')),
            format_bytes(data.get('telemt_user_octets_to_client', '0'))
        )
    
    return table

def main():
    parser = argparse.ArgumentParser(description='MTProtoMax Metrics Viewer')
    parser.add_argument('--url', default=METRICS_URL, help='Metrics URL')
    parser.add_argument('--section', choices=['all', 'status', 'users'], default='all')
    args = parser.parse_args()
    
    console.clear()
    console.print("[bold blue]Loading metrics...[/bold blue]")
    
    raw = fetch_metrics(args.url)
    m, h = parse_metrics(raw)
    
    console.clear()
    console.print(create_header())
    console.print()
    
    if args.section in ['all', 'status']:
        console.print(create_status_panel(m))
        console.print()
    
    if args.section in ['all', 'users']:
        console.print(create_users_table(m))
        console.print()
    
    console.print(f"[dim]Source: {args.url}[/dim]")

if __name__ == "__main__":
    main()
PYEOF

chmod +x src/metrics_viewer.py
