import flet as ft
from ui.tabs.editor_tab import build_editor_tab
from ui.tabs.constructor_tab import build_constructor_tab
from ui.tabs.viewer_tab import build_viewer_tab
from ui.tabs.assembly_tab import build_assembly_tab
from ui.tabs.pbr_tab import build_pbr_tab
from ui.tabs.files_tab import build_files_tab
from ui.tabs.ai_tab import build_ai_tab

def build_main_ui(page, status, txt_code, tools_lib, panel_globales, hw_panel,
                  panel_calibre, list_nexus_db, tf_path, list_android, row_quick_paths,
                  col_assembly, lbl_ensamble_warn,
                  set_tab, clear_editor, run_render, add_assembly_part,
                  refresh_nexus_db, nav_to, save_to_android,
                  internal_ip, local_port):
    tabs = [
        build_editor_tab(txt_code, clear_editor, run_render),
        build_constructor_tab(tools_lib, panel_globales, run_render),
        build_viewer_tab(hw_panel),
        build_assembly_tab(add_assembly_part, set_tab, col_assembly, lbl_ensamble_warn),
        build_pbr_tab(),
        build_files_tab(panel_calibre, list_nexus_db, tf_path, list_android, row_quick_paths,
                        refresh_nexus_db, nav_to, save_to_android, internal_ip, local_port),
        build_ai_tab()
    ]

    nav_bar = ft.Row([
        ft.ElevatedButton("💻 CODE", on_click=lambda _: set_tab(0), bgcolor="#21262D", color="white"),
        ft.ElevatedButton("🌐 PARAM", on_click=lambda _: set_tab(1), bgcolor="#FFAB00", color="black"),
        ft.ElevatedButton("👁️ 3D", on_click=lambda _: set_tab(2), bgcolor="#00E5FF", color="black"),
        ft.ElevatedButton("🧩 ENS", on_click=lambda _: set_tab(3), bgcolor="#7CB342", color="white"),
        ft.ElevatedButton("🎨 PBR", on_click=lambda _: set_tab(4), bgcolor="#C51162", color="white"),
        ft.ElevatedButton("📂 FILES", on_click=lambda _: set_tab(5), bgcolor="#21262D", color="white"),
        ft.ElevatedButton("🤖 IA", on_click=lambda _: set_tab(6), bgcolor="#B388FF", color="black"),
    ], scroll="auto")

    main_container = ft.Container(content=tabs[0], expand=True)

    return nav_bar, main_container, tabs
