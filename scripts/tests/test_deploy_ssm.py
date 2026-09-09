import base64
import importlib.util
from pathlib import Path
import shlex
import subprocess

import pytest

SPEC = importlib.util.spec_from_file_location(
    "deploy_ssm", Path(__file__).resolve().parents[1] / "deploy_ssm.py",
)
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


@pytest.mark.parametrize("value", [None, "", " ", "i-REPLACE_ME", "127.0.0.1", " i-0123456789abcdef0", "i-0123456789abcdef0\n"])
def test_invalid_instance_id_stops_before_aws(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("EC2_INSTANCE_ID", raising=False)
    else:
        monkeypatch.setenv("EC2_INSTANCE_ID", value)
    def unexpected_aws(*args):
        pytest.fail("AWS must not be called with an invalid instance ID")
    monkeypatch.setattr(deploy, "aws", unexpected_aws)
    with pytest.raises(ValueError, match="EC2_INSTANCE_ID"):
        deploy.main()


@pytest.mark.parametrize("value", ["i-01234567", "i-0123456789abcdef0"])
def test_valid_instance_id(monkeypatch, value):
    monkeypatch.setenv("EC2_INSTANCE_ID", value)
    assert deploy.deployment_instance_id() == value


def test_command_transfers_exact_checked_out_compose(monkeypatch):
    for key, value in {"TAG": "abc123", "REGISTRY": "example.ecr", "AWS_REGION": "ap-northeast-2"}.items():
        monkeypatch.setenv(key, value)
    command = shlex.split(deploy.remote_command())
    assert command[:2] == ["bash", "-c"]
    exports = dict(shlex.split(line)[1].split("=", 1) for line in command[2].splitlines()[:4])
    assert exports["TAG"] == "abc123"
    assert base64.b64decode(exports["COMPOSE_B64"]) == (deploy.ROOT / "compose.prod.yml").read_bytes()
    assert "set -Eeuo pipefail" in command[2]


def test_wait_handles_eventual_consistency_and_slow_model_start(monkeypatch):
    replies = iter([
        subprocess.CalledProcessError(1, "aws", stderr="InvocationDoesNotExist"),
        *[{"Status": "InProgress"}] * 25,
        {"Status": "Success", "ResponseCode": 0},
    ])
    def response(*args):
        item = next(replies)
        if isinstance(item, Exception):
            raise item
        return item
    monkeypatch.setattr(deploy, "aws", response)
    monkeypatch.setattr(deploy.time, "sleep", lambda _: None)
    deploy.wait_for_command("command", "instance")


@pytest.mark.parametrize("status,code", [("Failed", 1), ("TimedOut", -1), ("Cancelled", -1), ("Success", 1)])
def test_remote_failure_is_not_reported_as_success(monkeypatch, status, code):
    monkeypatch.setattr(deploy, "aws", lambda *args: {"Status": status, "ResponseCode": code})
    with pytest.raises(RuntimeError, match="Deployment failed"):
        deploy.wait_for_command("command", "instance")


def test_wait_timeout_is_failure(monkeypatch):
    ticks = iter([0, 0, 20])
    monkeypatch.setattr(deploy.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(deploy.time, "sleep", lambda _: None)
    monkeypatch.setattr(deploy, "aws", lambda *args: {"Status": "InProgress"})
    with pytest.raises(TimeoutError):
        deploy.wait_for_command("command", "instance", timeout=10)


def test_aws_permission_error_is_not_retried_forever(monkeypatch):
    def denied(*args):
        raise subprocess.CalledProcessError(1, "aws", stderr="AccessDeniedException")
    monkeypatch.setattr(deploy, "aws", denied)
    with pytest.raises(subprocess.CalledProcessError):
        deploy.wait_for_command("command", "instance")
