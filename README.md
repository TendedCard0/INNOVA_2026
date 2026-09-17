# INNOVA 2026

Prototipo de escritorio para **reconocer Lengua de Señas Mexicana (LSM)** a partir de la cámara del equipo.

Este repositorio corresponde a la **fase 1**: una base que ya abre una ventana, muestra el video en vivo, detecta las manos y deja listo el lugar donde más adelante se conectará un modelo de inteligencia artificial.

> Proyecto estudiantil — Instituto Tecnológico.

## ¿Qué hace hoy?

1. Abre la cámara del dispositivo.
2. Detecta hasta dos manos y dibuja landmarks, conexiones y un recuadro.
3. Muestra una **seña actual** (por ahora un marcador: `detectando…` o `—`).
4. Lleva una **transcripción corta** de las últimas predicciones.

Aún **no** clasifica letras ni palabras LSM. Eso es la fase 2.

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

El modo demostración genera un video sintético con una mano de ejemplo y el mismo overlay / panel de texto. No sustituye a la cámara real ni al modelo de LSM.

### Otra cámara

Si el equipo tiene varias cámaras (por ejemplo la integrada y una USB):

```bash
python app.py --camara 1
```

## Teclas

| Tecla | Acción |
| --- | --- |
| `Esc` o `Q` | Cerrar la aplicación |
| Botón *Reintentar cámara* | Volver a buscar un dispositivo si no se encontró al inicio |

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
  reconocimiento.py        Interfaz del clasificador LSM y marcador de la fase 1
  overlay.py               Landmarks, conexiones y recuadro
  pipeline.py              Une todo fotograma a fotograma
  ui.py                    Ventana (CustomTkinter)
  config.py                Textos, tamaños y colores
```

La UI **no** habla con MediaPipe ni con el futuro modelo: solo recibe un `ResultadoReconocimiento`. En la fase 2 se cambia `crear_reconocedor()` en `innova/reconocimiento.py` y el resto puede quedarse igual.

## Hoja de ruta

### Fase 1 (este prototipo)

- [x] Ventana de escritorio y cámara en vivo
- [x] Detección de manos con overlay
- [x] Marcador de reconocimiento (`detectando…` / `—`)
- [x] Transcripción reciente
- [x] Mensaje claro si no hay cámara

### Fase 2 (siguiente)

- Recortar o vectorizar landmarks de cada mano
- Entrenar o cargar un modelo de **letras LSM** (abecedario) y, más adelante, palabras
- Sustituir `ReconocedorMarcador` por el modelo real sin reescribir la ventana
- Filtrar predicciones inestables (voto entre varios fotogramas) antes de agregarlas a la transcripción
- Dataset propio, con consentimiento, de estudiantes del Instituto Tecnológico — no hace falta bajar colecciones enormes para empezar

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

## Licencia y uso

Código de un prototipo académico. Úsalo para aprender y para el concurso INNOVA; respeta la privacidad de las personas que aparezcan frente a la cámara.
