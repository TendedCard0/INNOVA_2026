# Guía de usuario de Mamatlatolli

Mamatlatolli es un programa de escritorio para reconocer **Lengua de Señas Mexicana (LSM)** con la cámara. Sirve para una demo en el salón, para practicar letras que el grupo acaba de capturar y para guardar palabras propias.

Las señas no vienen de fábrica. Quien usa el programa las captura en su computadora, con consentimiento, y Mamatlatolli las compara en vivo.

Proyecto estudiantil del Instituto Tecnológico de San Juan del Río.

## Para quién es

- Para un grupo escolar que quiere ver, en la computadora, cómo se lee una seña que ellos mismos guardaron.
- Para quien presenta la demo y necesita instalar, capturar una letra y abrir el mini juego sin tocar el código.
- Para quien quiere llevar las mismas señas a otra computadora del laboratorio.

Mamatlatolli no sustituye a una persona que enseña LSM ni trae un curso armado.

## Qué necesitas

- Una **cámara** (la del equipo o una web). Si no hay cámara, el **Modo demostración** abre un video de ejemplo para ver la interfaz; no sustituye a una seña real.
- **Windows** es lo recomendado si vas a usar el instalador (Setup). Hace falta Windows 10 o posterior, de 64 bits.
- Luz de frente sobre las manos, y espacio para que la mano (y, en Vocabulario, la cara y el torso) quepan en el cuadro.

Quien quiera correr el programa desde el código, en Windows, macOS o Linux, tiene los pasos en el [README](../README.md#desde-el-codigo).

## Instalar en Windows

1. Baja el archivo **Mamatlatolli-Setup.exe**. Sale del workflow **Instalador Windows de Mamatlatolli** en GitHub Actions (artifact **Mamatlatolli-Windows**). Los clics exactos están en [Empaquetar Mamatlatolli para Windows](empaquetado.md).
2. Ábrelo. La instalación normal es por usuario: no pide cuenta de administrador. Quedan accesos directos en el menú Inicio y en el escritorio.
3. Si Windows SmartScreen avisa que el publicador es desconocido, es porque el instalador no lleva firma de código: **Más información** → **Ejecutar de todas formas**.
4. Abre **Mamatlatolli** desde el acceso directo.

Las señas, el modo claro u oscuro y el récord del mini juego se guardan en `%LOCALAPPDATA%\Mamatlatolli`, no dentro de la carpeta del programa. Desinstalar no borra esa carpeta. El detalle está en [empaquetado.md](empaquetado.md).

## El menú

Al abrir ves el logo y ocho tarjetas:

| Tarjeta | Para qué |
| --- | --- |
| **Abecedario** | Leer letras que ya capturaste, quietas o con movimiento. |
| **Vocabulario** | Leer palabras que ya capturaste. Usa la mano, el cuerpo y el rostro. |
| **Mini juego** | Contrarreloj con una letra quieta de tu biblioteca. |
| **Capturar plantillas** | Guardar una letra o una palabra. |
| **Biblioteca de señas** | Ver, probar, borrar, exportar o importar las señas de este equipo. |
| **Configuración** | Modo claro u oscuro, y qué tan estricta es la lectura. |
| **Modo demostración** | Abecedario con un video de ejemplo, sin cámara. |
| **Acerca de Mamatlatolli** | Qué es el programa y dónde guarda las señas de esta copia. |

**Esc** o **← Menú** regresan al menú. En el menú, **Esc** o **Q** cierran el programa. **Q** no cierra si estás escribiendo una etiqueta.

En el menú, **Apariencia** cambia entre modo claro y modo oscuro al momento. Lo mismo está en **Configuración**. La elección se recuerda en esta computadora.

## Primeros pasos

Haz esta secuencia la primera vez. Si la biblioteca está vacía, Abecedario, Vocabulario, Mini juego y la biblioteca lo dicen en español y te mandan a capturar.

### 1. Captura una letra quieta

1. Menú → **Capturar plantillas**.
2. En **¿Letra o palabra?** deja **Letra**.
3. En **¿Quieta o con movimiento?** deja **Estática**.
4. Coloca la seña quieta, con la mano bien visible. Cuando el programa ve la mano, puedes guardar.
5. Escribe la etiqueta (por ejemplo `A`) y pulsa **Guardar seña**.

Conviene guardar varias tomas de la misma letra: un poco más cerca, un poco más lejos, con otro giro de la mano. Mini juego y Abecedario usan esas tomas.

### 2. Pruébala en Abecedario

Menú → **Abecedario**. Seña la letra y mantenla un momento. Un parpadeo no cuenta: Mamatlatolli espera a que la lectura se sostenga y entonces escribe la letra en **Lo que ya leímos**.

Si aún duda, verás **Buscando…**. Si no alcanza a ver la mano, verás **—**.

<a id="juega-una-ronda"></a>

### 3. Juega una ronda

Menú → **Mini juego**.

1. Ves el récord y el botón **Inicio**. La letra no sale hasta que lo pulses.
2. **Inicio** muestra una letra quieta que ya capturaste y arranca un reloj de **5 segundos**.
3. Seña esa letra y mantenla quieta. Si la lectura estable coincide a tiempo, sumas puntos y sale otra letra. Menos de 1 segundo: **1000**. De 1 segundo a menos de 3: **700**. De 3 segundos a menos de 5: **500**.
4. Si se acaban los 5 segundos, o la seña estable es otra letra, la partida vuelve a **Inicio**. Solo se guarda el récord si esa partida lo superó.

Mini juego no usa palabras ni señas con movimiento. Si todavía no hay letras quietas, la pantalla lo explica.

### Vocabulario, en breve

**Vocabulario** lee solo palabras que tú captures (categoría **Palabra**). No hay una lista precargada ni un recorrido guiado. En **Capturar plantillas** elige **Palabra**, quieta o con movimiento, y guarda la seña. Si la cámara ve a la persona, también se guardan el cuerpo y el rostro; en las letras solo se guarda la mano.

Hasta que no haya al menos una palabra, Vocabulario muestra un aviso y espera a que captures una.

### Llevar las señas a otra computadora

1. En el equipo donde ya están: **Biblioteca de señas** → **Exportar…**.
2. Guarda el archivo (el nombre sugerido es `senas-mamatlatolli.mamatlatolli`) y cópialo.
3. En la otra computadora: **Biblioteca de señas** → **Importar…** y elige ese archivo.

Si el archivo trae una letra o palabra que ya existe ahí —el mismo nombre, y quieta o con movimiento igual—, Mamatlatolli pregunta:

- **Reemplazar las que ya tengo.** Esas señas pasan a ser las del archivo. El resto de la biblioteca no se borra.
- **Solo agregar las nuevas.** No toca las que ya tienes.

Si no hay coincidencias, las agrega sin preguntar. Un archivo dañado o de una versión que esta copia no entiende se rechaza y la biblioteca no cambia. El diálogo abre en Documentos para que el archivo quede fácil de copiar.

## Señas con movimiento

Algunas letras y palabras no son una pose fija: la mano recorre un camino. En **Capturar plantillas** elige **Dinámica**, escribe la etiqueta, pulsa **Seña con movimiento** (o mantén **Espacio**), haz el gesto completo y suelta.

En Abecedario o Vocabulario, si la mano se mueve con claridad, Mamatlatolli compara ese recorrido con las señas dinámicas que guardaste. También puedes forzar la grabación con **Seña con movimiento** o manteniendo **Espacio**. Hace falta haber capturado antes esa seña como dinámica; si no, el programa lo dice.

## Consejos para la demo

- Ilumina las manos de frente. La luz detrás de la persona las deja en sombra.
- Deja la mano entera dentro del cuadro. En Vocabulario, encuadra también la cara y la parte de arriba del cuerpo.
- La cámara en vivo se ve en espejo, como una videollamada. Así es más fácil acomodar la seña.
- Cierra otras apps que estén usando la cámara (videollamadas, el navegador) y, si hace falta, pulsa **Reintentar cámara**.
- En Windows, el permiso de cámara está en Configuración → Privacidad y seguridad → Cámara. Con el Setup, el programa aparece como **Mamatlatolli**.
- Pide consentimiento antes de grabar a alguien. En Vocabulario la captura puede incluir rostro y torso, no solo la mano. No compartas el archivo `.mamatlatolli` con personas que no deban ver esas señas.
- Varias tomas de la misma seña aguantan mejor un cambio de distancia, de giro o de luz.

## Si algo no cuadra

| Lo que ves | Qué hacer |
| --- | --- |
| No encontramos la cámara | Conéctala, cierra otras apps y pulsa **Reintentar cámara**, o abre **Modo demostración**. |
| Todavía no hay letras / palabras | Ve a **Capturar plantillas** y guarda al menos una seña de ese tipo. |
| Todo el tiempo dice **Buscando…** | La mano se ve, pero no se parece lo bastante a una plantilla. Captura otra toma o seña más parecido al ejemplo guardado. |
| La seña con movimiento no se lee | Tiene que existir una plantilla **Dinámica** de esa letra o palabra. Grábala otra vez, el gesto completo, y suelta al terminar. |
| Vocabulario no tiene palabras | Elige **Palabra** al capturar. Las letras del abecedario no aparecen ahí. |

## Quiero ver cómo lo hace

El recorrido de la cámara al texto, con un diagrama, está en [Cómo funciona Mamatlatolli](como-funciona.md).

Quien va a modificar el programa o correrlo con Python sigue en el [README](../README.md#desde-el-codigo).
