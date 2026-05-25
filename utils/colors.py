#!/usr/bin/env python3
"""
Color utilities for enhanced UX in Slack DM Thread Cleaner
"""

import sys
from enum import Enum
from typing import Optional


class Color(Enum):
    """ANSI color codes for terminal output."""
    # Reset
    RESET = '\033[0m'
    
    # Basic colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    STRIKETHROUGH = '\033[9m'


class ColoredOutput:
    """Utility class for colored terminal output."""
    
    def __init__(self, enable_colors: bool = True):
        # Disable colors on Windows without colorama or if explicitly disabled
        self.colors_enabled = enable_colors and self._supports_color()
        
    def _supports_color(self) -> bool:
        """Check if terminal supports colors."""
        # Check if stdout is a TTY
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
            
        # Check environment variables
        term = sys.platform
        if term == 'win32':
            # Windows may need additional setup
            return True  # Assume it works, can be disabled via parameter
            
        return True
        
    def colorize(self, text: str, color: Color, bold: bool = False) -> str:
        """Apply color to text."""
        if not self.colors_enabled:
            return text
            
        color_code = color.value
        if bold:
            color_code = Color.BOLD.value + color_code
            
        return f"{color_code}{text}{Color.RESET.value}"
        
    def success(self, text: str, bold: bool = False) -> str:
        """Green text for success messages."""
        return self.colorize(text, Color.BRIGHT_GREEN, bold)
        
    def error(self, text: str, bold: bool = False) -> str:
        """Red text for error messages."""
        return self.colorize(text, Color.BRIGHT_RED, bold)
        
    def warning(self, text: str, bold: bool = False) -> str:
        """Yellow text for warning messages."""
        return self.colorize(text, Color.BRIGHT_YELLOW, bold)
        
    def info(self, text: str, bold: bool = False) -> str:
        """Blue text for info messages."""
        return self.colorize(text, Color.BRIGHT_BLUE, bold)
        
    def danger(self, text: str, bold: bool = True) -> str:
        """Bright red bold text for dangerous operations."""
        return self.colorize(text, Color.BRIGHT_RED, True)
        
    def highlight(self, text: str) -> str:
        """Cyan text for highlighting important info."""
        return self.colorize(text, Color.BRIGHT_CYAN, False)
        
    def dim(self, text: str) -> str:
        """Dim text for less important info."""
        return self.colorize(text, Color.BRIGHT_BLACK, False)
        
    def bold(self, text: str) -> str:
        """Bold text."""
        if not self.colors_enabled:
            return text
        return f"{Color.BOLD.value}{text}{Color.RESET.value}"


# Global instance for easy access
colored = ColoredOutput()


def print_success(message: str):
    """Print a success message in green."""
    print(colored.success(f"✅ {message}"))
    

def print_error(message: str):
    """Print an error message in red."""
    print(colored.error(f"❌ {message}"))
    

def print_warning(message: str):
    """Print a warning message in yellow."""
    print(colored.warning(f"⚠️  {message}"))
    

def print_info(message: str):
    """Print an info message in blue."""
    print(colored.info(f"ℹ️  {message}"))
    

def print_danger(message: str):
    """Print a danger message in bright red bold."""
    print(colored.danger(f"🚨 {message}"))


def print_header(title: str, width: int = 60):
    """Print a formatted header."""
    border = "=" * width
    print(colored.bold(border))
    print(colored.bold(f" {title.center(width-2)} "))
    print(colored.bold(border))


def print_section(title: str):
    """Print a section header."""
    print(colored.info(f"\n📋 {title}"))
    print(colored.dim("-" * (len(title) + 4)))


def format_stats_table(stats: dict) -> str:
    """Format statistics as a colored table."""
    lines = []
    max_key_len = max(len(str(k)) for k in stats.keys()) if stats else 0
    
    for key, value in stats.items():
        key_str = str(key).replace('_', ' ').title()
        value_str = str(value)
        
        # Color code based on value type or content
        if isinstance(value, bool):
            value_str = colored.success("Yes") if value else colored.error("No")
        elif isinstance(value, int) and value > 0:
            value_str = colored.highlight(str(value))
        elif "error" in key.lower() or "failed" in key.lower():
            value_str = colored.error(str(value))
        elif "success" in key.lower() or "deleted" in key.lower():
            value_str = colored.success(str(value))
            
        lines.append(f"  {key_str:<{max_key_len+2}}: {value_str}")
        
    return "\n".join(lines)