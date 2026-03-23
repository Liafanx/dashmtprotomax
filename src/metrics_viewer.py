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

def fv(value):
    try:
        num = float(value)
        if num == int(num):
            return f"{int(num):,}".replace(',', ' ')
        return f"{num:,.2f}".replace(',', ' ')
    except:
        return value

def fb(value):
    try:
        num = float(value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(num) < 1024:
                return f"{num:.2f} {unit}"
            num /= 1024
    except:
        pass
    return value

def fu(seconds):
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

def gv(metrics, name, default='0'):
    if name in metrics and metrics[name]:
        return metrics[name][0]['value']
    return default

def create_header():
    return Panel.fit(
        "[bold cyan]PROMETHEUS METRICS VIEWER[/bold cyan]\n"
        "[dim]MTProxyMax proxy metrics dashboard[/dim]",
        border_style="blue", padding=(1, 2)
    )

def create_status_panel(metrics):
    uptime = fu(gv(metrics, 'telemt_uptime_seconds'))
    total = int(float(gv(metrics, 'telemt_connections_total')))
    bad = int(float(gv(metrics, 'telemt_connections_bad_total')))
    good = total - bad
    current = int(float(gv(metrics, 'telemt_connections_current', '0')))
    current_me = int(float(gv(metrics, 'telemt_connections_me_current', '0')))
    current_direct = int(float(gv(metrics, 'telemt_connections_direct_current', '0')))

    up_total = int(float(gv(metrics, 'telemt_upstream_connect_attempt_total')))
    up_ok = int(float(gv(metrics, 'telemt_upstream_connect_success_total')))
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
  Total accepted:   {fv(str(total))}
  Authorized:       [green]{fv(str(good))}[/green] ({auth_rate:.1f}%)
  Rejected:         [red]{fv(str(bad))}[/red] (no valid secret)
  Active now:       [yellow]{fv(str(current))}[/yellow] (ME: {current_me}, Direct: {current_direct})

[bold]Upstream:[/bold]
  Attempts: {fv(str(up_total))}
  Success:  [green]{fv(str(up_ok))}[/green]
  Failed:   [red]{fv(str(up_total - up_ok))}[/red]
  Rate:     [{sc}]{up_rate:.1f}%[/{sc}]"""

    return Panel(content, title="Summary", border_style=sc, padding=(1, 2))

def create_main_table(metrics, help_texts):
    table = Table(title="System Metrics", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="green", min_width=50)
    table.add_column("Value", style="yellow", justify="right", min_width=15)
    table.add_column("Description", style="dim", overflow="fold")

    items = [
        ('telemt_uptime_seconds', 'Proxy uptime', lambda v: fu(v)),
        ('telemt_connections_total', 'Total accepted connections', None),
        ('telemt_connections_bad_total', 'Rejected connections (no valid secret)', None),
        ('telemt_connections_current', 'Current active connections', None),
        ('telemt_connections_me_current', 'Active middle-end connections', None),
        ('telemt_connections_direct_current', 'Active direct connections', None),
        ('telemt_handshake_timeouts_total', 'Handshake timeouts', None),
        ('telemt_upstream_connect_attempt_total', 'Upstream connect attempts', None),
        ('telemt_upstream_connect_success_total', 'Successful upstream connects', None),
        ('telemt_upstream_connect_fail_total', 'Failed upstream connects', None),
        ('telemt_upstream_connect_failfast_hard_error_total', 'Hard errors triggering failfast', None),
        ('telemt_reconnect_evict_total', 'Reconnect-driven session evictions', None),
        ('telemt_reconnect_stale_close_total', 'Stale sessions closed after reconnect', None),
        ('telemt_telemetry_core_enabled', 'Core telemetry switch', None),
        ('telemt_telemetry_user_enabled', 'Per-user telemetry switch', None),
    ]

    for name, desc, fmt in items:
        if name in metrics and metrics[name]:
            v = metrics[name][0]['value']
            dv = fmt(v) if fmt else fv(v)
            table.add_row(name, dv, desc)

    return table

def create_upstream_table(metrics):
    table = Table(title="Upstream Connection Duration", box=box.ROUNDED, show_header=True, header_style="bold blue")
    table.add_column("Range", style="cyan", min_width=15)
    table.add_column("Success", justify="right", style="green", min_width=12)
    table.add_column("Failed", justify="right", style="red", min_width=12)
    table.add_column("% Success", justify="right", style="yellow", min_width=10)

    buckets = ['le_100ms', '101_500ms', '501_1000ms', 'gt_1000ms']
    labels = {'le_100ms': '<= 100ms', '101_500ms': '101-500ms', '501_1000ms': '501-1000ms', 'gt_1000ms': '> 1000ms'}

    sd, fd = {}, {}
    if 'telemt_upstream_connect_duration_success_total' in metrics:
        for i in metrics['telemt_upstream_connect_duration_success_total']:
            sd[i['labels'].get('bucket', '')] = int(float(i['value']))
    if 'telemt_upstream_connect_duration_fail_total' in metrics:
        for i in metrics['telemt_upstream_connect_duration_fail_total']:
            fd[i['labels'].get('bucket', '')] = int(float(i['value']))

    for b in buckets:
        s = sd.get(b, 0)
        f = fd.get(b, 0)
        t = s + f
        p = (s / t * 100) if t > 0 else 0
        table.add_row(labels.get(b, b), fv(str(s)), fv(str(f)), f"{p:.1f}%")

    return table

def create_upstream_attempts_table(metrics):
    table = Table(title="Upstream Attempts Per Request", box=box.ROUNDED, show_header=True, header_style="bold blue")
    table.add_column("Bucket", style="cyan", min_width=20)
    table.add_column("Count", justify="right", style="yellow", min_width=15)
    table.add_column("Description", style="dim")

    buckets = [
        ('1', 'Resolved in 1 attempt'),
        ('2', 'Resolved in 2 attempts'),
        ('3_4', 'Resolved in 3-4 attempts'),
        ('gt_4', 'Required more than 4 attempts'),
    ]

    if 'telemt_upstream_connect_attempts_per_request' in metrics:
        data = {}
        for i in metrics['telemt_upstream_connect_attempts_per_request']:
            data[i['labels'].get('bucket', '')] = i['value']
        for bk, desc in buckets:
            table.add_row(bk, fv(data.get(bk, '0')), desc)

    return table

def create_me_table(metrics):
    table = Table(title="ME (Multiplexed Endpoint) Statistics", box=box.ROUNDED, show_header=True, header_style="bold yellow")
    table.add_column("Metric", style="green", min_width=55)
    table.add_column("Value", style="yellow", justify="right", min_width=12)
    table.add_column("Description", style="dim", overflow="fold")

    items = [
        ('telemt_me_reconnect_attempts_total', 'Reconnect attempts', 'Total ME reconnect attempts'),
        ('telemt_me_reconnect_success_total', 'Reconnect success', 'Successful ME reconnections'),
        ('telemt_me_handshake_reject_total', 'Handshake rejected', 'ME handshake rejects from upstream'),
        ('telemt_me_reader_eof_total', 'Reader EOF', 'ME reader EOF terminations'),
        ('telemt_me_idle_close_by_peer_total', 'Closed by peer (idle)', 'ME idle writers closed by peer'),
        ('telemt_me_crc_mismatch_total', 'CRC mismatch', 'ME CRC mismatches detected'),
        ('telemt_me_seq_mismatch_total', 'Sequence mismatch', 'ME sequence mismatches detected'),
        ('telemt_me_route_drop_no_conn_total', 'Drop: no connection', 'ME route drops - no bound connection'),
        ('telemt_me_route_drop_channel_closed_total', 'Drop: channel closed', 'ME route drops - channel closed'),
        ('telemt_me_route_drop_queue_full_total', 'Drop: queue full', 'ME route drops - queue backpressure'),
        ('telemt_me_endpoint_quarantine_total', 'Endpoint quarantine', 'Endpoints quarantined due to rapid flaps'),
        ('telemt_me_kdf_drift_total', 'KDF drift', 'KDF input drift detections'),
        ('telemt_me_kdf_port_only_drift_total', 'KDF port-only drift', 'Client-port changes with stable material'),
        ('telemt_me_writer_removed_unexpected_total', 'Writer removed (unexpected)', 'Unexpected writer removals triggering refill'),
        ('telemt_me_writer_restored_same_endpoint_total', 'Restored (same endpoint)', 'Writer restored on same endpoint'),
        ('telemt_me_writer_restored_fallback_total', 'Restored (fallback)', 'Writer restored via fallback endpoint'),
        ('telemt_me_refill_failed_total', 'Refill failed', 'Immediate ME refill failures'),
        ('telemt_me_no_writer_failfast_total', 'No writer failfast', 'Route failfast - missing writer'),
        ('telemt_me_async_recovery_trigger_total', 'Async recovery triggers', 'Async ME recovery from route path'),
        ('telemt_me_writers_active_current', 'Active writers', 'Current non-draining active ME writers'),
        ('telemt_me_writers_warm_current', 'Warm writers', 'Current non-draining warm ME writers'),
        ('telemt_me_writer_removed_unexpected_minus_restored_total', 'Uncompensated removals', 'Removals not yet compensated by restore'),
    ]

    for name, label, desc in items:
        if name in metrics and metrics[name]:
            table.add_row(label, fv(metrics[name][0]['value']), desc)

    return table

def create_me_keepalive_table(metrics):
    table = Table(title="ME Keepalive Statistics", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="green", min_width=40)
    table.add_column("Value", style="yellow", justify="right", min_width=12)
    table.add_column("Description", style="dim")

    items = [
        ('telemt_me_keepalive_sent_total', 'Keepalive sent', 'ME keepalive frames sent'),
        ('telemt_me_keepalive_failed_total', 'Keepalive failed', 'ME keepalive send failures'),
        ('telemt_me_keepalive_pong_total', 'Keepalive pong', 'ME keepalive pong replies received'),
        ('telemt_me_keepalive_timeout_total', 'Keepalive timeout', 'ME keepalive ping timeouts'),
    ]

    for name, label, desc in items:
        if name in metrics and metrics[name]:
            table.add_row(label, fv(metrics[name][0]['value']), desc)

    return table

def create_me_outage_table(metrics):
    table = Table(title="Single-Endpoint Outage Statistics", box=box.ROUNDED, show_header=True, header_style="bold red")
    table.add_column("Metric", style="green", min_width=45)
    table.add_column("Value", style="yellow", justify="right", min_width=12)
    table.add_column("Description", style="dim", overflow="fold")

    items = [
        ('telemt_me_single_endpoint_outage_enter_total', 'Outage enter', 'Transitions to outage state'),
        ('telemt_me_single_endpoint_outage_exit_total', 'Outage exit', 'Outage recovery transitions'),
        ('telemt_me_single_endpoint_outage_reconnect_attempt_total', 'Reconnect attempts', 'Reconnect attempts during outages'),
        ('telemt_me_single_endpoint_outage_reconnect_success_total', 'Reconnect success', 'Successful reconnects during outages'),
        ('telemt_me_single_endpoint_quarantine_bypass_total', 'Quarantine bypass', 'Outage reconnects that bypassed quarantine'),
        ('telemt_me_single_endpoint_shadow_rotate_total', 'Shadow rotations', 'Periodic shadow writer rotations'),
        ('telemt_me_single_endpoint_shadow_rotate_skipped_quarantine_total', 'Shadow skipped (quarantine)', 'Shadow rotations skipped - endpoint quarantined'),
    ]

    for name, label, desc in items:
        if name in metrics and metrics[name]:
            table.add_row(label, fv(metrics[name][0]['value']), desc)

    return table

def create_writer_pick_table(metrics):
    table = Table(title="ME Writer Pick Statistics", box=box.ROUNDED, show_header=True, header_style="bold green")
    table.add_column("Mode", style="cyan", min_width=12)
    table.add_column("Result", style="white", min_width=18)
    table.add_column("Count", justify="right", style="yellow", min_width=12)
    table.add_column("Description", style="dim")

    descs = {
        'success_try': 'Success on first try',
        'success_fallback': 'Success via fallback',
        'full': 'Rejected - queue full',
        'closed': 'Rejected - writer closed',
        'no_candidate': 'No candidate available',
    }

    if 'telemt_me_writer_pick_total' in metrics:
        for item in metrics['telemt_me_writer_pick_total']:
            mode = item['labels'].get('mode', '')
            result = item['labels'].get('result', '')
            val = int(float(item['value']))
            if val > 0 or mode == 'p2c':
                table.add_row(mode, result, fv(item['value']), descs.get(result, ''))

    return table

def create_adaptive_floor_table(metrics):
    table = Table(title="ME Adaptive Floor Configuration", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Parameter", style="green", min_width=45)
    table.add_column("Value", style="yellow", justify="right", min_width=12)
    table.add_column("Description", style="dim", overflow="fold")

    items = [
        ('telemt_me_adaptive_floor_cpu_cores_detected', 'CPU cores detected', 'Logical CPU cores detected'),
        ('telemt_me_adaptive_floor_cpu_cores_effective', 'CPU cores effective', 'Effective CPU cores used'),
        ('telemt_me_adaptive_floor_global_cap_raw', 'Global cap (raw)', 'Raw global adaptive floor cap'),
        ('telemt_me_adaptive_floor_global_cap_effective', 'Global cap (effective)', 'Effective global adaptive cap'),
        ('telemt_me_adaptive_floor_target_writers_total', 'Target writers', 'Adaptive floor target writer count'),
        ('telemt_me_adaptive_floor_active_cap_configured', 'Active cap (configured)', 'Configured active writer cap'),
        ('telemt_me_adaptive_floor_active_cap_effective', 'Active cap (effective)', 'Effective active writer cap'),
        ('telemt_me_adaptive_floor_warm_cap_configured', 'Warm cap (configured)', 'Configured warm writer cap'),
        ('telemt_me_adaptive_floor_warm_cap_effective', 'Warm cap (effective)', 'Effective warm writer cap'),
        ('telemt_me_writers_active_current', 'Active writers now', 'Current non-draining active writers'),
        ('telemt_me_writers_warm_current', 'Warm writers now', 'Current non-draining warm writers'),
        ('telemt_me_floor_cap_block_total', 'Cap blocks', 'Reconnects blocked by adaptive caps'),
        ('telemt_me_floor_swap_idle_total', 'Idle swaps', 'Cap recovery via idle writer swap'),
        ('telemt_me_floor_swap_idle_failed_total', 'Idle swaps failed', 'Failed idle swap attempts'),
    ]

    for name, label, desc in items:
        if name in metrics and metrics[name]:
            table.add_row(label, fv(metrics[name][0]['value']), desc)

    return table

def create_users_table(metrics):
    table = Table(title="User Statistics", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("User", style="cyan", min_width=12)
    table.add_column("Total Conn", justify="right", style="green")
    table.add_column("Active", justify="right", style="yellow")
    table.add_column("RX", justify="right", style="blue")
    table.add_column("TX", justify="right", style="blue")
    table.add_column("Msgs In", justify="right", style="dim")
    table.add_column("Msgs Out", justify="right", style="dim")
    table.add_column("IPs", justify="right", style="white")
    table.add_column("IP Limit", justify="right", style="dim")

    users = defaultdict(dict)
    for mn in [
        'telemt_user_connections_total', 'telemt_user_connections_current',
        'telemt_user_octets_from_client', 'telemt_user_octets_to_client',
        'telemt_user_msgs_from_client', 'telemt_user_msgs_to_client',
        'telemt_user_unique_ips_current', 'telemt_user_unique_ips_limit',
    ]:
        if mn in metrics:
            for item in metrics[mn]:
                user = item['labels'].get('user', 'unknown')
                users[user][mn] = item['value']

    sorted_users = sorted(
        users.items(),
        key=lambda x: int(float(x[1].get('telemt_user_connections_total', '0'))),
        reverse=True
    )

    for user, data in sorted_users:
        ip_limit = data.get('telemt_user_unique_ips_limit', '0')
        ip_limit_display = 'unlimited' if ip_limit == '0' else fv(ip_limit)
        table.add_row(
            user,
            fv(data.get('telemt_user_connections_total', '0')),
            fv(data.get('telemt_user_connections_current', '0')),
            fb(data.get('telemt_user_octets_from_client', '0')),
            fb(data.get('telemt_user_octets_to_client', '0')),
            fv(data.get('telemt_user_msgs_from_client', '0')),
            fv(data.get('telemt_user_msgs_to_client', '0')),
            fv(data.get('telemt_user_unique_ips_current', '0')),
            ip_limit_display,
        )

    return table

def create_socks_table(metrics):
    table = Table(title="SOCKS KDF Policy", box=box.ROUNDED, show_header=True, header_style="bold red")
    table.add_column("Policy", style="cyan", min_width=15)
    table.add_column("Outcome", style="yellow", min_width=15)
    table.add_column("Count", justify="right", style="red", min_width=12)
    table.add_column("Description", style="dim")

    descs = {
        'strict_reject': 'Strict mode rejected connection',
        'compat_fallback': 'Compat mode used fallback KDF',
    }

    if 'telemt_me_socks_kdf_policy_total' in metrics:
        for item in metrics['telemt_me_socks_kdf_policy_total']:
            policy = item['labels'].get('policy', '')
            outcome = item['labels'].get('outcome', '')
            key = f"{policy}_{outcome}"
            table.add_row(policy, outcome, fv(item['value']), descs.get(key, ''))

    return table

def create_pool_table(metrics):
    table = Table(title="Pool Management", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="green", min_width=45)
    table.add_column("Value", style="yellow", justify="right", min_width=12)
    table.add_column("Description", style="dim", overflow="fold")

    items = [
        ('telemt_pool_swap_total', 'Pool swaps', 'Successful ME pool generation swaps'),
        ('telemt_pool_drain_active', 'Active draining', 'Currently draining ME writers'),
        ('telemt_pool_force_close_total', 'Forced close', 'Forced close events for draining writers'),
        ('telemt_pool_drain_soft_evict_total', 'Soft evictions', 'Soft-evicted sessions on stuck writers'),
        ('telemt_pool_drain_soft_evict_writer_total', 'Writers with evictions', 'Draining writers with soft evictions'),
        ('telemt_pool_stale_pick_total', 'Stale picks', 'Stale writer fallback picks for new binds'),
        ('telemt_me_writer_close_signal_drop_total', 'Close signal drops', 'Drops for already-removed writers'),
        ('telemt_me_writer_close_signal_channel_full_total', 'Channel full drops', 'Drops caused by full command channels'),
        ('telemt_me_draining_writers_reap_progress_total', 'Reap progress', 'Draining writer removals by reap cleanup'),
    ]

    for name, label, desc in items:
        if name in metrics and metrics[name]:
            table.add_row(label, fv(metrics[name][0]['value']), desc)

    return table

def create_desync_table(metrics):
    table = Table(title="Security / Desync Statistics", box=box.ROUNDED, show_header=True, header_style="bold red")
    table.add_column("Metric", style="green", min_width=40)
    table.add_column("Value", style="yellow", justify="right", min_width=12)
    table.add_column("Description", style="dim", overflow="fold")

    items = [
        ('telemt_secure_padding_invalid_total', 'Invalid padding', 'Invalid secure frame lengths'),
        ('telemt_desync_total', 'Desync total', 'Total crypto-desync detections'),
        ('telemt_desync_full_logged_total', 'Desync logged', 'Full forensic desync logs emitted'),
        ('telemt_desync_suppressed_total', 'Desync suppressed', 'Suppressed desync forensic events'),
    ]

    for name, label, desc in items:
        if name in metrics and metrics[name]:
            table.add_row(label, fv(metrics[name][0]['value']), desc)

    return table

def create_relay_table(metrics):
    table = Table(title="Relay Adaptive Statistics", box=box.ROUNDED, show_header=True, header_style="bold blue")
    table.add_column("Metric", style="green", min_width=40)
    table.add_column("Value", style="yellow", justify="right", min_width=12)
    table.add_column("Description", style="dim", overflow="fold")

    items = [
        ('telemt_relay_adaptive_promotions_total', 'Promotions', 'Adaptive relay tier promotions'),
        ('telemt_relay_adaptive_demotions_total', 'Demotions', 'Adaptive relay tier demotions'),
        ('telemt_relay_adaptive_hard_promotions_total', 'Hard promotions', 'Hard promotions by write pressure'),
    ]

    for name, label, desc in items:
        if name in metrics and metrics[name]:
            table.add_row(label, fv(metrics[name][0]['value']), desc)

    return table

def main():
    parser = argparse.ArgumentParser(description='MTProxyMax Metrics Viewer')
    parser.add_argument('--url', default=METRICS_URL, help='Metrics URL')
    parser.add_argument(
        '--section',
        choices=['all', 'status', 'main', 'upstream', 'me', 'users', 'socks', 'pool', 'security', 'floor', 'outage', 'relay'],
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
        console.print(create_upstream_attempts_table(m))
        console.print()

    if args.section in ['all', 'me']:
        console.print(create_me_table(m))
        console.print()
        console.print(create_me_keepalive_table(m))
        console.print()
        console.print(create_writer_pick_table(m))
        console.print()

    if args.section in ['all', 'floor']:
        console.print(create_adaptive_floor_table(m))
        console.print()

    if args.section in ['all', 'outage']:
        console.print(create_me_outage_table(m))
        console.print()

    if args.section in ['all', 'socks']:
        console.print(create_socks_table(m))
        console.print()

    if args.section in ['all', 'pool']:
        console.print(create_pool_table(m))
        console.print()

    if args.section in ['all', 'security']:
        console.print(create_desync_table(m))
        console.print()

    if args.section in ['all', 'relay']:
        console.print(create_relay_table(m))
        console.print()

    if args.section in ['all', 'users']:
        console.print(create_users_table(m))
        console.print()

    console.print(f"[dim]Source: {args.url}[/dim]")
    console.print(f"[dim]Sections: status main upstream me floor outage socks pool security relay users[/dim]")

if __name__ == "__main__":
    main()
