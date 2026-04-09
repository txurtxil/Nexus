import flet as ft

def build_files_tab(panel_calibre, list_nexus_db, tf_path, list_android, row_quick_paths,
                   refresh_nexus_db, nav_to, save_to_android, internal_ip, local_port):
    return ft.Column([
        panel_calibre,
        ft.Container(
            content=ft.Column([
                ft.Text("🌐 INYECCIÓN WEB & NEXUS DB", color="#00E676", weight="bold"),
                ft.ElevatedButton(
                    "🌐 ABRIR INYECTOR WEB STL",
                    url=f"http://{internal_ip}:{local_port}/upload_ui.html",
                    bgcolor="#00B0FF",
                    color="white",
                    width=float('inf')
                ),
                ft.Row([
                    ft.Text("Archivos y Renders listos:", color="#E6EDF3", size=11),
                    ft.ElevatedButton("🔄", on_click=lambda _: refresh_nexus_db(), bgcolor="#1E1E1E", width=50)
                ], alignment="spaceBetween"),
                ft.Container(content=list_nexus_db, bgcolor="#0B0E14", border_radius=5, padding=5)
            ]),
            bgcolor="#161B22",
            padding=10,
            border_radius=8,
            border=ft.border.all(1, "#00E676")
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("📱 EXPLORADOR NATIVO ANDROID (Busca e Importa 📥)", color="#00E5FF", weight="bold"),
                row_quick_paths,
                ft.Row([tf_path, ft.ElevatedButton("Ir", on_click=lambda _: nav_to(tf_path.value), bgcolor="#FFAB00", color="black")]),
                ft.ElevatedButton("💾 GUARDAR CÓDIGO AQUÍ", on_click=save_to_android, bgcolor="#0D47A1", color="white", width=float('inf')),
                ft.Container(content=list_android, bgcolor="#0B0E14", border_radius=5, padding=5)
            ]),
            bgcolor="#161B22",
            padding=10,
            border_radius=8
        )
    ], expand=True, scroll="auto")
