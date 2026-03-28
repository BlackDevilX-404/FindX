"""System identifier utility for tracking which system uploaded documents."""
import os
import socket
import platform
from typing import Optional


def get_system_id() -> str:
    """
    Generate a unique system identifier.
    Uses hostname as the primary identifier.
    Falls back to machine platform info if hostname is unavailable.
    
    Returns:
        str: A unique system identifier
    """
    try:
        # Use hostname as primary identifier
        hostname = socket.gethostname()
        if hostname:
            return hostname.lower()
    except Exception:
        pass
    
    try:
        # Fallback to machine name from platform
        machine = platform.machine()
        node = platform.node()
        if node:
            return node.lower()
        if machine:
            return machine.lower()
    except Exception:
        pass
    
    # Last resort: use environment username + machine
    username = os.getenv("USERNAME", "unknown")
    return f"{username}-{platform.system().lower()}"


def get_system_id_with_details() -> dict:
    """
    Get system identifier along with additional system information.
    
    Returns:
        dict: System information including id, hostname, platform, etc.
    """
    return {
        "system_id": get_system_id(),
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "machine": platform.machine(),
    }
