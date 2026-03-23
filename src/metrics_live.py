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
        return {}
    metrics = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
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
    return metrics

def fv(value):
    try:
        n = float(value)
        return f"{int(n):,}".replace(',', ' ') if n == int(n) else f"{n:,.1f}".replace(',', ' ')
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
        parts = []
        if d > 0: parts.append(f"{d}d")
        if h > 0: parts.append(f"{h}h")
        if m > 0 or not parts: parts.append(f"{m}m")
        return ' '.join(parts)
    except:
        return seconds

def gv(metrics, name, default='0'):
    return metrics[name][0]['value'] if name in metrics and metrics[name] else default

def generate_dashboard(metrics):
    uptime = fu(gv(metrics, 'telemt_uptime_seconds'))

    total = int(float(gv(metrics, 'telemt_connections_total')))
    bad = int(float(gv(metrics, 'telemt_connections_bad_total')))
    good = total - bad
    ar = (good / total * 100) if total > 0 else 0
    current = int(float(gv(metrics, 'telemt_connections_current', '0')))
    current_me = int(float(gv(metrics, 'telemt_connections_me_current', '0')))
    current_direct = int(float(gv(metrics, 'telemt_connections_direct_current', '0')))

    ut = int(float(gv(metrics, 'telemt_upstream_connect_attempt_total')))
    us = int(float(gv(metrics, 'telemt_upstream_connect_success_total')))
    uf = int(float(gv(metrics, 'telemt_upstream_connect_fail_total')))
    ur = (us / ut * 100) if ut > 0 else 0

    mr = int(float(gv(metrics, 'telemt_me_reconnect_attempts_total')))
    ms = int(float(gv(metrics, 'telemt_me_reconnect_success_total')))
    mrr = (ms / mr * 100) if mr > 0 else 0

    writers_active = int(float(gv(metrics, 'telemt_me_writers_active_current', '0')))
    writers_warm = int(float(gv(metrics, 'telemt_me_writers_warm_current', '0')))
    quarantine = int(float(gv(metrics, 'telemt_me_endpoint_quarantine_total', '0')))

    sc = "green" if ur > 95 else "yellow" if ur > 80 else "red"
    se = f"[{sc}]{'OK' if ur > 95 else 'WARN' if ur > 80 else 'CRIT'}[/{sc}]"

    # System table
    mt = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", expand=True)
    mt.add_column("Metric", style="green")
    mt.add_column("Value", justify="right", style="yellow")

    mt.add_row("Uptime", uptime)
    mt.add_row("", "")
    mt.add_row("[bold]-- Connections --[/bold]", "")
    mt.add_row("Total accepted", fv(str(total)))
    mt.add_row("Authorized", f"[green]{fv(str(good))}[/green] ({ar:.1f}%)")
    mt.add_row("Rejected (no secret)", f"[red]{fv(str(bad))}[/red]")
    mt.add_row("Active now", f"[yellow]{current}[/yellow] (ME:{current_me} D:{current_direct})")
    mt.add_row("", "")
    mt.add_row("[bold]-- Upstream --[/bold]", "")
    mt.add_row("Attempts", fv(str(ut)))
    mt.add_row("Success", f"[green]{fv(str(us))}[/green]")
    mt.add_row("Failed", f"[red]{fv(str(uf))}[/red]")
    mt.add_row("Success rate", f"[{sc}]{ur:.1f}%[/{sc}]")
    mt.add_row("", "")
    mt.add_row("[bold]-- ME --[/bold]", "")
    mt.add_row("Reconnect attempts", fv(str(mr)))
    mt.add_row("Reconnect success", f"[green]{fv(str(ms))}[/green]")
    mt.add_row("Reconnect rate", f"[magenta]{mrr:.1f}%[/magenta]")
    mt.add_row("Writers active/warm", f"{writers_active}/{writers_warm}")
    mt.add_row("Quarantined endpoints", f"[red]{quarantine}[/red]")

    # Users table
    ut2 = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta", expand=True)
    ut2.add_column("User", style="cyan")
    ut2.add_column("Conn", justify="right")
    ut2.add_column("Active", justify="right", style="green")
    ut2.add_column("RX", justify="right", style="blue")
    ut2.add_column("TX", justify="right", style="blue")
    ut2.add_column("IPs", justify="right", style="dim")

    users = defaultdict(dict)
    for mn in [
        'telemt_user_connections_total', 'telemt_user_connections_current',
        'telemt_user_octets_from_client', 'telemt_user_octets_to_client',
        'telemt_user_unique_ips_current',
    ]:
        if mn in metrics:
            for i in metrics[mn]:
                u = i['labels'].get('user', 'unknown')
                users[u][mn] = i['value']

    for u, d in sorted(users.items(), key=lambda x: int(float(x[1].get('telemt_user_connections_total', '0'))), reverse=True):
        ut2.add_row(
            u[:12],
            fv(d.get('telemt_user_connections_total', '0')),
            fv(d.get('telemt_user_connections_current', '0')),
            fb(d.get('telemt_user_octets_from_client', '0')),
            fb(d.get('telemt_user_octets_to_client', '0')),
            fv(d.get('telemt_user_unique_ips_current', '0')),
        )

    # Duration table
    dt = Table(box=box.SIMPLE, show_header=True, header_style="bold blue")
    dt.add_column("Duration", style="cyan")
    dt.add_column("OK", justify="right", style="green")
    dt.add_column("FAIL", justify="right", style="red")
    dt.add_column("%", justify="right", style="yellow")

    bks = ['le_100ms', '101_500ms', '501_1000ms', 'gt_1000ms']
    bns = ['<=100ms', '101-500ms', '501-1s', '>1s']
    sd, fd = {}, {}

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
        f"[bold white]{se} MTPROXYMAX METRICS LIVE[/bold white]  |  "
        f"Uptime: [cyan]{uptime}[/cyan]  |  "
        f"Upstream: [{sc}]{ur:.1f}%[/{sc}]  |  "
        f"Active: [yellow]{current}[/yellow]  |  "
        f"Writers: {writers_active}/{writers_warm}  |  "
        f"[dim]{now}[/dim]",
        box=box.ROUNDED, border_style="blue"
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
    final.add_row(Text(f"Source: {METRICS_URL} | Refresh: {REFRESH_INTERVAL}s | Ctrl+C to exit", style="dim"))

    return final

def main():
    console.print("[bold blue]Starting live metrics viewer...[/bold blue]")
    time.sleep(1)

    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            try:
                raw = fetch_metrics(METRICS_URL)
                m = parse_metrics(raw)

                if m:
                    live.update(generate_dashboard(m))
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
