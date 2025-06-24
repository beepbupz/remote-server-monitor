"""Entry point for Remote Server Monitor."""

import asyncio
import sys
from pathlib import Path
import click
from . import __version__


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config.toml",
    help="Path to configuration file",
)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version and exit",
)
def main(config: Path, version: bool) -> None:
    """Remote Server Monitor - Terminal-based SSH monitoring tool."""
    if version:
        click.echo(f"Remote Server Monitor v{__version__}")
        sys.exit(0)
    
    # Import here to avoid circular imports and speed up CLI
    from .ui.app import RemoteServerMonitor
    
    try:
        app = RemoteServerMonitor(config_file=str(config))
        app.run()
    except KeyboardInterrupt:
        click.echo("\nExiting...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()