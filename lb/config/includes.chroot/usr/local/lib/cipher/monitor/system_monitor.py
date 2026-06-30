#!/usr/bin/env python3
"""CipherOS system monitor — watches CPU/RAM/disk/GPU and alerts via HUD."""
import asyncio
import json
import logging
import signal
import sys
import time

sys.path.insert(0, "/usr/local/lib")
from cipher.utils.logger import setup_logger
from cipher.utils.config_loader import get_monitor_config

logger = setup_logger("system-monitor")
HUD_SOCKET = "/tmp/cipher_hud.sock"


async def send_hud(data: dict) -> None:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(HUD_SOCKET), timeout=2.0
        )
        writer.write((json.dumps(data) + "\n").encode())
        await writer.drain()
        writer.close()
    except Exception:
        pass


async def monitor_loop() -> None:
    import psutil
    cfg      = get_monitor_config()
    poll     = cfg.get("polling", {}).get("interval", 10)
    thresh   = cfg.get("thresholds", {})
    cooldown = cfg.get("alerts", {}).get("cooldown", 300)
    last_alert: dict[str, float] = {}

    cpu_warn  = thresh.get("cpu_warning", 85)
    cpu_crit  = thresh.get("cpu_critical", 95)
    ram_warn  = thresh.get("ram_warning", 80)
    ram_crit  = thresh.get("ram_critical", 92)
    disk_warn = thresh.get("disk_warning", 85)
    disk_crit = thresh.get("disk_critical", 95)

    logger.info(f"System monitor active (poll every {poll}s)")

    while True:
        try:
            now = time.time()
            cpu  = psutil.cpu_percent(interval=1)
            mem  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net  = psutil.net_io_counters()
            temps: dict = {}
            try:
                sensor_data = psutil.sensors_temperatures()
                for chip, entries in sensor_data.items():
                    for e in entries:
                        if e.current:
                            temps[e.label or chip] = round(e.current, 1)
            except Exception:
                pass

            metrics = {
                "cpu_percent":   round(cpu, 1),
                "ram_percent":   round(mem.percent, 1),
                "ram_used_gb":   round(mem.used / 1e9, 2),
                "ram_total_gb":  round(mem.total / 1e9, 2),
                "disk_percent":  round(disk.percent, 1),
                "disk_free_gb":  round(disk.free / 1e9, 2),
                "net_sent_mb":   round(net.bytes_sent / 1e6, 2),
                "net_recv_mb":   round(net.bytes_recv / 1e6, 2),
                "temperatures":  temps,
            }

            await send_hud({"type": "system_metrics", "data": metrics})

            # Alert logic
            def _should_alert(key: str) -> bool:
                return (now - last_alert.get(key, 0)) > cooldown

            if cpu >= cpu_crit and _should_alert("cpu_crit"):
                await send_hud({"type": "alert", "data": {
                    "level": "critical", "title": "CPU Critical",
                    "message": f"CPU at {cpu:.0f}%"
                }})
                last_alert["cpu_crit"] = now
            elif cpu >= cpu_warn and _should_alert("cpu_warn"):
                await send_hud({"type": "alert", "data": {
                    "level": "warning", "title": "CPU High",
                    "message": f"CPU at {cpu:.0f}%"
                }})
                last_alert["cpu_warn"] = now

            if mem.percent >= ram_crit and _should_alert("ram_crit"):
                await send_hud({"type": "alert", "data": {
                    "level": "critical", "title": "RAM Critical",
                    "message": f"RAM at {mem.percent:.0f}%"
                }})
                last_alert["ram_crit"] = now

            if disk.percent >= disk_warn and _should_alert("disk"):
                await send_hud({"type": "alert", "data": {
                    "level": "warning", "title": "Disk Space Low",
                    "message": f"Disk {disk.percent:.0f}% full ({disk.free/1e9:.1f} GB free)"
                }})
                last_alert["disk"] = now

        except Exception as exc:
            logger.error(f"Monitor error: {exc}")

        await asyncio.sleep(poll)


def main() -> None:
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    asyncio.run(monitor_loop())


if __name__ == "__main__":
    main()
