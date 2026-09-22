# Esquema de datos de Mamatlatolli

Las plantillas y las futuras secuencias se guardan como JSON versionado
(`version: "1.0"`). Un mismo formato sirve para:

- una **muestra estática** (una pose);
- una **secuencia dinámica** (varios fotogramas / DTW).

El campo **`categoria`** separa el banco:

- `"letra"` — Abecedario (A, Ñ, J…);
- `"palabra"` — Vocabulario (HOLA, GRACIAS…).

Si un JSON antiguo **no trae** `categoria`, Mamatlatolli lo lee como
`"letra"` para no romper plantillas ya capturadas. Al volver a guardar
siempre se escribe el campo.

Los campos `pose` y `rostro` ya existen para el vocabulario completo
(cuerpo y cara). Hoy van en `null`: solo corre el detector de manos.
Los ganchos para llenarlos están en `innova/cuerpo.py` (ver más abajo).

Los archivos viven en `datos/plantillas/` (también se aceptan subcarpetas)
y se leen al arrancar el reconocedor. La validación está en `innova/esquema.py`
(`validar_muestra`, `muestra_desde_dict`, `MuestraLSM.a_dict()`).

## Campos de una muestra

| Campo | Tipo | Notas |
| --- | --- | --- |
| `version` | string | Hoy `"1.0"`. Si cambia el formato, se sube el número. |
| `etiqueta` | string | Letra o glosa, en mayúsculas (`A`, `Ñ`, `HOLA`). |
| `categoria` | `"letra"` \| `"palabra"` | Si falta, se asume `"letra"`. |
| `tipo` | `"estatico"` \| `"dinamico"` | Estático = un fotograma; dinámico = trayectoria. |
| `mano` | objeto o `null` | Obligatorio si `tipo` es `estatico`. |
| `pose` | objeto o `null` | Reservado (MediaPipe Pose, 33 puntos). Hoy: `null`. |
| `rostro` | objeto o `null` | Reservado (malla facial, ~478 puntos). Hoy: `null`. |
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
      "pose": null,
      "rostro": null
    }
  ]
}
```

`t` es el tiempo en segundos desde el inicio del gesto. El reconocedor
estático ignora este bloque; `predecir_dinamico()` compara `fotogramas`
con Dynamic Time Warping contra las plantillas `tipo: dinamico` **de la
misma categoría** (letra o palabra).

### `pose` y `rostro` (vocabulario completo)

Cuando existan, serán objetos con al menos `"landmarks": [ [x, y, z], ... ]`.
Hoy el validador acepta `null` o ese objeto.

**Ganchos (sin reescribir la UI):**

| Pieza | Rol |
| --- | --- |
| `innova/cuerpo.py` | `POSE_ACTIVA` / `ROSTRO_ACTIVO`, `extraer_pose()`, `extraer_rostro()`, `anotar_cuerpo()`. |
| `innova/pipeline.py` | Al capturar, llama `anotar_cuerpo(frame)` y guarda el resultado. |
| `innova/reconocimiento.py` | Al grabar una trayectoria en vivo, el fotograma también pasa por el gancho. |

Hoy esas funciones **devuelven `None`**. Para activarlas más adelante:

1. Implementa el detector MediaPipe Pose (33 landmarks) y/o Face Mesh.
2. Pon `POSE_ACTIVA` y/o `ROSTRO_ACTIVO` en `True`.
3. Llena el dict `{ "landmarks": [...] }` en `extraer_pose` / `extraer_rostro`.

Abecedario y Vocabulario no cambian de pantalla: el JSON ya tiene el hueco.

Mientras los ganchos estén apagados, **Vocabulario reconoce solo con la
mano**, igual que Abecedario, pero contra plantillas `categoria: "palabra"`.

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

En una captura real cada fotograma lleva su `mano` (y más adelante
`pose` / `rostro`). Cómo grabar esas secuencias desde el menú está en
[`menu-y-senas-dinamicas.md`](menu-y-senas-dinamicas.md).
