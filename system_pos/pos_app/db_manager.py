import sqlite3

DATABASE_NAME = "data/pos_database.db"

def connect_db():
    """Establece conexión con la base de datos."""
    conn = sqlite3.connect(DATABASE_NAME)
    return conn

def create_tables():
    """Crea las tablas si no existen."""
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
    """Añade un nuevo producto a la base de datos."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, precio, categoria, stock) VALUES (?, ?, ?, ?)",
                   (nombre, precio, categoria, stock))
    conn.commit()
    conn.close()

def get_all_products():
    """Obtiene todos los productos de la base de datos."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, precio, categoria, stock FROM productos")
    products = cursor.fetchall()
    conn.close()
    return products

# Más funciones para actualizar, eliminar productos, registrar ventas, etc.
# Ejemplo:
def record_sale(total, items_vendidos):
    """Registra una nueva venta."""
    conn = connect_db()
    cursor = conn.cursor()
    import datetime
    fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO ventas (fecha_hora, total) VALUES (?, ?)", (fecha_hora, total))
    venta_id = cursor.lastrowid

    for item in items_vendidos:
        producto_id = item['id']
        cantidad = item['cantidad']
        precio_unitario = item['precio']
        cursor.execute("INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                       (venta_id, producto_id, cantidad, precio_unitario))
        # Opcional: Actualizar stock
        cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, producto_id))

    conn.commit()
    conn.close()
    return venta_id

if __name__ == '__main__':
    create_tables()
    # Ejemplo de uso:
    # add_product("Hamburguesa Especial", 9900, "Hamburguesas")
    # add_product("Pechuga de Pollo", 10900, "Hamburguesas")
    # print(get_all_products())