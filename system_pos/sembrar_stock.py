"""Crea las tablas de stock y siembra las recetas de cada producto.

La cantidad de cada materia prima vive en la tabla `stock`, una fila por
categoria. Lo que gasta cada producto vive en `producto_stock`: la doble
gasta 2 bolas, la mixta gasta 1 bola y 1 pechuga, el sandwiche especial
gasta 3 materiales distintos.

Se corre UNA vez, desde donde sea (usa ruta absoluta desde __file__):

    python system_pos/sembrar_stock.py

Es idempotente: el reemplazo de recetas es por producto, y las
cantidades de `stock` solo se crean si la categoria no existia. Volver a
correrlo no duplica nada ni pisa un conteo ya hecho.

IMPORTANTE: las cantidades arrancan en CERO a proposito. Los numeros que
hay hoy en productos.stock (1856 bolas, 2801 pechugas) vienen de usar
"rellenar stock" y estan inflados; sembrar con ellos haria que el sistema
no detecte un faltante en anos. Se fijan con el conteo fisico real desde
Administracion -> Reponer insumos.

SI ALGO SALE MAL: `DELETE FROM producto_stock;` deja todos los productos
sin receta. Nada se descuenta, pero la caja sigue vendiendo con
normalidad. Es el interruptor de emergencia.
"""
import os
import shutil
import sqlite3
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "pos_database.db")

# (producto_id, nombre_esperado, [(categoria, cantidad), ...])
# El nombre se verifica contra la base: si no coincide, el script aborta.
# Asi un id que signifique otra cosa en otra instalacion no destroza nada.
RECETAS = [
    (1,  "H Pechuga de Pollo",   [("pechuga", 1)]),
    (2,  "H Especial",           [("Bola de carne", 1)]),
    (4,  "H Doble Carne",        [("Bola de carne", 2)]),
    (5,  "Sandwich de la casa",  [("Carnes", 1)]),
    (6,  "Twister",              [("pechuga", 1)]),
    (7,  "Mazorcas Especial",    [("Carnes", 1), ("maiz", 1)]),
    (8,  "Panze",                [("Panze", 1)]),
    (11, "Adicciones",           [("Adicionales", 1)]),      # "queso o vegetales"
    (12, "Papa a la Francesa",   [("papa", 1)]),
    (13, "Costo Recipiente",     [("desechables J1", 1)]),
    (14, "Bebida",               [("Bebidas", 1)]),
    (15, "gaseosa 1L",           [("bebidas 1,5L", 1)]),     # "Bebidas 1,5L"
    (21, "Choriperro",           [("Chorizo", 1)]),
    (22, "Choriperro Especial",  [("Chorizo", 1), ("tocineta", 1)]),
    (23, "DOMICILIO CERCA",      [("DOMI", 1)]),
    (24, "DOMICILIO ZONA",       [("DOMI", 1)]),
    (35, "Sandwich desmechada",  [("Desmechada", 1), ("maiz", 1)]),
    (36, "Costillas Cerdo",      [("al horno", 1)]),
    (37, "Salchipapa",           [("Chorizo", 1)]),
    (38, "Salchipapas Espacial", [("Chorizo", 1), ("Carnes", 1)]),
    (39, "hamburgesa mixta",     [("Bola de carne", 1), ("pechuga", 1)]),
    (40, "chorizo",              [("Chorizo", 1)]),
    (41, "bebida",               [("bebida", 1)]),
    (43, "COCA-COLA 3L",         [("COCA-COLA 3L", 1)]),
    (45, "GASTOS INSUMO",        [("GASTO", 1)]),
    (46, "H TRIPLE RES",         [("Bola de carne", 3)]),
    (47, "H TRIPE POLLO",        [("Bola de carne", 2), ("pechuga", 1)]),
    # El CSV declaraba 2 items pero lista tres materiales: se toman los tres.
    (48, "SANDWICHE ESPECIALES", [("Carnes", 1), ("Desmechada", 1), ("maiz", 1)]),
    (50, "AJI ORGANICO",         [("AJI", 1)]),
    (56, "Tinto",                [("tinto", 1)]),
    (57, "JUGO NAT AGUA",        [("PULPA", 1)]),
    (58, "JUGO NAT LECHE",       [("PULPA", 1), ("LECHE", 1)]),
]

# Productos que quedan SIN receta a proposito: no descuentan nada al
# venderse. Son los dos que estan ocultos con stock -10.
#   9  Panze Pollo con Champinones
#   10 Mexicano


def crear_tablas(cursor):
    """Mismo DDL que db_manager._crear_tablas_stock.

    Se duplica a proposito: el script NO importa db_manager para no
    arrastrar su ruta relativa DATABASE_NAME, que depende del cwd.
    """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            categoria TEXT PRIMARY KEY COLLATE NOCASE,
            cantidad REAL NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS producto_stock (
            producto_id INTEGER NOT NULL,
            categoria TEXT NOT NULL COLLATE NOCASE,
            cantidad REAL NOT NULL,
            PRIMARY KEY (producto_id, categoria)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            categoria TEXT NOT NULL,
            cantidad REAL NOT NULL,
            num_factura TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stockmov_fecha ON stock_movimientos(fecha_hora)')


def respaldar():
    """Copia la base antes de tocarla. Devuelve la ruta del respaldo."""
    destino = os.path.join(
        BASE_DIR, "data",
        "pos_database.backup-stock-%s.db" % date.today().strftime("%Y-%m-%d"))
    if os.path.exists(destino):
        print("Ya existe un respaldo de hoy: %s" % os.path.basename(destino))
        return destino
    shutil.copy2(DB_PATH, destino)
    print("Respaldo creado: %s" % destino)
    return destino


def verificar_productos(cursor):
    """Lista de problemas si algun id no existe o cambio de nombre."""
    problemas = []
    for producto_id, nombre_esperado, _receta in RECETAS:
        cursor.execute("SELECT nombre FROM productos WHERE id = ?", (producto_id,))
        fila = cursor.fetchone()
        if fila is None:
            problemas.append("id %s no existe (esperado %r)" % (producto_id, nombre_esperado))
        elif str(fila[0]).strip().lower() != nombre_esperado.strip().lower():
            problemas.append("id %s se llama %r, no %r" % (producto_id, fila[0], nombre_esperado))
    return problemas


def sembrar():
    if not os.path.exists(DB_PATH):
        raise RuntimeError("No se encontro la base: %s" % DB_PATH)

    # isolation_level=None -> sin transacciones implicitas, se manejan aca
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.text_factory = lambda b: b.decode("utf-8", "replace")
    cursor = conn.cursor()

    # --- Invariantes que este script NO debe tocar ---
    cursor.execute("SELECT COUNT(*) FROM productos")
    productos_antes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ventas")
    ventas_antes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM facturas")
    facturas_antes = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(valor_total), 0) FROM facturas")
    suma_antes = cursor.fetchone()[0]

    print("Antes de sembrar")
    print("  productos        : %s" % productos_antes)
    print("  ventas           : %s" % ventas_antes)
    print("  facturas         : %s" % facturas_antes)
    print("  SUM(valor_total) : %s" % suma_antes)
    print()

    crear_tablas(cursor)   # DDL idempotente, fuera de la transaccion

    problemas = verificar_productos(cursor)
    if problemas:
        print("ABORTADO: los ids de producto no coinciden con la base.")
        for p in problemas:
            print("   %s" % p)
        print("\nRevisa RECETAS antes de volver a correr. No se cambio nada.")
        conn.close()
        return

    categorias = []
    for _pid, _nom, receta in RECETAS:
        for categoria, _cant in receta:
            if categoria.lower() not in [c.lower() for c in categorias]:
                categorias.append(categoria)

    respaldar()
    print()

    try:
        cursor.execute("BEGIN")

        # 1. Categorias en stock, arrancando en cero. Solo las que faltan:
        #    nunca se pisa una cantidad ya contada.
        nuevas = 0
        for categoria in categorias:
            cursor.execute("SELECT 1 FROM stock WHERE categoria = ?", (categoria,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO stock (categoria, cantidad) VALUES (?, 0)",
                               (categoria,))
                nuevas += 1
        print("Categorias en stock: %s (%s nuevas)" % (len(categorias), nuevas))

        # 2. Recetas: reemplazo total por producto, asi el script es la
        #    fuente de verdad y corre las veces que haga falta.
        lineas = 0
        for producto_id, _nombre, receta in RECETAS:
            cursor.execute("DELETE FROM producto_stock WHERE producto_id = ?", (producto_id,))
            for categoria, cantidad in receta:
                cursor.execute(
                    "INSERT INTO producto_stock (producto_id, categoria, cantidad) VALUES (?, ?, ?)",
                    (producto_id, categoria, float(cantidad)))
                lineas += 1
        print("Lineas de receta escritas: %s en %s productos" % (lineas, len(RECETAS)))

        # --- Verificar que no se toco nada de ventas antes de confirmar ---
        cursor.execute("SELECT COUNT(*) FROM productos")
        productos_desp = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ventas")
        ventas_desp = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM facturas")
        facturas_desp = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(valor_total), 0) FROM facturas")
        suma_desp = cursor.fetchone()[0]

        if (productos_desp, ventas_desp, facturas_desp, suma_desp) != \
           (productos_antes, ventas_antes, facturas_antes, suma_antes):
            cursor.execute("ROLLBACK")
            print("\nABORTADO: el script toco datos de venta. No se cambio nada.")
            conn.close()
            return

        cursor.execute("COMMIT")

    except Exception:
        if conn.in_transaction:
            cursor.execute("ROLLBACK")
        conn.close()
        raise

    # --- Reporte ---
    print("\nSiembra aplicada.\n")
    cursor.execute('''
        SELECT p.id, p.nombre, ps.categoria, ps.cantidad
          FROM producto_stock AS ps
          JOIN productos AS p ON p.id = ps.producto_id
         ORDER BY p.id, ps.categoria
    ''')
    print("Recetas:")
    actual = None
    for pid, pnom, categoria, cantidad in cursor.fetchall():
        if pid != actual:
            print("  %-3s %s" % (pid, pnom.strip()))
            actual = pid
        print("        -> %-16s x%g" % (categoria, cantidad))

    cursor.execute("SELECT categoria, cantidad FROM stock ORDER BY categoria COLLATE NOCASE")
    print("\nCantidades (fijalas con el conteo fisico):")
    for categoria, cantidad in cursor.fetchall():
        print("  %-18s %10.0f" % (categoria, cantidad))

    conn.close()


if __name__ == "__main__":
    sembrar()
