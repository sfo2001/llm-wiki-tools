import subprocess
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("llm-wiki-tools")
except PackageNotFoundError:
    __version__ = "dev"


def _get_git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=__file__,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


__git_hash__ = _get_git_hash()
