# 🌌 NEXUS CAD TITAN PRO (v20.73.6)

![Versión](https://img.shields.io/badge/Versi%C3%B3n-20.73.6_TITAN_PRO-00E676?style=for-the-badge)
![Plataforma](https://img.shields.io/badge/Plataforma-Android_%7C_Windows_%7C_Web-00B0FF?style=for-the-badge)
![Tecnologías](https://img.shields.io/badge/Stack-Python_%7C_Flet_%7C_Three.js_%7C_CSG-B388FF?style=for-the-badge)

NEXUS CAD TITAN PRO es un ecosistema completo de diseño 3D paramétrico, edición avanzada de archivos STL, renderizado físico (PBR) y asistencia por Inteligencia Artificial, diseñado para ejecutarse de forma nativa en dispositivos móviles (vía Termux/Android) y PC.

## ✨ Características Principales

* **💻 Motor de Código JS-CSG:** Modelado 3D paramétrico impulsado por *Constructive Solid Geometry*. Renderizado asíncrono ultra-rápido mediante Web Workers para no bloquear la interfaz.
* **⚔️ ULTIMATE STL FORGE:** No solo creas de cero; puedes importar STLs masivos y modificarlos (Aplanar, Cortar, Taladrar, Añadir Orejetas, Mouse Ears, Honeycomb, etc.).
* **🧩 Mesa de Ensamblaje:** Combina y posiciona hasta 10 archivos STL diferentes para visualizar mecanismos completos.
* **🎨 PBR Studio PRO:** Motor fotorealista basado en Three.js con materiales avanzados (Fibra de Carbono, Cristal Oscuro, Cobre Oxidado, Oro, PETG, etc.), iluminación dinámica y controles de transformación manual en tiempo real.
* **🌐 Inyector Web Optimizado:** Interfaz web local para subir archivos STL gigantescos desde otros dispositivos de la red usando transmisión binaria en bruto (`ArrayBuffer` a `Chunks` de 8KB en Python) para proteger la RAM del dispositivo.
* **🤖 Agente IA Autónomo:** Integración con modelos de IA para generar código JS-CSG a partir de texto e inyectarlo automáticamente en el editor de la app.
* **📱 Explorador Nativo:** Navegación por el sistema de archivos de Android para importar modelos 3D y exportar directamente a la carpeta de *Descargas*.

---

## 🚀 El Potencial del Motor JS-CSG (Ejemplo)

El corazón de NEXUS es su motor de renderizado paramétrico. En lugar de pesados softwares de escritorio, puedes generar geometría compleja y operaciones booleanas mediante código JavaScript simple.

Copia este código en la pestaña **CODE** de NEXUS para ver la potencia del motor generando una **Carcasa de Electrónica Paramétrica con rejilla de ventilación** generada matemáticamente al instante:

```javascript
function main() {
  // Parámetros globales de la caja
  var width = 80; var length = 100; var height = 30; var thickness = 2;
  
  // 1. Crear el bloque exterior
  var outerBox = CSG.cube({radius: [width/2, length/2, height/2]});
  
  // 2. Crear el bloque interior para el vaciado (hollow)
  var innerBox = CSG.cube({radius: [width/2 - thickness, length/2 - thickness, height/2 - thickness]});
  innerBox = UTILS.trans(innerBox, [0, 0, thickness]); // Subir el hueco para dejar suelo
  
  // 3. Vaciado principal (Operación Booleana)
  var shell = outerBox.subtract(innerBox);
  
  // 4. Generar rejilla de ventilación superior mediante bucles
  var ventHoles = [];
  for(var i = -width/2 + 10; i <= width/2 - 10; i += 8) {
      var hole = CSG.cylinder({start: [i, -length/2 + 10, height/2 - 5], end: [i, length/2 - 10, height/2 + 5], radius: 2});
      ventHoles.push(hole);
  }
  
  // 5. Restar todos los agujeros de ventilación a la carcasa
  for(var j = 0; j < ventHoles.length; j++) {
      shell = shell.subtract(ventHoles[j]);
  }
  
  // Aplicar material global y retornar
  return UTILS.mat(shell);
}
