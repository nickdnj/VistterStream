#!/usr/bin/env python3
"""
Collect environment metadata (platform, Python, Node, Docker, ONVIF library versions).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _capture(cmd: list[str] | str) -> str:
    shell = isinstance(cmd, str)
    try:
        output = subprocess.check_output(
            cmd,
            shell=shell,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        data = exc.output.strip() if exc.output else str(exc)
        return f"error: {data}"
    return output.strip()


def _pip_show(package: str) -> Optional[str]:
    try:
        output = subprocess.check_output(
            [sys.executable, "-m", "pip", "show", package],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    for line in output.splitlines():
        if line.lower().startswith("version:"):
            return line.split(":", 1)[1].strip()
    return None


def collect_metadata(label: Optional[str]) -> dict:
    platform_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
    }
    python_info = {
        "executable": sys.executable,
        "version": platform.python_version(),
    }
    node_info = {
        "node": _capture("node -v"),
        "npm": _capture("npm -v"),
        "pnpm": _capture("pnpm -v"),
    }
    docker_info = {
        "docker": _capture("docker --version"),
        "docker compose": _capture("docker compose version"),
    }
    pip_info = {
        "onvif-zeep": _pip_show("onvif-zeep"),
        "zeep": _pip_show("zeep"),
    }

    env_info = {
        "platform": platform_info,
        "python": python_info,
        "node": node_info,
        "docker": docker_info,
        "pip": pip_info,
    }

    overrides = {
        "PTZ_DEBUG": os.getenv("PTZ_DEBUG"),
        "ONVIF_DEVICE_URL": os.getenv("ONVIF_DEVICE_URL"),
        "ONVIF_PTZ_URL": os.getenv("ONVIF_PTZ_URL"),
    }
    env_info["ptz_overrides"] = {k: v for k, v in overrides.items() if v}

    if label:
        env_info["label"] = label

    return env_info


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Vistter Stream environment metadata")
    parser.add_argument("--output", required=True, help="Path to write JSON output")
    parser.add_argument("--label", help="Optional environment label (e.g., mac, pi)")
    args = parser.parse_args()

    metadata = collect_metadata(args.label)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2))
    print(f"Wrote environment metadata to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
