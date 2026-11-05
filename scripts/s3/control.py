import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

# Publication adaptation: keep state and the credential-bearing .env backup
# outside the source repository. The original local helper used its own folder.
folder = Path.home() / "openrag-s3-lab"
folder.mkdir(mode=0o700, parents=True, exist_ok=True)
folder.chmod(0o700)
state_file = folder / "original-deployment.json"
override_file = folder / "compose.s3-native.override.json"

action = sys.argv[1] if len(sys.argv) == 2 else ""
if action not in {"enable", "disable"}:
    raise SystemExit("Usage: python3 control.py enable|disable")

def capture(*args):
    return subprocess.check_output(args, text=True).strip()

labels = json.loads(capture(
    "docker", "inspect",
    "--format", "{{json .Config.Labels}}",
    "tui-backend"
))

if state_file.exists():
    state = json.loads(state_file.read_text())
else:
    state = {
        "project": labels.get("com.docker.compose.project"),
        "workdir": labels.get("com.docker.compose.project.working_dir"),
        "service": labels.get("com.docker.compose.service"),
        "files": [
            item for item in
            labels.get(
                "com.docker.compose.project.config_files", ""
            ).split(",")
            if item
        ],
    }

    if not all(state.get(k) for k in (
        "project", "workdir", "service", "files"
    )):
        raise SystemExit("STOP: Compose deployment metadata is incomplete.")

    state_file.write_text(json.dumps(state, indent=2))
    os.chmod(state_file, 0o600)

if state["project"] != labels.get("com.docker.compose.project"):
    raise SystemExit("STOP: Current container belongs to a different project.")

workdir = Path(state["workdir"])
env_file = workdir / ".env"

if not env_file.is_file():
    raise SystemExit(
        "STOP: Expected .env not found. Inspect the launcher setup first."
    )

for filename in state["files"]:
    if not Path(filename).is_file():
        raise SystemExit(f"STOP: Compose file missing: {filename}")

backup = folder / ".env.before-s3-native"
if not backup.exists():
    shutil.copy2(env_file, backup)
    os.chmod(backup, 0o600)

override = {
    "services": {
        state["service"]: {
            "environment": {
                "OPENRAG_DEV_AWS_S3":
                    "true" if action == "enable" else "false"
            }
        }
    }
}
override_file.write_text(json.dumps(override, indent=2))

command = [
    "docker", "compose",
    "--project-directory", str(workdir),
    "--project-name", state["project"],
    "--env-file", str(env_file),
]

for filename in state["files"]:
    command.extend(["-f", filename])

command.extend(["-f", str(override_file)])

subprocess.run(command + ["config", "--quiet"], check=True)

subprocess.run(command + [
    "up", "-d",
    "--no-deps",
    "--no-build",
    "--pull", "never",
    "--force-recreate",
    state["service"],
], check=True)

print("Backend S3 development mode:", action)
print("Original deployment metadata retained.")
