import flet as ft

def build_assembly_tab(add_assembly_part, set_tab, col_assembly, lbl_ensamble_warn):
    return ft.Column([
        ft.Text("🧩 MESA DE ENSAMBLAJE", size=20, color="#FFAB00", weight="bold"),
        ft.Text("Une hasta 10 STLs. Se reflejará instantáneamente en PBR.", color="#8B949E", size=11),
        ft.Row([
            ft.ElevatedButton("➕ AÑADIR PIEZA", on_click=add_assembly_part, bgcolor="#1B5E20", color="white"),
            ft.ElevatedButton("👁️ ABRIR PBR", on_click=lambda _: set_tab(4), bgcolor="#C51162", color="white")
        ]),
        ft.Divider(),
        lbl_ensamble_warn,
        col_assembly
    ], expand=True)
