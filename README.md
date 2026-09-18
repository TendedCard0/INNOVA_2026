# Mamatlatolli

Prototipo de escritorio para **reconocer Lengua de Señas Mexicana (LSM)** a partir de la cámara del equipo con IA.

**Mamatlatolli** 

> Proyecto estudiantil — Instituto Tecnológico de San Juan de el Rio.

## ¿Qué hace hoy? (fase 2a)

1. Abre la cámara del dispositivo (o un video sintético con `--demo`).
2. Detecta hasta dos manos y dibuja landmarks, conexiones y un recuadro.
3. Compara la pose de la mano con **plantillas** guardadas (vectores de landmarks normalizados + distancia).
4. Aplica un **filtro de estabilidad** (umbral de confianza, voto temporal e histéresis) antes de comprometer una letra.
5. Muestra la **seña estable**, la **estimación instantánea** (útil para depurar) y una transcripción corta de las letras ya estables.
6. Permite **capturar una plantilla** desde la cámara: escribes la letra y pulsas *Guardar*.

Aún **no** reconoce letras con movimiento (J, Ñ, Z…) ni vocabulario completo con cuerpo y rostro. Eso es la fase 2b y la fase de vocabulario.

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

También funciona:

```bash
python -m innova
```

### Si no hay cámara (o quieres ensayar la interfaz)

```bash
python app.py --demo
```

El modo demostración genera un video sintético con una mano de ejemplo y el mismo overlay / panel de texto. Sirve para practicar la captura de plantillas y ver el filtro, pero no sustituye a una seña real.

### Otra cámara

Si el equipo tiene varias cámaras (por ejemplo la integrada y una USB):

```bash
python app.py --camara 1
```

## Cómo capturar plantillas

El reconocedor **no** descarga conjuntos enormes ni entrena una red. Tú (o quien seña, con su consentimiento) guardas ejemplos de cada letra:

1. Ejecuta `python app.py` (o `--demo`).
2. Coloca la seña estática frente a la cámara, con la mano bien visible.
3. En el panel derecho, escribe la letra (por ejemplo `A` o `Ñ`) en el campo *Letra*.
4. Pulsa **Guardar**.
5. El archivo se escribe en `datos/plantillas/` con el esquema versionado (mano + metadatos; `pose` y `rostro` quedan en `null`).
6. Las plantillas se recargan al instante: a partir de ese momento esa pose puede reconocerse.

Recomendaciones:

- Captura **varias** plantillas por letra (distinta distancia, un poco de giro, otra iluminación).
- Solo guarda señas de personas que hayan dado **consentimiento** (el JSON guarda ese dato en `metadatos.consentimiento`).
- Las letras con trayectoria (J, Ñ, Z, algunas palabras) se grabarán como `tipo: dinamico` en la fase 2b; hoy el botón guarda plantillas **estáticas**.

Los JSON de `datos/plantillas/` no se suben al git (pueden contener datos personales). El detalle de cada campo está en [`docs/esquema-datos.md`](docs/esquema-datos.md).

## Cómo funciona el reconocimiento

1. **Landmarks.** MediaPipe Hands entrega 21 puntos (x, y, z) por mano.
2. **Normalización.** Se traslada la muñeca al origen y se escala por el tamaño de la palma. No se rota: varias letras LSM se distinguen por la orientación.
3. **Vector.** Se arma un vector de 78 números (coords normalizadas + distancias entre puntas).
4. **Matching.** Se compara con cada plantilla estática (distancia euclidiana RMS, o coseno) y se obtiene una confianza `1 − distancia/saturación`.
5. **Estabilidad.** Una letra solo pasa a *seña estable* y a la transcripción si:
   - la confianza supera el umbral, **y**
   - hay **N fotogramas consecutivos** de la misma letra **o** **M de los últimos K**, **y**
   - la **histéresis** evita el parpadeo: la letra ya comprometida se mantiene con un umbral más bajo y no cambia hasta que otra también se estabilice.
6. Si no hay acuerdo, la UI muestra `detectando…` (hay mano) o `—` (no hay mano).

La estimación del fotograma actual se ve aparte, como *Estimación instantánea*, para depurar sin ensuciar la transcripción.

El gancho `predecir_dinamico(secuencia)` ya existe y, por ahora, responde que el DTW llega en la fase 2b.

## Teclas

| Tecla | Acción |
| --- | --- |
| `Esc` o `Q` | Cerrar la aplicación (Q no cierra si estás escribiendo la letra) |
| Botón *Reintentar cámara* | Volver a buscar un dispositivo si no se encontró al inicio |
| Botón *Guardar* | Guardar la mano actual como plantilla de la letra escrita |

## Permisos de la cámara

Si la ventana indica que **no se encontró una cámara**, casi siempre es un permiso del sistema o un dispositivo ocupado por otra app (Zoom, Teams, el navegador, etc.).

- **Windows:** Configuración → Privacidad y seguridad → Cámara → permite el acceso para el escritorio / Python.
- **macOS:** Configuración del Sistema → Privacidad y seguridad → Cámara → activa el permiso para Terminal, VS Code o Python.
- **Linux:** verifica que tu usuario esté en el grupo `video` y que ninguna otra aplicación tenga el dispositivo `/dev/video0` bloqueado.

Cierra otras apps que usen la cámara e intenta de nuevo, o pulsa **Reintentar cámara**.

## Estructura del código

```
app.py                     Punto de entrada
innova/
  camara.py                Captura (cámara real o fuente demo)
  detector.py              MediaPipe Hands + detector de demostración
  esquema.py               JSON versionado: muestra estática / secuencia
  caracteristicas.py       Normalización, vector y distancias
  plantillas.py            Leer/escribir datos/plantillas/
  estabilidad.py           Umbral + voto temporal + histéresis
  reconocimiento.py        crear_reconocedor() / ReconocedorEstatico
  overlay.py               Landmarks, conexiones y recuadro
  pipeline.py              Une todo fotograma a fotograma
  ui.py                    Ventana (CustomTkinter)
  config.py                Textos, tamaños y umbrales
docs/esquema-datos.md      Documentación del esquema (español)
datos/plantillas/          Plantillas JSON (locales, no se versionan)
```

La UI **no** habla con MediaPipe ni con el matching: solo recibe un `ResultadoReconocimiento`. En la fase 2b se puede enriquecer `predecir_dinamico()` sin reescribir la ventana.

## Hoja de ruta

### Fase 1

- [x] Ventana de escritorio y cámara en vivo
- [x] Detección de manos con overlay
- [x] Marcador de reconocimiento (`detectando…` / `—`)
- [x] Transcripción reciente
- [x] Mensaje claro si no hay cámara

### Fase 2a (esta versión)

- [x] Esquema JSON versionado (mano + pose/rostro reservados + secuencia)
- [x] Captura de plantillas estáticas desde la cámara o el modo demo
- [x] Matching por vectores normalizados (euclidiana / coseno)
- [x] Filtro de estabilidad (umbral, N consecutivos / M-de-K, histéresis)
- [x] Gancho `predecir_dinamico()` para la fase 2b

### Fase 2b (siguiente)

- Grabar **secuencias** (`tipo: dinamico`) para letras con movimiento
- Comparar trayectorias con **DTW** (Dynamic Time Warping) sobre `secuencia.fotogramas`
- Decidir automáticamente si una seña es estática o dinámica

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
Aún no hay plantillas, o la pose no se parece a ninguna. Captura la letra otra vez, más de frente y con mejor luz. La *estimación instantánea* te dice qué plantilla está ganando aunque todavía no sea estable.

**Guardar plantilla dice que no hay mano**  
Espera a que el overlay dibuje la mano y vuelve a pulsar *Guardar*.

## Licencia y uso

Código de un prototipo académico. Úsalo para aprender; respeta la privacidad de las personas que aparezcan frente a la cámara y no guardes plantillas sin consentimiento.
