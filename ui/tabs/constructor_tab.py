import flet as ft

def build_constructor_tab(tools_lib, panel_globales, run_render):
    return ft.Column([
        panel_globales,
        ft.Text("💡 Opciones Especiales:", size=12, color="#8B949E"), tools_lib.cat_especial,
        ft.Text("📐 Bocetos y Perfiles 2D:", size=12, color="#2962FF", weight="bold"), tools_lib.cat_bocetos,
        ft.Text("⚔️ ULTIMATE STL FORGE:", size=12, color="#00E676", weight="bold"), tools_lib.cat_stl_forge,
        ft.Text("🔋 Accesorios Prácticos:", size=12, color="#00E676"), tools_lib.cat_accesorios,
        ft.Text("🏭 Producción y Láser:", size=12, color="#00B0FF"), tools_lib.cat_produccion,
        ft.Text("🌪️ Transición de Formas:", size=12, color="#D50000"), tools_lib.cat_lofting,
        ft.Text("🧬 Topología y Voronoi:", size=12, color="#FBC02D"), tools_lib.cat_topologia,
        ft.Text("⚙️ Engranajes Avanzados:", size=12, color="#FF9100"), tools_lib.cat_engranajes,
        ft.Text("🧱 Ensamblajes Multi-Cuerpo:", size=12, color="#7CB342"), tools_lib.cat_multicuerpo,
        ft.Text("📐 Perfiles y Revolución 2D->3D:", size=12, color="#AB47BC"), tools_lib.cat_perfiles,
        ft.Text("🛸 Aero y Orgánico:", size=12, color="#00E5FF"), tools_lib.cat_aero,
        ft.Text("⚙️ Cinemática y Mecanismos:", size=12, color="#FFAB00"), tools_lib.cat_mecanismos,
        ft.Text("🛠️ Ingeniería:", size=12, color="#FF9100"), tools_lib.cat_ingenieria,
        ft.Text("📦 Geometría Básica:", size=12, color="#8B949E"), tools_lib.cat_basico,
        ft.Divider(color="#30363D"),
        tools_lib.panel_stl_transform,
        *tools_lib.tool_panels.values(),
        ft.ElevatedButton("▶ ENVIAR AL WORKER (RENDER 3D)", on_click=lambda _: run_render(), bgcolor="#00E676", color="black", height=60, width=float('inf'))
    ], expand=True, scroll="auto")
