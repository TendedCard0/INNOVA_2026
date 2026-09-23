# Empaquetar Mamatlatolli para Windows

Mamatlatolli se entrega como un **instalador** `Mamatlatolli-Setup.exe`. Quien lo ejecuta instala el programa, lo abre desde el menú Inicio o el escritorio, y lo desinstala desde Configuración de Windows → Aplicaciones. El icono del Setup, de la ventana y de los accesos directos es `assets/icono.ico`.

Hay además un ZIP portable (`Mamatlatolli-portable.zip`). Es un extra: no sustituye al instalador.

Este repositorio se puede editar en Linux. **El `.exe` no se cruza de sistema**: lo construye Windows (tu PC o GitHub Actions). Aquí no hay un binario fingido.

## Qué instala y dónde guarda las señas

Por omisión la instalación es **por usuario**. No hace falta ser administrador, que es lo práctico en un laboratorio escolar.

| Qué | Dónde |
| --- | --- |
| Programa (exe, modelos, logo, sonidos) | `%LOCALAPPDATA%\Programs\Mamatlatolli` |
| Señas, configuración y récord | `%LOCALAPPDATA%\Mamatlatolli` |

Ejemplo: `C:\Users\ana\AppData\Local\Mamatlatolli\plantillas` y `C:\Users\ana\AppData\Local\Mamatlatolli\config.json` (`tema` y `record_practica`).

Esa segunda carpeta es escribible. El programa no guarda plantillas dentro de su carpeta de instalación, así que sigue funcionando si algún día se instala en `Archivos de programa`. Exportar e importar (Biblioteca de señas, o `python -m innova.exportar` / `python -m innova.importar` en desarrollo) leen y escriben esa misma biblioteca. Los diálogos abren en Documentos para que el archivo `.mamatlatolli` quede fácil de copiar a otra computadora.

Desinstalar **no** borra las señas ni el récord. Para empezar de cero, borra `%LOCALAPPDATA%\Mamatlatolli` después de desinstalar.

Cada usuario de Windows tiene su propia biblioteca. Dos cuentas en el mismo equipo no comparten señas; para pasarlas, se exporta e importa.

Si el laboratorio prefiere una sola copia en `C:\Program Files\Mamatlatolli` (pide administrador), el build acepta `--maquina`. Los datos de cada estudiante siguen en su `%LOCALAPPDATA%\Mamatlatolli`.

En desarrollo no cambia el flujo:

```bash
python app.py
python -m innova
```

Ahí las señas siguen en `datos/plantillas/` del repositorio y la configuración en `datos/config.json`. `MAMATLATOLLI_DATOS` fuerza otra carpeta si se define **antes** de arrancar.

La app instalada no abre consola. Si se cierra por un error, el detalle queda en `%LOCALAPPDATA%\Mamatlatolli\mamatlatolli.log` y aparece un cuadro de aviso.

## Cómo lo baja Fernando (sin compilar)

1. En GitHub, abre **Actions** → **Instalador Windows de Mamatlatolli**.
2. Elige el run del pull request, o el de `main`, o pulsa **Run workflow** si quieres lanzarlo a mano.
3. Cuando termine en verde, baja el artifact **Mamatlatolli-Windows**.
4. Dentro del ZIP del artifact están:
   - `Mamatlatolli-Setup.exe` — el instalador.
   - `Mamatlatolli-portable.zip` — la carpeta suelta, por si hace falta copiarla sin instalar.

El workflow corre en `windows-latest` cada vez que hay un pull request, un push a `main`, o un lanzamiento manual. También corre las pruebas de `tests/` antes de empaquetar.

## SmartScreen

El instalador **no está firmado** con un certificado de código. Windows SmartScreen puede decir que el publicador es desconocido y bloquear el primer arranque. No es un fallo del programa: es la falta de firma.

En el aviso: **Más información** → **Ejecutar de todas formas**. Conviene avisar de esto en el salón antes de la demo. Una firma de código (certificado de pago) quita el aviso; no hace falta para probar Mamatlatolli.

## Construir en una PC con Windows

Hace falta Windows 10 o posterior, de 64 bits, y Python 3.11 (3.10 o 3.12 también sirven con estas dependencias).

En PowerShell, desde la raíz del repositorio:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r empaquetado\requirements-build.txt
```

Instala [Inno Setup 6.7.3](https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe) (el compilador queda en `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`). Si lo instalas en otra ruta, define la variable `ISCC` con la ruta de `ISCC.exe`.

Construye:

```powershell
python empaquetado\construir.py
```

O el atajo `empaquetado\construir.ps1`. Para Program Files:

```powershell
python empaquetado\construir.py --maquina
```

Salida:

- `dist\Mamatlatolli-Setup.exe`
- `dist\Mamatlatolli-portable.zip`
- `dist\Mamatlatolli\` — carpeta que mete el instalador (no hace falta repartirla suelta)

`python empaquetado\construir.py --comprobar` solo revisa que estén el spec, el script de Inno Setup, el icono y los sonidos. No crea un `.exe`. En Linux o macOS el comando sin `--comprobar` se detiene y explica cómo bajar el artifact; no inventa un instalador.

## Qué entra en el ejecutable

PyInstaller (`empaquetado/mamatlatolli.spec`) arma una carpeta, no un único exe que se descomprime en cada arranque: MediaPipe y OpenCV arrancan mejor así. El instalador de Inno Setup (`empaquetado/mamatlatolli.iss`) envuelve esa carpeta.

Van dentro:

- el código de `innova/` y el punto de entrada `app.py`;
- OpenCV, MediaPipe, numpy, CustomTkinter, Pillow y el audio de Windows (`winsound`);
- `assets/` (logo, `icono.ico`, `icono.png`, sonidos).

No van las señas ni `datos/config.json` de quien compiló. Esas se quedan en la computadora de cada estudiante.

## Permiso de la cámara

Después de instalar, si Windows pregunta por la cámara, el nombre es **Mamatlatolli** (no Python). En Configuración → Privacidad y seguridad → Cámara, el acceso de escritorio tiene que estar permitido.
