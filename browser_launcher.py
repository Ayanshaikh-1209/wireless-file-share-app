# browser_launcher.py
import webbrowser
import threading

def open_browser(url):
    """Open the given URL in the default web browser after a short delay."""
    def _open():
        webbrowser.open(url)
    
    # Run in a separate thread so server starts first
    timer = threading.Timer(1.5, _open)
    timer.daemon = True
    timer.start()