"""System data collector — psutil wrapper for Furnace."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import psutil


@dataclass
class SystemSnapshot:
    cpu_percent: float = 0.0
    cpu_per_core: list[float] = field(default_factory=list)
    mem_total: int = 0
    mem_used: int = 0
    mem_percent: float = 0.0
    swap_total: int = 0
    swap_used: int = 0
    swap_percent: float = 0.0
    disk_read_rate: float = 0.0   # bytes/sec
    disk_write_rate: float = 0.0  # bytes/sec
    net_recv_rate: float = 0.0    # bytes/sec
    net_send_rate: float = 0.0    # bytes/sec
    net_per_nic: dict[str, tuple[float, float]] = field(default_factory=dict)
    cpu_temp: float | None = None
    load_avg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    uptime: float = 0.0
    processes: list[ProcessInfo] = field(default_factory=list)


@dataclass
class ProcessInfo:
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str


class Collector:
    """Collects system snapshots with rate calculations for I/O."""

    def __init__(self):
        self._prev_disk = psutil.disk_io_counters()
        self._prev_net = psutil.net_io_counters()
        self._prev_net_per_nic = psutil.net_io_counters(pernic=True)
        self._prev_time = time.monotonic()
        # Prime cpu_percent (first call always returns 0)
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)

    def collect(self, include_processes: bool = False) -> SystemSnapshot:
        now = time.monotonic()
        dt = now - self._prev_time
        if dt < 0.01:
            dt = 1.0
        self._prev_time = now

        # CPU
        cpu = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_percent(interval=None, percpu=True)

        # Memory
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk I/O rates
        disk = psutil.disk_io_counters()
        disk_read_rate = 0.0
        disk_write_rate = 0.0
        if disk and self._prev_disk:
            disk_read_rate = (disk.read_bytes - self._prev_disk.read_bytes) / dt
            disk_write_rate = (disk.write_bytes - self._prev_disk.write_bytes) / dt
        self._prev_disk = disk

        # Network I/O rates
        net = psutil.net_io_counters()
        net_recv_rate = (net.bytes_recv - self._prev_net.bytes_recv) / dt
        net_send_rate = (net.bytes_sent - self._prev_net.bytes_sent) / dt
        self._prev_net = net

        # Per-NIC rates
        net_per_nic = {}
        cur_nics = psutil.net_io_counters(pernic=True)
        for nic, counters in cur_nics.items():
            if nic in self._prev_net_per_nic:
                prev = self._prev_net_per_nic[nic]
                recv_rate = (counters.bytes_recv - prev.bytes_recv) / dt
                send_rate = (counters.bytes_sent - prev.bytes_sent) / dt
                net_per_nic[nic] = (recv_rate, send_rate)
        self._prev_net_per_nic = cur_nics

        # Temperature
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                if key in temps and temps[key]:
                    cpu_temp = temps[key][0].current
                    break
        except Exception:
            pass

        # Load average
        load_avg = os.getloadavg()

        # Uptime
        uptime = time.time() - psutil.boot_time()

        # Processes (expensive — only when requested)
        processes = []
        if include_processes:
            for proc in psutil.process_iter(
                ["pid", "name", "username", "cpu_percent", "memory_percent", "status"]
            ):
                info = proc.info
                processes.append(ProcessInfo(
                    pid=info["pid"],
                    name=info["name"] or "?",
                    username=info["username"] or "?",
                    cpu_percent=info["cpu_percent"] or 0.0,
                    memory_percent=info["memory_percent"] or 0.0,
                    status=info["status"] or "?",
                ))

        return SystemSnapshot(
            cpu_percent=cpu,
            cpu_per_core=cpu_cores,
            mem_total=mem.total,
            mem_used=mem.used,
            mem_percent=mem.percent,
            swap_total=swap.total,
            swap_used=swap.used,
            swap_percent=swap.percent,
            disk_read_rate=disk_read_rate,
            disk_write_rate=disk_write_rate,
            net_recv_rate=net_recv_rate,
            net_send_rate=net_send_rate,
            net_per_nic=net_per_nic,
            cpu_temp=cpu_temp,
            load_avg=load_avg,
            uptime=uptime,
            processes=processes,
        )
