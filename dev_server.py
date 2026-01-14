#!/usr/bin/env python3
"""
Simple development server for React frontend
Serves static files from frontend directory and proxies API requests to Flask backend
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import sys
import urllib.request
import urllib.error
import json

# Use 127.0.0.1 to avoid IPv6 issues with localhost
BACKEND_URL = 'http://127.0.0.1:5000'

class DevServerHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        try:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            super().end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        try:
            if self.path.startswith('/api/'):
                self.proxy_request()
            else:
                # Handle root path - serve landing page
                if self.path == '/':
                    self.path = '/index.html'
                # Handle /cv-tools route
                elif self.path == '/cv-tools':
                    self.path = '/cv-tools.html'
                # Handle /image-viewer route
                elif self.path == '/image-viewer':
                    self.path = '/image-viewer.html'
                
                super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass
            
    def do_POST(self):
        try:
            if self.path.startswith('/api/'):
                self.proxy_request()
            else:
                self.send_json_error(404, "Not Found")
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json_error(self, code, message):
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({'success': False, 'error': message}).encode('utf-8')
            self.wfile.write(response)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def proxy_request(self):
        url = f'{BACKEND_URL}{self.path}'
        print(f'Proxying {self.command} {self.path} -> {url}')
        
        try:
            # Prepare data for POST
            data = None
            if self.command == 'POST':
                length = int(self.headers.get('Content-Length', 0))
                if length > 0:
                    data = self.rfile.read(length)
            
            # Create request
            req = urllib.request.Request(url, data=data, method=self.command)
            
            # Forward headers
            skip_headers = ['Host', 'Content-Length'] 
            for key, value in self.headers.items():
                if key not in skip_headers:
                    req.add_header(key, value)
            
            # Send request
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() != 'transfer-encoding':
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
                
        except urllib.error.HTTPError as e:
            # Forward backend error
            try:
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(e.read())
            except (BrokenPipeError, ConnectionResetError):
                pass
            
        except urllib.error.URLError as e:
            print(f'Connection error: {e}')
            self.send_json_error(502, f"Backend connection failed: {e.reason}")
            
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected during proxying
            pass
            
        except Exception as e:
            print(f'Proxy error: {e}')
            self.send_json_error(500, f"Proxy error: {str(e)}")

    def log_error(self, format, *args):
        # Silence broken pipe and connection reset errors in the logs
        if args and isinstance(args[0], str) and ("Broken pipe" in args[0] or "Connection reset by peer" in args[0]):
            return
        super().log_error(format, *args)

def run(port=8080):
    project_root = os.getcwd()
    frontend_dir = os.path.join(project_root, 'frontend')
    
    if os.path.exists(frontend_dir):
        os.chdir(frontend_dir)
        print(f'📂 Serving static files from: {frontend_dir}')
    else:
        print(f'⚠️ Frontend directory not found at {frontend_dir}, serving from current directory')

    server_address = ('', port)
    # Using ThreadingHTTPServer for better parallelism
    httpd = ThreadingHTTPServer(server_address, DevServerHandler)
    print(f'🚀 Frontend dev server running at http://localhost:{port}')
    print(f'📡 Proxying API requests to {BACKEND_URL}')
    print('Press Ctrl+C to stop')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping server...')
        httpd.server_close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
