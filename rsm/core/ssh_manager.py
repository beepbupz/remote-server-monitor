"""SSH connection management with pooling and reconnection."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any
from pathlib import Path
import asyncssh
from asyncssh import SSHClient, SSHClientConnection


logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    """SSH connection configuration."""
    
    hostname: str
    username: str
    port: int = 22
    key_filename: Optional[str] = None
    password: Optional[str] = None
    known_hosts: Optional[str] = None
    connect_timeout: float = 30.0
    
    def to_asyncssh_options(self) -> Dict[str, Any]:
        """Convert to asyncssh connection options."""
        options = {
            "host": self.hostname,
            "port": self.port,
            "username": self.username,
            "connect_timeout": self.connect_timeout,
            "known_hosts": self.known_hosts,
        }
        
        if self.key_filename:
            options["client_keys"] = [self.key_filename]
        elif self.password:
            options["password"] = self.password
            
        return options


class SSHConnectionPool:
    """Manages SSH connections with pooling and automatic reconnection."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        self.connections: Dict[str, Optional[SSHClientConnection]] = {}
        self.configs: Dict[str, SSHConfig] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._closed = False
        
    async def add_server(self, name: str, config: SSHConfig) -> None:
        """Add a server to the pool."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
            
        self.configs[name] = config
        self.locks[name] = asyncio.Lock()
        self.connections[name] = None
        
        # Try to establish initial connection
        await self._connect(name)
        
    async def _connect(self, server: str) -> SSHClientConnection:
        """Establish SSH connection with retry logic."""
        if server not in self.configs:
            raise ValueError(f"Server '{server}' not configured")
            
        config = self.configs[server]
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                logger.info(f"Connecting to {server} ({config.hostname}:{config.port})")
                
                # Use asyncssh to create connection
                conn = await asyncssh.connect(**config.to_asyncssh_options())
                self.connections[server] = conn
                logger.info(f"Successfully connected to {server}")
                return conn
                
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(
                    f"Failed to connect to {server} (attempt {retry_count}/{self.max_retries}): {e}"
                )
                
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay * retry_count)
                    
        raise ConnectionError(
            f"Failed to connect to {server} after {self.max_retries} attempts: {last_error}"
        )
        
    async def execute(
        self, 
        server: str, 
        command: str, 
        timeout: Optional[float] = None
    ) -> str:
        """Execute command on specified server."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
            
        async with self.locks[server]:
            conn = self.connections.get(server)
            
            # Check if connection is alive, reconnect if needed
            if not conn or conn.is_closed():
                logger.info(f"Reconnecting to {server}")
                conn = await self._connect(server)
                
            try:
                # Execute command with timeout
                result = await asyncio.wait_for(
                    conn.run(command, check=False),
                    timeout=timeout
                )
                
                if result.returncode != 0:
                    logger.warning(
                        f"Command on {server} returned non-zero: {result.returncode}\n"
                        f"stderr: {result.stderr}"
                    )
                    
                return result.stdout
                
            except asyncio.TimeoutError:
                logger.error(f"Command timeout on {server}: {command}")
                raise
            except Exception as e:
                logger.error(f"Command execution error on {server}: {e}")
                # Mark connection as potentially broken
                self.connections[server] = None
                raise
                
    async def execute_batch(
        self, 
        server: str, 
        commands: list[str], 
        timeout: Optional[float] = None
    ) -> list[str]:
        """Execute multiple commands in a single SSH session."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
            
        # Join commands with semicolon for single execution
        combined_command = "; ".join(f"echo '___CMD_START___'; {cmd}" for cmd in commands)
        output = await self.execute(server, combined_command, timeout)
        
        # Split output by our marker
        results = []
        current_output = []
        
        for line in output.splitlines():
            if line == "___CMD_START___":
                if current_output:
                    results.append("\n".join(current_output))
                    current_output = []
            else:
                current_output.append(line)
                
        if current_output:
            results.append("\n".join(current_output))
            
        return results
        
    async def get_connection(self, server: str) -> SSHClientConnection:
        """Get a raw connection for advanced operations."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
            
        async with self.locks[server]:
            conn = self.connections.get(server)
            
            if not conn or conn.is_closed():
                conn = await self._connect(server)
                
            return conn
            
    async def close(self) -> None:
        """Close all connections in the pool."""
        self._closed = True
        
        close_tasks = []
        for server, conn in self.connections.items():
            if conn and not conn.is_closed():
                logger.info(f"Closing connection to {server}")
                close_tasks.append(conn.close())
                
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
            
        self.connections.clear()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    def get_server_status(self, server: str) -> str:
        """Get connection status for a server."""
        if server not in self.configs:
            return "not_configured"
            
        conn = self.connections.get(server)
        if not conn:
            return "disconnected"
        elif conn.is_closed():
            return "closed"
        else:
            return "connected"