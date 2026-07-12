"""
File download manager with progress reporting.
Equivalent to asyncinet.cpp and loaddlg.cpp in the original C++ code.
"""

import os
import ssl
import urllib.request
import urllib.error
import threading
from typing import Optional, Callable


class DownloadProgress:
    """Tracks download progress."""

    def __init__(self):
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.speed = 0.0  # bytes per second
        self.percentage = 0.0
        self.cancelled = False
        self.error = None
        self._start_time = 0
        self._last_update = 0
        self._last_bytes = 0

    @property
    def is_complete(self) -> bool:
        return self.total_bytes > 0 and self.downloaded_bytes >= self.total_bytes


def download_file(
    url: str,
    dest_path: str,
    on_progress: Optional[Callable[[DownloadProgress], None]] = None,
    timeout: int = 300,
) -> bool:
    """
    Download a file from URL to local path.
    
    Args:
        url: URL to download from
        dest_path: Local file path to save to
        on_progress: Optional callback for progress updates
        timeout: Download timeout in seconds
    
    Returns:
        True if download succeeded, False otherwise
    """
    progress = DownloadProgress()
    progress._start_time = _time()

    try:
        # Create destination directory if needed
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        # Create temp file for partial download
        temp_path = dest_path + ".tmp"

        # Set up request
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "RAPPS/1.1")

        # Disable SSL verification for compatibility (same as original)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            # Get content length
            content_length = response.headers.get("Content-Length")
            if content_length:
                progress.total_bytes = int(content_length)

            # Write to temp file
            with open(temp_path, "wb") as f:
                while True:
                    if progress.cancelled:
                        progress.error = "Cancelled"
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass
                        return False

                    chunk = response.read(8192)
                    if not chunk:
                        break

                    f.write(chunk)
                    progress.downloaded_bytes += len(chunk)

                    # Calculate speed
                    now = _time()
                    elapsed = now - progress._last_update
                    if elapsed >= 0.5:
                        progress.speed = (progress.downloaded_bytes - progress._last_bytes) / elapsed
                        progress._last_update = now
                        progress._last_bytes = progress.downloaded_bytes

                    # Update percentage
                    if progress.total_bytes > 0:
                        progress.percentage = (progress.downloaded_bytes / progress.total_bytes) * 100

                    # Notify progress
                    if on_progress:
                        on_progress(progress)

        # Rename temp file to final destination
        try:
            os.remove(dest_path)
        except OSError:
            pass
        os.rename(temp_path, dest_path)

        return True

    except Exception as e:
        progress.error = str(e)
        try:
            os.remove(temp_path)
        except OSError:
            pass
        return False


def download_with_threads(
    downloads: list,
    on_progress: Optional[Callable] = None,
    on_complete: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
) -> "DownloadWorker":
    """
    Start a multi-file download in a background thread.
    
    Args:
        downloads: List of (url, dest_path) tuples
        on_progress: Called with (current_index, total, progress) for each download
        on_complete: Called when all downloads complete
        on_error: Called with error message on failure
    
    Returns:
        DownloadWorker instance (call .cancel() to stop)
    """
    worker = DownloadWorker(downloads, on_progress, on_complete, on_error)
    worker.start()
    return worker


class DownloadWorker:
    """Background worker for multi-file downloads."""

    def __init__(self, downloads, on_progress, on_complete, on_error):
        self.downloads = downloads
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self._thread = None
        self._cancelled = False
        self._results = []

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancelled = True

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        for i, (url, dest) in enumerate(self.downloads):
            if self._cancelled:
                break

            def progress_callback(progress, idx=i, total=len(self.downloads)):
                if self.on_progress:
                    self.on_progress(idx, total, progress)

            success = download_file(url, dest, on_progress=progress_callback)
            self._results.append((url, dest, success))

            if not success and self.on_error:
                self.on_error(url, dest)
                break

        if self.on_complete and not self._cancelled:
            self.on_complete(self._results)


def _time():
    """Get current time."""
    import time
    return time.time()
