import os
import re
import socket
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime, timedelta
from tempfile import SpooledTemporaryFile
import tkinter as tk
from tkinter import END, filedialog, messagebox, StringVar, ttk

import queue
import qrcode
from flask import Flask, render_template_string, request, send_file
from PIL import Image, ImageDraw, ImageTk
from werkzeug.serving import make_server
from werkzeug.utils import secure_filename

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
MAX_QR_TEXT_LENGTH = 2000
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024       # 100 MB per file
MAX_TOTAL_SHARE_BYTES = 500 * 1024 * 1024     # 500 MB total per share batch
MAX_MULTI_FILE_COUNT = 50
MIN_MULTI_FILE_CAPABILITY = 5
HOST_FALLBACK = "127.0.0.1"
RECEIVED_FOLDER_NAME = "Received_Files"
EXPIRY_WARNING_SECONDS = 30
DEFAULT_STORAGE_DURATION = "24 hours"
STORAGE_DURATION_OPTIONS = [
    ("5 minutes", 5 * 60),
    ("30 minutes", 30 * 60),
    ("1 hour", 60 * 60),
    ("24 hours", 24 * 60 * 60),
    ("7 days", 7 * 24 * 60 * 60),
    ("Forever / Never delete", None),
]

# Theme Colors: Refined Charcoal, Warm Coral-Orange, and Neutral Gray
COLOR_BG_DARK = "#121214"         # Window base & Sidebar background
COLOR_BG_MAIN = "#16161a"         # Main workspace surface
COLOR_BG_CARD = "#1e1e24"         # Panel & card surface
COLOR_BG_CARD_HOVER = "#262630"   # Interactive surface hover
COLOR_BG_INPUT = "#141418"        # Input fields & text areas
COLOR_BORDER = "#2b2b34"          # Thin neutral border
COLOR_BORDER_LIGHT = "#383846"    # Lighter border for hover/focus
COLOR_CORAL = "#f97316"           # Warm coral-orange accent
COLOR_CORAL_HOVER = "#ea580c"     # Coral hover state
COLOR_CORAL_SUBTLE = "#341f18"    # Coral background tint
COLOR_TEXT_PRIMARY = "#f4f4f6"    # High-contrast primary text
COLOR_TEXT_MUTED = "#9ca3af"      # Neutral secondary text
COLOR_TEXT_DIM = "#6b7280"        # Subdued captions & footnotes
COLOR_GREEN = "#10b981"           # Status online & connected
COLOR_GREEN_BG = "#132b21"        # Green badge background
COLOR_AMBER = "#f59e0b"           # Warning / Expiring
COLOR_RED = "#ef4444"             # Error / Danger
COLOR_RED_BG = "#301717"          # Red badge background

# ==============================================================================
# RESPONSIVE MOBILE TEMPLATES (MATCHING CHARCOAL & WARM CORAL THEME)
# ==============================================================================
UPLOAD_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>QR Share – Send to Laptop</title>
  <style>
    :root {
      --bg: #121214;
      --card: #1e1e24;
      --border: #2b2b34;
      --coral: #f97316;
      --coral-hover: #ea580c;
      --text: #f4f4f6;
      --muted: #9ca3af;
      --green: #10b981;
      --green-bg: #132b21;
      --red: #ef4444;
      --red-bg: #301717;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }
    .card {
      width: min(540px, 100%);
      background: var(--card);
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--green-bg);
      color: var(--green);
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    .badge-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--green);
    }
    h1 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 700;
    }
    p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.9rem;
    }
    .section {
      background: #15151a;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 14px;
    }
    .section-title {
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 8px;
    }
    input[type="file"], textarea {
      width: 100%;
      background: #111114;
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
      padding: 10px;
      font-size: 0.95rem;
      outline: none;
      transition: border-color 0.2s;
    }
    input[type="file"]:focus, textarea:focus {
      border-color: var(--coral);
    }
    textarea {
      min-height: 100px;
      resize: vertical;
      font-family: inherit;
    }
    .btn {
      width: 100%;
      border: none;
      border-radius: 8px;
      padding: 14px;
      background: var(--coral);
      color: #ffffff;
      font-weight: 700;
      font-size: 1rem;
      cursor: pointer;
      transition: background 0.2s, transform 0.1s;
    }
    .btn:hover { background: var(--coral-hover); }
    .btn:active { transform: scale(0.99); }
    .msg {
      margin-bottom: 16px;
      padding: 12px 14px;
      border-radius: 8px;
      font-size: 0.92rem;
    }
    .msg.ok {
      background: var(--green-bg);
      color: var(--green);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .msg.err {
      background: var(--red-bg);
      color: var(--red);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .hint {
      font-size: 0.8rem;
      color: var(--muted);
      margin-top: 6px;
    }
  </style>
</head>
<body>
  <main class="card">
    <div class="header">
      <div>
        <h1>Send to Laptop</h1>
        <p>Connected to Laptop Wi-Fi Network</p>
      </div>
      <div style="margin-left: auto;">
        <span class="badge"><span class="badge-dot"></span> Ready</span>
      </div>
    </div>

    {% if message %}
      <div class="msg {{ 'ok' if success else 'err' }}">{{ message }}</div>
    {% endif %}

    <form method="post" enctype="multipart/form-data">
      <section class="section">
        <div class="section-title">Upload File(s) to Laptop</div>
        <input type="file" name="upload_files" multiple>
        <div class="hint">Multi-file supported. Up to 100 MB per file.</div>
      </section>

      <section class="section">
        <div class="section-title">Send Quick Text or Note</div>
        <textarea name="note_text" placeholder="Type or paste text, links, or notes here..."></textarea>
      </section>

      <button class="btn" type="submit">Upload to Laptop</button>
    </form>
  </main>
</body>
</html>
"""

MULTI_DOWNLOAD_LANDING_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>QR Share – Shared Files</title>
  <style>
    :root {
      --bg: #121214;
      --card: #1e1e24;
      --border: #2b2b34;
      --coral: #f97316;
      --coral-hover: #ea580c;
      --text: #f4f4f6;
      --muted: #9ca3af;
      --green: #10b981;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 16px;
    }
    .card {
      max-width: 580px;
      margin: 20px auto;
      background: var(--card);
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 14px;
    }
    h1 { margin: 0; font-size: 1.25rem; font-weight: 700; }
    .meta { color: var(--muted); font-size: 0.9rem; }
    .btn-all {
      display: block;
      width: 100%;
      text-align: center;
      margin: 16px 0;
      padding: 13px;
      background: var(--coral);
      color: #ffffff !important;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.96rem;
      border: none;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-all:hover { background: var(--coral-hover); }
    ul { list-style: none; padding: 0; margin: 0; }
    li {
      background: #15151a;
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 8px;
      padding: 12px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .file-info { overflow: hidden; }
    .fname {
      display: block;
      font-weight: 600;
      font-size: 0.94rem;
      word-break: break-all;
    }
    .size {
      color: var(--muted);
      font-size: 0.82rem;
      margin-top: 2px;
    }
    .btn-dl {
      flex-shrink: 0;
      padding: 8px 14px;
      background: #2a2a34;
      color: var(--text) !important;
      text-decoration: none;
      border-radius: 6px;
      font-size: 0.88rem;
      font-weight: 600;
      border: 1px solid var(--border);
      transition: background 0.15s;
    }
    .btn-dl:hover { background: #343442; color: var(--coral) !important; }
  </style>
</head>
<body>
  <main class="card">
    <div class="header">
      <div>
        <h1>Shared from Laptop</h1>
        <div class="meta">{{ file_count }} file(s) ready · {{ total_size_human }}</div>
      </div>
    </div>
    
    <a class="btn-all" href="/download_all">⬇ Download All as ZIP Archive</a>

    <ul>
      {% for item in files %}
      <li>
        <div class="file-info">
          <span class="fname">{{ item.name }}</span>
          <span class="size">{{ item.size_human }}</span>
        </div>
        <a class="btn-dl" href="/download/{{ item.id }}">Download</a>
      </li>
      {% endfor %}
    </ul>
  </main>
</body>
</html>
"""

# ==============================================================================
# NETWORK & SYSTEM UTILITIES
# ==============================================================================
def get_local_ip() -> str:
    """Retrieve local machine's primary LAN IP address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return HOST_FALLBACK
    finally:
        sock.close()

def get_wifi_ssid() -> str:
    """Extract connected Wi-Fi network SSID on Windows; fallback safely."""
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True, stderr=subprocess.DEVNULL)
            match = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
            if match:
                ssid = match.group(1).strip()
                if ssid:
                    return ssid
    except Exception:
        pass
    return "Local Wi-Fi Network"

def looks_like_lan_ip(ip: str) -> bool:
    return ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172.")

def human_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"

def determine_file_category(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"]:
        return "Image"
    if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        return "Video"
    if ext in [".pdf"]:
        return "PDF"
    if ext in [".txt", ".md", ".log", ".json", ".xml", ".csv"]:
        return "Note / Text"
    if ext in [".zip", ".tar", ".gz", ".7z", ".rar"]:
        return "Archive"
    if ext in [".py", ".js", ".html", ".css", ".cpp", ".java"]:
        return "Code"
    return "File"

# ==============================================================================
# MAIN APPLICATION CLASS
# ==============================================================================
class QRShareApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QR Share – Laptop & Mobile")
        self.root.geometry("1100x780")
        self.root.minsize(980, 680)
        self.root.configure(bg=COLOR_BG_DARK)

        # Core State Variables
        self.current_nav = "share"
        self.mode = StringVar(value="send")          # "send" (Laptop to Mobile) or "receive"
        self.data_type = StringVar(value="file")      # "text", "code", "link", "file"
        self.shared_files = []                        # List of absolute file paths to share
        self.send_status_by_path = {}                 # File status mapping
        self.storage_duration = StringVar(value=DEFAULT_STORAGE_DURATION)
        self.last_activity_text = StringVar(value="Idle")
        
        # Server & Network State
        self.flask_server = None
        self.server_thread = None
        self.server_ip = get_local_ip()
        self.server_port = 8010
        self.wifi_ssid = get_wifi_ssid()
        self.current_qr_payload = ""
        self.current_qr_photo = None
        
        # Received Files State
        self.received_dir = self._ensure_received_folder()
        self.received_items = []
        self.received_item_counter = 0
        self.received_queue = queue.Queue()
        self.cleanup_job = None

        # Build UI Architecture
        self._setup_styles()
        self._build_layout()
        
        # Initial Population & Timers
        self._load_existing_received_files()
        self._refresh_metrics()
        self._schedule_cleanup_cycle()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --------------------------------------------------------------------------
    # STYLES & ASSETS
    # --------------------------------------------------------------------------
    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Treeview Styling
        self.style.configure(
            "Dark.Treeview",
            background="#16161b",
            foreground=COLOR_TEXT_PRIMARY,
            fieldbackground="#16161b",
            rowheight=28,
            font=("Segoe UI", 9),
            borderwidth=0,
        )
        self.style.configure(
            "Dark.Treeview.Heading",
            background="#202028",
            foreground=COLOR_TEXT_MUTED,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padding=(6, 6),
        )
        self.style.map("Dark.Treeview.Heading", background=[("active", "#282832")])
        self.style.map(
            "Dark.Treeview",
            background=[("selected", COLOR_CORAL)],
            foreground=[("selected", "#ffffff")],
        )

        # Combobox Styling
        self.style.configure(
            "Dark.TCombobox",
            fieldbackground=COLOR_BG_CARD,
            background="#262630",
            foreground=COLOR_TEXT_PRIMARY,
            arrowcolor=COLOR_CORAL,
            bordercolor=COLOR_BORDER,
            darkcolor=COLOR_BORDER,
            lightcolor=COLOR_BORDER,
            padding=4,
        )
        self.root.option_add("*TCombobox*Listbox.background", COLOR_BG_CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", COLOR_TEXT_PRIMARY)
        self.root.option_add("*TCombobox*Listbox.selectBackground", COLOR_CORAL)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

        # Scrollbar Styling
        self.style.configure(
            "Dark.Vertical.TScrollbar",
            background="#262630",
            troughcolor=COLOR_BG_DARK,
            bordercolor=COLOR_BORDER,
            arrowcolor=COLOR_TEXT_MUTED,
            relief="flat",
        )

    def _create_app_icon(self) -> ImageTk.PhotoImage:
        """Create a clean 32x32 rounded emblem icon with warm coral accent."""
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Rounded charcoal base
        draw.rounded_rectangle([0, 0, 31, 31], radius=7, fill="#202028", outline="#343442", width=1)
        # Warm coral center QR emblem
        draw.rectangle([7, 7, 13, 13], fill=COLOR_CORAL)
        draw.rectangle([9, 9, 11, 11], fill="#202028")
        draw.rectangle([18, 7, 24, 13], fill=COLOR_CORAL)
        draw.rectangle([20, 9, 22, 11], fill="#202028")
        draw.rectangle([7, 18, 13, 24], fill=COLOR_CORAL)
        draw.rectangle([9, 20, 11, 22], fill="#202028")
        draw.rectangle([17, 17, 24, 24], fill=COLOR_CORAL)
        return ImageTk.PhotoImage(img)

    # --------------------------------------------------------------------------
    # LAYOUT ASSEMBLY
    # --------------------------------------------------------------------------
    def _build_layout(self):
        # 1. Top Bar
        self._build_top_bar()

        # 2. Bottom Status Bar
        self._build_bottom_bar()

        # 3. Main Body Frame (Left Sidebar + Center Workspace)
        self.body_frame = tk.Frame(self.root, bg=COLOR_BG_DARK)
        self.body_frame.pack(side="top", fill="both", expand=True)

        self._build_sidebar()
        self._build_workspace()

    # --------------------------------------------------------------------------
    # 1. TOP BAR
    # --------------------------------------------------------------------------
    def _build_top_bar(self):
        self.top_bar = tk.Frame(self.root, bg="#151518", height=52, bd=0)
        self.top_bar.pack(side="top", fill="x")
        self.top_bar.pack_propagate(False)

        # Thin bottom divider line
        divider = tk.Frame(self.root, bg=COLOR_BORDER, height=1)
        divider.pack(side="top", fill="x")

        # Left: App Logo + Title + Badge
        left_box = tk.Frame(self.top_bar, bg="#151518")
        left_box.pack(side="left", fill="y", padx=16)

        self.app_logo_img = self._create_app_icon()
        logo_lbl = tk.Label(left_box, image=self.app_logo_img, bg="#151518")
        logo_lbl.pack(side="left", pady=10)

        title_lbl = tk.Label(
            left_box,
            text="QR Share",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg="#151518",
        )
        title_lbl.pack(side="left", padx=(10, 4))

        subtitle_lbl = tk.Label(
            left_box,
            text="– Laptop & Mobile",
            font=("Segoe UI", 11),
            fg=COLOR_TEXT_MUTED,
            bg="#151518",
        )
        subtitle_lbl.pack(side="left")

        tag_lbl = tk.Label(
            left_box,
            text="v2.0",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_CORAL,
            bg=COLOR_CORAL_SUBTLE,
            padx=6,
            pady=1,
            relief="flat",
        )
        tag_lbl.pack(side="left", padx=(10, 0))

        # Right: Wi-Fi Status, Network Name, IP Address, Refresh Button
        right_box = tk.Frame(self.top_bar, bg="#151518")
        right_box.pack(side="right", fill="y", padx=16)

        # Wi-Fi Online Pill
        wifi_pill = tk.Frame(right_box, bg=COLOR_GREEN_BG, padx=8, pady=3, highlightbackground="#1b4533", highlightthickness=1)
        wifi_pill.pack(side="left", pady=12, padx=4)

        dot_canvas = tk.Canvas(wifi_pill, width=8, height=8, bg=COLOR_GREEN_BG, highlightthickness=0)
        dot_canvas.pack(side="left", padx=(0, 5))
        dot_canvas.create_oval(1, 1, 7, 7, fill=COLOR_GREEN, outline="")

        tk.Label(
            wifi_pill,
            text="Wi-Fi Online",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_GREEN,
            bg=COLOR_GREEN_BG,
        ).pack(side="left")

        # Network SSID Pill
        self.ssid_var = StringVar(value=f"Network: {self.wifi_ssid}")
        ssid_pill = tk.Frame(right_box, bg="#1e1e24", padx=10, pady=3, highlightbackground=COLOR_BORDER, highlightthickness=1)
        ssid_pill.pack(side="left", pady=12, padx=4)

        tk.Label(
            ssid_pill,
            textvariable=self.ssid_var,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_PRIMARY,
            bg="#1e1e24",
        ).pack(side="left")

        # IP Pill
        self.ip_display_var = StringVar(value=f"IP: {self.server_ip}")
        ip_pill = tk.Frame(right_box, bg="#1e1e24", padx=10, pady=3, highlightbackground=COLOR_BORDER, highlightthickness=1)
        ip_pill.pack(side="left", pady=12, padx=4)

        tk.Label(
            ip_pill,
            textvariable=self.ip_display_var,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg="#1e1e24",
        ).pack(side="left")

        # Refresh Network Button
        refresh_btn = tk.Button(
            right_box,
            text="↻",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg="#1e1e24",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_CORAL,
            relief="flat",
            bd=0,
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.refresh_network_status,
        )
        refresh_btn.pack(side="left", pady=12, padx=(2, 0))

    # --------------------------------------------------------------------------
    # 2. LEFT SIDEBAR
    # --------------------------------------------------------------------------
    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.body_frame, bg=COLOR_BG_DARK, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Right border divider
        side_divider = tk.Frame(self.body_frame, bg=COLOR_BORDER, width=1)
        side_divider.pack(side="left", fill="y")

        # Sidebar Title Section
        tk.Label(
            self.sidebar,
            text="NAVIGATION",
            font=("Segoe UI", 7, "bold"),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_DARK,
        ).pack(anchor="w", padx=18, pady=(20, 8))

        # Nav Buttons
        self.nav_buttons = {}
        items = [
            ("share", "⬚  QR Data Share"),
            ("receive", "📥  Receive (Upload)"),
            ("files", "🗂  Received Files"),
            ("folder", "📂  Open Folder"),
            ("settings", "⚙  Settings"),
        ]

        for view_key, label_text in items:
            btn = tk.Button(
                self.sidebar,
                text=label_text,
                font=("Segoe UI", 9, "bold" if view_key == "share" else "normal"),
                fg=COLOR_CORAL if view_key == "share" else COLOR_TEXT_MUTED,
                bg="#1c1c24" if view_key == "share" else COLOR_BG_DARK,
                activebackground="#22222c",
                activeforeground=COLOR_CORAL,
                relief="flat",
                bd=0,
                anchor="w",
                padx=16,
                pady=10,
                cursor="hand2",
                command=lambda k=view_key: self.navigate_to(k),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[view_key] = btn

        # Sidebar Bottom Card
        bottom_card = tk.Frame(self.sidebar, bg=COLOR_BG_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        bottom_card.pack(side="bottom", fill="x", padx=10, pady=14)

        tk.Label(
            bottom_card,
            text="SYSTEM READY",
            font=("Segoe UI", 7, "bold"),
            fg=COLOR_GREEN,
            bg=COLOR_BG_CARD,
        ).pack(anchor="w", padx=10, pady=(10, 2))

        tk.Label(
            bottom_card,
            text="Fast P2P Transfer\nNo cloud or internet needed",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 10))

    def navigate_to(self, view_key: str):
        if view_key == "folder":
            self.open_received_folder()
            return
        elif view_key == "settings":
            self.open_settings_dialog()
            return

        self.current_nav = view_key
        # Update Nav buttons visuals
        for k, btn in self.nav_buttons.items():
            if k == view_key:
                btn.configure(fg=COLOR_CORAL, bg="#1c1c24", font=("Segoe UI", 9, "bold"))
            elif k not in ("folder", "settings"):
                btn.configure(fg=COLOR_TEXT_MUTED, bg=COLOR_BG_DARK, font=("Segoe UI", 9, "normal"))

        if view_key == "share":
            self.mode.set("send")
            self.on_mode_change()
            self.files_manager_view.pack_forget()
            self.main_sharing_view.pack(fill="both", expand=True)
        elif view_key == "receive":
            self.mode.set("receive")
            self.on_mode_change()
            self.files_manager_view.pack_forget()
            self.main_sharing_view.pack(fill="both", expand=True)
        elif view_key == "files":
            self.main_sharing_view.pack_forget()
            self.files_manager_view.pack(fill="both", expand=True)
            self._reload_files_manager_view()

    # --------------------------------------------------------------------------
    # 3. MAIN WORKSPACE
    # --------------------------------------------------------------------------
    def _build_workspace(self):
        self.workspace = tk.Frame(self.body_frame, bg=COLOR_BG_MAIN)
        self.workspace.pack(side="left", fill="both", expand=True)

        # Header Title & Description
        header_box = tk.Frame(self.workspace, bg=COLOR_BG_MAIN)
        header_box.pack(fill="x", padx=24, pady=(18, 12))

        self.view_title_lbl = tk.Label(
            header_box,
            text="QR Data Share",
            font=("Segoe UI", 16, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_BG_MAIN,
        )
        self.view_title_lbl.pack(anchor="w")

        self.view_desc_lbl = tk.Label(
            header_box,
            text="Transfer files, text notes, and links seamlessly between laptop and mobile on your local Wi-Fi.",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_MAIN,
        )
        self.view_desc_lbl.pack(anchor="w", pady=(2, 0))

        # Metrics / Stat Chips Banner
        self._build_metric_cards()

        # Content Views Container
        self.content_container = tk.Frame(self.workspace, bg=COLOR_BG_MAIN)
        self.content_container.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # 1. Main Sharing View (Default)
        self.main_sharing_view = tk.Frame(self.content_container, bg=COLOR_BG_MAIN)
        self.main_sharing_view.pack(fill="both", expand=True)

        # 2. Dedicated Received Files Manager View (Toggled via Sidebar)
        self.files_manager_view = tk.Frame(self.content_container, bg=COLOR_BG_MAIN)

        self._build_sharing_panes()
        self._build_files_manager_view()

    def _build_metric_cards(self):
        metrics_frame = tk.Frame(self.workspace, bg=COLOR_BG_MAIN)
        metrics_frame.pack(fill="x", padx=24, pady=(0, 14))

        self.metric_selected_count = StringVar(value="0 files")
        self.metric_selected_size = StringVar(value="0 B")
        self.metric_received_count = StringVar(value="0 files")

        cards_data = [
            ("Selected Files", self.metric_selected_count, "Ready to send"),
            ("Total File Size", self.metric_selected_size, "Current batch"),
            ("Received Files", self.metric_received_count, "Saved on laptop"),
            ("Last Activity", self.last_activity_text, "Event status"),
        ]

        for i, (title, var, subtitle) in enumerate(cards_data):
            card = tk.Frame(
                metrics_frame,
                bg=COLOR_BG_CARD,
                highlightbackground=COLOR_BORDER,
                highlightthickness=1,
            )
            card.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else 8, 0))

            tk.Label(
                card,
                text=title.upper(),
                font=("Segoe UI", 7, "bold"),
                fg=COLOR_TEXT_DIM,
                bg=COLOR_BG_CARD,
            ).pack(anchor="w", padx=14, pady=(10, 2))

            tk.Label(
                card,
                textvariable=var,
                font=("Segoe UI", 13, "bold"),
                fg=COLOR_TEXT_PRIMARY if i != 3 else COLOR_CORAL,
                bg=COLOR_BG_CARD,
            ).pack(anchor="w", padx=14)

            tk.Label(
                card,
                text=subtitle,
                font=("Segoe UI", 8),
                fg=COLOR_TEXT_DIM,
                bg=COLOR_BG_CARD,
            ).pack(anchor="w", padx=14, pady=(0, 10))

    # --------------------------------------------------------------------------
    # 4. SHARING PANES (LEFT CONTROLS + RIGHT QR PREVIEW)
    # --------------------------------------------------------------------------
    def _build_sharing_panes(self):
        # Top Split Area (Left Inputs & Controls, Right QR Panel)
        top_split = tk.Frame(self.main_sharing_view, bg=COLOR_BG_MAIN)
        top_split.pack(fill="both", expand=True)

        # ------------------- LEFT PANE: CONTROLS & INPUT -------------------
        self.left_pane = tk.Frame(
            top_split,
            bg=COLOR_BG_CARD,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )
        self.left_pane.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # Mode Selector & Duration Controls Row
        controls_top = tk.Frame(self.left_pane, bg=COLOR_BG_CARD)
        controls_top.pack(fill="x", padx=18, pady=(16, 12))

        # Mode Pill Switcher
        mode_box = tk.Frame(controls_top, bg="#15151a", highlightbackground=COLOR_BORDER, highlightthickness=1)
        mode_box.pack(side="left")

        self.btn_mode_send = tk.Button(
            mode_box,
            text="💻 Laptop to Mobile",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg=COLOR_CORAL,
            activebackground=COLOR_CORAL_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: self._set_mode("send"),
        )
        self.btn_mode_send.pack(side="left")

        self.btn_mode_receive = tk.Button(
            mode_box,
            text="📱 Receive from Mobile",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg="#15151a",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_CORAL,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: self._set_mode("receive"),
        )
        self.btn_mode_receive.pack(side="left")

        # Storage Duration Picker on Right
        duration_box = tk.Frame(controls_top, bg=COLOR_BG_CARD)
        duration_box.pack(side="right")

        tk.Label(
            duration_box,
            text="Retention:",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
        ).pack(side="left", padx=(0, 6))

        self.duration_combo = ttk.Combobox(
            duration_box,
            textvariable=self.storage_duration,
            values=[opt[0] for opt in STORAGE_DURATION_OPTIONS],
            width=18,
            state="readonly",
            style="Dark.TCombobox",
        )
        self.duration_combo.pack(side="left")
        self.duration_combo.bind("<<ComboboxSelected>>", self.on_storage_duration_change)

        # Container for Send Controls
        self.send_controls_container = tk.Frame(self.left_pane, bg=COLOR_BG_CARD)
        self.send_controls_container.pack(fill="both", expand=True, padx=18)

        # Data Type Selector
        type_row = tk.Frame(self.send_controls_container, bg=COLOR_BG_CARD)
        type_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            type_row,
            text="Share Type:",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_BG_CARD,
        ).pack(side="left", padx=(0, 10))

        self.type_buttons = {}
        for label, val in [("File(s)", "file"), ("Plain Text", "text"), ("Code", "code"), ("Link/URL", "link")]:
            btn = tk.Button(
                type_row,
                text=label,
                font=("Segoe UI", 8, "bold" if val == self.data_type.get() else "normal"),
                fg="#ffffff" if val == self.data_type.get() else COLOR_TEXT_MUTED,
                bg=COLOR_CORAL if val == self.data_type.get() else "#15151a",
                activebackground=COLOR_BG_CARD_HOVER,
                activeforeground=COLOR_CORAL,
                relief="flat",
                bd=0,
                padx=10,
                pady=4,
                cursor="hand2",
                command=lambda v=val: self._set_data_type(v),
            )
            btn.pack(side="left", padx=3)
            self.type_buttons[val] = btn

        # Dynamic Input Views (Files vs Text/Code/URL)
        self.input_card = tk.Frame(self.send_controls_container, bg=COLOR_BG_CARD)
        self.input_card.pack(fill="both", expand=True)

        # VIEW A: Text / Code / Link Input
        self.text_input_frame = tk.Frame(self.input_card, bg=COLOR_BG_CARD)
        
        self.text_counter_var = StringVar(value="0 / 2000 chars")
        text_header = tk.Frame(self.text_input_frame, bg=COLOR_BG_CARD)
        text_header.pack(fill="x", pady=(0, 4))
        
        tk.Label(
            text_header,
            text="Enter content to encode into QR code:",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
        ).pack(side="left")
        
        tk.Label(
            text_header,
            textvariable=self.text_counter_var,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
        ).pack(side="right")

        self.text_input = tk.Text(
            self.text_input_frame,
            bg=COLOR_BG_INPUT,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_CORAL,
            font=("Segoe UI", 9),
            height=6,
            bd=0,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_BORDER_LIGHT,
            highlightthickness=1,
            padx=10,
            pady=8,
            wrap="word",
        )
        self.text_input.pack(fill="both", expand=True)
        self.text_input.bind("<KeyRelease>", self._on_text_change)

        # VIEW B: Multi-File Input List
        self.file_input_frame = tk.Frame(self.input_card, bg=COLOR_BG_CARD)

        file_action_row = tk.Frame(self.file_input_frame, bg=COLOR_BG_CARD)
        file_action_row.pack(fill="x", pady=(0, 8))

        btn_choose = tk.Button(
            file_action_row,
            text="📁 Choose File(s)...",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#2a2a34",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_CORAL,
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.select_files,
        )
        btn_choose.pack(side="left")

        btn_remove_file = tk.Button(
            file_action_row,
            text="✖ Remove Selected",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg="#18181f",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_RED,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.remove_selected_shared_file,
        )
        btn_remove_file.pack(side="left", padx=8)

        btn_clear_files = tk.Button(
            file_action_row,
            text="Clear All",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg="#18181f",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=8,
            pady=5,
            cursor="hand2",
            command=self.clear_shared_files,
        )
        btn_clear_files.pack(side="left")

        self.file_list_count_var = StringVar(value="0 files selected")
        tk.Label(
            file_action_row,
            textvariable=self.file_list_count_var,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_CARD,
        ).pack(side="right")

        # Files Treeview
        tree_container = tk.Frame(self.file_input_frame, bg=COLOR_BG_CARD)
        tree_container.pack(fill="both", expand=True)

        self.files_tree = ttk.Treeview(
            tree_container,
            columns=("name", "size", "status"),
            show="headings",
            height=5,
            style="Dark.Treeview",
        )
        self.files_tree.heading("name", text="File Name")
        self.files_tree.heading("size", text="Size")
        self.files_tree.heading("status", text="Status")
        self.files_tree.column("name", width=240, anchor="w")
        self.files_tree.column("size", width=80, anchor="e")
        self.files_tree.column("status", width=90, anchor="center")

        ft_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.files_tree.yview, style="Dark.Vertical.TScrollbar")
        self.files_tree.configure(yscrollcommand=ft_scroll.set)
        self.files_tree.pack(side="left", fill="both", expand=True)
        ft_scroll.pack(side="right", fill="y")

        # Container for Receive Controls
        self.receive_info_container = tk.Frame(self.left_pane, bg=COLOR_BG_CARD)
        
        recv_box = tk.Frame(self.receive_info_container, bg="#16161c", highlightbackground=COLOR_BORDER, highlightthickness=1)
        recv_box.pack(fill="both", expand=True, pady=8)

        tk.Label(
            recv_box,
            text="Receive Files & Notes from Mobile",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_CORAL,
            bg="#16161c",
        ).pack(anchor="w", padx=16, pady=(14, 4))

        instructions = (
            "1. Click 'Start Receive Server' below to generate your connection QR.\n"
            "2. Scan the QR code using your phone's camera or QR reader.\n"
            "3. Your mobile browser opens a direct upload page to send files & notes.\n"
            "4. Uploaded items are saved automatically into your 'Received_Files' folder."
        )
        tk.Label(
            recv_box,
            text=instructions,
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg="#16161c",
            justify="left",
            pady=4,
        ).pack(anchor="w", padx=16)

        # Show initial input view
        self.file_input_frame.pack(fill="both", expand=True)

        # Action Buttons Row
        action_bar = tk.Frame(self.left_pane, bg=COLOR_BG_CARD)
        action_bar.pack(fill="x", padx=18, pady=(12, 16))

        self.main_action_btn = tk.Button(
            action_bar,
            text="⚡ Generate QR Code",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=COLOR_CORAL,
            activebackground=COLOR_CORAL_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.generate_qr_action,
        )
        self.main_action_btn.pack(side="left")

        btn_clear_all = tk.Button(
            action_bar,
            text="Clear All",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg="#24242e",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.clear_all,
        )
        btn_clear_all.pack(side="left", padx=8)

        # ------------------- RIGHT PANE: QR PREVIEW -------------------
        self.right_pane = tk.Frame(
            top_split,
            bg=COLOR_BG_CARD,
            width=360,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )
        self.right_pane.pack(side="right", fill="both")
        self.right_pane.pack_propagate(False)

        qr_header = tk.Frame(self.right_pane, bg=COLOR_BG_CARD)
        qr_header.pack(fill="x", padx=18, pady=(16, 8))

        tk.Label(
            qr_header,
            text="QR Code Preview",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_BG_CARD,
        ).pack(anchor="w")

        tk.Label(
            qr_header,
            text="Scan with mobile camera to connect",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
        ).pack(anchor="w")

        # White Rounded Quiet-Zone Card for Crisp QR Scanning
        self.qr_card = tk.Frame(
            self.right_pane,
            bg="#ffffff",
            width=250,
            height=250,
            highlightbackground="#e5e7eb",
            highlightthickness=1,
        )
        self.qr_card.pack(pady=10)
        self.qr_card.pack_propagate(False)

        self.qr_canvas = tk.Label(
            self.qr_card,
            text="QR Preview\n\nClick 'Generate QR' or\n'Start Receive Server'",
            font=("Segoe UI", 9),
            fg="#6b7280",
            bg="#ffffff",
            justify="center",
        )
        self.qr_canvas.pack(fill="both", expand=True)

        # QR Payload / URL Display Box
        self.payload_var = StringVar(value="No active server or data")
        payload_box = tk.Frame(self.right_pane, bg="#141418", highlightbackground=COLOR_BORDER, highlightthickness=1)
        payload_box.pack(fill="x", padx=18, pady=6)

        tk.Label(
            payload_box,
            textvariable=self.payload_var,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg="#141418",
            padx=8,
            pady=6,
        ).pack(fill="x")

        # QR Actions: Download QR, Copy URL, Open Browser
        qr_btn_row = tk.Frame(self.right_pane, bg=COLOR_BG_CARD)
        qr_btn_row.pack(fill="x", padx=18, pady=(8, 12))

        self.btn_download_qr = tk.Button(
            qr_btn_row,
            text="💾 Download QR",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg="#2a2a34",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_CORAL,
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self.download_qr_image,
        )
        self.btn_download_qr.pack(side="left")

        self.btn_copy_url = tk.Button(
            qr_btn_row,
            text="📋 Copy URL",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg="#24242e",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self.copy_server_url,
        )
        self.btn_copy_url.pack(side="left", padx=6)

        self.btn_open_browser = tk.Button(
            qr_btn_row,
            text="🌐 Open",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg="#24242e",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self.open_in_browser,
        )
        self.btn_open_browser.pack(side="left")

        # ------------------- BOTTOM SECTION: RECENT ACTIVITY -------------------
        bottom_activity = tk.Frame(
            self.main_sharing_view,
            bg=COLOR_BG_CARD,
            height=180,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )
        bottom_activity.pack(side="bottom", fill="x", pady=(12, 0))
        bottom_activity.pack_propagate(False)

        act_header = tk.Frame(bottom_activity, bg=COLOR_BG_CARD)
        act_header.pack(fill="x", padx=16, pady=(10, 6))

        tk.Label(
            act_header,
            text="Recent Received Files & Activity",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_BG_CARD,
        ).pack(side="left")

        tk.Button(
            act_header,
            text="📂 Open Folder",
            font=("Segoe UI", 8),
            fg=COLOR_CORAL,
            bg=COLOR_BG_CARD,
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_CORAL,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.open_received_folder,
        ).pack(side="right")

        tk.Button(
            act_header,
            text="View All In Full Manager →",
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda: self.navigate_to("files"),
        ).pack(side="right", padx=12)

        # Embedded Recent Activity Table
        act_table_frame = tk.Frame(bottom_activity, bg=COLOR_BG_CARD)
        act_table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.activity_tree = ttk.Treeview(
            act_table_frame,
            columns=("name", "type", "size", "received", "status"),
            show="headings",
            height=4,
            style="Dark.Treeview",
        )
        self.activity_tree.heading("name", text="File Name")
        self.activity_tree.heading("type", text="Type")
        self.activity_tree.heading("size", text="Size")
        self.activity_tree.heading("received", text="Received At")
        self.activity_tree.heading("status", text="Status / Retention")

        self.activity_tree.column("name", width=220, anchor="w")
        self.activity_tree.column("type", width=80, anchor="center")
        self.activity_tree.column("size", width=80, anchor="e")
        self.activity_tree.column("received", width=140, anchor="center")
        self.activity_tree.column("status", width=120, anchor="w")

        act_scroll = ttk.Scrollbar(act_table_frame, orient="vertical", command=self.activity_tree.yview, style="Dark.Vertical.TScrollbar")
        self.activity_tree.configure(yscrollcommand=act_scroll.set)
        self.activity_tree.pack(side="left", fill="both", expand=True)
        act_scroll.pack(side="right", fill="y")
        self.activity_tree.bind("<Double-1>", self._on_activity_double_click)

    # --------------------------------------------------------------------------
    # 5. DEDICATED FULL RECEIVED FILES MANAGER VIEW
    # --------------------------------------------------------------------------
    def _build_files_manager_view(self):
        container = tk.Frame(self.files_manager_view, bg=COLOR_BG_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        container.pack(fill="both", expand=True)

        toolbar = tk.Frame(container, bg=COLOR_BG_CARD)
        toolbar.pack(fill="x", padx=18, pady=(16, 10))

        tk.Label(
            toolbar,
            text="Received Files & Storage Directory",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_BG_CARD,
        ).pack(side="left")

        # Action Buttons
        btn_open = tk.Button(
            toolbar,
            text="📂 Open File",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg=COLOR_CORAL,
            activebackground=COLOR_CORAL_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.open_selected_received_file,
        )
        btn_open.pack(side="right", padx=(6, 0))

        btn_show = tk.Button(
            toolbar,
            text="📁 Show in Explorer",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_PRIMARY,
            bg="#2a2a34",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_CORAL,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.open_received_folder,
        )
        btn_show.pack(side="right", padx=6)

        btn_delete = tk.Button(
            toolbar,
            text="🗑 Delete File",
            font=("Segoe UI", 9),
            fg=COLOR_RED,
            bg="#281717",
            activebackground="#341a1a",
            activeforeground=COLOR_RED,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.delete_selected_received_file,
        )
        btn_delete.pack(side="right", padx=6)

        btn_refresh = tk.Button(
            toolbar,
            text="↻ Refresh",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg="#24242e",
            activebackground=COLOR_BG_CARD_HOVER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._load_existing_received_files,
        )
        btn_refresh.pack(side="right", padx=6)

        # Full Treeview
        tree_box = tk.Frame(container, bg=COLOR_BG_CARD)
        tree_box.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        self.full_files_tree = ttk.Treeview(
            tree_box,
            columns=("name", "type", "size", "received", "expires", "status"),
            show="headings",
            style="Dark.Treeview",
        )
        self.full_files_tree.heading("name", text="File Name")
        self.full_files_tree.heading("type", text="Type")
        self.full_files_tree.heading("size", text="Size")
        self.full_files_tree.heading("received", text="Received At")
        self.full_files_tree.heading("expires", text="Retention Expiry")
        self.full_files_tree.heading("status", text="Status")

        self.full_files_tree.column("name", width=280, anchor="w")
        self.full_files_tree.column("type", width=90, anchor="center")
        self.full_files_tree.column("size", width=90, anchor="e")
        self.full_files_tree.column("received", width=140, anchor="center")
        self.full_files_tree.column("expires", width=140, anchor="center")
        self.full_files_tree.column("status", width=120, anchor="w")

        full_scroll = ttk.Scrollbar(tree_box, orient="vertical", command=self.full_files_tree.yview, style="Dark.Vertical.TScrollbar")
        self.full_files_tree.configure(yscrollcommand=full_scroll.set)
        self.full_files_tree.pack(side="left", fill="both", expand=True)
        full_scroll.pack(side="right", fill="y")
        self.full_files_tree.bind("<Double-1>", lambda e: self.open_selected_received_file())

    def _reload_files_manager_view(self):
        self.full_files_tree.delete(*self.full_files_tree.get_children())
        for item in self.received_items:
            self.full_files_tree.insert(
                "",
                0,
                iid=f"full_{item['id']}",
                values=(
                    item["name"],
                    item["type"],
                    human_bytes(item["size"]),
                    self._format_time(item["received_at"]),
                    self._format_time(item["expires_at"]),
                    item["status"],
                ),
            )

    # --------------------------------------------------------------------------
    # 6. BOTTOM STATUS BAR
    # --------------------------------------------------------------------------
    def _build_bottom_bar(self):
        top_div = tk.Frame(self.root, bg=COLOR_BORDER, height=1)
        top_div.pack(side="bottom", fill="x")

        self.status_bar = tk.Frame(self.root, bg=COLOR_BG_DARK, height=32)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)

        # Left: Server Status Indicator & Text
        left_box = tk.Frame(self.status_bar, bg=COLOR_BG_DARK)
        left_box.pack(side="left", padx=16, fill="y")

        self.status_dot = tk.Canvas(left_box, width=8, height=8, bg=COLOR_BG_DARK, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 6), pady=12)
        self.status_dot_id = self.status_dot.create_oval(1, 1, 7, 7, fill=COLOR_TEXT_DIM, outline="")

        self.server_status_text = StringVar(value="Server: Inactive")
        tk.Label(
            left_box,
            textvariable=self.server_status_text,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_DARK,
        ).pack(side="left")

        # Center: Network Readiness
        self.network_status_text = StringVar(value=f"Network: Ready ({self.wifi_ssid})")
        tk.Label(
            self.status_bar,
            textvariable=self.network_status_text,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_DARK,
        ).pack(side="left", padx=24)

        # Right: Port & Retention Info
        right_box = tk.Frame(self.status_bar, bg=COLOR_BG_DARK)
        right_box.pack(side="right", padx=16, fill="y")

        self.port_info_text = StringVar(value=f"Port: {self.server_port} · Retention: {self.storage_duration.get()}")
        tk.Label(
            right_box,
            textvariable=self.port_info_text,
            font=("Segoe UI", 8),
            fg=COLOR_TEXT_DIM,
            bg=COLOR_BG_DARK,
        ).pack(side="right")

    # --------------------------------------------------------------------------
    # MODE & CONTROLS HANDLERS
    # --------------------------------------------------------------------------
    def _set_mode(self, mode: str):
        self.mode.set(mode)
        self.on_mode_change()

    def on_mode_change(self):
        is_receive = (self.mode.get() == "receive")
        if is_receive:
            self.btn_mode_send.configure(bg="#15151a", fg=COLOR_TEXT_MUTED, font=("Segoe UI", 9))
            self.btn_mode_receive.configure(bg=COLOR_CORAL, fg="#ffffff", font=("Segoe UI", 9, "bold"))
            self.send_controls_container.pack_forget()
            self.receive_info_container.pack(fill="both", expand=True, padx=18)
            self.main_action_btn.configure(text="⚡ Start Receive Server")
            self.view_title_lbl.configure(text="Receive from Mobile")
            self.view_desc_lbl.configure(
                text="Allow mobile devices to upload files and send text notes directly to this laptop."
            )
            self.set_status("Click 'Start Receive Server' to display the upload QR code.")
        else:
            self.btn_mode_send.configure(bg=COLOR_CORAL, fg="#ffffff", font=("Segoe UI", 9, "bold"))
            self.btn_mode_receive.configure(bg="#15151a", fg=COLOR_TEXT_MUTED, font=("Segoe UI", 9))
            self.receive_info_container.pack_forget()
            self.send_controls_container.pack(fill="both", expand=True, padx=18)
            self.main_action_btn.configure(text="⚡ Generate QR Code")
            self.view_title_lbl.configure(text="QR Data Share")
            self.view_desc_lbl.configure(
                text="Transfer files, text notes, and links seamlessly between laptop and mobile on your local Wi-Fi."
            )
            self.set_status("Select files or enter text, then click Generate QR Code.")

        self.clear_qr_preview()
        self.stop_servers()

    def _set_data_type(self, val: str):
        self.data_type.set(val)
        for k, btn in self.type_buttons.items():
            if k == val:
                btn.configure(bg=COLOR_CORAL, fg="#ffffff", font=("Segoe UI", 8, "bold"))
            else:
                btn.configure(bg="#15151a", fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8, "normal"))

        if val == "file":
            self.text_input_frame.pack_forget()
            self.file_input_frame.pack(fill="both", expand=True)
        else:
            self.file_input_frame.pack_forget()
            self.text_input_frame.pack(fill="both", expand=True)

    def _on_text_change(self, _event=None):
        length = len(self.text_input.get("1.0", "end-1c").strip())
        self.text_counter_var.set(f"{length} / {MAX_QR_TEXT_LENGTH} chars")
        if length > MAX_QR_TEXT_LENGTH:
            self.text_counter_var.set(f"{length} / {MAX_QR_TEXT_LENGTH} chars (Too long for raw QR!)")

    def on_storage_duration_change(self, _event=None):
        duration = self.storage_duration.get()
        self.port_info_text.set(f"Port: {self.server_port} · Retention: {duration}")
        self.set_status(f"Storage duration updated to {duration}.")

    # --------------------------------------------------------------------------
    # FILE SELECTION & LIST MANAGEMENT
    # --------------------------------------------------------------------------
    def select_files(self):
        paths = filedialog.askopenfilenames(
            title="Choose file(s) to share",
            filetypes=[
                ("All supported", "*.pdf *.txt *.docx *.doc *.png *.jpg *.jpeg *.gif *.webp *.mp4 *.zip"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return

        new_paths = list(paths)
        # Avoid duplicate entries in current selection
        combined = list(self.shared_files)
        for p in new_paths:
            if p not in combined:
                combined.append(p)

        if len(combined) > MAX_MULTI_FILE_COUNT:
            messagebox.showwarning(
                "Too many files",
                f"Maximum {MAX_MULTI_FILE_COUNT} files allowed. Only the first {MAX_MULTI_FILE_COUNT} were kept.",
            )
            combined = combined[:MAX_MULTI_FILE_COUNT]

        self.shared_files = combined
        for p in self.shared_files:
            if p not in self.send_status_by_path:
                self.send_status_by_path[p] = "Ready"

        self._rebuild_files_tree()
        self._refresh_metrics(last_action=f"Selected {len(self.shared_files)} file(s)")
        self.set_status(f"{len(self.shared_files)} file(s) selected. Ready to generate QR.")

    def remove_selected_shared_file(self):
        selected_items = self.files_tree.selection()
        if not selected_items:
            messagebox.showinfo("Select File", "Please select a file from the list to remove.")
            return

        for item_id in selected_items:
            path = item_id  # We use file path as iid
            if path in self.shared_files:
                self.shared_files.remove(path)
            self.send_status_by_path.pop(path, None)

        self._rebuild_files_tree()
        self._refresh_metrics(last_action="Removed file")
        self.set_status(f"{len(self.shared_files)} file(s) remaining in batch.")

    def clear_shared_files(self):
        self.shared_files = []
        self.send_status_by_path.clear()
        self._rebuild_files_tree()
        self._refresh_metrics(last_action="Cleared files")
        self.set_status("File selection cleared.")

    def _rebuild_files_tree(self):
        self.files_tree.delete(*self.files_tree.get_children())
        for path in self.shared_files:
            fname = os.path.basename(path)
            sz = os.path.getsize(path) if os.path.isfile(path) else 0
            st = self.send_status_by_path.get(path, "Ready")
            self.files_tree.insert("", "end", iid=path, values=(fname, human_bytes(sz), st))

        n = len(self.shared_files)
        total_sz = sum(os.path.getsize(p) for p in self.shared_files if os.path.isfile(p))
        self.file_list_count_var.set(f"{n} file(s) · {human_bytes(total_sz)}")

    # --------------------------------------------------------------------------
    # METRICS & STATUS UPDATES
    # --------------------------------------------------------------------------
    def set_status(self, msg: str, error: bool = False):
        if error:
            self.server_status_text.set(f"Error: {msg}")
            self.status_dot.itemconfig(self.status_dot_id, fill=COLOR_RED)
        else:
            if self.flask_server:
                self.server_status_text.set(f"Server Active: http://{self.server_ip}:{self.server_port}")
                self.status_dot.itemconfig(self.status_dot_id, fill=COLOR_GREEN)
            else:
                self.server_status_text.set("Server: Inactive")
                self.status_dot.itemconfig(self.status_dot_id, fill=COLOR_TEXT_DIM)

    def _refresh_metrics(self, last_action: str = None):
        sel_n = len(self.shared_files)
        sel_b = sum(os.path.getsize(p) for p in self.shared_files if os.path.isfile(p))
        rec_n = len(self.received_items)

        self.metric_selected_count.set(f"{sel_n} file(s)")
        self.metric_selected_size.set(human_bytes(sel_b))
        self.metric_received_count.set(f"{rec_n} file(s)")
        if last_action:
            self.last_activity_text.set(last_action)

    def refresh_network_status(self):
        self.server_ip = get_local_ip()
        self.wifi_ssid = get_wifi_ssid()
        self.ssid_var.set(f"Network: {self.wifi_ssid}")
        self.ip_display_var.set(f"IP: {self.server_ip}")
        self.network_status_text.set(f"Network: Ready ({self.wifi_ssid})")
        self.set_status("Network status refreshed.")

    # --------------------------------------------------------------------------
    # QR GENERATION & PREVIEW
    # --------------------------------------------------------------------------
    def generate_qr_image(self, payload: str):
        self.current_qr_payload = payload
        qr_obj = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
        qr_obj.add_data(payload)
        qr_obj.make(fit=True)
        img = qr_obj.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((230, 230), Image.Resampling.LANCZOS)
        
        self.current_qr_photo = ImageTk.PhotoImage(img)
        self.qr_canvas.configure(image=self.current_qr_photo, text="")

        display_text = payload if len(payload) <= 45 else payload[:42] + "..."
        self.payload_var.set(display_text)
        self.btn_download_qr.configure(state="normal")
        self.btn_copy_url.configure(state="normal")
        if payload.startswith("http://"):
            self.btn_open_browser.configure(state="normal")
        else:
            self.btn_open_browser.configure(state="disabled")

    def clear_qr_preview(self):
        self.qr_canvas.configure(image="", text="QR Preview\n\nClick 'Generate QR' or\n'Start Receive Server'")
        self.current_qr_photo = None
        self.current_qr_payload = ""
        self.payload_var.set("No active server or data")
        self.btn_download_qr.configure(state="disabled")
        self.btn_copy_url.configure(state="disabled")
        self.btn_open_browser.configure(state="disabled")

    def download_qr_image(self):
        if not self.current_qr_payload:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            initialfile="qr_share_code.png",
            title="Save QR Code Image",
        )
        if save_path:
            qr_obj = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=3)
            qr_obj.add_data(self.current_qr_payload)
            qr_obj.make(fit=True)
            img = qr_obj.make_image(fill_color="black", back_color="white")
            img.save(save_path)
            messagebox.showinfo("QR Saved", f"QR code image saved successfully to:\n{save_path}")

    def copy_server_url(self):
        if self.current_qr_payload:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_qr_payload)
            self.set_status("URL copied to clipboard!")

    def open_in_browser(self):
        if self.current_qr_payload and self.current_qr_payload.startswith("http"):
            import webbrowser
            webbrowser.open(self.current_qr_payload)

    # --------------------------------------------------------------------------
    # FLASK SERVERS (FILE SHARING & RECEIVING)
    # --------------------------------------------------------------------------
    def find_open_port(self):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("", 0))
        _, port = probe.getsockname()
        probe.close()
        return port

    def _validate_share_paths(self, paths: list):
        if not paths:
            raise ValueError("Please select one or more files to share.")
        total = 0
        for p in paths:
            if not os.path.isfile(p):
                raise FileNotFoundError(f"File missing or moved: {p}")
            sz = os.path.getsize(p)
            if sz > MAX_FILE_SIZE_BYTES:
                raise ValueError(
                    f"{os.path.basename(p)} exceeds maximum limit ({sz // (1024 * 1024)} MB). "
                    f"Max file size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                )
            total += sz
        if total > MAX_TOTAL_SHARE_BYTES:
            raise ValueError(
                f"Total batch size ({human_bytes(total)}) exceeds maximum limit ({human_bytes(MAX_TOTAL_SHARE_BYTES)})."
            )

    def start_flask_share_server(self, paths: list):
        self._validate_share_paths(paths)
        self.stop_servers()
        time.sleep(0.15)
        self.server_ip = get_local_ip()
        if self.server_ip == HOST_FALLBACK:
            raise ConnectionError("Could not detect local Wi-Fi IP. Ensure your laptop is connected to Wi-Fi.")

        self.server_port = self.find_open_port()
        flask_app = self._create_share_download_app(paths)
        try:
            self.flask_server = make_server("0.0.0.0", self.server_port, flask_app, threaded=True)
        except OSError as exc:
            raise RuntimeError(f"Share server failed on port {self.server_port}: {exc}") from exc

        self.server_thread = threading.Thread(target=self.flask_server.serve_forever, daemon=True)
        self.server_thread.start()

    def start_receive_server(self):
        self.stop_servers()
        time.sleep(0.15)
        self.server_ip = get_local_ip()
        if self.server_ip == HOST_FALLBACK:
            raise ConnectionError("Could not detect local Wi-Fi IP. Ensure your laptop is connected to Wi-Fi.")

        self.server_port = self.find_open_port()
        flask_app = self._create_receive_app()
        try:
            self.flask_server = make_server("0.0.0.0", self.server_port, flask_app, threaded=True)
        except OSError as exc:
            raise RuntimeError(f"Receive server failed on port {self.server_port}: {exc}") from exc

        self.server_thread = threading.Thread(target=self.flask_server.serve_forever, daemon=True)
        self.server_thread.start()

    def stop_servers(self):
        if self.flask_server:
            try:
                self.flask_server.shutdown()
            except Exception:
                pass
            try:
                self.flask_server.server_close()
            except Exception:
                pass
            self.flask_server = None

        if self.server_thread is not None:
            self.server_thread.join(timeout=2.0)
            self.server_thread = None

        self.set_status("Server stopped.")

    def _create_share_download_app(self, abs_paths: list):
        flask_app = Flask(__name__)
        indexed = [{"id": i, "path": p, "name": os.path.basename(p), "size": os.path.getsize(p)} for i, p in enumerate(abs_paths)]

        @flask_app.route("/", strict_slashes=False)
        def landing():
            files = [{"id": e["id"], "name": e["name"], "size_human": human_bytes(e["size"])} for e in indexed]
            total = sum(e["size"] for e in indexed)
            return render_template_string(
                MULTI_DOWNLOAD_LANDING_TEMPLATE,
                files=files,
                file_count=len(files),
                total_size_human=human_bytes(total),
            )

        @flask_app.route("/download/<int:fid>")
        def download_one(fid):
            if fid < 0 or fid >= len(indexed):
                return "File not found", 404
            path = indexed[fid]["path"]
            if not os.path.isfile(path):
                return "File not found", 404
            return send_file(path, as_attachment=True, download_name=indexed[fid]["name"], max_age=0, conditional=False)

        @flask_app.route("/download_all")
        def download_all_zip():
            buf = SpooledTemporaryFile(max_size=64 * 1024 * 1024, mode="w+b")
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                seen_names = {}
                for entry in indexed:
                    arc = entry["name"]
                    if arc in seen_names:
                        seen_names[arc] += 1
                        base, ext = os.path.splitext(arc)
                        arc = f"{base}_{seen_names[arc]}{ext}"
                    else:
                        seen_names[arc] = 0
                    zf.write(entry["path"], arcname=arc)
            buf.seek(0)
            return send_file(buf, as_attachment=True, download_name="shared_files.zip", mimetype="application/zip", max_age=0, conditional=False)

        return flask_app

    def _create_receive_app(self):
        flask_app = Flask(__name__)

        @flask_app.route("/", methods=["GET", "POST"])
        def receive_page():
            message = ""
            success = False
            try:
                if request.method == "POST":
                    has_content = False
                    uploads = request.files.getlist("upload_files")
                    note_text = (request.form.get("note_text") or "").strip()

                    for uploaded in uploads:
                        if not uploaded or not uploaded.filename:
                            continue
                        safe_name = secure_filename(uploaded.filename)
                        if not safe_name:
                            continue
                        save_path = self._unique_save_path(self.received_dir, safe_name)
                        uploaded.save(save_path)
                        file_sz = os.path.getsize(save_path)
                        if file_sz > MAX_FILE_SIZE_BYTES:
                            try:
                                os.remove(save_path)
                            except OSError:
                                pass
                            raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.")
                        has_content = True
                        self._enqueue_received_item(save_path, determine_file_category(safe_name))

                    if note_text:
                        note_name = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        note_path = os.path.join(self.received_dir, note_name)
                        with open(note_path, "w", encoding="utf-8") as tf:
                            tf.write(note_text)
                        has_content = True
                        self._enqueue_received_item(note_path, "Note / Text")

                    if not has_content:
                        raise ValueError("Please select file(s) or enter text before uploading.")

                    message = "Upload successful! Files saved to laptop."
                    success = True
            except Exception as exc:
                message = f"Upload error: {exc}"
                success = False

            return render_template_string(UPLOAD_PAGE_TEMPLATE, message=message, success=success)

        return flask_app

    def _unique_save_path(self, folder: str, filename: str) -> str:
        base, ext = os.path.splitext(filename)
        candidate = os.path.join(folder, filename)
        if not os.path.exists(candidate):
            return candidate
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(folder, f"{base}_{ts}{ext}")

    # --------------------------------------------------------------------------
    # MAIN ACTIONS
    # --------------------------------------------------------------------------
    def generate_qr_action(self):
        try:
            if self.mode.get() == "receive":
                self.start_receive_server()
                receive_url = f"http://{self.server_ip}:{self.server_port}/"
                self.generate_qr_image(receive_url)
                self.set_status(f"Receive Server Active on {receive_url}")
                self._refresh_metrics(last_action="Receive Server on")
                return

            selected_type = self.data_type.get()
            if selected_type == "file":
                if not self.shared_files:
                    raise ValueError("Please select one or more files using 'Choose File(s)' before generating QR.")
                self.start_flask_share_server(self.shared_files)
                url = f"http://{self.server_ip}:{self.server_port}/"
                self.generate_qr_image(url)
                for p in self.shared_files:
                    self.send_status_by_path[p] = "Sent"
                self._rebuild_files_tree()
                self._refresh_metrics(last_action=f"Sent {len(self.shared_files)} file(s)")
                self.set_status(f"Share Server Active: {url}")
            else:
                payload = self.text_input.get("1.0", "end-1c").strip()
                if not payload:
                    raise ValueError(f"Please enter {selected_type} content to generate QR.")
                if len(payload) > MAX_QR_TEXT_LENGTH:
                    raise ValueError(
                        f"Content too long for direct QR code ({len(payload)} chars). "
                        f"Limit is {MAX_QR_TEXT_LENGTH} chars. Consider sharing as a file instead."
                    )
                self.stop_servers()
                self.generate_qr_image(payload)
                self._refresh_metrics(last_action=f"Encoded {selected_type}")
                self.set_status("Scan this QR code with mobile camera to view content.")

        except (ValueError, FileNotFoundError, ConnectionError, RuntimeError) as exc:
            self.set_status(str(exc), error=True)
            messagebox.showerror("QR Share Notice", str(exc))
        except Exception as exc:
            self.set_status(f"Unexpected error: {exc}", error=True)
            messagebox.showerror("Error", str(exc))

    def clear_all(self):
        self.stop_servers()
        self.text_input.delete("1.0", END)
        self.shared_files = []
        self.send_status_by_path.clear()
        self._rebuild_files_tree()
        self.clear_qr_preview()
        self._refresh_metrics(last_action="Reset")
        self.set_status("Cleared all selections and stopped servers.")

    # --------------------------------------------------------------------------
    # RECEIVED FILES & EXPIRY CLEANUP
    # --------------------------------------------------------------------------
    def _ensure_received_folder(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        received_dir = os.path.join(base_dir, RECEIVED_FOLDER_NAME)
        os.makedirs(received_dir, exist_ok=True)
        return received_dir

    def _duration_label_to_seconds(self, label: str):
        for opt_label, sec in STORAGE_DURATION_OPTIONS:
            if opt_label == label:
                return sec
        return None

    def _format_time(self, dt):
        if dt is None:
            return "Forever"
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _load_existing_received_files(self):
        """Populate actual existing files from Received_Files folder so the UI starts with real data."""
        self.received_items.clear()
        self.activity_tree.delete(*self.activity_tree.get_children())
        if os.path.exists(self.received_dir):
            entries = os.listdir(self.received_dir)
            entries.sort(key=lambda f: os.path.getmtime(os.path.join(self.received_dir, f)) if os.path.isfile(os.path.join(self.received_dir, f)) else 0, reverse=True)
            for fname in entries:
                fpath = os.path.join(self.received_dir, fname)
                if os.path.isfile(fpath):
                    self.received_item_counter += 1
                    stat = os.stat(fpath)
                    mod_time = datetime.fromtimestamp(stat.st_mtime)
                    cat = determine_file_category(fname)
                    item = {
                        "id": str(self.received_item_counter),
                        "path": fpath,
                        "name": fname,
                        "type": cat,
                        "size": stat.st_size,
                        "received_at": mod_time,
                        "expires_at": None,
                        "status": "Saved on Laptop",
                        "warning_shown": False,
                    }
                    self.received_items.append(item)
                    self.activity_tree.insert(
                        "",
                        "end",
                        iid=item["id"],
                        values=(
                            item["name"],
                            item["type"],
                            human_bytes(item["size"]),
                            self._format_time(item["received_at"]),
                            item["status"],
                        ),
                    )

        self._refresh_metrics()
        self._reload_files_manager_view()

    def _enqueue_received_item(self, item_path: str, item_type: str):
        self.received_queue.put((item_path, item_type))
        try:
            self.root.after(0, self._process_received_queue)
        except Exception:
            pass

    def _process_received_queue(self):
        while not self.received_queue.empty():
            try:
                item_path, item_type = self.received_queue.get_nowait()
                self._register_received_item(item_path, item_type)
            except Exception:
                break

    def _register_received_item(self, item_path: str, item_type: str):
        duration_sec = self._duration_label_to_seconds(self.storage_duration.get())
        now = datetime.now()
        expires_at = now + timedelta(seconds=duration_sec) if duration_sec is not None else None
        
        self.received_item_counter += 1
        item_id = str(self.received_item_counter)
        sz = os.path.getsize(item_path) if os.path.isfile(item_path) else 0

        item = {
            "id": item_id,
            "path": item_path,
            "name": os.path.basename(item_path),
            "type": item_type,
            "size": sz,
            "received_at": now,
            "expires_at": expires_at,
            "status": "Received",
            "warning_shown": False,
        }
        self.received_items.insert(0, item)

        self.activity_tree.insert(
            "",
            0,
            iid=item_id,
            values=(
                item["name"],
                item["type"],
                human_bytes(sz),
                self._format_time(item["received_at"]),
                item["status"],
            ),
        )
        self._refresh_metrics(last_action=f"Received {item['name']}")
        self.set_status(f"Received {item_type}: {item['name']}")
        self._reload_files_manager_view()

    def _schedule_cleanup_cycle(self):
        if self.cleanup_job:
            try:
                self.root.after_cancel(self.cleanup_job)
            except Exception:
                pass
        self._process_received_queue()
        try:
            self.cleanup_job = self.root.after(1000, self._cleanup_expired_items)
        except Exception:
            pass

    def _cleanup_expired_items(self):
        self._process_received_queue()
        now = datetime.now()
        updated = False
        for item in self.received_items:
            if item["status"] in ("Expired and deleted", "Failed"):
                continue
            expires_at = item["expires_at"]
            if expires_at is None:
                continue

            remaining = (expires_at - now).total_seconds()
            if 0 < remaining <= EXPIRY_WARNING_SECONDS and not item["warning_shown"]:
                item["warning_shown"] = True
                item["status"] = "Expiring soon..."
                self._update_tree_row(item)
                updated = True
            elif remaining <= 0:
                try:
                    if os.path.exists(item["path"]):
                        os.remove(item["path"])
                    item["status"] = "Expired and deleted"
                except OSError:
                    item["status"] = "Failed"
                self._update_tree_row(item)
                updated = True

        if updated:
            self._refresh_metrics()
            self._reload_files_manager_view()

        self.cleanup_job = self.root.after(2000, self._cleanup_expired_items)

    def _update_tree_row(self, item):
        if self.activity_tree.exists(item["id"]):
            self.activity_tree.item(
                item["id"],
                values=(
                    item["name"],
                    item["type"],
                    human_bytes(item["size"]),
                    self._format_time(item["received_at"]),
                    item["status"],
                ),
            )

    def _on_activity_double_click(self, _event=None):
        sel = self.activity_tree.selection()
        if sel:
            item_id = sel[0]
            for it in self.received_items:
                if it["id"] == item_id:
                    self._open_file_by_path(it["path"])
                    break

    def open_selected_received_file(self):
        sel = self.full_files_tree.selection()
        if not sel:
            messagebox.showinfo("Select File", "Please select a file from the list to open.")
            return
        item_id = sel[0].replace("full_", "")
        for it in self.received_items:
            if it["id"] == item_id:
                self._open_file_by_path(it["path"])
                break

    def _open_file_by_path(self, fpath: str):
        if not os.path.exists(fpath):
            messagebox.showerror("File Missing", f"File does not exist: {fpath}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(fpath)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", fpath])
            else:
                subprocess.Popen(["xdg-open", fpath])
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open file: {exc}")

    def delete_selected_received_file(self):
        sel = self.full_files_tree.selection()
        if not sel:
            messagebox.showinfo("Select File", "Please select a file to delete.")
            return
        item_id = sel[0].replace("full_", "")
        target_item = None
        for it in self.received_items:
            if it["id"] == item_id:
                target_item = it
                break

        if not target_item:
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete:\n{target_item['name']}?",
        )
        if confirm:
            try:
                if os.path.exists(target_item["path"]):
                    os.remove(target_item["path"])
                self.received_items.remove(target_item)
                self._load_existing_received_files()
                self.set_status(f"Deleted {target_item['name']}.")
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to delete file: {exc}")

    def open_received_folder(self):
        try:
            if sys.platform == "win32":
                os.startfile(self.received_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.received_dir])
            else:
                subprocess.Popen(["xdg-open", self.received_dir])
            self.set_status(f"Opened folder: {self.received_dir}")
        except Exception as exc:
            self.set_status(f"Could not open folder: {exc}", error=True)

    # --------------------------------------------------------------------------
    # SETTINGS MODAL DIALOG
    # --------------------------------------------------------------------------
    def open_settings_dialog(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Application Settings")
        settings_win.geometry("480x420")
        settings_win.resizable(False, False)
        settings_win.configure(bg=COLOR_BG_CARD)
        settings_win.transient(self.root)
        settings_win.grab_set()

        tk.Label(
            settings_win,
            text="Settings & Preferences",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_BG_CARD,
        ).pack(anchor="w", padx=20, pady=(20, 4))

        tk.Label(
            settings_win,
            text="Configure server parameters and storage policies.",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_CARD,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        # Card 1: Network & Port
        card1 = tk.Frame(settings_win, bg="#16161c", highlightbackground=COLOR_BORDER, highlightthickness=1)
        card1.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(
            card1,
            text="NETWORK & PORTS",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_CORAL,
            bg="#16161c",
        ).pack(anchor="w", padx=14, pady=(10, 4))

        tk.Label(
            card1,
            text=f"Wi-Fi Network SSID:  {self.wifi_ssid}\n"
                 f"Local IP Address:   {self.server_ip}\n"
                 f"Default Server Port: {self.server_port}",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_PRIMARY,
            bg="#16161c",
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Card 2: Storage Retention
        card2 = tk.Frame(settings_win, bg="#16161c", highlightbackground=COLOR_BORDER, highlightthickness=1)
        card2.pack(fill="x", padx=20, pady=(0, 16))

        tk.Label(
            card2,
            text="STORAGE RETENTION POLICY",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_CORAL,
            bg="#16161c",
        ).pack(anchor="w", padx=14, pady=(10, 4))

        tk.Label(
            card2,
            text=f"Received Folder:  {self.received_dir}\n"
                 f"Current Policy:   {self.storage_duration.get()}\n"
                 f"Max File Size:    100 MB per file (500 MB batch)",
            font=("Segoe UI", 9),
            fg=COLOR_TEXT_PRIMARY,
            bg="#16161c",
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Bottom Button
        btn_close = tk.Button(
            settings_win,
            text="Close Settings",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg=COLOR_CORAL,
            activebackground=COLOR_CORAL_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            command=settings_win.destroy,
        )
        btn_close.pack(pady=10)

    # --------------------------------------------------------------------------
    # LIFECYCLE & SHUTDOWN
    # --------------------------------------------------------------------------
    def on_close(self):
        if self.cleanup_job:
            self.root.after_cancel(self.cleanup_job)
            self.cleanup_job = None
        self.stop_servers()
        self.root.destroy()

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    root = tk.Tk()
    QRShareApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()