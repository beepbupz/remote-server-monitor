"""Service monitoring widgets for webserver, database, and process metrics."""

from typing import Dict, Any, Optional, List
from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

from ...collectors.base import MetricData


class ServiceWidget(Static):
    """Base widget for service status display."""
    
    def __init__(self, title: str = "", service_type: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.service_type = service_type
        self.metric_data = None
    
    def update_metric(self, data: Optional[MetricData]) -> None:
        """Update the service metric display."""
        self.metric_data = data
        self.refresh()
    
    def get_status_color(self, status: str) -> str:
        """Get color for service status."""
        if status in ["active", "running", "accessible"]:
            return "green"
        elif status in ["inactive", "failed", "error"]:
            return "red"
        elif status in ["unknown", "not_accessible"]:
            return "yellow"
        else:
            return "dim"


class WebServerWidget(ServiceWidget):
    """Widget for displaying webserver status."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(title="Web Servers", service_type="webserver", *args, **kwargs)
    
    def render(self) -> Panel:
        """Render webserver metrics."""
        if not self.metric_data or self.metric_data.error:
            return Panel(
                Text("No webserver data available" if not self.metric_data else f"Error: {self.metric_data.error}", style="dim"),
                title="Web Servers",
                border_style="red"
            )
        
        services = []
        overall_status = "green"
        
        # Check Apache
        if "apache" in self.metric_data.data:
            apache_data = self.metric_data.data["apache"]
            apache_panel = self._render_apache(apache_data)
            services.append(apache_panel)
            
            if apache_data.get("status") not in ["active"]:
                overall_status = "yellow"
        
        # Check Nginx
        if "nginx" in self.metric_data.data:
            nginx_data = self.metric_data.data["nginx"]
            nginx_panel = self._render_nginx(nginx_data)
            services.append(nginx_panel)
            
            if nginx_data.get("status") not in ["active"]:
                overall_status = "yellow"
        
        if not services:
            return Panel(
                Text("No web servers detected", style="dim"),
                title="Web Servers",
                border_style="dim"
            )
        
        content = Group(*services) if len(services) > 1 else services[0]
        
        return Panel(
            content,
            title=f"Web Servers - {self.metric_data.server}",
            border_style=overall_status
        )
    
    def _render_apache(self, data: Dict[str, Any]) -> Text:
        """Render Apache status."""
        text = Text()
        text.append("Apache: ", style="bold")
        
        status = data.get("status", "unknown")
        status_color = self.get_status_color(status)
        text.append(f"{status}", style=status_color)
        
        process_count = data.get("process_count", 0)
        text.append(f" ({process_count} processes)")
        
        # Add port information
        ports = data.get("ports", [])
        if ports:
            port_list = [str(p["port"]) for p in ports]
            text.append(f"\n  Ports: {', '.join(port_list)}")
        
        # Add configuration status
        if "config_valid" in data:
            config_status = "✓" if data["config_valid"] else "✗"
            config_color = "green" if data["config_valid"] else "red"
            text.append(f"\n  Config: {config_status}", style=config_color)
        
        # Add metrics if available
        if "total_accesses" in data:
            text.append(f"\n  Requests: {data['total_accesses']:,}")
        if "busy_workers" in data:
            text.append(f"\n  Workers: {data['busy_workers']} busy, {data.get('idle_workers', 0)} idle")
        
        return text
    
    def _render_nginx(self, data: Dict[str, Any]) -> Text:
        """Render Nginx status."""
        text = Text()
        text.append("Nginx: ", style="bold")
        
        status = data.get("status", "unknown")
        status_color = self.get_status_color(status)
        text.append(f"{status}", style=status_color)
        
        process_count = data.get("process_count", 0)
        worker_count = data.get("worker_count", 0)
        text.append(f" ({process_count} processes, {worker_count} workers)")
        
        # Add port information
        ports = data.get("ports", [])
        if ports:
            port_list = [str(p["port"]) for p in ports]
            text.append(f"\n  Ports: {', '.join(port_list)}")
        
        # Add configuration status
        if "config_valid" in data:
            config_status = "✓" if data["config_valid"] else "✗"
            config_color = "green" if data["config_valid"] else "red"
            text.append(f"\n  Config: {config_status}", style=config_color)
        
        # Add metrics if available
        if "active_connections" in data:
            text.append(f"\n  Active Connections: {data['active_connections']}")
        if "requests" in data:
            text.append(f"\n  Total Requests: {data['requests']:,}")
        
        return text


class DatabaseWidget(ServiceWidget):
    """Widget for displaying database status."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(title="Databases", service_type="database", *args, **kwargs)
    
    def render(self) -> Panel:
        """Render database metrics."""
        if not self.metric_data or self.metric_data.error:
            return Panel(
                Text("No database data available" if not self.metric_data else f"Error: {self.metric_data.error}", style="dim"),
                title="Databases",
                border_style="red"
            )
        
        services = []
        overall_status = "green"
        
        # Check MySQL
        if "mysql" in self.metric_data.data:
            mysql_data = self.metric_data.data["mysql"]
            mysql_panel = self._render_mysql(mysql_data)
            services.append(mysql_panel)
            
            if not mysql_data.get("accessible", False):
                overall_status = "yellow"
        
        # Check PostgreSQL
        if "postgresql" in self.metric_data.data:
            postgres_data = self.metric_data.data["postgresql"]
            postgres_panel = self._render_postgres(postgres_data)
            services.append(postgres_panel)
            
            if not postgres_data.get("accessible", False):
                overall_status = "yellow"
        
        # Check Redis
        if "redis" in self.metric_data.data:
            redis_data = self.metric_data.data["redis"]
            redis_panel = self._render_redis(redis_data)
            services.append(redis_panel)
            
            if not redis_data.get("accessible", False):
                overall_status = "yellow"
        
        if not services:
            return Panel(
                Text("No databases detected", style="dim"),
                title="Databases",
                border_style="dim"
            )
        
        content = Group(*services) if len(services) > 1 else services[0]
        
        return Panel(
            content,
            title=f"Databases - {self.metric_data.server}",
            border_style=overall_status
        )
    
    def _render_mysql(self, data: Dict[str, Any]) -> Text:
        """Render MySQL status."""
        text = Text()
        text.append("MySQL: ", style="bold")
        
        status = data.get("status", "unknown")
        accessible = data.get("accessible", False)
        
        if accessible:
            text.append("accessible", style="green")
        else:
            text.append("not accessible", style="red")
        
        process_count = data.get("process_count", 0)
        text.append(f" ({process_count} processes)")
        
        # Add version if available
        if data.get("version"):
            text.append(f"\n  Version: {data['version']}")
        
        # Add connection info
        if "connections" in data:
            text.append(f"\n  Total Connections: {data['connections']:,}")
        if "threads_connected" in data:
            text.append(f"\n  Active Threads: {data['threads_connected']}")
        if "database_count" in data:
            text.append(f"\n  Databases: {data['database_count']}")
        
        return text
    
    def _render_postgres(self, data: Dict[str, Any]) -> Text:
        """Render PostgreSQL status."""
        text = Text()
        text.append("PostgreSQL: ", style="bold")
        
        accessible = data.get("accessible", False)
        
        if accessible:
            text.append("accessible", style="green")
        else:
            text.append("not accessible", style="red")
        
        process_count = data.get("process_count", 0)
        text.append(f" ({process_count} processes)")
        
        # Add version if available
        if data.get("version"):
            text.append(f"\n  Version: {data['version']}")
        
        # Add connection info
        if "active_connections" in data:
            text.append(f"\n  Active Connections: {data['active_connections']}")
        if "database_count" in data:
            text.append(f"\n  Databases: {data['database_count']}")
        if "uptime_seconds" in data:
            uptime_hours = data["uptime_seconds"] / 3600
            text.append(f"\n  Uptime: {uptime_hours:.1f} hours")
        
        return text
    
    def _render_redis(self, data: Dict[str, Any]) -> Text:
        """Render Redis status."""
        text = Text()
        text.append("Redis: ", style="bold")
        
        accessible = data.get("accessible", False)
        
        if accessible:
            text.append("accessible", style="green")
        else:
            text.append("not accessible", style="red")
        
        process_count = data.get("process_count", 0)
        text.append(f" ({process_count} processes)")
        
        # Add version if available
        if data.get("redis_version"):
            text.append(f"\n  Version: {data['redis_version']}")
        
        # Add info if available
        if "connected_clients" in data:
            text.append(f"\n  Connected Clients: {data['connected_clients']}")
        if "used_memory_human" in data:
            text.append(f"\n  Memory Usage: {data['used_memory_human']}")
        
        return text


class ProcessWidget(ServiceWidget):
    """Widget for displaying process status."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(title="Processes", service_type="process", *args, **kwargs)
    
    def render(self) -> Panel:
        """Render process metrics."""
        if not self.metric_data or self.metric_data.error:
            return Panel(
                Text("No process data available" if not self.metric_data else f"Error: {self.metric_data.error}", style="dim"),
                title="Processes",
                border_style="red"
            )
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Process", style="cyan", no_wrap=True)
        table.add_column("Count", justify="right")
        table.add_column("CPU%", justify="right")
        table.add_column("Mem%", justify="right")
        table.add_column("RSS", justify="right")
        
        overall_status = "green"
        has_processes = False
        
        for process_name, process_data in self.metric_data.data.items():
            if process_name == "error":
                continue
            
            count = process_data.get("count", 0)
            if count > 0:
                has_processes = True
                total_cpu = process_data.get("total_cpu", 0)
                total_memory = process_data.get("total_memory", 0)
                total_rss = process_data.get("total_rss", 0)
                
                # Format RSS in MB
                rss_mb = total_rss / 1024 if total_rss > 0 else 0
                
                # Color code based on resource usage
                if total_cpu > 50 or total_memory > 30:
                    cpu_style = "red"
                    overall_status = "yellow"
                elif total_cpu > 20 or total_memory > 10:
                    cpu_style = "yellow"
                else:
                    cpu_style = "green"
                
                table.add_row(
                    process_name.title(),
                    str(count),
                    f"[{cpu_style}]{total_cpu:.1f}[/{cpu_style}]",
                    f"[{cpu_style}]{total_memory:.1f}[/{cpu_style}]",
                    f"{rss_mb:.0f}MB"
                )
        
        if not has_processes:
            return Panel(
                Text("No monitored processes detected", style="dim"),
                title="Processes",
                border_style="dim"
            )
        
        return Panel(
            table,
            title=f"Processes - {self.metric_data.server}",
            border_style=overall_status
        )