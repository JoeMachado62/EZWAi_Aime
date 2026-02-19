"""
Service Watchdog
Monitors the OpenClaw Gateway process (which now handles voice natively
via the voice-call extension with Telnyx Call Control).
Auto-restarts on crash and logs failure/recovery events.

Usage:
    python watchdog.py
"""

import asyncio
import logging
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

# Load .env from project root
env_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
load_dotenv(env_path)

# --- Shared Configuration ---
CHECK_INTERVAL_SECS = 30
STARTUP_GRACE_SECS = 15
MAX_HTTP_FAILURES = 3
MAX_RESTARTS_IN_WINDOW = 5
RESTART_WINDOW_SECS = 600  # 10 minutes
COOLDOWN_SECS = 300  # 5 minutes
BACKOFF_BASE_SECS = 5
BACKOFF_MAX_SECS = 60
STABLE_UPTIME_SECS = 300  # 5 min uptime resets failure counters

# --- Service-specific config ---
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(AGENT_DIR, ".."))

# Node.js path - prefer env, then common locations
NODE_PATH = os.getenv("WATCHDOG_NODE_PATH", "node")

# Ensure ngrok is in PATH (WinGet installs to non-standard location)
NGROK_DIR = os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe"
)
if os.path.isdir(NGROK_DIR) and NGROK_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = NGROK_DIR + os.pathsep + os.environ.get("PATH", "")

OPENCLAW_URL = os.getenv("OPENCLAW_BASE_URL", "http://localhost:18789")
GATEWAY_PORT = 18789

# Telnyx Call Control Application - auto-update webhook URL on ngrok tunnel start
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
TELNYX_CC_APP_ID = os.getenv("TELNYX_CONNECTION_ID", "")  # Call Control Application ID
NGROK_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.ngrok[a-z.-]*/voice/webhook")

# --- Logging ---
log_file = os.path.join(AGENT_DIR, "watchdog.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("watchdog")


@dataclass
class ServiceConfig:
    """Configuration for a monitored service."""
    name: str
    command: list[str]
    cwd: str
    health_port: int
    health_path: str = "/"
    startup_grace_secs: int = STARTUP_GRACE_SECS


class ServiceMonitor:
    """Monitors a single service process with health checks and auto-restart."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.process: asyncio.subprocess.Process | None = None
        self.restart_times: list[float] = []
        self.consecutive_http_failures = 0
        self.total_restarts = 0
        self.last_start_time: float = 0
        self.in_cooldown = False
        self.had_failure = False
        self._log_prefix = f"[{config.name}]"
        self._reader_task: asyncio.Task | None = None

    def _log(self, level: str, msg: str):
        getattr(logger, level)(f"{self._log_prefix} {msg}")

    def _kill_port(self):
        """Kill any process occupying the service port before starting."""
        port = self.config.health_port
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = int(parts[-1])
                    if pid != os.getpid():
                        self._log("warning", f"Killing stale process on port {port} (PID {pid})")
                        subprocess.run(
                            ["taskkill", "/PID", str(pid), "/F"],
                            capture_output=True, timeout=10
                        )
                        time.sleep(2)
        except Exception as e:
            self._log("warning", f"Port cleanup failed: {e}")

    async def _read_stdout(self, on_line=None):
        """Background task to read stdout lines without blocking the event loop."""
        if not self.process or not self.process.stdout:
            return
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break  # EOF - process exited
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    # Sanitize for Windows cp1252 console - replace non-ASCII chars
                    safe_text = text.encode("ascii", errors="replace").decode("ascii")
                    self._log("info", f"[out] {safe_text}")
                    # Notify callback if provided (used for ngrok URL detection)
                    if on_line:
                        on_line(safe_text)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def start(self, on_line=None) -> bool:
        """Start the service subprocess."""
        self._kill_port()

        cmd = self.config.command
        self._log("info", f"Starting: {' '.join(cmd)}")

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.config.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.last_start_time = time.time()
            self.consecutive_http_failures = 0
            self._log("info", f"Started (PID {self.process.pid})")
            # Start background stdout reader (non-blocking)
            self._reader_task = asyncio.create_task(self._read_stdout(on_line=on_line))
            return True
        except Exception as e:
            self._log("error", f"Failed to start: {e}")
            return False

    def is_alive(self) -> bool:
        """Check if the subprocess is still running."""
        if self.process is None:
            return False
        return self.process.returncode is None

    async def check_health(self) -> bool:
        """HTTP health check on the service port."""
        try:
            async with httpx.AsyncClient() as client:
                await client.get(
                    f"http://localhost:{self.config.health_port}{self.config.health_path}",
                    timeout=5.0,
                )
                # Any response (even 400/404/426) means the server is up
                return True
        except Exception:
            return False

    async def kill(self):
        """Force-kill the service process."""
        # Cancel the stdout reader first
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self.process and self.is_alive():
            self._log("warning", f"Killing process (PID {self.process.pid})")
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await asyncio.wait_for(self.process.wait(), timeout=5)
            except Exception as e:
                self._log("error", f"Error killing process: {e}")
        self.process = None

    def record_restart(self) -> bool:
        """Record a restart event. Returns True if restart storm detected."""
        now = time.time()
        self.restart_times.append(now)
        self.total_restarts += 1
        cutoff = now - RESTART_WINDOW_SECS
        self.restart_times = [t for t in self.restart_times if t > cutoff]
        return len(self.restart_times) >= MAX_RESTARTS_IN_WINDOW

    def get_backoff_secs(self) -> float:
        """Calculate backoff delay based on recent restart count."""
        recent = len(self.restart_times)
        return min(BACKOFF_BASE_SECS * (2 ** (recent - 1)), BACKOFF_MAX_SECS)

    def get_uptime(self) -> float:
        """Get current service uptime in seconds."""
        if self.last_start_time == 0:
            return 0
        return time.time() - self.last_start_time


class Watchdog:
    """Main watchdog that monitors multiple services."""

    def __init__(self):
        self.shutting_down = False
        self._webhook_url_updated = False

        # OpenClaw Gateway service (handles voice natively via voice-call extension)
        # No --force: lsof unavailable on Windows, _kill_port handles stale processes
        self.gateway = ServiceMonitor(ServiceConfig(
            name="openclaw-gateway",
            command=[NODE_PATH, "scripts/run-node.mjs", "gateway",
                     "--allow-unconfigured"],
            cwd=PROJECT_ROOT,
            health_port=GATEWAY_PORT,
            health_path="/",
            startup_grace_secs=30,  # Gateway takes longer to compile + start
        ))

        self.services = [self.gateway]

    def _on_gateway_line(self, line: str):
        """Callback for gateway stdout lines. Detects ngrok URL and updates Telnyx."""
        if self._webhook_url_updated:
            return
        match = NGROK_URL_PATTERN.search(line)
        if match:
            url = match.group(0)
            self._webhook_url_updated = True
            logger.info(f"Detected ngrok webhook URL: {url}")
            # Fire-and-forget async task to update Telnyx
            asyncio.create_task(self._update_telnyx_webhook(url))

    async def _update_telnyx_webhook(self, webhook_url: str):
        """Update Telnyx Call Control Application webhook URL."""
        if not TELNYX_API_KEY or not TELNYX_CC_APP_ID:
            logger.warning(
                "Cannot update Telnyx webhook: missing TELNYX_API_KEY or TELNYX_CONNECTION_ID"
            )
            return
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"https://api.telnyx.com/v2/call_control_applications/{TELNYX_CC_APP_ID}",
                    headers={
                        "Authorization": f"Bearer {TELNYX_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"webhook_event_url": webhook_url},
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    logger.info(f"Updated Telnyx webhook URL to: {webhook_url}")
                else:
                    logger.error(
                        f"Failed to update Telnyx webhook: {resp.status_code} {resp.text[:200]}"
                    )
        except Exception as e:
            logger.error(f"Error updating Telnyx webhook: {e}")

    async def notify_openclaw(self, event: str, details: str, service: ServiceMonitor):
        """Send health event to OpenClaw gateway (only if gateway is up)."""
        # Don't try to notify the gateway about itself
        if service.config.name == "openclaw-gateway":
            return
        # Don't notify if gateway isn't running
        if not self.gateway.is_alive():
            return

        payload = {
            "event": f"{service.config.name}.{event}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
            "restart_count": service.total_restarts,
            "uptime_secs": round(service.get_uptime()),
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{OPENCLAW_URL}/hooks/voice-health",
                    json=payload,
                    timeout=5.0,
                )
                logger.info(f"Notified OpenClaw: {service.config.name}.{event}")
        except Exception as e:
            logger.warning(f"Failed to notify OpenClaw: {e}")

    async def _handle_process_exit(self, svc: ServiceMonitor):
        """Handle a service process that has exited."""
        exit_code = svc.process.returncode if svc.process else "unknown"
        svc._log("error", f"Process exited (code: {exit_code})")
        await self.notify_openclaw("crash", f"Process exited with code {exit_code}", svc)
        svc.had_failure = True
        # Reset webhook URL flag so it gets updated again after restart
        if svc.config.name == "openclaw-gateway":
            self._webhook_url_updated = False

        if svc.record_restart():
            svc._log("error",
                f"Restart storm detected ({MAX_RESTARTS_IN_WINDOW} restarts in "
                f"{RESTART_WINDOW_SECS}s). Entering cooldown for {COOLDOWN_SECS}s."
            )
            await self.notify_openclaw(
                "cooldown",
                f"Too many restarts ({svc.total_restarts}). Cooling down for {COOLDOWN_SECS}s.",
                svc,
            )
            svc.in_cooldown = True
            await asyncio.sleep(COOLDOWN_SECS)
            svc.in_cooldown = False
            svc.restart_times.clear()
            svc._log("info", "Cooldown complete, resuming")

        backoff = svc.get_backoff_secs()
        svc._log("info", f"Restarting in {backoff}s...")
        await asyncio.sleep(backoff)

        on_line = self._get_line_callback(svc)
        if await svc.start(on_line=on_line):
            svc._log("info", f"Waiting {svc.config.startup_grace_secs}s for startup...")
            await asyncio.sleep(svc.config.startup_grace_secs)

    async def _handle_health_failure(self, svc: ServiceMonitor):
        """Handle a service failing HTTP health checks."""
        svc._log("error",
            f"Unresponsive after {MAX_HTTP_FAILURES} health checks, force-restarting"
        )
        await self.notify_openclaw(
            "crash", "Unresponsive (HTTP health check failed)", svc
        )
        svc.had_failure = True
        # Reset webhook URL flag so it gets updated again after restart
        if svc.config.name == "openclaw-gateway":
            self._webhook_url_updated = False
        await svc.kill()

        if svc.record_restart():
            svc._log("error", "Restart storm, entering cooldown")
            await self.notify_openclaw(
                "cooldown", f"Too many restarts ({svc.total_restarts})", svc
            )
            svc.in_cooldown = True
            await asyncio.sleep(COOLDOWN_SECS)
            svc.in_cooldown = False
            svc.restart_times.clear()

        backoff = svc.get_backoff_secs()
        await asyncio.sleep(backoff)

        on_line = self._get_line_callback(svc)
        if await svc.start(on_line=on_line):
            await asyncio.sleep(svc.config.startup_grace_secs)

    def _get_line_callback(self, svc: ServiceMonitor):
        """Return a line callback for the service (ngrok URL detection for gateway)."""
        if svc.config.name == "openclaw-gateway":
            return self._on_gateway_line
        return None

    async def _monitor_service(self, svc: ServiceMonitor):
        """Monitor loop for a single service."""
        svc._log("info", f"Starting service: {' '.join(svc.config.command)}")
        on_line = self._get_line_callback(svc)

        if not await svc.start(on_line=on_line):
            svc._log("error", "Failed initial start")
            return

        svc._log("info", f"Waiting {svc.config.startup_grace_secs}s for startup...")
        await asyncio.sleep(svc.config.startup_grace_secs)

        while not self.shutting_down:
            try:
                # Check if process is alive
                if not svc.is_alive():
                    await self._handle_process_exit(svc)
                    continue

                # HTTP health check
                http_ok = await svc.check_health()
                if http_ok:
                    svc.consecutive_http_failures = 0

                    if svc.had_failure:
                        svc._log("info", "Recovered successfully")
                        await self.notify_openclaw("recovery", "Service is healthy again", svc)
                        svc.had_failure = False

                    if svc.get_uptime() > STABLE_UPTIME_SECS and svc.restart_times:
                        svc._log("info", "Stable for 5+ minutes, resetting failure counters")
                        svc.restart_times.clear()
                else:
                    svc.consecutive_http_failures += 1
                    svc._log("warning",
                        f"HTTP health check failed "
                        f"({svc.consecutive_http_failures}/{MAX_HTTP_FAILURES})"
                    )

                    if svc.consecutive_http_failures >= MAX_HTTP_FAILURES:
                        await self._handle_health_failure(svc)
                        continue

                await asyncio.sleep(CHECK_INTERVAL_SECS)

            except asyncio.CancelledError:
                break
            except Exception as e:
                svc._log("error", f"Monitor error: {e}")
                await asyncio.sleep(CHECK_INTERVAL_SECS)

        # Shutdown this service
        svc._log("info", "Shutting down...")
        await svc.kill()
        svc._log("info", "Stopped")

    async def run(self):
        """Main watchdog loop - monitors all services concurrently."""
        logger.info("=" * 60)
        logger.info("Service Watchdog starting")
        logger.info(f"  Services: {', '.join(s.config.name for s in self.services)}")
        logger.info(f"  Check interval: {CHECK_INTERVAL_SECS}s")
        logger.info(f"  OpenClaw URL: {OPENCLAW_URL}")
        for svc in self.services:
            logger.info(f"  [{svc.config.name}] port={svc.config.health_port} "
                        f"cmd={' '.join(svc.config.command)}")
        logger.info("=" * 60)

        # Run all service monitors concurrently
        tasks = [asyncio.create_task(self._monitor_service(svc)) for svc in self.services]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            # Cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Watchdog stopped")

    def shutdown(self):
        """Signal the watchdog to stop all services."""
        logger.info("Shutdown requested")
        self.shutting_down = True


def main():
    watchdog = Watchdog()

    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        watchdog.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(watchdog.run())
    except KeyboardInterrupt:
        watchdog.shutdown()


if __name__ == "__main__":
    main()
