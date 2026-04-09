import http.server
import socketserver
import threading
import json
import base64
import os
import shutil
import time
from urllib.parse import urlparse, unquote

from core.constants import EXPORT_DIR, DOWNLOAD_DIR, ASSETS_DIR
from core.state import state
from core.stl_utils import get_stl_hash

class NexusHandler(http.server.BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type, File-Name")
        self.send_header("Connection", "close")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/report_error':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                data = json.loads(self.rfile.read(cl).decode('utf-8'))
                state.last_error_log = data.get('error', '')
                self.send_response(200)
                self._send_cors()
                self.end_headers()
                self.wfile.write(b'ok')
            return

        elif parsed.path == '/api/send_vision':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                data = json.loads(self.rfile.read(cl).decode('utf-8'))
                state.vision_b64 = data.get('image', '')
                self.send_response(200)
                self._send_cors()
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            return

        elif parsed.path == '/api/inject_code':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                data = json.loads(self.rfile.read(cl).decode('utf-8'))
                state.injected_code_ia = data.get('code', '')
                self.send_response(200)
                self._send_cors()
                self.end_headers()
                self.wfile.write(b'ok')
            return

        elif parsed.path == '/api/agentic_ui':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                try:
                    data = json.loads(self.rfile.read(cl).decode('utf-8'))
                    state.agentic_payload = data
                    self.send_response(200)
                    self._send_cors()
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
                except:
                    pass
            self.send_response(500)
            self._send_cors()
            self.end_headers()
            return

        elif parsed.path == '/api/upload_raw':
            cl = int(self.headers.get('Content-Length', 0))
            filename = unquote(self.headers.get('File-Name', f'nexus_upload_{int(time.time())}.stl'))
            if cl > 0:
                try:
                    filepath_export = os.path.join(EXPORT_DIR, filename)
                    with open(filepath_export, 'wb') as f:
                        remaining = cl
                        chunk_size = 8192
                        while remaining > 0:
                            read_size = min(chunk_size, remaining)
                            data = self.rfile.read(read_size)
                            if not data:
                                break
                            f.write(data)
                            remaining -= len(data)
                    try:
                        shutil.copy(filepath_export, os.path.join(DOWNLOAD_DIR, filename))
                    except:
                        pass
                    self.send_response(200)
                    self._send_cors()
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
                except:
                    pass
            self.send_response(500)
            self._send_cors()
            self.end_headers()
            return

        elif parsed.path in ['/api/save_export', '/api/save_model']:
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                try:
                    data = json.loads(self.rfile.read(cl).decode('utf-8'))
                    filename = data.get('filename', f'nexus_export_{int(time.time())}.stl')
                    file_data = data.get('data', '')
                    if isinstance(file_data, str) and file_data.startswith('data:'):
                        file_bytes = base64.b64decode(file_data.split(',')[1])
                        mode = 'wb'
                    else:
                        file_bytes = file_data.encode('utf-8') if isinstance(file_data, str) else file_data
                        mode = 'wb' if isinstance(file_bytes, bytes) else 'w'
                    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                    with open(os.path.join(DOWNLOAD_DIR, filename), mode) as f:
                        f.write(file_bytes)
                    with open(os.path.join(EXPORT_DIR, filename), mode) as f:
                        f.write(file_bytes)
                    self.send_response(200)
                    self._send_cors()
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
                except:
                    pass
            self.send_response(500)
            self._send_cors()
            self.end_headers()
            return

        elif parsed.path == '/api/save_image':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                try:
                    data = json.loads(self.rfile.read(cl).decode('utf-8'))
                    filepath = os.path.join(EXPORT_DIR, data['filename'])
                    with open(filepath, 'wb') as f:
                        f.write(base64.b64decode(data['image_data'].split(',')[1]))
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.send_header("Content-Length", "13")
                    self._send_cors()
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
                except:
                    pass
            self.send_response(500)
            self._send_cors()
            self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/get_vision.json':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._send_cors()
            self.end_headers()
            payload = {"image_b64": state.vision_b64, "last_error": state.last_error_log}
            self.wfile.write(json.dumps(payload).encode())
            state.vision_b64 = ""
            state.last_error_log = ""
            return

        elif parsed.path == '/api/get_code_b64.json':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._send_cors()
            self.end_headers()
            hash_val = get_stl_hash() if state.latest_needs_stl else ""
            self.wfile.write(json.dumps({"code_b64": state.latest_code_b64, "stl_hash": hash_val}).encode())
            state.latest_code_b64 = ""
            return

        elif parsed.path == '/api/assembly_state.json':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._send_cors()
            self.end_headers()
            self.wfile.write(json.dumps(state.pbr_state).encode('utf-8'))
            return

        elif parsed.path == '/imported.stl':
            filepath = os.path.join(EXPORT_DIR, "imported.stl")
            data_to_send = b'NEXUS_DUMMY_STL' + (b'\x00' * 65) + (1).to_bytes(4, 'little') + (b'\x00' * 50)
            if os.path.exists(filepath):
                try:
                    sz = os.path.getsize(filepath)
                    if sz >= 84:
                        with open(filepath, "rb") as f:
                            data_to_send = f.read()
                except:
                    pass
            self.send_response(200)
            self.send_header("Content-type", "model/stl")
            self.send_header("Content-Length", str(len(data_to_send)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self._send_cors()
            self.end_headers()
            try:
                chunk_size = 65536
                for i in range(0, len(data_to_send), chunk_size):
                    self.wfile.write(data_to_send[i:i+chunk_size])
            except:
                pass
            return

        elif parsed.path.startswith('/descargar/'):
            filename = unquote(parsed.path.replace('/descargar/', ''))
            filepath = os.path.join(EXPORT_DIR, filename)
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self._send_cors()
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self._send_cors()
                self.end_headers()
            return

        elif parsed.path == '/' or parsed.path == '/openscad_engine.html':
            try:
                fn = "openscad_engine.html"
                with open(os.path.join(ASSETS_DIR, fn), "r", encoding="utf-8") as f:
                    content = f.read()
                stl_path = os.path.join(EXPORT_DIR, "imported.stl")
                b64_stl = base64.b64encode(b'NEXUS_DUMMY_STL' + (b'\x00' * 65) + (1).to_bytes(4, 'little') + (b'\x00' * 50)).decode('utf-8')
                if os.path.exists(stl_path) and os.path.getsize(stl_path) >= 84:
                    with open(stl_path, "rb") as stl_file:
                        b64_stl = base64.b64encode(stl_file.read()).decode('utf-8')
                injector = '''
                <script>
                (function() {
                    var stlData = "data:application/octet-stream;base64,__B64_STL__";
                    var origOpen = XMLHttpRequest.prototype.open;
                    XMLHttpRequest.prototype.open = function(method, url) { if (url && typeof url === "string" && url.indexOf("imported.stl") !== -1) { arguments[1] = stlData; } return origOpen.apply(this, arguments); };
                    if(window.fetch) { var origFetch = window.fetch; window.fetch = function(resource, config) { if (resource && typeof resource === "string" && resource.indexOf("imported.stl") !== -1) { resource = stlData; } return origFetch.call(this, resource, config); }; }
                    if(window.Worker) { var origWorker = window.Worker; window.Worker = function(scriptURL, options) { var absUrl = new URL(scriptURL, location.href).href; var code = "var stlData = '" + stlData + "'; var origOpen = XMLHttpRequest.prototype.open; XMLHttpRequest.prototype.open = function(m, u) { if (u && typeof u === 'string' && u.indexOf('imported.stl') !== -1) { arguments[1] = stlData; } return origOpen.apply(this, arguments); }; if(self.fetch) { var origFetch = self.fetch; self.fetch = function(r, c) { if (r && typeof r === 'string' && r.indexOf('imported.stl') !== -1) { r = stlData; } return origFetch.call(this, r, c); }; } importScripts('" + absUrl + "');"; var blob = new Blob([code], { type: "application/javascript" }); return new origWorker(URL.createObjectURL(blob), options); }; }
                })();
                </script>
                '''.replace("__B64_STL__", b64_stl)
                if "<head>" in content:
                    content = content.replace("<head>", "<head>" + injector)
                else:
                    content = injector + content
                encoded_content = content.encode('utf-8')
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.send_header("Content-Length", str(len(encoded_content)))
                self._send_cors()
                self.end_headers()
                self.wfile.write(encoded_content)
                return
            except Exception as e:
                self.send_response(500)
                self._send_cors()
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        else:
            try:
                fn = parsed.path.strip("/")
                filepath = os.path.join(ASSETS_DIR, fn)
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    with open(filepath, "rb") as f:
                        self.send_response(200)
                        if fn.endswith(".html"):
                            self.send_header("Content-type", "text/html; charset=utf-8")
                        elif fn.endswith(".js"):
                            self.send_header("Content-type", "application/javascript")
                        elif fn.endswith(".css"):
                            self.send_header("Content-type", "text/css")
                        elif fn.endswith(".png"):
                            self.send_header("Content-type", "image/png")
                        elif fn.endswith(".stl"):
                            self.send_header("Content-type", "model/stl")
                        else:
                            self.send_header("Content-type", "text/plain")
                        self._send_cors()
                        self.end_headers()
                        self.wfile.write(f.read())
                else:
                    self.send_response(404)
                    self._send_cors()
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self._send_cors()
                self.end_headers()

    def log_message(self, *args):
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def start_server(port):
    server = ThreadedHTTPServer(("0.0.0.0", port), NexusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
