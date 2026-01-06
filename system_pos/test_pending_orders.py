import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data", "pos_database.db")

print("DB:", DB)

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
INSERT INTO facturas_completas (
    num_factura, fecha, nom_cliente, direccion, metodo_pago,
    cantidad, producto, valor_unitario, subtotal, total, comentarios
) VALUES (
    'TEST001', '2026-01-01', 'Cliente Test', 'Dirección Test',
    'Efectivo', 1, 'Producto Test', 1000, 1000, 1000, 'OK'
)
""")

conn.commit()
conn.close()

print("✅ INSERT MANUAL OK")
