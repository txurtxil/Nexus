import flet as ft
import os, base64, json, threading, http.server, socket, time, warnings, subprocess, tempfile, traceback
import http.client
import ssl

warnings.simplefilter("ignore", DeprecationWarning)

# =========================================================
# RUTAS Y DIRECTORIOS
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

try:
    EXPORT_DIR = os.path.join(BASE_DIR, "nexus_proyectos")
    os.makedirs(EXPORT_DIR, exist_ok=True)
except:
    EXPORT_DIR = os.path.join(tempfile.gettempdir(), "nexus_proyectos")
    os.makedirs(EXPORT_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(EXPORT_DIR, "nexus_config.json")

# =========================================================
# SERVIDOR WEB LOCAL (Visor 3D)
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
        if self.path == '/api/get_code_b64.json':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"code_b64": LATEST_CODE_B64}).encode())
        else:
            try:
                filename = self.path.strip("/")
                if not filename: filename = "openscad_engine.html"
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
# APLICACIÓN PRINCIPAL NEXUS v5.1
# =========================================================
def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD v5.1"
        page.theme_mode = "dark"
        page.padding = 0

        status = ft.Text("NEXUS v5.1 | Online", color="green")
        prompt_text_saved = ""

        def open_dialog(dialog):
            try: page.open(dialog)
            except: 
                if dialog not in page.overlay: page.overlay.append(dialog)
                dialog.open = True
                page.update()

        def close_dialog(dialog):
            try: page.close(dialog)
            except: dialog.open = False; page.update()

        def export_manual(texto, titulo="Exportar"):
            txt_copy = ft.TextField(value=texto, multiline=True, read_only=True, expand=True)
            dlg_copy = ft.AlertDialog(
                title=ft.Text(titulo),
                content=ft.Column([ft.Text("Copia el texto:", color="grey"), ft.Container(content=txt_copy, height=300)]),
                actions=[ft.ElevatedButton("CERRAR", on_click=lambda _: close_dialog(dlg_copy))]
            )
            open_dialog(dlg_copy)

        def copy_text(text_to_copy):
            try:
                page.set_clipboard(str(text_to_copy))
                status.value = "✓ Texto copiado."
                page.update()
            except:
                export_manual(str(text_to_copy), "Copia Manual")

        # --- EDITOR ---
        DEFAULT_CODE = "function main() {\n  return CSG.cube({center:[0,0,0], radius:[10,10,10]});\n}"
        txt_code = ft.TextField(label="Editor de Código CSG", multiline=True, expand=True, value=DEFAULT_CODE, text_size=12)

        def load_template(t):
            txt_code.value = t
            txt_code.update()
            set_tab(0)
            status.value = "✓ Código cargado."
            page.update()

        def run_render():
            global LATEST_CODE_B64
            LATEST_CODE_B64 = base64.b64encode(txt_code.value.encode()).decode()
            set_tab(1)
            page.update()

        def save_project():
            fname = f"nexus_{int(time.time())}.jscad"
            with open(os.path.join(EXPORT_DIR, fname), "w") as f: f.write(txt_code.value)
            update_files()
            status.value = f"✓ Guardado: {fname}"
            page.update()

        # --- ARCHIVOS ---
        file_list = ft.ListView(expand=True, spacing=10)
        def update_files():
            file_list.controls.clear()
            for f in reversed(sorted(os.listdir(EXPORT_DIR))):
                if f == "nexus_config.json": continue 
                def make_load(name): return lambda _: load_template(open(os.path.join(EXPORT_DIR, name), "r").read())
                def make_del(name): return lambda _: (os.remove(os.path.join(EXPORT_DIR, name)), update_files())
                row = ft.Container(
                    content=ft.Column([
                        ft.Text(f, weight="bold"),
                        ft.Row([
                            ft.ElevatedButton("▶ Cargar", on_click=make_load(f), bgcolor="green900"),
                            ft.ElevatedButton("🗑️", on_click=make_del(f), bgcolor="red900"),
                        ])
                    ]), padding=10, bgcolor="#1a1a1a", border_radius=8
                )
                file_list.controls.append(row)
            page.update()

        # =========================================================
        # MÓDULO IA + DIAGNÓSTICO
        # =========================================================
        def load_config():
            try:
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r") as f: return json.load(f)
            except: pass
            return {"ai_api_key": "", "ai_provider": "Groq", "ai_model": "llama-3.3-70b-versatile"}

        conf = load_config()
        provider_dd = ft.Dropdown(options=[ft.dropdown.Option("Groq"), ft.dropdown.Option("OpenRouter")], value=conf.get("ai_provider"), width=120)
        api_key_input = ft.TextField(label="API Key", value=conf.get("ai_api_key"), password=True, can_reveal_password=True, expand=True)
        model_input = ft.TextField(label="Modelo LLM", value=conf.get("ai_model"), expand=True)

        def save_config_ui(e):
            with open(CONFIG_FILE, "w") as f:
                json.dump({"ai_api_key": api_key_input.value, "ai_provider": provider_dd.value, "ai_model": model_input.value}, f)
            status.value = "✓ Configuración Guardada."
            page.update()

        chat_history = ft.ListView(expand=True, spacing=10)
        user_prompt = ft.TextField(label="Escribe tu idea (ej: engranaje de 20 dientes)...", multiline=True, expand=True)
        loading_ring = ft.ProgressRing(visible=False, width=20, height=20)
        debug_console = ft.TextField(label="Terminal de Diagnóstico de Red", value="", multiline=True, read_only=True, height=120, text_size=10, color="#00ff00", bgcolor="black")

        def log_debug(msg):
            debug_console.value += f"[{time.strftime('%H:%M:%S')}] {msg}\n"
            page.update()

        SYS_PROMPT = """Eres un ingeniero experto en CAD paramétrico. Genera código en Javascript PURO para la librería CSG.js. 
REGLAS ESTRICTAS:
1. NUNCA uses comandos como cylinder() o translate() sueltos. Causan error.
2. Usa SIEMPRE el prefijo CSG: CSG.cube({center:[x,y,z], radius:[x,y,z]}), CSG.cylinder({start:[x,y,z], end:[x,y,z], radius:R, slices:N}).
3. Devuelve SOLO el código dentro de una 'function main() { ... }' dentro de bloques ```javascript."""

        def fetch_ai_logic():
            try:
                log_debug("1. Iniciando Petición...")
                key = api_key_input.value.strip()
                host = "api.groq.com" if provider_dd.value == "Groq" else "openrouter.ai"
                path = "/openai/v1/chat/completions"
                
                log_debug(f"2. Conectando a {host}...")
                data = {"model": model_input.value, "messages": [{"role": "system", "content": SYS_PROMPT}, {"role": "user", "content": prompt_text_saved}]}
                
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                conn = http.client.HTTPSConnection(host, timeout=20, context=ctx)
                log_debug("3. Enviando Sockets POST...")
                conn.request("POST", path, body=json.dumps(data).encode('utf-8'), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                
                log_debug("4. Esperando respuesta del LLM...")
                res = conn.getresponse()
                body = res.read().decode('utf-8')
                conn.close()
                log_debug(f"5. Servidor respondió HTTP {res.status}")

                if res.status == 200:
                    ai_text = json.loads(body)['choices'][0]['message']['content']
                    code = ""
                    if "```javascript" in ai_text:
                        code = ai_text.split("```javascript")[1].split("```")[0].strip()
                    elif "```js" in ai_text:
                        code = ai_text.split("```js")[1].split("```")[0].strip()
                    elif "function main()" in ai_text:
                        code = ai_text[ai_text.find("function main()"):].strip()

                    controls = [ft.Text(ai_text, color="#cccccc")]
                    if code:
                        controls.append(ft.ElevatedButton("▶ INYECTAR Y COMPILAR", on_click=lambda _, c=code: (load_template(c), run_render()), bgcolor="green900"))
                    
                    chat_history.controls.append(ft.Container(content=ft.Column(controls), bgcolor="#212121", padding=10, border_radius=8))
                else:
                    log_debug(f"FALLO: {body}")
                    chat_history.controls.append(ft.Text(f"Error HTTP {res.status}", color="red"))
            except Exception as ex:
                log_debug(f"CRASH EN HILO: {str(ex)}")
                chat_history.controls.append(ft.Text(f"Excepción: {str(ex)}", color="red"))
            finally:
                loading_ring.visible = False
                page.update()

        def start_ai_process(e):
            nonlocal prompt_text_saved
            if not api_key_input.value or not user_prompt.value: return
            prompt_text_saved = user_prompt.value
            user_prompt.value = ""
            loading_ring.visible = True
            debug_console.value = ""
            chat_history.controls.append(ft.Container(content=ft.Text(prompt_text_saved, color="white"), bgcolor="blue900", padding=10, border_radius=8, alignment=ft.alignment.center_right))
            page.update()
            threading.Thread(target=fetch_ai_logic, daemon=True).start()

        # =========================================================
        # MÓDULO LIBRERÍA
        # =========================================================
        AI_RULE = " REGLA: JS puro CSG.js. Usa primitivas ABSOLUTAS (prefijo CSG.). Devuelve function main() { return pieza; }."
        
        lib_prompts = [
            ("⚡ Electrónica", [
                ("Caja Arduino", "Crea una caja de 100x60x30mm con paredes de 2mm. Resta un hueco lateral para cable USB."),
                ("Soporte Batería", "Bloque sólido con huecos cilíndricos para 2 pilas 18650 (18.5mm radio).")
            ]),
            ("⚙️ Ingeniería", [
                ("Engranaje", "Cilindro de radio 40. Usa un bucle for para añadir 20 dientes rectangulares en el borde."),
                ("Rejilla", "Cubo plano de 100x100x5 con bucles anidados para restar cilindros de ventilación.")
            ])
        ]

        def create_folder_ui(title, items):
            col = ft.Column(visible=False)
            for n, p in items:
                f_p = p + AI_RULE
                col.controls.append(ft.ListTile(title=ft.Text(n), subtitle=ft.Text(p, size=10), trailing=ft.IconButton(ft.icons.COPY, on_click=lambda _, x=f_p: copy_text(x))))
            return ft.Column([ft.ElevatedButton(title, on_click=lambda _: (setattr(col, "visible", not col.visible), page.update()), width=float('inf')), col])

        CODE_ESTACION = """function main() {
  var base = CSG.cube({center: [0,0,12.5], radius: [80,60,12.5]});
  for(var x = -70; x <= -10; x += 22) {
    for(var y = -50; y <= 10; y += 22) {
      base = base.subtract(CSG.cube({center: [x,y,14.5], radius: [9,9,12.5]}));
    }
  }
  return base;
}"""

        CODE_ENGRANAJE = """function main() {
  var d = 16; var r = 25;
  var res = CSG.cylinder({start:[0,0,0], end:[0,0,5], radius:r, slices:64});
  for(var i=0; i<d; i++) {
    var a = (i * Math.PI * 2) / d;
    res = res.union(CSG.cube({center:[Math.cos(a)*r, Math.sin(a)*r, 2.5], radius:[3,5,2.5]}));
  }
  return res.subtract(CSG.cylinder({start:[0,0,-1], end:[0,0,6], radius:5, slices:32}));
}"""

        view_libreria = ft.Column([
            ft.Text("Modelos Maestros (Inyección Directa)", weight="bold", color="amber"),
            ft.ElevatedButton("💎 Estación de Microsoldadura", on_click=lambda _: (load_template(CODE_ESTACION), run_render()), width=float('inf')),
            ft.ElevatedButton("⚙️ Engranaje Paramétrico", on_click=lambda _: (load_template(CODE_ENGRANAJE), run_render()), width=float('inf')),
            ft.Divider(),
            ft.Text("Catálogo de Prompts IA", weight="bold", color="cyan"),
            *[create_folder_ui(t, i) for t, i in lib_prompts]
        ], scroll="auto", expand=True)

        # =========================================================
        # VISTAS Y NAVEGACIÓN
        # =========================================================
        view_editor = ft.Column([
            ft.ElevatedButton("▶ COMPILAR MALLA 3D", on_click=lambda _: run_render(), bgcolor="teal900", height=55),
            ft.Row([ft.ElevatedButton("💾 GUARDAR", on_click=lambda _: save_project()), ft.ElevatedButton("🗑️ RESET", on_click=lambda _: load_template(DEFAULT_CODE))]),
            txt_code
        ], expand=True)

        view_ia = ft.Column([
            ft.Row([provider_dd, api_key_input, ft.ElevatedButton("💾", on_click=save_config_ui)]),
            model_input, debug_console, ft.Divider(), chat_history,
            ft.Row([user_prompt, loading_ring, ft.ElevatedButton("🚀", on_click=start_ai_process)])
        ], expand=True)

        main_container = ft.Container(content=view_editor, expand=True)
        def set_tab(idx):
            tabs = [
                view_editor, 
                ft.Column([ft.Container(height=60), ft.ElevatedButton("🚀 ABRIR VISOR 3D", url=f"[http://127.0.0.1](http://127.0.0.1):{LOCAL_PORT}/", height=60, width=300)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Column([ft.Text("Mis Proyectos"), file_list]),
                view_ia,
                view_libreria
            ]
            main_container.content = tabs[idx]
            if idx == 2: update_files()
            page.update()

        nav = ft.Row([
            ft.ElevatedButton("💻", on_click=lambda _: set_tab(0)),
            ft.ElevatedButton("👁️", on_click=lambda _: set_tab(1)),
            ft.ElevatedButton("📁", on_click=lambda _: set_tab(2)),
            ft.ElevatedButton("🤖", on_click=lambda _: set_tab(3), bgcolor="cyan900"),
            ft.ElevatedButton("📚", on_click=lambda _: set_tab(4), bgcolor="amber900"),
        ], scroll="auto")

        page.add(ft.Container(content=ft.Column([nav, main_container, status], expand=True), padding=ft.padding.only(top=45, left=5, right=5, bottom=5), expand=True))
        update_files()

    except Exception:
        page.add(ft.Text(traceback.format_exc(), color="red"))
        page.update()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER if "TERMUX_VERSION" in os.environ else None)