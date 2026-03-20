cat > src/metrics_live.py << 'PYEOF'
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

def gv(metrics, name, default='0'):
    return metrics[name][0]['value'] if name in metrics and metrics[name] else default

def generate_dashboard(metrics):
    total = int(float(gv(metrics, 'telemt_connections_total')))
    bad = int(float(gv(metrics, 'telemt_connections_bad_total')))
    ut = int(float(gv(metrics, 'telemt_upstream_connect_attempt_total')))
    us = int(float(gv(metrics, 'telemt_upstream_connect_success_total')))
    ur = (us / ut * 100) if ut > 0 else 0
    
    sc = "green" if ur > 95 else "yellow" if ur > 80 else "red"
    se = f"[{sc}]{'OK' if ur > 95 else 'WARN' if ur > 80 else 'CRIT'}[/{sc}]"
    now = datetime.now().strftime("%H:%M:%S")
    
    info = Text(
        f"Status: {se}\n"
        f"Connections: {fv(str(total))}\n"
        f"Upstream: [{sc}]{ur:.1f}%[/{sc}]\n"
        f"\nPress Ctrl+C to exit",
        style="white"
    )
    
    header = Panel(
        f"[bold white]{se} MTPROTOMAX METRICS LIVE[/bold white]  |  {now}",
        box=box.ROUNDED, border_style="blue"
    )
    
    panel = Panel(info, title="Status", border_style=sc)
    
    final = Table.grid(expand=True)
    final.add_row(header)
    final.add_row(panel)
    final.add_row(Text(f"Refresh: {REFRESH_INTERVAL}s", style="dim"))
    
    return final

def main():
    console.print("[bold blue]Starting live metrics...[/bold blue]")
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
PYEOF

chmod +x src/metrics_live.py
