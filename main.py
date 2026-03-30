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
        page.title = "NEXUS CAD v1.6.0"
        page.theme_mode = "dark"
        page.bgcolor = "#0a0a0a"
        page.padding = 0
        
        # =========================================================
        # DIRECTORIO DE EXPORTACIÓN (MEMORIA INTERNA)
        # =========================================================
        export_dir = os.path.join(os.environ.get("HOME", os.getcwd()), "nexus_proyectos")
        os.makedirs(export_dir, exist_ok=True)

        code_eiffel = """// Eiffel Tower in OpenSCAD
module line(start, end, diameter=1) {}
r_outer_0 = 62.5; w0 = 12.5; h = 300;
module eiffel_tower() { }
eiffel_tower();"""

        # =========================================================
        # UI COMPONENTES
        # =========================================================
        txt_code = ft.TextField(
            label="Código OpenSCAD", multiline=True, expand=True, 
            value=code_eiffel, color="#00ff00", bgcolor="#050505", border_color="#333333",
            text_size=12
        )
        
        status_text = ft.Text("Sistema Online - v1.6.0", color="grey600", size=11)

        def save_project():
            filename = f"proyecto_{int(time.time())}.scad"
            filepath = os.path.join(export_dir, filename)
            with open(filepath, "w") as f:
                f.write(txt_code.value)
            status_text.value = f"✓ Guardado en Termux: {filepath}"
            page.update()

        def copy_code():
            page.set_clipboard(txt_code.value)
            status_text.value = "✓ Código copiado al portapapeles."
            page.update()
            
        def clear_code():
            txt_code.value = ""
            page.update()

        row_templates = ft.Row([
            ft.Text("Plantillas:", color="grey500", size=12),
            ft.ElevatedButton("🚲", on_click=lambda _: clear_code(), bgcolor="#222222", color="white"),
            ft.ElevatedButton("🌲", on_click=lambda _: clear_code(), bgcolor="#222222", color="white"),
            ft.ElevatedButton("🪐", on_click=lambda _: clear_code(), bgcolor="#222222", color="white"),
            ft.ElevatedButton("🗼", on_click=lambda _: clear_code(), bgcolor="#222222", color="white"),
        ], scroll=ft.ScrollMode.AUTO)
        
        row_actions = ft.Row([
            ft.ElevatedButton("📋 Copiar", on_click=lambda _: copy_code(), bgcolor="#1e88e5", color="white", style=ft.ButtonStyle(padding=5)),
            ft.ElevatedButton("💾 Guardar Local", on_click=lambda _: save_project(), bgcolor="#8e24aa", color="white", style=ft.ButtonStyle(padding=5)),
            ft.ElevatedButton("🗑️", on_click=lambda _: clear_code(), bgcolor="#e53935", color="white"),
        ], scroll=ft.ScrollMode.AUTO)
        
        # FIX DE SCROLL: Encapsular el editor para que controle su tamaño y el botón quede fijo
        editor_scrollable_area = ft.Container(
            content=ft.Column([row_templates, row_actions, txt_code], expand=True),
            expand=True
        )

        editor_container = ft.Container(
            content=ft.Column([
                editor_scrollable_area, 
                ft.ElevatedButton("▶ COMPILAR Y ROTAR 3D", on_click=lambda e: run_render(), bgcolor="green900", color="white", height=55, width=float('inf'))
            ], expand=True), 
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
