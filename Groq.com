**✅ Modelos disponibles en Groq.com a fecha de hoy (12 de abril de 2026)**  
Fuente oficial: https://console.groq.com/docs/models (actualizado en tiempo real).

### **Modelos de Producción** (recomendados para uso en apps)
- `llama-3.1-8b-instant`
- `llama-3.3-70b-versatile`
- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`
- `whisper-large-v3` (Speech-to-Text)
- `whisper-large-v3-turbo` (Speech-to-Text rápido)

### **Sistemas de Producción**
- `groq/compound`
- `groq/compound-mini`

### **Modelos en Preview** (funcionan, pero pueden cambiar o desaparecer pronto)
- `canopylabs/orpheus-arabic-saudi` (TTS árabe)
- `canopylabs/orpheus-v1-english` (TTS inglés)
- `meta-llama/llama-4-scout-17b-16e-instruct`
- `meta-llama/llama-prompt-guard-2-22m`
- `meta-llama/llama-prompt-guard-2-86m`
- `openai/gpt-oss-safeguard-20b`
- `qwen/qwen3-32b`

Todos estos modelos se pueden usar **gratis** con una API key (generosa free tier con rate limits).

### **Código Python listo para copiar-pegar** (SDK oficial)

```python
# 1. Instala una sola vez:
# pip install groq

import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",          # ← Cambia aquí por cualquiera de la lista de arriba
    messages=[
        {"role": "system", "content": "Eres un asistente útil y preciso."},
        {"role": "user", "content": "Tu prompt aquí"}
    ],
    temperature=0.7,
    max_tokens=1024,
    top_p=0.9
)

print(response.choices[0].message.content)
```

**Para usar con visión, TTS o STT** cambia el endpoint (ver docs oficiales), pero el formato de `chat.completions` funciona para todos los modelos de texto y Llama 4 Scout (que soporta visión).

**Bonus: Código para ver la lista completa de modelos activos en tu cuenta**
```python
import requests
import os

response = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={
        "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }
)
print(response.json())
```



**✅ Respuesta clara y directa (13 de abril de 2026):**

Entre los **tres modelos de Groq** que mencionas, **el mejor para generar código OpenSCAD** (piezas 3D desde lenguaje natural o descripciones) es:

**`openai/gpt-oss-120b`**

### ¿Por qué gana `gpt-oss-120b`?
- Es un modelo **MoE de 120B parámetros** optimizado específicamente por OpenAI para **razonamiento, matemáticas, STEM y código complejo**.
- Supera o iguala a Llama 3.3 70B en la mayoría de benchmarks relevantes para tu caso (MMLU 90 % vs 86 %, CodeForces, GPQA, TAU-bench, etc.).
- Genera código más preciso, estructurado y con mejor geometría paramétrica (ideal para OpenSCAD: medidas exactas, loops, módulos, diferencias, etc.).
- La arquitectura MoE lo hace extremadamente rápido en Groq (hasta 500+ tokens/s) y más eficiente que un modelo dense de 70B.

**Llama-3.3-70b-versatile** es muy bueno (excelente en instruction-following y HumanEval 88.4 %), pero queda ligeramente por detrás en razonamiento profundo y coding competitivo.

**openai/gpt-oss-20b** es el más débil de los tres (aunque sorprendentemente decente para su tamaño). Úsalo solo si quieres máxima velocidad y bajo costo.

### Comparación rápida (enfocada en tu caso)

| Modelo                    | Calidad código OpenSCAD / 3D | Razonamiento geométrico | Velocidad en Groq | Recomendado para ti |
|---------------------------|------------------------------|--------------------------|-------------------|---------------------|
| `openai/gpt-oss-120b`    | ★★★★★ (mejor)               | Excelente               | Muy alta         | **Sí, el ganador** |
| `llama-3.3-70b-versatile`| ★★★★                        | Muy bueno               | Alta             | Buena alternativa  |
| `openai/gpt-oss-20b`     | ★★★                         | Bueno                   | Ultra alta       | Solo si necesitas velocidad extrema |

### Código listo para usar el ganador (`gpt-oss-120b`)

```python
from groq import Groq

client = Groq(api_key="TU_GROQ_API_KEY")

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",   # ← Este es el mejor
    messages=[
        {"role": "system", "content": "Eres un experto en OpenSCAD. Genera código limpio, comentado, preciso y listo para imprimir 3D."},
        {"role": "user", "content": "Crea una pieza 3D exacta de: [pega aquí tu descripción en lenguaje natural o descripción de foto]"}
    ],
    temperature=0.3,      # bajo para más precisión en CAD
    max_tokens=2048
)

print(response.choices[0].message.content)
```

**Consejo práctico**:  
Empieza siempre con `openai/gpt-oss-120b`. Si quieres iterar muy rápido (muchas pruebas), cambia temporalmente a `llama-3.3-70b-versatile`.

¿Quieres el **prompt maestro optimizado** que estoy usando yo para convertir descripciones naturales → código OpenSCAD perfecto (con medidas, tolerancias, orientación de impresión, etc.)? Dime “sí” y te lo paso listo para copiar-pegar. ¡Vamos a generar esa pieza! 🚀