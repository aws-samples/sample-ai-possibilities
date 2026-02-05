#!/usr/bin/env python3
"""
FFmpeg utilities for Lambda
Downloads and manages FFmpeg binary for AWS Lambda execution
"""

import os
import subprocess
import tempfile
import logging
import requests
import tarfile
import gzip
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

# FFmpeg static binary URL for Linux ARM64
FFMPEG_URLS = {
    "x86_64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
    "aarch64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
}
FFMPEG_BINARY_PATH = "/tmp/ffmpeg"

def ensure_ffmpeg_available():
    """
    Ensure FFmpeg binary is available in /tmp/
    Downloads correct binary depending on architecture
    """
    if os.path.exists(FFMPEG_BINARY_PATH) and os.access(FFMPEG_BINARY_PATH, os.X_OK):
        try:
            result = subprocess.run([FFMPEG_BINARY_PATH, '-version'], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return FFMPEG_BINARY_PATH
            else:
                os.unlink(FFMPEG_BINARY_PATH)
        except Exception:
            if os.path.exists(FFMPEG_BINARY_PATH):
                os.unlink(FFMPEG_BINARY_PATH)

    arch = platform.machine()
    logger.info(f"Detected architecture: {arch}")
    
    download_url = FFMPEG_URLS.get(arch)
    if not download_url:
        raise RuntimeError(f"Unsupported architecture: {arch}")

    try:
        response = requests.get(download_url, stream=True, timeout=120)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.xz') as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_archive = tmp_file.name

        with tarfile.open(tmp_archive, 'r:xz') as tar:
            for member in tar.getmembers():
                if member.name.endswith('/ffmpeg') and member.isfile():
                    with tar.extractfile(member) as f_in, open(FFMPEG_BINARY_PATH, 'wb') as f_out:
                        f_out.write(f_in.read())
                    break
            else:
                raise RuntimeError("FFmpeg binary not found in archive")

        os.chmod(FFMPEG_BINARY_PATH, 0o755)
        os.unlink(tmp_archive)

        return FFMPEG_BINARY_PATH

    except Exception as e:
        logger.error(f"Failed to setup FFmpeg: {e}")
        raise RuntimeError(f"FFmpeg setup failed: {e}")

def get_ffmpeg_path():
    """Get the path to FFmpeg binary, ensuring it's available"""
    return ensure_ffmpeg_available()

def run_ffmpeg_command(command_args, timeout=60):
    """
    Run an FFmpeg command with the downloaded binary
    
    Args:
        command_args: List of command arguments (without 'ffmpeg')
        timeout: Command timeout in seconds
        
    Returns:
        subprocess.CompletedProcess object
    """
    ffmpeg_path = get_ffmpeg_path()
    full_command = [ffmpeg_path] + command_args
    
    logger.info(f"Running FFmpeg: {' '.join(full_command)}")
    
    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False  # Don't raise on non-zero exit
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg failed with code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
        
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"FFmpeg command timed out after {timeout}s")
        raise
    except Exception as e:
        logger.error(f"FFmpeg execution error: {e}")
        raise