"""Pose y rostro de Vocabulario: esquema, fusión y fallback a null."""

from __future__ import annotations

import unittest

import numpy as np

from innova.camara import esqueleto_mano_normalizado
from innova.caracteristicas import (
    DIM_FUSION_DINAMICA,
    DIM_POSE,
    DIM_ROSTRO,
    ErrorCaracteristicas,
    distancia,
    distancia_fusion_dinamica,
    distancia_partes,
    extraer_vector,
    normalizar_pose,
    vector_dinamico_fusion,
    vector_pose,
    vector_pose_opcional,
    vector_rostro,
    vector_rostro_opcional,
)
from innova.cuerpo import (
    N_LANDMARKS_POSE,
    N_LANDMARKS_ROSTRO,
    POSE_ACTIVA,
    ROSTRO_ACTIVO,
    _cache,
    _estado,
    anotar_cuerpo,
    bloque_desde_puntos,
    cuerpo_disponible,
    extraer_pose,
    extraer_rostro,
)
from innova.detector import ManoDetectada, Punto
from innova.esquema import muestra_estatica_desde_mano, muestra_desde_dict, validar_muestra
from innova.overlay import dibujar_cuerpo


def _mano() -> ManoDetectada:
    xy = esqueleto_mano_normalizado(0.5, 0.62, 0.22, 0.0, 0.0)
    return ManoDetectada(
        puntos=[Punto(x, y, 0.0) for x, y in xy],
        lateralidad="derecha",
        puntuacion=1.0,
    )


def _pose(muneca_y: float = 0.55, dx: float = 0.0) -> dict:
    pts = [[0.5 + dx, 0.5, 0.0] for _ in range(N_LANDMARKS_POSE)]
    pts[11] = [0.40 + dx, 0.35, 0.0]
    pts[12] = [0.60 + dx, 0.35, 0.0]
    pts[23] = [0.42 + dx, 0.70, 0.0]
    pts[24] = [0.58 + dx, 0.70, 0.0]
    pts[15] = [0.28 + dx, muneca_y, 0.0]
    return {"landmarks": pts, "visibilidad": [0.95] * N_LANDMARKS_POSE}


def _rostro(apertura: float = 0.0) -> dict:
    pts = [[0.50, 0.50, 0.0] for _ in range(N_LANDMARKS_ROSTRO)]
    pts[1] = [0.50, 0.48, 0.0]
    pts[33] = [0.42, 0.45, 0.0]
    pts[263] = [0.58, 0.45, 0.0]
    pts[13] = [0.50, 0.58, 0.0]
    pts[14] = [0.50, 0.64 + apertura, 0.0]
    pts[61] = [0.44, 0.61, 0.0]
    pts[291] = [0.56, 0.61, 0.0]
    return {"landmarks": pts}


class _Marca:
    def __init__(self, i: int, n: int) -> None:
        self.x = 0.2 + (i / max(1, n)) * 0.5
        self.y = 0.3
        self.z = -0.01 * i
        self.visibility = 0.9


class _Lista:
    def __init__(self, n: int) -> None:
        self.landmark = [_Marca(i, n) for i in range(n)]


class _ResultadoPose:
    def __init__(self, n: int | None) -> None:
        self.pose_landmarks = None if n is None else _Lista(n)


class _ResultadoRostro:
    def __init__(self, n: int | None) -> None:
        self.multi_face_landmarks = [] if n is None else [_Lista(n)]


class _ModeloFalso:
    def __init__(self, resultado: object, explota: bool = False) -> None:
        self._resultado = resultado
        self._explota = explota
        self.cerrado = False

    def process(self, rgb: np.ndarray) -> object:
        del rgb
        if self._explota:
            raise RuntimeError("grafo simulado")
        return self._resultado

    def close(self) -> None:
        self.cerrado = True


class TestEsquemaYFusión(unittest.TestCase):
    def test_bloque_llena_muestra_de_palabra(self) -> None:
        pose = bloque_desde_puntos(
            _pose()["landmarks"],
            visibilidad=[0.8] * N_LANDMARKS_POSE,
            minimo=N_LANDMARKS_POSE,
            maximo=N_LANDMARKS_POSE,
        )
        rostro = bloque_desde_puntos(_rostro()["landmarks"], minimo=468)
        assert pose is not None and rostro is not None
        self.assertEqual(len(pose["landmarks"]), 33)
        self.assertEqual(len(pose["visibilidad"]), 33)
        self.assertEqual(len(rostro["landmarks"]), 478)

        muestra = muestra_estatica_desde_mano(
            _mano(),
            "hola",
            categoria="palabra",
            pose=pose,
            rostro=rostro,
        )
        bruto = muestra.a_dict()
        self.assertEqual(validar_muestra(bruto), [])
        self.assertEqual(bruto["categoria"], "palabra")
        self.assertEqual(len(bruto["pose"]["landmarks"]), 33)
        self.assertEqual(len(bruto["rostro"]["landmarks"]), 478)
        recuperada = muestra_desde_dict(bruto)
        self.assertEqual(len(recuperada.pose["landmarks"]), 33)
        self.assertIn("visibilidad", recuperada.pose)

    def test_pose_invariante_a_traslacion_y_sensible_al_brazo(self) -> None:
        quieta = vector_pose(_pose(0.55, dx=0.0))
        movida = vector_pose(_pose(0.55, dx=0.25))
        np.testing.assert_allclose(quieta, movida, atol=1e-6)
        self.assertEqual(quieta.shape, (DIM_POSE,))
        brazo = vector_pose(_pose(0.15, dx=0.0))
        self.assertGreater(float(np.linalg.norm(quieta - brazo)), 0.05)
        norm = normalizar_pose(_pose())
        self.assertAlmostEqual(float(np.linalg.norm(norm[11] - norm[12])), 1.0, places=5)

    def test_rostro_normalizado_y_fusion_estatica(self) -> None:
        cara = vector_rostro(_rostro(0.0))
        self.assertEqual(cara.shape, (DIM_ROSTRO,))
        abierta = vector_rostro(_rostro(0.08))
        self.assertGreater(float(np.linalg.norm(cara - abierta)), 0.01)

        mano_a = extraer_vector(_mano().puntos)
        mano_b = extraer_vector(_mano().puntos)
        solo_mano = distancia(mano_a, mano_b)
        sin_cuerpo = distancia_partes(mano_a, mano_b, vector_pose(_pose()), None, None, None)
        self.assertAlmostEqual(sin_cuerpo, solo_mano, places=6)

        misma = distancia_partes(
            mano_a, mano_b, vector_pose(_pose(0.55)), vector_pose(_pose(0.55)), cara, cara
        )
        distinta = distancia_partes(
            mano_a,
            mano_b,
            vector_pose(_pose(0.55)),
            vector_pose(_pose(0.15)),
            cara,
            abierta,
        )
        self.assertAlmostEqual(misma, 0.0, places=6)
        self.assertGreater(distinta, misma)

    def test_pose_degenerada_no_rompe_la_fusion(self) -> None:
        self.assertIsNone(vector_pose_opcional({"landmarks": [[0.0, 0.0, 0.0]] * 3}))
        self.assertIsNone(vector_rostro_opcional(None))
        self.assertIsNone(vector_rostro_opcional({"landmarks": [[0.2, 0.2, 0.0]] * 10}))
        mano = extraer_vector(_mano().puntos)
        d = distancia_partes(mano, mano, None, None, None, None)
        self.assertAlmostEqual(d, 0.0, places=6)
        with self.assertRaises(ErrorCaracteristicas):
            distancia_partes(None, None, None, None, None, None)

    def test_vector_dinamico_ignora_bloques_ausentes(self) -> None:
        origen = np.array([0.5, 0.62])
        completo = vector_dinamico_fusion(_mano().puntos, origen, 0.2, _pose(), _rostro())
        sin_cara = vector_dinamico_fusion(_mano().puntos, origen, 0.2, _pose(), None)
        self.assertEqual(completo.shape, (DIM_FUSION_DINAMICA,))
        self.assertTrue(np.all(np.isfinite(completo)))
        self.assertTrue(np.all(np.isnan(sin_cara[-DIM_ROSTRO:])))
        d = distancia_fusion_dinamica(completo, sin_cara)
        # La cara falta en un lado: la distancia usa mano y pose, que coinciden.
        self.assertAlmostEqual(d, 0.0, places=6)
        otro = vector_dinamico_fusion(_mano().puntos, origen, 0.2, _pose(0.15), _rostro())
        self.assertGreater(distancia_fusion_dinamica(completo, otro), 0.01)


class TestFallback(unittest.TestCase):
    def test_conteos_y_ganchos_activos(self) -> None:
        self.assertTrue(POSE_ACTIVA)
        self.assertTrue(ROSTRO_ACTIVO)
        self.assertEqual(N_LANDMARKS_POSE, 33)
        self.assertEqual(N_LANDMARKS_ROSTRO, 478)
        self.assertTrue(cuerpo_disponible())

    def test_frame_vacio_es_null(self) -> None:
        self.assertIsNone(extraer_pose(None))
        self.assertIsNone(extraer_rostro(None))
        self.assertEqual(anotar_cuerpo(None), (None, None))
        raro = np.zeros((8, 8), dtype=np.uint8)
        self.assertEqual(anotar_cuerpo(raro), (None, None))

    def test_modelo_simulado_llena_y_un_fallo_no_tumba(self) -> None:
        previo = (
            _estado.intentado,
            _estado.pose,
            _estado.rostro,
            _estado.error_pose,
            _estado.error_rostro,
            _cache.clave,
        )
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        try:
            _estado.intentado = True
            _estado.pose = _ModeloFalso(_ResultadoPose(33))
            _estado.rostro = _ModeloFalso(_ResultadoRostro(478))
            _cache.clave = None
            pose = extraer_pose(frame)
            rostro = extraer_rostro(frame)
            assert pose is not None and rostro is not None
            self.assertEqual(len(pose["landmarks"]), 33)
            self.assertEqual(len(pose["visibilidad"]), 33)
            self.assertEqual(len(rostro["landmarks"]), 478)
            self.assertEqual(anotar_cuerpo(frame)[0], pose)

            _estado.pose = _ModeloFalso(_ResultadoPose(None), explota=True)
            _estado.rostro = _ModeloFalso(_ResultadoRostro(None))
            _cache.clave = None
            self.assertIsNone(extraer_pose(frame))
            self.assertIsNone(extraer_rostro(frame))
            self.assertEqual(anotar_cuerpo(frame), (None, None))
        finally:
            (
                _estado.intentado,
                _estado.pose,
                _estado.rostro,
                _estado.error_pose,
                _estado.error_rostro,
                _cache.clave,
            ) = previo

    def test_si_no_hay_modelo_devuelve_null(self) -> None:
        previo = (
            _estado.intentado,
            _estado.pose,
            _estado.rostro,
            _estado.error_pose,
            _estado.error_rostro,
            _cache.clave,
        )
        try:
            _estado.intentado = True
            _estado.pose = None
            _estado.rostro = None
            _estado.error_pose = "simulado"
            _estado.error_rostro = "simulado"
            _cache.clave = None
            frame = np.zeros((32, 40, 3), dtype=np.uint8)
            self.assertIsNone(extraer_pose(frame))
            self.assertIsNone(extraer_rostro(frame))
            self.assertEqual(anotar_cuerpo(frame), (None, None))
            self.assertFalse(cuerpo_disponible())
        finally:
            (
                _estado.intentado,
                _estado.pose,
                _estado.rostro,
                _estado.error_pose,
                _estado.error_rostro,
                _cache.clave,
            ) = previo
            _cache.clave = None


class TestOverlayCuerpo(unittest.TestCase):
    def test_dibuja_esqueleto_y_cara(self) -> None:
        base = np.zeros((120, 160, 3), dtype=np.uint8)
        pintado = dibujar_cuerpo(base.copy(), _pose(), _rostro())
        self.assertEqual(pintado.shape, base.shape)
        self.assertGreater(int(pintado.sum()), 0)
        self.assertEqual(int(dibujar_cuerpo(base, None, None).sum()), 0)
