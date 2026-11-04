"""
Respaldo automatico de la base de datos del POS.

Hace una copia CONSISTENTE usando la API de backup de SQLite, que es segura
aunque el POS este abierto y entre una venta en ese momento (una copia de
archivo normal puede salir partida).

Los respaldos se guardan FUERA del repositorio de git, para que ninguna
operacion de git o de GitHub Desktop pueda borrarlos.

Uso:
    python respaldar_bd.py            # un respaldo ahora
    python respaldar_bd.py --silencio # sin imprimir nada (para tareas programadas)

Para que corra solo al abrir el POS, agregar al final de "EL PANZE POS.bat":
    python respaldar_bd.py --silencio
"""

import os
import sys
import sqlite3
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.join(BASE_DIR, "data", "pos_database.db")

# Fuera del repositorio a proposito.
DESTINO_DIR = os.path.join(os.path.expanduser("~"), "Documents", "RESPALDOS_POS")

# Cuantos respaldos conservar antes de ir borrando los mas viejos.
CONSERVAR = 30


def respaldar(silencio=False):
    def log(msg):
        if not silencio:
            print(msg)

    if not os.path.exists(ORIGEN):
        log(f"ERROR: no se encontro la base en {ORIGEN}")
        return None

    os.makedirs(DESTINO_DIR, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = os.path.join(DESTINO_DIR, f"pos_database_{sello}.db")

    origen_cn = sqlite3.connect(f"file:{ORIGEN}?mode=ro", uri=True)
    destino_cn = sqlite3.connect(destino)
    try:
        with destino_cn:
            origen_cn.backup(destino_cn)
    finally:
        destino_cn.close()
        origen_cn.close()

    # Verificar que el respaldo sirve antes de darlo por bueno.
    v = sqlite3.connect(f"file:{destino}?mode=ro", uri=True)
    try:
        integridad = v.execute("PRAGMA integrity_check").fetchone()[0]
        lineas = v.execute("select count(*) from facturas_completas").fetchone()[0]
        ultima = v.execute(
            "select num_factura from facturas_completas order by id desc limit 1"
        ).fetchone()
    finally:
        v.close()

    if integridad != "ok":
        log(f"ERROR: el respaldo salio corrupto ({integridad}). Se elimina.")
        os.remove(destino)
        return None

    log(f"Respaldo OK  {os.path.basename(destino)}")
    log(f"  {lineas:,} lineas, ultima factura #{ultima[0] if ultima else '?'}")

    _rotar(log)
    return destino


def _rotar(log):
    """Deja solo los CONSERVAR mas recientes."""
    copias = sorted(
        (f for f in os.listdir(DESTINO_DIR)
         if f.startswith("pos_database_") and f.endswith(".db")),
        reverse=True,
    )
    for viejo in copias[CONSERVAR:]:
        try:
            os.remove(os.path.join(DESTINO_DIR, viejo))
            log(f"  rotado (borrado el mas viejo): {viejo}")
        except OSError as e:
            log(f"  no se pudo rotar {viejo}: {e}")


if __name__ == "__main__":
    respaldar(silencio="--silencio" in sys.argv)
