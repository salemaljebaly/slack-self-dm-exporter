#!/usr/bin/env python3
"""
Progress bar utilities for Slack DM Thread Cleaner
"""

import time
import sys
import threading
from typing import Optional


class ProgressBar:
    """A simple progress bar with ETA calculation."""
    
    def __init__(self, total: int, description: str = "", width: int = 50):
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.start_time = time.time()
        
    def update(self, count: int = 1, description: Optional[str] = None):
        """Update progress bar."""
        self.current += count
        if description:
            self.description = description
        self._render()
        
    def set_current(self, current: int, description: Optional[str] = None):
        """Set current progress."""
        self.current = current
        if description:
            self.description = description
        self._render()
        
    def _render(self):
        """Render the progress bar."""
        if self.total == 0:
            return
            
        percent = min(100.0, (self.current / self.total) * 100)
        filled = int(self.width * self.current // self.total)
        bar = '█' * filled + '░' * (self.width - filled)
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = self._format_time(eta)
        else:
            eta_str = "calculating..."
            
        # Format the line
        line = f"\r{self.description} {self.current}/{self.total} [{bar}] {percent:.1f}% ETA: {eta_str}"
        
        # Print and flush
        sys.stdout.write(line)
        sys.stdout.flush()
        
    def finish(self, description: Optional[str] = None):
        """Complete the progress bar."""
        self.current = self.total
        if description:
            self.description = description
        self._render()
        print()  # New line
        
    def _format_time(self, seconds: float) -> str:
        """Format seconds into readable time."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds//60)}m {int(seconds%60)}s"
        else:
            return f"{int(seconds//3600)}h {int((seconds%3600)//60)}m"


class MultiProgressTracker:
    """Track multiple progress bars for different operations."""
    
    def __init__(self):
        self.bars = {}
        self.active_bar = None
        
    def create_bar(self, name: str, total: int, description: str) -> ProgressBar:
        """Create a new progress bar."""
        bar = ProgressBar(total, description)
        self.bars[name] = bar
        self.active_bar = name
        return bar
        
    def update_bar(self, name: str, count: int = 1, description: Optional[str] = None):
        """Update a specific progress bar."""
        if name in self.bars:
            self.bars[name].update(count, description)
            
    def set_current_bar(self, name: str, current: int, description: Optional[str] = None):
        """Set current progress for a specific bar."""
        if name in self.bars:
            self.bars[name].set_current(current, description)
            
    def finish_bar(self, name: str, description: Optional[str] = None):
        """Finish a specific progress bar."""
        if name in self.bars:
            self.bars[name].finish(description)
            
    def get_bar(self, name: str) -> Optional[ProgressBar]:
        """Get a progress bar by name."""
        return self.bars.get(name)


class ActivityIndicator:
    """Displays a spinner to show activity during long operations."""

    def __init__(self, message: str = "Working", show_elapsed: bool = False):
        self.message = message
        self.is_running = False
        self.thread = None
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current_idx = 0
        self.show_elapsed = show_elapsed
        self.start_time = None

    def start(self):
        """Start the spinner."""
        if self.is_running:
            return
        self.is_running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def _spin(self):
        """Internal spinner loop."""
        while self.is_running:
            if self.show_elapsed and self.start_time:
                elapsed = time.time() - self.start_time
                elapsed_str = self._format_time(elapsed)
                sys.stdout.write(f"\r{self.spinner_chars[self.current_idx]} {self.message} [{elapsed_str}]...")
            else:
                sys.stdout.write(f"\r{self.spinner_chars[self.current_idx]} {self.message}...")
            sys.stdout.flush()
            self.current_idx = (self.current_idx + 1) % len(self.spinner_chars)
            time.sleep(0.1)

    def stop(self, final_message: Optional[str] = None):
        """Stop the spinner."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 50) + '\r')  # Clear line (increased for elapsed time)
        if final_message:
            print(final_message)
        sys.stdout.flush()

    def update_message(self, message: str):
        """Update the spinner message."""
        self.message = message

    def _format_time(self, seconds: float) -> str:
        """Format seconds into readable time."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds//60)}m {int(seconds%60)}s"
        else:
            return f"{int(seconds//3600)}h {int((seconds%3600)//60)}m"