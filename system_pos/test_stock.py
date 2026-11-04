"""Pruebas del descuento de materias primas por receta.

    cd system_pos
    python -m unittest test_stock -v

Se corre desde system_pos/ porque db_manager.connect_db() usa la ruta
RELATIVA DATABASE_NAME. Ese mismo detalle es la palanca de PR-02: basta
con apuntar DATABASE_NAME a un archivo temporal para que todas las
funciones del modulo escriban ahi y nunca en la base de produccion.

Se usa `import db_manager` (no `from system_pos import db_manager`) a
proposito: asi es el mismo objeto de modulo que ve ui_manager, y un
patch aqui vale alla.
"""
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import db_manager


# ---------------------------------------------------------------------
# PR-01 - Unitaria - Funcional - Confirmacion
# ---------------------------------------------------------------------
class TestCalculoDescuento(unittest.TestCase):
    """calcular_descuento es una funcion pura: ni base, ni Tk, ni mocks."""

    RECETAS = {
        1:  {"pechuga": 1},                                       # H Pechuga de Pollo
        2:  {"Bola de carne": 1},                                 # H Especial
        4:  {"Bola de carne": 2},                                 # H Doble Carne
        6:  {"pechuga": 1},                                       # Twister
        39: {"Bola de carne": 1, "pechuga": 1},                   # hamburgesa mixta
        46: {"Bola de carne": 3},                                 # H TRIPLE RES
        47: {"Bola de carne": 2, "pechuga": 1},                   # H TRIPE POLLO
        48: {"Carnes": 1, "Desmechada": 1, "maiz": 1},            # SANDWICHE ESPECIALES
    }

    @staticmethod
    def _item(producto_id, cantidad):
        return {'id': producto_id, 'nombre': 'x', 'cantidad': cantidad, 'precio': 1000}

    def _calc(self, *pares):
        items = [self._item(pid, cant) for pid, cant in pares]
        return db_manager.calcular_descuento(items, self.RECETAS)

    def test_especial_gasta_una_bola(self):
        self.assertEqual(self._calc((2, 1)), {"Bola de carne": 1.0})

    def test_doble_gasta_dos_bolas(self):
        self.assertEqual(self._calc((4, 1)), {"Bola de carne": 2.0})

    def test_triple_gasta_tres_bolas(self):
        self.assertEqual(self._calc((46, 1)), {"Bola de carne": 3.0})

    def test_mixta_gasta_de_dos_materiales(self):
        self.assertEqual(self._calc((39, 1)), {"Bola de carne": 1.0, "pechuga": 1.0})

    def test_triple_pollo_gasta_dos_bolas_y_una_pechuga(self):
        self.assertEqual(self._calc((47, 1)), {"Bola de carne": 2.0, "pechuga": 1.0})

    def test_sandwiche_especiales_gasta_tres_materiales(self):
        self.assertEqual(self._calc((48, 1)),
                         {"Carnes": 1.0, "Desmechada": 1.0, "maiz": 1.0})

    def test_tres_dobles_gastan_seis_bolas(self):
        self.assertEqual(self._calc((4, 3)), {"Bola de carne": 6.0})

    def test_dos_mixtas_mas_una_especial_acumulan_sobre_el_mismo_material(self):
        # El caso que mas facil se olvida: productos distintos del mismo
        # carrito suman sobre la misma materia prima.
        self.assertEqual(self._calc((39, 2), (2, 1)),
                         {"Bola de carne": 3.0, "pechuga": 2.0})

    def test_el_mismo_producto_repetido_se_acumula(self):
        self.assertEqual(self._calc((4, 1), (4, 2)), {"Bola de carne": 6.0})

    def test_producto_sin_receta_no_gasta_nada_ni_falla(self):
        # 14 Bebida, 23 DOMICILIO CERCA, 45 GASTOS INSUMO: no estan en RECETAS
        for producto_id in (14, 23, 45):
            with self.subTest(producto=producto_id):
                self.assertEqual(self._calc((producto_id, 2)), {})

    def test_cantidad_cero_no_gasta_nada(self):
        self.assertEqual(self._calc((4, 0)), {})

    def test_sin_recetas_cargadas_no_gasta_nada(self):
        items = [self._item(4, 5)]
        self.assertEqual(db_manager.calcular_descuento(items, {}), {})

    def test_entradas_malformadas_no_revientan(self):
        basura = [{'nombre': 'sin id'},
                  {'id': 'abc', 'cantidad': 1},
                  {'id': 4, 'cantidad': -3},
                  {'id': 4}]
        self.assertEqual(db_manager.calcular_descuento(basura, self.RECETAS), {})

    def test_mayusculas_distintas_cuentan_como_el_mismo_material(self):
        recetas = {21: {"Chorizo": 1}, 40: {"chorizo": 1}}
        items = [self._item(21, 1), self._item(40, 1)]
        resultado = db_manager.calcular_descuento(items, recetas)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(list(resultado.values()), [2.0])


# ---------------------------------------------------------------------
# PR-02 - Integracion (venta <-> stock) - Funcional - Regresion
# ---------------------------------------------------------------------
class _BaseConBaseTemporal(unittest.TestCase):
    """Monta una base real y desechable y apunta db_manager a ella.

    La palanca es DATABASE_NAME: connect_db() lee el global del modulo en
    cada llamada, asi que parchearlo redirige TODAS las funciones.
    """

    PRODUCTOS = [
        (1,  'H Pechuga de Pollo',   12000, 'pechuga',       10),
        (2,  'H Especial',           11000, 'Bola de carne', 10),
        (4,  'H Doble Carne',        16000, 'Bola de carne', 10),
        (6,  'Twister',              12000, 'pechuga',       10),
        (14, 'Bebida',                3500, 'Bebidas',       10),
        (39, 'hamburgesa mixta',     17000, 'hamburgesas',   10),
        (48, 'SANDWICHE ESPECIALES', 17000, 'TOCINETA',      10),
    ]
    RECETAS = [
        (1,  'pechuga',       1),
        (2,  'Bola de carne', 1),
        (4,  'Bola de carne', 2),
        (6,  'pechuga',       1),
        (39, 'Bola de carne', 1),
        (39, 'pechuga',       1),
        (48, 'Carnes',        1),
        (48, 'Desmechada',    1),
        (48, 'maiz',          1),
    ]

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_pos.db")
        self._patch_db = patch.object(db_manager, 'DATABASE_NAME', self.db_path)
        self._patch_db.start()
        db_manager._STOCK_LISTO = False      # cache por proceso: hay que resetearla
        self._montar_esquema()

    def tearDown(self):
        self._patch_db.stop()
        db_manager._STOCK_LISTO = False
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _montar_esquema(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL,
                       precio REAL NOT NULL, categoria TEXT, stock INTEGER DEFAULT 0)''')
        cur.execute('''CREATE TABLE ventas (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       fecha_hora TEXT NOT NULL, total REAL NOT NULL)''')
        cur.execute('''CREATE TABLE facturas (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       num_factura TEXT NOT NULL, fecha_hora TEXT NOT NULL, cliente TEXT,
                       metodo_pago TEXT, valor_total REAL NOT NULL)''')
        cur.execute('''CREATE TABLE facturas_completas (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       num_factura TEXT, fecha TEXT, nom_cliente TEXT, direccion TEXT,
                       metodo_pago TEXT, cantidad INTEGER, producto TEXT, valor_unitario REAL,
                       subtotal REAL, total REAL, comentarios TEXT)''')
        cur.executemany("INSERT INTO productos VALUES (?,?,?,?,?)", self.PRODUCTOS)
        conn.commit()
        conn.close()

        db_manager.asegurar_tablas_stock(forzar=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.executemany("INSERT INTO producto_stock (producto_id, categoria, cantidad) VALUES (?,?,?)",
                        self.RECETAS)
        for categoria in ("Bola de carne", "pechuga", "Carnes", "Desmechada", "maiz"):
            cur.execute("INSERT INTO stock (categoria, cantidad) VALUES (?, 10)", (categoria,))
        conn.commit()
        conn.close()

    # --- helpers ---
    def _scalar(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        try:
            fila = conn.execute(sql, params).fetchone()
            return fila[0] if fila else None
        finally:
            conn.close()

    def _cantidad(self, categoria):
        return self._scalar("SELECT cantidad FROM stock WHERE categoria = ?", (categoria,))

    def _vender(self, *pares):
        """_vender((4, 2), (14, 1)) -> vende 2 doble carne y 1 bebida."""
        items = []
        for producto_id, cant in pares:
            fila = [p for p in self.PRODUCTOS if p[0] == producto_id][0]
            items.append({'id': producto_id, 'nombre': fila[1],
                          'cantidad': cant, 'precio': fila[2]})
        total = sum(i['cantidad'] * i['precio'] for i in items)
        return db_manager.record_sale(total, items, cliente="Test", metodo_pago="EFECTIVO")


class TestVentaDescuentaStock(_BaseConBaseTemporal):

    def test_vender_dos_dobles_descuenta_cuatro_bolas(self):
        self._vender((4, 2))
        self.assertEqual(self._cantidad("Bola de carne"), 6)
        self.assertEqual(self._cantidad("pechuga"), 10)

    def test_mixta_descuenta_de_los_dos_materiales(self):
        self._vender((39, 1))
        self.assertEqual(self._cantidad("Bola de carne"), 9)
        self.assertEqual(self._cantidad("pechuga"), 9)

    def test_sandwiche_especiales_descuenta_los_tres_materiales(self):
        self._vender((48, 1))
        self.assertEqual(self._cantidad("Carnes"), 9)
        self.assertEqual(self._cantidad("Desmechada"), 9)
        self.assertEqual(self._cantidad("maiz"), 9)

    def test_carrito_mixto_acumula_por_material(self):
        # 2 mixtas + 1 especial -> 3 bolas y 2 pechugas
        self._vender((39, 2), (2, 1))
        self.assertEqual(self._cantidad("Bola de carne"), 7)
        self.assertEqual(self._cantidad("pechuga"), 8)

    def test_bebida_se_vende_sin_mover_stock(self):
        num_factura = self._vender((14, 3))
        self.assertIsNotNone(num_factura)
        self.assertEqual(self._cantidad("Bola de carne"), 10)
        self.assertEqual(self._scalar(
            "SELECT COUNT(*) FROM stock_movimientos WHERE num_factura = ?", (num_factura,)), 0)
        self.assertEqual(self._scalar("SELECT COUNT(*) FROM facturas"), 1)

    def test_sin_material_la_venta_pasa_y_el_saldo_queda_negativo(self):
        db_manager.fijar_stock("Bola de carne", 1)
        num_factura = self._vender((4, 2))           # 2 x 2 bolas = 4
        self.assertIsNotNone(num_factura)            # la venta NO se bloquea
        self.assertEqual(self._cantidad("Bola de carne"), -3)   # sin truncar a cero

    def test_si_el_descuento_falla_no_queda_ni_la_venta(self):
        antes = (self._scalar("SELECT COUNT(*) FROM ventas"),
                 self._scalar("SELECT COUNT(*) FROM facturas"),
                 self._scalar("SELECT COUNT(*) FROM facturas_completas"))
        with patch.object(db_manager, 'descontar_stock',
                          side_effect=RuntimeError("falla simulada")):
            with self.assertRaises(RuntimeError):
                self._vender((2, 1))
        despues = (self._scalar("SELECT COUNT(*) FROM ventas"),
                   self._scalar("SELECT COUNT(*) FROM facturas"),
                   self._scalar("SELECT COUNT(*) FROM facturas_completas"))
        self.assertEqual(antes, despues)
        self.assertEqual(self._cantidad("Bola de carne"), 10)

    def test_cada_venta_deja_su_movimiento(self):
        num_factura = self._vender((4, 1), (39, 1))
        # Bola de carne (2+1=3) y pechuga (1): dos movimientos
        filas = sqlite3.connect(self.db_path).execute(
            "SELECT categoria, cantidad FROM stock_movimientos WHERE num_factura = ? ORDER BY categoria",
            (num_factura,)).fetchall()
        self.assertEqual(filas, [("Bola de carne", -3.0), ("pechuga", -1.0)])

    def test_consumo_del_dia_agrega_por_material(self):
        from datetime import date
        self._vender((4, 2), (6, 1))
        filas = {f[0]: f for f in db_manager.consumo_por_fecha(date.today().strftime("%Y-%m-%d"))}
        self.assertEqual(filas["Bola de carne"][1], 4)
        self.assertEqual(filas["pechuga"][1], 1)
        self.assertEqual(filas["Bola de carne"][3], 6)   # lo que queda

    def test_productos_sin_material_marca_solo_los_que_no_alcanzan(self):
        db_manager.fijar_stock("Bola de carne", 1)
        agotados = db_manager.productos_sin_material()
        self.assertIn(4, agotados)       # doble necesita 2 bolas, solo hay 1
        self.assertNotIn(2, agotados)    # especial necesita 1, alcanza justo
        self.assertNotIn(39, agotados)   # mixta necesita 1 bola + 1 pechuga, alcanza
        self.assertNotIn(14, agotados)   # sin receta, nunca se marca

    def test_un_material_agotado_marca_el_producto_aunque_el_otro_alcance(self):
        db_manager.fijar_stock("pechuga", 0)
        agotados = db_manager.productos_sin_material()
        self.assertIn(39, agotados)      # mixta: sobran bolas pero no hay pechuga
        self.assertIn(1, agotados)       # H Pechuga de Pollo
        self.assertNotIn(2, agotados)    # especial solo usa bolas, sigue disponible

    def test_reponer_suma_y_fijar_asigna(self):
        db_manager.fijar_stock("Bola de carne", 1)
        self._vender((4, 2))                                   # queda en -3
        self.assertEqual(db_manager.reponer_stock("Bola de carne", 20), 17)
        db_manager.fijar_stock("Bola de carne", 5)
        self.assertEqual(self._cantidad("Bola de carne"), 5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
