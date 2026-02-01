import sqlite3
import datetime

DATABASE_NAME = "data/pos_database.db"

def connect_db():
    conn = sqlite3.connect(DATABASE_NAME)
    return conn

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            categoria TEXT,
            stock INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            total REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_venta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            precio_unitario REAL,
            FOREIGN KEY (venta_id) REFERENCES ventas(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    ''')

    conn.commit()
    conn.close()

def add_product(nombre, precio, categoria="General", stock=0):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO productos (nombre, precio, categoria, stock) VALUES (?, ?, ?, ?)",
        (nombre, precio, categoria, stock)
    )
    conn.commit()
    conn.close()

def get_all_products():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, precio, categoria, stock FROM productos")
    data = cursor.fetchall()
    conn.close()
    return data

def record_sale(total, items):
    conn = connect_db()
    cursor = conn.cursor()

    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO ventas (fecha_hora, total) VALUES (?, ?)", (fecha, total))
    venta_id = cursor.lastrowid

    for item in items:
        cursor.execute("""
            INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario)
            VALUES (?, ?, ?, ?)
        """, (venta_id, item["id"], item["cantidad"], item["precio"]))

        cursor.execute("UPDATE productos SET stock = stock - ? WHERE id=?", (item["cantidad"], item["id"]))

    conn.commit()
    conn.close()
    return venta_id

def nombre_producto( product_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT nombre, precio FROM productos WHERE id = ?",
        (product_id,)
    )
    prod = cursor.fetchone()

    cursor.close()
    conn.close()

    return prod