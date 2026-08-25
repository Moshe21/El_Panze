"""Normaliza las fechas de facturas_completas a formato YYYY-MM-DD.

Las facturas importadas desde PDF quedaron guardadas como 'DD/MM/YYYY'.
SQLite no entiende ese formato: date('12/12/2025') devuelve NULL, asi que
esas filas son invisibles para cualquier filtro por fecha (estadisticas
del dia, reportes, etc).

Este script se corre UNA vez. Es idempotente: despues de la primera
corrida los GLOB ya no encuentran nada, asi que volver a ejecutarlo
no hace dano.

    python system_pos/normalizar_fechas.py
"""
import os
import shutil
import sqlite3
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "pos_database.db")

# 'DD/MM/YYYY' -> 'YYYY-MM-DD'
GLOB_DDMMYYYY = '[0-3][0-9]/[0-1][0-9]/[0-9][0-9][0-9][0-9]'
# 'YYYY-MM-DD H:MM:SS' (hora sin cero a la izquierda) -> con cero
GLOB_HORA_CORTA = '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9]:[0-9][0-9]:[0-9][0-9]'


def respaldar():
    """Copia la base antes de tocarla. Devuelve la ruta del respaldo."""
    destino = os.path.join(
        BASE_DIR, "data", "pos_database.backup-%s.db" % date.today().strftime("%Y-%m-%d")
    )
    if os.path.exists(destino):
        raise RuntimeError(
            "Ya existe un respaldo de hoy: %s\n"
            "Borralo o movelo si realmente queres volver a migrar." % destino
        )
    shutil.copy2(DB_PATH, destino)
    print("Respaldo creado: %s" % destino)
    return destino


def migrar():
    if not os.path.exists(DB_PATH):
        raise RuntimeError("No se encontro la base: %s" % DB_PATH)

    # isolation_level=None -> sin transacciones implicitas, las manejamos aca
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    cursor = conn.cursor()

    # --- Estado antes ---
    cursor.execute("SELECT COUNT(*) FROM facturas_completas")
    total_filas = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM facturas_completas WHERE date(fecha) IS NULL")
    ilegibles_antes = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(subtotal) FROM facturas_completas")
    suma_antes = cursor.fetchone()[0]

    print("Antes de migrar")
    print("  filas totales     : %s" % total_filas)
    print("  fechas ilegibles  : %s" % ilegibles_antes)
    print("  SUM(subtotal)     : %s" % suma_antes)

    # Chequear antes de respaldar, para que una segunda corrida no falle
    # por respaldo duplicado sino que avise que no hay nada que hacer.
    if ilegibles_antes == 0:
        print("\nNo hay nada que migrar. La base ya esta normalizada.")
        conn.close()
        return

    respaldar()

    # --- Conversion, todo o nada ---
    try:
        cursor.execute("BEGIN")

        cursor.execute(
            """
            UPDATE facturas_completas
               SET fecha = substr(fecha,7,4) || '-' || substr(fecha,4,2) || '-' || substr(fecha,1,2)
             WHERE fecha GLOB ?
            """,
            (GLOB_DDMMYYYY,),
        )
        convertidas_fecha = cursor.rowcount

        cursor.execute(
            """
            UPDATE facturas_completas
               SET fecha = substr(fecha,1,11) || '0' || substr(fecha,12)
             WHERE fecha GLOB ?
            """,
            (GLOB_HORA_CORTA,),
        )
        convertidas_hora = cursor.rowcount

        # --- Verificar antes de confirmar ---
        cursor.execute("SELECT COUNT(*) FROM facturas_completas WHERE date(fecha) IS NULL")
        ilegibles_despues = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(subtotal) FROM facturas_completas")
        suma_despues = cursor.fetchone()[0]

        if ilegibles_despues != 0:
            cursor.execute("ROLLBACK")
            cursor.execute(
                "SELECT DISTINCT fecha FROM facturas_completas WHERE date(fecha) IS NULL LIMIT 10"
            )
            print("\nABORTADO: quedaron %s fechas sin convertir. No se cambio nada." % ilegibles_despues)
            print("Formatos no reconocidos:")
            for (valor,) in cursor.fetchall():
                print("   %r" % valor)
            conn.close()
            return

        if suma_despues != suma_antes:
            cursor.execute("ROLLBACK")
            print("\nABORTADO: SUM(subtotal) cambio (%s -> %s). No se cambio nada."
                  % (suma_antes, suma_despues))
            conn.close()
            return

        cursor.execute("COMMIT")

    except Exception:
        if conn.in_transaction:
            cursor.execute("ROLLBACK")
        conn.close()
        raise

    print("\nMigracion aplicada")
    print("  DD/MM/YYYY convertidas : %s" % convertidas_fecha)
    print("  horas sin cero          : %s" % convertidas_hora)
    print("  fechas ilegibles        : %s" % ilegibles_despues)
    print("  SUM(subtotal)           : %s  (sin cambios)" % suma_despues)

    # --- Dias recuperados ---
    cursor.execute(
        """
        SELECT date(fecha) d, COUNT(*) lineas, COUNT(DISTINCT num_factura) facturas
          FROM facturas_completas
         WHERE date(fecha) BETWEEN '2025-12-01' AND '2026-01-31'
         GROUP BY d ORDER BY d
        """
    )
    dias = cursor.fetchall()
    print("\nDias que ahora son consultables (%s):" % len(dias))
    for d, lineas, facturas in dias:
        print("   %s   %3s lineas   %3s facturas" % (d, lineas, facturas))

    conn.close()


if __name__ == "__main__":
    migrar()
