# Menú, Abecedario y Vocabulario en Mamatlatolli

Este documento describe el menú principal, la separación **letra /
palabra** y cómo se elige entre matching estático y **DTW**.

El programa se llama **Mamatlatolli**. El uso diario son dos modos:

- **Abecedario** — reconoce plantillas `categoria: "letra"`;
- **Vocabulario** — reconoce plantillas `categoria: "palabra"`.

*Capturar plantillas* y *Biblioteca de señas* organizan el banco
(filtro letra / palabra), no son una segunda app de reconocimiento.

## Menú principal

Al abrir `python app.py` aparece el menú (español), con el logo oficial
(`assets/logo.png`) centrado arriba —o un marco placeholder si el archivo
no está— y ocho tarjetas:

| Opción | Qué hace |
| --- | --- |
| **Abecedario** | Cámara en vivo, solo letras (estáticas y dinámicas). |
| **Vocabulario** | Cámara en vivo, solo palabras. Usa mano, pose y rostro. Si aún no hay plantillas de palabra, muestra un estado vacío en español. |
| **Mini juego** | Letra estática al azar tras pulsar Inicio, cronómetro de 5 segundos y puntos por rapidez (1000 / 700 / 500). Solo letras que ya capturaste; si no hay, un aviso en español. |
| **Capturar plantillas** | Guardar una pose o una trayectoria; eliges Letra o Palabra. |
| **Biblioteca de señas** | Listar, filtrar (`letra` / `palabra` / `todas`), probar o borrar. |
| **Configuración** | Umbrales de confianza/estabilidad, sensibilidad al movimiento y apariencia (modo claro / modo oscuro). |
| **Modo demostración** | Vista de Abecedario sin cámara (`--demo`). |
| **Acerca de Mamatlatolli** | LSM, fases del prototipo y créditos. |

Ya no existe la tarjeta única «Iniciar reconocimiento»: mezclar letras
y palabras en un solo modo confundía el banco.

Cada pantalla tiene **← Menú**. `Esc` o `Q` cierran la aplicación (Q no
cierra si estás escribiendo una etiqueta).

La cromática está en `innova/tema.py` (naranja, lima e índigo), con paleta
clara y paleta oscura. El menú muestra tarjetas en dos columnas (la última,
*Acerca de*, ocupa el ancho) y el logo oficial (`assets/logo.png`) centrado
arriba. Si el archivo no está, se usa un marco placeholder. Abajo, el
control **Apariencia** cambia entre **Modo claro** y **Modo oscuro** sin
salir del menú. Lo mismo está en **Configuración**. La elección se guarda
en `datos/config.json` (`"tema": "claro"` o `"tema": "oscuro"`) y
Mamatlatolli la aplica al volver a abrir.

`python app.py --demo` también abre el menú; *Abecedario*,
*Vocabulario* y *Mini juego* usan entonces el video sintético. *Modo demostración*
abre Abecedario sin cámara aunque no hayas pasado `--demo`.

## Mini juego

**Mini juego** no enseña un vocabulario ni trae palabras precargadas. Toma las
plantillas estáticas de `categoria: "letra"` que ya están en
`datos/plantillas/`. Al abrir el modo se ve el récord y el botón **Inicio**:
la letra y los **5 segundos** arrancan solo al pulsarlo. El tiempo se ve en
un aro que se vacía, en la cuenta numérica y en un tic-tac suave.

- Acierto: la predicción **estable** (el mismo filtro de Abecedario, no la
  estimación instantánea) es esa letra antes de los 5 s. Los puntos dependen
  de la rapidez: **1000** si tarda menos de 1 s, **700** de 1 s a menos de 3 s,
  **500** de 3 s a menos de 5 s. Suena el acierto y, sin otro botón, elige otra
  letra —sin repetir la anterior si hay más de una— y vuelve a contar 5 s.
  Los puntos se acumulan.
- Fallo: se cumplen los 5 segundos, o la seña estable es otra letra. Suena el
  error, se detiene el tic-tac y la partida vuelve al botón **Inicio**.
  **Menú**, Esc y Q salen en cualquier momento, sin arrancar una ronda.
- Récord: en `datos/config.json`, la clave `record_practica` solo se
  actualiza si la puntuación es mayor que la guardada. Ese momento suena una
  sola vez, no en cada acierto.
- Sonidos: `assets/sonidos/*.wav`, sintetizados con numpy en `innova/audio.py`.
  Windows los reproduce con `winsound` (sin FFmpeg). Linux y macOS usan
  `ffplay`, `paplay` o `aplay`, fuera del hilo de la cámara. Si falta el
  archivo o no hay salida de audio, el juego sigue en silencio.

Si no hay letras estáticas, la pantalla lo explica en español y remite a
**Capturar plantillas** (Letra · Estática). Las plantillas dinámicas y las
palabras no entran en esta partida. Mini juego no usa DTW: compara la pose
quieta.

## Cómo capturar

1. Menú → **Capturar plantillas**.
2. Elige **Letra** o **Palabra**.
3. Elige **Estática** o **Dinámica**.
4. Escribe la etiqueta (`A`, `Ñ`, `HOLA`…).
5. Estática: pose quieta → *Guardar pose actual*.
   Dinámica: *Seña con movimiento* o **Space**, haz el gesto y suelta.
6. El JSON lleva `categoria`, `tipo` y, si es dinámica, `secuencia`.
   En **Palabra**, `pose` y `rostro` se llenan cuando la cámara ve a la persona
   (también en cada fotograma de una dinámica). En **Letra** quedan en `null`.

Una grabación dinámica necesita al menos 6 fotogramas con mano.

## Automático vs botón

En **Abecedario** y **Vocabulario** hay dos formas de usar DTW (solo
contra plantillas de esa categoría):

**Automático (por omisión).** Se observa la muñeca durante ~0,4–0,8 s
(0,6 s por defecto). Si el desplazamiento es claro, se graba esa
trayectoria y se compara con las plantillas dinámicas. Si la mano está
estable, se usa el matching estático (vectores + filtro).

**Forzado.** El botón **Seña con movimiento** (clic para empezar/terminar)
o **mantener Space** graba aunque el detector no haya visto movimiento.
Al soltar se lanza DTW una sola vez: no se spamea la transcripción.

La sensibilidad de ese detector se regula en **Configuración** (más
sensibilidad = más fácil pasar a dinámico). Los ajustes, incluida la
apariencia, viven en `datos/config.json` y aplican a Abecedario y a
Vocabulario.

## Reconocimiento dinámico (DTW)

Cada fotograma de una **letra** se convierte en el vector de forma
(78 números) más la muñeca relativa al inicio del gesto (2 números).
En una **palabra**, el mismo fotograma suma la pose normalizada y el
recorte del rostro; si en ese instante no se vieron, el DTW ignora ese
bloque. Dynamic Time Warping alinea dos secuencias de distinta duración y
elige la plantilla `tipo: dinamico` más cercana **de la categoría
activa**.

Solo se *compromete* una seña (y se escribe en la transcripción) si la
confianza supera el umbral. Un gesto = como mucho un renglón.

## Biblioteca

Pestañas / segmento: **Letra** · **Palabra** · **Todas**.

Lista cada JSON: etiqueta, categoría, tipo (estática/dinámica), fecha
y, si aplica, número de fotogramas. **Eliminar** borra el archivo.
**Probar** abre Abecedario o Vocabulario según la categoría, con un
recordatorio de qué seña ensayar.

## Vocabulario: pose y rostro

Vocabulario corre MediaPipe Pose (33 puntos, modelo incluido en el paquete) y Face Mesh
(478 con iris), además de las manos. El esqueleto y unos puntos de la
cara se dibujan con índigo, lima y naranja del tema.

La distancia de una palabra reparte peso entre mano (0,55), pose (0,30)
y rostro (0,15). Si el modelo no carga o ese fotograma no trae cuerpo,
esa parte se omite y la seña sigue comparándose con lo que sí hay.
Abecedario no carga estos grafos.

Detalle del JSON: [`esquema-datos.md`](esquema-datos.md).

## Primer conjunto de palabras

No hay un corpus que descargar. El primer banco se captura a mano, con
consentimiento, en **Capturar plantillas → Palabra**. Confirmar con una
persona señalante qué glosas son una pose quieta y cuáles llevan
movimiento:

- Saludos y cortesía: HOLA, GRACIAS, POR FAVOR, BUENOS DÍAS
- Respuestas: SÍ, NO
- Casa y necesidades: AGUA, COMER, CASA, FAMILIA

Varias tomas por glosa (distancia, luz, giro). Las que mueven cabeza,
torso o boca se benefician de `pose` y `rostro`.

## Hoja de ruta

- [x] Fase 1: cámara y detección de manos
- [x] Fase 2a: plantillas estáticas y estabilidad
- [x] Fase 2b: menú, captura dinámica y DTW
- [x] Fase 3: Abecedario y Vocabulario separados; `categoria` letra/palabra
- [x] Fase 4: MediaPipe Pose y Face Mesh en Vocabulario (estático, DTW y overlay)
- [ ] Capturar el primer conjunto de palabras (lista de arriba)
