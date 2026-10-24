# handler.py
from http.server import SimpleHTTPRequestHandler
from urllib.parse import quote
import html
import io
import os

class FileHandler(SimpleHTTPRequestHandler):
    """Custom handler that serves files and suppresses server logs."""

    def log_message(self, format, *args):
        # Suppress default console logging for cleaner output
        pass

    def do_GET(self):
        """Handle GET requests."""
        super().do_GET()

    def list_directory(self, path):
        """Render a clean, styled directory listing page."""
        try:
            entries = sorted(os.listdir(path), key=lambda name: name.lower())
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

        display_path = html.escape(self.path)
        encoded_path = self.path
        if not encoded_path.endswith("/"):
            encoded_path += "/"

        items_html = []
        if encoded_path != "/":
            parent_link = quote(os.path.join(encoded_path, "..").replace("\\", "/"))
            items_html.append(
                f'<a class="item" href="{parent_link}"><span class="name">.. (Parent Directory)</span><span class="meta">Folder</span></a>'
            )

        for name in entries:
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            display_name = f"{name}/" if is_dir else name
            href_name = quote(name)
            href = href_name + "/" if is_dir else href_name
            size = "-" if is_dir else f"{os.path.getsize(full_path)} bytes"
            item_type = "Folder" if is_dir else "File"
            items_html.append(
                f'<a class="item" href="{href}"><span class="name">{html.escape(display_name)}</span><span class="meta">{item_type} • {size}</span></a>'
            )

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>File Sharing App</title>
  <style>
    :root {{
      color-scheme: light dark;
    }}
    body {{
      margin: 0;
      font-family: Segoe UI, Arial, sans-serif;
      background: linear-gradient(135deg, #f8fafc, #eef2ff);
      color: #1f2937;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      padding: 24px;
      box-sizing: border-box;
    }}
    .card {{
      width: min(860px, 100%);
      background: rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(4px);
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      box-shadow: 0 12px 30px rgba(30, 41, 59, 0.08);
      overflow: hidden;
    }}
    .header {{
      padding: 18px 20px;
      border-bottom: 1px solid #e5e7eb;
      background: #ffffff;
    }}
    .title {{
      margin: 0 0 6px 0;
      font-size: 1.25rem;
      font-weight: 700;
    }}
    .subtitle {{
      margin: 0;
      color: #6b7280;
      font-size: 0.95rem;
      word-break: break-all;
    }}
    .list {{
      display: grid;
      gap: 10px;
      padding: 16px;
    }}
    .item {{
      text-decoration: none;
      color: inherit;
      padding: 12px 14px;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
      background: #fff;
    }}
    .item:hover {{
      transform: translateY(-1px);
      border-color: #6366f1;
      box-shadow: 0 8px 18px rgba(99, 102, 241, 0.18);
    }}
    .name {{
      font-weight: 600;
      overflow-wrap: anywhere;
    }}
    .meta {{
      color: #6b7280;
      font-size: 0.9rem;
      white-space: nowrap;
    }}
  </style>
</head>
<body>
  <main class="card">
    <header class="header">
      <h1 class="title">Local File Sharing</h1>
      <p class="subtitle">Browsing: {display_path}</p>
    </header>
    <section class="list">
      {''.join(items_html)}
    </section>
  </main>
</body>
</html>
"""

        encoded = page.encode("utf-8", "surrogateescape")
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f