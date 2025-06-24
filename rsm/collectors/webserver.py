"""Webserver metrics collector for Apache and Nginx."""

import asyncio
import re
import logging
from typing import Dict, Any, List, Optional
from ..collectors.base import MetricCollector
from ..utils.platform import Platform


logger = logging.getLogger(__name__)


class WebServerCollector(MetricCollector):
    """Collects webserver metrics for Apache and Nginx."""
    
    name = "webserver"
    description = "Webserver metrics (Apache, Nginx)"
    default_interval = 5.0
    
    async def collect(self, server: str, platform: Platform) -> Dict[str, Any]:
        """Collect webserver metrics from server."""
        results = {}
        
        # Collect Apache metrics
        apache_data = await self._collect_apache_metrics(server)
        if apache_data:
            results["apache"] = apache_data
        
        # Collect Nginx metrics
        nginx_data = await self._collect_nginx_metrics(server)
        if nginx_data:
            results["nginx"] = nginx_data
        
        return results
    
    async def _collect_apache_metrics(self, server: str) -> Optional[Dict[str, Any]]:
        """Collect Apache metrics."""
        try:
            # Check if Apache is running
            processes_result = await self.ssh_pool.execute(
                server,
                "pgrep -f 'apache2|httpd' | wc -l",
                timeout=5.0
            )
            
            process_count = int(processes_result.strip())
            if process_count == 0:
                return None
            
            # Get Apache status information
            commands = [
                # Check if mod_status is available
                "curl -s http://localhost/server-status?auto 2>/dev/null || echo 'status_unavailable'",
                # Get process information
                "ps aux | grep -E '[a]pache2|[h]ttpd' | wc -l",
                # Check service status
                "systemctl is-active apache2 2>/dev/null || systemctl is-active httpd 2>/dev/null || echo 'unknown'",
                # Get listening ports
                "netstat -tlnp 2>/dev/null | grep -E ':80 |:443 ' | grep -E 'apache2|httpd' || echo 'no_ports'",
                # Check configuration syntax
                "apache2ctl configtest 2>&1 || httpd -t 2>&1 || echo 'config_check_failed'",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=10.0
            )
            
            status_info = results[0]
            process_count_str = results[1]
            service_status = results[2].strip()
            ports_info = results[3]
            config_test = results[4]
            
            apache_metrics = {
                "service": "apache",
                "status": service_status,
                "process_count": int(process_count_str.strip()) if process_count_str.strip().isdigit() else 0,
                "ports": self._parse_apache_ports(ports_info),
                "config_valid": "Syntax OK" in config_test,
            }
            
            # Parse mod_status if available
            if status_info != "status_unavailable":
                status_metrics = self._parse_apache_status(status_info)
                apache_metrics.update(status_metrics)
            
            return apache_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect Apache metrics: {e}")
            return {
                "service": "apache",
                "status": "error",
                "error": str(e)
            }
    
    async def _collect_nginx_metrics(self, server: str) -> Optional[Dict[str, Any]]:
        """Collect Nginx metrics."""
        try:
            # Check if Nginx is running
            processes_result = await self.ssh_pool.execute(
                server,
                "pgrep nginx | wc -l",
                timeout=5.0
            )
            
            process_count = int(processes_result.strip())
            if process_count == 0:
                return None
            
            commands = [
                # Get nginx status if stub_status is available
                "curl -s http://localhost/nginx_status 2>/dev/null || echo 'status_unavailable'",
                # Get process information
                "ps aux | grep '[n]ginx' | wc -l",
                # Check service status
                "systemctl is-active nginx 2>/dev/null || echo 'unknown'",
                # Get listening ports
                "netstat -tlnp 2>/dev/null | grep nginx || echo 'no_ports'",
                # Check configuration syntax
                "nginx -t 2>&1 || echo 'config_check_failed'",
                # Get worker processes
                "ps aux | grep '[n]ginx: worker' | wc -l",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=10.0
            )
            
            status_info = results[0]
            process_count_str = results[1]
            service_status = results[2].strip()
            ports_info = results[3]
            config_test = results[4]
            worker_count_str = results[5]
            
            nginx_metrics = {
                "service": "nginx",
                "status": service_status,
                "process_count": int(process_count_str.strip()) if process_count_str.strip().isdigit() else 0,
                "worker_count": int(worker_count_str.strip()) if worker_count_str.strip().isdigit() else 0,
                "ports": self._parse_nginx_ports(ports_info),
                "config_valid": "syntax is ok" in config_test.lower(),
            }
            
            # Parse stub_status if available
            if status_info != "status_unavailable":
                status_metrics = self._parse_nginx_status(status_info)
                nginx_metrics.update(status_metrics)
            
            return nginx_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect Nginx metrics: {e}")
            return {
                "service": "nginx",
                "status": "error",
                "error": str(e)
            }
    
    def _parse_apache_status(self, output: str) -> Dict[str, Any]:
        """Parse Apache mod_status output."""
        metrics = {}
        
        # Parse key-value pairs from mod_status
        patterns = {
            "total_accesses": r"Total Accesses:\s*(\d+)",
            "total_kbytes": r"Total kBytes:\s*(\d+)",
            "cpu_load": r"CPULoad:\s*(\d+\.?\d*)",
            "uptime": r"Uptime:\s*(\d+)",
            "requests_per_sec": r"ReqPerSec:\s*(\d+\.?\d*)",
            "bytes_per_sec": r"BytesPerSec:\s*(\d+\.?\d*)",
            "bytes_per_req": r"BytesPerReq:\s*(\d+\.?\d*)",
            "busy_workers": r"BusyWorkers:\s*(\d+)",
            "idle_workers": r"IdleWorkers:\s*(\d+)",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                try:
                    value = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
                    metrics[key] = value
                except ValueError:
                    continue
        
        return metrics
    
    def _parse_nginx_status(self, output: str) -> Dict[str, Any]:
        """Parse Nginx stub_status output."""
        metrics = {}
        
        # Nginx stub_status format:
        # Active connections: 291
        # server accepts handled requests
        #  16630948 16630948 31070465
        # Reading: 6 Writing: 179 Waiting: 106
        
        # Parse active connections
        active_match = re.search(r"Active connections:\s*(\d+)", output)
        if active_match:
            metrics["active_connections"] = int(active_match.group(1))
        
        # Parse server stats line
        stats_match = re.search(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s*$", output, re.MULTILINE)
        if stats_match:
            metrics["accepts"] = int(stats_match.group(1))
            metrics["handled"] = int(stats_match.group(2))
            metrics["requests"] = int(stats_match.group(3))
        
        # Parse reading/writing/waiting
        rww_match = re.search(r"Reading:\s*(\d+)\s+Writing:\s*(\d+)\s+Waiting:\s*(\d+)", output)
        if rww_match:
            metrics["reading"] = int(rww_match.group(1))
            metrics["writing"] = int(rww_match.group(2))
            metrics["waiting"] = int(rww_match.group(3))
        
        return metrics
    
    def _parse_apache_ports(self, output: str) -> List[Dict[str, Any]]:
        """Parse Apache listening ports from netstat output."""
        ports: List[Dict[str, Any]] = []
        
        if output == "no_ports":
            return ports
        
        lines = output.strip().split('\n')
        for line in lines:
            # Parse netstat line
            # tcp6       0      0 :::80                   :::*                    LISTEN      12345/apache2
            match = re.search(r':(\d+)\s+.*?(\d+)/(apache2|httpd)', line)
            if match:
                port = int(match.group(1))
                pid = int(match.group(2))
                process = match.group(3)
                
                ports.append({
                    "port": port,
                    "pid": pid,
                    "process": process,
                })
        
        return ports
    
    def _parse_nginx_ports(self, output: str) -> List[Dict[str, Any]]:
        """Parse Nginx listening ports from netstat output."""
        ports: List[Dict[str, Any]] = []
        
        if output == "no_ports":
            return ports
        
        lines = output.strip().split('\n')
        for line in lines:
            # Parse netstat line for nginx
            match = re.search(r':(\d+)\s+.*?(\d+)/nginx', line)
            if match:
                port = int(match.group(1))
                pid = int(match.group(2))
                
                ports.append({
                    "port": port,
                    "pid": pid,
                    "process": "nginx",
                })
        
        return ports


class ServiceCollector(MetricCollector):
    """Generic service collector for monitoring specific services."""
    
    name = "service"
    description = "Generic service monitoring"
    default_interval = 10.0
    
    def __init__(self, *args, services: Optional[List[str]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.services = services or []
    
    async def collect(self, server: str, platform: Platform) -> Dict[str, Any]:
        """Collect service metrics."""
        if not self.services:
            return {}
        
        commands = []
        for service in self.services:
            commands.extend([
                f"pgrep -f '{service}' | wc -l",  # Process count
                f"systemctl is-active {service} 2>/dev/null || echo 'unknown'",  # Service status
            ])
        
        try:
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=10.0
            )
            
            service_data = {}
            for i, service in enumerate(self.services):
                process_count = results[i * 2]
                service_status = results[i * 2 + 1].strip()
                
                service_data[service] = {
                    "name": service,
                    "process_count": int(process_count.strip()) if process_count.strip().isdigit() else 0,
                    "status": service_status,
                    "running": service_status == "active" or int(process_count.strip() or "0") > 0,
                }
            
            return {"services": service_data}
            
        except Exception as e:
            logger.error(f"Failed to collect service metrics: {e}")
            return {"error": str(e)}