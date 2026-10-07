import difflib
import hashlib
import json
import shutil
from pathlib import Path
from uuid import uuid4

from . import coding_accept
from .coding_run import launch
from .coding_snapshot import snapshot


def maintain(seed, image, output="runs/coding"):
    baseline = snapshot(seed)
    folder = Path(output) / uuid4().hex
    folder.mkdir(parents=True)
    workspace = folder / "candidate"
    shutil.copytree(seed, workspace)
    (folder / "baseline.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    run = launch(workspace, image, folder / "agent-evidence")
    acceptance = {"passed": False, "reason": "Agent run didn't finish normally."}
    if run["returncode"] == 0 and run["stop_reason"] is None:
        try:
            acceptance = coding_accept.assess(workspace, image, baseline)
        except ValueError as error:
            acceptance = {"passed": False, "reason": str(error)}
    patch = None
    if acceptance["passed"]:
        candidate = acceptance["candidate"]
        lines = difflib.unified_diff(
            baseline["capacity.py"]["text"].splitlines(keepends=True),
            candidate["capacity.py"]["text"].splitlines(keepends=True),
            fromfile="a/capacity.py", tofile="b/capacity.py",
        )
        patch = "".join(line if line.endswith("\n") else
                        line + "\n\\ No newline at end of file\n" for line in lines)
        (folder / "proposal.patch").write_text(patch, encoding="utf-8")
    (folder / "acceptance.json").write_text(json.dumps(acceptance, indent=2), encoding="utf-8")
    manifest = {
        "image": image, "accepted_by_tests": acceptance["passed"],
        "baseline_sha256": hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest(),
        "gate_sha256": hashlib.sha256(Path(coding_accept.__file__).read_bytes()).hexdigest(),
        "patch_sha256": None if patch is None else hashlib.sha256(patch.encode()).hexdigest(),
        "merge_status": "awaiting_human_review",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder
