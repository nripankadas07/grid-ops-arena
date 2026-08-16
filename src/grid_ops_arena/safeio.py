"""Symlink-safe, staged publication for a set of text artifacts."""

import os
import secrets
import stat
import sys
import tempfile
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

try:
    import fcntl
except ImportError:  # pragma: no cover - platform-specific fallback
    fcntl = None


Metadata = Optional[Tuple[int, int]]


_DESCRIPTOR_IO_AVAILABLE = all(
    function in os.supports_dir_fd
    for function in (os.open, os.mkdir, os.rename, os.stat, os.unlink)
)


def _absolute_output_path(path: Path) -> Path:
    """Return an absolute path while preserving application-owned symlinks.

    macOS exposes a few root-owned compatibility aliases.  Normalising only
    those verified aliases lets descriptor-relative walking accept ordinary
    ``tempfile`` paths without resolving any user-controlled component.
    """
    absolute = Path(os.path.abspath(os.fspath(path)))
    if sys.platform != "darwin" or len(absolute.parts) < 2:
        return absolute
    alias = Path(absolute.anchor or os.sep) / absolute.parts[1]
    expected = {
        Path("/etc"): Path("/private/etc"),
        Path("/tmp"): Path("/private/tmp"),
        Path("/var"): Path("/private/var"),
    }.get(alias)
    if expected is None:
        return absolute
    try:
        metadata = alias.lstat()
    except OSError:
        return absolute
    if (
        stat.S_ISLNK(metadata.st_mode)
        and metadata.st_uid == 0
        and Path(os.path.realpath(os.fspath(alias))) == expected
    ):
        return expected.joinpath(*absolute.parts[2:])
    return absolute


def _descriptor_io_available() -> bool:
    return _DESCRIPTOR_IO_AVAILABLE


def _require_directory_locking() -> None:
    if fcntl is None or not hasattr(fcntl, "flock"):
        raise OSError("advisory directory locking is unavailable on this platform")


def _lock_directory(directory_fd: int) -> None:
    _require_directory_locking()
    try:
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
    except OSError as exc:
        raise OSError(
            "unable to acquire the output-directory transaction lock"
        ) from exc


def _validate_names(files: Mapping[str, str]) -> None:
    if not files:
        raise ValueError("at least one output artifact is required")
    for name, content in files.items():
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("output artifact name must be a plain filename: {0!r}".format(name))
        if not isinstance(content, str):
            raise TypeError("output artifact content must be text: {0}".format(name))


def _open_directory(path: Path) -> Tuple[Path, int]:
    raw = Path(path)
    if ".." in raw.parts:
        raise ValueError("output directory must not contain parent traversal")
    normalized = Path(os.path.normpath(os.fspath(raw)))
    if normalized.is_absolute():
        normalized = _absolute_output_path(normalized)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    if normalized.is_absolute():
        descriptor = os.open(normalized.anchor or os.sep, flags)
        components = normalized.parts[1:]
    else:
        descriptor = os.open(".", flags)
        components = tuple(part for part in normalized.parts if part != ".")
    try:
        for component in components:
            try:
                os.mkdir(component, 0o755, dir_fd=descriptor)
            except FileExistsError:
                pass
            before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise ValueError(
                    "output path component is not a real directory: {0}".format(component)
                )
            child = os.open(component, flags, dir_fd=descriptor)
            try:
                opened = os.fstat(child)
                after = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
                    or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
                ):
                    raise ValueError(
                        "output path component changed while it was opened: {0}".format(
                            component
                        )
                    )
            except BaseException:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
        return _absolute_output_path(normalized), descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _metadata_at(directory_fd: int, name: str) -> Metadata:
    try:
        value = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(value.st_mode):
        raise ValueError("refusing to replace non-regular output artifact: {0}".format(name))
    return value.st_dev, value.st_ino


def _identity_at(directory_fd: int, name: str) -> Metadata:
    try:
        value = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return value.st_dev, value.st_ino


def _rename_at_reconciled(
    directory_fd: int,
    source: str,
    target: str,
    expected: Tuple[int, int],
) -> Optional[BaseException]:
    """Rename and report a post-operation exception after reconciling state."""
    error: Optional[BaseException] = None
    try:
        os.rename(
            source,
            target,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    except BaseException as exc:
        error = exc
    source_after = _identity_at(directory_fd, source)
    target_after = _identity_at(directory_fd, target)
    if source_after is None and target_after == expected:
        return error
    if error is not None:
        raise error
    raise OSError(
        "ambiguous rename outcome during artifact publication: {0} -> {1}".format(
            source, target
        )
    )


def _unique(prefix: str) -> str:
    return ".{0}-{1}".format(prefix, secrets.token_hex(12))


def _stage_at(directory_fd: int, name: str, content: str) -> Tuple[str, Tuple[int, int]]:
    temporary = _unique(name + ".tmp")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        value = os.stat(temporary, dir_fd=directory_fd, follow_symlinks=False)
        return temporary, (value.st_dev, value.st_ino)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        raise


def _unlink_if_same(directory_fd: int, name: str, expected: Tuple[int, int]) -> None:
    try:
        value = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (value.st_dev, value.st_ino) != expected:
        raise OSError("output artifact changed during rollback: {0}".format(name))
    os.unlink(name, dir_fd=directory_fd)


def _publish_at(directory_fd: int, files: Mapping[str, str]) -> None:
    original: Dict[str, Metadata] = {
        name: _metadata_at(directory_fd, name) for name in files
    }
    staged: Dict[str, Tuple[str, Tuple[int, int]]] = {}
    backups: Dict[str, str] = {}
    published: Dict[str, Tuple[int, int]] = {}
    try:
        for name, content in files.items():
            staged[name] = _stage_at(directory_fd, name, content)

        for name, expected in original.items():
            if expected is None:
                if _metadata_at(directory_fd, name) is not None:
                    raise OSError("output artifact appeared during publication: {0}".format(name))
                continue
            if _metadata_at(directory_fd, name) != expected:
                raise OSError("output artifact changed during publication: {0}".format(name))
            backup = _unique(name + ".bak")
            if _identity_at(directory_fd, backup) is not None:
                raise OSError("backup path appeared during publication: {0}".format(backup))
            rename_error = _rename_at_reconciled(
                directory_fd, name, backup, expected
            )
            backups[name] = backup
            if rename_error is not None:
                raise rename_error

        for name, (temporary, identity) in staged.items():
            if _identity_at(directory_fd, name) is not None:
                raise OSError("output artifact appeared during publication: {0}".format(name))
            if _identity_at(directory_fd, temporary) != identity:
                raise OSError("staged output changed during publication: {0}".format(name))
            rename_error = _rename_at_reconciled(
                directory_fd, temporary, name, identity
            )
            published[name] = identity
            staged[name] = ("", identity)
            if rename_error is not None:
                raise rename_error

        os.fsync(directory_fd)
        for backup in backups.values():
            try:
                os.unlink(backup, dir_fd=directory_fd)
            except OSError:
                # Publication is already complete.  A hidden recovery file is
                # safer than turning cleanup trouble into a partial rollback.
                pass
        backups.clear()
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
    except BaseException:
        for name, identity in reversed(list(published.items())):
            _unlink_if_same(directory_fd, name, identity)
        for name, backup in reversed(list(backups.items())):
            os.rename(backup, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        backups.clear()
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
        raise
    finally:
        for temporary, _identity in staged.values():
            if temporary:
                try:
                    os.unlink(temporary, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass


def _fallback_directory(path: Path) -> Path:
    raw = Path(path)
    if ".." in raw.parts:
        raise ValueError("output directory must not contain parent traversal")
    absolute = _absolute_output_path(raw)
    current = Path(absolute.anchor or os.sep)
    for component in absolute.parts[1:]:
        candidate = current / component
        try:
            candidate.mkdir(mode=0o755)
        except FileExistsError:
            pass
        value = candidate.lstat()
        if stat.S_ISLNK(value.st_mode) or not stat.S_ISDIR(value.st_mode):
            raise ValueError("output path must contain only real directories: {0}".format(candidate))
        current = candidate
    return absolute


def _open_fallback_lock_directory(output: Path) -> int:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(os.fspath(output), flags)
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ValueError("output path is not a real directory: {0}".format(output))
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _path_identity(path: Path) -> Metadata:
    try:
        value = path.lstat()
    except FileNotFoundError:
        return None
    return value.st_dev, value.st_ino


def _replace_reconciled(
    source: Path, target: Path, expected: Tuple[int, int]
) -> Optional[BaseException]:
    """Replace and report a post-operation exception after reconciling state."""
    error: Optional[BaseException] = None
    try:
        os.replace(str(source), str(target))
    except BaseException as exc:
        error = exc
    source_after = _path_identity(source)
    target_after = _path_identity(target)
    if source_after is None and target_after == expected:
        return error
    if error is not None:
        raise error
    raise OSError(
        "ambiguous replace outcome during artifact publication: {0} -> {1}".format(
            source, target
        )
    )


def _publish_fallback(output: Path, files: Mapping[str, str]) -> None:
    original: Dict[str, Metadata] = {}
    for name in files:
        target = output / name
        try:
            value = target.lstat()
        except FileNotFoundError:
            original[name] = None
            continue
        if not stat.S_ISREG(value.st_mode):
            raise ValueError("refusing to replace non-regular output artifact: {0}".format(target))
        original[name] = (value.st_dev, value.st_ino)
    staged: Dict[str, Tuple[Optional[Path], Tuple[int, int]]] = {}
    backups: Dict[str, Path] = {}
    published: Dict[str, Tuple[int, int]] = {}
    try:
        for name, content in files.items():
            descriptor, temporary_value = tempfile.mkstemp(prefix=".{0}.tmp-".format(name), dir=str(output))
            temporary = Path(temporary_value)
            staged[name] = (temporary, (-1, -1))
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                    descriptor = -1
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
            except BaseException:
                if descriptor >= 0:
                    os.close(descriptor)
                raise
            value = temporary.lstat()
            staged[name] = (temporary, (value.st_dev, value.st_ino))

        for name, expected in original.items():
            target = output / name
            try:
                value = target.lstat()
                current = (value.st_dev, value.st_ino)
            except FileNotFoundError:
                current = None
            if current != expected:
                raise OSError("output artifact changed during publication: {0}".format(target))
            if expected is not None:
                backup = output / _unique(name + ".bak")
                if _path_identity(backup) is not None:
                    raise OSError(
                        "backup path appeared during publication: {0}".format(backup)
                    )
                replace_error = _replace_reconciled(target, backup, expected)
                backups[name] = backup
                if replace_error is not None:
                    raise replace_error

        for name, (temporary, identity) in staged.items():
            if temporary is None:
                continue
            target = output / name
            if _path_identity(target) is not None:
                raise OSError("output artifact appeared during publication: {0}".format(target))
            if _path_identity(temporary) != identity:
                raise OSError("staged output changed during publication: {0}".format(target))
            replace_error = _replace_reconciled(temporary, target, identity)
            published[name] = identity
            staged[name] = (None, identity)
            if replace_error is not None:
                raise replace_error

        for backup in backups.values():
            try:
                backup.unlink()
            except OSError:
                pass
        backups.clear()
    except BaseException:
        for name, identity in reversed(list(published.items())):
            target = output / name
            try:
                value = target.lstat()
            except FileNotFoundError:
                continue
            if (value.st_dev, value.st_ino) != identity:
                raise OSError("output artifact changed during rollback: {0}".format(target))
            target.unlink()
        for name, backup in reversed(list(backups.items())):
            os.replace(str(backup), str(output / name))
        backups.clear()
        raise
    finally:
        for temporary, _identity in staged.values():
            if temporary is None:
                continue
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def write_text_files(output_dir: Path, files: Mapping[str, str]) -> None:
    """Publish a complete artifact set without following output symlinks."""
    _validate_names(files)
    _require_directory_locking()
    if _descriptor_io_available():
        _absolute, directory_fd = _open_directory(Path(output_dir))
        try:
            _lock_directory(directory_fd)
            _publish_at(directory_fd, files)
        finally:
            os.close(directory_fd)
    else:
        output = _fallback_directory(Path(output_dir))
        directory_fd = _open_fallback_lock_directory(output)
        try:
            _lock_directory(directory_fd)
            _publish_fallback(output, files)
        finally:
            os.close(directory_fd)
