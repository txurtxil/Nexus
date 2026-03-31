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

def start_server():
    try:
        http.server.HTTPServer(("127.0.0.1", LOCAL_PORT), NexusHandler).serve_forever()
    except:
        pass
threading.Thread(target=start_server, daemon=True).start()

# =========================================================
# APLICACIÓN PRINCIPAL (v3.6 UI Mejorada y Funcional)
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v3.6"
        page.theme_mode = "dark"
        page.padding = 0  # El padding lo manejaremos en un contenedor maestro
        
        status = ft.Text("Sistema Online Activo", color="green")

        # --- PORTAPAPELES (Reparado para Android 10+) ---
        def copy_text(text_to_copy):
            try:
                # Intento principal nativo de Flet 0.23+
                page.set_clipboard(str(text_to_copy))
                status.value = "✓ Código copiado al portapapeles."
                status.color = "green"
            except Exception as e:
                try:
                    # Fallback por consola Termux si estamos en entorno no compilado
                    subprocess.run(['termux-clipboard-set'], input=str(text_to_copy).encode('utf-8'))
                    status.value = "✓ Código copiado (Termux)."
                    status.color = "green"
                except:
                    # Mostrar el error real para diagnóstico si ambos fallan
                    status.value = f"❌ Error portapapeles: {str(e)}"
                    status.color = "red"
            page.update()

        # --- PLANTILLAS JS-CSG ---
        T_CARCASA = "function main() {\n  var ext = CSG.cube({center:[0,0,10], radius:[40,25,10]});\n  var int = CSG.cube({center:[0,0,12], radius:[38,23,10]});\n  return ext.subtract(int);\n}"
        T_ENGRARE = "function main() {\n  var b = CSG.cylinder({start:[0,0,0], end:[0,0,5], radius:20, slices:32});\n  var h = CSG.cylinder({start:[0,0,-1], end:[0,0,6], radius:5, slices:16});\n  return b.subtract(h);\n}"
        T_PEANA = "function main() {\n  var base = CSG.cube({center: [0, 0, 5], radius: [60, 40, 5]});\n  var soporte = CSG.cube({center: [0, 10, 25], radius: [60, 5, 25]});\n  return base.union(soporte);\n}"

        txt_code = ft.TextField(label="Código JS-CSG", multiline=True, expand=True, value=T_CARCASA)

        def load_template(t):
            txt_code.value = t
            page.update()

        btn_c = ft.ElevatedButton("📦 Carcasa", on_click=lambda _: load_template(T_CARCASA))
        btn_e = ft.ElevatedButton("⚙️ Engranaje", on_click=lambda _: load_template(T_ENGRARE))
        btn_p = ft.ElevatedButton("📱 Peana", on_click=lambda _: load_template(T_PEANA))
        
        row_templates = ft.Row([btn_c, btn_e, btn_p], scroll="auto")

        # --- GESTOR DE ARCHIVOS ---
        file_list = ft.ListView(expand=True, spacing=10)

        def update_files():
            file_list.controls.clear()
            for f in reversed(sorted(os.listdir(EXPORT_DIR))):
                def make_load(name): return lambda _: load_file_content(name)
                def make_copy(name): return lambda _: copy_file_content(name)
                def make_del(name): return lambda _: delete_file(name)
                def make_ren(name): return lambda _: prompt_rename(name)

                # Botones compactos y elegantes
                acciones = ft.Row(
                    [
                        ft.ElevatedButton("▶ Abrir", on_click=make_load(f), color="white", bgcolor="#1b5e20"),
                        ft.ElevatedButton("✏️ Editar", on_click=make_ren(f)),
                        ft.ElevatedButton("📋 Copiar", on_click=make_copy(f)),
                        ft.ElevatedButton("🗑️", on_click=make_del(f), color="white", bgcolor="#b71c1c"),
                    ],
                    scroll="auto"
                )

                row = ft.Column([ft.Text(f, weight="bold"), acciones])
                file_list.controls.append(ft.Container(content=row, padding=10, bgcolor="#1a1a1a", border_radius=8))
            page.update()

        def load_file_content(name):
            try:
                with open(os.path.join(EXPORT_DIR, name), "r") as f: txt_code.value = f.read()
                set_tab(0) # Salto al editor
                status.value = "✓ " + name + " cargado."
                status.color = "green"
            except:
                status.value = "❌ Error al leer."
                status.color = "red"
            page.update()

        def copy_file_content(name):
            try:
                with open(os.path.join(EXPORT_DIR, name), "r") as f: copy_text(f.read())
            except:
                status.value = "❌ Error al leer archivo para copiar."
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

        # --- RENOMBRAR (LÁPIZ REPARADO) ---
        def prompt_rename(old_name):
            txt_new = ft.TextField(label="Nuevo nombre (sin .jscad)")
            
            def do_rename(e):
                if txt_new.value:
                    try:
                        nuevo = txt_new.value + ".jscad"
                        os.rename(os.path.join(EXPORT_DIR, old_name), os.path.join(EXPORT_DIR, nuevo))
                        status.value = f"✓ Renombrado a {nuevo}"
                        status.color = "green"
                    except Exception as ex:
                        status.value = f"❌ Error: {str(ex)}"
                        status.color = "red"
                # Compatibilidad universal de cerrado de Dialogs
                try: page.close(dlg)
                except: dlg.open = False
                update_files()
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("Renombrar Proyecto"),
                content=txt_new,
                actions=[ft.ElevatedButton("GUARDAR", on_click=do_rename, bgcolor="blue900", color="white")]
            )
            
            # Compatibilidad universal de apertura de Dialogs
            try: page.open(dlg)
            except: page.dialog = dlg; dlg.open = True; page.update()

        # --- COMPILACIÓN Y GUARDADO ---
        def run_render():
            global LATEST_CODE_B64
            LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode()).decode()
            set_tab(1) # Salto al Visor
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
        # VISTAS INDEPENDIENTES 
        # =========================================================
        view_editor = ft.Column([
            ft.ElevatedButton("▶ COMPILAR MALLA 3D", on_click=lambda _: run_render(), color="white", bgcolor="#004d40", height=50),
            ft.Row([ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save_project(), color="white", bgcolor="#0d47a1"), ft.Text("Plantillas rápidas:")]),
            row_templates,
            txt_code
        ], expand=True)

        btn_visor = ft.ElevatedButton("🚀 ABRIR VISOR 3D", url="http://127.0.0.1:" + str(LOCAL_PORT) + "/", color="white", bgcolor="#4a148c", height=60)
        view_visor = ft.Column([
            ft.Container(height=60), # Empujar hacia abajo
            ft.Row([btn_visor], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=20),
            ft.Text("El motor 3D se abrirá renderizando la última compilación.", text_align=ft.TextAlign.CENTER, color="grey")
        ], expand=True)
        
        view_archivos = ft.Column([ft.Text("Proyectos Locales", weight="bold"), file_list], expand=True)
        
        # --- NUEVA PESTAÑA PROMPTS IA ---
        p1 = "Actúa como ingeniero CAD. Genera código Javascript para la libreria CSG.js. Crea una carcasa de 90x60x30mm con vaciado interno, pared de 2mm. Usa center:[x,y,z] en los cubos. Devuelve la pieza final en la function main()."
        p2 = "Genera el código JS (CSG.js) de una bandeja organizadora con patrón hexagonal. Usa cilindros con 'slices: 6' para crear compartimentos hexagonales y réstalos de un cubo sólido principal."
        p3 = "Crea un soporte paramétrico en forma de L usando CSG.js. Dimensiones base: 50x50x50mm, grosor 5mm. Haz 2 taladros pasantes de 4mm de radio en cada cara usando cilindros y .subtract()."
        
        view_ia = ft.Column([
            ft.Text("Pide código a tu IA favorita:", weight="bold", color="cyan"),
            
            ft.Text("1. Carcasa Electrónica", color="amber"),
            ft.TextField(value=p1, multiline=True, read_only=True, text_size=12),
            ft.ElevatedButton("📋 Copiar Prompt 1", on_click=lambda _: copy_text(p1)),
            ft.Container(height=10),
            
            ft.Text("2. Bandeja Hexagonal", color="amber"),
            ft.TextField(value=p2, multiline=True, read_only=True, text_size=12),
            ft.ElevatedButton("📋 Copiar Prompt 2", on_click=lambda _: copy_text(p2)),
            ft.Container(height=10),
            
            ft.Text("3. Soporte en L (Ingeniería)", color="amber"),
            ft.TextField(value=p3, multiline=True, read_only=True, text_size=12),
            ft.ElevatedButton("📋 Copiar Prompt 3", on_click=lambda _: copy_text(p3)),
            
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

        # FIX DEL NOTCH: Este contenedor empuja toda la app 45 píxeles hacia abajo para evitar la cámara
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