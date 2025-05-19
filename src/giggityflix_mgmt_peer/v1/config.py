# src/peer/config.py
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DriveConfig:
    """Configuration for drive-specific IO limits."""
    concurrent_io: int

    @classmethod
    def from_env(cls, drive: str, default: int = 2) -> 'DriveConfig':
        """Create from environment variables."""
        env_var = f"PEER_DRIVE_{drive.replace(':', '').replace('/', '_')}_IO"
        concurrent_io = int(os.environ.get(env_var, default))
        return cls(concurrent_io=concurrent_io)


@dataclass
class ProcessPoolConfig:
    """Configuration for process pool."""
    max_workers: int

    @classmethod
    def from_env(cls, default: int = None) -> 'ProcessPoolConfig':
        """Create from environment variables."""
        if default is None:
            default = os.cpu_count() or 4
        max_workers = int(os.environ.get("PEER_CPU_WORKERS", default))
        return cls(max_workers=max_workers)


@dataclass
class AppConfig:
    """Main application configuration."""
    db_path: str
    process_pool: ProcessPoolConfig
    drive_configs: Dict[str, DriveConfig] = field(default_factory=dict)
    default_io_limit: int = 2

    def get_drive_config(self, drive: str) -> DriveConfig:
        """Get configuration for a specific drive."""
        if drive not in self.drive_configs:
            self.drive_configs[drive] = DriveConfig.from_env(drive, self.default_io_limit)
        return self.drive_configs[drive]


def load_config() -> AppConfig:
    """Load application configuration from environment."""
    # Base configuration
    config = AppConfig(
        db_path=os.environ.get("PEER_DB_PATH", "peer.db"),
        process_pool=ProcessPoolConfig.from_env(),
        default_io_limit=int(os.environ.get("PEER_DEFAULT_IO_LIMIT", "2"))
    )

    # Pre-load common drive configurations
    if os.name == 'nt':  # Windows
        for drive in ['C:', 'D:', 'E:']:
            config.drive_configs[drive] = DriveConfig.from_env(drive, config.default_io_limit)
    else:  # Unix-like
        for mount in ['/', '/home', '/tmp']:
            if os.path.exists(mount):
                config.drive_configs[mount] = DriveConfig.from_env(
                    mount.replace('/', '_'), config.default_io_limit
                )

    return config
