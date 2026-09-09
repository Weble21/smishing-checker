"""Send checked-out deployment files to EC2 and report the actual SSM result."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def deployment_instance_id() -> str:
    value = os.environ.get("EC2_INSTANCE_ID", "")
    if not value.strip():
        raise ValueError("EC2_INSTANCE_ID is empty. Add the EC2 instance ID to GitHub Repository secrets.")
    if not re.fullmatch(r"i-(?:[0-9a-f]{8}|[0-9a-f]{17})", value):
        raise ValueError("EC2_INSTANCE_ID must be an EC2 ID (i- followed by 8 or 17 hex characters), without spaces; not an ARN or IP address.")
    return value


def remote_command() -> str:
    values = {
        "TAG": os.environ["TAG"],
        "REGISTRY": os.environ["REGISTRY"],
        "AWS_REGION": os.environ["AWS_REGION"],
        "COMPOSE_B64": base64.b64encode((ROOT / "compose.prod.yml").read_bytes()).decode(),
    }
    exports = "\n".join(f"export {key}={shlex.quote(value)}" for key, value in values.items())
    script = (ROOT / "scripts/deploy-ec2.sh").read_text(encoding="utf-8")
    return "bash -c " + shlex.quote(exports + "\n" + script)


def aws(*args: str) -> dict:
    result = subprocess.run(
        ["aws", "ssm", *args, "--region", os.environ["AWS_REGION"], "--output", "json"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def wait_for_command(command_id: str, instance_id: str, timeout: int = 2400) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = aws("get-command-invocation", "--command-id", command_id,
                         "--instance-id", instance_id)
        except subprocess.CalledProcessError as error:
            if "InvocationDoesNotExist" not in error.stderr:
                raise
            time.sleep(10)
            continue
        status = result["Status"]
        print(f"SSM status: {status}", flush=True)
        if status in {"Pending", "InProgress", "Delayed", "Cancelling"}:
            time.sleep(10)
            continue
        print(result.get("StandardOutputContent", ""))
        print(result.get("StandardErrorContent", ""))
        if status != "Success" or result.get("ResponseCode") != 0:
            raise RuntimeError(f"Deployment failed: {status}, exit={result.get('ResponseCode')}")
        return
    raise TimeoutError(f"SSM command {command_id} did not finish within {timeout}s; inspect EC2 before retrying")


def main() -> None:
    instance_id = deployment_instance_id()
    result = aws(
        "send-command", "--instance-ids", instance_id,
        "--document-name", "AWS-RunShellScript", "--timeout-seconds", "120",
        "--comment", f"Deploy smishing-checker {os.environ['TAG']}",
        "--parameters", json.dumps({"commands": [remote_command()], "executionTimeout": ["2100"]}),
    )
    command_id = result["Command"]["CommandId"]
    print(f"SSM command ID: {command_id}", flush=True)
    wait_for_command(command_id, instance_id)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stderr, flush=True)
        raise SystemExit(error.returncode) from None
    except ValueError as error:
        raise SystemExit(str(error)) from None
