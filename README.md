

# 🌌 NEXUS CAD TITAN AI (v21.2)

![Versión](https://img.shields.io/badge/Versi%C3%B3n-21.2_TITAN_AI-00E676?style=for-the-badge)
![Plataforma](https://img.shields.io/badge/Plataforma-Android_%7C_Windows_%7C_Web-00B0FF?style=for-the-badge)
![Tecnologías](https://img.shields.io/badge/Stack-Python_%7C_Flet_%7C_Three.js_%7C_CSG-B388FF?style=for-the-badge)

NEXUS CAD TITAN AI es un ecosistema completo de diseño 3D paramétrico, edición avanzada de archivos STL, renderizado físico (PBR) y asistencia por Inteligencia Artificial, diseñado para ejecutarse de forma nativa en dispositivos móviles (vía Termux/Android) y PC.

---

## ✨ ¿Qué hace la aplicación?

* **💻 Motor de Código JS-CSG:** Modelado 3D paramétrico impulsado por *Constructive Solid Geometry*. Renderizado asíncrono ultra-rápido mediante Web Workers.
* **⚔️ ULTIMATE STL FORGE:** Edición y modificación de archivos STL masivos (Aplanar, Cortar, Taladrar, Añadir Orejetas, Mouse Ears, Honeycomb, Prop-Guards, etc.).
* **🧩 Generadores Paramétricos:** Módulos pre-programados listos para usar: Engranajes, cajas multicuerpo, perfiles NACA, drones, planetarios cinemáticos y mucho más.
* **🎨 PBR Studio PRO:** Motor fotorealista basado en materiales reales (PLA, Fibra de Carbono, Aluminio) con físicas de colisión para organizar piezas.
* **🔥 Sistema Hot Reload:** Recarga en caliente del código base (`importlib`) que permite diseñar nuevas herramientas paramétricas sin reiniciar la app.
* **🤖 Asistente IA (Gemini):** Integración directa con LLMs para generar código de piezas complejas con prompts de lenguaje natural.

---

## 🛠️ ¿Cómo funciona bajo el capó?

El sistema tiene una arquitectura híbrida cliente/servidor corriendo localmente:
1. **Frontend (UI) y Backend:** Creado íntegramente en Python usando **Flet**, que proporciona una interfaz nativa. El script principal levanta un servidor HTTP asíncrono (`http.server` en el puerto 8556).
2. **Motor de Renderizado:** La UI de Flet incrusta WebViews (`ft.WebView`) que cargan archivos HTML estáticos (`openscad_engine.html`, `pbr_studio.html`).
3. **Comunicación (El Puente):** Python expone endpoints (`/api/get_code_b64.json`, `/api/upload_raw`) que los WebViews consultan periódicamente (Polling) o envían vía Fetch API.
4. **Cálculo Matemático:** Las operaciones booleanas intensivas se delegan al navegador interno (V8 Engine) utilizando `CSG.js` y se renderizan usando `Three.js`, manteniendo la app en Python siempre fluida.

---

## 📱 Replicar el Entorno en Termux (Otro Smartphone)

Sigue estos pasos en el nuevo dispositivo para tener el entorno de desarrollo y compilación exactamente igual.

### 1. Preparación Básica
Instala la app Termux desde F-Droid (no desde la Play Store). Ábrela y ejecuta:
```bash
# Actualizar repositorios
pkg update && pkg upgrade -y

# Instalar dependencias clave
pkg install python git nano openssh -y

# Dar permisos de almacenamiento a Termux
termux-setup-storage

```
### 2. Clonar Proyecto y Entorno Virtual
```bash
# Clonar el repositorio
git clone https://github.com/txurtxil/Nexus-CAD-App ~/nexus_app

# Crear y activar entorno virtual
export ANDROID_API_LEVEL=24
pip install pydantic-core
pkg update
pkg install python-psutil python-pydantic clang rust -y

cd ~/nexus_app
python -m venv venv
source venv/bin/activate

# Instalar librerías de Python
pip install flet flet-web

# Probamos que ha ido bien la instalación 

python -c "import flet; import psutil; print('🚀 Success! Components loaded.')"

```
### 3. Configurar Alias y Atajos de Desarrollo Senior
Vamos a inyectar tus comandos personalizados para que programar desde el móvil sea ultrarrápido.
Abre el archivo de configuración de Bash:
```bash
nano ~/.bashrc

```
Pega el siguiente bloque completo al final del archivo:
```bash
# ==========================================
# NEXUS CAD: ATAJOS DE DESARROLLO SENIOR
# ==========================================

# --- ATAJOS DE NAVEGACIÓN Y LISTADO ---
alias c='clear'
alias ..='cd ..'
alias ...='cd ../..'
alias l='ls -CF'
alias ll='ls -lh'
alias la='ls -A'
alias lla='ls -la'

# --- HERRAMIENTAS DE EDICIÓN ---
alias n='nano'
alias v='vim'
alias editar="nano ~/nexus_app/main.py"

# --- ATAJOS ESPECÍFICOS DE NEXUS CAD ---
alias nx='cd ~/nexus_app && source venv/bin/activate'
alias nexus='nx'
alias p='python main.py'
alias probar="p"
alias nxrun='nx && p'

# --- HERRAMIENTAS DE COMPILACIÓN (FLET) ---
alias apk='flet build apk'

# --- GESTIÓN DE MEMORIA Y LIMPIEZA ---
alias mfree='sync && history -c && pkill -9 python && clear && echo "[✓] Memoria RAM liberada y procesos antiguos cerrados."'
alias nxclean='rm -f ~/storage/downloads/Nexus-CAD-WASM-APK.zip && am start -a android.intent.action.DELETE -d package:com.flet.nexus_cad > /dev/null 2>&1 && echo "[✓] ZIP antiguo eliminado. Confirma la desinstalación en la pantalla emergente."'

# --- FUNCIÓN MÁGICA DE DESPLIEGUE ---
alias nxs='subir'
subir() {
    cd ~/nexus_app
    git add .
    # Si no le pasas mensaje, genera uno automático con la fecha
    if [ -z "$1" ]; then
        msg="⚡ Actualización rápida: $(date +'%Y-%m-%d %H:%M:%S')"
    else
        msg="$1"
    fi
    git commit -m "$msg"
    git push
    echo -e "\e[1;32m\n==============================================\e[0m"
    echo -e "\e[1;32m🚀 ¡CÓDIGO EN PRODUCCIÓN! \e[0m"
    echo -e "\e[1;32mGitHub Actions ya está compilando tu nuevo APK.\e[0m"
    echo -e "\e[1;32m==============================================\n\e[0m"
}

```
*Guarda pulsando Ctrl + O, Enter, y cierra con Ctrl + X.*
Aplica los cambios inmediatamente con:
```bash
source ~/.bashrc

```
¡Listo! Ya puedes escribir simplemente nxrun para lanzar el servidor y la app, o nxs "Tu mensaje" para subir cambios a GitHub automáticamente.
```


# 1. Limpiar caché
find . -type d -name "__pycache__" -exec rm -r {} +

# 2. Registrar v21.2 en GitHub
git add .
git commit -m "Nexus v21.2 TITAN AI - Actualizacion de README y despliegue de entorno Termux"
git push origin main


