# 🌌 NEXUS CAD TITAN PRO & AI CORE (v21.2)

![Versión](https://img.shields.io/badge/Versi%C3%B3n-21.2_TITAN_PRO-00E676?style=for-the-badge)
![Plataforma](https://img.shields.io/badge/Plataforma-Android_%7C_Windows_%7C_Web-00B0FF?style=for-the-badge)
![Tecnologías](https://img.shields.io/badge/Stack-Python_%7C_Flet_%7C_Three.js_%7C_CSG-B388FF?style=for-the-badge)
![IA](https://img.shields.io/badge/AI_Engine-Gemini_Flash_%7C_Groq_GPT--OSS-FFAB00?style=for-the-badge)

<p align="center">
  <img src="docs/screenshots/menu_principal.jpg" alt="Menú Principal Nexus CAD" width="400"/>
</p>

NEXUS CAD TITAN PRO es un ecosistema completo de diseño 3D paramétrico, edición avanzada de archivos STL, renderizado físico (PBR) y asistencia por Inteligencia Artificial (Doble Agente), diseñado para ejecutarse de forma nativa en dispositivos móviles (vía Termux/Android) y PC.

La interfaz está diseñada bajo una **Arquitectura de 3 Pilares** (`🧠 STUDIO`, `👁️ VER 3D` y `🏭 LAB`), permitiendo un flujo de trabajo sin fricciones desde la idea inicial hasta la configuración para impresión 3D.

---

## ✨ ¿Qué hace la aplicación? (Arquitectura 3 Pilares)

### 🧠 PILAR 1: STUDIO (Creación y AI Core)

<p align="center">
  <img src="docs/screenshots/agente_ia_01.jpg" alt="Nexus AI Core" width="250"/>
  <img src="docs/screenshots/agente_ia_02.jpg" alt="Asistencia Iterativa" width="250"/>
  <img src="docs/screenshots/agente_ia_03.jpg" alt="Vision to Print" width="250"/>
</p>

* **🤖 Nexus AI Core v23.26 (Doble Agente):** Integración con LLMs (Gemini 3.1 Flash Lite y Groq GPT-OSS 120B). Un agente "Arquitecto" estructura JSON técnicos, y un "Compilador" los traduce a código `CSG.js` con un puente de auto-reparación de errores (Anti-Z-Fighting y Anti-Flip).
* **👁️ Vision-to-Print (Ingeniería Inversa):** Sube una foto de una pieza rota o un plano, y la IA deducirá las instrucciones paramétricas para clonarla limitándola a un Bounding Box exacto.
* **🧬 Macros Generativas:** Aplica funciones complejas con un clic como *Generative Lattice* (Optimización topológica) o Vaciados (*Shell*).
* **🎛️ Generadores Paramétricos (Sliders):** Módulos pre-programados listos para usar: Engranajes (Evolvente, Cónico, Planetario), cajas multicuerpo, perfiles NACA, drones, planetarios cinemáticos y mucho más.
* **💻 Motor de Código JS-CSG:** Modelado 3D paramétrico impulsado por *Constructive Solid Geometry*.
* **🔥 Sistema Hot Reload:** Recarga en caliente del código base (`importlib`) que permite diseñar nuevas herramientas paramétricas sin reiniciar la app.

### 👁️ PILAR 2: VER 3D (Titan Space Engine)

<p align="center">
  <img src="docs/screenshots/visor_pbr.jpg" alt="Renderizado PBR 3D" width="400"/>
</p>

* **🚀 WebWorkers Asíncronos:** Las operaciones booleanas complejas se calculan en hilos secundarios para no congelar la UI jamás, permitiendo un renderizado asíncrono ultra-rápido.
* **🌐 Visor Externo y LAN:** Enrutamiento HTTP automático para visualizar tu diseño 3D en tiempo real desde cualquier monitor o PC conectado a la misma red WiFi.
* **🎨 PBR Studio PRO:** Motor fotorealista basado en materiales reales (PLA, Fibra de Carbono, Aluminio) con físicas de colisión para organizar piezas.
* **⚔️ ULTIMATE STL FORGE:** Edición y modificación de archivos STL masivos (Aplanar, Cortar, Taladrar, Añadir Orejetas, Mouse Ears, Honeycomb, Prop-Guards, etc.).

### 🏭 PILAR 3: LABORATORIO (Gestión y Ensamblaje)

<p align="center">
  <img src="docs/screenshots/solar.jpg" alt="Mesa de Ensamblaje" width="400"/>
</p>

* **☁️ Nexus DB (Supabase Cloud):** Guarda tus mejores "recetas" (prompts + código) en la base de datos en la nube. Explora tu biblioteca personal mediante un modal flotante e inyecta piezas con un clic.
* **🧩 Mesa de Ensamblaje:** Combina hasta 10 archivos STL distintos en un único entorno espacial, asignando materiales independientes a cada pieza para prototipos mecánicos complejos.
* **📐 Calibre 3D Inteligente:** Calcula en tiempo real las dimensiones (X, Y, Z), el volumen (cm³) y estima el peso en gramos antes de imprimir.
* **⚙️ Agentic UI Slicer:** La IA es capaz de analizar tu diseño y auto-configurar los parámetros de impresión G-Code (Temperatura, Velocidad y Relleno) en un panel dedicado.
* **📂 Explorador Nativo Integrado:** Navega por tu almacenamiento Android para cargar código o STLs directamente desde tus carpetas locales.

---

## 🛠️ ¿Cómo funciona bajo el capó?

El sistema tiene una arquitectura híbrida cliente/servidor corriendo localmente:
1. **Frontend (UI) y Backend:** Creado íntegramente en Python usando **Flet**, que proporciona una interfaz nativa. El script principal levanta un servidor HTTP asíncrono (`http.server` en el puerto 8556).
2. **Motor de Renderizado:** La UI de Flet incrusta WebViews (`ft.WebView`) que cargan archivos HTML estáticos (`openscad_engine.html`, `pbr_studio.html`, `upload_ui.html`).
3. **Comunicación (El Puente):** Python expone endpoints (`/api/get_code_b64.json`, `/api/upload_raw`) que los WebViews consultan periódicamente (Polling) o envían vía Fetch API.
4. **Cálculo Matemático:** Las operaciones booleanas intensivas se delegan al navegador interno (V8 Engine) utilizando `CSG.js` y se renderizan usando `Three.js`, manteniendo la app en Python siempre fluida.

--
