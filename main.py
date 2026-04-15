import flet as ft
import os, base64, json, threading, http.server, socketserver, socket, time, warnings, traceback, shutil, struct
import importlib  # <-- Motor para recarga en caliente
import param_generators
import nexus_ui_tools
import lang       # <-- ¡NUESTRO CEREBRO BILINGÜE!

from urllib.parse import urlparse, unquote

warnings.simplefilter("ignore", DeprecationWarning)

# =========================================================
# RUTAS DEL SISTEMA Y ANDROID
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
EXPORT_DIR = os.path.join(BASE_DIR, "nexus_proyectos")
os.makedirs(EXPORT_DIR, exist_ok=True)
DOWNLOAD_DIR = "/storage/emulated/0/Download"

def get_android_root():
    paths = ["/storage/emulated/0", os.path.expanduser("~/storage/shared"), BASE_DIR]
    for p in paths:
        try:
            os.listdir(p)
            return p
        except: pass
    return BASE_DIR

ANDROID_ROOT = get_android_root()

# =========================================================
# GLOBALES DE ESTADO (IA v21.2)
# =========================================================
LAN_IP = "127.0.0.1"
INTERNAL_IP = "127.0.0.1" 
LOCAL_PORT = 8556
LATEST_CODE_B64 = ""
LATEST_NEEDS_STL = False

INJECTED_CODE_IA = "" 
VISION_B64 = ""
LAST_ERROR_LOG = ""
AGENTIC_PAYLOAD = None  

MAX_ASSEMBLY_PARTS = 10
ASSEMBLY_PARTS_STATE = [{"active": False, "file": "", "mat": "pla", "x": 0, "y": 0, "z": 0} for _ in range(MAX_ASSEMBLY_PARTS)]
PBR_STATE = {"mode": "single", "parts": []}

def update_pbr_state():
    global PBR_STATE
    PBR_STATE["mode"] = "assembly"
    PBR_STATE["parts"] = [p for p in ASSEMBLY_PARTS_STATE if p["active"]]

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', 0))
        LOCAL_PORT = s.getsockname()[1]
except: pass

LAN_IP = get_lan_ip()

def get_stl_hash():
    path = os.path.join(EXPORT_DIR, "imported.stl")
    if os.path.exists(path):
        try:
            sz = os.path.getsize(path)
            if sz > 84: return f"{os.path.getmtime(path)}_{sz}"
        except: pass
    return ""

def validate_stl(filepath):
    try:
        sz = os.path.getsize(filepath)
        if sz < 84: return False, "El archivo es demasiado pequeño."
        with open(filepath, 'rb') as f:
            header = f.read(80)
            if b'solid ' in header[:10]: return True, "ASCII STL Detectado"
            tris = int.from_bytes(f.read(4), byteorder='little')
            expected = 84 + (tris * 50)
            if sz == expected: return True, "Binario STL Válido"
            return False, f"STL Incompleto/Roto: Pesa {sz}B, Motor exige {expected}B."
    except Exception as e: return False, f"Error lectura: {e}"

def convert_stl_to_obj(stl_path, obj_path):
    try:
        with open(stl_path, 'rb') as f:
            f.read(80)
            tris = int.from_bytes(f.read(4), 'little')
            with open(obj_path, 'w') as out:
                out.write("# NEXUS CAD Export\no Nexus_Mesh\n")
                v_idx = 1
                for _ in range(tris):
                    data = f.read(50)
                    if len(data) < 50: break
                    v1 = struct.unpack('<3f', data[12:24])
                    v2 = struct.unpack('<3f', data[24:36])
                    v3 = struct.unpack('<3f', data[36:48])
                    out.write(f"v {v1[0]} {v1[1]} {v1[2]}\nv {v2[0]} {v2[1]} {v2[2]}\nv {v3[0]} {v3[1]} {v3[2]}\nf {v_idx} {v_idx+1} {v_idx+2}\n")
                    v_idx += 3
        return True, "Convertido exitosamente."
    except Exception as e: return False, str(e)

def analyze_stl(filepath):
    try:
        with open(filepath, 'rb') as f:
            if b'solid ' in f.read(80)[:10]: return None
            f.seek(80)
            tri_count = int.from_bytes(f.read(4), byteorder='little')
            min_x = min_y = min_z = float('inf')
            max_x = max_y = max_z = float('-inf')
            volume = 0.0
            for _ in range(tri_count):
                data = f.read(50)
                if len(data) < 50: break
                v1 = struct.unpack('<3f', data[12:24]); v2 = struct.unpack('<3f', data[24:36]); v3 = struct.unpack('<3f', data[36:48])
                for v in (v1, v2, v3):
                    if v[0] < min_x: min_x = v[0]
                    if v[0] > max_x: max_x = v[0]
                    if v[1] < min_y: min_y = v[1]
                    if v[1] > max_y: max_y = v[1]
                    if v[2] < min_z: min_z = v[2]
                    if v[2] > max_z: max_z = v[2]
                v321 = v3[0]*v2[1]*v1[2]; v231 = v2[0]*v3[1]*v1[2]; v312 = v3[0]*v1[1]*v2[2]
                v132 = v1[0]*v3[1]*v2[2]; v213 = v2[0]*v1[1]*v3[2]; v123 = v1[0]*v2[1]*v3[2]
                volume += (1.0/6.0)*(-v321 + v231 + v312 - v132 - v213 + v123)
            vol_cm3 = abs(volume) / 1000.0; weight_pla = vol_cm3 * 1.24
            return {"dx": round(max_x - min_x, 2), "dy": round(max_y - min_y, 2), "dz": round(max_z - min_z, 2), "vol_cm3": round(vol_cm3, 2), "weight_g": round(weight_pla, 2)}
    except: return None

DUMMY_VALID_STL = b'NEXUS_DUMMY_STL' + (b'\x00' * 65) + (1).to_bytes(4, 'little') + (b'\x00' * 50)

# =========================================================
# SERVIDOR HTTP LOCAL
# =========================================================
class NexusHandler(http.server.BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type, File-Name")
        self.send_header("Connection", "close") 

    def do_OPTIONS(self):
        self.send_response(200); self._send_cors(); self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        global VISION_B64, INJECTED_CODE_IA, LAST_ERROR_LOG, AGENTIC_PAYLOAD
        
        if parsed.path == '/api/report_error':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                data = json.loads(self.rfile.read(cl).decode('utf-8'))
                LAST_ERROR_LOG = data.get('error', '')
                self.send_response(200); self._send_cors(); self.end_headers(); self.wfile.write(b'ok')
            return

        elif parsed.path == '/api/send_vision':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                data = json.loads(self.rfile.read(cl).decode('utf-8'))
                VISION_B64 = data.get('image', '')
                self.send_response(200); self._send_cors(); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
            return
            
        elif parsed.path == '/api/inject_code':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                data = json.loads(self.rfile.read(cl).decode('utf-8'))
                INJECTED_CODE_IA = data.get('code', '')
                self.send_response(200); self._send_cors(); self.end_headers(); self.wfile.write(b'ok')
            return

        elif parsed.path == '/api/agentic_ui':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                try:
                    data = json.loads(self.rfile.read(cl).decode('utf-8'))
                    AGENTIC_PAYLOAD = data 
                    self.send_response(200); self._send_cors(); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
                    return
                except: pass
            self.send_response(500); self._send_cors(); self.end_headers()
            return

        elif parsed.path == '/api/upload_raw':
            cl = int(self.headers.get('Content-Length', 0))
            filename = unquote(self.headers.get('File-Name', f'nexus_upload_{int(time.time())}.stl'))
            if cl > 0:
                try:
                    filepath_export = os.path.join(EXPORT_DIR, filename)
                    with open(filepath_export, 'wb') as f:
                        remaining = cl; chunk_size = 8192 
                        while remaining > 0:
                            read_size = min(chunk_size, remaining)
                            data = self.rfile.read(read_size)
                            if not data: break
                            f.write(data)
                            remaining -= len(data)
                    try: shutil.copy(filepath_export, os.path.join(DOWNLOAD_DIR, filename))
                    except: pass
                    self.send_response(200); self._send_cors(); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
                    return
                except: pass
            self.send_response(500); self._send_cors(); self.end_headers()
            return
            
        elif parsed.path in ['/api/save_export', '/api/save_model']:
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                try:
                    data = json.loads(self.rfile.read(cl).decode('utf-8'))
                    filename = data.get('filename', f'nexus_export_{int(time.time())}.stl')
                    file_data = data.get('data', '')
                    if isinstance(file_data, str) and file_data.startswith('data:'):
                        file_bytes = base64.b64decode(file_data.split(',')[1]); mode = 'wb'
                    else:
                        file_bytes = file_data.encode('utf-8') if isinstance(file_data, str) else file_data; mode = 'wb' if isinstance(file_bytes, bytes) else 'w'
                    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                    with open(os.path.join(DOWNLOAD_DIR, filename), mode) as f: f.write(file_bytes)
                    with open(os.path.join(EXPORT_DIR, filename), mode) as f: f.write(file_bytes)
                    self.send_response(200); self._send_cors(); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
                    return
                except: pass
            self.send_response(500); self._send_cors(); self.end_headers()
            
        elif parsed.path == '/api/save_image':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                try:
                    data = json.loads(self.rfile.read(cl).decode('utf-8'))
                    filepath = os.path.join(EXPORT_DIR, data['filename'])
                    with open(filepath, 'wb') as f: f.write(base64.b64decode(data['image_data'].split(',')[1]))
                    resp = b'{"status": "ok"}'
                    self.send_response(200); self.send_header("Content-type", "application/json"); self.send_header("Content-Length", str(len(resp))); self._send_cors(); self.end_headers(); self.wfile.write(resp)
                    return
                except: pass
            self.send_response(500); self._send_cors(); self.end_headers()

    def do_GET(self):
        global LATEST_CODE_B64, LATEST_NEEDS_STL, PBR_STATE, VISION_B64, LAST_ERROR_LOG
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/get_vision.json':
            self.send_response(200); self.send_header("Content-type", "application/json"); self._send_cors(); self.end_headers()
            payload = {"image_b64": VISION_B64, "last_error": LAST_ERROR_LOG}
            self.wfile.write(json.dumps(payload).encode())
            VISION_B64 = ""; LAST_ERROR_LOG = "" 
            return
            
        elif parsed.path == '/api/get_code_b64.json':
            self.send_response(200); self.send_header("Content-type", "application/json"); self._send_cors(); self.end_headers()
            hash_val = get_stl_hash() if LATEST_NEEDS_STL else ""
            self.wfile.write(json.dumps({"code_b64": LATEST_CODE_B64, "stl_hash": hash_val}).encode())
            LATEST_CODE_B64 = "" 
            
        elif parsed.path == '/api/assembly_state.json':
            self.send_response(200); self.send_header("Content-type", "application/json"); self._send_cors(); self.end_headers()
            self.wfile.write(json.dumps(PBR_STATE).encode('utf-8'))

        elif parsed.path == '/imported.stl':
            filepath = os.path.join(EXPORT_DIR, "imported.stl")
            data_to_send = DUMMY_VALID_STL
            if os.path.exists(filepath):
                try:
                    sz = os.path.getsize(filepath)
                    if sz >= 84:
                        with open(filepath, "rb") as f: data_to_send = f.read()
                except: pass
            self.send_response(200); self.send_header("Content-type", "model/stl"); self.send_header("Content-Length", str(len(data_to_send))); self.send_header("Cache-Control", "no-cache, no-store, must-revalidate"); self.send_header("Pragma", "no-cache"); self.send_header("Expires", "0"); self._send_cors(); self.end_headers()
            try:
                chunk_size = 65536
                for i in range(0, len(data_to_send), chunk_size): self.wfile.write(data_to_send[i:i+chunk_size])
            except: pass

        elif parsed.path.startswith('/descargar/'):
            filename = unquote(parsed.path.replace('/descargar/', ''))
            filepath = os.path.join(EXPORT_DIR, filename)
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    self.send_response(200); self.send_header("Content-Disposition", f'attachment; filename="{filename}"'); self._send_cors(); self.end_headers(); self.wfile.write(f.read())
            else: self.send_response(404); self._send_cors(); self.end_headers()
            
        elif parsed.path == '/' or parsed.path == '/openscad_engine.html':
            try:
                fn = "openscad_engine.html"
                with open(os.path.join(ASSETS_DIR, fn), "r", encoding="utf-8") as f: content = f.read()
                stl_path = os.path.join(EXPORT_DIR, "imported.stl")
                b64_stl = base64.b64encode(DUMMY_VALID_STL).decode('utf-8')
                if os.path.exists(stl_path) and os.path.getsize(stl_path) >= 84:
                    with open(stl_path, "rb") as stl_file: b64_stl = base64.b64encode(stl_file.read()).decode('utf-8')
                
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
                
                if "<head>" in content: content = content.replace("<head>", "<head>" + injector)
                else: content = injector + content
                    
                encoded_content = content.encode('utf-8')
                self.send_response(200); self.send_header("Content-type", "text/html"); self.send_header("Content-Length", str(len(encoded_content))); self._send_cors(); self.end_headers(); self.wfile.write(encoded_content)
                return
            except Exception as e:
                self.send_response(500); self._send_cors(); self.end_headers(); self.wfile.write(str(e).encode())

        elif parsed.path == '/nexus_pc.html':
            filepath = os.path.join(ASSETS_DIR, "nexus_pc.html")
            if not os.path.exists(filepath): 
                filepath = os.path.join(BASE_DIR, "nexus_pc.html")
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f: content = f.read().encode('utf-8')
                self.send_response(200); self.send_header("Content-type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(content))); self._send_cors(); self.end_headers(); self.wfile.write(content)
            else: 
                self.send_response(404); self._send_cors(); self.end_headers()
            return

        else:
            try:
                fn = parsed.path.strip("/")
                filepath = os.path.join(ASSETS_DIR, fn)
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    with open(filepath, "rb") as f:
                        self.send_response(200)
                        if fn.endswith(".html"): self.send_header("Content-type", "text/html; charset=utf-8")
                        elif fn.endswith(".js"): self.send_header("Content-type", "application/javascript")
                        elif fn.endswith(".css"): self.send_header("Content-type", "text/css")
                        elif fn.endswith(".png"): self.send_header("Content-type", "image/png")
                        elif fn.endswith(".stl"): self.send_header("Content-type", "model/stl")
                        else: self.send_header("Content-type", "text/plain")
                        self._send_cors(); self.end_headers(); self.wfile.write(f.read())
                else:
                    self.send_response(404); self._send_cors(); self.end_headers()
            except Exception as e:
                self.send_response(500); self._send_cors(); self.end_headers()
            
    def log_message(self, *args): pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

threading.Thread(target=lambda: ThreadedHTTPServer(("0.0.0.0", LOCAL_PORT), NexusHandler).serve_forever(), daemon=True).start()

# =========================================================
# APP FLET MAIN (ARQUITECTURA DE LOS 3 PILARES)
# =========================================================
def main(page: ft.Page):
    try:
        page.title = lang.t("app_title")
        page.theme_mode = "dark"
        page.bgcolor = "#0B0E14" 
        page.padding = 0 
        
        status = ft.Text(lang.t("app_title"), color="#00E676", weight="bold")

        def custom_icon_btn(text, action, tooltip_txt): 
            return ft.Container(content=ft.Text(text, size=16), padding=5, bgcolor="#30363D", border_radius=5, on_click=action, tooltip=tooltip_txt, ink=True)

        T_INICIAL = "function main() {\n  var pieza = CSG.cube({center:[0,0,GH/2], radius:[GW/2, GL/2, GH/2]});\n  return pieza;\n}"
        txt_code = ft.TextField(label="Código Fuente (JS-CSG)", multiline=True, expand=True, value=T_INICIAL, bgcolor="#161B22", color="#58A6FF", border_color="#30363D", text_size=12)

        ensamble_stack = []; herramienta_actual = "custom"; modo_ensamble = False

        # ==========================================
        # CONTROL DE NAVEGACIÓN Y PILARES
        # ==========================================
        # 0=IA, 1=CODE, 2=PARAM, 3=3D, 4=ENS, 5=PBR, 6=FILES
        def navigate_to(target_idx):
            global PBR_STATE
            if target_idx in [0, 1, 2, 3]: PBR_STATE["mode"] = "single"
            if target_idx == 4: render_assembly_ui()
            if target_idx == 6: refresh_nexus_db(); refresh_explorer(current_android_dir)

            if target_idx == 0: set_main_pillar(0); set_studio_tab(0)      # IA
            elif target_idx == 1: set_main_pillar(0); set_studio_tab(2)    # CODE
            elif target_idx == 2: set_main_pillar(0); set_studio_tab(1)    # PARAM
            elif target_idx == 3: set_main_pillar(1); set_vis_tab(0)       # 3D
            elif target_idx == 4: set_main_pillar(2); set_lab_tab(1)       # ENS
            elif target_idx == 5: set_main_pillar(1); set_vis_tab(1)       # PBR
            elif target_idx == 6: set_main_pillar(2); set_lab_tab(0)       # FILES

        def set_tab_wrapper(idx): 
            # Traductor de Nexus UI Tools hacia los nuevos pilares
            traduccion_indices = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}
            navigate_to(traduccion_indices.get(idx, idx))

        def check_ia_injection():
            global INJECTED_CODE_IA, AGENTIC_PAYLOAD
            while True:
                time.sleep(1)
                
                if INJECTED_CODE_IA:
                    txt_code.value = INJECTED_CODE_IA
                    INJECTED_CODE_IA = ""
                    try: txt_code.update()
                    except Exception: pass
                    status.value = "✓ Código inyectado."
                    status.color = "#00E5FF"
                    page.update()
                
                if AGENTIC_PAYLOAD is not None:
                    try:
                        payload = AGENTIC_PAYLOAD
                        AGENTIC_PAYLOAD = None 
                        
                        tool_name = payload.get("tool", "gear")
                        params = payload.get("params", {})
                        
                        select_tool(tool_name)
                        for key, val in params.items():
                            slider_name = f"sl_{key}"
                            if hasattr(tools_lib, slider_name):
                                slider_obj = getattr(tools_lib, slider_name)
                                slider_obj.value = float(val)
                        
                        update_code_wrapper(None)
                        run_render()
                        status.value = "🎛️ AGENTIC UI: Interfaz ajustada."
                        status.color = "#00E676"
                        page.update()
                    except Exception as e: print(f"Error Agentic Payload: {e}")
                    
        threading.Thread(target=check_ia_injection, daemon=True).start()

        def clear_editor():
            nonlocal ensamble_stack
            ensamble_stack = []
            txt_code.value = "function main() {\n  return CSG.cube({radius:[0.01,0.01,0.01]});\n}"
            status.value = "✓ Código borrado."; status.color = "#B71C1C"
            try: txt_code.update()
            except Exception: pass
            page.update()

        def update_code_wrapper(e=None): 
            if not modo_ensamble: generate_param_code()

        def create_slider(label, min_v, max_v, val, is_int):
            txt_val = ft.Text(f"{int(val) if is_int else val:.1f}", color="#00E5FF", width=45, text_align="right", size=13, weight="bold")
            sl = ft.Slider(min=min_v, max=max_v, value=val, expand=True, active_color="#00E5FF", inactive_color="#2A303C")
            if is_int: sl.divisions = int(max_v - min_v)
            def internal_change(e):
                txt_val.value = f"{int(sl.value) if is_int else sl.value:.1f}"; txt_val.update(); 
                if not modo_ensamble: update_code_wrapper()
            sl.on_change = internal_change
            return sl, ft.Row([ft.Text(label, width=110, size=12, color="#E6EDF3"), sl, txt_val])

        sl_g_w, r_g_w = create_slider("Ancho (GW)", 1, 300, 50, False); sl_g_l, r_g_l = create_slider("Largo (GL)", 1, 300, 50, False); sl_g_h, r_g_h = create_slider("Alto (GH)", 1, 300, 20, False); sl_g_t, r_g_t = create_slider("Grosor (GT)", 0.5, 20, 2, False); sl_g_tol, r_g_tol = create_slider("Tol. Global (G_TOL)", 0.0, 2.0, 0.2, False); sl_kine, r_kine = create_slider("Animación (º)", 0, 360, 0, True)

        dd_mat = ft.Dropdown(options=[ft.dropdown.Option("PLA Gris Mate"), ft.dropdown.Option("PETG Transparente"), ft.dropdown.Option("Fibra de Carbono"), ft.dropdown.Option("Aluminio Mecanizado"), ft.dropdown.Option("Madera Bambú"), ft.dropdown.Option("Oro Puro"), ft.dropdown.Option("Neón Cyan")], value="PLA Gris Mate", bgcolor="#161B22", color="#00E5FF", expand=True, text_size=12); dd_mat.on_change = update_code_wrapper

        def prepare_js_payload():
            c_val = {"PLA Gris Mate": "[0.5, 0.5, 0.5, 1.0]", "PETG Transparente": "[0.8, 0.9, 0.9, 0.45]", "Fibra de Carbono": "[0.15, 0.15, 0.15, 1.0]", "Aluminio Mecanizado": "[0.7, 0.75, 0.8, 1.0]", "Madera Bambú": "[0.6, 0.4, 0.2, 1.0]", "Oro Puro": "[0.9, 0.75, 0.1, 1.0]", "Neón Cyan": "[0.0, 1.0, 1.0, 0.8]"}.get(dd_mat.value, "[0.5, 0.5, 0.5, 1.0]")
            header = f"  var GW = {sl_g_w.value}; var GL = {sl_g_l.value}; var GH = {sl_g_h.value}; var GT = {sl_g_t.value}; var G_TOL = {sl_g_tol.value}; var KINE_T = {sl_kine.value}; var MAT_C = {c_val};\n"
            utils_block = """  if(typeof CSG !== 'undefined' && typeof CSG.Matrix4x4 === 'undefined' && typeof Matrix4x4 !== 'undefined') { CSG.Matrix4x4 = Matrix4x4; }
  var UTILS = { 
    trans: function(o, v) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.trans(x, v);}); if(typeof o.translate === 'function') return o.translate(v); if(typeof translate !== 'undefined') return translate(v, o); } catch(e) {} return o; },
    scale: function(o, v) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.scale(x, v);}); if(typeof o.scale === 'function') return o.scale(v); if(typeof scale !== 'undefined') return scale(v, o); } catch(e) {} return o; },
    rotZ: function(o, d) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.rotZ(x, d);}); if(typeof o.rotateZ === 'function') return o.rotateZ(d); if(typeof rotate !== 'undefined') return rotate([0,0,d], o); } catch(e) {} return o; },
    rotX: function(o, d) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.rotX(x, d);}); if(typeof o.rotateX === 'function') return o.rotateX(d); if(typeof rotate !== 'undefined') return rotate([d,0,0], o); } catch(e) {} return o; },
    rotY: function(o, d) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.rotY(x, d);}); if(typeof o.rotateY === 'function') return o.rotateY(d); if(typeof rotate !== 'undefined') return rotate([0,d,0], o); } catch(e) {} return o; },
    mat: function(o) { if(!o) return CSG.cube({radius:[0.01,0.01,0.01]}); try { if(Array.isArray(o)) return o.map(function(x){return UTILS.mat(x);}); if(typeof o.setColor === 'function') return o.setColor(MAT_C); } catch(e) {} return o; } 
  };\n"""
            header += utils_block
            param_def = "function getParameterDefinitions() { return [{name: 'KINE_T', type: 'slider', initial: 0, min: 0, max: 360, step: 1, caption: 'Cinemática (º)'}]; }\n"
            c = txt_code.value
            if "getParameterDefinitions" not in c:
                if "function main(" in c: c = param_def + c.replace("function main(params) {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1).replace("function main() {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1)
                else: c = param_def + header + "\n" + c
            else:
                if "function main(" in c: c = c.replace("function main(params) {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1).replace("function main() {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1)
                else: c = header + "\n" + c
            return c

        def run_render():
            global LATEST_CODE_B64, LATEST_NEEDS_STL
            
            # 🔥 Inyectamos el Javascript al WebView para que muestre el Loader al instante
            try:
                page.evaluate_javascript("window.showWorkerLoader('ENSAMBLANDO PIEZAS...');")
            except Exception as e:
                print(f"Aviso de inyección JS: {e}")

            js_payload = prepare_js_payload()
            LATEST_CODE_B64 = base64.b64encode(js_payload.encode('utf-8')).decode()
            LATEST_NEEDS_STL = ("IMPORTED_STL" in js_payload) or herramienta_actual.startswith("stl")
            navigate_to(3) # Va al visor 3D

        sw_ensamble = ft.Switch(label="Manejo Código Ensamblador", value=False, active_color="#FFAB00")
        
        def parse_current_tool_to_stack_var():
            code_lines = txt_code.value.split('\n')
            var_name = f"obj_{len(ensamble_stack)}"; body = []
            for line in code_lines[1:-1]:
                if line.strip().startswith("return "):
                    ret_val = line.replace("return UTILS.mat(", "").replace("return ", "").replace(");", "").replace(";", "").strip()
                    body.append(f"  var {var_name} = {ret_val};")
                else: body.append(line)
            return "\n".join(body), var_name

        def add_to_stack(op_type):
            nonlocal ensamble_stack
            body, var_name = parse_current_tool_to_stack_var()
            if not ensamble_stack: ensamble_stack.append({"body": body, "var": var_name, "op": "base"})
            else: ensamble_stack.append({"body": body, "var": var_name, "op": op_type})
            compile_stack_to_editor()

        def compile_stack_to_editor():
            if not ensamble_stack: return
            final_code = "function main() {\n"
            final_var = ""
            for i, item in enumerate(ensamble_stack):
                final_code += f"  // --- Modificador {i} ({item['op']}) ---\n{item['body']}\n"
                if item["op"] == "base": final_var = item["var"]
                elif item["op"] == "union": final_code += f"  {final_var} = {final_var}.union({item['var']});\n"
                elif item["op"] == "subtract": final_code += f"  {final_var} = {final_var}.subtract({item['var']});\n"
            final_code += f"  return UTILS.mat({final_var});\n}}"
            txt_code.value = final_code
            try: txt_code.update()
            except Exception: pass
            page.update()

        panel_ensamble_ops = ft.Row([
            ft.ElevatedButton(content=ft.Text("➕ UNIR", color="white"), on_click=lambda _: add_to_stack("union"), bgcolor="#1B5E20", expand=True),
            ft.ElevatedButton(content=ft.Text("➖ RESTAR", color="white"), on_click=lambda _: add_to_stack("subtract"), bgcolor="#B71C1C", expand=True)
        ], visible=False)

        def toggle_ensamble(e):
            nonlocal modo_ensamble
            modo_ensamble = sw_ensamble.value
            panel_ensamble_ops.visible = modo_ensamble
            page.update()
            
        sw_ensamble.on_change = toggle_ensamble

        panel_globales = ft.Container(content=ft.Column([
            ft.Row([ft.Text("🌐 PARÁMETROS", color="#00E5FF", weight="bold", size=11), sw_ensamble], alignment="spaceBetween"), 
            r_g_w, r_g_l, r_g_h, r_g_t, r_g_tol, ft.Divider(color="#333333"), 
            ft.Row([ft.Text("🎨 TEXTURA:", color="#E6EDF3", size=11, width=130), dd_mat]), ft.Divider(color="#333333"), 
            ft.Text("🎬 CINEMÁTICA", color="#B388FF", weight="bold", size=11), r_kine,
            panel_ensamble_ops
        ]), bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#333333"))

        def select_tool(nombre_herramienta):
            nonlocal herramienta_actual
            herramienta_actual = nombre_herramienta
            for k, p in tools_lib.tool_panels.items(): p.visible = (k == nombre_herramienta)
            tools_lib.panel_stl_transform.visible = nombre_herramienta.startswith("stl")
            generate_param_code(); page.update()

        tools_lib = nexus_ui_tools.NexusTools(create_slider, update_code_wrapper, set_tab_wrapper, select_tool)

        def generate_param_code():
            try: importlib.reload(param_generators)
            except Exception as e: print(f"Error recargando param_generators: {e}")
                
            h = herramienta_actual
            if h == "custom": return
            p_dict = tools_lib.get_p_dict()
            txt_code.value = param_generators.get_code(h, p_dict)
            try: txt_code.update()
            except Exception: pass

        # ==========================================
        # VISTAS SECUNDARIAS
        # ==========================================
        view_ia = ft.Column([
            ft.Container(height=20), ft.Text("🤖 AGENTE IA ACTIVO", size=22, color="#B388FF", weight="bold", text_align="center"), ft.Text("Asistente Copilot y Generador Agentic.", color="#E6EDF3", text_align="center"), ft.Container(height=20), ft.ElevatedButton("🚀 ABRIR ENTORNO IA", url=f"http://{INTERNAL_IP}:{LOCAL_PORT}/ia_assistant.html", bgcolor="#8E24AA", color="white", height=70, width=float('inf')), ft.Container(height=10), ft.Text("💡 El análisis ocurre en segundo plano. Usa las pestañas de arriba para ver el código o los parámetros.", color="#8B949E", size=12, text_align="center")
        ], expand=True, horizontal_alignment="center")

        view_constructor = ft.Column([
            panel_globales, 
            ft.Text("💡 Opciones:", size=12, color="#8B949E"), tools_lib.cat_especial,
            ft.Text("📐 Bocetos:", size=12, color="#2962FF", weight="bold"), tools_lib.cat_bocetos,
            ft.Text("⚔️ STL FORGE:", size=12, color="#00E676", weight="bold"), tools_lib.cat_stl_forge,
            ft.Text("🏭 Producción:", size=12, color="#00B0FF"), tools_lib.cat_produccion,
            ft.Text("🌪️ Formas:", size=12, color="#D50000"), tools_lib.cat_lofting,
            ft.Text("⚙️ Mecánica:", size=12, color="#FF9100"), tools_lib.cat_engranajes, tools_lib.cat_mecanismos,
            ft.Text("📦 Básico:", size=12, color="#8B949E"), tools_lib.cat_basico,
            ft.Divider(color="#30363D"), tools_lib.panel_stl_transform,
            *tools_lib.tool_panels.values(),
            ft.ElevatedButton("▶ RENDER 3D", on_click=lambda _: run_render(), bgcolor="#00E676", color="black", height=50, width=float('inf'))
        ], expand=True, scroll="auto")

        view_editor = ft.Column([
            ft.Row([ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save_project_to_nexus(), bgcolor="#0D47A1", color="white"), ft.ElevatedButton("🗑️ RESET", on_click=lambda _: clear_editor(), bgcolor="#B71C1C", color="white")], scroll="auto"),
            txt_code
        ], expand=True)

        view_visor = ft.Column([
            ft.Container(height=5),
            ft.Container(content=ft.Column([
                ft.Text("🥽 VISOR EXTERNO", color="#B388FF", weight="bold", size=11),
                ft.TextField(value=f"http://{LAN_IP}:{LOCAL_PORT}/openscad_engine.html", read_only=True, text_size=13, text_align="center", bgcolor="#161B22", color="#00E676"),
                ft.Text("☁️ NEXUS PC", color="#00E5FF", weight="bold", size=11),
                ft.TextField(value=f"http://{LAN_IP}:{LOCAL_PORT}/nexus_pc.html", read_only=True, text_size=13, text_align="center", bgcolor="#161B22", color="#00E5FF")
            ]), bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#00E5FF")),
            ft.Container(height=5),
            ft.ElevatedButton("🔄 ABRIR VISOR 3D NATIVO", url=f"http://{INTERNAL_IP}:{LOCAL_PORT}/openscad_engine.html", bgcolor="#00E676", color="black", height=60, width=float('inf')),
        ], expand=True, scroll="auto")
        
        def build_static_assembly_cards():
            cards = []
            for i in range(MAX_ASSEMBLY_PARTS):
                df = ft.Dropdown(options=[], width=160, text_size=12, bgcolor="#0B0E14", color="#00E5FF"); dm = ft.Dropdown(options=[ft.dropdown.Option("pla"), ft.dropdown.Option("petg"), ft.dropdown.Option("carbon"), ft.dropdown.Option("glass"), ft.dropdown.Option("aluminum"), ft.dropdown.Option("copper"), ft.dropdown.Option("wood"), ft.dropdown.Option("gold")], value="pla", width=100, text_size=12, bgcolor="#0B0E14")
                sl_x = ft.Slider(min=-200, max=200, value=0, expand=True); sl_y = ft.Slider(min=-200, max=200, value=0, expand=True); sl_z = ft.Slider(min=-200, max=200, value=0, expand=True)
                card = ft.Container(bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#C51162"), visible=False)
                def make_change_handler(idx, d_f, d_m, s_x, s_y, s_z):
                    def handler(e):
                        if not ASSEMBLY_PARTS_STATE[idx]["active"]: return
                        ASSEMBLY_PARTS_STATE[idx]["file"] = d_f.value; ASSEMBLY_PARTS_STATE[idx]["mat"] = d_m.value; ASSEMBLY_PARTS_STATE[idx]["x"] = s_x.value; ASSEMBLY_PARTS_STATE[idx]["y"] = s_y.value; ASSEMBLY_PARTS_STATE[idx]["z"] = s_z.value; update_pbr_state()
                    return handler
                change_handler = make_change_handler(i, df, dm, sl_x, sl_y, sl_z)
                df.on_change = change_handler; dm.on_change = change_handler; sl_x.on_change = change_handler; sl_y.on_change = change_handler; sl_z.on_change = change_handler
                def make_delete_handler(idx, c):
                    def handler(e): ASSEMBLY_PARTS_STATE[idx]["active"] = False; c.visible = False; update_pbr_state(); check_empty_assembly(); page.update()
                    return handler
                btn_del = ft.Container(content=ft.Text("🗑️", size=16), padding=5, bgcolor="#30363D", border_radius=5, on_click=make_delete_handler(i, card), ink=True)
                card.content = ft.Column([ft.Row([df, dm, btn_del], alignment="spaceBetween"), ft.Row([ft.Text("X", size=10, color="#8B949E", width=15), sl_x]), ft.Row([ft.Text("Y", size=10, color="#8B949E", width=15), sl_y]), ft.Row([ft.Text("Z", size=10, color="#8B949E", width=15), sl_z])])
                def refresh_opts(d=df, idx=i):
                    files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
                    d.options = [ft.dropdown.Option(f) for f in files]
                    if not d.value and files: d.value = files[0]
                    elif d.value not in files and files: d.value = files[0]
                    if files: ASSEMBLY_PARTS_STATE[idx]["file"] = d.value
                card.data = {"refresh": refresh_opts, "df": df, "dm": dm, "sx": sl_x, "sy": sl_y, "sz": sl_z}; cards.append(card)
            return cards

        col_assembly_cards = build_static_assembly_cards()
        lbl_ensamble_warn = ft.Text("⚠️ DB vacía. Sube STLs en Archivos.", color="#FFAB00", weight="bold", visible=False)
        col_assembly = ft.Column([lbl_ensamble_warn] + col_assembly_cards, scroll="auto", expand=True)

        def check_empty_assembly():
            has_active = any(p["active"] for p in ASSEMBLY_PARTS_STATE)
            files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
            lbl_ensamble_warn.visible = not has_active and not files

        def add_assembly_part(e):
            files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
            if not files: status.value = "❌ Sube archivos en la pestaña GESTOR primero."; status.color = "#FF5252"; page.update(); return
            for i in range(MAX_ASSEMBLY_PARTS):
                if not ASSEMBLY_PARTS_STATE[i]["active"]:
                    ASSEMBLY_PARTS_STATE[i]["active"] = True; card = col_assembly_cards[i]; card.data["refresh"](); card.data["sx"].value = 0; card.data["sy"].value = 0; card.data["sz"].value = 0
                    ASSEMBLY_PARTS_STATE[i]["x"] = 0; ASSEMBLY_PARTS_STATE[i]["y"] = 0; ASSEMBLY_PARTS_STATE[i]["z"] = 0; ASSEMBLY_PARTS_STATE[i]["mat"] = card.data["dm"].value
                    card.visible = True; update_pbr_state(); check_empty_assembly(); page.update(); return
            status.value = "❌ Límite (10) alcanzado."; status.color = "#FFAB00"; page.update()

        def render_assembly_ui():
            files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
            if not files: lbl_ensamble_warn.visible = True; [col_assembly_cards[i].__setattr__('visible', False) or ASSEMBLY_PARTS_STATE.__setitem__(i, {**ASSEMBLY_PARTS_STATE[i], "active":False}) for i in range(MAX_ASSEMBLY_PARTS)]
            else:
                lbl_ensamble_warn.visible = not any(p["active"] for p in ASSEMBLY_PARTS_STATE)
                for i, card in enumerate(col_assembly_cards):
                    if ASSEMBLY_PARTS_STATE[i]["active"]: card.data["refresh"]()

        view_ensamble = ft.Column([ft.Text("🧩 MESA DE ENSAMBLAJE", size=20, color="#FFAB00", weight="bold"), ft.Row([ft.ElevatedButton("➕ AÑADIR PIEZA", on_click=add_assembly_part, bgcolor="#1B5E20", color="white"), ft.ElevatedButton("👁️ VER PBR", on_click=lambda _: navigate_to(5), bgcolor="#C51162", color="white")]), ft.Divider(), col_assembly], expand=True)

        view_pbr = ft.Column([ft.Container(height=20), ft.Text("🎨 PBR STUDIO PRO", size=22, color="#FF007F", weight="bold", text_align="center"), ft.Text("Render Físico Realista.", color="#E6EDF3", text_align="center"), ft.Container(height=20), ft.ElevatedButton("🚀 ABRIR PBR STUDIO", url=f"http://{INTERNAL_IP}:{LOCAL_PORT}/pbr_studio.html", bgcolor="#C51162", color="white", height=70, width=float('inf'))], expand=True, horizontal_alignment="center")

        txt_dim_x = ft.Text("0.0 mm", color="#00E5FF", weight="bold"); txt_dim_y = ft.Text("0.0 mm", color="#00E5FF", weight="bold"); txt_dim_z = ft.Text("0.0 mm", color="#00E5FF", weight="bold"); txt_vol = ft.Text("0.0 cm³", color="#FFAB00", weight="bold"); txt_peso = ft.Text("0.0 g", color="#00E676", weight="bold")
        panel_calibre = ft.Container(content=ft.Column([ft.Text("📐 CALIBRE 3D", color="#E6EDF3", weight="bold"), ft.Row([ft.Text("X:", color="#8B949E", width=20), txt_dim_x, ft.Text("Y:", color="#8B949E", width=20), txt_dim_y]), ft.Row([ft.Text("Z:", color="#8B949E", width=20), txt_dim_z, ft.Text("Vol:", color="#8B949E", width=25), txt_vol])]), bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#2962FF"))

        rename_target = ""
        tf_rename = ft.TextField(label="Nuevo nombre", bgcolor="#161B22", color="#00E5FF")
        
        def open_rename_dialog(filename):
            global rename_target; rename_target = filename; tf_rename.value = filename; dialog_rename.open = True; page.update()

        def confirm_rename(e):
            global rename_target
            new_name = tf_rename.value.strip()
            if new_name and new_name != rename_target:
                if rename_target.lower().endswith(".stl") and not new_name.lower().endswith(".stl"): new_name += ".stl"
                if rename_target.lower().endswith(".jscad") and not new_name.lower().endswith(".jscad"): new_name += ".jscad"
                try: os.rename(os.path.join(EXPORT_DIR, rename_target), os.path.join(EXPORT_DIR, new_name)); status.value = f"✓ Renombrado"; status.color = "#00E676"
                except Exception as ex: status.value = f"❌ Error: {ex}"; status.color = "red"
            dialog_rename.open = False; refresh_nexus_db(); page.update()

        dialog_rename = ft.AlertDialog(title=ft.Text("Renombrar", color="#00E5FF"), content=tf_rename, actions=[ft.TextButton("Cancelar", on_click=lambda e: [setattr(dialog_rename, 'open', False), page.update()]), ft.ElevatedButton("Guardar", on_click=confirm_rename, bgcolor="#00E676", color="black")])
        page.overlay.append(dialog_rename)

        list_nexus_db = ft.ListView(height=200, spacing=5)

        def direct_download_file(e, filename):
            try: os.makedirs(DOWNLOAD_DIR, exist_ok=True); shutil.copy(os.path.join(EXPORT_DIR, filename), os.path.join(DOWNLOAD_DIR, filename)); status.value = f"✓ Guardado en Descargas."; status.color = "#00E676"
            except Exception as ex: status.value = f"❌ Error: {ex}"; status.color = "#FF5252"
            page.update()
            
        def export_obj_file(e, filename):
            os.makedirs(DOWNLOAD_DIR, exist_ok=True); success, msg = convert_stl_to_obj(os.path.join(EXPORT_DIR, filename), os.path.join(DOWNLOAD_DIR, filename.replace('.stl', '.obj')))
            status.value = f"✓ OBJ exportado." if success else f"❌ Error OBJ: {msg}"; status.color = "#00E5FF" if success else "#FF5252"; page.update()

        def refresh_nexus_db():
            list_nexus_db.controls.clear()
            try:
                files = [f for f in os.listdir(EXPORT_DIR) if not f.startswith('.') and f != "imported.stl"]
                if not files: list_nexus_db.controls.append(ft.Text("Vacío. Importa archivos.", color="#8B949E", italic=True))
                for f in files:
                    ext = f.lower().split('.')[-1]; p = os.path.join(EXPORT_DIR, f)
                    icon = "🧊" if ext=="stl" else ("🖼️" if ext=="png" else "🧩"); color = "#00E676" if ext=="stl" else ("#C51162" if ext=="png" else "white")
                    actions = [custom_icon_btn("✏️", lambda e, fn=f: open_rename_dialog(fn), "Renombrar"), custom_icon_btn("⬇️", lambda e, fn=f: direct_download_file(e, fn), "Bajar"), custom_icon_btn("🗑️", lambda e, fp=p: [os.remove(fp), refresh_nexus_db()], "Borrar")]
                    if ext == "stl": actions.insert(0, custom_icon_btn("📦", lambda e, fn=f: export_obj_file(e, fn), "OBJ")); actions.insert(0, custom_icon_btn("▶️", lambda e, fp=p: load_file(fp), "Cargar STL"))
                    elif ext == "jscad": actions.insert(0, custom_icon_btn("▶️", lambda e, fp=p: load_file(fp), "Cargar Código"))
                    list_nexus_db.controls.append(ft.Container(content=ft.Row([ft.Text(icon, size=20), ft.Text(f, color=color, weight="bold", expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)] + actions), bgcolor="#21262D", padding=5, border_radius=5))
            except Exception as e: list_nexus_db.controls.append(ft.Text(f"Error DB: {e}"))
            page.update()

        def load_file(filepath):
            fn = os.path.basename(filepath); ext = fn.lower().split('.')[-1]
            if ext == "stl":
                is_valid, msg = validate_stl(filepath)
                if not is_valid: status.value = f"❌ {msg}"; status.color = "#FF5252"; page.update(); return
                metrics = analyze_stl(filepath)
                if metrics:
                    txt_dim_x.value = f"{metrics['dx']} mm"; txt_dim_y.value = f"{metrics['dy']} mm"; txt_dim_z.value = f"{metrics['dz']} mm"
                    txt_vol.value = f"{metrics['vol_cm3']} cm³"; txt_peso.value = f"{metrics['weight_g']} g"
                shutil.copy(filepath, os.path.join(EXPORT_DIR, "imported.stl")); lbl_stl_status = tools_lib.lbl_stl_status; lbl_stl_status.value = f"✓ Activo: {fn}"; lbl_stl_status.color = "#00E676"
                select_tool("stl"); navigate_to(2); update_code_wrapper(); status.value = f"✓ STL Inyectado"
            elif ext == "jscad": txt_code.value = open(filepath).read(); navigate_to(1); status.value = "✓ Código Cargado"
            page.update()

        current_android_dir = ANDROID_ROOT
        tf_path = ft.TextField(value=current_android_dir, expand=True, bgcolor="#161B22", height=40, text_size=12); list_android = ft.ListView(height=300, spacing=5)

        def file_action(filepath):
            ext = filepath.lower().split('.')[-1] if '.' in filepath else ''
            if ext in ["stl", "jscad"]: load_file(filepath)
            else: status.value = f"⚠️ Formato no soportado."; status.color = "#FFAB00"; page.update()

        def copy_to_db(e, filepath, filename):
            try: shutil.copy(filepath, os.path.join(EXPORT_DIR, filename)); status.value = f"✓ {filename} importado."; status.color = "#00E676"; refresh_nexus_db()
            except Exception as ex: status.value = f"❌ Error: {ex}"; status.color = "red"
            page.update()

        def refresh_explorer(path):
            list_android.controls.clear()
            try:
                items = os.listdir(path); dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]; files = [f for f in items if os.path.isfile(os.path.join(path, f))]; dirs.sort(); files.sort()
                if path != "/" and path != "/storage" and path != "/storage/emulated": list_android.controls.append(ft.Container(content=ft.Row([ft.Text("⬆️", size=20), ft.Text(".. (Subir)", color="white", expand=True)]), bgcolor="#30363D", padding=5, border_radius=5, on_click=lambda e: nav_to(os.path.dirname(path)), ink=True))
                for d in dirs:
                    if not d.startswith('.'): list_android.controls.append(ft.Container(content=ft.Row([ft.Text("📁", size=20), ft.Text(d, color="#E6EDF3", expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS), custom_icon_btn("➡️", lambda e, p=os.path.join(path, d): nav_to(p), "Entrar")]), bgcolor="#161B22", padding=5, border_radius=5, on_click=lambda e, p=os.path.join(path, d): nav_to(p), ink=True))
                for f in files:
                    ext = f.lower().split('.')[-1] if '.' in f else ''; icon = "📄"; color = "#8B949E"
                    if ext == "stl": icon = "🧊"; color = "#00E676"
                    elif ext == "jscad": icon = "🧩"; color = "#00E5FF"
                    elif ext == "png": icon = "🖼️"; color = "#C51162"
                    p = os.path.join(path, f)
                    actions = [custom_icon_btn("▶️", lambda e, fp=p: file_action(fp), "Cargar"), custom_icon_btn("📥", lambda e, fp=p, fn=f: copy_to_db(e, fp, fn), "Importar")]
                    list_android.controls.append(ft.Container(content=ft.Row([ft.Text(icon, size=20), ft.Text(f, color=color, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)] + actions), bgcolor="#21262D", padding=5, border_radius=5))
            except Exception as ex: list_android.controls.append(ft.Text(f"Error: {ex}", color="red"))
            tf_path.value = path; page.update()

        def nav_to(path): nonlocal current_android_dir; current_android_dir = path; refresh_explorer(path)
        def save_to_android(e):
            if not os.path.isdir(current_android_dir): return
            fname = f"nexus_{int(time.time())}.jscad"
            try:
                with open(os.path.join(current_android_dir, fname), "w") as f: f.write(txt_code.value)
                status.value = f"✓ Guardado: {fname}"; status.color = "#00E676"; refresh_explorer(current_android_dir)
            except Exception as ex: status.value = f"❌ Error: {ex}"; status.color = "red"
            page.update()

        def save_project_to_nexus():
            fname = f"nexus_{int(time.time())}.jscad"
            with open(os.path.join(EXPORT_DIR, fname), "w") as f: f.write(txt_code.value)
            status.value = f"✓ Guardado en DB: {fname}"; page.update()

        row_quick_paths = ft.Row([ft.ElevatedButton("🏠 Android", on_click=lambda _: nav_to("/storage/emulated/0"), bgcolor="#21262D", color="white"), ft.ElevatedButton("📥 Descargas", on_click=lambda _: nav_to("/storage/emulated/0/Download"), bgcolor="#21262D", color="white"), ft.ElevatedButton("📁 Nexus DB", on_click=lambda _: nav_to(EXPORT_DIR), bgcolor="#1B5E20", color="white")], scroll="auto")
        
        view_archivos = ft.Column([
            panel_calibre,
            ft.Container(content=ft.Column([ft.Row([ft.Text("🌐 DB INTERNA", color="#00E676", weight="bold"), ft.ElevatedButton("🔄", on_click=lambda _: refresh_nexus_db(), bgcolor="#1E1E1E", width=50)], alignment="spaceBetween"), ft.ElevatedButton("🌐 ABRIR INYECTOR WEB", url=f"http://{INTERNAL_IP}:{LOCAL_PORT}/upload_ui.html", bgcolor="#00B0FF", color="white", width=float('inf')), ft.Container(content=list_nexus_db, bgcolor="#0B0E14", border_radius=5, padding=5)]), bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#00E676")),
            ft.Container(content=ft.Column([ft.Text("📱 EXPLORADOR NATIVO", color="#00E5FF", weight="bold"), row_quick_paths, ft.Row([tf_path, ft.ElevatedButton("Ir", on_click=lambda _: nav_to(tf_path.value), bgcolor="#FFAB00", color="black")]), ft.ElevatedButton("💾 GUARDAR CÓDIGO AQUÍ", on_click=save_to_android, bgcolor="#0D47A1", color="white", width=float('inf')), ft.Container(content=list_android, bgcolor="#0B0E14", border_radius=5, padding=5)]), bgcolor="#161B22", padding=10, border_radius=8)
        ], expand=True, scroll="auto")


        # ==========================================
        # CONSTRUCCIÓN DE LOS 3 PILARES PRINCIPALES
        # ==========================================

        # --- ETIQUETAS DINÁMICAS DE IDIOMA ---
        lbl_nav_studio = ft.Text(lang.t("nav_studio"), weight="bold")
        lbl_nav_view = ft.Text(lang.t("nav_view"), weight="bold", color="black")
        lbl_nav_lab = ft.Text(lang.t("nav_lab"), weight="bold")

        lbl_sub_ia = ft.Text(lang.t("btn_ia"), weight="bold")
        lbl_sub_sliders = ft.Text(lang.t("btn_sliders"), weight="bold", color="black")
        lbl_sub_code = ft.Text(lang.t("btn_code"), weight="bold")

        lbl_sub_3d = ft.Text(lang.t("btn_3d"), weight="bold", color="black")
        lbl_sub_pbr = ft.Text(lang.t("btn_pbr"), weight="bold")

        lbl_sub_db = ft.Text(lang.t("btn_db"), weight="bold")
        lbl_sub_assemble = ft.Text(lang.t("btn_assemble"), weight="bold")

        lbl_info = ft.Text(lang.t("btn_info"), color="#FFAB00", weight="bold")
        lbl_lang = ft.Text(lang.t("btn_lang"), color="white", weight="bold")


        # --- PILAR 1: STUDIO ---
        studio_content = ft.Container(content=view_ia, expand=True)
        def set_studio_tab(idx):
            studio_content.content = [view_ia, view_constructor, view_editor][idx]
            if studio_content.page: page.update()
            
        nav_studio = ft.Row([
            ft.ElevatedButton(content=lbl_sub_ia, on_click=lambda _: set_studio_tab(0), bgcolor="#8E24AA", color="white", expand=True),
            ft.ElevatedButton(content=lbl_sub_sliders, on_click=lambda _: set_studio_tab(1), bgcolor="#FFAB00", expand=True),
            ft.ElevatedButton(content=lbl_sub_code, on_click=lambda _: set_studio_tab(2), bgcolor="#21262D", color="white", expand=True),
        ])
        pillar_studio = ft.Column([nav_studio, ft.Divider(height=2, color="#30363D"), studio_content], expand=True)

        # --- PILAR 2: VISUALIZAR ---
        vis_content = ft.Container(content=view_visor, expand=True)
        def set_vis_tab(idx):
            vis_content.content = [view_visor, view_pbr][idx]
            if vis_content.page: page.update()

        nav_vis = ft.Row([
            ft.ElevatedButton(content=lbl_sub_3d, on_click=lambda _: set_vis_tab(0), bgcolor="#00E5FF", expand=True),
            ft.ElevatedButton(content=lbl_sub_pbr, on_click=lambda _: set_vis_tab(1), bgcolor="#C51162", color="white", expand=True),
        ])
        pillar_vis = ft.Column([nav_vis, ft.Divider(height=2, color="#30363D"), vis_content], expand=True)

        # --- PILAR 3: LABORATORIO ---
        lab_content = ft.Container(content=view_archivos, expand=True)
        def set_lab_tab(idx):
            lab_content.content = [view_archivos, view_ensamble][idx]
            if lab_content.page: page.update()

        nav_lab = ft.Row([
            ft.ElevatedButton(content=lbl_sub_db, on_click=lambda _: set_lab_tab(0), bgcolor="#21262D", color="white", expand=True),
            ft.ElevatedButton(content=lbl_sub_assemble, on_click=lambda _: set_lab_tab(1), bgcolor="#7CB342", color="white", expand=True),
        ])
        pillar_lab = ft.Column([nav_lab, ft.Divider(height=2, color="#30363D"), lab_content], expand=True)

        # ==========================================
        # DIÁLOGO ACERCA DE Y DONACIONES
        # ==========================================
        def open_about_dialog(e):
            def close_about(e):
                dialog_about.open = False
                page.update()
                
            dialog_about = ft.AlertDialog(
                bgcolor="#161B22",
                title=ft.Row([
                    ft.Text("🌟", size=20),
                    ft.Text("Acerca de NEXUS", color="#FFAB00", weight="bold")
                ]),
                content=ft.Column([
                    ft.Text("NEXUS CAD TITAN PRO", weight="bold", size=18, color="#E6EDF3"),
                    ft.Text("Versión 1.0 (Golden Master)", size=12, color="#00E676"),
                    ft.Divider(color="#30363D"),
                    ft.Text("Desarrollado de forma independiente para la comunidad. Nexus es y será siempre libre de rastreadores y publicidad.", size=13, color="#8B949E"),
                    ft.Container(height=10),
                    ft.Text("Si Nexus te ha sido útil en tus proyectos 3D, considera apoyar su desarrollo con la voluntad. ¡Cada euro ayuda a mantener el motor encendido!", size=13, color="#E6EDF3", italic=True),
                    ft.Container(height=15),
                    ft.ElevatedButton(
                        content=ft.Row([
                            ft.Text("☕", size=18), 
                            ft.Text("Apoyar el proyecto (Ko-fi)", color="black", weight="bold")
                        ], alignment="center"),
                        bgcolor="#FFD600",
                        width=float('inf'),
                        url="https://ko-fi.com/txurtxil",
                        style=ft.ButtonStyle(padding=15)
                    )
                ], tight=True, width=320),
                actions=[
                    ft.TextButton("Cerrar", on_click=close_about, style=ft.ButtonStyle(color="#00E5FF"))
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            page.overlay.append(dialog_about)
            dialog_about.open = True
            page.update()

        # ==========================================
        # CONTENEDOR MAESTRO Y BARRAS
        # ==========================================
        main_container = ft.Container(content=pillar_studio, expand=True)

        def set_main_pillar(idx):
            main_container.content = [pillar_studio, pillar_vis, pillar_lab][idx]
            if idx == 0: page.bgcolor = "#0B0E14" 
            elif idx == 1: page.bgcolor = "#002B36" 
            elif idx == 2: page.bgcolor = "#122A16" 
            page.update()

        # BARRA DE NAVEGACIÓN SUPERIOR (LOS 3 PILARES)
        main_nav_bar = ft.Row([
            ft.ElevatedButton(content=lbl_nav_studio, on_click=lambda _: set_main_pillar(0), bgcolor="#8E24AA", color="white", expand=True, height=45),
            ft.ElevatedButton(content=lbl_nav_view, on_click=lambda _: set_main_pillar(1), bgcolor="#00E5FF", expand=True, height=45),
            ft.ElevatedButton(content=lbl_nav_lab, on_click=lambda _: set_main_pillar(2), bgcolor="#1B5E20", color="white", expand=True, height=45),
        ], spacing=5)

        # FUNCIÓN MAESTRA DE CAMBIO DE IDIOMA
        def toggle_lang(e):
            lang.switch_lang()
            page.title = lang.t("app_title")
            status.value = lang.t("app_title")
            
            lbl_nav_studio.value = lang.t("nav_studio")
            lbl_nav_view.value = lang.t("nav_view")
            lbl_nav_lab.value = lang.t("nav_lab")
            
            lbl_sub_ia.value = lang.t("btn_ia")
            lbl_sub_sliders.value = lang.t("btn_sliders")
            lbl_sub_code.value = lang.t("btn_code")
            
            lbl_sub_3d.value = lang.t("btn_3d")
            lbl_sub_pbr.value = lang.t("btn_pbr")
            
            lbl_sub_db.value = lang.t("btn_db")
            lbl_sub_assemble.value = lang.t("btn_assemble")
            
            lbl_info.value = lang.t("btn_info")
            lbl_lang.value = lang.t("btn_lang")
            
            page.update()

        # BARRA DE ESTADO INFERIOR CON EL BOTÓN "ACERCA DE" Y "CERRAR SESIÓN"
        status_bar = ft.Row([
            status,
            ft.Container(expand=True),  # Espaciador para empujar el botón a la derecha
            ft.ElevatedButton(
                content=lbl_lang, 
                bgcolor="#0D47A1",
                on_click=toggle_lang, 
                tooltip="Change Language"
            ),
            ft.ElevatedButton(  
                content=lbl_info, 
                bgcolor="#21262D",
                on_click=open_about_dialog, 
                tooltip="About / Acerca de"
            )
        ])

        # Montaje final en la página
        page.add(ft.Container(content=ft.Column([main_nav_bar, main_container, status_bar], expand=True), padding=ft.padding.only(top=45, left=5, right=5, bottom=5), expand=True))
        
        # Inicialización
        select_tool("planetario")
        refresh_explorer(current_android_dir)

    except Exception:
        page.clean(); page.add(ft.Container(ft.Text("CRASH FATAL:\n" + traceback.format_exc(), color="red"), padding=50)); page.update()

if __name__ == "__main__":
    if "TERMUX_VERSION" in os.environ: ft.app(target=main, port=0, view=ft.AppView.WEB_BROWSER)
    else: ft.app(target=main)
