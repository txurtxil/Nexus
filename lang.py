# lang.py

translations = {
    "en": {
        "app_title": "NEXUS v1.0 | 3-Pillar Integrated Environment",
        "nav_studio": "🧠 STUDIO",
        "nav_view": "👁️ VIEW 3D",
        "nav_lab": "🏭 LAB",
        "btn_ia": "🤖 AI",
        "btn_sliders": "🎛️ SLIDERS",
        "btn_code": "💻 CODE",
        "btn_3d": "📐 FAST 3D",
        "btn_pbr": "🎨 PBR STUDIO",
        "btn_db": "📂 DB MANAGER",
        "btn_assemble": "🧩 ASSEMBLE",
        "btn_info": "ℹ️ INFO",
        "btn_lang": "🇬🇧 EN",
        
        # Tools
        "t_custom": "Free Code", "t_texto": "Text Plates", "t_vr": "VR Pedestal", 
        "t_sketch": "2D Sketch", "t_stl": "Base Hybrid", "t_flat": "Flatten", 
        "t_split": "Split XYZ", "t_crop": "Crop Box", "t_drill": "3D Drill", 
        "t_mount": "Mounts", "t_ears": "Mouse Ears", "t_patch": "Patch Block", 
        "t_honey": "Honeycomb", "t_prop": "Prop Guard", "t_stand": "Mobile Stand", 
        "t_clip": "Cable Clip", "t_laser": "Laser Profile", "t_grid": "Grid Matrix", 
        "t_polar": "Polar Matrix", "t_loft": "Loft Adapter", "t_panal": "Hex Comb", 
        "t_voronoi": "Voronoi", "t_evol": "Involute Gear", "t_rack": "Gear Rack", 
        "t_bevel": "Bevel Gear", "t_box": "Box+Lid", "t_star": "2D Star", 
        "t_rev": "Revolution", "t_naca": "NACA Foil", "t_helice": "Propeller", 
        "t_pipe": "Curved Pipe", "t_dronf": "Drone Frame", "t_dronp": "Drone Prop", 
        "t_solar": "Solar Sys", "t_earth": "Earth", "t_station": "Station", 
        "t_spring": "Spring", "t_joint": "Ball Joint", "t_planet": "Planetary", 
        "t_pulley": "Pulley", "t_bearing": "Bearing", "t_acme": "ACME Thread", 
        "t_case": "Smart Case", "t_screw": "Screws", "t_clamp": "Tube Clamp", 
        "t_pcb": "PCB Box", "t_hinge": "Hinge", "t_vslot": "V-Slot", 
        "t_cube": "Cube G", "t_cyl": "Cylinder G", "t_angle": "Angle L", "t_gear": "SQ Pinion"
    },
    "es": {
        "app_title": "NEXUS v1.0 | Entorno Integrado 3 Pilares",
        "nav_studio": "🧠 STUDIO",
        "nav_view": "👁️ VER 3D",
        "nav_lab": "🏭 LAB",
        "btn_ia": "🤖 IA",
        "btn_sliders": "🎛️ SLIDERS",
        "btn_code": "💻 CODE",
        "btn_3d": "📐 3D RÁPIDO",
        "btn_pbr": "🎨 PBR STUDIO",
        "btn_db": "📂 GESTOR DB",
        "btn_assemble": "🧩 ENSAMBLAR",
        "btn_info": "ℹ️ INFO",
        "btn_lang": "🇪🇸 ES",
        
        # Tools
        "t_custom": "Código Libre", "t_texto": "Placas Texto", "t_vr": "Pedestal VR", 
        "t_sketch": "Sketch 2D", "t_stl": "Híbrido Base", "t_flat": "Flatten", 
        "t_split": "Split XYZ", "t_crop": "Crop Box", "t_drill": "Taladro 3D", 
        "t_mount": "Orejetas", "t_ears": "Mouse Ears", "t_patch": "Bloque Ref", 
        "t_honey": "Honeycomb", "t_prop": "Prop Guard", "t_stand": "Stand Móvil", 
        "t_clip": "Clip Cables", "t_laser": "Perfil Láser", "t_grid": "Matriz Grid", 
        "t_polar": "Matriz Polar", "t_loft": "Adap. Loft", "t_panal": "Panal Hex", 
        "t_voronoi": "Voronoi", "t_evol": "Evolvente", "t_rack": "Cremallera", 
        "t_bevel": "Cónico", "t_box": "Caja+Tapa", "t_star": "Estrella 2D", 
        "t_rev": "Revolución", "t_naca": "Perfil NACA", "t_helice": "Hélice", 
        "t_pipe": "Tubo Curvo", "t_dronf": "Dron Frame", "t_dronp": "Dron Prop", 
        "t_solar": "S. Solar", "t_earth": "Tierra", "t_station": "Estación", 
        "t_spring": "Muelle", "t_joint": "Rótula", "t_planet": "Planetario", 
        "t_pulley": "Polea", "t_bearing": "Rodamiento", "t_acme": "Eje ACME", 
        "t_case": "Carcasa", "t_screw": "Tornillos", "t_clamp": "Abrazadera", 
        "t_pcb": "Caja PCB", "t_hinge": "Bisagra", "t_vslot": "V-Slot", 
        "t_cube": "Cubo G", "t_cyl": "Cilindro G", "t_angle": "Escuadra", "t_gear": "Piñón SQ"
    }
}

current_lang = "en"

def t(key):
    global current_lang
    return translations.get(current_lang, {}).get(key, f"[{key}]")

def switch_lang():
    global current_lang
    current_lang = "es" if current_lang == "en" else "en"
