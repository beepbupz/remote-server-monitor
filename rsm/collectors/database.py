"""Database metrics collector for MySQL, PostgreSQL, and other databases."""

import asyncio
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from ..collectors.base import MetricCollector
from ..utils.platform import Platform


logger = logging.getLogger(__name__)


class DatabaseCollector(MetricCollector):
    """Collects database metrics for MySQL, PostgreSQL, and other databases."""
    
    name = "database"
    description = "Database metrics (MySQL, PostgreSQL, Redis, etc.)"
    default_interval = 10.0
    
    async def collect(self, server: str, platform: Platform) -> Dict[str, Any]:
        """Collect database metrics from server."""
        results = {}
        
        # Collect MySQL metrics
        mysql_data = await self._collect_mysql_metrics(server)
        if mysql_data:
            results["mysql"] = mysql_data
        
        # Collect PostgreSQL metrics
        postgres_data = await self._collect_postgres_metrics(server)
        if postgres_data:
            results["postgresql"] = postgres_data
        
        # Collect Redis metrics
        redis_data = await self._collect_redis_metrics(server)
        if redis_data:
            results["redis"] = redis_data
        
        return results
    
    async def _collect_mysql_metrics(self, server: str) -> Optional[Dict[str, Any]]:
        """Collect MySQL metrics."""
        try:
            # Check if MySQL is running
            processes_result = await self.ssh_pool.execute(
                server,
                "pgrep -f 'mysqld' | wc -l",
                timeout=5.0
            )
            
            process_count = int(processes_result.strip())
            if process_count == 0:
                return None
            
            commands = [
                # Get MySQL process information
                "ps aux | grep '[m]ysqld' | wc -l",
                # Check service status
                "systemctl is-active mysql 2>/dev/null || systemctl is-active mysqld 2>/dev/null || echo 'unknown'",
                # Get listening ports
                "netstat -tlnp 2>/dev/null | grep mysqld || echo 'no_ports'",
                # Check if MySQL is accessible (basic connection test)
                "mysql -e 'SELECT 1' 2>/dev/null && echo 'accessible' || echo 'not_accessible'",
                # Get MySQL version if accessible
                "mysql -e 'SELECT VERSION()' 2>/dev/null || echo 'version_unavailable'",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=15.0
            )
            
            process_count = results[0]
            service_status = results[1].strip()
            ports_info = results[2]
            accessibility = results[3].strip()
            version_info = results[4]
            
            mysql_metrics = {
                "service": "mysql",
                "status": service_status,
                "process_count": int(process_count.strip()) if process_count.strip().isdigit() else 0,
                "accessible": accessibility == "accessible",
                "ports": self._parse_mysql_ports(ports_info),
                "version": self._parse_mysql_version(version_info),
            }
            
            # Get additional metrics if MySQL is accessible
            if accessibility == "accessible":
                stats_metrics = await self._get_mysql_stats(server)
                mysql_metrics.update(stats_metrics)
            
            return mysql_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect MySQL metrics: {e}")
            return {
                "service": "mysql",
                "status": "error",
                "error": str(e)
            }
    
    async def _collect_postgres_metrics(self, server: str) -> Optional[Dict[str, Any]]:
        """Collect PostgreSQL metrics."""
        try:
            # Check if PostgreSQL is running
            processes_result = await self.ssh_pool.execute(
                server,
                "pgrep -f 'postgres' | wc -l",
                timeout=5.0
            )
            
            process_count = int(processes_result.strip())
            if process_count == 0:
                return None
            
            commands = [
                # Get PostgreSQL process information
                "ps aux | grep '[p]ostgres' | wc -l",
                # Check service status
                "systemctl is-active postgresql 2>/dev/null || echo 'unknown'",
                # Get listening ports
                "netstat -tlnp 2>/dev/null | grep postgres || echo 'no_ports'",
                # Check if PostgreSQL is accessible
                "sudo -u postgres psql -c 'SELECT 1' 2>/dev/null && echo 'accessible' || echo 'not_accessible'",
                # Get PostgreSQL version if accessible
                "sudo -u postgres psql -c 'SELECT version()' 2>/dev/null || echo 'version_unavailable'",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=15.0
            )
            
            process_count = results[0]
            service_status = results[1].strip()
            ports_info = results[2]
            accessibility = results[3].strip()
            version_info = results[4]
            
            postgres_metrics = {
                "service": "postgresql",
                "status": service_status,
                "process_count": int(process_count.strip()) if process_count.strip().isdigit() else 0,
                "accessible": accessibility == "accessible",
                "ports": self._parse_postgres_ports(ports_info),
                "version": self._parse_postgres_version(version_info),
            }
            
            # Get additional metrics if PostgreSQL is accessible
            if accessibility == "accessible":
                stats_metrics = await self._get_postgres_stats(server)
                postgres_metrics.update(stats_metrics)
            
            return postgres_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect PostgreSQL metrics: {e}")
            return {
                "service": "postgresql",
                "status": "error",
                "error": str(e)
            }
    
    async def _collect_redis_metrics(self, server: str) -> Optional[Dict[str, Any]]:
        """Collect Redis metrics."""
        try:
            # Check if Redis is running
            processes_result = await self.ssh_pool.execute(
                server,
                "pgrep -f 'redis-server' | wc -l",
                timeout=5.0
            )
            
            process_count = int(processes_result.strip())
            if process_count == 0:
                return None
            
            commands = [
                # Get Redis process information
                "ps aux | grep '[r]edis-server' | wc -l",
                # Check service status
                "systemctl is-active redis 2>/dev/null || systemctl is-active redis-server 2>/dev/null || echo 'unknown'",
                # Get listening ports
                "netstat -tlnp 2>/dev/null | grep redis || echo 'no_ports'",
                # Check if Redis is accessible
                "redis-cli ping 2>/dev/null || echo 'not_accessible'",
                # Get Redis info if accessible
                "redis-cli info server 2>/dev/null || echo 'info_unavailable'",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=15.0
            )
            
            process_count = results[0]
            service_status = results[1].strip()
            ports_info = results[2]
            ping_result = results[3].strip()
            info_result = results[4]
            
            redis_metrics = {
                "service": "redis",
                "status": service_status,
                "process_count": int(process_count.strip()) if process_count.strip().isdigit() else 0,
                "accessible": ping_result == "PONG",
                "ports": self._parse_redis_ports(ports_info),
            }
            
            # Parse Redis info if available
            if info_result != "info_unavailable":
                info_metrics = self._parse_redis_info(info_result)
                redis_metrics.update(info_metrics)
            
            return redis_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect Redis metrics: {e}")
            return {
                "service": "redis",
                "status": "error",
                "error": str(e)
            }
    
    async def _get_mysql_stats(self, server: str) -> Dict[str, Any]:
        """Get MySQL performance statistics."""
        try:
            commands = [
                "mysql -e 'SHOW GLOBAL STATUS LIKE \"Connections\"' 2>/dev/null",
                "mysql -e 'SHOW GLOBAL STATUS LIKE \"Threads_connected\"' 2>/dev/null",
                "mysql -e 'SHOW GLOBAL STATUS LIKE \"Uptime\"' 2>/dev/null",
                "mysql -e 'SHOW GLOBAL STATUS LIKE \"Questions\"' 2>/dev/null",
                "mysql -e 'SHOW DATABASES' 2>/dev/null | wc -l",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=10.0
            )
            
            stats = {}
            
            # Parse status values
            for i, key in enumerate(["connections", "threads_connected", "uptime", "questions"]):
                if i < len(results):
                    value = self._parse_mysql_status_value(results[i])
                    if value is not None:
                        stats[key] = value
            
            # Parse database count
            if len(results) > 4:
                db_count = results[4].strip()
                if db_count.isdigit():
                    stats["database_count"] = int(db_count) - 1  # Subtract header line
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get MySQL stats: {e}")
            return {}
    
    async def _get_postgres_stats(self, server: str) -> Dict[str, Any]:
        """Get PostgreSQL performance statistics."""
        try:
            commands = [
                "sudo -u postgres psql -c 'SELECT count(*) FROM pg_stat_activity' 2>/dev/null",
                "sudo -u postgres psql -c 'SELECT count(*) FROM pg_database WHERE datistemplate = false' 2>/dev/null",
                "sudo -u postgres psql -c 'SELECT extract(epoch from now() - pg_postmaster_start_time())' 2>/dev/null",
            ]
            
            results = await self.ssh_pool.execute_batch(
                server, commands, timeout=10.0
            )
            
            stats = {}
            
            # Parse connection count
            if results[0]:
                conn_match = re.search(r'^\s*(\d+)\s*$', results[0].strip(), re.MULTILINE)
                if conn_match:
                    stats["active_connections"] = int(conn_match.group(1))
            
            # Parse database count
            if results[1]:
                db_match = re.search(r'^\s*(\d+)\s*$', results[1].strip(), re.MULTILINE)
                if db_match:
                    stats["database_count"] = int(db_match.group(1))
            
            # Parse uptime
            if results[2]:
                uptime_match = re.search(r'^\s*(\d+\.?\d*)\s*$', results[2].strip(), re.MULTILINE)
                if uptime_match:
                    stats["uptime_seconds"] = float(uptime_match.group(1))
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL stats: {e}")
            return {}
    
    def _parse_mysql_status_value(self, output: str) -> Optional[int]:
        """Parse MySQL status value from SHOW STATUS output."""
        # Format: Variable_name Value
        lines = output.strip().split('\n')
        if len(lines) >= 2:  # Skip header
            parts = lines[1].split('\t')
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    pass
        return None
    
    def _parse_mysql_version(self, output: str) -> Optional[str]:
        """Parse MySQL version from SELECT VERSION() output."""
        if output == "version_unavailable":
            return None
        
        # Look for version in output
        version_match = re.search(r'(\d+\.\d+\.\d+)', output)
        if version_match:
            return version_match.group(1)
        
        return None
    
    def _parse_postgres_version(self, output: str) -> Optional[str]:
        """Parse PostgreSQL version from SELECT version() output."""
        if output == "version_unavailable":
            return None
        
        # Look for PostgreSQL version in output
        version_match = re.search(r'PostgreSQL (\d+\.\d+)', output)
        if version_match:
            return version_match.group(1)
        
        return None
    
    def _parse_redis_info(self, output: str) -> Dict[str, Any]:
        """Parse Redis INFO output."""
        info = {}
        
        for line in output.split('\n'):
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Convert numeric values
                if key in ['redis_version', 'os', 'arch_bits', 'multiplexing_api']:
                    info[key] = value
                elif value.isdigit():
                    info[key] = int(value)
                elif '.' in value and value.replace('.', '').isdigit():
                    info[key] = float(value)
                else:
                    info[key] = value
        
        return info
    
    def _parse_mysql_ports(self, output: str) -> List[Dict[str, Any]]:
        """Parse MySQL listening ports from netstat output."""
        ports = []
        
        if output == "no_ports":
            return ports
        
        lines = output.strip().split('\n')
        for line in lines:
            match = re.search(r':(\d+)\s+.*?(\d+)/mysqld', line)
            if match:
                port = int(match.group(1))
                pid = int(match.group(2))
                
                ports.append({
                    "port": port,
                    "pid": pid,
                    "process": "mysqld",
                })
        
        return ports
    
    def _parse_postgres_ports(self, output: str) -> List[Dict[str, Any]]:
        """Parse PostgreSQL listening ports from netstat output."""
        ports = []
        
        if output == "no_ports":
            return ports
        
        lines = output.strip().split('\n')
        for line in lines:
            match = re.search(r':(\d+)\s+.*?(\d+)/postgres', line)
            if match:
                port = int(match.group(1))
                pid = int(match.group(2))
                
                ports.append({
                    "port": port,
                    "pid": pid,
                    "process": "postgres",
                })
        
        return ports
    
    def _parse_redis_ports(self, output: str) -> List[Dict[str, Any]]:
        """Parse Redis listening ports from netstat output."""
        ports = []
        
        if output == "no_ports":
            return ports
        
        lines = output.strip().split('\n')
        for line in lines:
            match = re.search(r':(\d+)\s+.*?(\d+)/redis', line)
            if match:
                port = int(match.group(1))
                pid = int(match.group(2))
                
                ports.append({
                    "port": port,
                    "pid": pid,
                    "process": "redis-server",
                })
        
        return ports