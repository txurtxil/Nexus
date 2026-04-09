import flet as ft

def build_editor_tab(txt_code, clear_editor, run_render):
    return ft.Column([
        ft.Row([
            ft.ElevatedButton("💾 GUARDAR LOCAL", on_click=lambda _: save_project_to_nexus(), bgcolor="#0D47A1", color="white"),
            ft.ElevatedButton("🗑️ RESET", on_click=lambda _: clear_editor(), bgcolor="#B71C1C", color="white")
        ], scroll="auto"),
        txt_code
    ], expand=True)

def save_project_to_nexus():
    # Se implementa en main.py y se pasa como callback
    pass
