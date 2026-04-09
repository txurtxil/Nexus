import flet as ft
from core.state import state

def build_pbr_tab():
    return ft.Column([
        ft.Container(height=20),
        ft.Text("🎨 PBR STUDIO PRO", size=24, color="#FF007F", weight="bold", text_align="center"),
        ft.Text("Renderizado Físico Realista con Shaders Procedurales.", color="#E6EDF3", text_align="center"),
        ft.Container(height=20),
        ft.Container(
            content=ft.Column([
                ft.Text("Soporta la Pieza Única (PARAM) o Ensamble (MESA).", color="#00E676"),
                ft.Text("El botón 'Tomar Foto' guarda el render en NEXUS DB.", color="#00E676", weight="bold")
            ]),
            bgcolor="#161B22",
            padding=15,
            border_radius=8,
            border=ft.border.all(1, "#C51162")
        ),
        ft.Container(height=20),
        ft.ElevatedButton(
            "🚀 ABRIR PBR STUDIO",
            url=f"http://{state.internal_ip}:{state.local_port}/pbr_studio.html",
            bgcolor="#C51162",
            color="white",
            height=80,
            width=float('inf')
        )
    ], expand=True, horizontal_alignment="center")
