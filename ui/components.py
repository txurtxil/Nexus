import flet as ft

def custom_icon_btn(text, action, tooltip_txt):
    return ft.Container(
        content=ft.Text(text, size=16),
        padding=5,
        bgcolor="#30363D",
        border_radius=5,
        on_click=action,
        tooltip=tooltip_txt,
        ink=True
    )
