import flet as ft
from core.state import state

def build_ai_tab():
    return ft.Column([
        ft.Container(height=30),
        ft.Text("🤖 MOTOR IA MULTI-AGENTE v21.2", size=24, color="#B388FF", weight="bold", text_align="center"),
        ft.Text("Ingeniería Paramétrica y Control Total.", color="#E6EDF3", text_align="center"),
        ft.Container(height=30),
        ft.ElevatedButton(
            "🚀 ABRIR ENTORNO IA",
            url=f"http://{state.internal_ip}:{state.local_port}/ia_assistant.html",
            bgcolor="#8E24AA",
            color="white",
            height=80,
            width=float('inf')
        ),
        ft.Container(height=20),
        ft.Text("💡 El análisis 3D y las inyecciones Agentic ocurren en segundo plano.", color="#8B949E", size=12, text_align="center")
    ], expand=True, horizontal_alignment="center")
