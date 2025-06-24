"""Process monitoring collector for Node.js, Python, and other application processes."""

import asyncio
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from ..collectors.base import MetricCollector
from ..utils.platform import Platform


logger = logging.getLogger(__name__)


class ProcessCollector(MetricCollector):
    """Collects process metrics for various application types."""
    
    name = "process"
    description = "Process monitoring (Node.js, Python, Java, etc.)"
    default_interval = 5.0
    
    def __init__(self, *args, monitored_processes: List[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Default processes to monitor
        self.monitored_processes = monitored_processes or [
            "node",
            "python",
            "java",
            "docker",
            "pm2",
            "gunicorn",
            "uwsgi",
            "celery",
        ]
    
    async def collect(self, server: str, platform: Platform) -> Dict[str, Any]:
        """Collect process metrics from server."""
        commands = await self.platform_manager.get_server_commands(self.ssh_pool, server)
        
        # Get comprehensive process list
        process_list_cmd = commands.process_list_cmd()
        
        try:
            process_output = await self.ssh_pool.execute(
                server, process_list_cmd, timeout=10.0
            )
            
            # Parse process information
            processes = self._parse_process_list(process_output, platform)
            
            # Filter and organize by process type
            results = {}
            for process_name in self.monitored_processes:
                matching_processes = [
                    p for p in processes 
                    if self._matches_process_pattern(p, process_name)
                ]
                
                if matching_processes:
                    results[process_name] = {
                        "processes": matching_processes,
                        "count": len(matching_processes),
                        "total_cpu": sum(p.get("cpu_percent", 0) for p in matching_processes),
                        "total_memory": sum(p.get("memory_percent", 0) for p in matching_processes),
                        "total_rss": sum(p.get("rss_kb", 0) for p in matching_processes),
                    }
            
            # Get additional Node.js specific metrics
            if "node" in results:
                node_metrics = await self._collect_nodejs_metrics(server)
                results["node"].update(node_metrics)
            
            # Get additional Python specific metrics
            if "python" in results:
                python_metrics = await self._collect_python_metrics(server)
                results["python"].update(python_metrics)
            
            # Get Docker specific metrics
            if "docker" in results:
                docker_metrics = await self._collect_docker_metrics(server)
                results["docker"].update(docker_metrics)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to collect process metrics: {e}")
            return {"error": str(e)}
    
    def _parse_process_list(self, output: str, platform: Platform) -> List[Dict[str, Any]]:
        """Parse process list output."""
        processes = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            try:
                # ps aux format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split(None, 10)  # Split on whitespace, max 11 parts
                
                if len(parts) >= 11:
                    process = {
                        "user": parts[0],
                        "pid": int(parts[1]),
                        "cpu_percent": float(parts[2]),
                        "memory_percent": float(parts[3]),
                        "vsz_kb": int(parts[4]),  # Virtual memory size
                        "rss_kb": int(parts[5]),  # Resident set size
                        "tty": parts[6],
                        "stat": parts[7],
                        "start": parts[8],
                        "time": parts[9],
                        "command": parts[10],
                    }
                    processes.append(process)
            
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse process line: {line} - {e}")
                continue
        
        return processes
    
    def _matches_process_pattern(self, process: Dict[str, Any], pattern: str) -> bool:
        """Check if a process matches the given pattern."""
        command = process.get("command", "").lower()
        
        if pattern == "node":
            return ("node" in command and 
                    not command.startswith("grep") and
                    not "[" in command)  # Exclude kernel threads
        elif pattern == "python":
            return (("python" in command or "python3" in command) and
                    not command.startswith("grep") and
                    not "[" in command)
        elif pattern == "java":
            return ("java" in command and
                    not command.startswith("grep") and
                    not "[" in command)
        elif pattern == "docker":
            return (("docker" in command or "containerd" in command) and
                    not command.startswith("grep"))
        elif pattern == "pm2":
            return ("pm2" in command and not command.startswith("grep"))
        elif pattern == "gunicorn":
            return ("gunicorn" in command and not command.startswith("grep"))
        elif pattern == "uwsgi":
            return ("uwsgi" in command and not command.startswith("grep"))
        elif pattern == "celery":
            return ("celery" in command and not command.startswith("grep"))
        else:
            # Generic pattern matching
            return (pattern in command and not command.startswith("grep"))
    
    async def _collect_nodejs_metrics(self, server: str) -> Dict[str, Any]:
        """Collect Node.js specific metrics."""
        try:
            commands = [
                # Check for PM2 processes
                "pm2 list 2>/dev/null | tail -n +4 | head -n -1 || echo 'no_pm2'",
                # Check Node.js version
                "node --version 2>/dev/null || echo 'no_node'",
                # Check NPM processes/version
                "npm --version 2>/dev/null || echo 'no_npm'",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=10.0
            )
            
            metrics = {}
            
            # Parse PM2 list
            if results[0] != "no_pm2":
                metrics["pm2_processes"] = self._parse_pm2_list(results[0])
            
            # Parse Node.js version
            if results[1] != "no_node":
                metrics["node_version"] = results[1].strip()
            
            # Parse NPM version
            if results[2] != "no_npm":
                metrics["npm_version"] = results[2].strip()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect Node.js metrics: {e}")
            return {"nodejs_error": str(e)}
    
    async def _collect_python_metrics(self, server: str) -> Dict[str, Any]:
        """Collect Python specific metrics."""
        try:
            commands = [
                # Check Python version
                "python3 --version 2>/dev/null || python --version 2>/dev/null || echo 'no_python'",
                # Check pip version
                "pip3 --version 2>/dev/null || pip --version 2>/dev/null || echo 'no_pip'",
                # Check for virtual environments
                "pgrep -f 'venv/\\|virtualenv\\|conda' | wc -l",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=10.0
            )
            
            metrics = {}
            
            # Parse Python version
            if results[0] != "no_python":
                version_match = re.search(r'Python (\d+\.\d+\.\d+)', results[0])
                if version_match:
                    metrics["python_version"] = version_match.group(1)
            
            # Parse pip version
            if results[1] != "no_pip":
                version_match = re.search(r'pip (\d+\.\d+\.\d+)', results[1])
                if version_match:
                    metrics["pip_version"] = version_match.group(1)
            
            # Parse virtual environment count
            venv_count = results[2].strip()
            if venv_count.isdigit():
                metrics["virtual_env_processes"] = int(venv_count)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect Python metrics: {e}")
            return {"python_error": str(e)}
    
    async def _collect_docker_metrics(self, server: str) -> Dict[str, Any]:
        """Collect Docker specific metrics."""
        try:
            commands = [
                # Check Docker version
                "docker --version 2>/dev/null || echo 'no_docker'",
                # List running containers
                "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo 'no_containers'",
                # Get Docker system info
                "docker system df 2>/dev/null || echo 'no_system_info'",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=15.0
            )
            
            metrics = {}
            
            # Parse Docker version
            if results[0] != "no_docker":
                version_match = re.search(r'Docker version (\d+\.\d+\.\d+)', results[0])
                if version_match:
                    metrics["docker_version"] = version_match.group(1)
            
            # Parse running containers
            if results[1] != "no_containers":
                containers = self._parse_docker_containers(results[1])
                metrics["containers"] = containers
                metrics["container_count"] = len(containers)
            
            # Parse system info
            if results[2] != "no_system_info":
                system_info = self._parse_docker_system_info(results[2])
                metrics.update(system_info)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect Docker metrics: {e}")
            return {"docker_error": str(e)}
    
    def _parse_pm2_list(self, output: str) -> List[Dict[str, Any]]:
        """Parse PM2 list output."""
        processes = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip() or "│" not in line:
                continue
            
            try:
                # PM2 list format with table separators
                parts = [p.strip() for p in line.split('│')]
                if len(parts) >= 6:
                    process = {
                        "name": parts[1],
                        "mode": parts[2],
                        "pid": parts[3],
                        "status": parts[4],
                        "restart": parts[5],
                        "uptime": parts[6] if len(parts) > 6 else "",
                        "cpu": parts[7] if len(parts) > 7 else "",
                        "memory": parts[8] if len(parts) > 8 else "",
                    }
                    processes.append(process)
            except (ValueError, IndexError):
                continue
        
        return processes
    
    def _parse_docker_containers(self, output: str) -> List[Dict[str, Any]]:
        """Parse Docker ps output."""
        containers = []
        lines = output.strip().split('\n')
        
        # Skip header line
        for line in lines[1:]:
            if not line.strip():
                continue
            
            try:
                parts = line.split('\t')
                if len(parts) >= 3:
                    container = {
                        "name": parts[0].strip(),
                        "status": parts[1].strip(),
                        "ports": parts[2].strip(),
                    }
                    containers.append(container)
            except (ValueError, IndexError):
                continue
        
        return containers
    
    def _parse_docker_system_info(self, output: str) -> Dict[str, Any]:
        """Parse Docker system df output."""
        info = {}
        lines = output.strip().split('\n')
        
        for line in lines:
            if "Images" in line:
                # Parse images line
                match = re.search(r'(\d+)\s+\d+\s+([\d.]+\w+)', line)
                if match:
                    info["image_count"] = int(match.group(1))
                    info["images_size"] = match.group(2)
            elif "Containers" in line:
                # Parse containers line
                match = re.search(r'(\d+)\s+\d+\s+([\d.]+\w+)', line)
                if match:
                    info["total_containers"] = int(match.group(1))
                    info["containers_size"] = match.group(2)
            elif "Local Volumes" in line:
                # Parse volumes line
                match = re.search(r'(\d+)\s+\d+\s+([\d.]+\w+)', line)
                if match:
                    info["volume_count"] = int(match.group(1))
                    info["volumes_size"] = match.group(2)
        
        return info