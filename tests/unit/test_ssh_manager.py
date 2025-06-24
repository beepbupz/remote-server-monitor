"""Unit tests for SSH connection manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncssh
from asyncssh import SSHClient, SSHClientConnection

from rsm.core.ssh_manager import SSHConfig, SSHConnectionPool


class TestSSHConfig:
    """Test SSH configuration class."""
    
    def test_ssh_config_creation(self):
        """Test SSH config creation with defaults."""
        config = SSHConfig(
            hostname="test.example.com",
            username="testuser"
        )
        
        assert config.hostname == "test.example.com"
        assert config.username == "testuser"
        assert config.port == 22
        assert config.key_filename is None
        assert config.password is None
        assert config.connect_timeout == 30.0
    
    def test_ssh_config_custom_values(self):
        """Test SSH config with custom values."""
        config = SSHConfig(
            hostname="test.example.com",
            username="testuser",
            port=2222,
            key_filename="/path/to/key",
            password="secret",
            connect_timeout=60.0
        )
        
        assert config.port == 2222
        assert config.key_filename == "/path/to/key"
        assert config.password == "secret"
        assert config.connect_timeout == 60.0
    
    def test_to_asyncssh_options(self):
        """Test conversion to asyncssh options."""
        config = SSHConfig(
            hostname="test.example.com",
            username="testuser",
            port=2222,
            key_filename="/path/to/key",
            connect_timeout=60.0
        )
        
        options = config.to_asyncssh_options()
        
        expected = {
            "host": "test.example.com",
            "port": 2222,
            "username": "testuser",
            "connect_timeout": 60.0,
            "known_hosts": None,
            "client_keys": ["/path/to/key"]
        }
        
        assert options == expected
    
    def test_to_asyncssh_options_with_password(self):
        """Test conversion with password authentication."""
        config = SSHConfig(
            hostname="test.example.com",
            username="testuser",
            password="secret"
        )
        
        options = config.to_asyncssh_options()
        assert "password" in options
        assert options["password"] == "secret"
        assert "client_keys" not in options


class TestSSHConnectionPool:
    """Test SSH connection pool."""
    
    @pytest.fixture
    def pool(self):
        """Create SSH connection pool."""
        return SSHConnectionPool(max_retries=2, retry_delay=0.1)
    
    @pytest.fixture
    def mock_connection(self):
        """Create mock SSH connection."""
        conn = AsyncMock(spec=SSHClientConnection)
        conn.is_closed.return_value = False
        conn.close = AsyncMock()
        return conn
    
    def test_pool_initialization(self, pool):
        """Test pool initialization."""
        assert pool.max_retries == 2
        assert pool.retry_delay == 0.1
        assert len(pool.connections) == 0
        assert len(pool.configs) == 0
        assert not pool._closed
    
    @pytest.mark.asyncio
    async def test_add_server_success(self, pool, mock_connection):
        """Test successful server addition."""
        config = SSHConfig("test.example.com", "testuser")
        
        with patch('asyncssh.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_connection
            
            await pool.add_server("test-server", config)
            
            assert "test-server" in pool.configs
            assert "test-server" in pool.connections
            assert "test-server" in pool.locks
            assert pool.connections["test-server"] == mock_connection
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_server_connection_failure(self, pool):
        """Test server addition with connection failure."""
        config = SSHConfig("test.example.com", "testuser")
        
        with patch('asyncssh.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = ConnectionError("Connection failed")
            
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await pool.add_server("test-server", config)
            
            # Config should still be added even if connection fails
            assert "test-server" in pool.configs
    
    @pytest.mark.asyncio
    async def test_add_server_retry_logic(self, mock_connection):
        """Test connection retry logic."""
        # Create pool with 3 retries for this test
        pool = SSHConnectionPool(max_retries=3, retry_delay=0.01)
        config = SSHConfig("test.example.com", "testuser")
        
        with patch('asyncssh.connect', new_callable=AsyncMock) as mock_connect:
            # Fail twice, succeed on third attempt
            mock_connect.side_effect = [
                ConnectionError("First failure"),
                ConnectionError("Second failure"),
                mock_connection
            ]
            
            await pool.add_server("test-server", config)
            
            assert mock_connect.call_count == 3
            assert pool.connections["test-server"] == mock_connection
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, pool, mock_connection):
        """Test successful command execution."""
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.connections["test-server"] = mock_connection
        pool.locks["test-server"] = asyncio.Lock()
        
        # Mock command result
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "command output"
        mock_result.stderr = ""
        
        mock_connection.run = AsyncMock(return_value=mock_result)
        
        result = await pool.execute("test-server", "ls -la")
        
        assert result == "command output"
        mock_connection.run.assert_called_once_with("ls -la", check=False)
    
    @pytest.mark.asyncio
    async def test_execute_command_with_timeout(self, pool, mock_connection):
        """Test command execution with timeout."""
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.connections["test-server"] = mock_connection
        pool.locks["test-server"] = asyncio.Lock()
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "command output"
        
        mock_connection.run = AsyncMock(return_value=mock_result)
        
        result = await pool.execute("test-server", "ls -la", timeout=5.0)
        
        assert result == "command output"
    
    @pytest.mark.asyncio
    async def test_execute_command_timeout_error(self, pool, mock_connection):
        """Test command execution timeout."""
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.connections["test-server"] = mock_connection
        pool.locks["test-server"] = asyncio.Lock()
        
        # Mock timeout
        mock_connection.run = AsyncMock(side_effect=asyncio.TimeoutError)
        
        with pytest.raises(asyncio.TimeoutError):
            await pool.execute("test-server", "sleep 10", timeout=1.0)
    
    @pytest.mark.asyncio
    async def test_execute_command_reconnection(self, pool, mock_connection):
        """Test automatic reconnection on broken connection."""
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.locks["test-server"] = asyncio.Lock()
        
        # Initially no connection
        pool.connections["test-server"] = None
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "command output"
        
        with patch('asyncssh.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_connection
            mock_connection.run = AsyncMock(return_value=mock_result)
            
            result = await pool.execute("test-server", "ls -la")
            
            assert result == "command output"
            mock_connect.assert_called_once()
            assert pool.connections["test-server"] == mock_connection
    
    @pytest.mark.asyncio
    async def test_execute_batch_commands(self, pool, mock_connection):
        """Test batch command execution."""
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.connections["test-server"] = mock_connection
        pool.locks["test-server"] = asyncio.Lock()
        
        # Mock combined command output
        combined_output = (
            "___CMD_START___\n"
            "output1\n"
            "___CMD_START___\n"
            "output2\n"
            "output2 line2"
        )
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = combined_output
        
        mock_connection.run = AsyncMock(return_value=mock_result)
        
        commands = ["command1", "command2"]
        results = await pool.execute_batch("test-server", commands)
        
        assert len(results) == 2
        assert results[0] == "output1"
        assert results[1] == "output2\noutput2 line2"
    
    @pytest.mark.asyncio
    async def test_get_connection(self, pool, mock_connection):
        """Test getting raw connection."""
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.connections["test-server"] = mock_connection
        pool.locks["test-server"] = asyncio.Lock()
        
        conn = await pool.get_connection("test-server")
        assert conn == mock_connection
    
    @pytest.mark.asyncio
    async def test_close_pool(self, pool, mock_connection):
        """Test closing connection pool."""
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.connections["test-server"] = mock_connection
        pool.locks["test-server"] = asyncio.Lock()
        
        await pool.close()
        
        assert pool._closed
        mock_connection.close.assert_called_once()
        assert len(pool.connections) == 0
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_connection):
        """Test async context manager."""
        config = SSHConfig("test.example.com", "testuser")
        
        with patch('asyncssh.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_connection
            
            async with SSHConnectionPool() as pool:
                await pool.add_server("test-server", config)
                assert not pool._closed
            
            assert pool._closed
            mock_connection.close.assert_called_once()
    
    def test_get_server_status(self, pool, mock_connection):
        """Test server status checking."""
        # Not configured
        assert pool.get_server_status("unknown") == "not_configured"
        
        # Configured but disconnected
        config = SSHConfig("test.example.com", "testuser")
        pool.configs["test-server"] = config
        pool.connections["test-server"] = None
        assert pool.get_server_status("test-server") == "disconnected"
        
        # Connected but closed
        mock_connection.is_closed.return_value = True
        pool.connections["test-server"] = mock_connection
        assert pool.get_server_status("test-server") == "closed"
        
        # Connected and active
        mock_connection.is_closed.return_value = False
        assert pool.get_server_status("test-server") == "connected"
    
    @pytest.mark.asyncio
    async def test_closed_pool_operations(self, pool):
        """Test operations on closed pool."""
        await pool.close()
        
        with pytest.raises(RuntimeError, match="Connection pool is closed"):
            await pool.add_server("test", SSHConfig("test", "user"))
        
        with pytest.raises(RuntimeError, match="Connection pool is closed"):
            await pool.execute("test", "ls")
        
        with pytest.raises(RuntimeError, match="Connection pool is closed"):
            await pool.get_connection("test")