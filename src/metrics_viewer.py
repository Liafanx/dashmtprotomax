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
        console.print(f"[red]Error fetching metrics: {e}[/red]")
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
        return f"{num:.2f} PB"
    except:
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
  Rejected:   [red]{format_value(str(bad))}[/red] (no valid secret)

[bold]Upstream:[/bold]
  Attempts: {format_value(str(up_total))}
  Success:  [green]{format_value(str(up_ok))}[/green]
  Failed:   [red]{format_value(str(up_total - up_ok))}[/red]
  Rate:     [{sc}]{up_rate:.1f}%[/{sc}]"""
    
    return Panel(content, title="Summary", border_style=sc, padding=(1, 2))

def create_main_table(metrics, help_texts):
    table = Table(
        title="System Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Metric", style="green", min_width=45)
    table.add_column("Value", style="yellow", justify="right", min_width=15)
    table.add_column("Description", style="dim", overflow="fold")
    
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
    table.add_column("% Success", justify="right", style="yellow", min_width=10)
    
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
        ('telemt_me_writer_restored_same_endpoint_total', 'Restored (same)'),
        ('telemt_me_writer_restored_fallback_total', 'Restored (fallback)'),
        ('telemt_me_refill_failed_total', 'Refill failed')
    ]
    
    for name, label in items:
        if name in metrics and metrics[name]:
            table.add_row(label, format_value(metrics[name][0]['value']))
    
    return table

def create_writer_table(metrics):
    table = Table(
        title="Writer Pick Statistics (p2c mode)",
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
    table.add_column("Total Conn", justify="right", style="green")
    table.add_column("Active", justify="right", style="yellow")
    table.add_column("RX", justify="right", style="blue")
    table.add_column("TX", justify="right", style="blue")
    table.add_column("Msgs In", justify="right", style="dim")
    table.add_column("Msgs Out", justify="right", style="dim")
    
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
        ('telemt_pool_swap_total', 'Pool swap success'),
        ('telemt_pool_drain_active', 'Active draining'),
        ('telemt_pool_force_close_total', 'Forced close'),
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
    m, h = parse_metrics(raw)
    
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
    console.print(f"[dim]Use --section for specific sections[/dim]")

if __name__ == "__main__":
    main()
