# -*- coding: utf-8 -*-
"""
Simple HTTP Server for Website Preview
Run: python website_server.py
Open: http://localhost:8080
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8080
DIRECTORY = Path(__file__).parent / "website"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        # Add UTF-8 charset for proper Persian text display
        if self.path.endswith('.html'):
            self.send_header('Content-Type', 'text/html; charset=utf-8')
        elif self.path.endswith('.css'):
            self.send_header('Content-Type', 'text/css; charset=utf-8')
        elif self.path.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
        super().end_headers()

def main():
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"\n{'='*50}")
        print(f"  🚀 OdooMaster Website Server")
        print(f"{'='*50}")
        print(f"\n  🌐 Server running at: http://localhost:{PORT}")
        print(f"  📁 Serving directory: {DIRECTORY}")
        print(f"\n  Pages:")
        print(f"    • Home:      http://localhost:{PORT}/index.html")
        print(f"    • Login:     http://localhost:{PORT}/login.html")
        print(f"    • Register:  http://localhost:{PORT}/register.html")
        print(f"    • Dashboard: http://localhost:{PORT}/dashboard.html")
        print(f"\n  Press Ctrl+C to stop the server\n")
        print(f"{'='*50}\n")
        
        # Auto-open browser
        webbrowser.open(f'http://localhost:{PORT}/index.html')
        
        httpd.serve_forever()

if __name__ == "__main__":
    main()
