# utils.py
import os
import re
import sys


def _enable_console():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            kernel32.SetConsoleMode(handle, kernel32.GetConsoleMode(handle) | 0x0004)
        except Exception:
            pass


class _C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"


def _visible_len(text: str) -> int:
    return len(re.sub(r"\033\[[0-9;]*m", "", text))


def get_current_directory():
    """Return the current working directory."""
    return os.getcwd()


def _human_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def list_files():
    """List all files in the current directory."""
    _enable_console()
    cwd = get_current_directory()
    entries = sorted(os.listdir(cwd), key=str.lower)

    width = 62
    print()
    print(f"{_C.CYAN}{_C.BOLD}╔{'═' * (width - 2)}╗{_C.RESET}")
    print(f"{_C.CYAN}{_C.BOLD}║{'  📂  SHARED FILES':<{width - 2}}║{_C.RESET}")
    print(f"{_C.CYAN}╠{'═' * (width - 2)}╣{_C.RESET}")
    print(f"{_C.DIM}║  From: {cwd[: width - 10]:<{width - 10}}║{_C.RESET}")
    print(f"{_C.CYAN}╠{'─' * (width - 2)}╣{_C.RESET}")

    file_count = 0
    folder_count = 0
    for name in entries:
        filepath = os.path.join(cwd, name)
        display = name if len(name) <= 34 else name[:31] + "..."
        if os.path.isdir(filepath):
            folder_count += 1
            row = f"  📁  {_C.BLUE}{display:<34}{_C.RESET}  {'folder':>10}  "
        else:
            file_count += 1
            row = f"  📄  {_C.GREEN}{display:<34}{_C.RESET}  {_human_size(os.path.getsize(filepath)):>10}  "
        pad = width - 2 - _visible_len(row)
        print(f"║{row}{' ' * pad}║")

    print(f"{_C.CYAN}╠{'─' * (width - 2)}╣{_C.RESET}")
    summary = f"  {file_count} file(s) · {folder_count} folder(s)"
    print(f"{_C.DIM}║{summary:<{width - 2}}║{_C.RESET}")
    print(f"{_C.CYAN}{_C.BOLD}╚{'═' * (width - 2)}╝{_C.RESET}")
    print()


def cleanup_qr(qr_file):
    """Remove the QR code image after server stops."""
    _enable_console()
    if os.path.exists(qr_file):
        os.remove(qr_file)
        print()
        print(f"{_C.GREEN}  ✓  Cleaned up {_C.BOLD}{qr_file}{_C.RESET}{_C.GREEN} — server stopped.{_C.RESET}")
        print()
