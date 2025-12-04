# Performance Utilities - Memory monitoring and optimization

import psutil
import logging
import gc
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
import shutil

logger = logging.getLogger(__name__)


@contextmanager
def memory_monitor(job_id: str) -> Generator[None, None, None]:
    """
    Monitor memory usage for a job and cleanup after
    
    Usage:
        with memory_monitor(job_id):
            # process video
            pass
    """
    process = psutil.Process()
    start_mem = process.memory_info().rss / 1024 / 1024  # MB
    
    logger.info(f"💾 Memory at start: {start_mem:.1f}MB")
    
    try:
        yield
    finally:
        end_mem = process.memory_info().rss / 1024 / 1024
        delta = end_mem - start_mem
        
        logger.info(f"💾 Memory at end: {end_mem:.1f}MB (Δ{delta:+.1f}MB)")
        
        # Force garbage collection
        gc.collect()
        
        after_gc = process.memory_info().rss / 1024 / 1024
        gc_freed = end_mem - after_gc
        
        if gc_freed > 0:
            logger.info(f"♻️  GC freed: {gc_freed:.1f}MB")


def get_disk_space(path: Path) -> dict:
    """Get disk space info"""
    stat = shutil.disk_usage(path)
    return {
        'total_gb': stat.total / (1024**3),
        'used_gb': stat.used / (1024**3),
        'free_gb': stat.free / (1024**3),
        'percent': (stat.used / stat.total) * 100
    }


def check_disk_space(path: Path, required_gb: float = 1.0) -> bool:
    """Check if enough disk space available"""
    space = get_disk_space(path)
    
    if space['free_gb'] < required_gb:
        logger.error(f"❌ Insufficient disk space: {space['free_gb']:.2f}GB < {required_gb}GB")
        return False
    
    logger.info(f"💿 Disk space: {space['free_gb']:.1f}GB free ({space['percent']:.1f}% used)")
    return True


@contextmanager
def temp_file_cleanup(*paths: Path) -> Generator[None, None, None]:
    """
    Ensure temp files are cleaned up even if error occurs
    
    Usage:
        with temp_file_cleanup(file1, file2):
            # process files
            pass
    """
    try:
        yield
    finally:
        for path in paths:
            try:
                if path.exists():
                    if path.is_file():
                        path.unlink()
                        logger.debug(f"🗑️  Cleaned up: {path.name}")
                    elif path.is_dir():
                        shutil.rmtree(path)
                        logger.debug(f"🗑️  Cleaned up dir: {path.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {e}")


def detect_hardware_accel() -> str | None:
    """
    Detect available hardware acceleration
    
    Returns:
        'cuda' | 'qsv' | 'videotoolbox' | None
    """
    import subprocess
    import platform
    
    try:
        # Check NVIDIA GPU (CUDA)
        if platform.system() == "Windows" or platform.system() == "Linux":
            try:
                result = subprocess.run(
                    ['nvidia-smi'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    logger.info("🎮 CUDA acceleration available")
                    return 'cuda'
            except:
                pass
        
        # Check Intel QuickSync (QSV)
        if platform.system() == "Windows":
            # Check for Intel GPU
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if 'Intel' in result.stdout:
                    logger.info("⚡ Intel QSV acceleration available")
                    return 'qsv'
            except:
                pass
        
        # Check Apple VideoToolbox (macOS)
        if platform.system() == "Darwin":
            logger.info("🍎 VideoToolbox acceleration available")
            return 'videotoolbox'
        
    except Exception as e:
        logger.debug(f"Hardware detection failed: {e}")
    
    logger.info("💻 No hardware acceleration, using software encoding")
    return None


class ProgressTracker:
    """Track and report pipeline progress"""
    
    def __init__(self, total_steps: int = 9):
        self.total_steps = total_steps
        self.current_step = 0
        self.step_name = ""
    
    def update(self, step: int, step_name: str, message: str = ""):
        """Update progress"""
        self.current_step = step
        self.step_name = step_name
        percent = (step / self.total_steps) * 100
        
        logger.info(f"📊 Progress: {percent:.0f}% - Step {step}/{self.total_steps}: {step_name}")
        if message:
            logger.info(f"   {message}")
    
    def complete(self):
        """Mark as complete"""
        logger.info(f"✅ Processing complete!")
