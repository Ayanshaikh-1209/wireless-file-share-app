# server.py
from http.server import HTTPServer
import socketserver

PORT = 8010

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def create_server(handler):
    """Create and return an HTTP server on the defined PORT."""
    server = ReusableTCPServer(("", PORT), handler)
    return server, PORT