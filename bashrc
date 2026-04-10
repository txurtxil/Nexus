alias p='python main.py'
alias apk='flet build apk'

# ==========================================
# NEXUS CAD: ATAJOS DE DESARROLLO SENIOR
# ==========================================

# Ir a la carpeta del proyecto instantáneamente
alias nexus="cd ~/nexus_app && source venv/bin/activate"

# Probar la app localmente en el puerto 8555
alias probar="python main.py"

# Abrir el editor Nano para retoques rápidos
alias editar="nano main.py"

# Función mágica para subir y compilar el APK con un solo comando
subir() {
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
alias nx='cd ~/nexus_app && source venv/bin/activate'

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

# --- ATAJOS ESPECÍFICOS DE NEXUS CAD ---
alias nx='cd ~/nexus_app && source venv/bin/activate'
alias nxrun='nx && python main.py'
alias nxs='subir'

# --- GESTIÓN DE MEMORIA (EL COMANDO QUE PEDISTE) ---
alias mfree='sync && history -c && pkill -9 python && clear && echo "Memoria RAM liberada y procesos antiguos cerrados."'
alias nxclean="rm -f ~/storage/downloads/Nexus-CAD-WASM-APK.zip && am start -a android.intent.action.DELETE -d package:com.flet.nexus_cad > /dev/null 2>&1 && echo \"[✓] ZIP antiguo eliminado. Confirma la desinstalación en la pantalla emergente.\""
