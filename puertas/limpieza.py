"""AIFEC — fábrica de plugins: puerta «limpieza» (nada de sobra, y nada que no se pueda publicar).

Cuatro cosas, ninguna de las cuales mira el validador del sistema de la misma manera:
1. Ningún fichero que no sea del plugin: paquetes comprimidos, mapas de código, `node_modules`, `vendor`,
   `composer.json`, ficheros de entorno, copias, registros, capturas y programas; y nada en la raíz que no sea
   una de las piezas por convenio de un plugin (`plugin.json`, `hooks.php`, `migrations/`, `views/`…).
2. Cabeceras: cada `.php` empieza **exactamente** por `<?php` y, en la línea siguiente, el bloque `/**` con su
   `@author` y su `@license`; los que no son vistas llevan además `declare(strict_types=1);`; sin BOM.
3. Ninguna credencial con pinta de real: claves largas en hexadecimal o base64 asignadas a algo que se llame
   `key`, `secret`, `token` o `password`, y los formatos de clave conocidos (`sk-…`, `ghp_…`, `AKIA…`, `AIza…`).
4. Ninguna dirección de correo que no sea de ejemplo (`.test`, `example.com`, `.invalid`…). Las de las líneas
   `@author` y `@copyright` de las cabeceras no cuentan.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

PAQUETES = (".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2", ".xz", ".phar")
SUELTOS = (".map", ".psd", ".ai", ".sketch", ".fig", ".log", ".bak", ".orig", ".swp", ".exe", ".dll", ".sh", ".bat", ".pem", ".key")
NOMBRES_DE_SOBRA = ("composer.json", "composer.lock", "package.json", "package-lock.json", "yarn.lock", ".env", ".ds_store", "thumbs.db")
CARPETAS_PROHIBIDAS = ("node_modules", "vendor", ".git", ".github", "capturas", "screenshots", "logs", "__pycache__")
IMAGENES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif")
# Lo que puede haber en la raíz de un plugin: las piezas por convenio (plan.md § 5) y la documentación.
RAIZ_PERMITIDA = ("plugin.json", "leeme.md", "readme.md", "license", "license.md", "changelog.md",
                  "hooks.php", "routes.php", "admin.php", "settings.php", "jobs.php", "cli.php", "blocks.php",
                  "migrations", "views", "lang", "assets", "mail", "src", "tests", "docs")
TEXTOS = (".php", ".json", ".md", ".js", ".css", ".txt", ".html", ".svg", ".xml", ".yml", ".yaml", ".ini", ".csv")

CABECERA = re.compile(r"\A<\?php\n/\*\*\n(?: \*[^\n]*\n)+? \*/\n")
CORREO = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)")
DOMINIOS_DE_EJEMPLO = ("example.com", "example.org", "example.net", "ejemplo.com")
SUFIJOS_DE_EJEMPLO = (".test", ".example", ".invalid", ".localhost", ".local")
LINEA_DE_AUTOR = re.compile(r"@(?:author|copyright|license|package|link|see)\b|[\"']author[\"']\s*[:=]", re.I)

ASIGNACION = re.compile(
    r"""(?ix)
    ['"]?[\w.\-]*(?:key|secret|token|passw(?:or)?d)[\w.\-]*['"]?    # algo que se llama key, secret, token o password
    \s*(?:=>|=|:)\s*
    ['"]([A-Za-z0-9+/_\-=]{24,})['"]                                 # y vale una cadena larga sin espacios
    """)
FORMATOS = (
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "clave con formato «sk-…»"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}"), "token de GitHub («ghp_…»)"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "clave de acceso de AWS («AKIA…»)"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "clave de API de Google («AIza…»)"),
    (re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}"), "token de Slack («xox…»)"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"), "una clave privada"),
)
DE_MENTIRA = ("mentira", "ejemplo", "example", "placeholder", "changeme", "xxxx", "your-", "your_", "tu-clave", "dummy", "fake", "test", "prueba")


def ficheros_de_sobra(carpeta: Path) -> list:
    """(ruta, motivo) de lo que no debería estar en un plugin."""
    sobra = []
    vistas = set()
    for ruta in sorted(carpeta.rglob("*")):
        relativa = ruta.relative_to(carpeta)
        partes = relativa.parts
        for pieza in partes:
            if pieza.lower() in CARPETAS_PROHIBIDAS and pieza.lower() not in vistas:
                vistas.add(pieza.lower())
                sobra.append((relativa.as_posix(), "carpeta que no es de un plugin («%s»)" % pieza))
        if any(p.lower() in CARPETAS_PROHIBIDAS for p in partes) or not ruta.is_file():
            continue
        sufijo = ruta.suffix.lower()
        if len(partes) == 1 and partes[0].lower() not in RAIZ_PERMITIDA:
            sobra.append((relativa.as_posix(), "no es una pieza de un plugin (en la raíz solo van plugin.json, las piezas por convenio y la documentación)"))
        elif sufijo in PAQUETES or ruta.name.lower().endswith(".tar.gz"):
            sobra.append((relativa.as_posix(), "un paquete comprimido"))
        elif sufijo in SUELTOS:
            sobra.append((relativa.as_posix(), "un fichero de trabajo (%s)" % sufijo))
        elif ruta.name.lower() in NOMBRES_DE_SOBRA:
            sobra.append((relativa.as_posix(), "un fichero de otra cosa («%s»): un plugin no lleva dependencias ni entorno propio" % ruta.name))
        elif sufijo in IMAGENES and partes[0] != "assets":
            sobra.append((relativa.as_posix(), "una imagen fuera de assets/ (¿una captura?)"))
    return sobra


def cabeceras_mal(carpeta: Path) -> list:
    """(fichero, motivo) de cada `.php` cuya cabecera no es la del proyecto."""
    mal = []
    for relativa in _comun.ficheros(carpeta, (".php",)):
        crudo = (carpeta / relativa).read_bytes()
        if crudo.startswith(b"\xef\xbb\xbf"):
            mal.append((relativa, "lleva marca BOM delante de <?php (escupe tres bytes al cargarse)"))
            continue
        if b"\r\n" in crudo:
            mal.append((relativa, "usa saltos de línea CRLF: el proyecto es LF"))
        texto = crudo.decode("utf-8", errors="replace").replace("\r\n", "\n")
        if not texto.startswith("<?php\n"):
            mal.append((relativa, "no empieza por «<?php» seguido de salto de línea"))
            continue
        encontrada = CABECERA.match(texto)
        if not encontrada:
            mal.append((relativa, "tras «<?php» tiene que ir enseguida el bloque «/**» de la cabecera (sin línea en blanco)"))
            continue
        bloque = encontrada.group(0)
        if "@author" not in bloque or "@license" not in bloque:
            mal.append((relativa, "la cabecera no trae «@author» y «@license»"))
        es_vista = relativa.startswith("views/") or relativa.startswith("mail/")
        if not es_vista and "declare(strict_types=1);" not in texto[:1500]:
            mal.append((relativa, "falta «declare(strict_types=1);» tras la cabecera"))
    return mal


def _parece_real(valor: str) -> bool:
    """Una cadena larga que parece una clave y no una palabra: mezcla letras y cifras, y no dice «ejemplo»."""
    minuscula = valor.lower()
    if any(marca in minuscula for marca in DE_MENTIRA):
        return False
    tiene_cifra = any(c.isdigit() for c in valor)
    tiene_letra = any(c.isalpha() for c in valor)
    if not (tiene_cifra and tiene_letra):
        return False
    return len(set(valor)) >= 8  # «aaaa1111aaaa1111aaaa1111» no es una clave


def credenciales(carpeta: Path) -> list:
    """(fichero, línea, descripción) de cada credencial con pinta de real."""
    encontradas = []
    for relativa in _comun.ficheros(carpeta):
        if Path(relativa).suffix.lower() not in TEXTOS:
            continue
        for numero, linea in enumerate(_comun.leer_texto(carpeta / relativa).splitlines(), 1):
            for patron, que in FORMATOS:
                if patron.search(linea):
                    encontradas.append((relativa, numero, que))
            for coincidencia in ASIGNACION.finditer(linea):
                if _parece_real(coincidencia.group(1)):
                    encontradas.append((relativa, numero, "una cadena con pinta de clave asignada a un nombre secreto"))
    return encontradas


def correos_reales(carpeta: Path) -> list:
    """(fichero, línea, dirección) de cada correo que no es de ejemplo."""
    encontrados = []
    for relativa in _comun.ficheros(carpeta):
        if Path(relativa).suffix.lower() not in TEXTOS:
            continue
        for numero, linea in enumerate(_comun.leer_texto(carpeta / relativa).splitlines(), 1):
            if LINEA_DE_AUTOR.search(linea):
                continue
            for coincidencia in CORREO.finditer(linea):
                dominio = coincidencia.group(1).lower()
                if dominio in DOMINIOS_DE_EJEMPLO or dominio.endswith(SUFIJOS_DE_EJEMPLO):
                    continue
                encontrados.append((relativa, numero, coincidencia.group(0)))
    return encontrados


def puerta(ctx) -> int:
    carpeta = ctx.candidato
    if not carpeta.is_dir():
        raise _comun.NoPasa("no hay candidato en %s" % carpeta)
    problemas = []
    for relativa, motivo in ficheros_de_sobra(carpeta):
        problemas.append("%s: %s" % (relativa, motivo))
    for relativa, motivo in cabeceras_mal(carpeta):
        problemas.append("%s: %s" % (relativa, motivo))
    for relativa, numero, que in credenciales(carpeta):
        problemas.append("%s:%d trae %s" % (relativa, numero, que))
    for relativa, numero, direccion in correos_reales(carpeta):
        problemas.append("%s:%d trae una dirección de correo que no es de ejemplo (%s)" % (relativa, numero, direccion))
    medidas = {"ficheros": len(_comun.ficheros(carpeta)), "problemas": len(problemas)}
    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas, medidas)
    return ctx.terminar(_comun.PASA, "plugin limpio: %d ficheros, cabeceras correctas, sin credenciales ni correos reales" % medidas["ficheros"], [], medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("limpieza", puerta))
