"""Validate a source distribution and run its complete embedded test suite."""

import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Iterable, List


BLOCKED_PARTS = {
    ".DS_Store",
    ".coverage",
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "reports",
}
BLOCKED_SUFFIXES = {".pyc", ".pyo"}
REQUIRED_PREFIXES = ("examples/", "artifacts/demo/")


def _validated_members(archive: tarfile.TarFile) -> List[tarfile.TarInfo]:
    members = archive.getmembers()
    if not members:
        raise ValueError("source distribution is empty")
    roots = set()
    has_required = {prefix: False for prefix in REQUIRED_PREFIXES}
    for member in members:
        name = PurePosixPath(member.name)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError("unsafe source-distribution path: {0}".format(member.name))
        if not (member.isfile() or member.isdir()):
            raise ValueError(
                "source distribution contains a non-file entry: {0}".format(
                    member.name
                )
            )
        roots.add(name.parts[0])
        relative = PurePosixPath(*name.parts[1:])
        if any(part in BLOCKED_PARTS for part in relative.parts):
            raise ValueError(
                "source distribution contains build/cache data: {0}".format(
                    member.name
                )
            )
        if relative.suffix in BLOCKED_SUFFIXES:
            raise ValueError(
                "source distribution contains bytecode: {0}".format(member.name)
            )
        if member.isfile():
            rendered = str(relative)
            for prefix in REQUIRED_PREFIXES:
                if rendered.startswith(prefix):
                    has_required[prefix] = True
    if len(roots) != 1:
        raise ValueError("source distribution must contain exactly one root directory")
    missing = [prefix for prefix, present in has_required.items() if not present]
    if missing:
        raise ValueError(
            "source distribution is missing fixture trees: {0}".format(
                ", ".join(missing)
            )
        )
    return members


def _find_generated_cache(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in BLOCKED_PARTS for part in path.relative_to(root).parts):
            yield path
        elif path.suffix in BLOCKED_SUFFIXES:
            yield path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_sdist.py PATH_TO_SDIST.tar.gz", file=sys.stderr)
        return 2
    archive_path = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="sdist-check-") as directory:
        destination = Path(directory)
        with tarfile.open(str(archive_path), "r:gz") as archive:
            members = _validated_members(archive)
            root_name = PurePosixPath(members[0].name).parts[0]
            if sys.version_info >= (3, 12):
                archive.extractall(str(destination), members=members, filter="data")
            else:
                archive.extractall(str(destination), members=members)
        root = destination / root_name
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPATH"] = str(root / "src")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ],
            cwd=str(root),
            env=environment,
            check=True,
        )
        generated = list(_find_generated_cache(root))
        if generated:
            raise ValueError(
                "source-distribution tests generated cache data: {0}".format(
                    ", ".join(str(path.relative_to(root)) for path in generated[:10])
                )
            )
    print("Validated source distribution: {0}".format(archive_path.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
