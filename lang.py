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
        "btn_lang": "🇬🇧 EN"
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
        "btn_lang": "🇪🇸 ES" 
    }
}

current_lang = "en"

def t(key):
    global current_lang
    return translations.get(current_lang, {}).get(key, f"[{key}]")

def switch_lang():
    global current_lang
    current_lang = "es" if current_lang == "en" else "en"
