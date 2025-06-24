"""Base metric collector architecture."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from ..core.ssh_manager import SSHConnectionPool
from ..utils.platform import Platform, PlatformManager


logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Container for metric data with timestamp."""
    
    server: str
    collector_name: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None
    
    @property
    def age(self) -> float:
        """Get age of metric in seconds."""
        return time.time() - self.timestamp
    
    def is_stale(self, max_age: float) -> bool:
        """Check if metric is stale."""
        return self.age > max_age


class MetricCollector(ABC):
    """Base class for all metric collectors."""
    
    # Collector metadata
    name: str = "base"
    description: str = "Base metric collector"
    default_interval: float = 2.0
    
    def __init__(
        self, 
        ssh_pool: SSHConnectionPool,
        platform_manager: Optional[PlatformManager] = None,
        cache_duration: float = 2.0
    ):
        self.ssh_pool = ssh_pool
        self.platform_manager = platform_manager or PlatformManager()
        self.cache_duration = cache_duration
        self._cache: Dict[str, MetricData] = {}
        self._collection_tasks: Dict[str, asyncio.Task] = {}
        self._stop_event = asyncio.Event()
        
    @abstractmethod
    async def collect(self, server: str, platform: Platform) -> Dict[str, Any]:
        """
        Collect metrics from a server.
        
        Args:
            server: Server name
            platform: Server platform
            
        Returns:
            Dictionary of collected metrics
        """
        pass
    
    async def get_metrics(self, server: str, force_refresh: bool = False) -> MetricData:
        """
        Get metrics for a server with caching.
        
        Args:
            server: Server name
            force_refresh: Force collection even if cache is valid
            
        Returns:
            MetricData object with metrics or error
        """
        # Check cache first
        if not force_refresh and server in self._cache:
            cached = self._cache[server]
            if not cached.is_stale(self.cache_duration):
                logger.debug(f"{self.name}: Using cached metrics for {server}")
                return cached
        
        # Collect fresh metrics
        try:
            platform = await self.platform_manager.detect_platform(self.ssh_pool, server)
            data = await self.collect(server, platform)
            
            metric_data = MetricData(
                server=server,
                collector_name=self.name,
                data=data,
            )
            self._cache[server] = metric_data
            
            logger.debug(f"{self.name}: Collected fresh metrics for {server}")
            return metric_data
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to collect metrics for {server}: {e}")
            
            # Return error metric data
            metric_data = MetricData(
                server=server,
                collector_name=self.name,
                data={},
                error=str(e),
            )
            self._cache[server] = metric_data
            return metric_data
    
    async def start_collection(self, servers: List[str], interval: float) -> None:
        """
        Start periodic collection for multiple servers.
        
        Args:
            servers: List of server names
            interval: Collection interval in seconds
        """
        for server in servers:
            if server not in self._collection_tasks:
                task = asyncio.create_task(
                    self._collection_loop(server, interval),
                    name=f"{self.name}-{server}"
                )
                self._collection_tasks[server] = task
                logger.info(f"{self.name}: Started collection for {server}")
    
    async def stop_collection(self) -> None:
        """Stop all collection tasks."""
        self._stop_event.set()
        
        # Cancel all tasks
        for task in self._collection_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._collection_tasks:
            await asyncio.gather(
                *self._collection_tasks.values(),
                return_exceptions=True
            )
        
        self._collection_tasks.clear()
        logger.info(f"{self.name}: Stopped all collection tasks")
    
    async def _collection_loop(self, server: str, interval: float) -> None:
        """Collection loop for a single server."""
        logger.info(f"{self.name}: Starting collection loop for {server} (interval={interval}s)")
        
        while not self._stop_event.is_set():
            try:
                # Collect metrics
                await self.get_metrics(server, force_refresh=True)
                
                # Wait for next collection
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info(f"{self.name}: Collection cancelled for {server}")
                break
            except Exception as e:
                logger.error(f"{self.name}: Collection error for {server}: {e}")
                await asyncio.sleep(interval)
    
    def get_cached_metrics(self, servers: Optional[List[str]] = None) -> Dict[str, MetricData]:
        """
        Get all cached metrics.
        
        Args:
            servers: Optional list of servers to filter by
            
        Returns:
            Dictionary of server -> MetricData
        """
        if servers is None:
            return self._cache.copy()
        
        return {
            server: data 
            for server, data in self._cache.items() 
            if server in servers
        }
    
    def clear_cache(self, server: Optional[str] = None) -> None:
        """Clear cache for a server or all servers."""
        if server:
            self._cache.pop(server, None)
        else:
            self._cache.clear()


class CollectorRegistry:
    """Registry for managing multiple metric collectors."""
    
    def __init__(self):
        self._collectors: Dict[str, MetricCollector] = {}
        self._enabled_collectors: Set[str] = set()
        
    def register(self, collector: MetricCollector) -> None:
        """Register a collector."""
        self._collectors[collector.name] = collector
        logger.info(f"Registered collector: {collector.name}")
    
    def enable(self, name: str) -> None:
        """Enable a collector."""
        if name in self._collectors:
            self._enabled_collectors.add(name)
            logger.info(f"Enabled collector: {name}")
        else:
            logger.warning(f"Collector not found: {name}")
    
    def disable(self, name: str) -> None:
        """Disable a collector."""
        self._enabled_collectors.discard(name)
        logger.info(f"Disabled collector: {name}")
    
    def get_collector(self, name: str) -> Optional[MetricCollector]:
        """Get a collector by name."""
        return self._collectors.get(name)
    
    def get_enabled_collectors(self) -> List[MetricCollector]:
        """Get all enabled collectors."""
        return [
            self._collectors[name]
            for name in self._enabled_collectors
            if name in self._collectors
        ]
    
    async def start_all(self, servers: List[str], intervals: Dict[str, float]) -> None:
        """Start collection for all enabled collectors."""
        tasks = []
        
        for collector in self.get_enabled_collectors():
            interval = intervals.get(collector.name, collector.default_interval)
            tasks.append(collector.start_collection(servers, interval))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def stop_all(self) -> None:
        """Stop all collectors."""
        tasks = [
            collector.stop_collection()
            for collector in self._collectors.values()
        ]
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def get_all_metrics(self, server: str) -> Dict[str, MetricData]:
        """Get metrics from all enabled collectors for a server."""
        results = {}
        
        tasks = []
        collectors = []
        
        for collector in self.get_enabled_collectors():
            tasks.append(collector.get_metrics(server))
            collectors.append(collector.name)
        
        if tasks:
            metrics = await asyncio.gather(*tasks, return_exceptions=True)
            
            for name, metric in zip(collectors, metrics):
                if isinstance(metric, Exception):
                    logger.error(f"Failed to get metrics from {name}: {metric}")
                    results[name] = MetricData(
                        server=server,
                        collector_name=name,
                        data={},
                        error=str(metric)
                    )
                else:
                    results[name] = metric
        
        return results