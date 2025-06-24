"""Configuration management for Remote Server Monitor."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
import tomli
import tomli_w

from .ssh_manager import SSHConfig


logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Configuration for a single server."""
    
    name: str
    hostname: str
    username: str
    port: int = 22
    key_filename: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_ssh_config(self) -> SSHConfig:
        """Convert to SSHConfig."""
        return SSHConfig(
            hostname=self.hostname,
            username=self.username,
            port=self.port,
            key_filename=self.key_filename,
        )


@dataclass
class CollectorConfig:
    """Configuration for a metric collector."""
    
    enabled: bool = True
    interval: float = 2.0
    
    
@dataclass
class ExportConfig:
    """Configuration for data export."""
    
    enabled: bool = False
    port: Optional[int] = None
    file: Optional[str] = None
    

@dataclass
class Config:
    """Main application configuration."""
    
    # General settings
    poll_interval: float = 2.0
    enable_compression: bool = True
    connection_timeout: float = 30.0
    retry_attempts: int = 3
    log_level: str = "INFO"
    
    # Servers
    servers: List[ServerConfig] = field(default_factory=list)
    
    # Collectors
    collectors: Dict[str, CollectorConfig] = field(default_factory=dict)
    
    # Plugins
    plugins_enabled: List[str] = field(default_factory=list)
    plugins_directory: str = "./plugins"
    
    # Export
    export_prometheus: ExportConfig = field(default_factory=ExportConfig)
    export_json: ExportConfig = field(default_factory=ExportConfig)
    
    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from TOML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "rb") as f:
            data = tomli.load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        config = cls()
        
        # General settings
        general = data.get("general", {})
        config.poll_interval = general.get("poll_interval", config.poll_interval)
        config.enable_compression = general.get("enable_compression", config.enable_compression)
        config.connection_timeout = general.get("connection_timeout", config.connection_timeout)
        config.retry_attempts = general.get("retry_attempts", config.retry_attempts)
        config.log_level = general.get("log_level", config.log_level)
        
        # Servers
        servers_data = data.get("servers", [])
        config.servers = [
            ServerConfig(
                name=s["name"],
                hostname=s["hostname"],
                username=s["username"],
                port=s.get("port", 22),
                key_filename=s.get("key_filename"),
                tags=s.get("tags", []),
            )
            for s in servers_data
        ]
        
        # Collectors
        collectors_data = data.get("collectors", {})
        config.collectors = {
            name: CollectorConfig(
                enabled=coll.get("enabled", True),
                interval=coll.get("interval", 2.0),
            )
            for name, coll in collectors_data.items()
        }
        
        # Plugins
        plugins = data.get("plugins", {})
        config.plugins_enabled = plugins.get("enabled", [])
        config.plugins_directory = plugins.get("directory", "./plugins")
        
        # Export
        export = data.get("export", {})
        if "prometheus" in export:
            prom = export["prometheus"]
            config.export_prometheus = ExportConfig(
                enabled=prom.get("enabled", False),
                port=prom.get("port"),
            )
        
        if "json" in export:
            json_export = export["json"]
            config.export_json = ExportConfig(
                enabled=json_export.get("enabled", False),
                file=json_export.get("file"),
            )
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "general": {
                "poll_interval": self.poll_interval,
                "enable_compression": self.enable_compression,
                "connection_timeout": self.connection_timeout,
                "retry_attempts": self.retry_attempts,
                "log_level": self.log_level,
            },
            "servers": [
                {
                    "name": s.name,
                    "hostname": s.hostname,
                    "username": s.username,
                    "port": s.port,
                    "key_filename": s.key_filename,
                    "tags": s.tags,
                }
                for s in self.servers
            ],
            "collectors": {
                name: {
                    "enabled": coll.enabled,
                    "interval": coll.interval,
                }
                for name, coll in self.collectors.items()
            },
            "plugins": {
                "enabled": self.plugins_enabled,
                "directory": self.plugins_directory,
            },
            "export": {
                "prometheus": {
                    "enabled": self.export_prometheus.enabled,
                    "port": self.export_prometheus.port,
                },
                "json": {
                    "enabled": self.export_json.enabled,
                    "file": self.export_json.file,
                },
            },
        }
    
    def save(self, config_path: Path) -> None:
        """Save configuration to TOML file."""
        with open(config_path, "wb") as f:
            tomli_w.dump(self.to_dict(), f)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Check servers
        if not self.servers:
            errors.append("No servers configured")
        
        server_names = set()
        for server in self.servers:
            if server.name in server_names:
                errors.append(f"Duplicate server name: {server.name}")
            server_names.add(server.name)
            
            if not server.hostname:
                errors.append(f"Server {server.name} has no hostname")
            if not server.username:
                errors.append(f"Server {server.name} has no username")
            if server.port <= 0 or server.port > 65535:
                errors.append(f"Server {server.name} has invalid port: {server.port}")
        
        # Check intervals
        if self.poll_interval <= 0:
            errors.append(f"Invalid poll_interval: {self.poll_interval}")
        
        for name, coll in self.collectors.items():
            if coll.interval <= 0:
                errors.append(f"Invalid interval for collector {name}: {coll.interval}")
        
        return errors
    
    def get_server_by_name(self, name: str) -> Optional[ServerConfig]:
        """Get server configuration by name."""
        for server in self.servers:
            if server.name == name:
                return server
        return None