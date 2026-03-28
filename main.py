import flet as ft
import sqlite3
import os
import traceback
import base64
import warnings
from datetime import datetime

# Silenciador de Warnings obsoletos
warnings.simplefilter("ignore", DeprecationWarning)

try:
    import flet_webview as fwv
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

WASM_ENGINE_FILE = "openscad_engine.html"

def main(page: ft.Page):
    # -------------------------------------------------------------------
    # 1. BLINDAJE: try/except total para evitar cierres silenciosos
    # -------------------------------------------------------------------
    try:
        # Configuración visual blindada (emojis y colores hex)
        page.title = "NEXUS 3D Studio"
        page.theme_mode = "dark"
        page.bgcolor = "#0a0a0a"
        page.padding = 10

        # -------------------------------------------------------------------
        # 2. BLINDAJE: Ruta segura DB para Android Sandbox (Android 10+)
        # -------------------------------------------------------------------
        home_dir = os.environ.get("HOME")
        if not home_dir or home_dir == "/":
            home_dir = os.environ.get("TMPDIR", os.getcwd())
            
        db_path = os.path.join(home_dir, "nexus_cad.db")
        
        # Inicializar SQLite3
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
            label="Nombre del Proyecto", 
            bgcolor="#151515", 
            border_color="#333333"
        )
        
        txt_code = ft.TextField(
            label="Editor OpenSCAD",
            multiline=True,
            min_lines=10,
            expand=True,
            bgcolor="#000000",
            color="#00ff00",
            text_style=ft.TextStyle(font_family="monospace", size=12),
            value="cube([20,20,10], center=true);"
        )
        
        status_text = ft.Text("Sistema listo Offline.", color="grey600", size=12)
        projects_list = ft.ListView(expand=True, spacing=10, padding=10)

        # -------------------------------------------------------------------
        # EL MOTOR WASM (OPCIÓN B OFFLINE)
        # -------------------------------------------------------------------
        wasm_html_content = ""
        # REGLA TÉCNICA SENIOR: Buscar assets localmente para el APK
        assets_path = os.path.join(os.getcwd(), "assets", WASM_ENGINE_FILE)
        
        if os.path.exists(assets_path):
            with open(assets_path, "r", encoding="utf-8") as f:
                wasm_html_content = f.read()
        else:
            # Placeholder seguro para modo desarrollo si no tienes los assets aún
            wasm_html_content = """
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>body{background:#111;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;}</style>
            </head><body><h3>Error: openscad_engine.html no encontrado en assets.</h3></body></html>
            """

        # Cargamos el HTML como Data URI para asegurar persistencia offline en el WebView nativo
        b64_html = base64.b64encode(wasm_html_content.encode('utf-8')).decode('utf-8')
        
        # Componente WebView (Puente a la Opción B)
        # REGLA DE BLINDAJE: El WebView NO funciona en navegadores normales (Termux). 
        # Solo se instancia si estamos en el APK o en app de escritorio.
        if HAS_WEBVIEW and not page.web:
            wasm_webview = fwv.WebView(
                url=f"data:text/html;base64,{b64_html}",
                expand=True,
                # JavaScript habilitado obligatoriamente para el motor
                javascript_enabled=True, 
            )
        else:
            # Placeholder para cuando pruebes localmente en localhost:8555
            wasm_webview = ft.Container(
                content=ft.Text("Visor 3D: Activo solo en APK (WASM)", color="yellow"),
                alignment=ft.Alignment(0, 0),
                expand=True,
                bgcolor="#111111",
                border_radius=8
            )

        # -------------------------------------------------------------------
        # FUNCIONES LÓGICAS (Base de Datos Blindada)
        # -------------------------------------------------------------------
        
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
                            # TextButtons con Emojis para evitar crashes de iconos nativos
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
                # Cambiar a la pestaña del Editor (índice 0)
                switch_tab(0)
                # Renderizar inmediatamente en WASM
                render_in_wasm()
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

        # REGLA TÉCNICA SENIOR: Comunicar Python -> JavaScript del WebView
        # Inyectamos el códigoOpenSCAD sanitizado como un string JS
        def render_in_wasm():
            code = txt_code.value
            # Sanitizar código para enviarlo como JS string (escapar comillas y saltos de línea)
            safe_code = code.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            
            status_text.value = "Renderizando en WASM offline..."
            status_text.color = "orange400"
            page.update()
            
            # Cambiamos automáticamente a la pestaña del Visor 3D (índice 1)
            switch_tab(1)
            
            try:
                if HAS_WEBVIEW and not page.web:
                    # Inyectar JavaScript en el WebView
                    # Asume que el HTML tiene la función processOpenScad('{safe_code}');
                    wasm_webview.run_javascript(f"processOpenScad('{safe_code}');")
            except Exception as ex:
                # Si post_message falla, es probable que estemos en modo Web_Browser
                status_text.value = f"WASM Error: {ex}"
                status_text.color = "red900"
                page.update()

        # VISTAS (Pestañas convertidas a Columnas independientes)
        editor_view = ft.Column([
            txt_name, txt_code,
            ft.Row([
                ft.FilledButton("💾 Guardar", on_click=save_to_db, style=ft.ButtonStyle(bgcolor="blue900")),
                # Botón de renderizado con Emoji
                ft.FilledButton("▶️ Compilar", on_click=lambda e: render_in_wasm(), style=ft.ButtonStyle(bgcolor="green900")),
                ft.FilledButton("🧹 Limpiar", on_click=clear_editor, style=ft.ButtonStyle(bgcolor="red900")),
            ], alignment="center", wrap=True),
            status_text,
        ], expand=True, visible=True) # Visible al inicio

        viewer_view = ft.Column([wasm_webview], expand=True, visible=False)

        history_view = ft.Column([
            ft.Text("Proyectos (Offline DB)", size=18, color="blue400", weight="bold"),
            projects_list,
        ], expand=True, visible=False)

        # -------------------------------------------------------------------
        # NAVEGACIÓN PERSONALIZADA (Blindada contra submódulos Flet obsoletos)
        # -------------------------------------------------------------------
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

        # Botones de navegación personalizados con Emojis
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

    # -------------------------------------------------------------------
    # 3. BLINDAJE: Diagnóstico rojo ante fallos del try principal
    # -------------------------------------------------------------------
    except Exception:
        page.clean()
        page.bgcolor = "red900" # Pantalla roja de diagnóstico
        page.scroll = "auto"
        page.add(
            ft.Text("FALLO CRÍTICO EN SANDBOX ANDROID", size=24, weight="bold", color="white"),
            ft.Text(traceback.format_exc(), color="white", selectable=True, size=11)
        )
        page.update()

if __name__ == "__main__":
    # Creamos assets obligatoriamente para desarrollo local
    if not os.path.exists("assets"): os.makedirs("assets")
        
    ft.app(
        target=main, 
        assets_dir="assets", 
        view="web_browser", # Modo para probar en Termux
        port=8555
    )
