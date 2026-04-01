import flet as ft
import os, base64, json, threading, http.server, socket, time, warnings, subprocess, tempfile, traceback
from urllib.parse import urlparse

warnings.simplefilter("ignore", DeprecationWarning)

# =========================================================
# RUTAS BLINDADAS 
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

try:
    EXPORT_DIR = os.path.join(BASE_DIR, "nexus_proyectos")
    os.makedirs(EXPORT_DIR, exist_ok=True)
except:
    EXPORT_DIR = os.path.join(tempfile.gettempdir(), "nexus_proyectos")
    os.makedirs(EXPORT_DIR, exist_ok=True)

# =========================================================
# MOTOR SERVIDOR LOCAL (VISOR 3D)
# =========================================================
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        LOCAL_PORT = s.getsockname()[1]
except:
    LOCAL_PORT = 8556

LATEST_CODE_B64 = ""

class NexusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global LATEST_CODE_B64
        parsed = urlparse(self.path)
        if parsed.path == '/api/get_code_b64.json':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"code_b64": LATEST_CODE_B64}).encode())
        else:
            try:
                filename = self.path.strip("/")
                if not filename or filename == "": filename = "openscad_engine.html"
                fpath = os.path.join(ASSETS_DIR, filename)
                with open(fpath, "rb") as f:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(f.read())
            except:
                self.send_response(404)
                self.end_headers()
    def log_message(self, *args): pass

threading.Thread(target=lambda: http.server.HTTPServer(("127.0.0.1", LOCAL_PORT), NexusHandler).serve_forever(), daemon=True).start()

# =========================================================
# APLICACIÓN PRINCIPAL v5.3 (MODO INDUSTRIAL PRO)
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v5.3"
        page.theme_mode = "dark"
        page.padding = 0 
        
        status = ft.Text("NEXUS v5.3 | Catálogo Industrial Activo", color="green")

        def open_dialog(dialog):
            try: page.open(dialog)
            except: 
                if dialog not in page.overlay: page.overlay.append(dialog)
                dialog.open = True
                page.update()

        def close_dialog(dialog):
            try: page.close(dialog)
            except: dialog.open = False; page.update()

        def copy_text(text_to_copy):
            try:
                page.set_clipboard(str(text_to_copy))
                status.value = "✓ Código copiado."
                status.color = "green"
            except:
                try:
                    subprocess.run(['termux-clipboard-set'], input=str(text_to_copy).encode('utf-8'))
                    status.value = "✓ Copiado (Termux)."
                    status.color = "green"
                except: pass
            page.update()

        # --- EDITOR JS-CSG BASE ---
        T_INICIAL = "function main() {\n  return CSG.cube({center:[0,0,10], radius:[20,20,10]});\n}"
        txt_code = ft.TextField(label="Código JS-CSG", multiline=True, expand=True, value=T_INICIAL, text_size=12)

        def load_template(t):
            txt_code.value = t
            txt_code.update() 
            set_tab(0) 
            status.value = "✓ Código inyectado."
            status.color = "green"
            status.update()

        def clear_editor():
            txt_code.value = "function main() {\n  return CSG.cube({center:[0,0,0], radius:[10,10,10]});\n}"
            txt_code.update()

        def inject_snippet(code_snippet):
            txt_code.value = txt_code.value + "\n" + code_snippet
            txt_code.update()

        row_snippets = ft.Row([
            ft.Text("Inyectar:", color="grey", size=12),
            ft.ElevatedButton("+ Cubo", on_click=lambda _: inject_snippet("  var cubo = CSG.cube({center:[0,0,0], radius:[5,5,5]});"), bgcolor="#263238", color="white"),
            ft.ElevatedButton("+ Cilindro", on_click=lambda _: inject_snippet("  var cil = CSG.cylinder({start:[0,0,0], end:[0,0,10], radius:5, slices:32});"), bgcolor="#263238", color="white"),
            ft.ElevatedButton("- Restar", on_click=lambda _: inject_snippet("  var final = pieza1.subtract(pieza2);"), bgcolor="#4e342e", color="white"),
        ], scroll="auto")

        def run_render():
            global LATEST_CODE_B64
            LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode()).decode()
            set_tab(2)
            page.update()

        # =========================================================
        # CONSTRUCTOR PARAMÉTRICO PRO (INTERFAZ BLENDER)
        # =========================================================
        def create_slider(label, min_v, max_v, val, is_int, on_change_fn):
            txt_val = ft.Text(f"{int(val) if is_int else val:.1f}", color="cyan", width=45, text_align="right", size=13)
            sl = ft.Slider(min=min_v, max=max_v, value=val, expand=True)
            if is_int: sl.divisions = int(max_v - min_v)
                
            def internal_change(e):
                txt_val.value = f"{int(sl.value) if is_int else sl.value:.1f}"
                txt_val.update()
                on_change_fn(e)
                
            sl.on_change = internal_change
            row = ft.Row([ft.Text(label, width=110, size=12, color="white"), sl, txt_val])
            return sl, row

        def generate_param_code(e=None):
            shape = param_shape_dd.value
            
            if shape == "📦 Cubo / Caja":
                g = sl_c_grosor.value
                code = f"function main() {{\n  var ext = CSG.cube({{center:[0,0,{sl_c_z.value/2}], radius:[{sl_c_x.value/2}, {sl_c_y.value/2}, {sl_c_z.value/2}]}});\n"
                if g > 0:
                    g = min(g, min(sl_c_x.value, sl_c_y.value) / 2.1)
                    code += f"  var int = CSG.cube({{center:[0,0,{sl_c_z.value/2 + g}], radius:[{sl_c_x.value/2 - g}, {sl_c_y.value/2 - g}, {sl_c_z.value/2}]}});\n  return ext.subtract(int);\n}}"
                else: code += f"  return ext;\n}}"

            elif shape == "🛢️ Revolución":
                rint = min(sl_p_rint.value, sl_p_rext.value - 0.5)
                if rint < 0: rint = 0
                c = int(sl_p_lados.value)
                code = f"function main() {{\n  var ext = CSG.cylinder({{start:[0,0,0], end:[0,0,{sl_p_h.value}], radius:{sl_p_rext.value}, slices:{c}}});\n"
                if rint > 0:
                    code += f"  var int = CSG.cylinder({{start:[0,0,-1], end:[0,0,{sl_p_h.value+2}], radius:{rint}, slices:{c}}});\n  return ext.subtract(int);\n}}"
                else: code += f"  return ext;\n}}"
                    
            elif shape == "⚙️ Engranaje":
                d, r, h, eje = int(sl_e_dientes.value), sl_e_radio.value, sl_e_grosor.value, sl_e_eje.value
                d_x, d_y = r * 0.15, r * 0.2
                code = f"function main() {{\n  var dientes = {d}; var r = {r}; var h = {h};\n  var base = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r, slices:64}});\n"
                code += f"  for(var i=0; i<dientes; i++) {{\n    var a = (i * Math.PI * 2) / dientes;\n"
                code += f"    var diente = CSG.cube({{center:[Math.cos(a)*r, Math.sin(a)*r, h/2], radius:[{d_x}, {d_y}, h/2]}});\n    base = base.union(diente);\n  }}\n"
                if eje > 0: code += f"  var hueco = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:{eje}, slices:32}});\n  return base.subtract(hueco);\n}}"
                else: code += f"  return base;\n}}"
            
            elif shape == "📐 Escuadra en L":
                l, w, t, hr = sl_l_largo.value, sl_l_ancho.value, sl_l_grosor.value, sl_l_hueco.value
                code = f"function main() {{\n  var l = {l}; var w = {w}; var t = {t}; var r = {hr};\n"
                code += f"  var base = CSG.cube({{center:[l/2, w/2, t/2], radius:[l/2, w/2, t/2]}});\n"
                code += f"  var wall = CSG.cube({{center:[t/2, w/2, l/2], radius:[t/2, w/2, l/2]}});\n"
                code += f"  var bracket = base.union(wall);\n"
                if hr > 0:
                    code += f"  var h1 = CSG.cylinder({{start:[l*0.7, w/2, -1], end:[l*0.7, w/2, t+1], radius:r, slices:32}});\n"
                    code += f"  var h2 = CSG.cylinder({{start:[-1, w/2, l*0.7], end:[t+1, w/2, l*0.7], radius:r, slices:32}});\n"
                    code += f"  bracket = bracket.subtract(h1).subtract(h2);\n"
                code += f"  return bracket;\n}}"

            elif shape == "🔩 Placa NEMA 17":
                t, tol = sl_n_grosor.value, sl_n_tol.value
                w, c_hole, m3, dist = 42.3, 11 + tol, 1.5 + tol, 15.5
                code = f"function main() {{\n  var t = {t};\n  var base = CSG.cube({{center:[0,0,t/2], radius:[{w/2}, {w/2}, t/2]}});\n"
                code += f"  var c_hole = CSG.cylinder({{start:[0,0,-1], end:[0,0,t+1], radius:{c_hole}, slices:64}});\n"
                code += f"  var h1 = CSG.cylinder({{start:[{dist}, {dist}, -1], end:[{dist}, {dist}, t+1], radius:{m3}, slices:32}});\n"
                code += f"  var h2 = CSG.cylinder({{start:[{-dist}, {dist}, -1], end:[{-dist}, {dist}, t+1], radius:{m3}, slices:32}});\n"
                code += f"  var h3 = CSG.cylinder({{start:[{dist}, {-dist}, -1], end:[{dist}, {-dist}, t+1], radius:{m3}, slices:32}});\n"
                code += f"  var h4 = CSG.cylinder({{start:[{-dist}, {-dist}, -1], end:[{-dist}, {-dist}, t+1], radius:{m3}, slices:32}});\n"
                code += f"  return base.subtract(c_hole).subtract(h1).subtract(h2).subtract(h3).subtract(h4);\n}}"

            elif shape == "🎛️ Matriz de Huecos":
                w, d, h, r = sl_m_w.value, sl_m_d.value, sl_m_h.value, sl_m_r.value
                cols, rows, sx, sy = int(sl_m_c.value), int(sl_m_fil.value), sl_m_sx.value, sl_m_sy.value
                code = f"function main() {{\n  var base = CSG.cube({{center:[0,0,{h/2}], radius:[{w/2}, {d/2}, {h/2}]}});\n"
                code += f"  var huecos = null;\n  var start_x = -(({cols}-1)*{sx})/2;\n  var start_y = -(({rows}-1)*{sy})/2;\n"
                code += f"  for(var i=0; i<{cols}; i++) {{\n    for(var j=0; j<{rows}; j++) {{\n"
                code += f"      var x = start_x + (i*{sx});\n      var y = start_y + (j*{sy});\n"
                code += f"      var cil = CSG.cylinder({{start:[x,y,-1], end:[x,y,{h+1}], radius:{r}, slices:32}});\n"
                code += f"      if(huecos === null) huecos = cil; else huecos = huecos.union(cil);\n"
                code += f"    }}\n  }}\n  if(huecos !== null) return base.subtract(huecos);\n  return base;\n}}"

            # === NUEVAS FUNCIONES v5.3 ===
            elif shape == "🛹 Soporte Rodamiento":
                diam, h, t, w = sl_r_diam.value, sl_r_h.value, sl_r_t.value, sl_r_w.value
                code = f"function main() {{\n  var w = {w}; var h = {h}; var d = {diam}; var t = {t};\n"
                code += f"  var base = CSG.cube({{center:[0,0,h/2], radius:[w/2, (d/2)+t, h/2]}});\n"
                code += f"  var b_hole = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:d/2, slices:64}});\n"
                code += f"  var s1 = CSG.cylinder({{start:[w/2 - 6, 0, -1], end:[w/2 - 6, 0, h+1], radius:2, slices:32}});\n"
                code += f"  var s2 = CSG.cylinder({{start:[-w/2 + 6, 0, -1], end:[-w/2 + 6, 0, h+1], radius:2, slices:32}});\n"
                code += f"  return base.subtract(b_hole).subtract(s1).subtract(s2);\n}}"

            elif shape == "🔗 Acople de Ejes":
                d1, d2, dext, h = sl_a_d1.value, sl_a_d2.value, sl_a_dext.value, sl_a_h.value
                code = f"function main() {{\n  var d1 = {d1}; var d2 = {d2}; var dext = {dext}; var h = {h};\n"
                code += f"  var body = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:dext/2, slices:64}});\n"
                code += f"  var h1 = CSG.cylinder({{start:[0,0,-1], end:[0,0,h/2 + 0.5], radius:d1/2, slices:32}});\n"
                code += f"  var h2 = CSG.cylinder({{start:[0,0,h/2 - 0.5], end:[0,0,h+1], radius:d2/2, slices:32}});\n"
                code += f"  var slit = CSG.cube({{center:[dext/2, 0, h/2], radius:[dext/2, 0.5, h/2 + 1]}});\n"
                code += f"  var scr1 = CSG.cylinder({{start:[0, -dext, h/4], end:[0, dext, h/4], radius:1.5, slices:16}});\n"
                code += f"  var scr2 = CSG.cylinder({{start:[0, -dext, 3*h/4], end:[0, dext, 3*h/4], radius:1.5, slices:16}});\n"
                code += f"  return body.subtract(h1).subtract(h2).subtract(slit).subtract(scr1).subtract(scr2);\n}}"

            elif shape == "🔌 Caja PCB":
                px, py, h, t = sl_pcb_x.value, sl_pcb_y.value, sl_pcb_h.value, sl_pcb_t.value
                code = f"function main() {{\n  var px = {px}; var py = {py}; var h = {h}; var t = {t};\n"
                code += f"  var ext = CSG.cube({{center:[0,0,h/2], radius:[px/2 + t + 1, py/2 + t + 1, h/2]}});\n"
                code += f"  var int = CSG.cube({{center:[0,0,h/2 + t], radius:[px/2 + 1, py/2 + 1, h/2]}});\n"
                code += f"  var box = ext.subtract(int);\n"
                code += f"  var dx = px/2 - 3; var dy = py/2 - 3;\n"
                code += f"  var m = [ [-1,-1], [-1,1], [1,-1], [1,1] ];\n"
                code += f"  for (var i=0; i<4; i++) {{\n"
                code += f"    var tor = CSG.cylinder({{start:[m[i][0]*dx, m[i][1]*dy, t], end:[m[i][0]*dx, m[i][1]*dy, t+5], radius:3.5, slices:16}});\n"
                code += f"    var hol = CSG.cylinder({{start:[m[i][0]*dx, m[i][1]*dy, t], end:[m[i][0]*dx, m[i][1]*dy, t+6], radius:1.5, slices:16}});\n"
                code += f"    box = box.union(tor).subtract(hol);\n  }}\n  return box;\n}}"

            txt_code.value = code
            txt_code.update()

        def update_constructor_ui(e=None):
            for col in [col_cubo, col_prisma, col_engranaje, col_escuadra, col_nema, col_matriz, col_rod, col_acople, col_pcb]: 
                col.visible = False
            v = param_shape_dd.value
            if v == "📦 Cubo / Caja": col_cubo.visible = True
            elif v == "🛢️ Revolución": col_prisma.visible = True
            elif v == "⚙️ Engranaje": col_engranaje.visible = True
            elif v == "📐 Escuadra en L": col_escuadra.visible = True
            elif v == "🔩 Placa NEMA 17": col_nema.visible = True
            elif v == "🎛️ Matriz de Huecos": col_matriz.visible = True
            elif v == "🛹 Soporte Rodamiento": col_rod.visible = True
            elif v == "🔗 Acople de Ejes": col_acople.visible = True
            elif v == "🔌 Caja PCB": col_pcb.visible = True
            generate_param_code()
            page.update()

        opciones_herramientas = [
            "📦 Cubo / Caja", "🛢️ Revolución", "📐 Escuadra en L", "🎛️ Matriz de Huecos",
            "⚙️ Engranaje", "🔩 Placa NEMA 17", "🛹 Soporte Rodamiento", "🔗 Acople de Ejes", "🔌 Caja PCB"
        ]

        param_shape_dd = ft.Dropdown(
            options=[ft.dropdown.Option(x) for x in opciones_herramientas],
            value="📦 Cubo / Caja", label="1. Herramienta Paramétrica", bgcolor="#212121"
        )
        param_shape_dd.on_change = update_constructor_ui

        # --- UI BLOCKS v5.2 ---
        sl_c_x, r_c_x = create_slider("Ancho X", 5, 200, 50, False, generate_param_code)
        sl_c_y, r_c_y = create_slider("Fondo Y", 5, 200, 30, False, generate_param_code)
        sl_c_z, r_c_z = create_slider("Alto Z", 5, 200, 20, False, generate_param_code)
        sl_c_grosor, r_c_g = create_slider("Grosor Pared", 0, 20, 0, False, generate_param_code)
        col_cubo = ft.Column([ft.Container(content=ft.Column([r_c_x, r_c_y, r_c_z, r_c_g]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=True)

        sl_p_rext, r_p_rext = create_slider("Radio Ext", 5, 100, 25, False, generate_param_code)
        sl_p_rint, r_p_rint = create_slider("Radio Int", 0, 95, 15, False, generate_param_code)
        sl_p_h, r_p_h = create_slider("Altura", 2, 200, 10, False, generate_param_code)
        sl_p_lados, r_p_lados = create_slider("Caras/Resol.", 3, 64, 6, True, generate_param_code)
        col_prisma = ft.Column([ft.Container(content=ft.Column([r_p_rext, r_p_rint, r_p_h, r_p_lados]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_e_dientes, r_e_d = create_slider("Dientes", 6, 40, 16, True, generate_param_code)
        sl_e_radio, r_e_r = create_slider("Radio Base", 10, 100, 30, False, generate_param_code)
        sl_e_grosor, r_e_g = create_slider("Grosor", 2, 50, 5, False, generate_param_code)
        sl_e_eje, r_e_e = create_slider("Hueco Eje", 0, 30, 5, False, generate_param_code)
        col_engranaje = ft.Column([ft.Container(content=ft.Column([r_e_d, r_e_r, r_e_g, r_e_e]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_l_largo, r_l_l = create_slider("Largo Brazos", 10, 100, 40, False, generate_param_code)
        sl_l_ancho, r_l_a = create_slider("Ancho Perfil", 5, 50, 15, False, generate_param_code)
        sl_l_grosor, r_l_g = create_slider("Grosor Chapa", 1, 20, 3, False, generate_param_code)
        sl_l_hueco, r_l_h = create_slider("Radio Agujero", 0, 10, 2, False, generate_param_code)
        col_escuadra = ft.Column([ft.Container(content=ft.Column([r_l_l, r_l_a, r_l_g, r_l_h]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_n_grosor, r_n_g = create_slider("Grosor Placa", 2, 20, 5, False, generate_param_code)
        sl_n_tol, r_n_t = create_slider("Tolerancia", 0, 2, 0.4, False, generate_param_code)
        col_nema = ft.Column([ft.Text("Genera una placa estándar NEMA 17", color="grey", size=12), ft.Container(content=ft.Column([r_n_g, r_n_t]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_m_w, r_m_w = create_slider("Ancho Base", 20, 200, 80, False, generate_param_code)
        sl_m_d, r_m_d = create_slider("Fondo Base", 20, 200, 60, False, generate_param_code)
        sl_m_h, r_m_h = create_slider("Alto Base", 1, 50, 5, False, generate_param_code)
        sl_m_r, r_m_r = create_slider("Radio Huecos", 1, 20, 3, False, generate_param_code)
        sl_m_c, r_m_c = create_slider("Nº Columnas", 1, 10, 4, True, generate_param_code)
        sl_m_fil, r_m_fil = create_slider("Nº Filas", 1, 10, 3, True, generate_param_code)
        sl_m_sx, r_m_sx = create_slider("Espaciado X", 5, 50, 15, False, generate_param_code)
        sl_m_sy, r_m_sy = create_slider("Espaciado Y", 5, 50, 15, False, generate_param_code)
        col_matriz = ft.Column([ft.Container(content=ft.Column([r_m_w, r_m_d, r_m_h, r_m_r, ft.Divider(), r_m_c, r_m_fil, r_m_sx, r_m_sy]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        # --- NUEVOS UI BLOCKS v5.3 ---
        sl_r_diam, r_r_diam = create_slider("Ø Ext. Rodam.", 10, 50, 22, False, generate_param_code) # 22mm = 608ZZ
        sl_r_h, r_r_h = create_slider("Grosor (Z)", 4, 30, 7, False, generate_param_code)
        sl_r_t, r_r_t = create_slider("Pared Borde", 1, 15, 4, False, generate_param_code)
        sl_r_w, r_r_w = create_slider("Ancho Base", 30, 150, 50, False, generate_param_code)
        col_rod = ft.Column([ft.Text("Soporte para rodamientos (Ej: 608ZZ = Ø22mm, h=7mm)", color="grey", size=12), ft.Container(content=ft.Column([r_r_diam, r_r_h, r_r_t, r_r_w]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_a_d1, r_a_d1 = create_slider("Diámetro Eje 1", 2, 20, 5, False, generate_param_code)
        sl_a_d2, r_a_d2 = create_slider("Diámetro Eje 2", 2, 20, 8, False, generate_param_code)
        sl_a_dext, r_a_dext = create_slider("Ø Exterior", 10, 50, 20, False, generate_param_code)
        sl_a_h, r_a_h = create_slider("Longitud Total", 10, 80, 25, False, generate_param_code)
        col_acople = ft.Column([ft.Text("Acople rígido con ranura tensora", color="grey", size=12), ft.Container(content=ft.Column([r_a_d1, r_a_d2, r_a_dext, r_a_h]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_pcb_x, r_pcb_x = create_slider("Largo PCB", 20, 200, 70, False, generate_param_code)
        sl_pcb_y, r_pcb_y = create_slider("Ancho PCB", 20, 200, 50, False, generate_param_code)
        sl_pcb_h, r_pcb_h = create_slider("Altura Caja", 10, 100, 20, False, generate_param_code)
        sl_pcb_t, r_pcb_t = create_slider("Grosor Pared", 1, 10, 2, False, generate_param_code)
        col_pcb = ft.Column([ft.Text("Caja con 4 torretas M3 esquineras autogeneradas", color="grey", size=12), ft.Container(content=ft.Column([r_pcb_x, r_pcb_y, r_pcb_h, r_pcb_t]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        view_constructor = ft.Column([
            ft.Text("🛠️ Constructores Industriales (Modo Blender)", weight="bold", color="amber", size=16),
            param_shape_dd,
            col_cubo, col_prisma, col_engranaje, col_escuadra, col_nema, col_matriz, col_rod, col_acople, col_pcb,
            ft.Container(height=10),
            ft.ElevatedButton("▶ PROCESAR Y VER EN 3D", on_click=lambda _: run_render(), color="black", bgcolor="amber", height=60, width=float('inf'))
        ], expand=True, scroll="auto")

        # =========================================================
        # GESTOR DE ARCHIVOS Y RUTINAS BASE
        # =========================================================
        file_list = ft.ListView(expand=True, spacing=10)

        def update_files():
            file_list.controls.clear()
            for f in reversed(sorted(os.listdir(EXPORT_DIR))):
                if f == "nexus_config.json": continue
                def make_load(name): return lambda _: load_file_content(name)
                def make_copy(name): return lambda _: export_manual(open(os.path.join(EXPORT_DIR, name), "r").read())
                def make_del(name): return lambda _: delete_file(name)

                acciones = ft.Row([
                    ft.ElevatedButton("▶ Cargar", on_click=make_load(f), color="white", bgcolor="#1b5e20"),
                    ft.ElevatedButton("📤 Exportar", on_click=make_copy(f), color="white", bgcolor="#0d47a1"),
                    ft.ElevatedButton("🗑️", on_click=make_del(f), color="white", bgcolor="#b71c1c"),
                ], scroll="auto")
                row = ft.Column([ft.Text(f, weight="bold"), acciones])
                file_list.controls.append(ft.Container(content=row, padding=10, bgcolor="#1a1a1a", border_radius=8))
            page.update()

        def load_file_content(name):
            try:
                with open(os.path.join(EXPORT_DIR, name), "r") as f: txt_code.value = f.read()
                set_tab(0) 
                status.value = f"✓ {name} cargado."
            except: pass
            page.update()

        def delete_file(name):
            os.remove(os.path.join(EXPORT_DIR, name)); update_files()

        def save_project():
            fname = f"nexus_{int(time.time())}.jscad"
            with open(os.path.join(EXPORT_DIR, fname), "w") as f: f.write(txt_code.value)
            update_files()
            status.value = f"✓ Guardado: {fname}"
            page.update()

        # =========================================================
        # VISTAS INDEPENDIENTES 
        # =========================================================
        view_editor = ft.Column([
            ft.ElevatedButton("▶ COMPILAR MALLA 3D", on_click=lambda _: run_render(), color="white", bgcolor="#004d40", height=50),
            ft.Row([
                ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save_project(), color="white", bgcolor="#0d47a1"),
                ft.ElevatedButton("🗑️ LIMPIAR", on_click=lambda _: clear_editor(), color="white", bgcolor="#b71c1c"), 
            ], scroll="auto"),
            row_snippets,
            txt_code
        ], expand=True)

        btn_visor = ft.ElevatedButton("🚀 ABRIR VISOR 3D", url="http://127.0.0.1:" + str(LOCAL_PORT) + "/", color="black", bgcolor="white", height=60)
        view_visor = ft.Column([ft.Container(height=80), ft.Row([btn_visor], alignment=ft.MainAxisAlignment.CENTER)], expand=True)
        view_archivos = ft.Column([ft.Text("Mis Proyectos", weight="bold"), file_list], expand=True)

        main_container = ft.Container(content=view_editor, expand=True)

        def set_tab(idx):
            tabs = [view_editor, view_constructor, view_visor, view_archivos]
            main_container.content = tabs[idx]
            if idx == 3: update_files()
            page.update()

        nav_bar = ft.Row([
            ft.ElevatedButton("💻 CODE", on_click=lambda _: set_tab(0)),
            ft.ElevatedButton("🛠️ BUILD", on_click=lambda _: set_tab(1), color="black", bgcolor="amber"),
            ft.ElevatedButton("👁️ 3D", on_click=lambda _: set_tab(2)),
            ft.ElevatedButton("📁 FILE", on_click=lambda _: set_tab(3)),
        ], scroll="auto")

        root_container = ft.Container(content=ft.Column([nav_bar, main_container, status], expand=True), padding=ft.padding.only(top=45, left=5, right=5, bottom=5), expand=True)
        page.add(root_container)
        
        generate_param_code()
        update_files()

    except Exception:
        page.clean()
        page.add(ft.Container(ft.Text("CRASH FATAL:\n" + traceback.format_exc(), color="red"), padding=50))
        page.update()

if __name__ == "__main__":
    if "TERMUX_VERSION" in os.environ:
        ft.app(target=main, port=0, view=ft.AppView.WEB_BROWSER)
    else:
        ft.app(target=main)