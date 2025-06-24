"""Main Textual application for Remote Server Monitor."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, Label
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.timer import Timer
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

from ..core.config import Config
from ..core.ssh_manager import SSHConnectionPool, SSHConfig
from ..collectors.base import CollectorRegistry, MetricData
from ..collectors.system import SystemMetricsCollector
from ..collectors.webserver import WebServerCollector
from ..collectors.database import DatabaseCollector
from ..collectors.process import ProcessCollector
from ..utils.platform import PlatformManager
from .widgets import WebServerWidget, DatabaseWidget, ProcessWidget


logger = logging.getLogger(__name__)


class MetricWidget(Static):
    """Base widget for displaying metrics."""
    
    def __init__(self, title: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.metric_data = None
    
    def update_metric(self, data: Optional[MetricData]) -> None:
        """Update the metric display."""
        self.metric_data = data
        self.refresh()


class CPUWidget(MetricWidget):
    """Widget for displaying CPU metrics."""
    
    def render(self) -> Panel:
        """Render CPU metrics."""
        if not self.metric_data or self.metric_data.error:
            return Panel(
                Text("No data available" if not self.metric_data else f"Error: {self.metric_data.error}", style="dim"),
                title="CPU Usage",
                border_style="red"
            )
        
        cpu_data = self.metric_data.data.get("cpu", {})
        usage = cpu_data.get("usage_percent", 0)
        
        # Create progress bar
        progress = Progress(
            TextColumn("[bold blue]CPU Usage"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        
        task = progress.add_task("CPU", total=100)
        progress.update(task, completed=usage)
        
        # Determine color based on usage
        if usage > 80:
            border_style = "red"
        elif usage > 60:
            border_style = "yellow"
        else:
            border_style = "green"
        
        return Panel(
            progress,
            title=f"CPU Usage - {self.metric_data.server}",
            border_style=border_style
        )


class MemoryWidget(MetricWidget):
    """Widget for displaying memory metrics."""
    
    def render(self) -> Panel:
        """Render memory metrics."""
        if not self.metric_data or self.metric_data.error:
            return Panel(
                Text("No data available" if not self.metric_data else f"Error: {self.metric_data.error}", style="dim"),
                title="Memory Usage",
                border_style="red"
            )
        
        mem_data = self.metric_data.data.get("memory", {})
        usage = mem_data.get("usage_percent", 0)
        total = mem_data.get("total_bytes", 0)
        used = mem_data.get("used_bytes", 0)
        
        # Create progress bar
        progress = Progress(
            TextColumn("[bold blue]Memory"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        
        task = progress.add_task("Memory", total=100)
        progress.update(task, completed=usage)
        
        # Add size info
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        info = f"\n{used_gb:.1f} GB / {total_gb:.1f} GB"
        
        # Determine color
        if usage > 90:
            border_style = "red"
        elif usage > 75:
            border_style = "yellow"
        else:
            border_style = "green"
        
        content = Vertical(
            progress,
            Text(info, style="dim")
        )
        
        return Panel(
            content,
            title=f"Memory Usage - {self.metric_data.server}",
            border_style=border_style
        )


class DiskWidget(MetricWidget):
    """Widget for displaying disk metrics."""
    
    def render(self) -> Panel:
        """Render disk metrics."""
        if not self.metric_data or self.metric_data.error:
            return Panel(
                Text("No data available" if not self.metric_data else f"Error: {self.metric_data.error}", style="dim"),
                title="Disk Usage",
                border_style="red"
            )
        
        disk_data = self.metric_data.data.get("disk", [])
        
        if not disk_data:
            return Panel(
                Text("No disk information available", style="dim"),
                title="Disk Usage",
                border_style="yellow"
            )
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Mount", style="cyan", no_wrap=True)
        table.add_column("Size", justify="right")
        table.add_column("Used", justify="right")
        table.add_column("Free", justify="right")
        table.add_column("Use%", justify="right")
        
        for disk in disk_data[:5]:  # Show top 5 disks
            mount = disk.get("mount_point", "")
            size = disk.get("size", "")
            used = disk.get("used", "")
            avail = disk.get("available", "")
            usage = disk.get("usage_percent", 0)
            
            # Color code based on usage
            if usage > 90:
                usage_style = "red"
            elif usage > 75:
                usage_style = "yellow"
            else:
                usage_style = "green"
            
            table.add_row(
                mount,
                size,
                used,
                avail,
                f"[{usage_style}]{usage:.0f}%[/{usage_style}]"
            )
        
        return Panel(
            table,
            title=f"Disk Usage - {self.metric_data.server}",
            border_style="green"
        )


class LoadWidget(MetricWidget):
    """Widget for displaying system load."""
    
    def render(self) -> Panel:
        """Render load metrics."""
        if not self.metric_data or self.metric_data.error:
            return Panel(
                Text("No data available" if not self.metric_data else f"Error: {self.metric_data.error}", style="dim"),
                title="System Load",
                border_style="red"
            )
        
        load_data = self.metric_data.data.get("load", {})
        
        load_1 = load_data.get("1min", 0)
        load_5 = load_data.get("5min", 0)
        load_15 = load_data.get("15min", 0)
        
        content = Text()
        content.append("Load Average\n", style="bold")
        content.append(f"1 min:  {load_1:.2f}\n")
        content.append(f"5 min:  {load_5:.2f}\n")
        content.append(f"15 min: {load_15:.2f}\n")
        
        # Simple color coding (assumes 4 CPU cores as baseline)
        if load_1 > 8:
            border_style = "red"
        elif load_1 > 4:
            border_style = "yellow"
        else:
            border_style = "green"
        
        return Panel(
            content,
            title=f"System Load - {self.metric_data.server}",
            border_style=border_style
        )


class ServerDashboard(ScrollableContainer):
    """Dashboard for a single server."""
    
    def __init__(self, server_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_name = server_name
        self.cpu_widget = CPUWidget()
        self.memory_widget = MemoryWidget()
        self.disk_widget = DiskWidget()
        self.load_widget = LoadWidget()
        self.webserver_widget = WebServerWidget()
        self.database_widget = DatabaseWidget()
        self.process_widget = ProcessWidget()
    
    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        with Vertical():
            yield Label(f"Server: {self.server_name}", classes="server-title")
            
            # System metrics row
            with Horizontal(classes="metrics-row"):
                yield self.cpu_widget
                yield self.memory_widget
            with Horizontal(classes="metrics-row"):
                yield self.disk_widget
                yield self.load_widget
            
            # Service metrics row
            with Horizontal(classes="services-row"):
                yield self.webserver_widget
                yield self.database_widget
            
            # Process metrics row
            with Horizontal(classes="process-row"):
                yield self.process_widget
    
    def update_metrics(self, metrics: Dict[str, MetricData]) -> None:
        """Update all metric widgets."""
        # Update system metrics
        if "system" in metrics:
            system_data = metrics["system"]
            self.cpu_widget.update_metric(system_data)
            self.memory_widget.update_metric(system_data)
            self.disk_widget.update_metric(system_data)
            self.load_widget.update_metric(system_data)
        
        # Update service metrics
        if "webserver" in metrics:
            self.webserver_widget.update_metric(metrics["webserver"])
        
        if "database" in metrics:
            self.database_widget.update_metric(metrics["database"])
        
        if "process" in metrics:
            self.process_widget.update_metric(metrics["process"])


class RemoteServerMonitor(App):
    """Main TUI application for Remote Server Monitor."""
    
    CSS = """
    .server-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1;
    }
    
    .metrics-row {
        height: auto;
        margin: 1;
    }
    
    .services-row {
        height: auto;
        margin: 1;
    }
    
    .process-row {
        height: auto;
        margin: 1;
    }
    
    MetricWidget {
        width: 1fr;
        height: auto;
        margin: 0 1;
    }
    
    WebServerWidget, DatabaseWidget, ProcessWidget {
        width: 1fr;
        height: auto;
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]
    
    def __init__(self, config_file: str):
        super().__init__()
        self.config_path = Path(config_file)
        self.config: Optional[Config] = None
        self.ssh_pool: Optional[SSHConnectionPool] = None
        self.collector_registry: Optional[CollectorRegistry] = None
        self.platform_manager = PlatformManager()
        self.dashboards: Dict[str, ServerDashboard] = {}
        self.update_timer: Optional[Timer] = None
        
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)
        
        with TabbedContent(id="server-tabs"):
            # Tabs will be added dynamically after config is loaded
            pass
            
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize the application when mounted."""
        try:
            # Load configuration
            self.config = Config.from_file(self.config_path)
            
            # Validate configuration
            errors = self.config.validate()
            if errors:
                self.notify("\n".join(errors), severity="error")
                self.exit()
                return
            
            # Setup logging
            logging.basicConfig(
                level=getattr(logging, self.config.log_level),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Initialize SSH pool
            self.ssh_pool = SSHConnectionPool(
                max_retries=self.config.retry_attempts,
                retry_delay=2.0
            )
            
            # Initialize collectors
            self.collector_registry = CollectorRegistry()
            
            # Register system collector
            system_collector = SystemMetricsCollector(
                self.ssh_pool,
                self.platform_manager,
                cache_duration=self.config.poll_interval
            )
            self.collector_registry.register(system_collector)
            self.collector_registry.enable("system")
            
            # Register webserver collector
            webserver_collector = WebServerCollector(
                self.ssh_pool,
                self.platform_manager,
                cache_duration=self.config.poll_interval
            )
            self.collector_registry.register(webserver_collector)
            self.collector_registry.enable("webserver")
            
            # Register database collector
            database_collector = DatabaseCollector(
                self.ssh_pool,
                self.platform_manager,
                cache_duration=self.config.poll_interval
            )
            self.collector_registry.register(database_collector)
            self.collector_registry.enable("database")
            
            # Register process collector
            process_collector = ProcessCollector(
                self.ssh_pool,
                self.platform_manager,
                cache_duration=self.config.poll_interval
            )
            self.collector_registry.register(process_collector)
            self.collector_registry.enable("process")
            
            # Add servers to SSH pool and create tabs
            tabs_container = self.query_one("#server-tabs", TabbedContent)
            
            for server_config in self.config.servers:
                # Add to SSH pool
                await self.ssh_pool.add_server(
                    server_config.name,
                    server_config.to_ssh_config()
                )
                
                # Create dashboard
                dashboard = ServerDashboard(server_config.name)
                self.dashboards[server_config.name] = dashboard
                
                # Add tab using proper Textual API
                tabs_container.add_pane(TabPane(server_config.name, dashboard, id=f"tab-{server_config.name}"))
            
            # Start metric collection
            server_names = [s.name for s in self.config.servers]
            intervals = {
                name: conf.interval 
                for name, conf in self.config.collectors.items()
            }
            
            await self.collector_registry.start_all(server_names, intervals)
            
            # Start update timer
            self.update_timer = self.set_interval(
                self.config.poll_interval,
                self.update_all_metrics
            )
            
            self.notify("Remote Server Monitor started successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            self.notify(f"Initialization error: {e}", severity="error")
            self.exit()
    
    async def update_all_metrics(self) -> None:
        """Update metrics for all servers."""
        for server_config in self.config.servers:
            try:
                # Get metrics from all collectors
                metrics = await self.collector_registry.get_all_metrics(server_config.name)
                
                # Update dashboard
                if server_config.name in self.dashboards:
                    self.dashboards[server_config.name].update_metrics(metrics)
                    
            except Exception as e:
                logger.error(f"Failed to update metrics for {server_config.name}: {e}")
    
    async def action_refresh(self) -> None:
        """Refresh all metrics."""
        self.notify("Refreshing metrics...")
        await self.update_all_metrics()
    
    async def on_unmount(self) -> None:
        """Cleanup when application unmounts."""
        if self.update_timer:
            self.update_timer.stop()
        
        if self.collector_registry:
            await self.collector_registry.stop_all()
        
        if self.ssh_pool:
            await self.ssh_pool.close()