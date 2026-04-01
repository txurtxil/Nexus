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
# APLICACIÓN PRINCIPAL v7.2 (STRESS TEST EDITION)
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v7.2"
        page.theme_mode = "dark"
        page.padding = 0 
        
        status = ft.Text("NEXUS v7.2 | Prueba de Estrés Lista", color="green")

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
        T_INICIAL = "function main() {\n  // Pega aquí el código de la IA\n  var pieza = CSG.cube({center:[0,0,10], radius:[20,20,10]});\n  return pieza;\n}"
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

        # =========================================================
        # CONSTRUCTOR PARAMÉTRICO Y GALERÍA (PESTAÑA BUILD)
        # =========================================================
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
                    
            elif h == "engranaje":
                d, r, ht, eje = int(sl_e_dientes.value), sl_e_radio.value, sl_e_grosor.value, sl_e_eje.value
                d_x, d_y = r * 0.15, r * 0.2
                code = f"function main() {{\n  var dientes = {d}; var r = {r}; var h = {ht};\n  var pieza = CSG.cylinder({{start:[0,0,0], end:[0,0,h], radius:r, slices:64}});\n"
                code += f"  for(var i=0; i<dientes; i++) {{\n    var a = (i * Math.PI * 2) / dientes;\n"
                code += f"    var diente = CSG.cube({{center:[Math.cos(a)*r, Math.sin(a)*r, h/2], radius:[{d_x}, {d_y}, h/2]}});\n    pieza = pieza.union(diente);\n  }}\n"
                if eje > 0: code += f"  var hueco = CSG.cylinder({{start:[0,0,-1], end:[0,0,h+1], radius:{eje}, slices:32}});\n  pieza = pieza.subtract(hueco);\n"
                code += f"  return pieza;\n}}"
                txt_code.value = code

            elif h == "solar":
                # === EL FIX DE LA PRUEBA DE ESTRÉS (String crudo para evitar problemas de llaves) ===
                code = """function main() {
    // ==========================================
    // FUNCIÓN CORREGIDA: ESFERA NATIVA CSG
    // ==========================================
    // Intersectar 3 cilindros crea un "Sólido de Steinmetz" (cubos redondeados), no esferas.
    // Usamos la primitiva CSG nativa para mallas esféricas puras y ultra rápidas.
    function createRealSphere(x, y, z, r, slices) {
        return CSG.sphere({center: [x, y, z], radius: r, resolution: slices});
    }

    const BASE_Z = -5;
    const SURFACE_Z = 0;
    const SUN_Y = 15;
    
    function createFlatRing(x, y, z, innerR, outerR, thickness, slices) {
        let outer = CSG.cylinder({start: [x, y, z], end: [x, y + thickness, z], radius: outerR, slices: slices});
        let inner = CSG.cylinder({start: [x, y - 0.1, z], end: [x, y + thickness + 0.1, z], radius: innerR, slices: slices});
        return outer.subtract(inner);
    }

    // 1. BASE
    let base = CSG.cylinder({start: [0, BASE_Z, 0], end: [0, SURFACE_Z, 0], radius: 180, slices: 64});
    let orbitRings = new CSG();
    const orbitDistances = [26, 38, 52, 68, 92, 125, 150, 172];
    for(let i = 0; i < orbitDistances.length; i++) {
        orbitRings = orbitRings.union(createFlatRing(0, SURFACE_Z + 0.2, 0, orbitDistances[i] - 0.3, orbitDistances[i] + 0.3, 0.2, 64));
    }
    let scene = base.union(orbitRings);

    // 2. SOL
    let sunBody = createRealSphere(0, SUN_Y, 0, 16, 32);
    let sunProminences = new CSG();
    for(let i = 0; i < 24; i++) {
        let angle = (i / 24) * Math.PI * 2;
        let px = Math.cos(angle) * 17;
        let pz = Math.sin(angle) * 17;
        sunProminences = sunProminences.union(CSG.cylinder({start: [px * 0.6, SUN_Y, pz * 0.6], end: [px * 1.3, SUN_Y, pz * 1.3], radius: 1.5, slices: 12}));
    }
    scene = scene.union(sunBody).union(sunProminences);

    // 3. MERCURIO
    let mercury = createRealSphere(26, SUN_Y, 0, 2.2, 24);
    let mercSupport = CSG.cylinder({start:[26, SURFACE_Z, 0], end:[26, SUN_Y, 0], radius:1, slices:12});
    scene = scene.union(mercury).union(mercSupport);

    // 4. VENUS
    let venus = createRealSphere(38, SUN_Y, 0, 3.0, 32);
    let venSupport = CSG.cylinder({start:[38, SURFACE_Z, 0], end:[38, SUN_Y, 0], radius:1, slices:12});
    scene = scene.union(venus).union(venSupport);

    // 5. TIERRA Y LUNA
    let earth = createRealSphere(52, SUN_Y, 0, 3.0, 32);
    let moon = createRealSphere(52 + 5, SUN_Y + 2, 0, 0.8, 16);
    let earthSupport = CSG.cylinder({start:[52, SURFACE_Z, 0], end:[52, SUN_Y, 0], radius:1.2, slices:12});
    let moonArm = CSG.cylinder({start:[52, SUN_Y, 0], end:[57, SUN_Y+2, 0], radius:0.5, slices:8});
    scene = scene.union(earth).union(moon).union(earthSupport).union(moonArm);

    // 6. MARTE
    let mars = createRealSphere(68, SUN_Y, 0, 2.4, 24);
    let marsSupport = CSG.cylinder({start:[68, SURFACE_Z, 0], end:[68, SUN_Y, 0], radius:1, slices:12});
    scene = scene.union(mars).union(marsSupport);

    // 7. JÚPITER
    let jupBody = createRealSphere(92, SUN_Y, 0, 9.5, 32);
    let jupSupport = CSG.cylinder({start:[92, SURFACE_Z, 0], end:[92, SUN_Y-5, 0], radius:3, slices:24});
    scene = scene.union(jupBody).union(jupSupport);

    // 8. SATURNO
    let satY = SUN_Y + 3;
    let saturn = createRealSphere(125, satY, 0, 7.5, 32);
    let rings = createFlatRing(125, satY, 0, 9.5, 16.5, 0.3, 64);
    let satSupport = CSG.cylinder({start:[125, SURFACE_Z, 0], end:[125, satY-4, 0], radius:2.5, slices:24});
    scene = scene.union(saturn).union(rings).union(satSupport);

    // 9. URANO
    let uranus = createRealSphere(150, SUN_Y, 0, 5.2, 24);
    let uraSupport = CSG.cylinder({start:[150, SURFACE_Z, 0], end:[150, SUN_Y, 0], radius:2, slices:20});
    scene = scene.union(uranus).union(uraSupport);

    // 10. NEPTUNO
    let neptune = createRealSphere(172, SUN_Y, 0, 5.0, 24);
    let nepSupport = CSG.cylinder({start:[172, SURFACE_Z, 0], end:[172, SUN_Y, 0], radius:2, slices:20});
    scene = scene.union(neptune).union(nepSupport);

    return scene;
}"""
                txt_code.value = code

            txt_code.update()

        def update_constructor_ui(e=None):
            for col in [col_custom, col_cubo, col_cilindro, col_engranaje, col_escuadra, col_solar]: 
                col.visible = False
            v = herramienta_actual
            if v == "custom": col_custom.visible = True
            elif v == "cubo": col_cubo.visible = True
            elif v == "cilindro": col_cilindro.visible = True
            elif v == "engranaje": col_engranaje.visible = True
            elif v == "escuadra": col_escuadra.visible = True
            elif v == "solar": col_solar.visible = True
            generate_param_code()
            page.update()

        # UI Blocks
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

        # NUEVA COLUMNA PARA SISTEMA SOLAR
        col_solar = ft.Column([
            ft.Text("🪐 Prueba de Rendimiento (Corregida)", color="amber", weight="bold"),
            ft.Text("Algoritmo de Intersección de Cilindros reemplazado por Esferas CSG Nativas.", color="grey", size=12),
            ft.Text("Se generarán mallas esféricas perfectas y lisas reduciendo drásticamente el coste de polígonos.", color="cyan", size=11)
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
            create_thumbnail("🪐", "Sist. Solar", "solar", "#d84315"), # BOTÓN DEL SISTEMA SOLAR
            create_thumbnail("📦", "Caja", "cubo", "#37474f"),
            create_thumbnail("⚙️", "Piñón", "engranaje", "#ff6f00"),
            create_thumbnail("🛢️", "Tubo", "cilindro", "#37474f"),
            create_thumbnail("📐", "Escuadra", "escuadra", "#bf360c"),
        ], scroll="auto")

        view_constructor = ft.Column([
            ft.Text("1. Galería y Constructores:", weight="bold", color="amber"),
            row_miniaturas,
            ft.Divider(),
            col_custom, col_solar, col_cubo, col_cilindro, col_engranaje, col_escuadra,
            ft.Container(height=10),
            ft.ElevatedButton("▶ GENERAR CÓDIGO", on_click=lambda _: set_tab(0), color="white", bgcolor="#0d47a1", height=50, width=float('inf'))
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

        btn_visor = ft.ElevatedButton("🔄 FORZAR RECARGA WEBGL", url="http://127.0.0.1:" + str(LOCAL_PORT) + "/", color="black", bgcolor="amber", height=60, width=300)
        view_visor = ft.Column([
            ft.Container(height=40), 
            ft.Text("Visualizador 3D Compilado", text_align="center", color="cyan", weight="bold"),
            ft.Row([btn_visor], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=20),
            ft.Text("📦 Usa el visor Web para exportar STL.", color="grey", text_align="center", size=12)
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