# Menú, Abecedario y Vocabulario en Mamatlatolli

Este documento describe el menú principal, la separación **letra /
palabra** y cómo se elige entre matching estático y **DTW**.

El programa se llama **Mamatlatolli**. El uso diario son dos modos:

- **Abecedario** — reconoce plantillas `categoria: "letra"`;
- **Vocabulario** — reconoce plantillas `categoria: "palabra"`.

*Capturar plantillas* y *Biblioteca de señas* organizan el banco
(filtro letra / palabra), no son una segunda app de reconocimiento.

## Menú principal

Al abrir `python app.py` aparece el menú (español), con el logo o un
marco placeholder centrado y siete tarjetas:

| Opción | Qué hace |
| --- | --- |
| **Abecedario** | Cámara en vivo, solo letras (estáticas y dinámicas). |
| **Vocabulario** | Cámara en vivo, solo palabras. Si aún no hay plantillas de palabra, muestra un estado vacío en español. |
| **Capturar plantillas** | Guardar una pose o una trayectoria; eliges Letra o Palabra. |
| **Biblioteca de señas** | Listar, filtrar (`letra` / `palabra` / `todas`), probar o borrar. |
| **Configuración** | Umbrales de confianza/estabilidad y sensibilidad al movimiento. |
| **Modo demostración** | Vista de Abecedario sin cámara (`--demo`). |
| **Acerca de Mamatlatolli** | LSM, fases del prototipo y créditos. |

Ya no existe la tarjeta única «Iniciar reconocimiento»: mezclar letras
y palabras en un solo modo confundía el banco.

Cada pantalla tiene **← Menú**. `Esc` o `Q` cierran la aplicación (Q no
cierra si estás escribiendo una etiqueta).

La cromática está en `innova/tema.py` (naranja, lima e índigo). El menú
es claro, con tarjetas en dos columnas (la última, *Acerca de*, ocupa
el ancho) y un hueco para `assets/logo.png`.

`python app.py --demo` también abre el menú; *Abecedario* y
*Vocabulario* usan entonces el video sintético. *Modo demostración*
abre Abecedario sin cámara aunque no hayas pasado `--demo`.

## Cómo capturar

1. Menú → **Capturar plantillas**.
2. Elige **Letra** o **Palabra**.
3. Elige **Estática** o **Dinámica**.
4. Escribe la etiqueta (`A`, `Ñ`, `HOLA`…).
5. Estática: pose quieta → *Guardar pose actual*.
   Dinámica: *Seña con movimiento* o **Space**, haz el gesto y suelta.
6. El JSON lleva `categoria`, `tipo` y, si es dinámica, `secuencia`.
   `pose` y `rostro` quedan en `null` hasta activar los ganchos.

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

La sensibilidad de ese detector se regula en **Configuración**. Los
ajustes viven en `datos/config.json` y aplican a ambos modos.

## Reconocimiento dinámico (DTW)

Cada fotograma de la secuencia se convierte en el vector de forma
(78 números) más la muñeca relativa al inicio del gesto (2 números).
Dynamic Time Warping alinea dos secuencias de distinta duración y
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

## Vocabulario y cuerpo (siguiente paso)

Hoy Vocabulario usa **solo la mano**, igual que Abecedario. El esquema
ya reserva `pose` y `rostro`. Para activarlos más adelante, sin
reescribir las pantallas:

1. Implementa MediaPipe Pose / Face Mesh en `innova/cuerpo.py`.
2. Activa `POSE_ACTIVA` y/o `ROSTRO_ACTIVO`.
3. El pipeline y el reconocedor ya llaman `anotar_cuerpo(frame)`.

Detalle del JSON: [`esquema-datos.md`](esquema-datos.md).

## Hoja de ruta

- [x] Fase 1: cámara y detección de manos
- [x] Fase 2a: plantillas estáticas y estabilidad
- [x] Fase 2b: menú, captura dinámica y DTW
- [x] Fase 3: Abecedario y Vocabulario separados; `categoria` letra/palabra
- [ ] Activar MediaPipe Pose y Face Mesh (`innova/cuerpo.py`)
