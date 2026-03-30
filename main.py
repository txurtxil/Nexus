import flet as ft
import os, base64, json, threading, http.server, socket, time, warnings
from urllib.parse import urlparse

warnings.simplefilter("ignore", DeprecationWarning)

# Configuración de red local
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); LOCAL_PORT = s.getsockname()[1]
except: LOCAL_PORT = 8556

LATEST_CODE_B64 = ""

class NexusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global LATEST_CODE_B64
        parsed = urlparse(self.path)
        if parsed.path == '/api/get_code_b64.json':
            self.send_response(200); self.send_header("Content-type", "application/json"); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
            self.wfile.write(json.dumps({"code_b64": LATEST_CODE_B64}).encode())
        else:
            try:
                fpath = os.path.join("assets", self.path.strip("/"))
                if not os.path.exists(fpath) or os.path.isdir(fpath): fpath = "assets/openscad_engine.html"
                with open(fpath, "rb") as f:
                    self.send_response(200); self.end_headers(); self.wfile.write(f.read())
            except: self.send_response(404); self.end_headers()
    def log_message(self, *args): pass

threading.Thread(target=lambda: http.server.HTTPServer(("127.0.0.1", LOCAL_PORT), NexusHandler).serve_forever(), daemon=True).start()

def main(page: ft.Page):
    page.title = "NEXUS CAD v2.6"
    page.theme_mode = "dark"
    page.bgcolor = "#0a0a0a"
    page.padding = 0
    
    export_dir = os.path.join(os.environ.get("HOME", os.getcwd()), "nexus_proyectos")
    os.makedirs(export_dir, exist_ok=True)

    # PLANTILLAS INDUSTRIALES
    T_ENGRARE = """function main() {
    var base = CSG.cylinder({start: [0,0,0], end: [0,0,10], radius: 20, slices: 64});
    var hueco = CSG.cylinder({start: [0,0,-5], end: [0,0,15], radius: 5});
    var engranaje = base.subtract(hueco);
    for(var i=0; i<12; i++) {
        var a = (i * 30) * Math.PI / 180;
        var diente = CSG.cube({center: [Math.cos(a)*20, Math.sin(a)*20, 5], radius: [4, 2, 5]});
        engranaje = engranaje.union(diente);
    }
    return engranaje;
}"""

    T_DISIPADOR = """function main() {
    var base = CSG.cube({center: [0,0,2], radius: [30, 30, 2]});
    for(var x=-25; x<=25; x+=10) {
        var aleta = CSG.cube({center: [x, 0, 12], radius: [1, 28, 10]});
        base = base.union(aleta);
    }
    return base;
}"""

    txt_code = ft.TextField(label="Código JS-CSG", multiline=True, expand=True, value=T_ENGRARE, text_size=12, color="#00ff00", font_family="monospace")
    status = ft.Text("Listo v2.6", size=10, color="grey")

    def run():
        global LATEST_CODE_B64
        LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode()).decode()
        tabs.selected_index = 1; page.update()

    def save():
        fname = f"PROYECTO_{int(time.time())}.jscad"
        with open(os.path.join(export_dir, fname), "w") as f: f.write(txt_code.value)
        status.value = f"Guardado: {fname}"; update_files(); page.update()

    # FUNCIONES DE ARCHIVOS (CORREGIDAS)
    def update_files():
        file_list.controls.clear()
        for f in reversed(sorted(os.listdir(export_dir))):
            def handle_load(e, name=f):
                with open(os.path.join(export_dir, name), "r") as file: txt_code.value = file.read()
                tabs.selected_index = 0; page.update()
            
            def handle_rename(e, name=f):
                def do_rename(e2):
                    new = os.path.join(export_dir, new_name.value + ".jscad")
                    os.rename(os.path.join(export_dir, name), new)
                    dlg.open = False; update_files(); page.update()
                new_name = ft.TextField(label="Nuevo nombre")
                dlg = ft.AlertDialog(title=ft.Text("Renombrar"), content=new_name, actions=[ft.TextButton("OK", on_click=do_rename)])
                page.dialog = dlg; dlg.open = True; page.update()

            def handle_copy(e, name=f):
                with open(os.path.join(export_dir, name), "r") as file: page.set_clipboard(file.read())
                status.value = "Código copiado!"; page.update()

            file_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f[:20], size=12, expand=True),
                        ft.IconButton(ft.icons.PLAY_ARROW, on_click=handle_load),
                        ft.IconButton(ft.icons.EDIT, on_click=handle_rename),
                        ft.IconButton(ft.icons.COPY, on_click=handle_copy),
                    ]), bgcolor="#1a1a1a", padding=5, border_radius=8
                )
            )

    file_list = ft.ListView(expand=True, spacing=5)

    # LAYOUT
    editor_tab = ft.Column([
        ft.ElevatedButton("▶ COMPILAR MODELO", on_click=lambda _: run(), height=50, width=500, bgcolor="green900", color="white"),
        ft.Row([
            ft.TextButton("⚙️ Engranaje", on_click=lambda _: (setattr(txt_code, "value", T_ENGRARE), page.update())),
            ft.TextButton("🔥 Disipador", on_click=lambda _: (setattr(txt_code, "value", T_DISIPADOR), page.update())),
            ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save(), bgcolor="blue900")
        ], scroll="auto"),
        txt_code
    ])

    viewer_tab = ft.Container(content=ft.ElevatedButton("LANZAR VISOR NATIVO", url=f"http://127.0.0.1:{LOCAL_PORT}/"), alignment=ft.alignment.center)

    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="EDITOR", content=editor_tab),
            ft.Tab(text="VISOR", content=viewer_tab),
            ft.Tab(text="ARCHIVOS", content=ft.Column([ft.Text("Mis Proyectos"), file_list], expand=True))
        ], expand=True, on_change=lambda _: update_files()
    )

    page.add(ft.SafeArea(content=ft.Column([tabs, status], expand=True)))
    update_files()

ft.app(target=main, port=8555, view=ft.AppView.WEB_BROWSER if "TERMUX_VERSION" in os.environ else None)
