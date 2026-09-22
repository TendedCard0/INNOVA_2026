# Menú y señas dinámicas en Mamatlatolli

Este documento describe la **fase 2b**: el menú principal, cómo capturar
letras con movimiento y cómo se elige entre matching estático y **DTW**.

El programa se llama **Mamatlatolli**. El uso diario es *Iniciar
reconocimiento*; *Capturar plantillas* y *Biblioteca de señas* solo
organizan el banco de ejemplos.

## Menú principal

Al abrir `python app.py` aparece el menú (español), con el logo o un
marco placeholder centrado y seis tarjetas:

| Opción | Qué hace |
| --- | --- |
| **Iniciar reconocimiento** | Cámara en vivo, letras estáticas y dinámicas. |
| **Capturar plantillas** | Guardar una pose quieta o una trayectoria. |
| **Biblioteca de señas** | Listar (`etiqueta` + tipo), probar o borrar. |
| **Configuración** | Umbrales de confianza/estabilidad, sensibilidad al movimiento y apariencia (modo claro / modo oscuro). |
| **Modo demostración** | La misma vista de reconocimiento, sin cámara (`--demo`). |
| **Acerca de Mamatlatolli** | LSM, fases del prototipo y créditos. |

Cada pantalla tiene **← Menú**. `Esc` o `Q` cierran la aplicación (Q no
cierra si estás escribiendo una letra).

La cromática está en `innova/tema.py` (naranja, lima e índigo), con paleta
clara y paleta oscura. El menú muestra tarjetas en dos columnas y un hueco
para `assets/logo.png`. Abajo, el control **Apariencia** cambia entre
**Modo claro** y **Modo oscuro** sin salir del menú. Lo mismo está en
**Configuración**. La elección se guarda en `datos/config.json`
(`"tema": "claro"` o `"tema": "oscuro"`) y Mamatlatolli la aplica al
volver a abrir.

`python app.py --demo` también abre el menú; *Iniciar reconocimiento* usa
entonces el video sintético. *Modo demostración* hace lo mismo aunque no
hayas pasado `--demo`.

## Cómo capturar una seña dinámica

1. Menú → **Capturar plantillas**.
2. Elige **Dinámica** (no Estática).
3. Escribe la etiqueta (`J`, `Ñ`, `Z`…).
4. Coloca la mano en el encuadre.
5. Pulsa **Seña con movimiento** (o mantén **Space**), haz el gesto y
   suelta.
6. El JSON se escribe en `datos/plantillas/` con `tipo: "dinamico"`,
   `secuencia.fotogramas` llenos, `pose` y `rostro` en `null`.

Una grabación necesita al menos 6 fotogramas con mano. Si sueltas demasiado
pronto, Mamatlatolli pide repetir el movimiento.

Las estáticas siguen igual: tipo **Estática**, pose quieta, *Guardar pose
actual*.

## Automático vs botón

En **Iniciar reconocimiento** hay dos formas de usar DTW:

**Automático (por omisión).** Se observa la muñeca durante ~0,4–0,8 s
(0,6 s por defecto). Si el desplazamiento es claro, se graba esa
trayectoria y se compara con las plantillas dinámicas. Si la mano está
estable, se usa el matching estático de la fase 2a (vectores + filtro).

**Forzado.** El botón **Seña con movimiento** (clic para empezar/terminar)
o **mantener Space** graba aunque el detector no haya visto movimiento.
Al soltar se lanza DTW una sola vez: no se spamea la transcripción.

La sensibilidad de ese detector se regula en **Configuración** (más
sensibilidad = más fácil pasar a dinámico). Los ajustes, incluida la
apariencia, viven en `datos/config.json`.

## Reconocimiento dinámico (DTW)

Cada fotograma de la secuencia se convierte en el vector de la fase 2a
(78 números de forma) más la muñeca relativa al inicio del gesto (2
números). Dynamic Time Warping alinea dos secuencias de distinta
duración y elige la plantilla `tipo: dinamico` más cercana.

Solo se *compromete* una letra (y se escribe en la transcripción) si la
confianza supera el umbral. Un gesto = como mucho un renglón, no una
ráfaga de predicciones.

## Biblioteca

Lista cada JSON: etiqueta, tipo (estática/dinámica), fecha y, si aplica,
número de fotogramas. **Eliminar** borra el archivo. **Probar** abre el
reconocimiento con un recordatorio de qué seña ensayar.

## Hoja de ruta

- [x] Fase 1: cámara y detección de manos
- [x] Fase 2a: plantillas estáticas y estabilidad
- [x] Fase 2b: menú, captura dinámica y DTW
- [ ] Vocabulario completo: pose y rostro (hoy van en `null`)
