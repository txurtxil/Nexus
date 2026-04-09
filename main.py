import flet as ft
import os
import sys
import base64
import json
import threading
import time
import importlib
import shutil

# Añadir el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import EXPORT_DIR, DOWNLOAD_DIR, LOCAL_PORT, MAX_ASSEMBLY_PARTS
from core.state import state
from core.system_utils import get_lan_ip, get_android_root, get_sys_info
from core.stl_utils import validate_stl, analyze_stl, convert_stl_to_obj
from server.http_server import start_server
from ui.main_ui import build_main_ui
from ui.components import custom_icon_btn
import nexus_ui_tools
import param_generators

# =========================================================
# INICIALIZACIÓN DEL SERVIDOR HTTP
# =========================================================
port = LOCAL_PORT
start_server(port)
state.lan_ip = get_lan_ip()
state.local_port = port
state.internal_ip = "127.0.0.1"

ANDROID_ROOT = get_android_root()

def main(page: ft.Page):
    page.title = "NEXUS CAD v21.2 TITAN PRO"
    page.theme_mode = "dark"
    page.bgcolor = "#0B0E14"
    page.padding = 0

    status = ft.Text("NEXUS v21.2 TITAN | Motor IA Multi-Agente Activo", color="#00E676", weight="bold")

    T_INICIAL = "function main() {\n  var pieza = CSG.cube({center:[0,0,GH/2], radius:[GW/2, GL/2, GH/2]});\n  return pieza;\n}"
    txt_code = ft.TextField(
        label="Código Fuente (JS-CSG)", multiline=True, expand=True,
        value=T_INICIAL, bgcolor="#161B22", color="#58A6FF",
        border_color="#30363D", text_size=12
    )

    ensamble_stack = []
    herramienta_actual = "custom"
    modo_ensamble = False

    # --- Funciones auxiliares UI ---
    def clear_editor():
        nonlocal ensamble_stack
        ensamble_stack = []
        txt_code.value = "function main() {\n  return CSG.cube({radius:[0.01,0.01,0.01]});\n}"
        status.value = "✓ Código borrado."
        status.color = "#B71C1C"
        txt_code.update()
        page.update()

    def run_render():
        # Lógica de preparación de código y cambio a pestaña 3D
        js_payload = prepare_js_payload()
        state.latest_code_b64 = base64.b64encode(js_payload.encode('utf-8')).decode()
        state.latest_needs_stl = ("IMPORTED_STL" in js_payload) or herramienta_actual.startswith("stl")
        set_tab(2)
        page.update()

    current_tab = 0
    def set_tab(idx):
        nonlocal current_tab
        current_tab = idx
        main_container.content = tabs[idx]
        if idx == 3:
            render_assembly_ui()
        if idx == 5:
            refresh_nexus_db()
            refresh_explorer(current_android_dir)
        page.update()

    # --- Hilo de monitoreo de IA ---
    def check_ia_injection():
        while True:
            time.sleep(1)
            if state.injected_code_ia:
                txt_code.value = state.injected_code_ia
                state.injected_code_ia = ""
                txt_code.update()
                status.value = "✓ Código de IA recibido e inyectado con éxito."
                status.color = "#B388FF"
                page.update()
            if state.agentic_payload is not None:
                try:
                    payload = state.agentic_payload
                    state.agentic_payload = None
                    tool_name = payload.get("tool", "gear")
                    params = payload.get("params", {})
                    select_tool(tool_name)
                    for key, val in params.items():
                        slider_name = f"sl_{key}"
                        if hasattr(tools_lib, slider_name):
                            slider_obj = getattr(tools_lib, slider_name)
                            slider_obj.value = float(val)
                    update_code_wrapper(None)
                    run_render()
                    status.value = "🎛️ AGENTIC UI: Interfaz ajustada automáticamente."
                    status.color = "#00E676"
                    page.update()
                except Exception as e:
                    print(f"Error procesando el Agentic Payload: {e}")

    threading.Thread(target=check_ia_injection, daemon=True).start()

    # --- Sliders globales y herramientas ---
    def create_slider(label, min_v, max_v, val, is_int):
        txt_val = ft.Text(f"{int(val) if is_int else val:.1f}", color="#00E5FF", width=45, text_align="right", size=13, weight="bold")
        sl = ft.Slider(min=min_v, max=max_v, value=val, expand=True, active_color="#00E5FF", inactive_color="#2A303C")
        if is_int:
            sl.divisions = int(max_v - min_v)
        def internal_change(e):
            txt_val.value = f"{int(sl.value) if is_int else sl.value:.1f}"
            txt_val.update()
            if not modo_ensamble:
                update_code_wrapper()
        sl.on_change = internal_change
        return sl, ft.Row([ft.Text(label, width=110, size=12, color="#E6EDF3"), sl, txt_val])

    sl_g_w, r_g_w = create_slider("Ancho (GW)", 1, 300, 50, False)
    sl_g_l, r_g_l = create_slider("Largo (GL)", 1, 300, 50, False)
    sl_g_h, r_g_h = create_slider("Alto (GH)", 1, 300, 20, False)
    sl_g_t, r_g_t = create_slider("Grosor (GT)", 0.5, 20, 2, False)
    sl_g_tol, r_g_tol = create_slider("Tol. Global (G_TOL)", 0.0, 2.0, 0.2, False)
    sl_kine, r_kine = create_slider("Animación (º)", 0, 360, 0, True)

    dd_mat = ft.Dropdown(
        options=[ft.dropdown.Option("PLA Gris Mate"), ft.dropdown.Option("PETG Transparente"),
                 ft.dropdown.Option("Fibra de Carbono"), ft.dropdown.Option("Aluminio Mecanizado"),
                 ft.dropdown.Option("Madera Bambú"), ft.dropdown.Option("Oro Puro"), ft.dropdown.Option("Neón Cyan")],
        value="PLA Gris Mate", bgcolor="#161B22", color="#00E5FF", expand=True, text_size=12
    )

    def update_code_wrapper(e=None):
        if not modo_ensamble:
            generate_param_code()

    def select_tool(nombre_herramienta):
        nonlocal herramienta_actual
        herramienta_actual = nombre_herramienta
        for k, p in tools_lib.tool_panels.items():
            p.visible = (k == nombre_herramienta)
        tools_lib.panel_stl_transform.visible = nombre_herramienta.startswith("stl")
        generate_param_code()
        page.update()

    tools_lib = nexus_ui_tools.NexusTools(create_slider, update_code_wrapper, set_tab, select_tool)

    def generate_param_code():
        try:
            importlib.reload(param_generators)
        except Exception as e:
            print(f"Error recargando param_generators: {e}")
        h = herramienta_actual
        if h == "custom":
            return
        p_dict = tools_lib.get_p_dict()
        txt_code.value = param_generators.get_code(h, p_dict)
        txt_code.update()

    def prepare_js_payload():
        c_val = {
            "PLA Gris Mate": "[0.5, 0.5, 0.5, 1.0]",
            "PETG Transparente": "[0.8, 0.9, 0.9, 0.45]",
            "Fibra de Carbono": "[0.15, 0.15, 0.15, 1.0]",
            "Aluminio Mecanizado": "[0.7, 0.75, 0.8, 1.0]",
            "Madera Bambú": "[0.6, 0.4, 0.2, 1.0]",
            "Oro Puro": "[0.9, 0.75, 0.1, 1.0]",
            "Neón Cyan": "[0.0, 1.0, 1.0, 0.8]"
        }.get(dd_mat.value, "[0.5, 0.5, 0.5, 1.0]")
        header = f"  var GW = {sl_g_w.value}; var GL = {sl_g_l.value}; var GH = {sl_g_h.value}; var GT = {sl_g_t.value}; var G_TOL = {sl_g_tol.value}; var KINE_T = {sl_kine.value}; var MAT_C = {c_val};\n"
        utils_block = """  if(typeof CSG !== 'undefined' && typeof CSG.Matrix4x4 === 'undefined' && typeof Matrix4x4 !== 'undefined') { CSG.Matrix4x4 = Matrix4x4; }
  var UTILS = { 
    trans: function(o, v) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.trans(x, v);}); if(typeof o.translate === 'function') return o.translate(v); if(typeof translate !== 'undefined') return translate(v, o); } catch(e) {} return o; },
    scale: function(o, v) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.scale(x, v);}); if(typeof o.scale === 'function') return o.scale(v); if(typeof scale !== 'undefined') return scale(v, o); } catch(e) {} return o; },
    rotZ: function(o, d) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.rotZ(x, d);}); if(typeof o.rotateZ === 'function') return o.rotateZ(d); if(typeof rotate !== 'undefined') return rotate([0,0,d], o); } catch(e) {} return o; },
    rotX: function(o, d) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.rotX(x, d);}); if(typeof o.rotateX === 'function') return o.rotateX(d); if(typeof rotate !== 'undefined') return rotate([d,0,0], o); } catch(e) {} return o; },
    rotY: function(o, d) { if(!o) return o; try { if(Array.isArray(o)) return o.map(function(x){return UTILS.rotY(x, d);}); if(typeof o.rotateY === 'function') return o.rotateY(d); if(typeof rotate !== 'undefined') return rotate([0,d,0], o); } catch(e) {} return o; },
    mat: function(o) { if(!o) return CSG.cube({radius:[0.01,0.01,0.01]}); try { if(Array.isArray(o)) return o.map(function(x){return UTILS.mat(x);}); if(typeof o.setColor === 'function') return o.setColor(MAT_C); } catch(e) {} return o; } 
  };\n"""
        header += utils_block
        param_def = "function getParameterDefinitions() { return [{name: 'KINE_T', type: 'slider', initial: 0, min: 0, max: 360, step: 1, caption: 'Cinemática (º)'}]; }\n"
        c = txt_code.value
        if "getParameterDefinitions" not in c:
            if "function main(" in c:
                c = param_def + c.replace("function main(params) {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1).replace("function main() {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1)
            else:
                c = param_def + header + "\n" + c
        else:
            if "function main(" in c:
                c = c.replace("function main(params) {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1).replace("function main() {", "function main(params) {\n" + header + "  if(params && params.KINE_T !== undefined) KINE_T = params.KINE_T;\n", 1)
            else:
                c = header + "\n" + c
        return c

    # --- Panel de globales y switch ensamble ---
    sw_ensamble = ft.Switch(label="Manejo Código Ensamblador", value=False, active_color="#FFAB00")
    panel_ensamble_ops = ft.Row([
        ft.ElevatedButton(content=ft.Text("➕ UNIR PIEZA", color="white"), on_click=lambda _: add_to_stack("union"), bgcolor="#1B5E20", expand=True),
        ft.ElevatedButton(content=ft.Text("➖ RESTAR PIEZA", color="white"), on_click=lambda _: add_to_stack("subtract"), bgcolor="#B71C1C", expand=True)
    ], visible=False)

    def toggle_ensamble(e):
        nonlocal modo_ensamble
        modo_ensamble = sw_ensamble.value
        panel_ensamble_ops.visible = modo_ensamble
        page.update()

    sw_ensamble.on_change = toggle_ensamble

    def parse_current_tool_to_stack_var():
        code_lines = txt_code.value.split('\n')
        var_name = f"obj_{len(ensamble_stack)}"
        body = []
        for line in code_lines[1:-1]:
            if line.strip().startswith("return "):
                ret_val = line.replace("return UTILS.mat(", "").replace("return ", "").replace(");", "").replace(";", "").strip()
                body.append(f"  var {var_name} = {ret_val};")
            else:
                body.append(line)
        return "\n".join(body), var_name

    def add_to_stack(op_type):
        nonlocal ensamble_stack
        body, var_name = parse_current_tool_to_stack_var()
        if not ensamble_stack:
            ensamble_stack.append({"body": body, "var": var_name, "op": "base"})
        else:
            ensamble_stack.append({"body": body, "var": var_name, "op": op_type})
        compile_stack_to_editor()

    def compile_stack_to_editor():
        if not ensamble_stack:
            return
        final_code = "function main() {\n"
        final_var = ""
        for i, item in enumerate(ensamble_stack):
            final_code += f"  // --- Modificador {i} ({item['op']}) ---\n{item['body']}\n"
            if item["op"] == "base":
                final_var = item["var"]
            elif item["op"] == "union":
                final_code += f"  {final_var} = {final_var}.union({item['var']});\n"
            elif item["op"] == "subtract":
                final_code += f"  {final_var} = {final_var}.subtract({item['var']});\n"
        final_code += f"  return UTILS.mat({final_var});\n}}"
        txt_code.value = final_code
        txt_code.update()
        page.update()

    panel_globales = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("🌐 PARÁMETROS GLOBALES", color="#00E5FF", weight="bold", size=11), sw_ensamble], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            r_g_w, r_g_l, r_g_h, r_g_t, r_g_tol,
            ft.Divider(color="#333333"),
            ft.Row([ft.Text("🎨 TEXTURA / RENDER:", color="#E6EDF3", size=11, width=130), dd_mat]),
            ft.Divider(color="#333333"),
            ft.Text("🎬 CINEMÁTICA INTERACTIVA", color="#B388FF", weight="bold", size=11),
            r_kine,
            panel_ensamble_ops
        ]),
        bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#333333")
    )

    # --- Panel de telemetría hardware ---
    pb_cpu = ft.ProgressBar(width=100, color="#FFAB00", bgcolor="#30363D", value=0, expand=True)
    txt_cpu_val = ft.Text("0.0%", size=11, color="#FFAB00", width=40, text_align="right")
    pb_ram = ft.ProgressBar(width=100, color="#00E5FF", bgcolor="#30363D", value=0, expand=True)
    txt_ram_val = ft.Text("0.0%", size=11, color="#00E5FF", width=40, text_align="right")
    txt_cores = ft.Text("CORES: ?", size=11, color="#8B949E", weight="bold")

    hw_panel = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("📊 TELEMETRÍA HARDWARE", size=11, color="#E6EDF3", weight="bold"), txt_cores], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("CPU", size=11, color="#FFAB00", weight="bold", width=30), pb_cpu, txt_cpu_val]),
            ft.Row([ft.Text("RAM", size=11, color="#00E5FF", weight="bold", width=30), pb_ram, txt_ram_val])
        ], spacing=5),
        bgcolor="#1E1E1E", padding=10, border_radius=8, border=ft.border.all(1, "#333333")
    )

    def hw_monitor_loop():
        while True:
            time.sleep(1.5)
            try:
                if current_tab == 2:
                    cpu, ram, cores = get_sys_info()
                    pb_cpu.value = cpu / 100.0
                    txt_cpu_val.value = f"{cpu:.1f}%"
                    pb_ram.value = ram / 100.0
                    txt_ram_val.value = f"{ram:.1f}%"
                    txt_cores.value = f"CORES: {cores}"
                    hw_panel.update()
            except:
                pass
    threading.Thread(target=hw_monitor_loop, daemon=True).start()

    # --- Panel calibre ---
    txt_dim_x = ft.Text("0.0 mm", color="#00E5FF", weight="bold")
    txt_dim_y = ft.Text("0.0 mm", color="#00E5FF", weight="bold")
    txt_dim_z = ft.Text("0.0 mm", color="#00E5FF", weight="bold")
    txt_vol = ft.Text("0.0 cm³", color="#FFAB00", weight="bold")
    txt_peso = ft.Text("0.0 g", color="#00E676", weight="bold")
    panel_calibre = ft.Container(
        content=ft.Column([
            ft.Text("📐 CALIBRE 3D Y PRESUPUESTO (STL ACTUAL)", color="#E6EDF3", weight="bold"),
            ft.Row([ft.Text("Ancho (X):", color="#8B949E", width=80), txt_dim_x]),
            ft.Row([ft.Text("Largo (Y):", color="#8B949E", width=80), txt_dim_y]),
            ft.Row([ft.Text("Alto (Z):", color="#8B949E", width=80), txt_dim_z]),
            ft.Divider(color="#30363D"),
            ft.Row([ft.Text("Volumen:", color="#8B949E", width=80), txt_vol]),
            ft.Row([ft.Text("Peso PLA:", color="#8B949E", width=80), txt_peso])
        ]),
        bgcolor="#161B22", padding=15, border_radius=8, border=ft.border.all(1, "#2962FF")
    )

    # --- Lista de archivos Nexus DB ---
    list_nexus_db = ft.ListView(height=250, spacing=5)
    def refresh_nexus_db():
        list_nexus_db.controls.clear()
        try:
            files = [f for f in os.listdir(EXPORT_DIR) if not f.startswith('.') and f != "imported.stl"]
            if not files:
                list_nexus_db.controls.append(ft.Text("Vacío. Inyecta un archivo.", color="#8B949E", italic=True))
            for f in files:
                ext = f.lower().split('.')[-1]
                p = os.path.join(EXPORT_DIR, f)
                icon = "🧊" if ext=="stl" else ("🖼️" if ext=="png" else "🧩")
                color = "#00E676" if ext=="stl" else ("#C51162" if ext=="png" else "white")
                actions = [
                    custom_icon_btn("✏️", lambda e, fn=f: open_rename_dialog(fn), "Renombrar"),
                    custom_icon_btn("⬇️", lambda e, fn=f: direct_download_file(e, fn), "Guardar a Download"),
                    custom_icon_btn("🗑️", lambda e, fp=p: [os.remove(fp), refresh_nexus_db()], "Borrar")
                ]
                if ext == "stl":
                    actions.insert(0, custom_icon_btn("📦", lambda e, fn=f: export_obj_file(e, fn), "Exportar OBJ"))
                    actions.insert(0, custom_icon_btn("▶️", lambda e, fp=p: load_file(fp), "Cargar STL"))
                elif ext == "jscad":
                    actions.insert(0, custom_icon_btn("▶️", lambda e, fp=p: load_file(fp), "Cargar Código"))
                list_nexus_db.controls.append(
                    ft.Container(
                        content=ft.Row([ft.Text(icon, size=20), ft.Text(f, color=color, weight="bold", expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)] + actions),
                        bgcolor="#21262D", padding=5, border_radius=5
                    )
                )
        except Exception as e:
            list_nexus_db.controls.append(ft.Text(f"Error DB: {e}"))
        page.update()

    def load_file(filepath):
        fn = os.path.basename(filepath)
        ext = fn.lower().split('.')[-1]
        if ext == "stl":
            is_valid, msg = validate_stl(filepath)
            if not is_valid:
                status.value = f"❌ {msg}"
                status.color = "#FF5252"
                page.update()
                return
            metrics = analyze_stl(filepath)
            if metrics:
                txt_dim_x.value = f"{metrics['dx']} mm"
                txt_dim_y.value = f"{metrics['dy']} mm"
                txt_dim_z.value = f"{metrics['dz']} mm"
                txt_vol.value = f"{metrics['vol_cm3']} cm³"
                txt_peso.value = f"{metrics['weight_g']} g"
            shutil.copy(filepath, os.path.join(EXPORT_DIR, "imported.stl"))
            tools_lib.lbl_stl_status.value = f"✓ Activo: {fn}"
            tools_lib.lbl_stl_status.color = "#00E676"
            select_tool("stl")
            set_tab(1)
            update_code_wrapper()
            status.value = f"✓ STL Inyectado en Memoria"
        elif ext == "jscad":
            with open(filepath) as f:
                txt_code.value = f.read()
            set_tab(0)
            status.value = "✓ Código Cargado"
        page.update()

    # --- Explorador Android ---
    current_android_dir = ANDROID_ROOT
    tf_path = ft.TextField(value=current_android_dir, expand=True, bgcolor="#161B22", height=40, text_size=12)
    list_android = ft.ListView(height=400, spacing=5)

    def nav_to(path):
        nonlocal current_android_dir
        current_android_dir = path
        refresh_explorer(path)

    def refresh_explorer(path):
        list_android.controls.clear()
        try:
            items = os.listdir(path)
            dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
            files = [f for f in items if os.path.isfile(os.path.join(path, f))]
            dirs.sort()
            files.sort()
            if path != "/" and path != "/storage" and path != "/storage/emulated":
                list_android.controls.append(
                    ft.Container(
                        content=ft.Row([ft.Text("⬆️", size=20), ft.Text(".. (Subir nivel)", color="white", expand=True)]),
                        bgcolor="#30363D", padding=5, border_radius=5,
                        on_click=lambda e: nav_to(os.path.dirname(path)), ink=True
                    )
                )
            for d in dirs:
                if not d.startswith('.'):
                    list_android.controls.append(
                        ft.Container(
                            content=ft.Row([ft.Text("📁", size=20), ft.Text(d, color="#E6EDF3", expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                                            custom_icon_btn("➡️", lambda e, p=os.path.join(path, d): nav_to(p), "Entrar")]),
                            bgcolor="#161B22", padding=5, border_radius=5,
                            on_click=lambda e, p=os.path.join(path, d): nav_to(p), ink=True
                        )
                    )
            for f in files:
                ext = f.lower().split('.')[-1] if '.' in f else ''
                icon = "📄"
                color = "#8B949E"
                if ext == "stl":
                    icon = "🧊"; color = "#00E676"
                elif ext == "jscad":
                    icon = "🧩"; color = "#00E5FF"
                elif ext == "png":
                    icon = "🖼️"; color = "#C51162"
                p = os.path.join(path, f)
                actions = [
                    custom_icon_btn("▶️", lambda e, fp=p: file_action(fp), "Cargar directamente"),
                    custom_icon_btn("📥", lambda e, fp=p, fn=f: copy_to_db(e, fp, fn), "Importar archivo a la DB")
                ]
                list_android.controls.append(
                    ft.Container(
                        content=ft.Row([ft.Text(icon, size=20), ft.Text(f, color=color, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(f"{os.path.getsize(p) // 1024} KB", size=10, color="#8B949E")] + actions),
                        bgcolor="#21262D", padding=5, border_radius=5
                    )
                )
        except PermissionError:
            list_android.controls.append(ft.Text("❌ Permiso Denegado.", color="red", weight="bold"))
        except Exception as ex:
            list_android.controls.append(ft.Text(f"Error: {ex}", color="red"))
        tf_path.value = path
        page.update()

    def file_action(filepath):
        ext = filepath.lower().split('.')[-1] if '.' in filepath else ''
        if ext in ["stl", "jscad"]:
            load_file(filepath)
        else:
            status.value = f"⚠️ Formato .{ext} no soportado."
            status.color = "#FFAB00"
            page.update()

    def copy_to_db(e, filepath, filename):
        try:
            shutil.copy(filepath, os.path.join(EXPORT_DIR, filename))
            status.value = f"✓ {filename} importado a NEXUS DB."
            status.color = "#00E676"
            refresh_nexus_db()
        except Exception as ex:
            status.value = f"❌ Error importando: {ex}"
            status.color = "red"
        page.update()

    def save_to_android(e):
        if not os.path.isdir(current_android_dir):
            return
        fname = f"nexus_{int(time.time())}.jscad"
        try:
            with open(os.path.join(current_android_dir, fname), "w") as f:
                f.write(txt_code.value)
            status.value = f"✓ Guardado en Android: {fname}"
            status.color = "#00E676"
            refresh_explorer(current_android_dir)
        except Exception as ex:
            status.value = f"❌ Error guardando: {ex}"
            status.color = "red"
        page.update()

    row_quick_paths = ft.Row([
        ft.ElevatedButton("🏠 Android", on_click=lambda _: nav_to("/storage/emulated/0"), bgcolor="#21262D", color="white"),
        ft.ElevatedButton("📥 Descargas", on_click=lambda _: nav_to("/storage/emulated/0/Download"), bgcolor="#21262D", color="white"),
        ft.ElevatedButton("📁 Nexus DB", on_click=lambda _: nav_to(EXPORT_DIR), bgcolor="#1B5E20", color="white")
    ], scroll="auto")

    # --- Ensamblaje ---
    col_assembly_cards = build_static_assembly_cards()
    lbl_ensamble_warn = ft.Text("⚠️ DB de STLs vacía.\nVe a la pestaña FILES y sube o guarda STLs primero.", color="#FFAB00", weight="bold", visible=False)
    col_assembly = ft.Column([lbl_ensamble_warn] + col_assembly_cards, scroll="auto", expand=True)

    def build_static_assembly_cards():
        cards = []
        for i in range(MAX_ASSEMBLY_PARTS):
            df = ft.Dropdown(options=[], width=160, text_size=12, bgcolor="#0B0E14", color="#00E5FF")
            dm = ft.Dropdown(
                options=[ft.dropdown.Option("pla"), ft.dropdown.Option("petg"), ft.dropdown.Option("carbon"),
                         ft.dropdown.Option("glass"), ft.dropdown.Option("aluminum"), ft.dropdown.Option("copper"),
                         ft.dropdown.Option("wood"), ft.dropdown.Option("gold")],
                value="pla", width=100, text_size=12, bgcolor="#0B0E14"
            )
            sl_x = ft.Slider(min=-200, max=200, value=0, expand=True)
            sl_y = ft.Slider(min=-200, max=200, value=0, expand=True)
            sl_z = ft.Slider(min=-200, max=200, value=0, expand=True)
            card = ft.Container(bgcolor="#161B22", padding=10, border_radius=8, border=ft.border.all(1, "#C51162"), visible=False)
            def make_change_handler(idx, d_f, d_m, s_x, s_y, s_z):
                def handler(e):
                    if not state.assembly_parts_state[idx]["active"]:
                        return
                    state.assembly_parts_state[idx]["file"] = d_f.value
                    state.assembly_parts_state[idx]["mat"] = d_m.value
                    state.assembly_parts_state[idx]["x"] = s_x.value
                    state.assembly_parts_state[idx]["y"] = s_y.value
                    state.assembly_parts_state[idx]["z"] = s_z.value
                    state.update_pbr_state()
                return handler
            change_handler = make_change_handler(i, df, dm, sl_x, sl_y, sl_z)
            df.on_change = change_handler
            dm.on_change = change_handler
            sl_x.on_change = change_handler
            sl_y.on_change = change_handler
            sl_z.on_change = change_handler
            def make_delete_handler(idx, c):
                def handler(e):
                    state.assembly_parts_state[idx]["active"] = False
                    c.visible = False
                    state.update_pbr_state()
                    check_empty_assembly()
                    page.update()
                return handler
            btn_del = ft.Container(content=ft.Text("🗑️", size=16), padding=5, bgcolor="#30363D", border_radius=5,
                                   on_click=make_delete_handler(i, card), ink=True)
            card.content = ft.Column([
                ft.Row([df, dm, btn_del], alignment="spaceBetween"),
                ft.Row([ft.Text("X", size=10, color="#8B949E", width=15), sl_x]),
                ft.Row([ft.Text("Y", size=10, color="#8B949E", width=15), sl_y]),
                ft.Row([ft.Text("Z", size=10, color="#8B949E", width=15), sl_z])
            ])
            def refresh_opts(d=df, idx=i):
                files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
                d.options = [ft.dropdown.Option(f) for f in files]
                if not d.value and files:
                    d.value = files[0]
                elif d.value not in files and files:
                    d.value = files[0]
                if files:
                    state.assembly_parts_state[idx]["file"] = d.value
            card.data = {"refresh": refresh_opts, "df": df, "dm": dm, "sx": sl_x, "sy": sl_y, "sz": sl_z}
            cards.append(card)
        return cards

    def check_empty_assembly():
        has_active = any(p["active"] for p in state.assembly_parts_state)
        files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
        lbl_ensamble_warn.visible = not has_active and not files

    def add_assembly_part(e):
        files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
        if not files:
            status.value = "❌ No hay STLs para añadir. Sube archivos en la pestaña FILES."
            status.color = "#FF5252"
            page.update()
            return
        for i in range(MAX_ASSEMBLY_PARTS):
            if not state.assembly_parts_state[i]["active"]:
                state.assembly_parts_state[i]["active"] = True
                card = col_assembly_cards[i]
                card.data["refresh"]()
                card.data["sx"].value = 0
                card.data["sy"].value = 0
                card.data["sz"].value = 0
                state.assembly_parts_state[i]["x"] = 0
                state.assembly_parts_state[i]["y"] = 0
                state.assembly_parts_state[i]["z"] = 0
                state.assembly_parts_state[i]["mat"] = card.data["dm"].value
                card.visible = True
                state.update_pbr_state()
                check_empty_assembly()
                page.update()
                return
        status.value = "❌ Límite máximo de piezas (10) alcanzado."
        status.color = "#FFAB00"
        page.update()

    def render_assembly_ui():
        files = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith('.stl') and f != "imported.stl"]
        if not files:
            lbl_ensamble_warn.visible = True
            for i in range(MAX_ASSEMBLY_PARTS):
                col_assembly_cards[i].visible = False
                state.assembly_parts_state[i]["active"] = False
        else:
            lbl_ensamble_warn.visible = not any(p["active"] for p in state.assembly_parts_state)
            for i, card in enumerate(col_assembly_cards):
                if state.assembly_parts_state[i]["active"]:
                    card.data["refresh"]()

    # --- Construir UI principal ---
    nav_bar, main_container, tabs = build_main_ui(
        page, status, txt_code, tools_lib, panel_globales, hw_panel,
        panel_calibre, list_nexus_db, tf_path, list_android, row_quick_paths,
        col_assembly, lbl_ensamble_warn,
        set_tab, clear_editor, run_render, add_assembly_part,
        refresh_nexus_db, nav_to, save_to_android,
        state.internal_ip, state.local_port
    )

    page.add(
        ft.Container(
            content=ft.Column([nav_bar, main_container, status], expand=True),
            padding=ft.padding.only(top=45, left=5, right=5, bottom=5),
            expand=True
        )
    )

    select_tool("planetario")
    refresh_explorer(current_android_dir)

if __name__ == "__main__":
    if "TERMUX_VERSION" in os.environ:
        ft.app(target=main, port=0, view=ft.AppView.WEB_BROWSER)
    else:
        ft.app(target=main)
