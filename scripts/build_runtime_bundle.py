#!/usr/bin/env python3
"""
Build a runtime bundle that does not require Node.js on target machines.

Features:
- Ensures frontend dist exists (builds it if needed).
- Downloads Python dependencies into wheelhouse for offline bootstrap.
- Copies runtime files with cross-platform Python stdlib.
- Creates both .tar.gz and .zip archives.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_frontend_dist(root_dir: Path, frontend_dir: Path, dist_entry: Path) -> None:
    if dist_entry.exists():
        print(f"Using existing frontend bundle: {dist_entry}")
        return

    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError(
            f"Frontend bundle missing: {dist_entry}\n"
            "npm is not available, cannot build frontend on this machine."
        )

    print("frontend/dist missing, building with Vite...")
    lock_file = frontend_dir / "package-lock.json"
    if lock_file.exists():
        run([npm, "--prefix", str(frontend_dir), "ci"], cwd=root_dir)
    else:
        run([npm, "--prefix", str(frontend_dir), "install"], cwd=root_dir)
    run([npm, "--prefix", str(frontend_dir), "run", "build"], cwd=root_dir)

    if not dist_entry.exists():
        raise RuntimeError(f"Build finished but {dist_entry} is still missing.")


def resolve_python() -> str:
    candidates = []
    env_py = os.environ.get("SELF_TOOLS_PYTHON")
    if env_py:
        candidates.append(env_py)
    candidates.extend(["python3.12", "python3.11", "python3.10", "python3.9", "python3"])

    for candidate in candidates:
        exe = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
        if not exe or not os.path.exists(exe):
            continue
        try:
            out = subprocess.check_output(
                [exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                text=True,
            ).strip()
        except Exception:
            continue
        try:
            major, minor = [int(x) for x in out.split(".")]
        except Exception:
            continue
        if major == 3 and 9 <= minor <= 12:
            return exe

    raise RuntimeError(
        "No supported Python found for wheelhouse build. "
        "Need Python 3.9 - 3.12 (set SELF_TOOLS_PYTHON to override)."
    )


def build_wheelhouse(root_dir: Path, requirements: Path, wheelhouse: Path) -> None:
    py = resolve_python()
    wheelhouse.mkdir(parents=True, exist_ok=True)
    run([py, "-m", "pip", "download", "-r", str(requirements), "-d", str(wheelhouse)], cwd=root_dir)


def copy_tree(src: Path, dst: Path, ignore: shutil.IgnorePattern | None = None) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def write_runtime_docs(bundle_dir: Path) -> None:
    content = """# Runtime Package (No Node.js Required)

This package already includes `frontend/dist`.

## Start

```bash
./start.sh
```

If Python virtualenv is missing, bootstrap will create `.venv` and install
dependencies from local `wheelhouse` (offline mode).

## Notes

- Node.js is not required at runtime.
- If `frontend/dist/cv-tools.html` is deleted, `/cv-tools` will not work.
- Python 3.9 - 3.12 is recommended for runtime dependencies.
- If your default python is 3.13, run with:
  `SELF_TOOLS_PYTHON=/usr/bin/python3 ./start.sh`
"""
    (bundle_dir / "RUNTIME.md").write_text(content, encoding="utf-8")


def get_git_commit(root_dir: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root_dir), "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def write_manifest(bundle_dir: Path, root_dir: Path) -> None:
    lines = [
        f"bundle_created_at={dt.datetime.utcnow().replace(microsecond=0).isoformat()}Z",
        f"git_commit={get_git_commit(root_dir)}",
        "dist_entry=frontend/dist/cv-tools.html",
        "node_required_at_runtime=no",
        "offline_wheelhouse=1",
    ]
    (bundle_dir / "BUNDLE_INFO.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_archives(out_base: Path, bundle_dir: Path) -> tuple[Path, Path]:
    tar_path = out_base / f"{bundle_dir.name}.tar.gz"
    zip_path = out_base / f"{bundle_dir.name}.zip"

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(bundle_dir, arcname=bundle_dir.name)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in bundle_dir.rglob("*"):
            zf.write(path, path.relative_to(bundle_dir.parent))

    return tar_path, zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build runtime bundle.")
    parser.add_argument(
        "out_base",
        nargs="?",
        default=None,
        help="Output base directory (default: <repo>/release)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root_dir = Path(__file__).resolve().parent.parent
    frontend_dir = root_dir / "frontend"
    dist_entry = frontend_dir / "dist" / "cv-tools.html"
    out_base = Path(args.out_base).resolve() if args.out_base else (root_dir / "release")
    out_base.mkdir(parents=True, exist_ok=True)

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_dir = out_base / f"self_tools_runtime_{stamp}"
    wheelhouse_dir = bundle_dir / "wheelhouse"

    ensure_frontend_dist(root_dir, frontend_dir, dist_entry)

    # Build offline wheelhouse first; if this fails, bundle is incomplete for offline runtime.
    build_wheelhouse(root_dir, root_dir / "requirements.txt", wheelhouse_dir)

    copy_tree(root_dir / "backend", bundle_dir / "backend")
    copy_tree(
        frontend_dir,
        bundle_dir / "frontend",
        ignore=shutil.ignore_patterns("node_modules", ".cache"),
    )
    copy_tree(root_dir / "scripts", bundle_dir / "scripts")

    for rel in ["requirements.txt", "dev_server.py", "start.sh", "README.md"]:
        src = root_dir / rel
        dst = bundle_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    write_runtime_docs(bundle_dir)
    write_manifest(bundle_dir, root_dir)
    tar_path, zip_path = make_archives(out_base, bundle_dir)

    print("Runtime bundle created:")
    print(f"  Directory: {bundle_dir}")
    print(f"  Archive  : {tar_path}")
    print(f"  Archive  : {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
