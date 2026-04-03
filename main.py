import flet as ft
import os, base64, json, threading, http.server, socket, time, warnings, traceback, shutil

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from urllib.parse import urlparse

warnings.simplefilter("ignore", DeprecationWarning)

# =========================================================
# RUTAS DEL SISTEMA
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
EXPORT_DIR = os.path.join(BASE_DIR, "nexus_proyectos")
os.makedirs(EXPORT_DIR, exist_ok=True)

# =========================================================
# TELEMETRÍA Y RED LOCAL
# =========================================================
def get_sys_info():
    cores = os.cpu_count() or 1
    cpu_p, ram_p = 0.0, 0.0
    if HAS_PSUTIL:
        cpu_p = psutil.cpu_percent()
        ram_p = psutil.virtual_memory().percent
    else:
        try:
            with open('/proc/meminfo', 'r') as f: lines = f.readlines()
            total = free = buffers = cached = 0
            for line in lines:
                if 'MemTotal:' in line: total = int(line.split()[1])
                elif 'MemFree:' in line: free = int(line.split()[1])
                elif 'Buffers:' in line: buffers = int(line.split()[1])
                elif 'Cached:' in line: cached = int(line.split()[1])
            if total > 0:
                used = total - free - buffers - cached
                ram_p = (used / total) * 100.0
            with open('/proc/loadavg', 'r') as f:
                load = float(f.read().split()[0])
            cpu_p = min((load / cores) * 100.0, 100.0)
        except: pass
    return cpu_p, ram_p, cores

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

# =========================================================
# SERVIDOR LOCAL WEBGL (SOLO PARA VISOR 3D)
# =========================================================
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', 0))
        LOCAL_PORT = s.getsockname()[1]
except:
    LOCAL_PORT = 8556

LAN_IP = get_lan_ip()
LATEST_CODE_B64 = ""

def get_stl_hash():
    path = os.path.join(EXPORT_DIR, "imported.stl")
    if os.path.exists(path): return str(os.path.getmtime(path))
    return ""

class NexusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global LATEST_CODE_B64
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/get_code_b64.json':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            payload = json.dumps({"code_b64": LATEST_CODE_B64, "stl_hash": get_stl_hash()})
            self.wfile.write(payload.encode())
            LATEST_CODE_B64 = "" 
        elif parsed.path.startswith('/exports/'):
            filename = parsed.path.replace('/exports/', '')
            filepath = os.path.join(EXPORT_DIR, filename)
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            try:
                filename = self.path.strip("/")
                if not filename: filename = "openscad_engine.html"
                with open(os.path.join(ASSETS_DIR, filename), "rb") as f:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(f.read())
            except:
                self.send_response(404)
                self.end_headers()
    def log_message(self, *args): pass

threading.Thread(target=lambda: http.server.HTTPServer(("0.0.0.0", LOCAL_PORT), NexusHandler).serve_forever(), daemon=True).start()

# =========================================================
# APP FLET MAIN
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v22.2 TITAN"
        page.theme_mode = "dark"
        page.bgcolor = "#0B0E14" 
        page.padding = 0 
        
        status = ft.Text("NEXUS v22.2 TITAN | Selector Nativo Optimizado", color="#00E5FF", weight="bold")

        T_INICIAL = "function main() {\n  return CSG.cube({center:[0,0,GH/2], radius:[GW/2, GL/2, GH/2]});\n}"
        txt_code = ft.TextField(label="Código Fuente (JS-CSG)", multiline=True, expand=True, value=T_INICIAL, bgcolor="#161B22", color="#58A6FF", border_color="#30363D", text_size=12)

        ensamble_stack = []
        herramienta_actual = "custom"
        modo_ensamble = False
        
        stl_tools_list = ["stl", "stl_flatten", "stl_split", "stl_crop", "stl_drill", "stl_mount", "stl_ears", "stl_patch", "stl_hex", "stl_guard"]

        def clear_editor():
            nonlocal ensamble_stack
            ensamble_stack = []
            txt_code.value = "function main() {\n  return CSG.cube({radius:[0,0,0]});\n}"
            status.value = "✓ Código borrado."
            status.color = "#B71C1C"
            txt_code.update(); page.update()

        def inject_snippet(code_snippet):
            c = txt_code.value
            pos = c.rfind('return ')
            if pos != -1: txt_code.value = c[:pos] + code_snippet + "\n  " + c[pos:]
            else: txt_code.value = c + "\n" + code_snippet
            txt_code.update()

        def update_code_wrapper(e=None): generate_param_code()

        def create_slider(label, min_v, max_v, val, is_int):
            txt_val = ft.Text(f"{int(val) if is_int else val:.1f}", color="#00E5FF", width=45, text_align="right", size=13, weight="bold")
            sl = ft.Slider(min=min_v, max=max_v, value=val, expand=True, active_color="#00E5FF", inactive_color="#2A303C")
            if is_int: sl.divisions = int(max_v - min_v)
            def internal_change(e):
                txt_val.value = f"{int(sl.value) if is_int else sl.value:.1f}"
                txt_val.update(); 
                if not modo_ensamble: update_code_wrapper()
            sl.on_change = internal_change
            return sl, ft.Row([ft.Text(label, width=110, size=12, color="#E6EDF3"), sl, txt_val])

        # === PARAMETROS GLOBALES ===
        sl_g_w, r_g_w = create_slider("Ancho (GW)", 1, 300, 50, False)
        sl_g_l, r_g_l = create_slider("Largo (GL)", 1, 300, 50, False)
        sl_g_h, r_g_h = create_slider("Alto (GH)", 1, 300, 20, False)
        sl_g_t, r_g_t = create_slider("Grosor (GT)", 0.5, 20, 2, False)
        sl_g_tol, r_g_tol = create_slider("Tol. Global (G_TOL)", 0.0, 2.0, 0.2, False)

        def prepare_js_payload():
            header = f"  var GW = {sl_g_w.value}; var GL = {sl_g_l.value}; var GH = {sl_g_h.value}; var GT = {sl_g_t.value}; var G_TOL = {sl_g_tol.value};\n"
            c = txt_code.value
            if "function main() {" in c: c = c.replace("function main() {", "function main() {\n" + header, 1)
            else: c = header + "\n" + c
            return c

        def run_render():
            global LATEST_CODE_B64
            LATEST_CODE_B64 = base64.b64encode(prepare_js_payload().encode('utf-8')).decode()
            set_tab(2); page.update()

        sw_ensamble = ft.Switch(label="Activar Ensamblador", value=False, active_color="#FFAB00")
        def toggle_ensamble(e):
            nonlocal modo_ensamble
            modo_ensamble = sw_ensamble.value
            panel_ensamble_ops.visible = modo_ensamble; page.update()
        sw_ensamble.on_change = toggle_ensamble

        def parse_current_tool_to_stack_var():
            code_lines = txt_code.value.split('\n')
            var_name = f"obj_{len(ensamble_stack)}"
            body = []
            for line in code_lines[1:-1]:
                if line.strip().startswith("return "):
                    ret_val = line.replace("return", "").replace(";", "").strip()
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
            final_code += f"  return {final_var};\n}}"
            txt_code.value = final_code; txt_code.update(); page.update()

        panel_ensamble_ops = ft.Row([
            ft.ElevatedButton("➕ UNIR", on_click=lambda _: add_to_stack("union"), bgcolor="#1B5E20", color="white", expand=True),
            ft.ElevatedButton("➖ RESTAR", on_click=lambda _: add_to_stack("subtract"), bgcolor="#B71C1C", color="white", expand=True)
        ], visible=False)

        panel_globales = ft.Container(content=ft.Column([ft.Row([ft.Text("🌐 PARÁMETROS GLOBALES", color="#00E5FF", weight="bold", size=11), sw_ensamble], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), r_g_w, r_g_l, r_g_h, r_g_t, r_g_tol, panel_ensamble_ops]), bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#333333"))

        def inst(texto): return ft.Text("ℹ️ " + texto, color="#FFD54F", size=11, italic=True)
        col_custom = ft.Column([ft.Text("Modo Código Libre", color="#00E676")], visible=True)

        # =========================================================
        # FILE PICKER NATIVO (CORREGIDO SIN EVENT TYPE)
        # =========================================================
        file_picker = ft.FilePicker()
        
        # Le quitamos el ": ft.FilePickerResultEvent" a la 'e' para que Flet antiguo no crashee
        def on_file_picked(e):
            if e.files and len(e.files) > 0:
                filepath = e.files[0].path
                ext = filepath.lower().split('.')[-1] if '.' in filepath else ''
                if ext == "stl":
                    dest = os.path.join(EXPORT_DIR, "imported.stl")
                    try:
                        shutil.copy(filepath, dest)
                        lbl_stl_status.value = f"✓ STL Listo: {e.files[0].name}"
                        lbl_stl_status.color = "#00E676"
                        select_tool("stl")
                        set_tab(1)
                        update_code_wrapper()
                        status.value = f"✓ STL Importado: {e.files[0].name}"
                        status.color = "#00E676"
                    except Exception as ex:
                        status.value = f"❌ Error leyendo STL: {ex}"; status.color = "red"
                elif ext == "jscad":
                    try:
                        txt_code.value = open(filepath).read()
                        set_tab(0)
                        status.value = f"✓ Código {e.files[0].name} cargado."; status.color = "#00E676"
                    except Exception as ex:
                        status.value = f"❌ Error leyendo JSCAD: {ex}"; status.color = "red"
                else:
                    status.value = f"⚠️ Formato .{ext} no soportado."; status.color = "#FFAB00"
            page.update()

        file_picker.on_result = on_file_picked
        page.overlay.append(file_picker)

        # =========================================================
        # TRANSFORMACIÓN STL UNIVERSAL
        # =========================================================
        lbl_stl_status = ft.Text("Ningún STL cargado aún en memoria.", color="#8B949E", size=11)
        sl_stl_sc, r_stl_sc = create_slider("Escala (%)", 1, 500, 100, True)
        sl_stl_x, r_stl_x = create_slider("Mover X", -200, 200, 0, False)
        sl_stl_y, r_stl_y = create_slider("Mover Y", -200, 200, 0, False)
        sl_stl_z, r_stl_z = create_slider("Mover Z", -200, 200, 0, False)

        panel_stl_transform = ft.Container(content=ft.Column([
            ft.Row([ft.Text("🔄 Transformación Base STL", color="#00E676", weight="bold"), lbl_stl_status]),
            ft.ElevatedButton("📂 BUSCAR ARCHIVO (NATIVO)", on_click=lambda _: file_picker.pick_files(allowed_extensions=["stl", "jscad"]), bgcolor="#00E5FF", color="black", width=float('inf'), height=35),
            r_stl_sc, r_stl_x, r_stl_y, r_stl_z
        ]), bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#00E676"), visible=False)

        col_stl = ft.Column([ft.Text("Híbrido Básico (Solo Visor STL)", color="#00E676", weight="bold")], visible=False)

        # =========================================================
        # HERRAMIENTAS STL FORGE
        # =========================================================
        
        # 1. Flatten
        sl_stlf_z, r_stlf_z = create_slider("Corte Inferior (Z)", 0, 50, 1, False)
        col_stl_flatten = ft.Column([ft.Text("📏 Aplanar Base", color="#00E676", weight="bold"), inst("Elimina los primeros milímetros de abajo para asegurar una base perfectamente plana para la cama de impresión."), ft.Container(content=ft.Column([r_stlf_z]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # 2. Split
        dd_stls_axis = ft.Dropdown(options=[ft.dropdown.Option("X"), ft.dropdown.Option("Y"), ft.dropdown.Option("Z")], value="Z", bgcolor="#161B22", width=100)
        dd_stls_axis.on_change = update_code_wrapper 
        
        sl_stls_pos, r_stls_pos = create_slider("Posición Corte", -150, 150, 0, False)
        sw_stls_inv = ft.Switch(label="Invertir Lado", value=False, active_color="#FFAB00")
        sw_stls_inv.on_change = update_code_wrapper

        col_stl_split = ft.Column([ft.Text("🔪 Cortador Avanzado (Split)", color="#00E676", weight="bold"), inst("Guillotina el modelo en el eje y posición exacta. Quédate con la mitad que necesites."), ft.Container(content=ft.Column([ft.Row([ft.Text("Eje de Corte:"), dd_stls_axis]), r_stls_pos, sw_stls_inv]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # 3. Crop Box
        sl_stlc_sx, r_stlc_sx = create_slider("Tamaño Caja X", 10, 300, 50, False)
        sl_stlc_sy, r_stlc_sy = create_slider("Tamaño Caja Y", 10, 300, 50, False)
        sl_stlc_sz, r_stlc_sz = create_slider("Tamaño Caja Z", 10, 300, 50, False)
        col_stl_crop = ft.Column([ft.Text("✂️ Recorte de Aislamiento (Crop Box)", color="#00E676", weight="bold"), inst("Todo lo que quede FUERA de esta caja será eliminado. Usa los controles 'Mover' arriba para posicionar el dron dentro de la caja."), ft.Container(content=ft.Column([r_stlc_sx, r_stlc_sy, r_stlc_sz]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # 4. Drill 3D
        dd_stld_axis = ft.Dropdown(options=[ft.dropdown.Option("X"), ft.dropdown.Option("Y"), ft.dropdown.Option("Z")], value="Z", bgcolor="#161B22", width=100)
        dd_stld_axis.on_change = update_code_wrapper
        
        sl_stld_r, r_stld_r = create_slider("Radio Agujero", 0.5, 20, 1.6, False)
        sl_stld_p1, r_stld_p1 = create_slider("Posición Coord 1", -150, 150, 0, False)
        sl_stld_p2, r_stld_p2 = create_slider("Posición Coord 2", -150, 150, 0, False)
        col_stl_drill = ft.Column([ft.Text("🕳️ Taladro Universal 3D", color="#00E676", weight="bold"), inst("Perfora infinitamente a través del modelo. Coord 1 y 2 dependen del eje elegido."), ft.Container(content=ft.Column([ft.Row([ft.Text("Eje de Taladro:"), dd_stld_axis]), r_stld_r, r_stld_p1, r_stld_p2]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # 5. Mounts
        sl_stlm_w, r_stlm_w = create_slider("Ancho Orejetas", 10, 100, 40, False)
        sl_stlm_r, r_stlm_r = create_slider("Radio Tornillo", 1, 10, 2.2, False)
        sl_stlm_d, r_stlm_d = create_slider("Separación Ext.", 20, 200, 80, False)
        col_stl_mount = ft.Column([ft.Text("🔩 Añadir Orejetas de Montaje", color="#00E676", weight="bold"), inst("Añade pestañas atornillables a los lados (Eje X) para fijar tu modelo a una superficie."), ft.Container(content=ft.Column([r_stlm_w, r_stlm_r, r_stlm_d]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # 6. Mouse Ears
        sl_stle_r, r_stle_r = create_slider("Radio Discos", 5, 30, 15, False)
        sl_stle_d, r_stle_d = create_slider("Apertura XY", 10, 200, 50, False)
        col_stl_ears = ft.Column([ft.Text("🖱️ Discos Anti-Warping", color="#00E676", weight="bold"), inst("Genera parches ultradelgados (0.4mm) en las esquinas inferiores para evitar que la pieza se despegue de la cama."), ft.Container(content=ft.Column([r_stle_r, r_stle_d]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # 7. Block Patch
        sl_stlp_sx, r_stlp_sx = create_slider("Tamaño X", 1, 100, 20, False)
        sl_stlp_sy, r_stlp_sy = create_slider("Tamaño Y", 1, 100, 20, False)
        sl_stlp_sz, r_stlp_sz = create_slider("Tamaño Z", 1, 100, 10, False)
        col_stl_patch = ft.Column([ft.Text("🧱 Parche de Refuerzo Sólido", color="#00E676", weight="bold"), inst("Inyecta un bloque sólido de material en el STL. Usa 'Mover' global para llevar el bloque a una zona débil que quieras reforzar."), ft.Container(content=ft.Column([r_stlp_sx, r_stlp_sy, r_stlp_sz]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # 8 & 9. Hex & Guard 
        sl_stlx_a, r_stlx_a = create_slider("Área Aplicada", 20, 200, 100, True); sl_stlx_r, r_stlx_r = create_slider("Radio Hex", 2, 20, 5, False)
        col_stl_hex = ft.Column([ft.Text("🐝 Aligerado Honeycomb", color="#00E676", weight="bold"), inst("Perfora un patrón de panel de abejas para reducir el peso."), ft.Container(content=ft.Column([r_stlx_a, r_stlx_r]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        sl_stlg_x, r_stlg_x = create_slider("Posición X", -100, 100, 50, False); sl_stlg_y, r_stlg_y = create_slider("Posición Y", -100, 100, 50, False); sl_stlg_r, r_stlg_r = create_slider("Radio Aro", 10, 150, 40, False); sl_stlg_h, r_stlg_h = create_slider("Altura Guard", 2, 30, 15, False)
        col_stl_guard = ft.Column([ft.Text("🛡️ Añadir Protector de Hélice", color="#00E676", weight="bold"), inst("Genera y fusiona un protector circular al brazo del dron."), ft.Container(content=ft.Column([r_stlg_x, r_stlg_y, r_stlg_r, r_stlg_h]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # =========================================================
        # OTRAS HERRAMIENTAS
        # =========================================================
        tf_texto = ft.TextField(label="Escribe Texto", value="NEXUS", max_length=15, bgcolor="#161B22")
        dd_txt_estilo = ft.Dropdown(options=[ft.dropdown.Option("Voxel Fino"), ft.dropdown.Option("Voxel Grueso"), ft.dropdown.Option("Braille")], value="Voxel Grueso", expand=True, bgcolor="#161B22")
        dd_txt_base = ft.Dropdown(options=[ft.dropdown.Option("Solo Texto"), ft.dropdown.Option("Llavero (Anilla)"), ft.dropdown.Option("Placa Atornillable"), ft.dropdown.Option("Soporte de Mesa"), ft.dropdown.Option("Colgante Militar"), ft.dropdown.Option("Placa Ovalada")], value="Colgante Militar", expand=True, bgcolor="#161B22")
        sw_txt_grabado = ft.Switch(label="Texto Grabado (Hueco)", value=False, active_color="#00E5FF")
        
        tf_texto.on_change = update_code_wrapper
        dd_txt_estilo.on_change = update_code_wrapper
        dd_txt_base.on_change = update_code_wrapper
        sw_txt_grabado.on_change = update_code_wrapper

        col_texto = ft.Column([ft.Text("Tipografía y Placas Especiales", color="#880E4F", weight="bold"), inst("GH define el grosor de la placa. 'Grabado' hunde el texto en el material."), ft.Container(content=ft.Column([tf_texto, ft.Row([dd_txt_estilo, dd_txt_base]), sw_txt_grabado]), bgcolor="#161B22", padding=10, border_radius=8)], visible=False)

        # =========================================================
        # GENERADOR DE CÓDIGO CORE
        # =========================================================
        def get_stl_base_js():
            return f"""
  var sc = {sl_stl_sc.value / 100.0}; var tx = {sl_stl_x.value}; var ty = {sl_stl_y.value}; var tz = {sl_stl_z.value};
  var stlParts = Array.isArray(IMPORTED_STL) ? IMPORTED_STL : [IMPORTED_STL];
  var finalPolys = [];
  stlParts.forEach(function(part) {{
      var polys = part.polygons || (part.toPolygons ? part.toPolygons() : []);
      polys.forEach(function(p) {{
          var newVerts = p.vertices.map(function(v) {{
              var VecClass = (typeof CSG.Vector3D !== 'undefined') ? CSG.Vector3D : ((typeof CSG.Vector !== 'undefined') ? CSG.Vector : null);
              return new CSG.Vertex(
                  new VecClass(v.pos.x * sc + tx, v.pos.y * sc + ty, v.pos.z * sc + tz),
                  new VecClass(v.normal.x, v.normal.y, v.normal.z)
              );
          }});
          finalPolys.push(new CSG.Polygon(newVerts, p.shared));
      }});
  }});
  var dron = CSG.fromPolygons(finalPolys);
  if(!dron.polygons || dron.polygons.length === 0) return CSG.cube({{radius:[0.1,0.1,0.1]}});
"""

        def generate_param_code():
            h = herramienta_actual
            code = "function main() {\n"
            
            if h == "custom": pass
            
            elif h in stl_tools_list:
                code += f"  // ================================================\n"
                code += f"  // ULTIMATE STL FORGE ACTIVO\n"
                code += f"  // ================================================\n"
                code += get_stl_base_js()

                if h == "stl":
                    code += f"\n  return dron;\n}}"

                elif h == "stl_flatten":
                    zc = sl_stlf_z.value
                    code += f"\n  var flattenCut = CSG.cube({{center:[0, 0, -500 + {zc}], radius:[1000, 1000, 500]}});\n"
                    code += f"  return dron.subtract(flattenCut);\n}}"

                elif h == "stl_split":
                    axis = dd_stls_axis.value; pos = sl_stls_pos.value; inv = sw_stls_inv.value
                    offset = 500 if inv else -500
                    cx = pos + offset if axis == 'X' else 0
                    cy = pos + offset if axis == 'Y' else 0
                    cz = pos + offset if axis == 'Z' else 0
                    rx = 500 if axis == 'X' else 1000
                    ry = 500 if axis == 'Y' else 1000
                    rz = 500 if axis == 'Z' else 1000
                    code += f"\n  var splitCut = CSG.cube({{center:[{cx}, {cy}, {cz}], radius:[{rx}, {ry}, {rz}]}});\n"
                    code += f"  return dron.subtract(splitCut);\n}}"

                elif h == "stl_crop":
                    sx = sl_stlc_sx.value; sy = sl_stlc_sy.value; sz = sl_stlc_sz.value
                    code += f"\n  var cropBox = CSG.cube({{center:[0, 0, 0], radius:[{sx/2}, {sy/2}, {sz/2}]}});\n"
                    code += f"  return dron.intersect(cropBox);\n}}"

                elif h == "stl_drill":
                    axis = dd_stld_axis.value; rad = sl_stld_r.value; p1 = sl_stld_p1.value; p2 = sl_stld_p2.value
                    if axis == 'X': start = f"[-500, {p1}, {p2}]"; end = f"[500, {p1}, {p2}]"
                    elif axis == 'Y': start = f"[{p1}, -500, {p2}]"; end = f"[{p1}, 500, {p2}]"
                    else: start = f"[{p1}, {p2}, -500]"; end = f"[{p1}, {p2}, 500]"
                    code += f"\n  var taladro = CSG.cylinder({{start:{start}, end:{end}, radius:{rad}, slices:32}});\n"
                    code += f"  return dron.subtract(taladro);\n}}"

                elif h == "stl_mount":
                    w = sl_stlm_w.value; r = sl_stlm_r.value; d = sl_stlm_d.value
                    code += f"\n  var m1 = CSG.cube({{center:[{d/2}, 0, 0], radius:[{w/2}, 15, 3]}}).subtract(CSG.cylinder({{start:[{d/2},0,-5], end:[{d/2},0,5], radius:{r}, slices:32}}));\n"
                    code += f"  var m2 = CSG.cube({{center:[{-d/2}, 0, 0], radius:[{w/2}, 15, 3]}}).subtract(CSG.cylinder({{start:[{-d/2},0,-5], end:[{-d/2},0,5], radius:{r}, slices:32}}));\n"
                    code += f"  return dron.union(m1).union(m2);\n}}"

                elif h == "stl_ears":
                    r = sl_stle_r.value; d = sl_stle_d.value
                    code += f"\n  var t = 0.4; // Grosor típico de 2 capas\n"
                    code += f"  var e1 = CSG.cylinder({{start:[{d/2}, {d/2}, 0], end:[{d/2}, {d/2}, t], radius:{r}, slices:32}});\n"
                    code += f"  var e2 = CSG.cylinder({{start:[{-d/2}, {d/2}, 0], end:[{-d/2}, {d/2}, t], radius:{r}, slices:32}});\n"
                    code += f"  var e3 = CSG.cylinder({{start:[{d/2}, {-d/2}, 0], end:[{d/2}, {-d/2}, t], radius:{r}, slices:32}});\n"
                    code += f"  var e4 = CSG.cylinder({{start:[{-d/2}, {-d/2}, 0], end:[{-d/2}, {-d/2}, t], radius:{r}, slices:32}});\n"
                    code += f"  return dron.union(e1).union(e2).union(e3).union(e4);\n}}"

                elif h == "stl_patch":
                    sx = sl_stlp_sx.value; sy = sl_stlp_sy.value; sz = sl_stlp_sz.value
                    code += f"\n  var patchBlock = CSG.cube({{center:[0, 0, 0], radius:[{sx/2}, {sy/2}, {sz/2}]}});\n"
                    code += f"  return dron.union(patchBlock);\n}}"

                elif h == "stl_hex":
                    area = sl_stlx_a.value; hex_r = sl_stlx_r.value
                    code += f"\n  var hex_r = {hex_r}; var t = 1.5; var dx = hex_r * 1.732 + t; var dy = hex_r * 1.5 + t;\n"
                    code += f"  var holes = null; var maxA = {area/2};\n"
                    code += f"  for(var x = -maxA; x < maxA; x += dx) {{ for(var y = -maxA; y < maxA; y += dy) {{\n"
                    code += f"      var offset = (Math.abs(Math.round(y/dy)) % 2 === 1) ? dx/2 : 0; var cx = x + offset;\n"
                    code += f"      if(cx < maxA && cx > -maxA) {{\n"
                    code += f"          var hex = CSG.cylinder({{start:[cx, y, -500], end:[cx, y, 500], radius:hex_r, slices:6}});\n"
                    code += f"          if(holes === null) holes = hex; else holes = holes.union(hex);\n"
                    code += f"      }}\n  }} }}\n"
                    code += f"  if(holes !== null) return dron.subtract(holes);\n  return dron;\n}}"

                elif h == "stl_guard":
                    px = sl_stlg_x.value; py = sl_stlg_y.value; pr = sl_stlg_r.value; ph = sl_stlg_h.value
                    code += f"\n  var px = {px}; var py = {py}; var pr = {pr}; var ph = {ph}; var t = 3;\n"
                    code += f"  var ext = CSG.cylinder({{start:[px, py, 0], end:[px, py, ph], radius:pr+t, slices:64}});\n"
                    code += f"  var int_c = CSG.cylinder({{start:[px, py, -1], end:[px, py, ph+1], radius:pr, slices:64}});\n"
                    code += f"  var guard = ext.subtract(int_c);\n"
                    code += f"  var spoke1 = CSG.cube({{center:[px, py, ph/2], radius:[pr, t/2, ph/2]}});\n"
                    code += f"  var spoke2 = CSG.cube({{center:[px, py, ph/2], radius:[t/2, pr, ph/2]}});\n"
                    code += f"  guard = guard.union(spoke1).union(spoke2);\n"
                    code += f"  return dron.union(guard);\n}}"

            elif h == "texto":
                txt_input = tf_texto.value.upper()[:15]; estilo = dd_txt_estilo.value; base = dd_txt_base.value; grabado = sw_txt_grabado.value
                if not txt_input: txt_input = " "
                code += f"  var texto = \"{txt_input}\"; var h = GH;\n"
                code += f"  var font = {{ 'A':[14,17,31,17,17], 'B':[30,17,30,17,30], 'C':[14,17,16,17,14], 'D':[30,17,17,17,30], 'E':[31,16,30,16,31], 'F':[31,16,30,16,16], 'G':[14,17,23,17,14], 'H':[17,17,31,17,17], 'I':[14,4,4,4,14], 'J':[7,2,2,18,12], 'K':[17,18,28,18,17], 'L':[16,16,16,16,31], 'M':[17,27,21,17,17], 'N':[17,25,21,19,17], 'O':[14,17,17,17,14], 'P':[30,17,30,16,16], 'Q':[14,17,21,18,13], 'R':[30,17,30,18,17], 'S':[14,16,14,1,14], 'T':[31,4,4,4,4], 'U':[17,17,17,17,14], 'V':[17,17,17,10,4], 'W':[17,17,21,27,17], 'X':[17,10,4,10,17], 'Y':[17,10,4,4,4], 'Z':[31,2,4,8,31], ' ':[0,0,0,0,0], '0':[14,17,17,17,14], '1':[4,12,4,4,14], '2':[14,1,14,16,31], '3':[14,1,14,1,14], '4':[18,18,31,2,2], '5':[31,16,14,1,14], '6':[14,16,30,17,14], '7':[31,1,2,4,8], '8':[14,17,14,17,14], '9':[14,17,15,1,14] }};\n"
                z_start = "h/2" if not grabado else "h - 1"
                h_letra = "h/2" if not grabado else "h+2"
                code += "  if (pText === null) pText = CSG.cube({center:[0,0,0], radius:[0.01, 0.01, 0.01]});\n  var baseObj = CSG.cube({center:[0,0,0], radius:[0.1, 0.1, 0.1]});\n"
                code += "  return pText;\n}"

            if not modo_ensamble and h != "custom": 
                txt_code.value = code
            txt_code.update()

        def select_tool(nombre_herramienta):
            nonlocal herramienta_actual
            herramienta_actual = nombre_herramienta
            paneles = [
                col_custom, col_stl, col_stl_flatten, col_stl_split, col_stl_crop, 
                col_stl_drill, col_stl_mount, col_stl_ears, col_stl_patch, 
                col_stl_hex, col_stl_guard, col_texto
            ]
            for p in paneles: p.visible = False
            
            panel_stl_transform.visible = nombre_herramienta in stl_tools_list

            if nombre_herramienta == "custom": col_custom.visible = True
            elif nombre_herramienta == "stl": col_stl.visible = True
            elif nombre_herramienta == "stl_flatten": col_stl_flatten.visible = True
            elif nombre_herramienta == "stl_split": col_stl_split.visible = True
            elif nombre_herramienta == "stl_crop": col_stl_crop.visible = True
            elif nombre_herramienta == "stl_drill": col_stl_drill.visible = True
            elif nombre_herramienta == "stl_mount": col_stl_mount.visible = True
            elif nombre_herramienta == "stl_ears": col_stl_ears.visible = True
            elif nombre_herramienta == "stl_patch": col_stl_patch.visible = True
            elif nombre_herramienta == "stl_hex": col_stl_hex.visible = True
            elif nombre_herramienta == "stl_guard": col_stl_guard.visible = True
            elif nombre_herramienta == "texto": col_texto.visible = True
            generate_param_code(); page.update()

        def thumbnail(icon, title, tool_id, color): return ft.Container(content=ft.Column([ft.Text(icon, size=24), ft.Text(title, size=10, color="white", weight="bold")], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), width=75, height=70, bgcolor=color, border_radius=8, on_click=lambda _: select_tool(tool_id), ink=True, border=ft.border.all(1, "#30363D"))

        cat_especial = ft.Row([thumbnail("🧠", "Código Libre", "custom", "#000000"), thumbnail("🔠", "Placas Texto", "texto", "#880E4F")], scroll="auto")
        
        cat_stl_forge = ft.Row([
            thumbnail("🧊", "Ver STL", "stl", "#1B5E20"),
            thumbnail("📏", "Aplanar Base", "stl_flatten", "#00C853"),
            thumbnail("🔪", "Dividir (Split)", "stl_split", "#00C853"),
            thumbnail("✂️", "Aislar (Crop)", "stl_crop", "#00C853"),
            thumbnail("🕳️", "Taladro 3D", "stl_drill", "#00E676"),
            thumbnail("🔩", "Orejetas Mnt", "stl_mount", "#00E676"),
            thumbnail("🖱️", "Discos Warp", "stl_ears", "#00E676"),
            thumbnail("🧱", "Refuerzo", "stl_patch", "#B2FF59"),
            thumbnail("🐝", "Honeycomb", "stl_hex", "#B2FF59"),
            thumbnail("🛡️", "Aro Hélice", "stl_guard", "#B2FF59")
        ], scroll="auto")

        view_constructor = ft.Column([
            panel_globales, panel_stl_transform,
            ft.Text("🚀 ULTIMATE STL FORGE (Modificadores):", size=13, color="#00E676", weight="bold"), cat_stl_forge,
            ft.Text("💡 Otras Herramientas:", size=12, color="#8B949E"), cat_especial,
            ft.Divider(color="#30363D"),
            
            col_custom, col_stl, col_stl_flatten, col_stl_split, col_stl_crop, 
            col_stl_drill, col_stl_mount, col_stl_ears, col_stl_patch, 
            col_stl_hex, col_stl_guard, col_texto,
            
            ft.Container(height=10),
            ft.ElevatedButton("▶ ENVIAR AL WORKER (RENDER 3D)", on_click=lambda _: run_render(), color="black", bgcolor="#00E676", height=60, width=float('inf'))
        ], expand=True, scroll="auto")

        view_editor = ft.Column([
            ft.Row([ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save_project_to_nexus(), color="white", bgcolor="#0D47A1"), ft.ElevatedButton("🗑️ RESET TOTAL", on_click=lambda _: clear_editor(), color="white", bgcolor="#B71C1C")], scroll="auto"),
            txt_code
        ], expand=True)

        # =========================================================
        # SECCIÓN VISOR 3D
        # =========================================================
        pb_cpu = ft.ProgressBar(width=100, color="#FFAB00", bgcolor="#30363D", value=0, expand=True)
        txt_cpu_val = ft.Text("0.0%", size=11, color="#FFAB00", width=40, text_align="right")
        pb_ram = ft.ProgressBar(width=100, color="#00E5FF", bgcolor="#30363D", value=0, expand=True)
        txt_ram_val = ft.Text("0.0%", size=11, color="#00E5FF", width=40, text_align="right")
        txt_cores = ft.Text("CORES: ?", size=11, color="#8B949E", weight="bold")

        hw_panel = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("📊 TELEMETRÍA HARDWARE", size=11, color="#E6EDF3", weight="bold"), txt_cores], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("CPU", size=11, color="#FFAB00", weight="bold", width=30), pb_cpu, txt_cpu_val]),
                ft.Row([ft.Text("RAM", size=11, color="#00E5FF", weight="bold", width=30), pb_ram, txt_ram_val])
            ], spacing=5),
            bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#333333")
        )

        def hw_monitor_loop():
            while True:
                time.sleep(1.5)
                try:
                    if main_container.content == view_visor:
                        cpu, ram, cores = get_sys_info()
                        pb_cpu.value = cpu / 100.0; txt_cpu_val.value = f"{cpu:.1f}%"
                        pb_ram.value = ram / 100.0; txt_ram_val.value = f"{ram:.1f}%"
                        txt_cores.value = f"CORES: {cores}"
                        hw_panel.update()
                except: pass

        threading.Thread(target=hw_monitor_loop, daemon=True).start()

        view_visor = ft.Column([
            ft.Container(height=5), hw_panel, ft.Container(height=5),
            ft.Text("Motor Web Worker / Multi-Hilo", text_align="center", color="#00E5FF", weight="bold"),
            ft.Row([ft.ElevatedButton("🔄 ABRIR VISOR 3D (LOCAL)", url="http://127.0.0.1:" + str(LOCAL_PORT) + "/", color="black", bgcolor="#00E676", height=60, expand=True)], alignment=ft.MainAxisAlignment.CENTER)
        ], expand=True, scroll="auto")
        
        # =========================================================
        # PESTAÑA FILES: INTERFAZ NATIVA Y LIMPIA
        # =========================================================
        def save_project_to_nexus():
            fname = f"nexus_{int(time.time())}.jscad"
            with open(os.path.join(EXPORT_DIR, fname), "w") as f: f.write(txt_code.value)
            status.value = f"✓ Guardado en DB Interna: {fname}"; page.update()

        view_archivos = ft.Column([
            ft.Text("GESTIÓN DE ARCHIVOS Y PROYECTOS", size=16, color="#E6EDF3", weight="bold"),
            ft.Divider(color="#30363D"),
            ft.Container(height=10),
            ft.ElevatedButton(
                "📂 IMPORTAR STL DESDE ANDROID", 
                on_click=lambda _: file_picker.pick_files(allowed_extensions=["stl", "jscad"]), 
                bgcolor="#00E676", color="black", width=float('inf'), height=70, 
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
            ),
            ft.Text("Abre el selector nativo de tu móvil (como Cx File Explorer o Archivos). Soporta .STL y .JSCAD", size=11, color="#8B949E", italic=True),
            ft.Container(height=20),
            ft.ElevatedButton(
                "💾 GUARDAR PROYECTO ACTUAL", 
                on_click=lambda _: save_project_to_nexus(), 
                bgcolor="#21262D", color="white", width=float('inf'), height=50
            )
        ], expand=True)

        main_container = ft.Container(content=view_editor, expand=True)

        def set_tab(idx):
            if idx == 2:
                global LATEST_CODE_B64
                LATEST_CODE_B64 = base64.b64encode(prepare_js_payload().encode('utf-8')).decode()
            main_container.content = [view_editor, view_constructor, view_visor, view_archivos][idx]
            page.update()

        nav_bar = ft.Row([
            ft.ElevatedButton("💻 CODE", on_click=lambda _: set_tab(0), bgcolor="#21262D", color="white"),
            ft.ElevatedButton("🛠️ STL FORGE", on_click=lambda _: set_tab(1), color="black", bgcolor="#00E676"),
            ft.ElevatedButton("👁️ 3D", on_click=lambda _: set_tab(2), color="black", bgcolor="#00E5FF"),
            ft.ElevatedButton("📂 FILES", on_click=lambda _: set_tab(3), bgcolor="#21262D", color="white"),
        ], scroll="auto")

        page.add(ft.Container(content=ft.Column([nav_bar, main_container, status], expand=True), padding=ft.padding.only(top=45, left=5, right=5, bottom=5), expand=True))
        select_tool("custom")

    except Exception:
        page.clean(); page.add(ft.Container(ft.Text("CRASH FATAL:\n" + traceback.format_exc(), color="red"), padding=50)); page.update()

if __name__ == "__main__":
    if "TERMUX_VERSION" in os.environ: ft.app(target=main, port=0, view=ft.AppView.WEB_BROWSER)
    else: ft.app(target=main)