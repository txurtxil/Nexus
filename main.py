import flet as ft
import os, base64, traceback, sqlite3, warnings, time
from datetime import datetime

warnings.simplefilter("ignore", DeprecationWarning)
try:
    import flet_webview as fwv
    HAS_WEBVIEW = True
except:
    HAS_WEBVIEW = False

def main(page: ft.Page):
    try:
        page.title = "NEXUS CAD"
        page.theme_mode = "dark"
        page.bgcolor = "#0a0a0a"
        
        db_path = "nexus_cad.db"
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("CREATE TABLE IF NOT EXISTS p (name TEXT UNIQUE, code TEXT)")

        txt_name = ft.TextField(label="Proyecto", bgcolor="#121212")
        txt_code = ft.TextField(label="Código", multiline=True, expand=True, value="cube();", color="#00ff00")
        
        # Carga de HTML
        html_b64 = ""
        if os.path.exists("assets/openscad_engine.html"):
            with open("assets/openscad_engine.html", "r") as f:
                html_b64 = base64.b64encode(f.read().encode()).decode()

        wv = fwv.WebView(url=f"data:text/html;base64,{html_b64}", expand=True, visible=False)

        def switch(idx):
            edit.visible = (idx == 0)
            wv.visible = (idx == 1)
            page.update()

        def run_render(e):
            switch(1)
            time.sleep(0.5) # Delay de seguridad para Android
            safe_code = txt_code.value.replace("\n", " ").replace("'", "\\'")
            wv.run_javascript(f"window.processOpenScad('{safe_code}')")

        edit = ft.Column([txt_name, txt_code, ft.ElevatedButton("▶ COMPILAR", on_click=run_render)], expand=True)

        page.add(
            ft.Row([
                ft.TextButton("EDITOR", on_click=lambda _: switch(0)),
                ft.TextButton("VISOR", on_click=lambda _: switch(1)),
            ], alignment="center"),
            edit, wv
        )

    except:
        page.add(ft.Text(traceback.format_exc(), color="red"))
        page.update()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
