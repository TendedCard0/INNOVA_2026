# Esquema de datos de Mamatlatolli

Las plantillas y las futuras secuencias se guardan como JSON versionado
(`version: "1.0"`). Un mismo formato sirve para:

- una **muestra estática** (una pose, fase 2a);
- una **secuencia dinámica** (varios fotogramas, fase 2b / DTW).

Los campos `pose` y `rostro` ya existen para el vocabulario completo
(cuerpo y cara). En la fase 2a **siempre van en `null`**: solo corre el
detector de manos.

Los archivos viven en `datos/plantillas/` y se leen al arrancar
(`crear_reconocedor()`). La validación está en `innova/esquema.py`
(`validar_muestra`, `muestra_desde_dict`, `MuestraLSM.a_dict()`).

## Campos de una muestra

| Campo | Tipo | Notas |
| --- | --- | --- |
| `version` | string | Hoy `"1.0"`. Si cambia el formato, se sube el número. |
| `etiqueta` | string | Letra o glosa, en mayúsculas (`A`, `Ñ`, `HOLA`). |
| `tipo` | `"estatico"` \| `"dinamico"` | Estático = un fotograma; dinámico = trayectoria. |
| `mano` | objeto o `null` | Obligatorio si `tipo` es `estatico`. |
| `pose` | objeto o `null` | Reservado (MediaPipe Pose, 33 puntos). Fase 2a: `null`. |
| `rostro` | objeto o `null` | Reservado (malla facial). Fase 2a: `null`. |
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

### `secuencia` (fase 2b)

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
estático ignora este bloque; `ReconocedorEstatico.predecir_dinamico()` es
el gancho donde irá DTW.

### `pose` y `rostro` (vocabulario completo)

Cuando existan, serán objetos con al menos `"landmarks": [ [x, y, z], ... ]`.
Hoy el validador acepta `null` o ese objeto, y el pipeline **no** llena
ni uno ni otro.

### `metadatos`

| Campo | Tipo | Notas |
| --- | --- | --- |
| `marca_tiempo` | string ISO-8601 | UTC, obligatorio. |
| `fps` | número o `null` | Fotogramas por segundo de la captura. |
| `notas` | string | Texto libre. |
| `consentimiento` | boolean | Debe ser `true` si la seña es de una persona. |
| `origen` | string | `"camara"`, `"demo"` u otro. |

## Ejemplo estático (fase 2a)

```json
{
  "version": "1.0",
  "etiqueta": "A",
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

## Ejemplo dinámico (listo para 2b)

```json
{
  "version": "1.0",
  "etiqueta": "J",
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
    "notas": "Trayectoria; DTW en fase 2b",
    "consentimiento": true,
    "origen": "camara"
  }
}
```

En una captura real cada fotograma llevará su `mano` (y más adelante
`pose` / `rostro`).
