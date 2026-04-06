import flet as ft
import os, base64, json, threading, http.server, socketserver, socket, time, warnings, traceback, shutil, struct
import param_generators 

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

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
# GLOBALES DE ESTADO
# =========================================================
LAN_IP = "127.0.0.1"
LOCAL_PORT = 8556
LATEST_CODE_B64 = ""
LATEST_NEEDS_STL = False
INJECTED_CODE_IA = "" 

MAX_ASSEMBLY_PARTS = 10
ASSEMBLY_PARTS_STATE = [{"active": False, "file": "", "mat": "pla", "x": 0, "y": 0, "z": 0} for _ in range(MAX_ASSEMBLY_PARTS)]
PBR_STATE = {"mode": "single", "parts": []}

def update_pbr_state():
    global PBR_STATE
    PBR_STATE["mode"] = "assembly"
    PBR_STATE["parts"] = [p for p in ASSEMBLY_PARTS_STATE if p["active"]]

def get_sys_info():
    cores = os.cpu_count() or 1
    cpu_p, ram_p = 0.0, 0.0
    if HAS_PSUTIL:
        cpu_p = psutil.cpu_percent()
        ram_p = psutil.virtual_memory().percent
    return cpu_p, ram_p, cores

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
        if parsed.path == '/api/inject_code':
            cl = int(self.headers.get('Content-Length', 0))
            if cl > 0:
                try:
                    data = json.loads(self.rfile.read(cl).decode('utf-8'))
                    global INJECTED_CODE_IA
                    INJECTED_CODE_IA = data.get('code', '')
                    self.send_response(200); self._send_cors(); self.end_headers(); self.wfile.write(b'ok')
                    return
                except: pass
            self.send_response(500); self._send_cors(); self.end_headers()
            
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
        global LATEST_CODE_B64, LATEST_NEEDS_STL, PBR_STATE
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/get_code_b64.json':
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
# APP FLET MAIN
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v20.73.6 TITAN PRO"
        page.theme_mode = "dark"
        page.bgcolor = "#0B0E14" 
        page.padding = 0 
        
        status = ft.Text("NEXUS v20.73.6 TITAN | Archivos y Renombrado", color="#00E676", weight="bold")

        def custom_icon_btn(text, action, tooltip_txt): 
            return ft.Container(content=ft.Text(text, size=16), padding=5, bgcolor="#30363D", border_radius=5, on_click=action, tooltip=tooltip_txt, ink=True)

        T_INICIAL = "function main() {\n  var pieza = CSG.cube({center:[0,0,GH/2], radius:[GW/2, GL/2, GH/2]});\n  return pieza;\n}"
        txt_code = ft.TextField(label="Código Fuente (JS-CSG)", multiline=True, expand=True, value=T_INICIAL, bgcolor="#161B22", color="#58A6FF", border_color="#30363D", text_size=12)

        ensamble_stack = []; herramienta_actual = "custom"; modo_ensamble = False

        def check_ia_injection():
            global INJECTED_CODE_IA
            while True:
                time.sleep(1)
                if INJECTED_CODE_IA:
                    txt_code.value = INJECTED_CODE_IA
                    INJECTED_CODE_IA = ""
                    txt_code.update()
                    status.value = "✓ Código de IA recibido e inyectado con éxito."
                    status.color = "#B388FF"
                    page.update()
                    
        threading.Thread(target=check_ia_injection, daemon=True).start()

        def clear_editor():
            nonlocal ensamble_stack
            ensamble_stack = []
            txt_code.value = "function main() {\n  return CSG.cube({radius:[0.01,0.01,0.01]});\n}"
            status.value = "✓ Código borrado."; status.color = "#B71C1C"
            txt_code.update(); page.update()

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
            js_payload = prepare_js_payload()
            LATEST_CODE_B64 = base64.b64encode(js_payload.encode('utf-8')).decode()
            LATEST_NEEDS_STL = ("IMPORTED_STL" in js_payload) or herramienta_actual.startswith("stl")
            set_tab(2); page.update()

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
            txt_code.value = final_code; txt_code.update(); page.update()

        panel_ensamble_ops = ft.Row([
            ft.ElevatedButton(content=ft.Text("➕ UNIR PIEZA", color="white"), on_click=lambda _: add_to_stack("union"), bgcolor="#1B5E20", expand=True),
            ft.ElevatedButton(content=ft.Text("➖ RESTAR PIEZA", color="white"), on_click=lambda _: add_to_stack("subtract"), bgcolor="#B71C1C", expand=True)
        ], visible=False)

        def toggle_ensamble(e):
            nonlocal modo_ensamble
            modo_ensamble = sw_ensamble.value
            panel_ensamble_ops.visible = modo_ensamble
            page.update()
            
        sw_ensamble.on_change = toggle_ensamble

        panel_globales = ft.Container(content=ft.Column([
            ft.Row([ft.Text("🌐 PARÁMETROS GLOBALES", color="#00E5FF", weight="bold", size=11), sw_ensamble], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
            r_g_w, r_g_l, r_g_h, r_g_t, r_g_tol, ft.Divider(color="#333333"), 
            ft.Row([ft.Text("🎨 TEXTURA / RENDER:", color="#E6EDF3", size=11, width=130), dd_mat]), ft.Divider(color="#333333"), 
            ft.Text("🎬 CINEMÁTICA INTERACTIVA", color="#B388FF", weight="bold", size=11), r_kine,
            panel_ensamble_ops
        ]), bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#333333"))

        col_custom = ft.Column([ft.Text("Modo Código Libre (Edita en la pestaña CODE)", color="#00E676")], visible=True)
        def inst(texto): return ft.Text("ℹ️ " + texto, color="#FFD54F", size=11, italic=True)

        tf_sketch_pts = ft.TextField(label="Coordenadas (X, Y) - Una por línea", value="0,0\n50,0\n50,20\n25,40\n0,20", multiline=True, height=150, bgcolor="#161B22", color="#00E5FF"); tf_sketch_pts.on_change = update_code_wrapper; sl_sketch_h, r_sketch_h = create_slider("Altura (Z)", 1, 300, 20, False); col_sketcher = ft.Column([ft.Text("Sketcher 2D / Extrusor Libre", color="#2962FF", weight="bold"), inst("Pega tabla Excel."), ft.Container(content=ft.Column([tf_sketch_pts, r_sketch_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        lbl_stl_status = ft.Text("Ningún STL cargado.", color="#8B949E", size=11)
        sl_stl_sc, r_stl_sc = create_slider("Escala (%)", 1, 500, 100, True); sl_stl_x, r_stl_x = create_slider("Mover X", -150, 150, 0, False); sl_stl_y, r_stl_y = create_slider("Mover Y", -150, 150, 0, False); sl_stl_z, r_stl_z = create_slider("Mover Z", -150, 150, 0, False)
        panel_stl_transform = ft.Container(content=ft.Column([ft.Row([ft.Text("🔄 TRANSF. BASE STL", color="#00E676", weight="bold"), lbl_stl_status]), ft.ElevatedButton(content=ft.Text("📂 IR A FILES", color="black"), on_click=lambda _: set_tab(5), bgcolor="#00E5FF", width=float('inf')), r_stl_sc, r_stl_x, r_stl_y, r_stl_z]), bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#00E676"), visible=False)

        col_stl = ft.Column([ft.Text("Visor STL Original", color="#00E676", weight="bold")], visible=False)
        sl_stlf_z, r_stlf_z = create_slider("Corte Z (mm)", 0, 50, 1, False); col_stl_flatten = ft.Column([ft.Text("Aplanar Base (Flatten)", color="#00E676", weight="bold"), r_stlf_z], visible=False)
        dd_stls_axis = ft.Dropdown(options=[ft.dropdown.Option("X"), ft.dropdown.Option("Y"), ft.dropdown.Option("Z")], value="Z", bgcolor="#1E1E1E"); dd_stls_axis.on_change = update_code_wrapper; sl_stls_pos, r_stls_pos = create_slider("Punto Corte", -150, 150, 0, False); col_stl_split = ft.Column([ft.Text("Split XYZ", color="#00E676", weight="bold"), dd_stls_axis, r_stls_pos], visible=False)
        sl_stlc_s, r_stlc_s = create_slider("Caja Tamaño", 10, 300, 50, False); col_stl_crop = ft.Column([ft.Text("Crop Box", color="#00E676", weight="bold"), r_stlc_s], visible=False)
        dd_stld_axis = ft.Dropdown(options=[ft.dropdown.Option("X"), ft.dropdown.Option("Y"), ft.dropdown.Option("Z")], value="Z", bgcolor="#1E1E1E"); dd_stld_axis.on_change = update_code_wrapper; sl_stld_r, r_stld_r = create_slider("Radio Perfo.", 0.5, 20, 1.6, False); sl_stld_px, r_stld_px = create_slider("Coord 1", -150, 150, 0, False); sl_stld_py, r_stld_py = create_slider("Coord 2", -150, 150, 0, False); col_stl_drill = ft.Column([ft.Text("Taladro 3D", color="#00E676", weight="bold"), dd_stld_axis, r_stld_r, r_stld_px, r_stld_py], visible=False)
        sl_stlm_w, r_stlm_w = create_slider("Ancho Orejeta", 10, 100, 40, False); sl_stlm_d, r_stlm_d = create_slider("Separación Ext.", 20, 200, 80, False); col_stl_mount = ft.Column([ft.Text("Orejetas", color="#00E676", weight="bold"), r_stlm_w, r_stlm_d], visible=False)
        sl_stle_r, r_stle_r = create_slider("Radio Disco", 5, 30, 15, False); sl_stle_d, r_stle_d = create_slider("Apertura XY", 10, 200, 50, False); col_stl_ears = ft.Column([ft.Text("Mouse Ears", color="#00E676", weight="bold"), r_stle_r, r_stle_d], visible=False)
        sl_stlp_sx, r_stlp_sx = create_slider("Largo Parche X", 5, 100, 20, False); sl_stlp_sy, r_stlp_sy = create_slider("Ancho Parche Y", 5, 100, 20, False); sl_stlp_sz, r_stlp_sz = create_slider("Alto Parche Z", 1, 50, 5, False); col_stl_patch = ft.Column([ft.Text("Parche Refuerzo", color="#00E676", weight="bold"), r_stlp_sx, r_stlp_sy, r_stlp_sz], visible=False)
        sl_stlh_r, r_stlh_r = create_slider("Tamaño Hex", 2, 20, 5, False); col_stl_honeycomb = ft.Column([ft.Text("Aligerado Honeycomb", color="#00E676", weight="bold"), r_stlh_r], visible=False)
        sl_stlpg_r, r_stlpg_r = create_slider("Radio Hélice", 10, 100, 40, False); sl_stlpg_t, r_stlpg_t = create_slider("Grosor Aro", 1, 10, 3, False); sl_stlpg_x, r_stlpg_x = create_slider("Centro X", -100, 100, 0, False); sl_stlpg_y, r_stlpg_y = create_slider("Centro Y", -100, 100, 0, False); col_stl_propguard = ft.Column([ft.Text("Prop-Guard", color="#00E676", weight="bold"), r_stlpg_r, r_stlpg_t, r_stlpg_x, r_stlpg_y], visible=False)

        tf_texto = ft.TextField(label="Escribe Texto", value="NEXUS", max_length=15, bgcolor="#161B22")
        dd_txt_estilo = ft.Dropdown(options=[ft.dropdown.Option("Voxel Fino"), ft.dropdown.Option("Voxel Grueso"), ft.dropdown.Option("Braille")], value="Voxel Grueso", expand=True, bgcolor="#161B22")
        dd_txt_base = ft.Dropdown(options=[ft.dropdown.Option("Solo Texto"), ft.dropdown.Option("Llavero (Anilla)"), ft.dropdown.Option("Placa Atornillable"), ft.dropdown.Option("Soporte de Mesa"), ft.dropdown.Option("Colgante Militar"), ft.dropdown.Option("Placa Ovalada")], value="Colgante Militar", expand=True, bgcolor="#161B22")
        sw_txt_grabado = ft.Switch(label="Texto Grabado", value=False, active_color="#00E5FF")
        tf_texto.on_change = update_code_wrapper; dd_txt_estilo.on_change = update_code_wrapper; dd_txt_base.on_change = update_code_wrapper; sw_txt_grabado.on_change = update_code_wrapper
        col_texto = ft.Column([ft.Text("Placas Especiales", color="#880E4F", weight="bold"), ft.Container(content=ft.Column([tf_texto, ft.Row([dd_txt_estilo, dd_txt_base]), sw_txt_grabado]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        sl_las_x, r_las_x = create_slider("Ancho Objeto", 10, 200, 50, False); sl_las_y, r_las_y = create_slider("Largo Objeto", 10, 200, 50, False); sl_las_z, r_las_z = create_slider("Altura Z Corte", 0, 100, 5, False); col_laser = ft.Column([ft.Text("Perfil Láser", color="#D50000"), ft.Container(content=ft.Column([r_las_x, r_las_y, r_las_z]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_alin_f, r_alin_f = create_slider("Filas (Y)", 1, 10, 3, True); sl_alin_c, r_alin_c = create_slider("Columnas (X)", 1, 10, 3, True); sl_alin_dx, r_alin_dx = create_slider("Distancia X", 5, 100, 20, False); sl_alin_dy, r_alin_dy = create_slider("Distancia Y", 5, 100, 20, False); sl_alin_h, r_alin_h = create_slider("Altura Base", 2, 50, 10, False); col_array_lin = ft.Column([ft.Text("Matriz Lineal Grid", color="#00B0FF"), ft.Container(content=ft.Column([r_alin_f, r_alin_c, r_alin_dx, r_alin_dy, r_alin_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_apol_n, r_apol_n = create_slider("Repeticiones", 2, 36, 8, True); sl_apol_r, r_apol_r = create_slider("Radio Corona", 10, 150, 40, False); sl_apol_rp, r_apol_rp = create_slider("Radio Pieza", 2, 20, 5, False); sl_apol_h, r_apol_h = create_slider("Grosor (Z)", 2, 50, 5, False); col_array_pol = ft.Column([ft.Text("Matriz Polar Circular", color="#00B0FF"), ft.Container(content=ft.Column([r_apol_n, r_apol_r, r_apol_rp, r_apol_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_loft_w, r_loft_w = create_slider("Ancho Base SQ", 10, 150, 60, False); sl_loft_r, r_loft_r = create_slider("Radio Top", 5, 100, 20, False); sl_loft_h, r_loft_h = create_slider("Altura Z", 10, 200, 80, False); sl_loft_g, r_loft_g = create_slider("Grosor Pared", 1, 10, 2, False); col_loft = ft.Column([ft.Text("Lofting Adaptador", color="#D50000"), ft.Container(content=ft.Column([r_loft_w, r_loft_r, r_loft_h, r_loft_g]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_pan_x, r_pan_x = create_slider("Ancho X", 20, 200, 80, False); sl_pan_y, r_pan_y = create_slider("Largo Y", 20, 200, 80, False); sl_pan_z, r_pan_z = create_slider("Alto Z", 2, 50, 10, False); sl_pan_r, r_pan_r = create_slider("Radio Hex", 2, 20, 5, False); col_panal = ft.Column([ft.Text("Panal Honeycomb", color="#FBC02D"), ft.Container(content=ft.Column([r_pan_x, r_pan_y, r_pan_z, r_pan_r]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_vor_ro, r_vor_ro = create_slider("Radio Ext", 10, 100, 40, False); sl_vor_ri, r_vor_ri = create_slider("Radio Int", 5, 95, 35, False); sl_vor_h, r_vor_h = create_slider("Altura Tubo", 20, 200, 100, False); sl_vor_d, r_vor_d = create_slider("Densidad Red", 4, 24, 12, True); col_voronoi = ft.Column([ft.Text("Carcasa Voronoi", color="#FBC02D"), ft.Container(content=ft.Column([r_vor_ro, r_vor_ri, r_vor_h, r_vor_d]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_evo_d, r_evo_d = create_slider("Nº Dientes", 8, 60, 20, True); sl_evo_m, r_evo_m = create_slider("Módulo", 1, 10, 2, False); sl_evo_h, r_evo_h = create_slider("Grosor (Z)", 2, 50, 10, False); col_evolvente = ft.Column([ft.Text("Engranaje Evolvente", color="#FFAB00"), ft.Container(content=ft.Column([r_evo_d, r_evo_m, r_evo_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_crem_d, r_crem_d = create_slider("Nº Dientes", 5, 50, 15, True); sl_crem_m, r_crem_m = create_slider("Módulo", 1, 10, 2, False); sl_crem_h, r_crem_h = create_slider("Grosor (Z)", 2, 50, 10, False); sl_crem_w, r_crem_w = create_slider("Ancho Base", 2, 50, 8, False); col_cremallera = ft.Column([ft.Text("Cremallera", color="#FFAB00"), ft.Container(content=ft.Column([r_crem_d, r_crem_m, r_crem_h, r_crem_w]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_con_d, r_con_d = create_slider("Nº Dientes", 8, 40, 16, True); sl_con_rb, r_con_rb = create_slider("Radio Base", 10, 100, 30, False); sl_con_rt, r_con_rt = create_slider("Radio Top", 5, 80, 15, False); sl_con_h, r_con_h = create_slider("Altura Cono", 5, 100, 20, False); col_conico = ft.Column([ft.Text("Engranaje Cónico", color="#FFAB00"), ft.Container(content=ft.Column([r_con_d, r_con_rb, r_con_rt, r_con_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_mc_x, r_mc_x = create_slider("Ancho X", 20, 200, 60, False); sl_mc_y, r_mc_y = create_slider("Largo Y", 20, 200, 40, False); sl_mc_z, r_mc_z = create_slider("Alto Z", 10, 100, 30, False); sl_mc_tol, r_mc_tol = create_slider("Tol. Encaje", 0.0, 2.0, 0.4, False); sl_mc_sep, r_mc_sep = create_slider("Sep. Visual", 0, 50, 15, False); col_multicaja = ft.Column([ft.Text("Caja+Tapa (Multicuerpo)", color="#7CB342"), ft.Container(content=ft.Column([r_mc_x, r_mc_y, r_mc_z, r_mc_tol, r_mc_sep]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_perf_p, r_perf_p = create_slider("Nº Puntas", 3, 20, 5, True); sl_perf_re, r_perf_re = create_slider("Radio Ext", 10, 100, 40, False); sl_perf_ri, r_perf_ri = create_slider("Radio Int", 5, 80, 15, False); sl_perf_h, r_perf_h = create_slider("Grosor (Z)", 2, 50, 10, False); col_perfil = ft.Column([ft.Text("Estrella Paramétrica 2D", color="#AB47BC"), ft.Container(content=ft.Column([r_perf_p, r_perf_re, r_perf_ri, r_perf_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_rev_h, r_rev_h = create_slider("Altura Total", 20, 200, 80, False); sl_rev_r1, r_rev_r1 = create_slider("Radio Base", 10, 100, 30, False); sl_rev_r2, r_rev_r2 = create_slider("Radio Cuello", 5, 80, 15, False); sl_rev_g, r_rev_g = create_slider("Grosor Pared", 0, 15, 2, False); col_revolucion = ft.Column([ft.Text("Sólido de Revolución", color="#AB47BC"), ft.Container(content=ft.Column([r_rev_h, r_rev_r1, r_rev_r2, r_rev_g]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_cubo, r_cubo = create_slider("Cubo Lado", 1, 200, 50, False); sl_c_grosor, r_c_g = create_slider("Vaciado Pared", 0, 20, 0, False); col_cubo = ft.Column([ft.Text("Cubo Paramétrico", color="#8B949E"), r_cubo, r_c_g], visible=False)
        sl_p_rint, r_p_rint = create_slider("Radio Hueco", 0, 95, 15, False); sl_p_lados, r_p_lados = create_slider("Caras (LowPoly)", 3, 64, 64, True); col_cilindro = ft.Column([ft.Text("Cilindro / Prisma", color="#8B949E"), r_p_rint, r_p_lados], visible=False)
        sl_l_largo, r_l_l = create_slider("Largo Brazos", 10, 100, 40, False); sl_l_ancho, r_l_a = create_slider("Ancho Perfil", 5, 50, 15, False); sl_l_grosor, r_l_g = create_slider("Grosor Chapa", 1, 20, 3, False); sl_l_hueco, r_l_h = create_slider("Agujero", 0, 10, 2, False); sl_l_chaf, r_l_chaf = create_slider("Refuerzo Int", 0, 20, 5, False); col_escuadra = ft.Column([ft.Text("Escuadra Tipo L", color="#8B949E"), ft.Container(content=ft.Column([r_l_l, r_l_a, r_l_g, r_l_h, r_l_chaf]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_e_dientes, r_e_d = create_slider("Dientes", 6, 40, 16, True); sl_e_radio, r_e_r = create_slider("Radio Base", 10, 100, 30, False); sl_e_grosor, r_e_g = create_slider("Grosor", 2, 50, 5, False); sl_e_eje, r_e_e = create_slider("Hueco Eje", 0, 30, 5, False); col_engranaje = ft.Column([ft.Text("Piñón Cuadrado Básico", color="#8B949E"), ft.Container(content=ft.Column([r_e_d, r_e_r, r_e_g, r_e_e]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_pcb_x, r_pcb_x = create_slider("Largo PCB", 20, 200, 70, False); sl_pcb_y, r_pcb_y = create_slider("Ancho PCB", 20, 200, 50, False); sl_pcb_h, r_pcb_h = create_slider("Altura Caja", 10, 100, 20, False); sl_pcb_t, r_pcb_t = create_slider("Grosor Pared", 1, 10, 2, False); col_pcb = ft.Column([ft.Text("Caja para Electrónica", color="#8B949E"), ft.Container(content=ft.Column([r_pcb_x, r_pcb_y, r_pcb_h, r_pcb_t]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_v_l, r_v_l = create_slider("Longitud", 10, 300, 50, False); col_vslot = ft.Column([ft.Text("Perfil V-Slot 2020", color="#8B949E"), ft.Container(content=ft.Column([r_v_l]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_bi_l, r_bi_l = create_slider("Largo Total", 10, 100, 30, False); sl_bi_d, r_bi_d = create_slider("Diámetro Eje", 5, 30, 10, False); col_bisagra = ft.Column([ft.Text("Bisagra Print-in-Place", color="#8B949E"), ft.Container(content=ft.Column([r_bi_l, r_bi_d]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_clamp_d, r_clamp_d = create_slider("Ø Tubo", 10, 100, 25, False); sl_clamp_g, r_clamp_g = create_slider("Grosor Arco", 2, 15, 5, False); sl_clamp_w, r_clamp_w = create_slider("Ancho Pieza", 5, 50, 15, False); col_abrazadera = ft.Column([ft.Text("Abrazadera de Tubo", color="#8B949E"), ft.Container(content=ft.Column([r_clamp_d, r_clamp_g, r_clamp_w]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_fij_m, r_fij_m = create_slider("Métrica (M)", 3, 20, 8, True); sl_fij_l, r_fij_l = create_slider("Largo Tornillo", 0, 100, 30, False); col_fijacion = ft.Column([ft.Text("Tuerca / Tornillo Hex", color="#FFAB00"), ft.Container(content=ft.Column([r_fij_m, r_fij_l]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_rod_dint, r_rod_dint = create_slider("Ø Eje Interno", 3, 50, 8, False); sl_rod_dext, r_rod_dext = create_slider("Ø Externo", 10, 100, 22, False); sl_rod_h, r_rod_h = create_slider("Altura", 3, 30, 7, False); col_rodamiento = ft.Column([ft.Text("Rodamiento de Bolas", color="#FFAB00"), ft.Container(content=ft.Column([r_rod_dint, r_rod_dext, r_rod_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_plan_rs, r_plan_rs = create_slider("Radio Sol", 5, 40, 10, False); sl_plan_rp, r_plan_rp = create_slider("Radio Planetas", 4, 30, 8, False); sl_plan_h, r_plan_h = create_slider("Grosor Total", 3, 30, 6, False); col_planetario = ft.Column([ft.Text("Mecanismo Planetario (Soporta Cinemática)", color="#FFAB00"), ft.Container(content=ft.Column([r_plan_rs, r_plan_rp, r_plan_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_pol_t, r_pol_t = create_slider("Nº Dientes", 10, 60, 20, True); sl_pol_w, r_pol_w = create_slider("Ancho Correa", 4, 20, 6, False); sl_pol_d, r_pol_d = create_slider("Ø Eje Motor", 2, 12, 5, False); col_polea = ft.Column([ft.Text("Polea Dentada GT2", color="#00E5FF"), ft.Container(content=ft.Column([r_pol_t, r_pol_w, r_pol_d]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_hel_r, r_hel_r = create_slider("Radio Total", 20, 150, 50, False); sl_hel_n, r_hel_n = create_slider("Nº Aspas", 2, 12, 4, True); sl_hel_p, r_hel_p = create_slider("Torsión", 10, 80, 45, False); col_helice = ft.Column([ft.Text("Hélice Paramétrica", color="#00E5FF"), ft.Container(content=ft.Column([r_hel_r, r_hel_n, r_hel_p]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_rot_r, r_rot_r = create_slider("Radio Bola", 5, 30, 10, False); col_rotula = ft.Column([ft.Text("Rótula Articulada", color="#00E5FF"), ft.Container(content=ft.Column([r_rot_r]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_car_x, r_car_x = create_slider("Ancho (X)", 20, 200, 80, False); sl_car_y, r_car_y = create_slider("Largo (Y)", 20, 200, 120, False); sl_car_z, r_car_z = create_slider("Alto (Z)", 10, 100, 30, False); sl_car_t, r_car_t = create_slider("Grosor Pared", 1, 5, 2, False); col_carcasa = ft.Column([ft.Text("Carcasa Smart con Ventilación", color="#00E5FF"), ft.Container(content=ft.Column([r_car_x, r_car_y, r_car_z, r_car_t]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_mue_r, r_mue_r = create_slider("Radio Resorte", 5, 50, 15, False); sl_mue_h, r_mue_h = create_slider("Radio Hilo", 1, 10, 2, False); sl_mue_v, r_mue_v = create_slider("Nº Vueltas", 2, 20, 5, False); sl_mue_alt, r_mue_alt = create_slider("Altura Total", 10, 200, 40, False); col_muelle = ft.Column([ft.Text("Muelle Helicoidal", color="#FFAB00"), ft.Container(content=ft.Column([r_mue_r, r_mue_h, r_mue_v, r_mue_alt]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_acme_d, r_acme_d = create_slider("Diámetro Eje", 4, 30, 8, False); sl_acme_p, r_acme_p = create_slider("Paso (Pitch)", 1, 10, 2, False); sl_acme_l, r_acme_l = create_slider("Longitud", 10, 200, 50, False); col_acme = ft.Column([ft.Text("Eje Roscado (ACME)", color="#FFAB00"), ft.Container(content=ft.Column([r_acme_d, r_acme_p, r_acme_l]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_codo_r, r_codo_r = create_slider("Radio Tubo", 2, 50, 10, False); sl_codo_c, r_codo_c = create_slider("Radio Curva", 10, 150, 30, False); sl_codo_a, r_codo_a = create_slider("Ángulo Giroº", 10, 180, 90, False); sl_codo_g, r_codo_g = create_slider("Grosor Hueco", 0, 10, 2, False); col_codo = ft.Column([ft.Text("Tubería y Codos", color="#00E5FF"), ft.Container(content=ft.Column([r_codo_r, r_codo_c, r_codo_a, r_codo_g]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_naca_c, r_naca_c = create_slider("Cuerda", 20, 200, 80, False); sl_naca_g, r_naca_g = create_slider("Grosor Max %", 5, 30, 15, False); sl_naca_e, r_naca_e = create_slider("Envergadura Z", 10, 300, 100, False); col_naca = ft.Column([ft.Text("Perfil Alar NACA", color="#00E5FF"), ft.Container(content=ft.Column([r_naca_c, r_naca_g, r_naca_e]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_st_ang, r_st_ang = create_slider("Inclinación º", 5, 45, 15, False); sl_st_w, r_st_w = create_slider("Ancho Base", 40, 120, 70, False); sl_st_t, r_st_t = create_slider("Grosor Dispo.", 6, 20, 12, False); col_stand_movil = ft.Column([ft.Text("Soporte para Móvil/Tablet", color="#00E676"), ft.Container(content=ft.Column([r_st_ang, r_st_w, r_st_t]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_clip_d, r_clip_d = create_slider("Ø Cable", 3, 15, 6, False); sl_clip_w, r_clip_w = create_slider("Ancho Adhesivo", 10, 40, 20, False); col_clip_cable = ft.Column([ft.Text("Clip de Cables (Desk)", color="#00E676"), ft.Container(content=ft.Column([r_clip_d, r_clip_w]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)
        sl_vr_s, r_vr_s = create_slider("Tamaño Base", 50, 500, 200, False); col_vr_pedestal = ft.Column([ft.Text("Pedestal de Exhibición (Modo VR)", color="#B388FF"), ft.Container(content=ft.Column([r_vr_s]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        def generate_param_code():
            h = herramienta_actual
            if h == "custom": return
            
            p_dict = {
                "sc": sl_stl_sc.value, "tx": sl_stl_x.value, "ty": sl_stl_y.value, "tz": sl_stl_z.value, "stlf_z": sl_stlf_z.value, "stls_axis": dd_stls_axis.value, "stls_pos": sl_stls_pos.value, "stlc_s": sl_stlc_s.value, "stld_axis": dd_stld_axis.value, "stld_r": sl_stld_r.value, "stld_px": sl_stld_px.value, "stld_py": sl_stld_py.value, "stlm_w": sl_stlm_w.value, "stlm_d": sl_stlm_d.value, "stle_r": sl_stle_r.value, "stle_d": sl_stle_d.value, "stlp_sx": sl_stlp_sx.value, "stlp_sy": sl_stlp_sy.value, "stlp_sz": sl_stlp_sz.value, "stlh_r": sl_stlh_r.value, "stlpg_r": sl_stlpg_r.value, "stlpg_t": sl_stlpg_t.value, "stlpg_x": sl_stlpg_x.value, "stlpg_y": sl_stlpg_y.value,
                "sketch_h": sl_sketch_h.value, "sketch_pts": tf_sketch_pts.value, "txt_input": tf_texto.value, "txt_estilo": dd_txt_estilo.value, "txt_base": dd_txt_base.value, "txt_grabado": sw_txt_grabado.value,
                "las_x": sl_las_x.value, "las_y": sl_las_y.value, "las_z": sl_las_z.value, "alin_f": sl_alin_f.value, "alin_c": sl_alin_c.value, "alin_dx": sl_alin_dx.value, "alin_dy": sl_alin_dy.value, "alin_h": sl_alin_h.value, "apol_n": sl_apol_n.value, "apol_r": sl_apol_r.value, "apol_rp": sl_apol_rp.value, "apol_h": sl_apol_h.value, "loft_w": sl_loft_w.value, "loft_r": sl_loft_r.value, "loft_h": sl_loft_h.value, "loft_g": sl_loft_g.value, "pan_x": sl_pan_x.value, "pan_y": sl_pan_y.value, "pan_z": sl_pan_z.value, "pan_r": sl_pan_r.value, "vor_ro": sl_vor_ro.value, "vor_ri": sl_vor_ri.value, "vor_h": sl_vor_h.value, "vor_d": sl_vor_d.value, "evo_d": sl_evo_d.value, "evo_m": sl_evo_m.value, "evo_h": sl_evo_h.value, "crem_d": sl_crem_d.value, "crem_m": sl_crem_m.value, "crem_h": sl_crem_h.value, "crem_w": sl_crem_w.value, "con_d": sl_con_d.value, "con_rb": sl_con_rb.value, "con_rt": sl_con_rt.value, "con_h": sl_con_h.value, "mc_x": sl_mc_x.value, "mc_y": sl_mc_y.value, "mc_z": sl_mc_z.value, "mc_tol": sl_mc_tol.value, "mc_sep": sl_mc_sep.value, "perf_p": sl_perf_p.value, "perf_re": sl_perf_re.value, "perf_ri": sl_perf_ri.value, "perf_h": sl_perf_h.value, "rev_h": sl_rev_h.value, "rev_r1": sl_rev_r1.value, "rev_r2": sl_rev_r2.value, "rev_g": sl_rev_g.value, "cubo": sl_cubo.value, "c_grosor": sl_c_grosor.value, "p_rint": sl_p_rint.value, "p_lados": sl_p_lados.value, "l_largo": sl_l_largo.value, "l_ancho": sl_l_ancho.value, "l_grosor": sl_l_grosor.value, "l_hueco": sl_l_hueco.value, "l_chaf": sl_l_chaf.value, "e_dientes": sl_e_dientes.value, "e_radio": sl_e_radio.value, "e_grosor": sl_e_grosor.value, "e_eje": sl_e_eje.value, "pcb_x": sl_pcb_x.value, "pcb_y": sl_pcb_y.value, "pcb_h": sl_pcb_h.value, "pcb_t": sl_pcb_t.value, "v_l": sl_v_l.value, "bi_l": sl_bi_l.value, "bi_d": sl_bi_d.value, "clamp_d": sl_clamp_d.value, "clamp_g": sl_clamp_g.value, "clamp_w": sl_clamp_w.value, "fij_m": sl_fij_m.value, "fij_l": sl_fij_l.value, "rod_dint": sl_rod_dint.value, "rod_dext": sl_rod_dext.value, "rod_h": sl_rod_h.value, "plan_rs": sl_plan_rs.value, "plan_rp": sl_plan_rp.value, "plan_h": sl_plan_h.value, "pol_t": sl_pol_t.value, "pol_w": sl_pol_w.value, "pol_d": sl_pol_d.value, "hel_r": sl_hel_r.value, "hel_n": sl_hel_n.value, "hel_p": sl_hel_p.value, "rot_r": sl_rot_r.value, "car_x": sl_car_x.value, "car_y": sl_car_y.value, "car_z": sl_car_z.value, "car_t": sl_car_t.value, "mue_r": sl_mue_r.value, "mue_h": sl_mue_h.value, "mue_v": sl_mue_v.value, "mue_alt": sl_mue_alt.value, "acme_d": sl_acme_d.value, "acme_p": sl_acme_p.value, "acme_l": sl_acme_l.value, "codo_r": sl_codo_r.value, "codo_c": sl_codo_c.value, "codo_a": sl_codo_a.value, "codo_g": sl_codo_g.value, "naca_c": sl_naca_c.value, "naca_g": sl_naca_g.value, "naca_e": sl_naca_e.value, "st_ang": sl_st_ang.value, "st_w": sl_st_w.value, "st_t": sl_st_t.value, "clip_d": sl_clip_d.value, "clip_w": sl_clip_w.value, "vr_s": sl_vr_s.value
            }
            txt_code.value = param_generators.get_code(h, p_dict)
            txt_code.update()

        def select_tool(nombre_herramienta):
            nonlocal herramienta_actual
            herramienta_actual = nombre_herramienta
            tool_panels = {"custom": col_custom, "sketcher": col_sketcher, "stl": col_stl, "stl_flatten": col_stl_flatten, "stl_split": col_stl_split, "stl_crop": col_stl_crop, "stl_drill": col_stl_drill, "stl_mount": col_stl_mount, "stl_ears": col_stl_ears, "stl_patch": col_stl_patch, "stl_honeycomb": col_stl_honeycomb, "stl_propguard": col_stl_propguard, "texto": col_texto, "cubo": col_cubo, "cilindro": col_cilindro, "laser": col_laser, "array_lin": col_array_lin, "array_pol": col_array_pol, "loft": col_loft, "panal": col_panal, "voronoi": col_voronoi, "evolvente": col_evolvente, "cremallera": col_cremallera, "conico": col_conico, "multicaja": col_multicaja, "perfil": col_perfil, "revolucion": col_revolucion, "escuadra": col_escuadra, "engranaje": col_engranaje, "pcb": col_pcb, "vslot": col_vslot, "bisagra": col_bisagra, "abrazadera": col_abrazadera, "fijacion": col_fijacion, "rodamiento": col_rodamiento, "planetario": col_planetario, "polea": col_polea, "helice": col_helice, "rotula": col_rotula, "carcasa": col_carcasa, "muelle": col_muelle, "acme": col_acme, "codo": col_codo, "naca": col_naca, "stand_movil": col_stand_movil, "clip_cable": col_clip_cable, "vr_pedestal": col_vr_pedestal}
            for k, p in tool_panels.items(): p.visible = (k == nombre_herramienta)
            panel_stl_transform.visible = nombre_herramienta.startswith("stl")
            generate_param_code(); page.update()

        def thumbnail(icon, title, tool_id, color): return ft.Container(content=ft.Column([ft.Text(icon, size=24), ft.Text(title, size=10, color="white", weight="bold")], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), width=75, height=70, bgcolor=color, border_radius=8, on_click=lambda _: select_tool(tool_id), ink=True, border=ft.border.all(1, "#30363D"))

        cat_especial = ft.Row([thumbnail("🧠", "Código Libre", "custom", "#000000"), thumbnail("🔠", "Placas Texto", "texto", "#880E4F"), thumbnail("🥽", "Pedestal VR", "vr_pedestal", "#B388FF")], scroll="auto")
        cat_bocetos = ft.Row([thumbnail("✍️", "Sketch 2D", "sketcher", "#2962FF")], scroll="auto")
        cat_stl_forge = ft.Row([thumbnail("🧊", "Híbrido Base", "stl", "#00C853"), thumbnail("📏", "Flatten", "stl_flatten", "#00C853"), thumbnail("✂️", "Split XYZ", "stl_split", "#00C853"), thumbnail("📦", "Crop Box", "stl_crop", "#00C853"), thumbnail("🕳️", "Taladro 3D", "stl_drill", "#00C853"), thumbnail("🔩", "Orejetas", "stl_mount", "#00C853"), thumbnail("🖱️", "Mouse Ears", "stl_ears", "#00C853"), thumbnail("🧱", "Bloque Ref", "stl_patch", "#00C853"), thumbnail("🐝", "Honeycomb", "stl_honeycomb", "#00C853"), thumbnail("🛡️", "Prop Guard", "stl_propguard", "#00C853")], scroll="auto")
        cat_accesorios = ft.Row([thumbnail("📱", "Stand Móvil", "stand_movil", "#00C853"), thumbnail("🔌", "Clip Cables", "clip_cable", "#00C853")], scroll="auto")
        cat_produccion = ft.Row([thumbnail("🔪", "Perfil Láser", "laser", "#D50000"), thumbnail("🔲", "Matriz Grid", "array_lin", "#0091EA"), thumbnail("🎡", "Matriz Polar", "array_pol", "#00B0FF")], scroll="auto")
        cat_lofting = ft.Row([thumbnail("🌪️", "Adap. Loft", "loft", "#D50000")], scroll="auto")
        cat_topologia = ft.Row([thumbnail("🐝", "Panal Hex", "panal", "#F57F17"), thumbnail("🕸️", "Voronoi", "voronoi", "#6A1B9A")], scroll="auto")
        cat_engranajes = ft.Row([thumbnail("⚙️", "Evolvente", "evolvente", "#E65100"), thumbnail("🛤️", "Cremallera", "cremallera", "#5D4037"), thumbnail("🍦", "Cónico", "conico", "#D84315")], scroll="auto")
        cat_multicuerpo = ft.Row([thumbnail("📦", "Caja+Tapa", "multicaja", "#33691E")], scroll="auto")
        cat_perfiles = ft.Row([thumbnail("⭐", "Estrella 2D", "perfil", "#F57F17"), thumbnail("🏺", "Revolución", "revolucion", "#6A1B9A")], scroll="auto")
        cat_aero = ft.Row([thumbnail("✈️", "Perfil NACA", "naca", "#01579B"), thumbnail("🚁", "Hélice", "helice", "#006064"), thumbnail("🚰", "Tubo Curvo", "codo", "#004D40")], scroll="auto")
        cat_mecanismos = ft.Row([thumbnail("🌀", "Muelle", "muelle", "#3E2723"), thumbnail("🦾", "Rótula", "rotula", "#BF360C"), thumbnail("⚙️", "Planetario", "planetario", "#E65100"), thumbnail("🛼", "Polea", "polea", "#0277BD"), thumbnail("🛞", "Rodamiento", "rodamiento", "#4E342E")], scroll="auto")
        cat_ingenieria = ft.Row([thumbnail("🚧", "Eje ACME", "acme", "#212121"), thumbnail("🗃️", "Carcasa", "carcasa", "#1B5E20"), thumbnail("🔩", "Tornillos", "fijacion", "#B71C1C"), thumbnail("🗜️", "Abrazadera", "abrazadera", "#0D47A1"), thumbnail("🔌", "Caja PCB", "pcb", "#004D40"), thumbnail("🚪", "Bisagra", "bisagra", "#311B92"), thumbnail("🏗️", "V-Slot", "vslot", "#1A237E")], scroll="auto")
        cat_basico = ft.Row([thumbnail("📦", "Cubo G", "cubo", "#263238"), thumbnail("🛢️", "Cilindro G", "cilindro", "#263238"), thumbnail("📐", "Escuadra", "escuadra", "#D84315"), thumbnail("⚙️", "Piñón SQ", "engranaje", "#FF6F00")], scroll="auto")

        view_constructor = ft.Column([
            panel_globales, 
            ft.Text("💡 Opciones Especiales:", size=12, color="#8B949E"), cat_especial,
            ft.Text("📐 Bocetos y Perfiles 2D:", size=12, color="#2962FF", weight="bold"), cat_bocetos,
            ft.Text("⚔️ ULTIMATE STL FORGE:", size=12, color="#00E676", weight="bold"), cat_stl_forge,
            ft.Text("🔋 Accesorios Prácticos:", size=12, color="#00E676"), cat_accesorios,
            ft.Text("🏭 Producción y Láser:", size=12, color="#00B0FF"), cat_produccion,
            ft.Text("🌪️ Transición de Formas:", size=12, color="#D50000"), cat_lofting,
            ft.Text("🧬 Topología y Voronoi:", size=12, color="#FBC02D"), cat_topologia,
            ft.Text("⚙️ Engranajes Avanzados:", size=12, color="#FF9100"), cat_engranajes,
            ft.Text("🧱 Ensamblajes Multi-Cuerpo:", size=12, color="#7CB342"), cat_multicuerpo,
            ft.Text("📐 Perfiles y Revolución 2D->3D:", size=12, color="#AB47BC"), cat_perfiles,
            ft.Text("🛸 Aero y Orgánico:", size=12, color="#00E5FF"), cat_aero,
            ft.Text("⚙️ Cinemática y Mecanismos:", size=12, color="#FFAB00"), cat_mecanismos,
            ft.Text("🛠️ Ingeniería:", size=12, color="#FF9100"), cat_ingenieria,
            ft.Text("📦 Geometría Básica:", size=12, color="#8B949E"), cat_basico,
            ft.Divider(color="#30363D"), panel_stl_transform,
            col_custom, col_sketcher, col_stl, col_stl_flatten, col_stl_split, col_stl_crop, col_stl_drill, col_stl_mount, col_stl_ears, col_stl_patch, col_stl_honeycomb, col_stl_propguard,
            col_texto, col_cubo, col_cilindro, col_laser, col_array_lin, col_array_pol, col_loft, col_panal, col_voronoi, col_evolvente, col_cremallera, col_conico, col_multicaja, col_perfil, col_revolucion, col_escuadra, col_engranaje, col_pcb, col_vslot, col_bisagra, col_abrazadera, col_fijacion, col_rodamiento, col_planetario, col_polea, col_helice, col_rotula, col_carcasa, col_muelle, col_acme, col_codo, col_naca, col_stand_movil, col_clip_cable, col_vr_pedestal,
            ft.ElevatedButton("▶ ENVIAR AL WORKER (RENDER 3D)", on_click=lambda _: run_render(), bgcolor="#00E676", color="black", height=60, width=float('inf'))
        ], expand=True, scroll="auto")

        view_editor = ft.Column([
            ft.Row([ft.ElevatedButton("💾 GUARDAR LOCAL", on_click=lambda _: save_project_to_nexus(), bgcolor="#0D47A1", color="white"), ft.ElevatedButton("🗑️ RESET", on_click=lambda _: clear_editor(), bgcolor="#B71C1C", color="white")], scroll="auto"),
            txt_code
        ], expand=True)

        pb_cpu = ft.ProgressBar(width=100, color="#FFAB00", bgcolor="#30363D", value=0, expand=True)
        txt_cpu_val = ft.Text("0.0%", size=11, color="#FFAB00", width=40, text_align="right")
        pb_ram = ft.ProgressBar(width=100, color="#00E5FF", bgcolor="#30363D", value=0, expand=True)
        txt_ram_val = ft.Text("0.0%", size=11, color="#00E5FF", width=40, text_align="right")
        txt_cores = ft.Text("CORES: ?", size=11, color="#8B949E", weight="bold")

        hw_panel = ft.Container(content=ft.Column([ft.Row([ft.Text("📊 TELEMETRÍA HARDWARE", size=11, color="#E6EDF3", weight="bold"), txt_cores], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Row([ft.Text("CPU", size=11, color="#FFAB00", weight="bold", width=30), pb_cpu, txt_cpu_val]), ft.Row([ft.Text("RAM", size=11, color="#00E5FF", weight="bold", width=30), pb_ram, txt_ram_val])], spacing=5), bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#333333"))

        def hw_monitor_loop():
            while True:
                time.sleep(1.5)
                try:
                    if main_container.content == view_visor:
                        cpu, ram, cores = get_sys_info()
                        pb_cpu.value = cpu / 100.0; txt_cpu_val.value = f"{cpu:.1f}%"
                        pb_ram.value = ram / 100.0; txt_ram_val.value = f"{ram:.1f}%"
                        txt_cores.value = f"CORES: {cores}"; hw_panel.update()
                except: pass

        threading.Thread(target=hw_monitor_loop, daemon=True).start()

        view_visor = ft.Column([
            ft.Container(height=5), hw_panel, ft.Container(height=5),
            ft.Container(content=ft.Column([ft.Text("🥽 MODO GAFAS VR O PC EXTERNO", color="#B388FF", weight="bold", size=11), ft.TextField(value=f"http://{LAN_IP}:{LOCAL_PORT}/openscad_engine.html", read_only=True, text_size=16, text_align="center", bgcolor="#161B22", color="#00E676")]), bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#B388FF")),
            ft.Container(height=5),
            ft.Text("Motor Web Worker (Exportación 100% Nativa TITAN)", text_align="center", color="#00E5FF", weight="bold"),
            ft.ElevatedButton("🔄 ABRIR VISOR 3D (ESTÁNDAR)", url=f"http://{LAN_IP}:{LOCAL_PORT}/openscad_engine.html", bgcolor="#00E676", color="black", height=60, width=float('inf')),
        ], expand=True, scroll="auto")
        
        def build_static_assembly_cards():
            cards = []
            for i in range(MAX_ASSEMBLY_PARTS):
                df = ft.Dropdown(options=[], width=160, text_size=12, bgcolor="#0B0E14", color="#00E5FF")
                dm = ft.Dropdown(options=[ft.dropdown.Option("pla"), ft.dropdown.Option("petg"), ft.dropdown.Option("carbon"), ft.dropdown.Option("aluminum"), ft.dropdown.Option("wood"), ft.dropdown.Option("gold")], value="pla", width=100, text_size=12, bgcolor="#0B0E14")
                sl_x = ft.Slider(min=-200, max=200, value=0, expand=True); sl_y = ft.Slider(min=-200, max=200, value=0, expand=True); sl_z = ft.Slider(min=-200, max=200, value=0, expand=True)
                card = ft.Container(bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#C51162"), visible=False)
                
                def make_change_handler(idx, d_f, d_m, s_x, s_y, s_z):
                    def handler(e):
                        if not ASSEMBLY_PARTS_STATE[idx]["active"]: return
                        ASSEMBLY_PARTS_STATE[idx]["file"] = d_f.value; ASSEMBLY_PARTS_STATE[idx]["mat"] = d_m.value
                        ASSEMBLY_PARTS_STATE[idx]["x"] = s_x.value; ASSEMBLY_PARTS_STATE[idx]["y"] = s_y.value; ASSEMBLY_PARTS_STATE[idx]["z"] = s_z.value
                        update_pbr_state()
                    return handler
                    
                change_handler = make_change_handler(i, df, dm, sl_x, sl_y, sl_z)
                df.on_change = change_handler; dm.on_change = change_handler; sl_x.on_change = change_handler; sl_y.on_change = change_handler; sl_z.on_change = change_handler
                
                def make_delete_handler(idx, c):
                    def handler(e):
                        ASSEMBLY_PARTS_STATE[idx]["active"] = False; c.visible = False; update_pbr_state(); check_empty_assembly(); page.update()
                    return handler
                    
                btn_del = ft.Container(content=ft.Text("🗑️", size=16), padding=5, bgcolor="#30363D", border_radius=5, on_click=make_delete_handler(i, card), ink=True)
                card.content = ft.Column([ft.Row([df, dm, btn_del], alignment="spaceBetween"), ft.Row([ft.Text("X", size=10, color="#8B949E", width=15), sl_x]), ft.Row([ft.Text("Y", size=10, color="#8B949E", width=15), sl_y]), ft.Row([ft.Text("Z", size=10, color="#8B949E", width=15), sl_z])])
                
                def refresh_opts(d=df, idx=i):
                    files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
                    d.options = [ft.dropdown.Option(f) for f in files]
                    if not d.value and files: d.value = files[0]
                    elif d.value not in files and files: d.value = files[0]
                    if files: ASSEMBLY_PARTS_STATE[idx]["file"] = d.value
                    
                card.data = {"refresh": refresh_opts, "df": df, "dm": dm, "sx": sl_x, "sy": sl_y, "sz": sl_z}
                cards.append(card)
            return cards

        col_assembly_cards = build_static_assembly_cards()
        lbl_ensamble_warn = ft.Text("⚠️ DB de STLs vacía.\nVe a la pestaña FILES y sube o guarda STLs primero.", color="#FFAB00", weight="bold", visible=False)
        col_assembly = ft.Column([lbl_ensamble_warn] + col_assembly_cards, scroll="auto", expand=True)

        def check_empty_assembly():
            has_active = any(p["active"] for p in ASSEMBLY_PARTS_STATE)
            files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
            lbl_ensamble_warn.visible = not has_active and not files

        def add_assembly_part(e):
            files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
            if not files:
                status.value = "❌ No hay STLs para añadir. Sube archivos en la pestaña FILES."; status.color = "#FF5252"; page.update(); return
            for i in range(MAX_ASSEMBLY_PARTS):
                if not ASSEMBLY_PARTS_STATE[i]["active"]:
                    ASSEMBLY_PARTS_STATE[i]["active"] = True; card = col_assembly_cards[i]; card.data["refresh"]()
                    card.data["sx"].value = 0; card.data["sy"].value = 0; card.data["sz"].value = 0
                    ASSEMBLY_PARTS_STATE[i]["x"] = 0; ASSEMBLY_PARTS_STATE[i]["y"] = 0; ASSEMBLY_PARTS_STATE[i]["z"] = 0; ASSEMBLY_PARTS_STATE[i]["mat"] = card.data["dm"].value
                    card.visible = True; update_pbr_state(); check_empty_assembly(); page.update()
                    return
            status.value = "❌ Límite máximo de piezas (10) alcanzado."; status.color = "#FFAB00"; page.update()

        def render_assembly_ui():
            files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
            if not files:
                lbl_ensamble_warn.visible = True
                for i in range(MAX_ASSEMBLY_PARTS): col_assembly_cards[i].visible = False; ASSEMBLY_PARTS_STATE[i]["active"] = False
            else:
                lbl_ensamble_warn.visible = not any(p["active"] for p in ASSEMBLY_PARTS_STATE)
                for i, card in enumerate(col_assembly_cards):
                    if ASSEMBLY_PARTS_STATE[i]["active"]: card.data["refresh"]()

        view_ensamble = ft.Column([
            ft.Text("🧩 MESA DE ENSAMBLAJE", size=20, color="#FFAB00", weight="bold"),
            ft.Text("Une hasta 10 STLs. Se reflejará instantáneamente en PBR.", color="#8B949E", size=11),
            ft.Row([ft.ElevatedButton("➕ AÑADIR PIEZA", on_click=add_assembly_part, bgcolor="#1B5E20", color="white"), ft.ElevatedButton("👁️ ABRIR PBR", on_click=lambda _: set_tab(4), bgcolor="#C51162", color="white")]),
            ft.Divider(), col_assembly
        ], expand=True)

        view_pbr = ft.Column([
            ft.Container(height=20),
            ft.Text("🎨 PBR STUDIO PRO", size=24, color="#FF007F", weight="bold", text_align="center"),
            ft.Text("Renderizado Físico Realista con Shaders Procedurales.", color="#E6EDF3", text_align="center"),
            ft.Container(height=20),
            ft.Container(content=ft.Column([ft.Text("Soporta la Pieza Única (PARAM) o Ensamble (MESA).", color="#00E676"), ft.Text("El botón 'Tomar Foto' guarda el render en NEXUS DB.", color="#00E676", weight="bold")]), bgcolor="#161B22", padding=15, border_radius=8, border=ft.border.all(1, "#C51162")),
            ft.Container(height=20),
            ft.ElevatedButton("🚀 ABRIR PBR STUDIO", url=f"http://{LAN_IP}:{LOCAL_PORT}/pbr_studio.html", bgcolor="#C51162", color="white", height=80, width=float('inf'))
        ], expand=True, horizontal_alignment="center")

        txt_dim_x = ft.Text("0.0 mm", color="#00E5FF", weight="bold"); txt_dim_y = ft.Text("0.0 mm", color="#00E5FF", weight="bold"); txt_dim_z = ft.Text("0.0 mm", color="#00E5FF", weight="bold")
        txt_vol = ft.Text("0.0 cm³", color="#FFAB00", weight="bold"); txt_peso = ft.Text("0.0 g", color="#00E676", weight="bold")
        panel_calibre = ft.Container(content=ft.Column([ft.Text("📐 CALIBRE 3D Y PRESUPUESTO (STL ACTUAL)", color="#E6EDF3", weight="bold"), ft.Row([ft.Text("Ancho (X):", color="#8B949E", width=80), txt_dim_x]), ft.Row([ft.Text("Largo (Y):", color="#8B949E", width=80), txt_dim_y]), ft.Row([ft.Text("Alto (Z):", color="#8B949E", width=80), txt_dim_z]), ft.Divider(color="#30363D"), ft.Row([ft.Text("Volumen:", color="#8B949E", width=80), txt_vol]), ft.Row([ft.Text("Peso PLA:", color="#8B949E", width=80), txt_peso])]), bgcolor="#161B22", padding=15, border_radius=8, border=ft.border.all(1, "#2962FF"))

        # POPUP PARA RENOMBRAR (Se mantiene)
        rename_target = ""
        tf_rename = ft.TextField(label="Nuevo nombre.stl/.jscad", bgcolor="#161B22", color="#00E5FF")
        
        def open_rename_dialog(filename):
            global rename_target
            rename_target = filename
            tf_rename.value = filename
            dialog_rename.open = True
            page.update()

        def confirm_rename(e):
            global rename_target
            new_name = tf_rename.value.strip()
            if new_name and new_name != rename_target:
                if rename_target.lower().endswith(".stl") and not new_name.lower().endswith(".stl"): new_name += ".stl"
                if rename_target.lower().endswith(".jscad") and not new_name.lower().endswith(".jscad"): new_name += ".jscad"
                try:
                    os.rename(os.path.join(EXPORT_DIR, rename_target), os.path.join(EXPORT_DIR, new_name))
                    status.value = f"✓ Renombrado a {new_name}"; status.color = "#00E676"
                except Exception as ex:
                    status.value = f"❌ Error: {ex}"; status.color = "red"
            dialog_rename.open = False
            refresh_nexus_db()
            page.update()

        dialog_rename = ft.AlertDialog(
            title=ft.Text("Renombrar Archivo", color="#00E5FF"),
            content=tf_rename,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: [setattr(dialog_rename, 'open', False), page.update()]),
                ft.ElevatedButton("Guardar", on_click=confirm_rename, bgcolor="#00E676", color="black")
            ]
        )
        page.overlay.append(dialog_rename)

        list_nexus_db = ft.ListView(height=250, spacing=5)

        def direct_download_file(e, filename):
            try:
                os.makedirs(DOWNLOAD_DIR, exist_ok=True); shutil.copy(os.path.join(EXPORT_DIR, filename), os.path.join(DOWNLOAD_DIR, filename))
                status.value = f"✓ {filename} guardado en Descargas."; status.color = "#00E676"
            except Exception as ex: status.value = f"❌ Error guardando: {ex}"; status.color = "#FF5252"
            page.update()
            
        def export_obj_file(e, filename):
            os.makedirs(DOWNLOAD_DIR, exist_ok=True); success, msg = convert_stl_to_obj(os.path.join(EXPORT_DIR, filename), os.path.join(DOWNLOAD_DIR, filename.replace('.stl', '.obj')))
            status.value = f"✓ OBJ en Descargas." if success else f"❌ Error OBJ: {msg}"; status.color = "#00E5FF" if success else "#FF5252"; page.update()

        def refresh_nexus_db():
            list_nexus_db.controls.clear()
            try:
                files = [f for f in os.listdir(EXPORT_DIR) if not f.startswith('.') and f != "imported.stl"]
                if not files: list_nexus_db.controls.append(ft.Text("Vacío. Inyecta un archivo.", color="#8B949E", italic=True))
                for f in files:
                    ext = f.lower().split('.')[-1]; p = os.path.join(EXPORT_DIR, f)
                    icon = "🧊" if ext=="stl" else ("🖼️" if ext=="png" else "🧩"); color = "#00E676" if ext=="stl" else ("#C51162" if ext=="png" else "white")
                    
                    actions = [
                        custom_icon_btn("✏️", lambda e, fn=f: open_rename_dialog(fn), "Renombrar"),
                        custom_icon_btn("⬇️", lambda e, fn=f: direct_download_file(e, fn), "Guardar a Download"), 
                        custom_icon_btn("🗑️", lambda e, fp=p: [os.remove(fp), refresh_nexus_db()], "Borrar")
                    ]
                    
                    if ext == "stl":
                        actions.insert(0, custom_icon_btn("📦", lambda e, fn=f: export_obj_file(e, fn), "Exportar OBJ"))
                        actions.insert(0, custom_icon_btn("▶️", lambda e, fp=p: load_file(fp), "Cargar STL"))
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
                shutil.copy(filepath, os.path.join(EXPORT_DIR, "imported.stl")); lbl_stl_status.value = f"✓ Activo: {fn}"; lbl_stl_status.color = "#00E676"
                select_tool("stl"); set_tab(1); update_code_wrapper(); status.value = f"✓ STL Inyectado en Memoria"
            elif ext == "jscad": txt_code.value = open(filepath).read(); set_tab(0); status.value = "✓ Código Cargado"
            page.update()

        current_android_dir = ANDROID_ROOT
        tf_path = ft.TextField(value=current_android_dir, expand=True, bgcolor="#161B22", height=40, text_size=12); list_android = ft.ListView(height=400, spacing=5)

        def file_action(filepath):
            ext = filepath.lower().split('.')[-1] if '.' in filepath else ''
            if ext in ["stl", "jscad"]: load_file(filepath)
            else: status.value = f"⚠️ Formato .{ext} no soportado."; status.color = "#FFAB00"; page.update()

        # NUEVA FUNCIÓN PARA IMPORTAR A LA DB SIN DEPENDER DEL FILEPICKER
        def copy_to_db(e, filepath, filename):
            try:
                shutil.copy(filepath, os.path.join(EXPORT_DIR, filename))
                status.value = f"✓ {filename} importado a NEXUS DB."
                status.color = "#00E676"
                refresh_nexus_db()
            except Exception as ex:
                status.value = f"❌ Error importando: {ex}"
                status.color = "red"
            page.update()

        def refresh_explorer(path):
            list_android.controls.clear()
            try:
                items = os.listdir(path); dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]; files = [f for f in items if os.path.isfile(os.path.join(path, f))]; dirs.sort(); files.sort()
                
                if path != "/" and path != "/storage" and path != "/storage/emulated":
                    list_android.controls.append(
                        ft.Container(
                            content=ft.Row([ft.Text("⬆️", size=20), ft.Text(".. (Subir nivel)", color="white", expand=True)]),
                            bgcolor="#30363D", padding=5, border_radius=5, on_click=lambda e: nav_to(os.path.dirname(path)), ink=True
                        )
                    )
                    
                for d in dirs:
                    if not d.startswith('.'):
                        list_android.controls.append(
                            ft.Container(
                                content=ft.Row([ft.Text("📁", size=20), ft.Text(d, color="#E6EDF3", expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS), custom_icon_btn("➡️", lambda e, p=os.path.join(path, d): nav_to(p), "Entrar")]),
                                bgcolor="#161B22", padding=5, border_radius=5, on_click=lambda e, p=os.path.join(path, d): nav_to(p), ink=True
                            )
                        )
                        
                for f in files:
                    ext = f.lower().split('.')[-1] if '.' in f else ''; icon = "📄"; color = "#8B949E"
                    if ext == "stl": icon = "🧊"; color = "#00E676"
                    elif ext == "jscad": icon = "🧩"; color = "#00E5FF"
                    elif ext == "png": icon = "🖼️"; color = "#C51162"
                    
                    p = os.path.join(path, f)
                    # Botón exclusivo para importar
                    actions = [
                        custom_icon_btn("▶️", lambda e, fp=p: file_action(fp), "Cargar directamente"),
                        custom_icon_btn("📥", lambda e, fp=p, fn=f: copy_to_db(e, fp, fn), "Importar archivo a la DB")
                    ]
                    list_android.controls.append(
                        ft.Container(
                            content=ft.Row([ft.Text(icon, size=20), ft.Text(f, color=color, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(f"{os.path.getsize(p) // 1024} KB", size=10, color="#8B949E")] + actions),
                            bgcolor="#21262D", padding=5, border_radius=5
                        )
                    )
            except PermissionError: list_android.controls.append(ft.Text("❌ Permiso Denegado.", color="red", weight="bold"))
            except Exception as ex: list_android.controls.append(ft.Text(f"Error: {ex}", color="red"))
            tf_path.value = path; page.update()

        def nav_to(path): nonlocal current_android_dir; current_android_dir = path; refresh_explorer(path)

        def save_to_android(e):
            if not os.path.isdir(current_android_dir): return
            fname = f"nexus_{int(time.time())}.jscad"
            try:
                with open(os.path.join(current_android_dir, fname), "w") as f: f.write(txt_code.value)
                status.value = f"✓ Guardado en Android: {fname}"; status.color = "#00E676"; refresh_explorer(current_android_dir)
            except Exception as ex: status.value = f"❌ Error guardando: {ex}"; status.color = "red"
            page.update()

        def save_project_to_nexus():
            fname = f"nexus_{int(time.time())}.jscad"
            with open(os.path.join(EXPORT_DIR, fname), "w") as f: f.write(txt_code.value)
            status.value = f"✓ Guardado en DB Interna: {fname}"; page.update()

        row_quick_paths = ft.Row([ft.ElevatedButton("🏠 Android", on_click=lambda _: nav_to("/storage/emulated/0"), bgcolor="#21262D", color="white"), ft.ElevatedButton("📥 Descargas", on_click=lambda _: nav_to("/storage/emulated/0/Download"), bgcolor="#21262D", color="white"), ft.ElevatedButton("📁 Nexus DB", on_click=lambda _: nav_to(EXPORT_DIR), bgcolor="#1B5E20", color="white")], scroll="auto")

        view_archivos = ft.Column([
            panel_calibre,
            ft.Container(content=ft.Column([
                ft.Text("🌐 INYECCIÓN WEB & NEXUS DB", color="#00E676", weight="bold"),
                ft.ElevatedButton("🌐 ABRIR INYECTOR WEB STL", url=f"http://{LAN_IP}:{LOCAL_PORT}/upload_ui.html", bgcolor="#00B0FF", color="white", width=float('inf')),
                ft.Row([ft.Text("Archivos y Renders listos:", color="#E6EDF3", size=11), ft.ElevatedButton("🔄", on_click=lambda _: refresh_nexus_db(), bgcolor="#1E1E1E", width=50)], alignment="spaceBetween"),
                ft.Container(content=list_nexus_db, bgcolor="#0B0E14", border_radius=5, padding=5)
            ]), bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#00E676")),
            ft.Container(content=ft.Column([
                ft.Text("📱 EXPLORADOR NATIVO ANDROID (Busca e Importa 📥)", color="#00E5FF", weight="bold"),
                row_quick_paths, ft.Row([tf_path, ft.ElevatedButton("Ir", on_click=lambda _: nav_to(tf_path.value), bgcolor="#FFAB00", color="black")]),
                ft.ElevatedButton("💾 GUARDAR CÓDIGO AQUÍ", on_click=save_to_android, bgcolor="#0D47A1", color="white", width=float('inf')),
                ft.Container(content=list_android, bgcolor="#0B0E14", border_radius=5, padding=5)
            ]), bgcolor="#161B22", padding=10, border_radius=8)
        ], expand=True, scroll="auto")

        view_ia = ft.Column([
            ft.Container(height=30),
            ft.Text("🤖 AGENTE IA AUTÓNOMO", size=24, color="#B388FF", weight="bold", text_align="center"),
            ft.Text("NEXUS ahora tiene su propio motor de IA integrado vía Web.", color="#E6EDF3", text_align="center"),
            ft.Container(height=30),
            ft.ElevatedButton("🚀 ABRIR ENTORNO IA", url=f"http://{LAN_IP}:{LOCAL_PORT}/ia_assistant.html", bgcolor="#8E24AA", color="white", height=80, width=float('inf')),
            ft.Container(height=20),
            ft.Text("💡 Nota: El código generado por la IA se inyectará automáticamente en la pestaña CODE.", color="#8B949E", size=12, text_align="center")
        ], expand=True, horizontal_alignment="center")

        main_container = ft.Container(content=view_editor, expand=True)

        def set_tab(idx):
            global PBR_STATE, LATEST_CODE_B64, LATEST_NEEDS_STL
            if idx in [0, 1, 2, 6]: PBR_STATE["mode"] = "single"
            if idx == 3: render_assembly_ui()
            if idx == 5: refresh_nexus_db(); refresh_explorer(current_android_dir)
            main_container.content = [view_editor, view_constructor, view_visor, view_ensamble, view_pbr, view_archivos, view_ia][idx]
            page.update()

        nav_bar = ft.Row([
            ft.ElevatedButton("💻 CODE", on_click=lambda _: set_tab(0), bgcolor="#21262D", color="white"),
            ft.ElevatedButton("🌐 PARAM", on_click=lambda _: set_tab(1), bgcolor="#FFAB00", color="black"),
            ft.ElevatedButton("👁️ 3D", on_click=lambda _: set_tab(2), bgcolor="#00E5FF", color="black"),
            ft.ElevatedButton("🧩 ENS", on_click=lambda _: set_tab(3), bgcolor="#7CB342", color="white"),
            ft.ElevatedButton("🎨 PBR", on_click=lambda _: set_tab(4), bgcolor="#C51162", color="white"),
            ft.ElevatedButton("📂 FILES", on_click=lambda _: set_tab(5), bgcolor="#21262D", color="white"),
            ft.ElevatedButton("🤖 IA", on_click=lambda _: set_tab(6), bgcolor="#B388FF", color="black"),
        ], scroll="auto")

        page.add(ft.Container(content=ft.Column([nav_bar, main_container, status], expand=True), padding=ft.padding.only(top=45, left=5, right=5, bottom=5), expand=True))
        select_tool("planetario"); refresh_explorer(current_android_dir)

    except Exception:
        page.clean(); page.add(ft.Container(ft.Text("CRASH FATAL:\n" + traceback.format_exc(), color="red"), padding=50)); page.update()

if __name__ == "__main__":
    if "TERMUX_VERSION" in os.environ: ft.app(target=main, port=0, view=ft.AppView.WEB_BROWSER)
    else: ft.app(target=main)