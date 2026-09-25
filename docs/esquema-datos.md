# Esquema de datos de Mamatlatolli

El uso diario está en la [guía de usuario](guia-usuario.md) y el recorrido
de la cámara al texto en [cómo funciona](como-funciona.md). Aquí va el
formato de cada seña y del paquete para llevarlas a otra computadora.

Las plantillas estáticas y las secuencias dinámicas se guardan como JSON versionado
(`version: "1.0"`). Un mismo formato sirve para:

- una **muestra estática** (una pose);
- una **secuencia dinámica** (varios fotogramas / DTW).

El campo **`categoria`** separa el banco:

- `"letra"` — Abecedario (A, Ñ, J…);
- `"palabra"` — Vocabulario (HOLA, GRACIAS…).

Si un JSON antiguo **no trae** `categoria`, Mamatlatolli lo lee como
`"letra"` para no romper plantillas ya capturadas. Al volver a guardar
siempre se escribe el campo.

Los campos `pose` y `rostro` los llena **Vocabulario** (`categoria: "palabra"`).
**Abecedario** los deja en `null` y solo corre el detector de manos.
La extracción vive en `innova/cuerpo.py`.

Los archivos viven en `datos/plantillas/` (también se aceptan subcarpetas)
y se leen al arrancar el reconocedor. La validación está en `innova/esquema.py`
(`validar_muestra`, `muestra_desde_dict`, `MuestraLSM.a_dict()`).

En desarrollo, `datos/` es la carpeta del repositorio (`datos/plantillas/`
y `datos/config.json`, con el tema y `record_practica`). Con el instalador
de Windows el programa no escribe en su carpeta de instalación: las señas,
la configuración y el récord van a `%LOCALAPPDATA%\Mamatlatolli`
(`plantillas\` y `config.json`). Exportar e importar usan esa misma
biblioteca. El detalle está en [`empaquetado.md`](empaquetado.md).

## Campos de una muestra

| Campo | Tipo | Notas |
| --- | --- | --- |
| `version` | string | Hoy `"1.0"`. Si cambia el formato, se sube el número. |
| `etiqueta` | string | Letra o glosa, en mayúsculas (`A`, `Ñ`, `HOLA`). |
| `categoria` | `"letra"` \| `"palabra"` | Si falta, se asume `"letra"`. |
| `tipo` | `"estatico"` \| `"dinamico"` | Estático = un fotograma; dinámico = trayectoria. |
| `mano` | objeto o `null` | Obligatorio si `tipo` es `estatico`. |
| `pose` | objeto o `null` | MediaPipe Pose, 33 puntos. `null` en letras, o si no se ve el cuerpo. |
| `rostro` | objeto o `null` | Face Mesh, 478 puntos con iris (se aceptan 468). `null` en letras, o si no se ve la cara. |
| `secuencia` | objeto o `null` | Obligatorio si `tipo` es `dinamico`. |
| `metadatos` | objeto | Tiempo, fps, notas, consentimiento, origen. |

### `mano`

| Campo | Tipo | Notas |
| --- | --- | --- |
| `lateralidad` | `"izquierda"` \| `"derecha"` \| `"desconocida"` | Vista de la persona usuaria (ya corregida si hay espejo). |
| `landmarks` | 21 × `[x, y, z]` | Coordenadas de MediaPipe (x, y en 0–1 respecto al fotograma). |
| `landmarks_normalizados` | 21 × `[x, y, z]` | Muñeca en el origen, palma de tamaño ≈ 1. |
| `caracteristicas` | lista de números | Vector para matching (78 valores: coords + distancias de puntas). |

Si al leer un archivo faltan `landmarks_normalizados` o `caracteristicas`,
se recalculan a partir de `landmarks`.

### `secuencia` (DTW)

```json
{
  "fps": 30.0,
  "fotogramas": [
    {
      "t": 0.0,
      "mano": { "...": "mismo bloque mano, o null" },
      "pose": { "landmarks": [[0.5, 0.4, 0.0]], "visibilidad": [0.9] },
      "rostro": { "landmarks": [[0.5, 0.4, 0.0]] }
    }
  ]
}
```

`t` es el tiempo en segundos desde el inicio del gesto. El reconocedor
estático ignora este bloque; `predecir_dinamico()` compara `fotogramas`
con Dynamic Time Warping contra las plantillas `tipo: dinamico` **de la
misma categoría** (letra o palabra). En palabras, cada fotograma aporta
también pose y rostro cuando existen.

### `pose` y `rostro` (Vocabulario)

Objeto o `null`. Cuando hay detección:

```json
{
  "landmarks": [[0.5, 0.4, -0.1]],
  "visibilidad": [0.98]
}
```

`visibilidad` es opcional (la trae la pose; el rostro no). `landmarks` son
coordenadas normalizadas de MediaPipe (x, y en 0–1). Pose: 33 puntos.
Rostro: 478 con `refine_landmarks=True` (se acepta una malla de 468).

El vector de matching **no** se guarda dentro de `pose` / `rostro`. Al
reconocer, `innova/caracteristicas.py` normaliza y fusiona:

| Parte | Referencia | Peso |
| --- | --- | --- |
| Mano | Muñeca al origen, palma ≈ 1 | 0,55 |
| Pose | Punto medio de caderas, ancho de hombros ≈ 1 | 0,30 |
| Rostro | Nariz al origen, distancia entre ojos ≈ 1 (15 puntos: ojos, cejas, boca) | 0,15 |

Si falta pose o rostro en la consulta o en la plantilla, ese peso se reparte
entre las partes que sí están. Una palabra antigua, solo con mano, sigue
comparándose.

**Dónde corre:**

| Pieza | Rol |
| --- | --- |
| `innova/cuerpo.py` | `extraer_pose()`, `extraer_rostro()`, `anotar_cuerpo()`. Pose (`model_complexity=1`, modelo incluido) y Face Mesh. |
| `innova/pipeline.py` | En Vocabulario y al capturar Palabra, anota el fotograma crudo y dibuja el overlay. |
| `innova/reconocimiento.py` | Matching estático y DTW de `categoria: "palabra"` usan la fusión. |

Abecedario no carga estos modelos. Si el grafo no arranca, las funciones
devuelven `None` y la palabra se reconoce con la mano.

### `metadatos`

| Campo | Tipo | Notas |
| --- | --- | --- |
| `marca_tiempo` | string ISO-8601 | UTC, obligatorio. |
| `fps` | número o `null` | Fotogramas por segundo de la captura. |
| `notas` | string | Texto libre. |
| `consentimiento` | boolean | Debe ser `true` si la seña es de una persona. |
| `origen` | string | `"camara"`, `"demo"` u otro. |

## Ejemplo estático (letra)

```json
{
  "version": "1.0",
  "etiqueta": "A",
  "categoria": "letra",
  "tipo": "estatico",
  "mano": {
    "lateralidad": "derecha",
    "landmarks": [[0.51, 0.70, 0.0]],
    "landmarks_normalizados": [[0.0, 0.0, 0.0]],
    "caracteristicas": [0.0, 0.0]
  },
  "pose": null,
  "rostro": null,
  "secuencia": null,
  "metadatos": {
    "marca_tiempo": "2026-09-17T12:00:00+00:00",
    "fps": 30.0,
    "notas": "Seña de ejemplo",
    "consentimiento": true,
    "origen": "camara"
  }
}
```

(El ejemplo recorta las listas; un archivo real lleva 21 puntos y 78
características.)

## Ejemplo dinámico (palabra)

```json
{
  "version": "1.0",
  "etiqueta": "HOLA",
  "categoria": "palabra",
  "tipo": "dinamico",
  "mano": null,
  "pose": null,
  "rostro": null,
  "secuencia": {
    "fps": 30.0,
    "fotogramas": [
      { "t": 0.0, "mano": null, "pose": null, "rostro": null },
      { "t": 0.03, "mano": null, "pose": null, "rostro": null }
    ]
  },
  "metadatos": {
    "marca_tiempo": "2026-09-17T12:00:00+00:00",
    "fps": 30.0,
    "notas": "Trayectoria reconocida con DTW",
    "consentimiento": true,
    "origen": "camara"
  }
}
```

En una captura real de palabra cada fotograma lleva su `mano` y, si se
detectan, `pose` y `rostro`. Cómo grabar esas secuencias desde el menú está en
[`menu-y-senas-dinamicas.md`](menu-y-senas-dinamicas.md).

## Paquete para llevar las señas (`.mamatlatolli`)

La biblioteca se puede copiar de un equipo a otro sin volver a capturar.
El archivo no es una base de datos ni se sincroniza: es un paquete local.
La lectura y la escritura viven en `innova/paquete.py`.

Extensión preferida: **`.mamatlatolli`** (ZIP). También se acepta un solo
JSON con los mismos campos y las muestras dentro de `plantillas`.

### `manifiesto.json`

| Campo | Tipo | Notas |
| --- | --- | --- |
| `formato` | string | Siempre `"mamatlatolli-plantillas"`. Si no coincide, el archivo se rechaza. |
| `version` | string | Versión **del paquete**, hoy `"1.0"`. No es la `version` de cada muestra. Otra versión se rechaza. |
| `producto` | string | `"Mamatlatolli"`. |
| `creado` | string ISO-8601 | Cuándo se exportó, en UTC. |
| `conteo` | número | Cuántas señas trae. Tiene que coincidir con los archivos; si no, el paquete se considera incompleto. |
| `letras` / `palabras` | número | Conteos informativos. |
| `quietas` / `con_movimiento` | número | Conteos informativos. |
| `idioma` | string | Código de la lengua de señas. Hoy `"lsm"`. Gancho para otras lenguas; no filtra ni sincroniza. |
| `nombre_idioma` | string | Hoy `"Lengua de Señas Mexicana"`. |
| `idioma_glosa` | string | Idioma en que está escrita la glosa. Hoy `"es-MX"`. |
| `notas` | string | Texto libre, puede ir vacío. |
| `archivos` | lista de rutas | Dentro del ZIP: `plantillas/0001_A_letra_estatico.json`, etc. |

Los campos que esta versión no conoce se ignoran, para poder sumar metadata
sin romper los paquetes `"1.0"`. Una `version` nueva solo se acepta cuando
Mamatlatolli la agregue a la lista de versiones compatibles.

### Señas que coinciden

Al importar, dos señas son la misma si coinciden:

- la glosa (`etiqueta`, sin importar mayúsculas);
- la categoría (`letra` o `palabra`);
- si es quieta (`estatico`) o con movimiento (`dinamico`).

Varias tomas de esa seña forman un solo grupo.

En Biblioteca, si hay grupos en común, un diálogo ofrece **Reemplazar las
que ya tengo** o **Solo agregar las nuevas**. En la terminal, `python -m
innova.importar` reemplaza por omisión; `--solo-nuevas` deja los grupos
existentes intactos. Las señas que no vienen en el archivo no se borran.

Un archivo dañado, que no es un paquete, incompleto, de otra versión, o
con una seña ilegible, se rechaza entero: la biblioteca no cambia.
