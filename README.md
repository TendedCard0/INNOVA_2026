# Mamatlatolli

Prototipo de escritorio para **reconocer Lengua de Señas Mexicana (LSM)** a partir de la cámara del equipo.

**Mamatlatolli** abre un menú principal de tarjetas: **Abecedario** (letras) y **Vocabulario** (palabras) por separado, más captura de plantillas, biblioteca, configuración y modo demostración.

El menú usa acentos tríadicos (**naranja**, **lima** e **índigo**) sobre fondo claro u oscuro. El logo oficial vive en `assets/logo.png` (PNG transparente) y se muestra centrado arriba. Si ese archivo no está, el menú usa un marco placeholder.

> Proyecto estudiantil — Instituto Tecnológico de San Juan del Río.

## ¿Qué hace hoy? (Abecedario y Vocabulario)

1. Arranca en un **menú** de tarjetas en español: *Abecedario*, *Vocabulario*, *Capturar plantillas*, *Biblioteca de señas*, *Configuración*, *Modo demostración*, *Acerca de Mamatlatolli*. El logo (o su placeholder) va centrado arriba.
2. Detecta hasta dos manos (MediaPipe Hands) y dibuja landmarks, conexiones y un recuadro.
3. **Abecedario** compara solo plantillas `categoria: "letra"` (solo manos). **Vocabulario** compara solo `categoria: "palabra"` y, además de la mano, usa **pose** (33 puntos) y **rostro** (malla facial). Si aún no hay palabras, muestra un estado vacío en español.
4. Compara una pose quieta con **plantillas estáticas** (vectores de landmarks normalizados). En palabras, la distancia mezcla mano, pose y rostro; si falta el cuerpo o la cara, esa parte se omite.
5. Si la mano se mueve con claridad ~0,4–0,8 s —o si mantienes **Seña con movimiento** / **Space**— compara la **trayectoria** con plantillas dinámicas de esa categoría mediante **DTW**. En palabras, cada fotograma de la secuencia puede llevar pose y rostro.
6. Aplica un **filtro de estabilidad** antes de comprometer una seña (las dinámicas se confirman al terminar el gesto, no en cada fotograma).
7. Permite **organizar** el banco (captura Letra/Palabra × estática/dinámica; biblioteca con filtro letra | palabra | todas).
8. En Vocabulario dibuja un esqueleto y puntos del rostro con los colores del tema (índigo, lima, naranja).

Abecedario deja `pose` y `rostro` en `null` para ir más ligero. Si MediaPipe Pose o Face Mesh no cargan, Vocabulario sigue reconociendo con la mano.

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

Sigue apareciendo el menú; *Abecedario*, *Vocabulario* y *Modo demostración* usan un video sintético. Sirve para practicar la captura y ver el filtro, pero no sustituye a una seña real.

### Otra cámara

```bash
python app.py --camara 1
```

## Cómo capturar plantillas

El reconocedor **no** descarga conjuntos enormes ni entrena una red. Tú (o quien seña, con su consentimiento) guardas ejemplos.

### Estática (A, B, C… o HOLA)

1. Menú → **Capturar plantillas** → categoría **Letra** o **Palabra** → tipo **Estática**.
2. Coloca la seña quieta, con la mano bien visible.
3. Escribe la etiqueta y pulsa **Guardar pose actual**. En **Palabra**, si la cámara ve a la persona, el JSON guarda también `pose` y `rostro`. En **Letra** esos campos quedan en `null`.

### Dinámica (J, Ñ, Z… o una palabra con movimiento)

1. Menú → **Capturar plantillas** → categoría **Letra** o **Palabra** → tipo **Dinámica**.
2. Escribe la etiqueta.
3. Pulsa **Seña con movimiento** (o mantén **Space**), haz el gesto y suelta.
4. El archivo lleva `categoria`, `tipo: dinamico` y `secuencia`. En **Palabra**, cada fotograma puede traer `pose` y `rostro`. En **Letra** siguen en `null`.

Recomendaciones:

- Varias plantillas por seña (distancia, giro, luz).
- Solo con **consentimiento** (`metadatos.consentimiento`).
- Los JSON de `datos/plantillas/` no se suben al git.

## Cómo funciona el reconocimiento

1. **Modo.** Abecedario carga solo `categoria: "letra"`; Vocabulario solo `"palabra"`.
2. **Landmarks.** MediaPipe Hands entrega 21 puntos (x, y, z) por mano. En Vocabulario, MediaPipe Pose entrega 33 puntos y Face Mesh 478 (`refine_landmarks=True`), con la misma versión del paquete (`mediapipe==0.10.14`, API `mp.solutions`).
3. **Enrutado.** Si la muñeca se mueve con claridad en una ventana de ~0,6 s (0,4–0,8 s), se trata como seña dinámica. Si está estable, como estática. El botón *Seña con movimiento* o Space fuerza el modo dinámico.
4. **Estático.** La mano se normaliza (muñeca al origen, palma ≈ 1, sin rotar) a un vector de 78 números. En palabras se suman la pose (caderas al origen, ancho de hombros ≈ 1) y un recorte del rostro (nariz al origen, distancia entre ojos ≈ 1: ojos, cejas y boca). Los pesos son mano 0,55, pose 0,30, rostro 0,15; si falta una parte, se reparte el peso entre las demás.
5. **Dinámico (DTW).** Cada fotograma de letra suma la forma más la muñeca relativa al inicio del gesto (80 números). En palabras el fotograma añade pose y rostro; los bloques ausentes no entran en la distancia. Dynamic Time Warping alinea la secuencia con las plantillas `tipo: dinamico` de esa categoría.
6. **Estabilidad.** Una seña estática solo se compromete con umbral + N consecutivos o M-de-K e histéresis. Una dinámica se compromete **al terminar** el gesto si la confianza basta; no se escribe un renglón por fotograma.
7. Si no hay acuerdo, la UI muestra `detectando…` (hay mano) o `—` (no hay mano).

## Teclas

| Tecla | Acción |
| --- | --- |
| `Esc` o `Q` | Cerrar Mamatlatolli (Q no cierra si estás escribiendo) |
| `Space` (mantener) | Grabar / reconocer una seña con movimiento |
| Botón *← Menú* | Volver al menú principal |
| Botón *Reintentar cámara* | Volver a buscar un dispositivo si no se encontró |
| Botón *Seña con movimiento* | Forzar grabación dinámica (clic para empezar y terminar) |

## Apariencia (modo claro y oscuro)

Mamatlatolli abre en **modo claro**. En **Configuración**, o con el control **Apariencia** del menú principal, se elige **Modo claro** o **Modo oscuro**. La ventana cambia al momento, sin cerrar el programa.

La preferencia se guarda en `datos/config.json` (`"tema": "claro"` o `"tema": "oscuro"`) y se vuelve a aplicar al siguiente arranque. Los acentos siguen siendo naranja, lima e índigo, con tonos legibles sobre cada fondo.

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
  tema.py                  Paletas clara y oscura (naranja / lima / índigo) y logo
  menu.py                  Destinos del menú (sin Tk)
  pantallas.py             Menú, reconocimiento, captura, biblioteca, ajustes
  ui.py                    Ventana (CustomTkinter) y navegación
  camara.py                Captura (cámara real o fuente demo)
  detector.py              MediaPipe Hands + detector de demostración
  esquema.py               JSON versionado: categoria letra|palabra + secuencia
  cuerpo.py                MediaPipe Pose (33) y Face Mesh (478) para Vocabulario
  caracteristicas.py       Normalización de mano, pose y rostro; fusión ponderada
  dtw.py                   Dynamic Time Warping
  movimiento.py            Detector de movimiento (auto-DTW)
  ajustes.py               datos/config.json
  plantillas.py            Leer/escribir/borrar y filtrar datos/plantillas/
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

### Fase 2b

- [x] Menú principal y pantallas (captura, biblioteca, configuración, demo, acerca de)
- [x] Captura de secuencias `tipo: dinamico`
- [x] `predecir_dinamico()` con DTW
- [x] Enrutado automático estático vs dinámico + botón/Space

### Fase 3 (esta versión)

- [x] Abecedario y Vocabulario como tarjetas separadas (sin «Iniciar reconocimiento»)
- [x] Campo `categoria: "letra" | "palabra"` con migración a letra
- [x] Captura y biblioteca con filtro letra / palabra
- [x] Reconocimiento aislado por categoría
- [x] MediaPipe Pose y Face Mesh en vivo para `categoria: "palabra"`
- [x] Pose y rostro en el matching estático y en el DTW (con degradación si faltan)
- [x] Overlay ligero de esqueleto y cara en Vocabulario

### Primer conjunto de palabras

Todavía no hay un banco descargado ni una red entrenada: las palabras se capturan en **Capturar plantillas** (categoría Palabra), con consentimiento y varias tomas. Conviene confirmar con una persona señalante cuáles se sostienen (estáticas) y cuáles recorren un trayecto (dinámicas). Pose y rostro ayudan cuando la seña usa cabeza, torso o boca.

- [ ] Saludos y cortesía: HOLA, GRACIAS, POR FAVOR, BUENOS DÍAS
- [ ] Respuestas: SÍ, NO
- [ ] Casa y necesidades: AGUA, COMER, CASA, FAMILIA

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
Es normal: carga el modelo de manos. Vocabulario carga además la pose y la malla facial, que ya vienen en el paquete de MediaPipe. Los siguientes arranques son más rápidos. Si pose o rostro no arrancan, la palabra se reconoce con la mano y el JSON deja esos campos en `null`.

**El video se ve al revés (como en un espejo)**  
Es intencional: la vista espejo se siente más natural, como una videollamada.

**Todo el tiempo aparece `detectando…`**  
Aún no hay plantillas, o la pose/trayectoria no se parece a ninguna. Captura otra vez. La *estimación instantánea* muestra qué plantilla va ganando.

**Vocabulario dice que no hay plantillas**  
Aún no hay JSON con `categoria: "palabra"`. En Capturar plantillas elige *Palabra* y guarda al menos una.

**Las señas con movimiento no se reconocen**  
Tienen que existir plantillas **dinámicas** de esa categoría. En Capturar plantillas elige *Dinámica* y graba el gesto. Si el automático no dispara, usa *Seña con movimiento* o sube la sensibilidad en Configuración.

**Guardar plantilla dice que no hay mano / seña corta**  
Espera el overlay. En dinámicas, mantén el botón durante todo el gesto (mínimo ~6 fotogramas).

## Licencia y uso

Código de un prototipo académico. Úsalo para aprender; respeta la privacidad de las personas que aparezcan frente a la cámara y no guardes plantillas sin consentimiento.
