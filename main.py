import flet as ft
import sqlite3
import os
import traceback
import base64
import warnings
from datetime import datetime

warnings.simplefilter("ignore", DeprecationWarning)

try:
    import flet_webview as fwv
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

def main(page: ft.Page):
    try:
        page.title = "NEXUS 3D Studio"
        page.theme_mode = "dark"
        page.bgcolor = "#0a0a0a"
        page.padding = 10

        db_path = "nexus_cad.db"
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS projects (name TEXT UNIQUE, code TEXT, created_at TEXT)")
        conn.commit()

        txt_name = ft.TextField(label="Nombre", bgcolor="#151515")
        txt_code = ft.TextField(
            label="Código OpenSCAD", multiline=True, expand=True,
            bgcolor="#000000", color="#00ff00", text_style=ft.TextStyle(font_family="monospace"),
            value="cube([20,20,10], center=true);"
        )
        
        status_text = ft.Text("Listo", color="grey600")
        projects_list = ft.ListView(expand=True, spacing=10)

        # Cargar HTML desde assets
        html_b64 = ""
        assets_path = os.path.join("assets", "openscad_engine.html")
        if os.path.exists(assets_path):
            with open(assets_path, "r", encoding="utf-8") as f:
                content = f.read()
                html_b64 = base64.b64encode(content.encode()).decode()

        # Componente WebView Blindado
        wv = fwv.WebView(
            url=f"data:text/html;base64,{html_b64}",
            expand=True,
            visible=False
        )

        def switch_tab(idx):
            editor_container.visible = (idx == 0)
            wv.visible = (idx == 1)
            history_container.visible = (idx == 2)
            page.update()

        def render_now(e):
            switch_tab(1)
            code_safe = txt_code.value.replace("\n", " ").replace("'", "\\'")
            # Inyectar JS con un pequeño delay para asegurar carga
            wv.run_javascript(f"window.processOpenScad('{code_safe}')")
            status_text.value = "Renderizando..."
            page.update()

        def save_db(e):
            now = datetime.now().strftime("%H:%M:%S")
            cursor.execute("INSERT OR REPLACE INTO projects VALUES (?, ?, ?)", (txt_name.value, txt_code.value, now))
            conn.commit()
            status_text.value = "✓ Guardado"
            page.update()

        editor_container = ft.Column([
            txt_name, txt_code,
            ft.Row([
                ft.FilledButton("💾", on_click=save_db),
                ft.FilledButton("▶️ COMPILAR", on_click=render_now, bgcolor="green900"),
            ], alignment="center")
        ], expand=True)

        history_container = ft.Column([ft.Text("Historial"), projects_list], expand=True, visible=False)

        page.add(
            ft.Row([
                ft.TextButton("💻 Editor", on_click=lambda _: switch_tab(0)),
                ft.TextButton("👁️ Visor", on_click=lambda _: switch_tab(1)),
                ft.TextButton("📂 Base", on_click=lambda _: switch_tab(2)),
            ], alignment="center"),
            ft.Divider(),
            editor_container,
            wv,
            history_container,
            status_text
        )

    except Exception:
        page.add(ft.Text(traceback.format_exc(), color="red"))
        page.update()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
