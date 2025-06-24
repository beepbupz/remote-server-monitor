"""Unit tests for metric collectors."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from rsm.collectors.base import MetricData, MetricCollector, CollectorRegistry
from rsm.collectors.system import SystemMetricsCollector
from rsm.utils.platform import Platform, PlatformManager


class TestMetricData:
    """Test MetricData class."""
    
    def test_metric_data_creation(self):
        """Test MetricData creation."""
        data = MetricData(
            server="test-server",
            collector_name="test-collector",
            data={"cpu": 50.0}
        )
        
        assert data.server == "test-server"
        assert data.collector_name == "test-collector"
        assert data.data == {"cpu": 50.0}
        assert data.error is None
        assert isinstance(data.timestamp, float)
    
    def test_metric_data_with_error(self):
        """Test MetricData with error."""
        data = MetricData(
            server="test-server",
            collector_name="test-collector",
            data={},
            error="Connection failed"
        )
        
        assert data.error == "Connection failed"
    
    def test_metric_data_age(self):
        """Test metric age calculation."""
        # Create data with specific timestamp
        past_time = time.time() - 10.0
        data = MetricData(
            server="test-server",
            collector_name="test-collector",
            data={},
            timestamp=past_time
        )
        
        assert data.age >= 10.0
    
    def test_metric_data_is_stale(self):
        """Test stale metric detection."""
        # Fresh data
        fresh_data = MetricData("server", "collector", {})
        assert not fresh_data.is_stale(10.0)
        
        # Stale data
        stale_data = MetricData(
            "server", "collector", {}, 
            timestamp=time.time() - 20.0
        )
        assert stale_data.is_stale(10.0)


class MockCollector(MetricCollector):
    """Mock collector for testing."""
    
    name = "mock"
    description = "Mock collector"
    default_interval = 1.0
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collect_called = False
        self.collect_data = {"mock_metric": 42}
        self.collect_error = None
    
    async def collect(self, server: str, platform: Platform) -> dict:
        """Mock collect method."""
        self.collect_called = True
        if self.collect_error:
            raise self.collect_error
        return self.collect_data.copy()


class TestMetricCollector:
    """Test base MetricCollector class."""
    
    @pytest.fixture
    def ssh_pool(self):
        """Create mock SSH pool."""
        return AsyncMock()
    
    @pytest.fixture
    def platform_manager(self):
        """Create mock platform manager."""
        manager = AsyncMock(spec=PlatformManager)
        manager.detect_platform = AsyncMock(return_value=Platform.LINUX)
        return manager
    
    @pytest.fixture
    def collector(self, ssh_pool, platform_manager):
        """Create mock collector."""
        return MockCollector(ssh_pool, platform_manager, cache_duration=1.0)
    
    def test_collector_initialization(self, ssh_pool, platform_manager):
        """Test collector initialization."""
        collector = MockCollector(ssh_pool, platform_manager)
        
        assert collector.ssh_pool == ssh_pool
        assert collector.platform_manager == platform_manager
        assert collector.cache_duration == 2.0  # default
        assert len(collector._cache) == 0
        assert len(collector._collection_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_get_metrics_fresh_collection(self, collector):
        """Test fresh metric collection."""
        result = await collector.get_metrics("test-server")
        
        assert collector.collect_called
        assert result.server == "test-server"
        assert result.collector_name == "mock"
        assert result.data == {"mock_metric": 42}
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_get_metrics_caching(self, collector):
        """Test metric caching."""
        # First call
        result1 = await collector.get_metrics("test-server")
        collector.collect_called = False  # Reset flag
        
        # Second call should use cache
        result2 = await collector.get_metrics("test-server")
        
        assert not collector.collect_called  # Should not call collect again
        assert result1.data == result2.data
        assert result1.timestamp == result2.timestamp
    
    @pytest.mark.asyncio
    async def test_get_metrics_force_refresh(self, collector):
        """Test forced metric refresh."""
        # First call
        await collector.get_metrics("test-server")
        collector.collect_called = False
        
        # Force refresh
        result = await collector.get_metrics("test-server", force_refresh=True)
        
        assert collector.collect_called
        assert result.data == {"mock_metric": 42}
    
    @pytest.mark.asyncio
    async def test_get_metrics_stale_cache(self, collector):
        """Test stale cache handling."""
        # Set very short cache duration
        collector.cache_duration = 0.1
        
        # First call
        await collector.get_metrics("test-server")
        collector.collect_called = False
        
        # Wait for cache to become stale
        await asyncio.sleep(0.2)
        
        # Second call should refresh
        await collector.get_metrics("test-server")
        assert collector.collect_called
    
    @pytest.mark.asyncio
    async def test_get_metrics_error_handling(self, collector):
        """Test error handling during collection."""
        collector.collect_error = Exception("Collection failed")
        
        result = await collector.get_metrics("test-server")
        
        assert result.error == "Collection failed"
        assert result.data == {}
    
    @pytest.mark.asyncio
    async def test_start_collection(self, collector):
        """Test starting collection tasks."""
        servers = ["server1", "server2"]
        
        # Start collection
        await collector.start_collection(servers, interval=0.1)
        
        assert len(collector._collection_tasks) == 2
        assert "server1" in collector._collection_tasks
        assert "server2" in collector._collection_tasks
        
        # Let it run briefly
        await asyncio.sleep(0.05)
        
        # Stop collection
        await collector.stop_collection()
        
        assert len(collector._collection_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_stop_collection(self, collector):
        """Test stopping collection tasks."""
        await collector.start_collection(["test-server"], interval=0.1)
        assert len(collector._collection_tasks) == 1
        
        await collector.stop_collection()
        
        assert len(collector._collection_tasks) == 0
        assert collector._stop_event.is_set()
    
    def test_get_cached_metrics_all(self, collector):
        """Test getting all cached metrics."""
        # Add some test data to cache
        data1 = MetricData("server1", "mock", {"value": 1})
        data2 = MetricData("server2", "mock", {"value": 2})
        collector._cache["server1"] = data1
        collector._cache["server2"] = data2
        
        cached = collector.get_cached_metrics()
        
        assert len(cached) == 2
        assert cached["server1"] == data1
        assert cached["server2"] == data2
    
    def test_get_cached_metrics_filtered(self, collector):
        """Test getting filtered cached metrics."""
        data1 = MetricData("server1", "mock", {"value": 1})
        data2 = MetricData("server2", "mock", {"value": 2})
        collector._cache["server1"] = data1
        collector._cache["server2"] = data2
        
        cached = collector.get_cached_metrics(["server1"])
        
        assert len(cached) == 1
        assert cached["server1"] == data1
        assert "server2" not in cached
    
    def test_clear_cache(self, collector):
        """Test cache clearing."""
        data1 = MetricData("server1", "mock", {"value": 1})
        data2 = MetricData("server2", "mock", {"value": 2})
        collector._cache["server1"] = data1
        collector._cache["server2"] = data2
        
        # Clear specific server
        collector.clear_cache("server1")
        assert "server1" not in collector._cache
        assert "server2" in collector._cache
        
        # Clear all
        collector.clear_cache()
        assert len(collector._cache) == 0


class TestSystemMetricsCollector:
    """Test SystemMetricsCollector."""
    
    @pytest.fixture
    def ssh_pool(self):
        """Create mock SSH pool."""
        pool = AsyncMock()
        pool.execute_batch = AsyncMock()
        return pool
    
    @pytest.fixture
    def platform_manager(self):
        """Create mock platform manager."""
        manager = AsyncMock(spec=PlatformManager)
        manager.get_server_commands = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_commands(self):
        """Create mock platform commands."""
        commands = MagicMock()
        commands.cpu_usage_cmd.return_value = "cat /proc/stat"
        commands.memory_info_cmd.return_value = "cat /proc/meminfo"
        commands.disk_usage_cmd.return_value = "df -h"
        commands.uptime_cmd.return_value = "uptime"
        return commands
    
    @pytest.fixture
    def collector(self, ssh_pool, platform_manager):
        """Create system metrics collector."""
        return SystemMetricsCollector(ssh_pool, platform_manager)
    
    def test_collector_metadata(self, collector):
        """Test collector metadata."""
        assert collector.name == "system"
        assert "system metrics" in collector.description.lower()
        assert collector.default_interval == 2.0
    
    @pytest.mark.asyncio
    async def test_collect_linux_metrics(self, collector, mock_commands):
        """Test collecting Linux system metrics."""
        collector.platform_manager.get_server_commands.return_value = mock_commands
        
        # Mock command outputs
        cpu_output = "cpu  1234 0 5678 9012 0 0 0 0 0 0"
        memory_output = """MemTotal:        8000000 kB
MemFree:         2000000 kB
MemAvailable:    3000000 kB
Buffers:          500000 kB
Cached:          1000000 kB"""
        disk_output = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G   10G   10G  50% /"""
        uptime_output = "12:34:56 up 1 day, 2:34, 1 user, load average: 0.50, 0.75, 1.00"
        
        collector.ssh_pool.execute_batch.return_value = [
            cpu_output, memory_output, disk_output, uptime_output
        ]
        
        result = await collector.collect("test-server", Platform.LINUX)
        
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "load" in result
        
        # Check CPU parsing
        assert "usage_percent" in result["cpu"]
        assert isinstance(result["cpu"]["usage_percent"], float)
        
        # Check memory parsing
        assert "total_bytes" in result["memory"]
        assert "usage_percent" in result["memory"]
        
        # Check disk parsing
        assert isinstance(result["disk"], list)
        
        # Check load parsing
        assert "1min" in result["load"]
        assert "5min" in result["load"]
        assert "15min" in result["load"]
    
    def test_parse_linux_cpu(self, collector):
        """Test Linux CPU parsing."""
        output = "cpu  1000 200 800 7000 0 0 0 0 0 0"
        
        result = collector._parse_cpu(output, Platform.LINUX)
        
        assert "usage_percent" in result
        assert "user" in result
        assert "system" in result
        assert "idle" in result
        
        # Total = 1000+200+800+7000 = 9000
        # Used = 1000+200+800 = 2000
        # Usage = 2000/9000 * 100 = 22.22%
        expected_usage = round(2000 / 9000 * 100, 2)
        assert result["usage_percent"] == expected_usage
    
    def test_parse_linux_memory(self, collector):
        """Test Linux memory parsing."""
        output = """MemTotal:        8000000 kB
MemFree:         2000000 kB
MemAvailable:    3000000 kB
Buffers:          500000 kB
Cached:          1000000 kB
SwapTotal:       2000000 kB
SwapFree:        1500000 kB"""
        
        result = collector._parse_memory(output, Platform.LINUX)
        
        assert result["total_bytes"] == 8000000 * 1024
        assert result["available_bytes"] == 3000000 * 1024
        assert result["used_bytes"] == (8000000 - 3000000) * 1024
        assert result["buffers_bytes"] == 500000 * 1024
        assert result["cached_bytes"] == 1000000 * 1024
        assert result["swap_total_bytes"] == 2000000 * 1024
        
        # Usage percentage
        expected_usage = round((8000000 - 3000000) / 8000000 * 100, 2)
        assert result["usage_percent"] == expected_usage
    
    def test_parse_bsd_cpu(self, collector):
        """Test BSD CPU parsing."""
        output = """
        last pid: 12345;  load averages:  0.50,  0.75,  1.00
        CPU: 25.0% user,  0.0% nice, 10.0% system,  5.0% interrupt, 60.0% idle
        """
        
        result = collector._parse_cpu(output, Platform.FREEBSD)
        
        assert "usage_percent" in result
        assert result["usage_percent"] == 40.0  # 100 - 60 (idle)
        assert result["user"] == 25.0
        assert result["idle"] == 60.0
    
    def test_parse_macos_cpu(self, collector):
        """Test macOS CPU parsing."""
        output = """
        Processes: 234 total, 2 running, 232 sleeping, 1234 threads
        CPU usage: 15.5% user, 5.2% sys, 79.3% idle
        """
        
        result = collector._parse_cpu(output, Platform.MACOS)
        
        assert "usage_percent" in result
        assert result["usage_percent"] == 20.7  # 100 - 79.3 (idle)
        assert result["user"] == 15.5
        assert result["system"] == 5.2
        assert result["idle"] == 79.3
    
    def test_parse_disk_usage(self, collector):
        """Test disk usage parsing."""
        output = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G   10G   10G  50% /
/dev/sda2       100G   25G   75G  25% /home
tmpfs           4.0G     0  4.0G   0% /tmp"""
        
        result = collector._parse_disk(output)
        
        assert len(result) == 2  # Only /dev/sda1 and /dev/sda2, tmpfs is filtered out
        
        disk1 = result[0]
        assert disk1["filesystem"] == "/dev/sda1"
        assert disk1["mount_point"] == "/"
        assert disk1["usage_percent"] == 50.0
        
        disk2 = result[1]
        assert disk2["filesystem"] == "/dev/sda2"
        assert disk2["mount_point"] == "/home"
        assert disk2["usage_percent"] == 25.0
    
    def test_parse_load_averages(self, collector):
        """Test load average parsing."""
        test_cases = [
            ("12:34:56 up 1 day, 2:34, 1 user, load average: 0.50, 0.75, 1.00", (0.5, 0.75, 1.0)),
            ("12:34:56 up 1 day, 2:34, 1 user, load averages: 2.50, 1.75, 1.25", (2.5, 1.75, 1.25)),
            ("load average: 0.1, 0.2, 0.3", (0.1, 0.2, 0.3)),
        ]
        
        for output, expected in test_cases:
            result = collector._parse_load(output)
            
            assert result["1min"] == expected[0]
            assert result["5min"] == expected[1]
            assert result["15min"] == expected[2]
    
    def test_parse_cpu_error_handling(self, collector):
        """Test CPU parsing error handling."""
        invalid_output = "invalid cpu output"
        
        result = collector._parse_cpu(invalid_output, Platform.LINUX)
        
        assert result["usage_percent"] == 0.0
        assert "error" in result
    
    def test_parse_memory_error_handling(self, collector):
        """Test memory parsing error handling."""
        invalid_output = "invalid memory output"
        
        result = collector._parse_memory(invalid_output, Platform.LINUX)
        
        assert "error" in result


class TestCollectorRegistry:
    """Test CollectorRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create collector registry."""
        return CollectorRegistry()
    
    @pytest.fixture
    def mock_collector1(self):
        """Create first mock collector."""
        collector = MagicMock(spec=MetricCollector)
        collector.name = "collector1"
        collector.default_interval = 1.0
        collector.start_collection = AsyncMock()
        collector.stop_collection = AsyncMock()
        collector.get_metrics = AsyncMock()
        return collector
    
    @pytest.fixture
    def mock_collector2(self):
        """Create second mock collector."""
        collector = MagicMock(spec=MetricCollector)
        collector.name = "collector2"
        collector.default_interval = 2.0
        collector.start_collection = AsyncMock()
        collector.stop_collection = AsyncMock()
        collector.get_metrics = AsyncMock()
        return collector
    
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry._collectors) == 0
        assert len(registry._enabled_collectors) == 0
    
    def test_register_collector(self, registry, mock_collector1):
        """Test collector registration."""
        registry.register(mock_collector1)
        
        assert "collector1" in registry._collectors
        assert registry._collectors["collector1"] == mock_collector1
    
    def test_enable_disable_collector(self, registry, mock_collector1):
        """Test enabling and disabling collectors."""
        registry.register(mock_collector1)
        
        # Enable
        registry.enable("collector1")
        assert "collector1" in registry._enabled_collectors
        
        # Disable
        registry.disable("collector1")
        assert "collector1" not in registry._enabled_collectors
    
    def test_enable_nonexistent_collector(self, registry):
        """Test enabling non-existent collector."""
        registry.enable("nonexistent")
        assert "nonexistent" not in registry._enabled_collectors
    
    def test_get_collector(self, registry, mock_collector1):
        """Test getting collector by name."""
        registry.register(mock_collector1)
        
        collector = registry.get_collector("collector1")
        assert collector == mock_collector1
        
        # Non-existent collector
        assert registry.get_collector("nonexistent") is None
    
    def test_get_enabled_collectors(self, registry, mock_collector1, mock_collector2):
        """Test getting enabled collectors."""
        registry.register(mock_collector1)
        registry.register(mock_collector2)
        registry.enable("collector1")
        
        enabled = registry.get_enabled_collectors()
        
        assert len(enabled) == 1
        assert enabled[0] == mock_collector1
    
    @pytest.mark.asyncio
    async def test_start_all_collectors(self, registry, mock_collector1, mock_collector2):
        """Test starting all enabled collectors."""
        registry.register(mock_collector1)
        registry.register(mock_collector2)
        registry.enable("collector1")
        registry.enable("collector2")
        
        servers = ["server1", "server2"]
        intervals = {"collector1": 5.0}  # collector2 should use default
        
        await registry.start_all(servers, intervals)
        
        mock_collector1.start_collection.assert_called_once_with(servers, 5.0)
        mock_collector2.start_collection.assert_called_once_with(servers, 2.0)
    
    @pytest.mark.asyncio
    async def test_stop_all_collectors(self, registry, mock_collector1, mock_collector2):
        """Test stopping all collectors."""
        registry.register(mock_collector1)
        registry.register(mock_collector2)
        
        await registry.stop_all()
        
        mock_collector1.stop_collection.assert_called_once()
        mock_collector2.stop_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_metrics(self, registry, mock_collector1, mock_collector2):
        """Test getting metrics from all enabled collectors."""
        registry.register(mock_collector1)
        registry.register(mock_collector2)
        registry.enable("collector1")
        registry.enable("collector2")
        
        # Mock return values
        metric1 = MetricData("server1", "collector1", {"value": 1})
        metric2 = MetricData("server1", "collector2", {"value": 2})
        mock_collector1.get_metrics.return_value = metric1
        mock_collector2.get_metrics.return_value = metric2
        
        result = await registry.get_all_metrics("server1")
        
        assert len(result) == 2
        assert result["collector1"] == metric1
        assert result["collector2"] == metric2
    
    @pytest.mark.asyncio
    async def test_get_all_metrics_with_error(self, registry, mock_collector1):
        """Test getting metrics with collector error."""
        registry.register(mock_collector1)
        registry.enable("collector1")
        
        # Mock collector error
        mock_collector1.get_metrics.side_effect = Exception("Collector failed")
        
        result = await registry.get_all_metrics("server1")
        
        assert len(result) == 1
        assert result["collector1"].error == "Collector failed"
        assert result["collector1"].data == {}