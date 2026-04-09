import flet as ft
from core.state import state

def build_viewer_tab(hw_panel):
    return ft.Column([
        ft.Container(height=5),
        hw_panel,
        ft.Container(height=5),
        ft.Container(
            content=ft.Column([
                ft.Text("🥽 MODO GAFAS VR O PC EXTERNO", color="#B388FF", weight="bold", size=11),
                ft.TextField(
                    value=f"http://{state.lan_ip}:{state.local_port}/openscad_engine.html",
                    read_only=True,
                    text_size=16,
                    text_align="center",
                    bgcolor="#161B22",
                    color="#00E676"
                )
            ]),
            bgcolor="#1E1E1E",
            padding=10,
            border_radius=8,
            border=ft.border.all(1, "#B388FF")
        ),
        ft.Container(height=5),
        ft.Text("Motor Web Worker (Exportación 100% Nativa TITAN)", text_align="center", color="#00E5FF", weight="bold"),
        ft.ElevatedButton(
            "🔄 ABRIR VISOR 3D (ESTÁNDAR)",
            url=f"http://{state.internal_ip}:{state.local_port}/openscad_engine.html",
            bgcolor="#00E676",
            color="black",
            height=60,
            width=float('inf')
        ),
    ], expand=True, scroll="auto")
