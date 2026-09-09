"""Exercise the real remote script with fake CLI tools, never touching AWS/Docker."""
import base64
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = ("C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash"))


@pytest.fixture
def server(tmp_path):
    for relative in ("models/text/config.json", "models/url/model/config.json",
                     "models/url/internal_test_metrics.json"):
        file = tmp_path / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("{}", encoding="utf-8")
    (tmp_path / ".env").write_text("VT_API_KEY=test-placeholder\nIMAGE_TAG=old\n", encoding="utf-8")
    (tmp_path / "compose.prod.yml").write_text("old compose", encoding="utf-8")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    stubs = {
        "docker": '''printf '%s\\n' "docker $*" >> "$COMMAND_LOG"
case "$*" in
  'compose up --help') echo '--wait-timeout'; exit 0 ;;
  login*) cat >/dev/null ;;
esac
if [[ "$FAIL_AT" == pull && "$*" == *' pull' ]]; then exit 42; fi
if [[ "$FAIL_AT" == up && "$*" == *' up -d '* ]]; then exit 43; fi
exit 0
''',
        "aws": "echo fake-password\n",
        "flock": "exit 0\n",
        "curl": '''echo curl >> "$COMMAND_LOG"
if [ "$FAIL_AT" = curl ]; then exit 22; fi
''',
    }
    for name, content in stubs.items():
        file = binaries / name
        file.write_text("#!/usr/bin/env bash\n" + content, encoding="utf-8", newline="\n")
        file.chmod(0o755)
    return tmp_path


def run_deploy(server, failure=""):
    environment = dict(os.environ, DEPLOY_DIR=server.as_posix(), TAG="new-tag",
                       REGISTRY="test.ecr", AWS_REGION="ap-northeast-2", FAIL_AT=failure,
                       FAKE_BIN=(server / "bin").as_posix(),
                       COMMAND_LOG=(server / "commands.log").as_posix(),
                       DEPLOY_SCRIPT=(ROOT / "scripts/deploy-ec2.sh").as_posix(),
                       COMPOSE_B64=base64.b64encode(b"new compose").decode())
    return subprocess.run(
        [BASH, "-c", 'export PATH="$(cd "$FAKE_BIN" && pwd):$PATH"; exec bash "$DEPLOY_SCRIPT"'],
        env=environment, capture_output=True, text=True, timeout=30,
    )


@pytest.mark.parametrize("release_env", ["IMAGE_TAG=old\n", "", " export IMAGE_TAG = old\nECR_REGISTRY = old.ecr\n"])
def test_success_updates_compose_and_tag_and_checks_http(server, release_env):
    original_env = "VT_API_KEY=test-placeholder\n" + release_env
    (server / ".env").write_text(original_env, encoding="utf-8")
    result = run_deploy(server)
    assert result.returncode == 0, result.stderr
    assert (server / "compose.prod.yml").read_text() == "new compose"
    assert (server / "compose.prod.yml.previous").read_text() == "old compose"
    assert (server / ".env.previous").read_text() == original_env
    env = (server / ".env").read_text()
    assert "VT_API_KEY=test-placeholder" in env
    assert "IMAGE_TAG=new-tag" in env and "ECR_REGISTRY=test.ecr" in env
    assert env.count("IMAGE_TAG=") == 1
    assert env.count("IMAGE_TAG") == 1 and env.count("ECR_REGISTRY") == 1
    assert "curl" in (server / "commands.log").read_text()
    assert "Deployment verified: new-tag" in result.stdout


def test_pull_failure_preserves_existing_release(server):
    result = run_deploy(server, "pull")
    assert result.returncode == 42
    assert (server / "compose.prod.yml").read_text() == "old compose"
    assert "IMAGE_TAG=old" in (server / ".env").read_text()
    assert " up -d " not in (server / "commands.log").read_text()


@pytest.mark.parametrize("failure,code", [("up", 43), ("curl", 22)])
def test_start_or_http_failure_remains_a_failure(server, failure, code):
    result = run_deploy(server, failure)
    assert result.returncode == code
    assert "Deployment verified" not in result.stdout
    assert "logs --no-color --tail 100" in (server / "commands.log").read_text()


def test_missing_model_fails_before_docker_changes(server):
    (server / "models/text/config.json").unlink()
    result = run_deploy(server)
    assert result.returncode != 0
    assert not (server / "commands.log").exists()
