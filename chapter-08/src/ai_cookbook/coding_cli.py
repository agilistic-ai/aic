"""Run a bounded coding job and collect an independently reviewed patch."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from .coding_package import maintain


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="examples/coding/seed")
    parser.add_argument("--image", required=True, help="Inspected Docker image ID, sha256:...")
    parser.add_argument("--output", default="runs/coding")
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image):
            raise ValueError("Use the inspected local image ID.")
        seed = Path(args.seed).resolve()
        output = Path(args.output).resolve()
        if not seed.is_dir():
            raise ValueError("Seed must be an existing directory.")
        if output == seed or seed in output.parents:
            raise ValueError("Output must be outside the seed directory.")
        if not shutil.which("docker"):
            raise ValueError("Docker is required; no worker was started.")
        checked = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", args.image],
                                 capture_output=True, text=True, timeout=15)
        if checked.returncode or checked.stdout.strip() != args.image:
            raise ValueError("The inspected image is not available locally.")
        folder = maintain(seed, args.image, output)
        manifest = json.loads((folder / "manifest.json").read_text())
        print(json.dumps({"job": str(folder), "accepted_by_tests": manifest["accepted_by_tests"],
                          "merge_status": manifest["merge_status"]}))
        return 0 if manifest["accepted_by_tests"] else 1
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Coding job failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
