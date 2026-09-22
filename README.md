# Mamatlatolli

Prototipo de escritorio para **reconocer Lengua de Señas Mexicana (LSM)** a partir de la cámara del equipo.

**Mamatlatolli** abre un menú principal de tarjetas: reconocimiento en vivo (letras estáticas y con movimiento), captura de plantillas, biblioteca, configuración y modo demostración.

El menú usa un fondo claro y acentos tríadicos (**naranja**, **lima** e **índigo**). El logo oficial vive en `assets/logo.png` (PNG transparente) y se muestra centrado arriba. Si ese archivo no está, el menú usa un marco placeholder.

> Proyecto estudiantil — Instituto Tecnológico de San Juan del Río.

## ¿Qué hace hoy? (fase 2b)

1. Arranca en un **menú** de tarjetas en español: *Iniciar reconocimiento*, *Capturar plantillas*, *Biblioteca de señas*, *Configuración*, *Modo demostración*, *Acerca de Mamatlatolli*. El logo (o su placeholder) va centrado arriba.
2. Detecta hasta dos manos (MediaPipe) y dibuja landmarks, conexiones y un recuadro.
3. Compara una pose quieta con **plantillas estáticas** (vectores de landmarks normalizados).
4. Si la mano se mueve con claridad ~0,4–0,8 s —o si mantienes **Seña con movimiento** / **Space**— compara la **trayectoria** con plantillas dinámicas mediante **DTW**.
5. Aplica un **filtro de estabilidad** antes de comprometer una letra (las dinámicas se confirman al terminar el gesto, no en cada fotograma).
6. Permite **organizar** el banco de señas (captura estática o dinámica, listar, borrar). Eso no es una segunda app de reconocimiento diario.

Aún **no** usa cuerpo ni rostro (`pose` y `rostro` van en `null`). El vocabulario de palabras completas llega después.

Detalle del menú, la captura dinámica y el enrutado automático vs botón: [`docs/menu-y-senas-dinamicas.md`](docs/menu-y-senas-dinamicas.md). Esquema JSON: [`docs/esquema-datos.md`](docs/esquema-datos.md).

## Requisitos

- Python 3.10, 3.11 o 3.12
- Una cámara web (o el modo demostración, si solo quieres ver la interfaz)
- Windows, macOS o Linux

Se recomienda un entorno virtual para no mezclar librerías con otras materias o proyectos.

## Instalación

En la carpeta del repositorio:

```bash
python -m venv .venv
```

Activa el entorno:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

Instala las dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

En Linux puede hacer falta el soporte de Tk:

```bash
sudo apt install python3-tk
```

## Cómo ejecutarlo

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
python app.py
```

La ventana abre en el **menú de Mamatlatolli**. También funciona:

```bash
python -m innova
```

### Si no hay cámara (o quieres ensayar la interfaz)

```bash
python app.py --demo
```

Sigue apareciendo el menú; *Iniciar reconocimiento* y *Modo demostración* usan un video sintético. Sirve para practicar la captura y ver el filtro, pero no sustituye a una seña real.

### Otra cámara

```bash
python app.py --camara 1
```

## Cómo capturar plantillas

El reconocedor **no** descarga conjuntos enormes ni entrena una red. Tú (o quien seña, con su consentimiento) guardas ejemplos.

### Estática (A, B, C…)

1. Menú → **Capturar plantillas** → tipo **Estática**.
2. Coloca la seña quieta, con la mano bien visible.
3. Escribe la letra y pulsa **Guardar pose actual**.

### Dinámica (J, Ñ, Z…)

1. Menú → **Capturar plantillas** → tipo **Dinámica**.
2. Escribe la etiqueta.
3. Pulsa **Seña con movimiento** (o mantén **Space**), haz el gesto y suelta.
4. El archivo lleva `tipo: dinamico` y `secuencia` con los fotogramas (`pose` / `rostro` = `null`).

Recomendaciones:

- Varias plantillas por letra (distancia, giro, luz).
- Solo con **consentimiento** (`metadatos.consentimiento`).
- Los JSON de `datos/plantillas/` no se suben al git.

## Cómo funciona el reconocimiento

1. **Landmarks.** MediaPipe Hands entrega 21 puntos (x, y, z) por mano.
2. **Enrutado.** Si la muñeca se mueve con claridad en una ventana de ~0,6 s (0,4–0,8 s), se trata como seña dinámica. Si está estable, como estática. El botón *Seña con movimiento* o Space fuerza el modo dinámico.
3. **Estático.** Se normaliza (muñeca al origen, palma ≈ 1, sin rotar), se arma un vector de 78 números y se compara con plantillas `tipo: estatico` (euclidiana RMS o coseno).
4. **Dinámico (DTW).** Cada fotograma suma esa forma más la muñeca relativa al inicio del gesto (80 números). Dynamic Time Warping alinea la secuencia con las plantillas `tipo: dinamico`.
5. **Estabilidad.** Una letra estática solo se compromete con umbral + N consecutivos o M-de-K e histéresis. Una dinámica se compromete **al terminar** el gesto si la confianza basta; no se escribe un renglón por fotograma.
6. Si no hay acuerdo, la UI muestra `detectando…` (hay mano) o `—` (no hay mano).

## Teclas

| Tecla | Acción |
| --- | --- |
| `Esc` o `Q` | Cerrar Mamatlatolli (Q no cierra si estás escribiendo) |
| `Space` (mantener) | Grabar / reconocer una seña con movimiento |
| Botón *← Menú* | Volver al menú principal |
| Botón *Reintentar cámara* | Volver a buscar un dispositivo si no se encontró |
| Botón *Seña con movimiento* | Forzar grabación dinámica (clic para empezar y terminar) |

## Permisos de la cámara

Si la ventana indica que **no se encontró una cámara**, casi siempre es un permiso del sistema o un dispositivo ocupado por otra app (Zoom, Teams, el navegador, etc.).

- **Windows:** Configuración → Privacidad y seguridad → Cámara → permite el acceso para el escritorio / Python.
- **macOS:** Configuración del Sistema → Privacidad y seguridad → Cámara → activa el permiso para Terminal, VS Code o Python.
- **Linux:** verifica que tu usuario esté en el grupo `video` y que ninguna otra aplicación tenga el dispositivo `/dev/video0` bloqueado.

Cierra otras apps que usen la cámara e intenta de nuevo, o pulsa **Reintentar cámara**, o entra a **Modo demostración**.

## Estructura del código

```
app.py                     Punto de entrada
innova/
  tema.py                  Paleta tríadica (naranja / lima / índigo) y logo
  menu.py                  Destinos del menú (sin Tk)
  pantallas.py             Menú, reconocimiento, captura, biblioteca, ajustes
  ui.py                    Ventana (CustomTkinter) y navegación
  camara.py                Captura (cámara real o fuente demo)
  detector.py              MediaPipe Hands + detector de demostración
  esquema.py               JSON versionado: muestra estática / secuencia
  caracteristicas.py       Normalización, vector estático y vector dinámico
  dtw.py                   Dynamic Time Warping
  movimiento.py            Detector de movimiento (auto-DTW)
  ajustes.py               datos/config.json
  plantillas.py            Leer/escribir/borrar datos/plantillas/
  estabilidad.py           Umbral + voto temporal + histéresis
  reconocimiento.py        crear_reconocedor() / estático + predecir_dinamico()
  overlay.py               Landmarks, conexiones y recuadro
  pipeline.py              Une todo fotograma a fotograma
  config.py                Textos, tamaños y umbrales (colores reexportados de tema)
docs/esquema-datos.md      Esquema JSON (español)
docs/menu-y-senas-dinamicas.md  Menú, captura DTW, auto vs botón
datos/plantillas/          Plantillas JSON (locales, no se versionan)
assets/logo.png            Logo oficial (PNG transparente). Si falta, el menú usa un placeholder
```

## Hoja de ruta

### Fase 1

- [x] Ventana de escritorio y cámara en vivo
- [x] Detección de manos con overlay
- [x] Marcador de reconocimiento (`detectando…` / `—`)
- [x] Transcripción reciente
- [x] Mensaje claro si no hay cámara

### Fase 2a

- [x] Esquema JSON versionado (mano + pose/rostro reservados + secuencia)
- [x] Captura de plantillas estáticas
- [x] Matching por vectores normalizados (euclidiana / coseno)
- [x] Filtro de estabilidad (umbral, N consecutivos / M-de-K, histéresis)

### Fase 2b (esta versión)

- [x] Menú principal y pantallas (captura, biblioteca, configuración, demo, acerca de)
- [x] Captura de secuencias `tipo: dinamico`
- [x] `predecir_dinamico()` con DTW
- [x] Enrutado automático estático vs dinámico + botón/Space

### Vocabulario completo (después)

- Activar MediaPipe Pose y Face Mesh
- Llenar `pose` y `rostro` (hoy van en `null`)
- Palabras y frases que usan cuerpo, mirada y boca, no solo la mano

## Pruebas rápidas (sin ventana)

```bash
python -m unittest discover -s tests -v
```

## Solución de problemas

**`ModuleNotFoundError: No module named 'cv2'` (o `mediapipe`, `customtkinter`)**  
No está activado el entorno virtual o faltó `pip install -r requirements.txt`.

**La ventana no abre en Linux**  
Instala `python3-tk` y comprueba que hay un display gráfico.

**MediaPipe tarda la primera vez**  
Es normal: carga el modelo de manos. Los siguientes arranques son más rápidos.

**El video se ve al revés (como en un espejo)**  
Es intencional: la vista espejo se siente más natural, como una videollamada.

**Todo el tiempo aparece `detectando…`**  
Aún no hay plantillas, o la pose/trayectoria no se parece a ninguna. Captura otra vez. La *estimación instantánea* muestra qué plantilla va ganando.

**Las letras con movimiento no se reconocen**  
Tienen que existir plantillas **dinámicas**. En Capturar plantillas elige *Dinámica* y graba el gesto. Si el automático no dispara, usa *Seña con movimiento* o sube la sensibilidad en Configuración.

**Guardar plantilla dice que no hay mano / seña corta**  
Espera el overlay. En dinámicas, mantén el botón durante todo el gesto (mínimo ~6 fotogramas).

## Licencia y uso

Código de un prototipo académico. Úsalo para aprender; respeta la privacidad de las personas que aparezcan frente a la cámara y no guardes plantillas sin consentimiento.
