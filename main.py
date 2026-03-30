import flet as ft
import os, base64, traceback, sqlite3, warnings, json
import urllib.request
import http.server
import threading
import socket
import time
from urllib.parse import urlparse

warnings.simplefilter("ignore", DeprecationWarning)

# =========================================================
# GESTOR OFFLINE (Descarga librerías JS locales)
# =========================================================
assets_dir = os.path.join(os.getcwd(), "assets")
os.makedirs(assets_dir, exist_ok=True)
libs = {
    "three.min.js": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
    "csg.js": "https://raw.githubusercontent.com/evanw/csg.js/master/csg.js"
}
for name, url in libs.items():
    path = os.path.join(assets_dir, name)
    if not os.path.exists(path):
        try: urllib.request.urlretrieve(url, path)
        except: pass

# =========================================================
# MOTOR API LOCAL HTTP
# =========================================================
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); LOCAL_PORT = s.getsockname()[1]
except: LOCAL_PORT = 8556

LATEST_CODE_B64 = ""

class NexusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global LATEST_CODE_B64
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/get_code_b64.json':
            self.send_response(200); self.send_header("Content-type", "application/json"); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
            self.wfile.write(json.dumps({"code_b64": LATEST_CODE_B64}).encode('utf-8'))
        elif self.path == '/three.min.js' or self.path == '/csg.js':
            try:
                with open(os.path.join(assets_dir, self.path.replace('/', '')), "r", encoding="utf-8") as f:
                    self.send_response(200); self.send_header("Content-type", "application/javascript"); self.end_headers(); self.wfile.write(f.read().encode('utf-8'))
            except: self.send_response(404); self.end_headers()
        else:
            try:
                with open(os.path.join(assets_dir, "openscad_engine.html"), "r", encoding="utf-8") as f:
                    self.send_response(200); self.send_header("Content-type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(f.read().encode('utf-8'))
            except: self.send_response(500); self.end_headers()
    def log_message(self, format, *args): pass 

threading.Thread(target=lambda: http.server.HTTPServer(("127.0.0.1", LOCAL_PORT), NexusHandler).serve_forever(), daemon=True).start()

def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v2.0 (Core Edition)"
        page.theme_mode = "dark"
        page.bgcolor = "#0a0a0a"
        page.padding = 0
        
        export_dir = os.path.join(os.environ.get("HOME", os.getcwd()), "nexus_proyectos")
        os.makedirs(export_dir, exist_ok=True)

        status_text = ft.Text("Sistema Online - v2.0 Core", color="grey600", size=11)

        # =========================================================
        # PLANTILLAS JS-CSG
        # =========================================================
        code_gear = """function main() {
    var base = CSG.cylinder({start: [0,-2,0], end: [0,2,0], radius: 15, slices: 32});
    var hole = CSG.cylinder({start: [0,-3,0], end: [0,3,0], radius: 5, slices: 16});
    var gear = base.subtract(hole);
    for(var i=0; i<8; i++) {
        var a = (i * 45) * Math.PI / 180;
        var tooth = CSG.cube({center: [Math.cos(a)*15, 0, Math.sin(a)*15], radius: [2, 2, 2]});
        gear = gear.union(tooth);
    }
    return gear;
}"""

        code_box = """function main() {
    var exterior = CSG.cube({center: [0,0,0], radius: [20, 10, 15]});
    var interior = CSG.cube({center: [0,2,0], radius: [18, 10, 13]}); 
    return exterior.subtract(interior);
}"""

        code_stand = """function main() {
    var base = CSG.cube({center: [0, 0, 20], radius: [60, 40, 20]});
    var ranura = CSG.cube({center: [0, 5, 35], radius: [70, 15, 30]});
    var rebaje_frontal = CSG.cube({center: [0, -45, 45], radius: [70, 40, 30]});
    var ventilacion = CSG.cylinder({start: [0, -50, 15], end: [0, 50, 15], radius: 20, slices: 32});
    var peana_final = base.subtract(ranura).subtract(rebaje_frontal).subtract(ventilacion);
    var tope_frontal = CSG.cube({center: [0, -32, 5], radius: [60, 3, 5]});
    return peana_final.union(tope_frontal);
}"""

        # =========================================================
        # 1. UI EDITOR
        # =========================================================
        txt_code = ft.TextField(
            label="Código JSCAD (Booleano)", multiline=True, expand=True, 
            value=code_stand, color="#00ff00", bgcolor="#050505", border_color="#333333", text_size=12
        )

        def save_project():
            filename = f"nexus_{int(time.time())}.jscad"
            filepath = os.path.join(export_dir, filename)
            with open(filepath, "w") as f: f.write(txt_code.value)
            status_text.value = f"✓ Guardado: {filename}"; update_explorer(); page.update()

        def clear_code(): txt_code.value = "function main() {\n  return CSG.sphere({radius: 10});\n}"; page.update()
        def load_template(code): txt_code.value = code; page.update()

        row_actions = ft.Row([
            ft.ElevatedButton("⚙️", on_click=lambda _: load_template(code_gear), bgcolor="#222222", color="white", tooltip="Engranaje"),
            ft.ElevatedButton("📦", on_click=lambda _: load_template(code_box), bgcolor="#222222", color="white", tooltip="Caja"),
            ft.ElevatedButton("📱", on_click=lambda _: load_template(code_stand), bgcolor="#222222", color="white", tooltip="Peana Consola"),
            ft.ElevatedButton("💾 Guardar", on_click=lambda _: save_project(), bgcolor="#8e24aa", color="white"),
            ft.ElevatedButton("🗑️", on_click=lambda _: clear_code(), bgcolor="#e53935", color="white"),
        ], scroll=ft.ScrollMode.AUTO)
        
        btn_compile = ft.ElevatedButton("▶ COMPILAR MALLA BOOLEANA", on_click=lambda e: run_render(), bgcolor="green900", color="white", height=50, width=float('inf'))

        editor_container = ft.Container(
            content=ft.Column([
                btn_compile,
                row_actions,
                txt_code
            ], expand=True), 
            padding=10, expand=True, bgcolor="#0a0a0a", visible=True
        )

        # =========================================================
        # 2. UI EXPLORADOR DE ARCHIVOS PRO
        # =========================================================
        lv_files = ft.ListView(expand=True, spacing=5)
        
        def load_file(filename):
            with open(os.path.join(export_dir, filename), "r") as f: txt_code.value = f.read()
            status_text.value = f"✓ Cargado: {filename}"; switch(0)

        def delete_file(filename):
            os.remove(os.path.join(export_dir, filename))
            status_text.value = f"🗑️ Eliminado: {filename}"; update_explorer()

        def export_file(filename):
            with open(os.path.join(export_dir, filename), "r") as f: page.set_clipboard(f.read())
            status_text.value = f"📤 Código copiado al portapapeles."; page.update()

        def rename_file(old_name, new_name, dlg):
            if new_name:
                os.rename(os.path.join(export_dir, old_name), os.path.join(export_dir, new_name + ".jscad"))
                status_text.value = f"✏️ Renombrado a {new_name}.jscad"
            dlg.open = False; update_explorer()

        def prompt_rename(filename):
            txt_new_name = ft.TextField(label="Nuevo nombre (sin extensión)")
            dlg = ft.AlertDialog(
                title=ft.Text("Renombrar Archivo"), content=txt_new_name,
                actions=[ft.TextButton("Guardar", on_click=lambda e: rename_file(filename, txt_new_name.value, dlg))]
            )
            page.dialog = dlg; dlg.open = True; page.update()

        def update_explorer():
            lv_files.controls.clear()
            for f in reversed(os.listdir(export_dir)):
                row = ft.Row([
                    ft.Text("📄 " + f[:18], color="white", size=13, expand=True),
                    ft.TextButton("📂", on_click=lambda e, fname=f: load_file(fname), tooltip="Cargar"),
                    ft.TextButton("✏️", on_click=lambda e, fname=f: prompt_rename(fname), tooltip="Renombrar"),
                    ft.TextButton("📤", on_click=lambda e, fname=f: export_file(fname), tooltip="Copiar Código"),
                    ft.TextButton("🗑️", on_click=lambda e, fname=f: delete_file(fname), tooltip="Eliminar")
                ], alignment="spaceBetween")
                lv_files.controls.append(ft.Container(content=row, bgcolor="#1a1a1a", padding=5, border_radius=5))
            page.update()

        explorer_container = ft.Container(content=ft.Column([ft.Text("Gestor de Proyectos", color="white", weight="bold"), lv_files], expand=True), padding=10, expand=True, bgcolor="#0a0a0a", visible=False)

        # =========================================================
        # 3. VISOR Y NAVEGACIÓN
        # =========================================================
        viewer_container = ft.Container(content=ft.Text("Visor inactivo."), alignment=ft.Alignment(0,0), expand=True, visible=False)

        def switch(idx):
            editor_container.visible = (idx == 0); viewer_container.visible = (idx == 1); explorer_container.visible = (idx == 2)
            if idx == 2: update_explorer()
            page.update()

        def run_render():
            global LATEST_CODE_B64
            status_text.value = "Compilando operaciones booleanas..."
            switch(1) 
            try:
                LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode('utf-8')).decode('utf-8').replace('\n', '').replace('\r', '')
                viewer_container.content = ft.ElevatedButton("🚀 ABRIR RENDERIZADOR HARDWARE", url=f"http://127.0.0.1:{LOCAL_PORT}/?t={time.time()}", bgcolor="blue900", color="white", expand=True)
                status_text.value = f"✓ Listo."
            except Exception as e: status_text.value = f"Error: {e}"
            page.update()

        main_content = ft.SafeArea(
            content=ft.Column([
                ft.Row([
                    ft.TextButton("💻 Editor", on_click=lambda _: switch(0)), 
                    ft.TextButton("👁️ Visor", on_click=lambda _: switch(1)),
                    ft.TextButton("📁 Archivos", on_click=lambda _: switch(2))
                ], alignment="center", scroll=ft.ScrollMode.AUTO),
                editor_container, viewer_container, explorer_container, status_text
            ], expand=True)
        )
        page.add(main_content); update_explorer()
        
    except Exception:
        page.clean(); page.add(ft.SafeArea(content=ft.Text(traceback.format_exc(), color="red", selectable=True))); page.update()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets", view="web_browser", port=8555) if "com.termux" in os.environ.get("PREFIX", "") else ft.app(target=main, assets_dir="assets")
