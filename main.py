import flet as ft
import os, base64, json, threading, http.server, socket, time, warnings, tempfile, traceback
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
# MOTOR SERVIDOR LOCAL
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
# APLICACIÓN PRINCIPAL v4.0
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v4.0"
        page.theme_mode = "dark"
        page.padding = 0 
        
        status = ft.Text("Sistema Acorazado v4.0 Activo", color="green")

        # --- GESTOR UNIVERSAL DE CUADROS DE DIÁLOGO (Fix del Lápiz y Portapapeles) ---
        def open_dialog(dialog):
            try: page.open(dialog)
            except: 
                if dialog not in page.overlay: page.overlay.append(dialog)
                dialog.open = True
                page.update()

        def close_dialog(dialog):
            try: page.close(dialog)
            except: dialog.open = False; page.update()

        # --- PORTAPAPELES NATIVO A PRUEBA DE BLOQUEOS (Android 10+) ---
        def export_manual(texto):
            # Si el sistema bloquea la copia oculta, forzamos copia física visual
            txt_copy = ft.TextField(value=texto, multiline=True, read_only=True, expand=True)
            dlg_copy = ft.AlertDialog(
                title=ft.Text("Exportar Código"),
                content=ft.Column([
                    ft.Text("Mantén pulsado dentro del cuadro azul para COPIAR TODO:", color="grey"),
                    ft.Container(content=txt_copy, height=300)
                ]),
                actions=[ft.ElevatedButton("CERRAR", on_click=lambda _: close_dialog(dlg_copy))]
            )
            open_dialog(dlg_copy)

        # --- PLANTILLAS JS-CSG RÁPIDAS ---
        T_CARCASA = "function main() {\n  var ext = CSG.cube({center:[0,0,10], radius:[40,25,10]});\n  var int = CSG.cube({center:[0,0,12], radius:[38,23,10]});\n  return ext.subtract(int);\n}"
        T_ENGRARE = "function main() {\n  var b = CSG.cylinder({start:[0,0,0], end:[0,0,5], radius:20, slices:32});\n  var h = CSG.cylinder({start:[0,0,-1], end:[0,0,6], radius:5, slices:16});\n  return b.subtract(h);\n}"

        txt_code = ft.TextField(label="Código JS-CSG", multiline=True, expand=True, value=T_CARCASA)

        # --- GESTOR DE ARCHIVOS ---
        file_list = ft.ListView(expand=True, spacing=10)

        def update_files():
            file_list.controls.clear()
            for f in reversed(sorted(os.listdir(EXPORT_DIR))):
                def make_load(name): return lambda _: load_file_content(name)
                def make_copy(name): return lambda _: export_manual(open(os.path.join(EXPORT_DIR, name), "r").read())
                def make_del(name): return lambda _: delete_file(name)
                def make_ren(name): return lambda _: prompt_rename(name)

                acciones = ft.Row([
                    ft.ElevatedButton("▶ Abrir", on_click=make_load(f), color="white", bgcolor="#1b5e20"),
                    ft.ElevatedButton("✏️ Editar", on_click=make_ren(f)),
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
                status.value = "✓ " + name + " cargado."
                status.color = "green"
            except:
                status.value = "❌ Error al leer."
                status.color = "red"
            page.update()

        def delete_file(name):
            try:
                os.remove(os.path.join(EXPORT_DIR, name))
                status.value = "✓ Eliminado."
                status.color = "green"
            except:
                status.value = "❌ Error al borrar."
                status.color = "red"
            update_files()

        # --- RENOMBRAR (REPARADO 100%) ---
        def prompt_rename(old_name):
            txt_new = ft.TextField(label="Nuevo nombre (sin .jscad)")
            
            def do_rename(e):
                if txt_new.value:
                    try:
                        nuevo = txt_new.value + ".jscad"
                        os.rename(os.path.join(EXPORT_DIR, old_name), os.path.join(EXPORT_DIR, nuevo))
                        status.value = "✓ Renombrado"
                        status.color = "green"
                    except Exception as ex:
                        status.value = "❌ Error: " + str(ex)
                        status.color = "red"
                close_dialog(dlg)
                update_files()

            dlg = ft.AlertDialog(
                title=ft.Text("Renombrar Proyecto"),
                content=txt_new,
                actions=[ft.ElevatedButton("GUARDAR", on_click=do_rename, bgcolor="#0d47a1", color="white")]
            )
            open_dialog(dlg)

        # --- COMPILACIÓN Y GUARDADO ---
        def run_render():
            global LATEST_CODE_B64
            LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode()).decode()
            set_tab(1) 
            page.update()

        def save_project():
            fname = "nexus_" + str(int(time.time())) + ".jscad"
            try:
                with open(os.path.join(EXPORT_DIR, fname), "w") as f: f.write(txt_code.value)
                status.value = "✓ Guardado: " + fname
                status.color = "green"
            except:
                status.value = "❌ Error de escritura."
                status.color = "red"
            update_files()

        # =========================================================
        # CARPETAS DE IA (SISTEMA ACCORDION MANUAL)
        # =========================================================
        def create_folder(icon, title, prompts):
            controls = []
            for name, text in prompts:
                controls.append(ft.Text(name, color="amber", weight="bold"))
                controls.append(ft.TextField(value=text, multiline=True, read_only=True, text_size=12))
                controls.append(ft.Container(height=15))

            content_col = ft.Column(controls, visible=False)

            def toggle(e):
                content_col.visible = not content_col.visible
                page.update()

            btn = ft.ElevatedButton(icon + " " + title, on_click=toggle, width=float('inf'), color="white", bgcolor="#424242")
            return ft.Column([btn, content_col])

        ia_electronica = [
            ("Caja Raspberry Pi", "Actúa como ingeniero CAD. Usa CSG.js para hacer una caja de 90x60x30mm (pared 2mm). Añade agujeros laterales para puertos USB y Ethernet. Devuelve código puro en function main()."),
            ("Pasacables de Escritorio", "Genera código CSG.js para un cilindro hueco paramétrico (radio exterior 30mm, interior 25mm, altura 20mm) con una ranura lateral para introducir cables."),
        ]
        
        ia_hogar = [
            ("Maceta Geométrica Low-Poly", "Crea en CSG.js una maceta combinando y rotando cubos a 45 grados para darle aspecto facetado. Hazle un vaciado cilíndrico central profundo y un agujero de drenaje inferior."),
            ("Posavasos de Panal", "Diseña un posavasos redondo de radio 45mm y grosor 5mm en CSG.js. Usa un bucle 'for' para sustraer hexágonos (cilindros de 6 lados) y crear un patrón de panal de abejas."),
        ]
        
        ia_deportes = [
            ("Clip Mosquetón", "Programa en CSG.js la silueta de un mosquetón simple usando esferas y cilindros unidos, con una abertura lateral."),
            ("Silbato Paramétrico", "Diseña un silbato deportivo con CSG.js. Mezcla un cilindro hueco como cámara de aire y un rectángulo como boquilla, con un corte superior para la salida del sonido."),
        ]
        
        ia_herramientas = [
            ("Soporte L con Refuerzo", "Crea un soporte de montaje en forma de L de 50x50x50mm en CSG.js. Añade un triángulo de refuerzo interno entre ambas caras. Incluye 2 agujeros de tornillo."),
            ("Organizador de Brocas", "Haz un bloque sólido en CSG.js de 100x30x20mm. Usa un bucle for para restar cilindros de diferentes diámetros a lo largo del bloque (3mm, 4mm, 5mm...)."),
        ]

        # =========================================================
        # VISTAS INDEPENDIENTES 
        # =========================================================
        view_editor = ft.Column([
            ft.ElevatedButton("▶ COMPILAR MALLA 3D", on_click=lambda _: run_render(), color="white", bgcolor="#004d40", height=50),
            ft.Row([
                ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save_project(), color="white", bgcolor="#0d47a1"),
                ft.ElevatedButton("📦 Plantilla", on_click=lambda _: load_template(T_CARCASA)),
            ], scroll="auto"),
            txt_code
        ], expand=True)

        btn_visor = ft.ElevatedButton("🚀 ABRIR VISOR 3D", url="http://127.0.0.1:" + str(LOCAL_PORT) + "/", color="white", bgcolor="#4a148c", height=60)
        view_visor = ft.Column([
            ft.Container(height=60), 
            ft.Row([btn_visor], alignment=ft.MainAxisAlignment.CENTER),
            ft.Text("Haz clic para abrir el motor 3D interactivo WebGL.", text_align=ft.TextAlign.CENTER, color="grey")
        ], expand=True)
        
        view_archivos = ft.Column([ft.Text("Proyectos", weight="bold"), file_list], expand=True)
        
        view_ia = ft.Column([
            ft.Text("Catálogo de Prompts IA:", weight="bold", color="cyan"),
            ft.Text("Pulsa las carpetas para abrirlas. Mantén pulsado el texto para copiarlo a ChatGPT.", color="grey", size=11),
            create_folder("⚡", "Electrónica y PCB", ia_electronica),
            create_folder("🏠", "Hogar y Decoración", ia_hogar),
            create_folder("🔧", "Herramientas y Taller", ia_herramientas),
            create_folder("🚴", "Deportes y Outdoors", ia_deportes),
        ], expand=True, scroll="auto")

        # =========================================================
        # MOTOR DE NAVEGACIÓN Y DISTRIBUCIÓN (Notch Fix)
        # =========================================================
        main_container = ft.Container(content=view_editor, expand=True)

        def set_tab(idx):
            if idx == 0: main_container.content = view_editor
            elif idx == 1: main_container.content = view_visor
            elif idx == 2: main_container.content = view_archivos
            elif idx == 3: main_container.content = view_ia
            page.update()

        nav_bar = ft.Row([
            ft.ElevatedButton("💻 EDITOR", on_click=lambda _: set_tab(0)),
            ft.ElevatedButton("👁️ VISOR", on_click=lambda _: set_tab(1)),
            ft.ElevatedButton("📁 ARCHIVOS", on_click=lambda _: (update_files(), set_tab(2))),
            ft.ElevatedButton("🧠 PROMPTS IA", on_click=lambda _: set_tab(3), color="black", bgcolor="cyan"),
        ], scroll="auto")

        root_container = ft.Container(
            content=ft.Column([nav_bar, main_container, status], expand=True),
            padding=ft.padding.only(top=45, left=5, right=5, bottom=5),
            expand=True
        )

        page.add(root_container)
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