"""Operating-directory resolution for DynosAI Core.

The capability is read-only: it resolves and validates the filesystem directory
DynosAI Core operates on without creating, deleting, or modifying anything, and
without searching parents, inspecting repository/tool markers, or using the
network.
"""

import errno
import os
import pathlib


def resolve_operating_directory(
    directory: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
    """Return the validated operating directory as an absolute resolved path.

    ``directory`` omitted or ``None`` resolves the current working directory of
    this call. An explicit ``str`` or path-like value is resolved against the
    current working directory of this call, with ``.``/``..`` segments and
    redundant separators normalized and symlink/junction indirections followed
    to the platform-resolved target spelling. Shell-style expansion (``~``,
    environment variables) is never performed.

    Raises:
        ValueError: the explicit input's ``os.fspath`` representation is an
            empty or whitespace-only string.
        FileNotFoundError: the resolved path does not exist (errno ``ENOENT``).
        NotADirectoryError: the resolved path exists but is not a directory
            (errno ``ENOTDIR``).

    Filesystem failures carry the offending resolved path in the standard
    ``OSError`` ``filename`` attribute.
    """
    if directory is None:
        candidate = pathlib.Path.cwd()
    else:
        representation = os.fspath(directory)
        if isinstance(representation, str) and not representation.strip():
            raise ValueError(
                "explicit operating directory input is empty or "
                f"whitespace-only: {representation!r}"
            )
        candidate = pathlib.Path(representation)
    resolved = candidate.resolve()
    if not resolved.exists():
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), str(resolved)
        )
    if not resolved.is_dir():
        raise NotADirectoryError(
            errno.ENOTDIR, os.strerror(errno.ENOTDIR), str(resolved)
        )
    return resolved
