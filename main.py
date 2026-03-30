import flet as ft
import os, base64, traceback, sqlite3, warnings, json
import http.server
import threading
import socket
import time
from urllib.parse import urlparse

warnings.simplefilter("ignore", DeprecationWarning)

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
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/get_code_b64.json':
            self.send_response(200); self.send_header("Content-type", "application/json"); self.send_header("Cache-Control", "no-cache, no-store, must-revalidate"); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
            self.wfile.write(json.dumps({"code_b64": LATEST_CODE_B64}).encode('utf-8'))
        else:
            try:
                with open(os.path.join("assets", "openscad_engine.html"), "r", encoding="utf-8") as f:
                    self.send_response(200); self.send_header("Content-type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                self.send_response(500); self.end_headers()
    def log_message(self, format, *args): pass 

threading.Thread(target=lambda: http.server.HTTPServer(("127.0.0.1", LOCAL_PORT), NexusHandler).serve_forever(), daemon=True).start()

def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v1.4.0"
        page.theme_mode = "dark"
        page.bgcolor = "#0a0a0a"
        page.padding = 0
        
        # =========================================================
        # BASES DE DATOS DE CÓDIGO (PLANTILLAS)
        # =========================================================
        code_tree = """module branch(length, thickness, angle, depth) {
    if (depth > 0) {
        cylinder(h = length, r1 = thickness, r2 = thickness * 0.6, $fn = 12);
        translate([0, 0, length]) {
            rotate([angle, 0, 0]) branch(length * 0.7, thickness * 0.7, angle * 1.1, depth - 1);
            rotate([-angle * 0.8, 0, 120]) branch(length * 0.7, thickness * 0.7, angle, depth - 1);
            rotate([angle * 0.5, 0, 240]) branch(length * 0.7, thickness * 0.7, angle * 1.2, depth - 1);
        }
    }
}
module tree() { branch(20, 3, 25, 7); }
tree();"""

        code_bike = """// Parámetros Generales de Bicicleta
wheel_diameter = 622;
frame_size = 560;
module bicycle() { // Motor dinámico 3D }
bicycle();"""

        code_solar = """// Sistema Solar en OpenSCAD - 11 de Mayo 2017, 20:00h
// Posiciones aproximadas basadas en cálculos orbitales

// Tamaños de planetas (escala relativa ajustada)
sun_radius = 15;
mercury_radius = 2;
venus_radius = 3;
earth_radius = 3.5;
mars_radius = 2.5;
jupiter_radius = 10;
saturn_radius = 8;
uranus_radius = 6;
neptune_radius = 5.5;

// Distancias orbitales
mercury_orbit = 25;
venus_orbit = 35;
earth_orbit = 45;
mars_orbit = 55;
jupiter_orbit = 75;
saturn_orbit = 95;
uranus_orbit = 115;
neptune_orbit = 135;"""

        # =========================================================
        # COMPONENTES DE INTERFAZ
        # =========================================================
        # FIX DE SCROLL: min_lines y max_lines para forzar crecimiento seguro
        txt_code = ft.TextField(
            label="Código OpenSCAD", multiline=True, expand=True, min_lines=15,
            value=code_solar, color="#00ff00", bgcolor="#050505", border_color="#333333"
        )
        
        def load_template(tipo):
            if tipo == 'bike': txt_code.value = code_bike
            elif tipo == 'tree': txt_code.value = code_tree
            else: txt_code.value = code_solar
            page.update()

        def copy_code():
            page.set_clipboard(txt_code.value)
            status_text.value = "✓ Código copiado al portapapeles."
            page.update()
            
        def clear_code():
            txt_code.value = ""
            page.update()

        row_templates = ft.Row([
            ft.Text("Plantillas:", color="grey500"),
            ft.ElevatedButton("🚲", on_click=lambda _: load_template('bike'), bgcolor="#222222", color="white", tooltip="Bicicleta"),
            ft.ElevatedButton("🌲", on_click=lambda _: load_template('tree'), bgcolor="#222222", color="white", tooltip="Árbol"),
            ft.ElevatedButton("🪐", on_click=lambda _: load_template('solar'), bgcolor="#222222", color="white", tooltip="Sistema Solar"),
        ])
        
        row_actions = ft.Row([
            ft.ElevatedButton("📋 COPIAR", on_click=lambda _: copy_code(), bgcolor="#1e88e5", color="white"),
            ft.ElevatedButton("🗑️ LIMPIAR", on_click=lambda _: clear_code(), bgcolor="#e53935", color="white"),
        ])
        
        status_text = ft.Text("Sistema Online - v1.4.0", color="grey600")

        # FIX DE SCROLL: scroll=ft.ScrollMode.AUTO añadido a la Columna principal
        editor_container = ft.Container(
            content=ft.Column([
                row_templates, 
                row_actions,
                txt_code, 
                ft.ElevatedButton("▶ COMPILAR Y ROTAR 3D", on_click=lambda e: run_render(), bgcolor="green900", color="white", height=50)
            ], expand=True, scroll=ft.ScrollMode.AUTO), 
            padding=10, expand=True, bgcolor="#0a0a0a"
        )
        
        viewer_container = ft.Container(content=ft.Text("Visor inactivo."), alignment=ft.Alignment(0,0), expand=True, visible=False)

        def switch(idx):
            editor_container.visible = (idx == 0); viewer_container.visible = (idx == 1)
            page.update()

        def run_render():
            global LATEST_CODE_B64
            status_text.value = "Generando..."
            switch(1) 
            try:
                LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode('utf-8')).decode('utf-8').replace('\n', '').replace('\r', '')
                viewer_container.content = ft.ElevatedButton(
                    "🚀 ABRIR SIMULADOR 3D INTERACTIVO", url=f"http://127.0.0.1:{LOCAL_PORT}/?t={time.time()}",
                    bgcolor="blue900", color="white", expand=True
                )
                status_text.value = f"✓ Listo."
            except Exception as e:
                status_text.value = f"Error: {e}"
            page.update()

        main_content = ft.SafeArea(
            content=ft.Column([
                ft.Container(content=ft.Row([ft.TextButton("💻 EDITOR", on_click=lambda _: switch(0)), ft.TextButton("👁️ VISOR", on_click=lambda _: switch(1))], alignment="center"), bgcolor="#111111", padding=5),
                editor_container, viewer_container, status_text
            ], expand=True)
        )
        page.add(main_content)
        
    except Exception:
        page.clean(); page.add(ft.SafeArea(content=ft.Text(traceback.format_exc(), color="red", selectable=True))); page.update()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets", view="web_browser", port=8555) if "com.termux" in os.environ.get("PREFIX", "") else ft.app(target=main, assets_dir="assets")
