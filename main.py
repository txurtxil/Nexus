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
# APLICACIÓN PRINCIPAL v9.0 (POWER TRANSMISSION)
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v9.0"
        page.theme_mode = "dark"
        page.padding = 0 
        
        status = ft.Text("NEXUS v9.0 | Transmisión de Potencia Activa", color="green")

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

        T_INICIAL = "function main() {\n  var pieza = CSG.cube({center:[0,0,10], radius:[20,20,10]});\n  return pieza;\n}"
        txt_code = ft.TextField(label="Código Fuente (JS-CSG)", multiline=True, expand=True, value=T_INICIAL)

        def clear_editor():
            txt_code.value = "function main() {\n  var pieza = CSG.cube({center:[0,0,0], radius:[10,10,10]});\n  return pieza;\n}"
            txt_code.update()

        def inject_snippet(code_snippet):
            c = txt_code.value
            pos = c.rfind('return ')
            if pos != -1:
                txt_code.value = c[:pos] + code_snippet + "\n  " + c[pos:]
            else:
                txt_code.value = c + "\n" + code_snippet
            txt_code.update()

        def run_render():
            global LATEST_CODE_B64
            LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode()).decode()
            set_tab(2)
            page.update()

        row_snippets = ft.Row([
            ft.Text("Primitivas:", color="grey", size=12),
            ft.ElevatedButton("+ Cubo", on_click=lambda _: inject_snippet("  var cubo = CSG.cube({center:[0,0,0], radius:[5,5,5]});")),
            ft.ElevatedButton("+ Cilindro", on_click=lambda _: inject_snippet("  var cil = CSG.cylinder({start:[0,0,0], end:[0,0,10], radius:5, slices:32});")),
            ft.ElevatedButton("- Restar", on_click=lambda _: inject_snippet("  pieza = pieza.subtract(pieza2);")),
        ], scroll="auto")

        herramienta_actual = "custom"

        def create_slider(label, min_v, max_v, val, is_int, on_change_fn):
            txt_val = ft.Text(f"{int(val) if is_int else val:.1f}", color="cyan", width=45, text_align="right", size=13)
            sl = ft.Slider(min=min_v, max=max_v, value=val, expand=True)
            if is_int: sl.divisions = int(max_v - min_v)
            def internal_change(e):
                txt_val.value = f"{int(sl.value) if is_int else sl.value:.1f}"
                txt_val.update()
                on_change_fn(e)
            sl.on_change = internal_change
            return sl, ft.Row([ft.Text(label, width=110, size=12, color="white"), sl, txt_val])

        def generate_param_code(e=None):
            h = herramienta_actual
            
            if h == "custom":
                pass 

            elif h == "cubo":
                g = sl_c_grosor.value
                code = f"function main() {{\n  var pieza = CSG.cube({{center:[0,0,{sl_c_z.value/2}], radius:[{sl_c_x.value/2}, {sl_c_y.value/2}, {sl_c_z.value/2}]}});\n"
                if g > 0:
                    g = min(g, min(sl_c_x.value, sl_c_y.value) / 2.1)
                    code += f"  var int = CSG.cube({{center:[0,0,{sl_c_z.value/2 + g}], radius:[{sl_c_x.value/2 - g}, {sl_c_y.value/2 - g}, {sl_c_z.value/2}]}});\n  pieza = pieza.subtract(int);\n"
                code += f"  return pieza;\n}}"
                txt_code.value = code

            elif h == "cilindro":
                rint = min(sl_p_rint.value, sl_p_rext.value - 0.5)
                c = int(sl_p_lados.value)
                code = f"function main() {{\n  var pieza = CSG.cylinder({{start:[0,0,0], end:[0,0,{sl_p_h.value}], radius:{sl_p_rext.value}, slices:{c}}});\n"
                if rint > 0:
                    code += f"  var int = CSG.cylinder({{start:[0,0,-1], end:[0,0,{sl_p_h.value+2}], radius:{rint}, slices:{c}}});\n  pieza = pieza.subtract(int);\n"
                code += f"  return pieza;\n}}"
                txt_code.value = code
            
            elif h == "escuadra":
                l, w, t, hr = sl_l_largo.value, sl_l_ancho.value, sl_l_grosor.value, sl_l_hueco.value
                code = f"function main() {{\n  var l = {l}; var w = {w}; var t = {t}; var r = {hr};\n"
                code += f"  var base = CSG.cube({{center:[l/2, w/2, t/2], radius:[l/2, w/2, t/2]}});\n"
                code += f"  var wall = CSG.cube({{center:[t/2, w/2, l/2], radius:[t/2, w/2, l/2]}});\n  var pieza = base.union(wall);\n"
                if hr > 0:
                    code += f"  var h1 = CSG.cylinder({{start:[l*0.7, w/2, -1], end:[l*0.7, w/2, t+1], radius:r, slices:32}});\n"
                    code += f"  var h2 = CSG.cylinder({{start:[-1, w/2, l*0.7], end:[t+1, w/2, l*0.7], radius:r, slices:32}});\n"
                    code += f"  pieza = pieza.subtract(h1).subtract(h2);\n"
                code += f"  return pieza;\n}}"
                txt_code.value = code

            elif h == "fijacion":
                m, l_tornillo, tol = sl_fij_m.value, sl_fij_l.value, sl_fij_tol.value
                r_hex = (m * 1.8) / 2
                h_cabeza = m * 0.8
                r_eje = m / 2
                
                if l_tornillo == 0:
                    code = f"function main() {{\n  var m = {m}; var h = {h_cabeza};\n"
                    code += f"  var cuerpo = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:{r_hex}, slices:6}});\n"
                    code += f"  var agujero = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:{r_eje + tol}, slices:32}});\n"
                    code += f"  return cuerpo.subtract(agujero);\n}}"
                else:
                    code = f"function main() {{\n"
                    code += f"  var m = {m}; var l_tornillo = {l_tornillo}; var r_eje = {r_eje - tol};\n"
                    code += f"  var h_cabeza = {h_cabeza}; var r_hex = {r_hex};\n"
                    code += f"  var cabeza = CSG.cylinder({{start:[0,0,0], end:[0,0,h_cabeza], radius:r_hex, slices:6}});\n"
                    code += f"  var eje = CSG.cylinder({{start:[0,0,h_cabeza - 0.1], end:[0,0,h_cabeza + l_tornillo], radius:r_eje - (m*0.08), slices:32}});\n"
                    code += f"  var pieza = cabeza.union(eje);\n"
                    code += f"  var paso = m * 0.15;\n"
                    code += f"  for(var z = h_cabeza + 1; z < h_cabeza + l_tornillo - 1; z += paso*1.5) {{\n"
                    code += f"      var anillo = CSG.cylinder({{start:[0,0,z], end:[0,0,z+paso], radius:r_eje, slices:16}});\n"
                    code += f"      pieza = pieza.union(anillo);\n"
                    code += f"  }}\n"
                    code += f"  return pieza;\n}}"
                txt_code.value = code

            elif h == "rodamiento":
                d_int, d_ext, ht = sl_rod_dint.value, sl_rod_dext.value, sl_rod_h.value
                code = f"function main() {{\n  var d_int = {d_int}; var d_ext = {d_ext}; var h = {ht};\n"
                code += f"  var pista_ext = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:d_ext/2, slices:64}})\n"
                code += f"       .subtract( CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:(d_ext/2)-2, slices:64}}) );\n"
                code += f"  var pista_int = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:(d_int/2)+2, slices:64}})\n"
                code += f"       .subtract( CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:d_int/2, slices:64}}) );\n"
                code += f"  var pieza = pista_ext.union(pista_int);\n\n"
                code += f"  var r_espacio = (((d_ext/2)-2) - ((d_int/2)+2)) / 2;\n"
                code += f"  var radio_centro = ((d_int/2)+2 + (d_ext/2)-2)/2;\n"
                code += f"  var n_bolas = Math.floor((Math.PI * 2 * radio_centro) / (r_espacio * 2.2));\n"
                code += f"  for(var i=0; i<n_bolas; i++) {{\n"
                code += f"      var a = (i * Math.PI * 2) / n_bolas;\n"
                code += f"      var bx = Math.cos(a) * radio_centro;\n"
                code += f"      var by = Math.sin(a) * radio_centro;\n"
                code += f"      var bola = CSG.sphere({{center:[bx, by, h/2], radius:r_espacio*0.95, resolution:16}});\n"
                code += f"      pieza = pieza.union(bola);\n"
                code += f"  }}\n"
                code += f"  return pieza;\n}}"
                txt_code.value = code

            elif h == "helice":
                rad, n_aspas, pitch = sl_hel_r.value, int(sl_hel_n.value), sl_hel_p.value
                code = f"function main() {{\n  var rad = {rad}; var n = {n_aspas}; var pitch = {pitch};\n"
                code += f"  var hub = CSG.cylinder({{start:[0,0,0], end:[0,0,10], radius:8, slices:32}});\n"
                code += f"  var agujero = CSG.cylinder({{start:[0,0,-1], end:[0,0,11], radius:2.5, slices:16}});\n"
                code += f"  var aspas = new CSG();\n"
                code += f"  for(var i=0; i<n; i++) {{\n    var a = (i * Math.PI * 2) / n;\n"
                code += f"    var dx = Math.cos(a); var dy = Math.sin(a);\n"
                code += f"    var aspa = CSG.cylinder({{\n"
                code += f"        start: [6*dx, 6*dy, 5 - (pitch/10)],\n"
                code += f"        end: [rad*dx, rad*dy, 5 + (pitch/10)],\n"
                code += f"        radius: 3, slices: 4\n"
                code += f"    }});\n"
                code += f"    aspas = aspas.union(aspa);\n  }}\n"
                code += f"  var pieza = hub.union(aspas).subtract(agujero);\n  return pieza;\n}}"
                txt_code.value = code

            # ==========================================
            # v9.0 MÓDULO: ENGRANAJE PLANETARIO
            # ==========================================
            elif h == "planetario":
                r_sol, r_planeta, ht = sl_plan_rs.value, sl_plan_rp.value, sl_plan_h.value
                code = f"function main() {{\n"
                code += f"  var r_sol = {r_sol}; var r_planeta = {r_planeta}; var h = {ht};\n"
                code += f"  var tol = 0.5; // Tolerancia cinemática para engranar\n"
                code += f"  var r_anillo = r_sol + (r_planeta*2);\n"
                code += f"  var dist_centros = r_sol + r_planeta;\n"
                code += f"  // 1. SOL CENTRAL (Dientes Cicloidales / Pin-Gear)\n"
                code += f"  var sol = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r_sol - 1, slices:32}});\n"
                code += f"  var dientes_sol = Math.floor(r_sol * 1.5);\n"
                code += f"  for(var i=0; i<dientes_sol; i++) {{\n"
                code += f"      var a = (i * Math.PI * 2) / dientes_sol;\n"
                code += f"      var diente = CSG.cylinder({{start:[Math.cos(a)*r_sol, Math.sin(a)*r_sol, 0], end:[Math.cos(a)*r_sol, Math.sin(a)*r_sol, h], radius:1.2, slices:12}});\n"
                code += f"      sol = sol.union(diente);\n"
                code += f"  }}\n"
                code += f"  sol = sol.subtract(CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:3, slices:16}}));\n\n"
                code += f"  // 2. TRES PLANETAS\n"
                code += f"  var planetas = new CSG();\n"
                code += f"  var dientes_planeta = Math.floor(r_planeta * 1.5);\n"
                code += f"  for(var p=0; p<3; p++) {{\n"
                code += f"      var ap = (p * Math.PI * 2) / 3;\n"
                code += f"      var cx = Math.cos(ap) * dist_centros; var cy = Math.sin(ap) * dist_centros;\n"
                code += f"      var planeta = CSG.cylinder({{start:[cx, cy, 0], end:[cx, cy, h], radius:r_planeta - 1 - tol, slices:32}});\n"
                code += f"      for(var i=0; i<dientes_planeta; i++) {{\n"
                code += f"          var a = (i * Math.PI * 2) / dientes_planeta;\n"
                code += f"          var px = cx + Math.cos(a)*(r_planeta - tol);\n"
                code += f"          var py = cy + Math.sin(a)*(r_planeta - tol);\n"
                code += f"          var diente = CSG.cylinder({{start:[px, py, 0], end:[px, py, h], radius:1.2 - (tol/2), slices:12}});\n"
                code += f"          planeta = planeta.union(diente);\n"
                code += f"      }}\n"
                code += f"      planeta = planeta.subtract(CSG.cylinder({{start:[cx, cy, -1], end:[cx, cy, h+1], radius:2, slices:12}}));\n"
                code += f"      planetas = planetas.union(planeta);\n"
                code += f"  }}\n\n"
                code += f"  // 3. CORONA EXTERIOR (Ring Gear)\n"
                code += f"  var corona = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r_anillo + 5, slices:64}});\n"
                code += f"  var hueco = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:r_anillo + tol, slices:64}});\n"
                code += f"  corona = corona.subtract(hueco);\n"
                code += f"  var dientes_corona = Math.floor(r_anillo * 1.5);\n"
                code += f"  var anillo_dientes = new CSG();\n"
                code += f"  for(var i=0; i<dientes_corona; i++) {{\n"
                code += f"      var a = (i * Math.PI * 2) / dientes_corona;\n"
                code += f"      var diente = CSG.cylinder({{start:[Math.cos(a)*(r_anillo + tol), Math.sin(a)*(r_anillo + tol), 0], end:[Math.cos(a)*(r_anillo + tol), Math.sin(a)*(r_anillo + tol), h], radius:1.2, slices:12}});\n"
                code += f"      anillo_dientes = anillo_dientes.union(diente);\n"
                code += f"  }}\n"
                code += f"  corona = corona.union(anillo_dientes);\n\n"
                code += f"  return sol.union(planetas).union(corona);\n}}"
                txt_code.value = code

            # ==========================================
            # v9.0 MÓDULO: POLEA GT2 (TIMING PULLEY)
            # ==========================================
            elif h == "polea":
                dientes, ancho, d_eje = int(sl_pol_t.value), sl_pol_w.value, sl_pol_d.value
                code = f"function main() {{\n"
                code += f"  var dientes = {dientes}; var ancho = {ancho}; var r_eje = {d_eje/2};\n"
                code += f"  var pitch = 2; // Estándar correa GT2 (2mm pitch)\n"
                code += f"  var r_primitivo = (dientes * pitch) / (2 * Math.PI);\n"
                code += f"  var r_ext = r_primitivo - 0.25;\n\n"
                code += f"  // Cuerpo dentado por sustracción\n"
                code += f"  var cuerpo = CSG.cylinder({{start:[0,0,1.5], end:[0,0,1.5+ancho], radius:r_ext, slices:64}});\n"
                code += f"  var matriz_dientes = new CSG();\n"
                code += f"  for(var i=0; i<dientes; i++) {{\n"
                code += f"      var a = (i * Math.PI * 2) / dientes;\n"
                code += f"      var d = CSG.cylinder({{start:[Math.cos(a)*r_ext, Math.sin(a)*r_ext, 1], end:[Math.cos(a)*r_ext, Math.sin(a)*r_ext, 2+ancho], radius:0.55, slices:8}});\n"
                code += f"      matriz_dientes = matriz_dientes.union(d);\n"
                code += f"  }}\n"
                code += f"  cuerpo = cuerpo.subtract(matriz_dientes);\n\n"
                code += f"  // Pestañas (Flanges) para que la correa no se salga\n"
                code += f"  var base = CSG.cylinder({{start:[0,0,0], end:[0,0,1.5], radius:r_ext + 1, slices:64}});\n"
                code += f"  var tapa = CSG.cylinder({{start:[0,0,1.5+ancho], end:[0,0,3+ancho], radius:r_ext + 1, slices:64}});\n"
                code += f"  var polea = base.union(cuerpo).union(tapa);\n\n"
                code += f"  // Taladro central\n"
                code += f"  polea = polea.subtract(CSG.cylinder({{start:[0,0,-1], end:[0,0,5+ancho], radius:r_eje, slices:32}}));\n"
                code += f"  return polea;\n}}"
                txt_code.value = code

            txt_code.update()

        def update_constructor_ui(e=None):
            for col in [col_custom, col_cubo, col_cilindro, col_escuadra, col_fijacion, col_rodamiento, col_planetario, col_polea, col_helice]: 
                col.visible = False
            v = herramienta_actual
            if v == "custom": col_custom.visible = True
            elif v == "cubo": col_cubo.visible = True
            elif v == "cilindro": col_cilindro.visible = True
            elif v == "escuadra": col_escuadra.visible = True
            elif v == "fijacion": col_fijacion.visible = True
            elif v == "rodamiento": col_rodamiento.visible = True
            elif v == "planetario": col_planetario.visible = True
            elif v == "polea": col_polea.visible = True
            elif v == "helice": col_helice.visible = True
            generate_param_code()
            page.update()

        # UI Blocks Base
        col_custom = ft.Column([
            ft.Text("Módulo Activo: Tu Código de IA", color="green", weight="bold"),
            ft.Row([
                ft.ElevatedButton("🕳️ Vaciado", on_click=lambda _: inject_snippet("  var vaciado = pieza.scale([0.9, 0.9, 0.9]);\n  pieza = pieza.subtract(vaciado);"), bgcolor="#4e342e", color="white"),
                ft.ElevatedButton("🔄 Redondeo", on_click=lambda _: inject_snippet("  pieza = pieza.expand(2, 16);"), bgcolor="#1b5e20", color="white"),
            ], scroll="auto")
        ], visible=True)

        sl_c_x, r_c_x = create_slider("Ancho X", 5, 200, 50, False, generate_param_code)
        sl_c_y, r_c_y = create_slider("Fondo Y", 5, 200, 30, False, generate_param_code)
        sl_c_z, r_c_z = create_slider("Alto Z", 5, 200, 20, False, generate_param_code)
        sl_c_grosor, r_c_g = create_slider("Grosor Pared", 0, 20, 0, False, generate_param_code)
        col_cubo = ft.Column([ft.Container(content=ft.Column([r_c_x, r_c_y, r_c_z, r_c_g]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_p_rext, r_p_rext = create_slider("Radio Ext", 5, 100, 25, False, generate_param_code)
        sl_p_rint, r_p_rint = create_slider("Radio Int", 0, 95, 15, False, generate_param_code)
        sl_p_h, r_p_h = create_slider("Altura", 2, 200, 10, False, generate_param_code)
        sl_p_lados, r_p_lados = create_slider("Caras/Resol.", 3, 64, 64, True, generate_param_code)
        col_cilindro = ft.Column([ft.Container(content=ft.Column([r_p_rext, r_p_rint, r_p_h, r_p_lados]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_l_largo, r_l_l = create_slider("Largo Brazos", 10, 100, 40, False, generate_param_code)
        sl_l_ancho, r_l_a = create_slider("Ancho Perfil", 5, 50, 15, False, generate_param_code)
        sl_l_grosor, r_l_g = create_slider("Grosor Chapa", 1, 20, 3, False, generate_param_code)
        sl_l_hueco, r_l_h = create_slider("Radio Agujero", 0, 10, 2, False, generate_param_code)
        col_escuadra = ft.Column([ft.Container(content=ft.Column([r_l_l, r_l_a, r_l_g, r_l_h]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_fij_m, r_fij_m = create_slider("Métrica (M)", 3, 20, 8, True, generate_param_code)
        sl_fij_l, r_fij_l = create_slider("Largo Tornillo", 0, 100, 30, False, generate_param_code)
        sl_fij_tol, r_fij_tol = create_slider("Tolerancia", 0, 1.0, 0.2, False, generate_param_code)
        col_fijacion = ft.Column([ft.Container(content=ft.Column([r_fij_m, r_fij_l, r_fij_tol]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_rod_dint, r_rod_dint = create_slider("Ø Eje Interno", 3, 50, 8, False, generate_param_code)
        sl_rod_dext, r_rod_dext = create_slider("Ø Externo", 10, 100, 22, False, generate_param_code)
        sl_rod_h, r_rod_h = create_slider("Altura (mm)", 3, 30, 7, False, generate_param_code)
        col_rodamiento = ft.Column([ft.Container(content=ft.Column([r_rod_dint, r_rod_dext, r_rod_h]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        sl_hel_r, r_hel_r = create_slider("Radio Total", 20, 150, 50, False, generate_param_code)
        sl_hel_n, r_hel_n = create_slider("Nº Aspas", 2, 12, 4, True, generate_param_code)
        sl_hel_p, r_hel_p = create_slider("Torsión", 10, 80, 45, False, generate_param_code)
        col_helice = ft.Column([ft.Container(content=ft.Column([r_hel_r, r_hel_n, r_hel_p]), bgcolor="#1e1e1e", padding=10, border_radius=8)], visible=False)

        # MÓDULOS v9.0
        sl_plan_rs, r_plan_rs = create_slider("Radio Sol", 5, 40, 10, False, generate_param_code)
        sl_plan_rp, r_plan_rp = create_slider("Radio Planetas", 4, 30, 8, False, generate_param_code)
        sl_plan_h, r_plan_h = create_slider("Grosor Total", 3, 30, 6, False, generate_param_code)
        col_planetario = ft.Column([
            ft.Text("Mecanismo Planetario complejo. Dentado cicloidal de pasadores calculado matricialmente.", color="amber", size=12),
            ft.Container(content=ft.Column([r_plan_rs, r_plan_rp, r_plan_h]), bgcolor="#1e1e1e", padding=10, border_radius=8)
        ], visible=False)

        sl_pol_t, r_pol_t = create_slider("Nº Dientes", 10, 60, 20, True, generate_param_code)
        sl_pol_w, r_pol_w = create_slider("Ancho Correa", 4, 20, 6, False, generate_param_code)
        sl_pol_d, r_pol_d = create_slider("Ø Eje Motor", 2, 12, 5, False, generate_param_code)
        col_polea = ft.Column([
            ft.Text("Polea dentada GT2 estándar. Resta matricial del perfil de dientes en el contorno exterior.", color="cyan", size=12),
            ft.Container(content=ft.Column([r_pol_t, r_pol_w, r_pol_d]), bgcolor="#1e1e1e", padding=10, border_radius=8)
        ], visible=False)


        # CARRUSEL
        def select_tool(nombre_herramienta):
            nonlocal herramienta_actual
            herramienta_actual = nombre_herramienta
            update_constructor_ui()

        def create_thumbnail(icon, title, tool_id, color):
            return ft.Container(
                content=ft.Column([
                    ft.Text(icon, size=30), 
                    ft.Text(title, size=10, color="white", weight="bold")
                ]),
                width=80, height=80, bgcolor=color, border_radius=8, padding=10,
                on_click=lambda _: select_tool(tool_id)
            )

        row_miniaturas = ft.Row([
            create_thumbnail("🧠", "Mi Código", "custom", "#000000"),
            create_thumbnail("⚙️", "Planetario", "planetario", "#e65100"), # v9.0
            create_thumbnail("🛼", "Polea GT2", "polea", "#0277bd"), # v9.0
            create_thumbnail("🔩", "Tornillería", "fijacion", "#c62828"),
            create_thumbnail("🛞", "Rodamiento", "rodamiento", "#5d4037"), 
            create_thumbnail("🚁", "Hélice", "helice", "#00838f"), 
            create_thumbnail("📦", "Caja", "cubo", "#37474f"),
            create_thumbnail("🛢️", "Tubo", "cilindro", "#37474f"),
            create_thumbnail("📐", "Escuadra", "escuadra", "#bf360c"),
        ], scroll="auto")

        view_constructor = ft.Column([
            ft.Text("1. Galería Cinemática:", weight="bold", color="amber"),
            row_miniaturas,
            ft.Divider(),
            col_custom, col_planetario, col_polea, col_fijacion, col_rodamiento, col_helice, col_cubo, col_cilindro, col_escuadra,
            ft.Container(height=10),
            ft.ElevatedButton("▶ ACTUALIZAR MALLA (3D)", on_click=lambda _: run_render(), color="black", bgcolor="amber", height=60, width=float('inf'))
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

        view_editor = ft.Column([
            ft.Row([
                ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save_project(), color="white", bgcolor="#0d47a1"),
                ft.ElevatedButton("🗑️ RESET", on_click=lambda _: clear_editor(), color="white", bgcolor="#b71c1c"), 
            ], scroll="auto"),
            row_snippets,
            txt_code
        ], expand=True)

        btn_visor = ft.ElevatedButton("🔄 RECARGAR VISOR 3D", url="http://127.0.0.1:" + str(LOCAL_PORT) + "/", color="black", bgcolor="amber", height=60, width=300)
        view_visor = ft.Column([
            ft.Container(height=40), 
            ft.Text("Visualizador 3D Compilado", text_align="center", color="cyan", weight="bold"),
            ft.Row([btn_visor], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=20),
            ft.Text("📦 Usa el botón del visor Web para exportar a STL.", color="grey", text_align="center", size=12)
        ], expand=True)
        
        view_archivos = ft.Column([ft.Text("Mis Archivos", weight="bold"), file_list], expand=True)

        main_container = ft.Container(content=view_editor, expand=True)

        def set_tab(idx):
            tabs = [view_editor, view_constructor, view_visor, view_archivos]
            if idx == 2:
                global LATEST_CODE_B64
                LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode()).decode()
            if idx == 3: update_files()
            main_container.content = tabs[idx]
            page.update()

        nav_bar = ft.Row([
            ft.ElevatedButton("💻 CODE", on_click=lambda _: set_tab(0)),
            ft.ElevatedButton("🛠️ BUILD", on_click=lambda _: set_tab(1), color="black", bgcolor="amber"),
            ft.ElevatedButton("👁️ 3D", on_click=lambda _: set_tab(2), color="white", bgcolor="#004d40"),
            ft.ElevatedButton("📁 FILES", on_click=lambda _: set_tab(3)),
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