import flet as ft
import sqlite3
import os
import traceback
import base64
import warnings
import time
from datetime import datetime

warnings.simplefilter("ignore", DeprecationWarning)

try:
    import flet_webview as fwv
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

WASM_ENGINE_FILE = "openscad_engine.html"

# Variable global para el Handshake técnico
IS_VIEWER_READY = False

def main(page: ft.Page):
    # ---------------------------------------------------------
    # 1. BLINDAJE GENERAL: try/except contra crasheos del Sandbox
    # ---------------------------------------------------------
    try:
        # Configuración blindada: Uso hex y minúsculas (image_2.png approved)
        page.title = "NEXUS 3D Studio"
        page.theme_mode = "dark"
        page.bgcolor = "#0a0a0a" 
        page.padding = 10

        # RUTA DB ULTRA-BLINDADA PARA ANDROID Sandbox (image_5.png fix)
        # Usamos la técnica para encontrar HOME o TMPDIR si falla os.getcwd()
        home_dir = os.environ.get("HOME")
        if not home_dir or home_dir == "/":
            home_dir = os.environ.get("TMPDIR", os.getcwd())
            
        db_path = os.path.join(home_dir, "nexus_cad.db")
        
        # SQLite3 seguro offline
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS projects
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           name TEXT UNIQUE, 
                           code TEXT,
                           created_at TEXT)''')
        conn.commit()

        # COMPONENTES DE LA UI
        txt_name = ft.TextField(
            label="Nombre del Proyecto", bgcolor="#151515", border_color="#333333"
        )
        txt_code = ft.TextField(
            label="Editor OpenSCAD",
            multiline=True, min_lines=10, expand=True,
            bgcolor="#000000", color="#00ff00", # Estilo CAD clásico (image_8.png approved)
            text_style=ft.TextStyle(font_family="monospace", size=12),
            value="cube([20,20,10], center=true);"
        )
        
        status_text = ft.Text("Sistema listo Offline.", color="grey600", size=12)
        projects_list = ft.ListView(expand=True, spacing=10, padding=10)

        # ---------------------------------------------------------
        # EL MOTOR WASM (OPCIÓN B OFFLINE) CON HANDSHAKE
        # ---------------------------------------------------------
        wasm_html_content = ""
        # REGLA SENIOR: Buscamos assets localmente
        assets_path = os.path.join(os.getcwd(), "assets", WASM_ENGINE_FILE)
        
        if os.path.exists(assets_path):
            with open(assets_path, "r", encoding="utf-8") as f:
                wasm_html_content = f.read()
        else:
            wasm_html_content = "<html><body style='background:#111;color:#fff;'>Visor 3D no encontrado en assets.</body></html>"

        # Cargar HTML como Data URI para asegurar persistencia offline en el WebView nativo
        b64_html = base64.b64encode(wasm_html_content.encode('utf-8')).decode('utf-8')
        
        # === FUNCIÓN CLAVE DE HANDSHAKE: RECEPCIÓN DE MENSAJES JS -> PYTHON ===
        def on_webview_message(e):
            global IS_VIEWER_READY
            print("MENSAJE DESDE WEBVIEW:", e.data)
            if e.data == "viewer_ready":
                IS_VIEWER_READY = True
                status_text.value = "✓ Visor Sincronizado. Renderizando..."
                status_text.color = "green400"
                
                # Sincronización exitosa, inyectamos el códigoOpenScad que estaba esperando
                render_in_wasm_confirmed()
                page.update()

        if HAS_WEBVIEW and not page.web:
            wasm_webview = fwv.WebView(
                url=f"data:text/html;base64,{b64_html}",
                expand=True,
                # FIX CRÍTICO: No poner javascript_enabled=True, crashea Flet 0.83+
                # === ACTIVAMOS EL ESCUCHADOR DE MENSAJES ===
                on_message=on_webview_message # Llama al Handshake técnico
            )
        else:
            wasm_webview = ft.Container(
                content=ft.Text("Visor 3D: Activo solo en APK (Modo Web local)", color="yellow"),
                alignment=ft.Alignment(0, 0), expand=True, bgcolor="#111111", border_radius=8
            )

        # FUNCIONES LÓGICAS DB (image_2.png approved)
        def load_history():
            projects_list.controls.clear()
            cursor.execute("SELECT name, created_at FROM projects ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for row in rows:
                projects_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("📦", size=16),
                            ft.Text(row[0], color="white", weight="bold", expand=True),
                            ft.TextButton("✏️ Cargar", on_click=lambda e, n=row[0]: load_project_to_editor(n)),
                            ft.TextButton("🗑️ Borrar", on_click=lambda e, n=row[0]: delete_project(n)),
                        ]),
                        bgcolor="#151515", padding=10, border_radius=8
                    )
                )
            page.update()

        def load_project_to_editor(name):
            cursor.execute("SELECT code FROM projects WHERE name=?", (name,))
            row = cursor.fetchone()
            if row:
                txt_name.value = name
                txt_code.value = row[0]
                switch_tab(0) # Volver al editor
            page.update()

        def delete_project(name):
            cursor.execute("DELETE FROM projects WHERE name=?", (name,))
            conn.commit()
            load_history()

        def save_to_db(e):
            if not txt_name.value: return
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            try:
                cursor.execute("INSERT OR REPLACE INTO projects (name, code, created_at) VALUES (?, ?, ?)", 
                             (txt_name.value, txt_code.value, now))
                conn.commit()
                status_text.value = f"✓ Guardado: {txt_name.value}"
                status_text.color = "green400"
                load_history()
                page.update()
            except Exception as ex:
                status_text.value = f"Error DB: {str(ex)}"
                status_text.color = "red900"
                page.update()

        def clear_editor(e):
            txt_name.value = ""
            txt_code.value = ""
            page.update()

        # REGLA TÉCNICA SENIOR: Inyección Directa vía JS confirmed by image_11.png
        # Ahora espera el handshake
        def render_in_wasm():
            # Avisamos visualmente antes de enviar
            status_text.value = "Iniciando motor WASM offline... (Sincronizando)"
            status_text.color = "orange400"
            switch_tab(1) # Pestaña del visor
            
            # BLINDAJE: Si el visor ya está sincronizado, renderizamos directo.
            # Si no, on_webview_message se encargará.
            if IS_VIEWER_READY:
                render_in_wasm_confirmed()
            
            page.update()

        def render_in_wasm_confirmed():
            # Limpiar comillas simples y saltos de línea
            code = txt_code.value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            
            try:
                # SOLO inyectamos si el WebView está inicializado y estamos en APK
                if HAS_WEBVIEW and not page.web:
                    if IS_VIEWER_READY:
                        # Inyectar JavaScript en el WebView nativo
                        # Asume que el HTML tiene la función processOpenScad('{code}');
                        wasm_webview.run_javascript(f"processOpenScad('{code}');")
                        
                        # Actualizamos estatus inferior (image_10.png/image_11.png style)
                        status_text.value = "✓ Objeto generado nativamente."
                        status_text.color = "blue400"
                    else:
                        status_text.value = "Esperando sincronización del Visor..."
                        status_text.color = "orange400"
            except Exception as ex:
                status_text.value = f"WASM Error al inyectar: {ex}"
                status_text.color = "red900"
            page.update()

        # VISTAS (Pestañas Columnas independientes)
        editor_view = ft.Column([
            txt_name, txt_code,
            ft.Row([
                # Colores en minúsculas obligatorios
                ft.FilledButton("💾 Guardar", on_click=save_to_db, style=ft.ButtonStyle(bgcolor="blue900")),
                # Botón Compilar con Emoji ▶ (image_8.png style)
                ft.FilledButton("▶ Compilar", on_click=lambda e: render_in_wasm(), style=ft.ButtonStyle(bgcolor="green900")),
                ft.FilledButton("🧹 Limpiar", on_click=clear_editor, style=ft.ButtonStyle(bgcolor="red900")),
            ], alignment="center", wrap=True),
            status_text,
        ], expand=True, visible=True) # Visible al inicio

        viewer_view = ft.Column([wasm_webview], expand=True, visible=False)

        history_view = ft.Column([
            ft.Text("Proyectos (Offline DB)", size=18, color="blue400", weight="bold"),
            projects_list,
        ], expand=True, visible=False)

        # NAVEGACIÓN PERSONALIZADA (approved)
        def get_btn_style(is_active):
            return ft.ButtonStyle(bgcolor="blue900" if is_active else "#222222", color="white")

        def switch_tab(index):
            # Mostrar la vista correcta
            editor_view.visible = (index == 0)
            viewer_view.visible = (index == 1)
            history_view.visible = (index == 2)
            
            # Resaltar el botón activo y apagar los otros
            btn_editor.style = get_btn_style(index == 0)
            btn_viewer.style = get_btn_style(index == 1)
            btn_history.style = get_btn_style(index == 2)
            
            if index == 2:
                load_history()
            
            page.update()

        # Botones de navegación personalizados con Emojis approved
        btn_editor = ft.FilledButton("💻 Editor", on_click=lambda e: switch_tab(0), style=get_btn_style(True))
        btn_viewer = ft.FilledButton("👁️ Visor 3D", on_click=lambda e: switch_tab(1), style=get_btn_style(False))
        btn_history = ft.FilledButton("📂 Historial", on_click=lambda e: switch_tab(2), style=get_btn_style(False))

        nav_row = ft.Row([btn_editor, btn_viewer, btn_history], alignment="center", wrap=True)

        # Inyectar todo en la página
        page.add(
            ft.Text("NEXUS STUDIO CAD", size=24, weight="bold", color="blue400"),
            nav_row,
            ft.Divider(color="#333333"),
            editor_view,
            viewer_view,
            history_view
        )
        
        load_history()

    # ---------------------------------------------------------
    # 3. BLINDAJE: Diagnóstico rojo ante fallos de Sandbox (image_5.png style)
    # ---------------------------------------------------------
    except Exception:
        page.clean()
        page.bgcolor = "#990000" 
        page.scroll = "auto"
        page.add(
            ft.Text("FALLO CRÍTICO EN SANDBOX ANDROID", size=20, weight="bold", color="white"),
            # Traceback seleccionable para depuración
            ft.Text(traceback.format_exc(), color="white", selectable=True, size=12)
        )
        page.update()

if __name__ == "__main__":
    # FIX CRÍTICO: Eliminado el 'os.makedirs("assets")' que crasheaba el APK
    # Si probamos en local Termux, usamos view="web_browser"
    is_termux = "com.termux" in os.environ.get("PREFIX", "")
    
    if is_termux:
        # Modo Desarrollo (Termux) -> Abre navegador en localhost:8555
        ft.app(target=main, assets_dir="assets", view="web_browser", port=8555)
    else:
        # Modo Producción (APK Android) -> Ejecuta nativo (Lazy Load WebView)
        # NUNCA le pasamos "view" ni "port" aquí en APK nativo.
        ft.app(target=main, assets_dir="assets")
