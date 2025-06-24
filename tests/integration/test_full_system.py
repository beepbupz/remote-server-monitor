"""Integration tests for the full RSM system."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rsm.core.ssh_manager import SSHConnectionPool, SSHConfig
from rsm.collectors.system import SystemMetricsCollector
from rsm.collectors.base import CollectorRegistry
from rsm.utils.platform import Platform, PlatformManager


class TestFullSystemIntegration:
    """Test full system integration."""
    
    @pytest.fixture
    def mock_ssh_results(self):
        """Mock SSH command results for a Linux server."""
        return {
            "uname -s": "Linux",
            "cat /proc/stat": "cpu  1000 200 800 7000 100 50 25 0 0 0",
            "cat /proc/meminfo": """MemTotal:        8000000 kB
MemFree:         2000000 kB
MemAvailable:    3000000 kB
Buffers:          500000 kB
Cached:          1000000 kB""",
            "df -h": """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G   10G   10G  50% /""",
            "uptime": "12:34:56 up 1 day, load average: 0.50, 0.75, 1.00"
        }
    
    @pytest.fixture
    def setup_system(self, mock_ssh_results):
        """Set up a complete monitoring system."""
        # Create SSH pool
        ssh_pool = AsyncMock(spec=SSHConnectionPool)
        
        # Mock execute method to return appropriate results
        def mock_execute(server, command, timeout=None):
            return mock_ssh_results.get(command, "")
        
        def mock_execute_batch(server, commands, timeout=None):
            return [mock_ssh_results.get(cmd, "") for cmd in commands]
        
        ssh_pool.execute = AsyncMock(side_effect=mock_execute)
        ssh_pool.execute_batch = AsyncMock(side_effect=mock_execute_batch)
        ssh_pool.add_server = AsyncMock()
        ssh_pool.close = AsyncMock()
        
        # Create platform manager
        platform_manager = PlatformManager()
        
        # Create system collector
        system_collector = SystemMetricsCollector(ssh_pool, platform_manager)
        
        # Create registry and register collector
        registry = CollectorRegistry()
        registry.register(system_collector)
        registry.enable("system")
        
        return {
            "ssh_pool": ssh_pool,
            "platform_manager": platform_manager,
            "system_collector": system_collector,
            "registry": registry
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_metric_collection(self, setup_system):
        """Test end-to-end metric collection."""
        components = setup_system
        ssh_pool = components["ssh_pool"]
        registry = components["registry"]
        
        # Add a server
        config = SSHConfig("test.example.com", "testuser")
        await ssh_pool.add_server("test-server", config)
        
        # Collect metrics from all collectors
        all_metrics = await registry.get_all_metrics("test-server")
        
        assert "system" in all_metrics
        system_metrics = all_metrics["system"]
        
        assert system_metrics.server == "test-server"
        assert system_metrics.collector_name == "system"
        assert system_metrics.error is None
        
        # Check that all expected metrics are present
        data = system_metrics.data
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert "load" in data
        
        # Verify CPU metrics
        cpu = data["cpu"]
        assert "usage_percent" in cpu
        assert isinstance(cpu["usage_percent"], (int, float))
        assert 0 <= cpu["usage_percent"] <= 100
        
        # Verify memory metrics
        memory = data["memory"]
        assert "total_bytes" in memory
        assert "usage_percent" in memory
        assert isinstance(memory["total_bytes"], int)
        assert memory["total_bytes"] > 0
        
        # Verify disk metrics
        disk = data["disk"]
        assert isinstance(disk, list)
        if disk:
            assert "filesystem" in disk[0]
            assert "usage_percent" in disk[0]
        
        # Verify load metrics
        load = data["load"]
        assert "1min" in load
        assert "5min" in load
        assert "15min" in load
    
    @pytest.mark.asyncio
    async def test_multi_server_monitoring(self, setup_system, mock_ssh_results):
        """Test monitoring multiple servers simultaneously."""
        components = setup_system
        ssh_pool = components["ssh_pool"]
        registry = components["registry"]
        
        # Add multiple servers
        servers = ["server1", "server2", "server3"]
        for server in servers:
            config = SSHConfig(f"{server}.example.com", "testuser")
            await ssh_pool.add_server(server, config)
        
        # Collect metrics from all servers
        all_server_metrics = {}
        for server in servers:
            metrics = await registry.get_all_metrics(server)
            all_server_metrics[server] = metrics
        
        # Verify all servers have metrics
        assert len(all_server_metrics) == 3
        
        for server, metrics in all_server_metrics.items():
            assert "system" in metrics
            system_metrics = metrics["system"]
            assert system_metrics.server == server
            assert system_metrics.error is None
            assert "cpu" in system_metrics.data
    
    @pytest.mark.asyncio
    async def test_platform_detection_and_commands(self, setup_system):
        """Test platform detection and command selection."""
        components = setup_system
        ssh_pool = components["ssh_pool"]
        platform_manager = components["platform_manager"]
        
        # Test Linux detection
        platform = await platform_manager.detect_platform(ssh_pool, "linux-server")
        assert platform == Platform.LINUX
        
        commands = platform_manager.get_commands(platform)
        assert commands.cpu_usage_cmd() == "cat /proc/stat"
        assert commands.memory_info_cmd() == "cat /proc/meminfo"
    
    @pytest.mark.asyncio
    async def test_collector_lifecycle(self, setup_system):
        """Test collector start/stop lifecycle."""
        components = setup_system
        registry = components["registry"]
        system_collector = components["system_collector"]
        
        servers = ["test-server"]
        intervals = {"system": 0.1}  # Very fast for testing
        
        # Start collection
        await registry.start_all(servers, intervals)
        
        # Let it run briefly
        await asyncio.sleep(0.05)
        
        # Check that collection tasks are running
        assert len(system_collector._collection_tasks) == 1
        assert "test-server" in system_collector._collection_tasks
        
        # Stop collection
        await registry.stop_all()
        
        # Verify tasks are stopped
        assert len(system_collector._collection_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_ssh_failure(self, setup_system):
        """Test error handling when SSH commands fail."""
        components = setup_system
        ssh_pool = components["ssh_pool"]
        registry = components["registry"]
        
        # Make SSH operations fail
        ssh_pool.execute.side_effect = Exception("SSH connection failed")
        ssh_pool.execute_batch.side_effect = Exception("SSH connection failed")
        
        # Try to collect metrics
        metrics = await registry.get_all_metrics("failed-server")
        
        assert "system" in metrics
        system_metrics = metrics["system"]
        assert system_metrics.error is not None
        assert "SSH connection failed" in system_metrics.error
        assert system_metrics.data == {}
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, setup_system):
        """Test metric caching functionality."""
        components = setup_system
        ssh_pool = components["ssh_pool"]
        system_collector = components["system_collector"]
        
        # Set short cache duration for testing
        system_collector.cache_duration = 0.1
        
        # First collection
        metrics1 = await system_collector.get_metrics("test-server")
        call_count_1 = ssh_pool.execute_batch.call_count
        
        # Second collection (should use cache)
        metrics2 = await system_collector.get_metrics("test-server")
        call_count_2 = ssh_pool.execute_batch.call_count
        
        # Should not have made additional SSH calls due to caching
        assert call_count_2 == call_count_1
        assert metrics1.timestamp == metrics2.timestamp
        
        # Wait for cache to expire
        await asyncio.sleep(0.2)
        
        # Third collection (should refresh cache)
        metrics3 = await system_collector.get_metrics("test-server")
        call_count_3 = ssh_pool.execute_batch.call_count
        
        # Should have made new SSH calls
        assert call_count_3 > call_count_2
        assert metrics3.timestamp > metrics1.timestamp
    
    @pytest.mark.asyncio
    async def test_concurrent_collection(self, setup_system):
        """Test concurrent metric collection from multiple servers."""
        components = setup_system
        ssh_pool = components["ssh_pool"]
        registry = components["registry"]
        
        # Add multiple servers
        servers = [f"server{i}" for i in range(5)]
        for server in servers:
            config = SSHConfig(f"{server}.example.com", "testuser")
            await ssh_pool.add_server(server, config)
        
        # Collect metrics concurrently
        tasks = [
            registry.get_all_metrics(server)
            for server in servers
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all collections succeeded
        assert len(results) == 5
        for i, metrics in enumerate(results):
            assert "system" in metrics
            assert metrics["system"].server == f"server{i}"
            assert metrics["system"].error is None
    
    @pytest.mark.asyncio
    async def test_different_platforms(self, setup_system):
        """Test handling different platforms."""
        components = setup_system
        ssh_pool = components["ssh_pool"]
        platform_manager = components["platform_manager"]
        
        # Mock different platform responses
        platform_responses = {
            "linux-server": "Linux",
            "freebsd-server": "FreeBSD", 
            "macos-server": "Darwin",
            "unknown-server": "UnknownOS"
        }
        
        def mock_execute(server, command, timeout=None):
            if command == "uname -s":
                return platform_responses.get(server, "Linux")
            return "mock output"
        
        ssh_pool.execute = AsyncMock(side_effect=mock_execute)
        
        # Test each platform
        for server, expected_os in platform_responses.items():
            platform = await platform_manager.detect_platform(ssh_pool, server)
            
            if expected_os == "Linux":
                assert platform == Platform.LINUX
            elif expected_os == "FreeBSD":
                assert platform == Platform.FREEBSD
            elif expected_os == "Darwin":
                assert platform == Platform.MACOS
            else:
                assert platform == Platform.UNKNOWN