"""System metrics collector for CPU, memory, disk, and load."""

import asyncio
import re
import logging
from typing import Dict, Any, List, Tuple
from ..collectors.base import MetricCollector
from ..utils.platform import Platform


logger = logging.getLogger(__name__)


class SystemMetricsCollector(MetricCollector):
    """Collects system metrics: CPU, memory, disk, and load."""
    
    name = "system"
    description = "System metrics (CPU, memory, disk, load)"
    default_interval = 2.0
    
    async def collect(self, server: str, platform: Platform) -> Dict[str, Any]:
        """Collect system metrics from server."""
        commands = await self.platform_manager.get_server_commands(self.ssh_pool, server)
        
        # Execute commands in parallel
        results = await self.ssh_pool.execute_batch(
            server,
            [
                commands.cpu_usage_cmd(),
                commands.memory_info_cmd(),
                commands.disk_usage_cmd(),
                commands.uptime_cmd(),
            ],
            timeout=10.0
        )
        
        return {
            "cpu": self._parse_cpu(results[0], platform),
            "memory": self._parse_memory(results[1], platform),
            "disk": self._parse_disk(results[2]),
            "load": self._parse_load(results[3]),
        }
    
    def _parse_cpu(self, output: str, platform: Platform) -> Dict[str, Any]:
        """Parse CPU usage based on platform."""
        try:
            if platform == Platform.LINUX:
                return self._parse_linux_cpu(output)
            elif platform in (Platform.FREEBSD, Platform.OPENBSD):
                return self._parse_bsd_cpu(output)
            elif platform == Platform.MACOS:
                return self._parse_macos_cpu(output)
            else:
                logger.warning(f"Unknown platform for CPU parsing: {platform}")
                return {"usage_percent": 0.0, "error": "Unknown platform"}
        except Exception as e:
            logger.error(f"Failed to parse CPU data: {e}")
            return {"usage_percent": 0.0, "error": str(e)}
    
    def _parse_linux_cpu(self, output: str) -> Dict[str, float]:
        """Parse Linux /proc/stat output."""
        lines = output.strip().split('\n')
        
        # First line contains overall CPU stats
        cpu_line = lines[0].split()
        if not cpu_line[0].startswith('cpu'):
            raise ValueError("Invalid /proc/stat format")
        
        # Values are: user nice system idle iowait irq softirq steal guest guest_nice
        values = [int(x) for x in cpu_line[1:8]]  # Take first 7 values
        
        user, nice, system, idle, iowait, irq, softirq = values
        
        total = sum(values)
        idle_total = idle + iowait
        used = total - idle_total
        
        usage_percent = (used / total * 100) if total > 0 else 0.0
        
        return {
            "usage_percent": round(usage_percent, 2),
            "user": user,
            "system": system,
            "idle": idle,
            "iowait": iowait,
        }
    
    def _parse_bsd_cpu(self, output: str) -> Dict[str, float]:
        """Parse BSD top output."""
        # Look for CPU line in top output
        cpu_match = re.search(
            r'CPU:\s*(\d+\.?\d*)%\s*user.*?(\d+\.?\d*)%\s*idle',
            output,
            re.IGNORECASE
        )
        
        if cpu_match:
            user = float(cpu_match.group(1))
            idle = float(cpu_match.group(2))
            usage_percent = 100.0 - idle
            
            return {
                "usage_percent": round(usage_percent, 2),
                "user": user,
                "idle": idle,
            }
        
        return {"usage_percent": 0.0, "error": "Could not parse CPU usage"}
    
    def _parse_macos_cpu(self, output: str) -> Dict[str, float]:
        """Parse macOS top output."""
        # macOS top format: "CPU usage: X.X% user, Y.Y% sys, Z.Z% idle"
        cpu_match = re.search(
            r'CPU usage:\s*(\d+\.?\d*)%\s*user.*?(\d+\.?\d*)%\s*sys.*?(\d+\.?\d*)%\s*idle',
            output,
            re.IGNORECASE
        )
        
        if cpu_match:
            user = float(cpu_match.group(1))
            system = float(cpu_match.group(2))
            idle = float(cpu_match.group(3))
            usage_percent = 100.0 - idle
            
            return {
                "usage_percent": round(usage_percent, 2),
                "user": user,
                "system": system,
                "idle": idle,
            }
        
        return {"usage_percent": 0.0, "error": "Could not parse CPU usage"}
    
    def _parse_memory(self, output: str, platform: Platform) -> Dict[str, Any]:
        """Parse memory info based on platform."""
        try:
            if platform == Platform.LINUX:
                return self._parse_linux_memory(output)
            elif platform in (Platform.FREEBSD, Platform.OPENBSD):
                return self._parse_bsd_memory(output)
            elif platform == Platform.MACOS:
                return self._parse_macos_memory(output)
            else:
                return {"error": "Unknown platform"}
        except Exception as e:
            logger.error(f"Failed to parse memory data: {e}")
            return {"error": str(e)}
    
    def _parse_linux_memory(self, output: str) -> Dict[str, Any]:
        """Parse Linux /proc/meminfo output."""
        memory_info = {}
        
        # Parse key memory values
        patterns = {
            'MemTotal': r'MemTotal:\s*(\d+)\s*kB',
            'MemFree': r'MemFree:\s*(\d+)\s*kB',
            'MemAvailable': r'MemAvailable:\s*(\d+)\s*kB',
            'Buffers': r'Buffers:\s*(\d+)\s*kB',
            'Cached': r'Cached:\s*(\d+)\s*kB',
            'SwapTotal': r'SwapTotal:\s*(\d+)\s*kB',
            'SwapFree': r'SwapFree:\s*(\d+)\s*kB',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                memory_info[key] = int(match.group(1)) * 1024  # Convert to bytes
        
        # Calculate derived values
        if 'MemTotal' in memory_info and 'MemAvailable' in memory_info:
            total = memory_info['MemTotal']
            available = memory_info['MemAvailable']
            used = total - available
            
            return {
                "total_bytes": total,
                "available_bytes": available,
                "used_bytes": used,
                "usage_percent": round((used / total * 100) if total > 0 else 0, 2),
                "buffers_bytes": memory_info.get('Buffers', 0),
                "cached_bytes": memory_info.get('Cached', 0),
                "swap_total_bytes": memory_info.get('SwapTotal', 0),
                "swap_free_bytes": memory_info.get('SwapFree', 0),
            }
        
        return {"error": "Could not parse memory info"}
    
    def _parse_bsd_memory(self, output: str) -> Dict[str, Any]:
        """Parse BSD sysctl memory output."""
        # Parse sysctl output for memory values
        lines = output.strip().split('\n')
        
        if len(lines) >= 2:
            try:
                total = int(lines[0])
                user_mem = int(lines[1])
                
                # Rough approximation - BSD doesn't provide available memory easily
                used = user_mem
                usage_percent = (used / total * 100) if total > 0 else 0
                
                return {
                    "total_bytes": total,
                    "used_bytes": used,
                    "usage_percent": round(usage_percent, 2),
                }
            except ValueError:
                pass
        
        return {"error": "Could not parse memory info"}
    
    def _parse_macos_memory(self, output: str) -> Dict[str, Any]:
        """Parse macOS vm_stat output."""
        # Parse vm_stat output
        page_size_match = re.search(r'page size of (\d+) bytes', output)
        page_size = int(page_size_match.group(1)) if page_size_match else 4096
        
        stats = {}
        patterns = {
            'free': r'Pages free:\s*(\d+)',
            'active': r'Pages active:\s*(\d+)',
            'inactive': r'Pages inactive:\s*(\d+)',
            'wired': r'Pages wired down:\s*(\d+)',
            'compressed': r'Pages compressed:\s*(\d+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                stats[key] = int(match.group(1)) * page_size
        
        if stats:
            # Calculate total and used
            total = sum(stats.values())
            free = stats.get('free', 0)
            used = total - free
            
            return {
                "total_bytes": total,
                "free_bytes": free,
                "used_bytes": used,
                "usage_percent": round((used / total * 100) if total > 0 else 0, 2),
                "active_bytes": stats.get('active', 0),
                "inactive_bytes": stats.get('inactive', 0),
                "wired_bytes": stats.get('wired', 0),
            }
        
        return {"error": "Could not parse memory info"}
    
    def _parse_disk(self, output: str) -> List[Dict[str, Any]]:
        """Parse df -h output (cross-platform)."""
        disks = []
        lines = output.strip().split('\n')
        
        # Skip header line
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                # Handle filesystem names with spaces
                if len(parts) > 6:
                    # Merge filesystem name parts
                    filesystem = ' '.join(parts[:-5])
                    parts = [filesystem] + parts[-5:]
                
                try:
                    filesystem, size, used, avail, percent, mount = parts[:6]
                    
                    # Include real filesystems (usually start with /dev/ or are mount points)
                    if not filesystem.startswith(('tmpfs', 'proc', 'sys', 'dev')) and filesystem != 'Filesystem':
                        # Parse percentage (remove % sign)
                        usage_percent = float(percent.rstrip('%'))
                        
                        disks.append({
                            "filesystem": filesystem,
                            "mount_point": mount,
                            "size": size,
                            "used": used,
                            "available": avail,
                            "usage_percent": usage_percent,
                        })
                except ValueError:
                    continue
        
        return disks
    
    def _parse_load(self, output: str) -> Dict[str, float]:
        """Parse uptime output for load averages."""
        # Look for load average pattern
        load_match = re.search(
            r'load average[s]?:\s*(\d+\.?\d*)[,\s]+(\d+\.?\d*)[,\s]+(\d+\.?\d*)',
            output,
            re.IGNORECASE
        )
        
        if load_match:
            return {
                "1min": float(load_match.group(1)),
                "5min": float(load_match.group(2)),
                "15min": float(load_match.group(3)),
            }
        
        return {"1min": 0.0, "5min": 0.0, "15min": 0.0}