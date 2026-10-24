# qr_generator.py
import re
import socket
import sys

import pyqrcode


def _enable_console():
    """Enable UTF-8 and ANSI colors on Windows terminals."""
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
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"


def _visible_len(text: str) -> int:
    return len(re.sub(r"\033\[[0-9;]*m", "", text))


def _box_line(text: str, width: int = 58) -> str:
    inner = f" {text} "
    if _visible_len(inner) > width - 2:
        plain = re.sub(r"\033\[[0-9;]*m", "", inner)
        inner = plain[: width - 5] + "..."
    pad = width - 2 - _visible_len(inner)
    return f"║{inner}{' ' * pad}║"


def _print_banner(title: str, lines: list[str]):
    width = 58
    top = f"╔{'═' * (width - 2)}╗"
    mid = f"╠{'═' * (width - 2)}╣"
    bot = f"╚{'═' * (width - 2)}╝"
    print()
    print(f"{_C.CYAN}{_C.BOLD}{top}{_C.RESET}")
    print(f"{_C.CYAN}{_C.BOLD}{_box_line(title, width)}{_C.RESET}")
    print(f"{_C.CYAN}{mid}{_C.RESET}")
    for line in lines:
        print(f"{_C.WHITE}{_box_line(line, width)}{_C.RESET}")
    print(f"{_C.CYAN}{_C.BOLD}{bot}{_C.RESET}")
    print()


def get_local_ip():
    """Get the local machine's IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def generate_qr(port):
    """Generate a QR code PNG for the server URL."""
    _enable_console()
    ip = get_local_ip()
    url = f"http://{ip}:{port}"
    qr_file = "qrcode.png"

    _print_banner(
        "📡  FILE SHARING — SCAN TO CONNECT",
        [
            f"🌐  Server URL  →  {_C.GREEN}{url}{_C.WHITE}",
            f"💾  QR saved    →  {qr_file}",
            "📱  Open camera on your phone & scan below",
        ],
    )

    qr = pyqrcode.create(url)
    qr.png(qr_file, scale=6)

    print(f"{_C.MAGENTA}{_C.BOLD}  ┌{'─' * 42}┐{_C.RESET}")
    print(f"{_C.MAGENTA}{_C.BOLD}  │{'  Scan this QR code with your phone  ':^42}│{_C.RESET}")
    print(f"{_C.MAGENTA}{_C.BOLD}  └{'─' * 42}┘{_C.RESET}")
    print()
    print(f"{_C.YELLOW}{qr.terminal(quiet_zone=1)}{_C.RESET}")
    print()
    print(f"{_C.DIM}  Tip: Same Wi-Fi required · Press Ctrl+C to stop server{_C.RESET}")
    print()

    return url, qr_file
