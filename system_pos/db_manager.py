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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_factura TEXT NOT NULL,
            fecha_hora TEXT NOT NULL,
            cliente TEXT,
            metodo_pago TEXT,
            valor_total REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observaciones_venta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_factura INTEGER NOT NULL,
            producto_nombre TEXT NOT NULL,
            observacion TEXT,
            FOREIGN KEY (facturaS) REFERENCES ventas(num_factura)
        )
    ''')
    # Tabla de direcciones/ciudades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS direcciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            envio_incluido INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


DEFAULT_ADDRESSES = [
    "Batará", "Aracari", "Milano", "Ibis", "Amazilia", "Jilguero", "Alondra", "Tángara", "Andaríos", "Frontino",
    "Sie 1", "Sie 2", "Sie 3", "Sie 4","andarios",
    "Tángara", "Terranova", "Frontino","bosques alizos","bosques arrayan ","altamorada",
    "Taller Motos",
    "al frente iglesia",
    "Torre de San Juan 1B", "Torre de San Juan 2B", "Torre de San Juan 3B", "Torre de San Juan 4B", "Torre de San Juan 5B",
    "Torre de San Juan 6B", "Torre de San Juan 7B", "Torre de San Juan 8B", "Torre de San Juan 9B", "Torre de San Juan 10B",
    "Torre de San Juan 11B", "Torre de San Juan 12B", "Torre de San Juan 13B", "Torre de San Juan 14B", "Torre de San Juan 15B",
    "Torre de San Juan 16B", "Torre de San Juan 17B", "Torre de San Juan 18B", "Torre de San Juan 19B", "Torre de San Juan 20B",
    "Torre de San Juan 21B", "Torre de San Juan 22B", "Torre de San Juan 23B", "Torre de San Juan 24B", "Torre de San Juan 25B",
    "Torre de San Juan 26B", "Torre de San Juan 27B", "Torre de San Juan 28B", "Torre de San Juan 29B", "Torre de San Juan 30B",
    "Torre de San Juan 31B", "Torre de San Juan 32B", "Torre de San Juan 33B", "Torre de San Juan 34B", "Torre de San Juan 35B",
    "Torre de San Juan 36B", "Torre de San Juan 37B", "Torre de San Juan 38B",
    "San javier 1", "San javier 2", "San javier 3", "San javier 4", "San javier 5", "San javier 6", "San javier 7",
    "San javier 8", "San javier 9", "San javier 10", "San javier 11", "San javier 12", "San javier 13", "San javier 14",
    "San javier 15", "San javier 16", "San javier 17", "San javier 18", "San javier 19", "San javier 20","San javier 21",
    "San javier 22", "San javier 23", "San javier 24", "San javier 25", "San javier 26", "San javier 27", "San javier 28",
    "San javier 29", "San javier 30", "San javier 31", "San javier 32", "San javier 33", "San javier 34","pago punto"
]

# Subconjunto de direcciones con envío incluido
DEFAULT_FREE = set([
    "Batará", "Aracari", "Milano", "Ibis", "Amazilia", "Jilguero", "Andaríos",
    "Tángara", "Frontino","bosques alizos","bosques arrayan ","altamorada",
    "andarios","Taller Motos",
    "Sie 1", "Sie 2", "Sie 3", "Sie 4",
    "al frente iglesia","Terranova",
    # Torres y San javier también incluidos en la lista por defecto
    "Torre de San Juan 1B", "Torre de San Juan 2B", "Torre de San Juan 3B",
    "Torre de San Juan 4B", "Torre de San Juan 5B", "Torre de San Juan 6B", "Torre de San Juan 7B",
    "Torre de San Juan 8B", "Torre de San Juan 9B", "Torre de San Juan 10B",
    "Torre de San Juan 11B", "Torre de San Juan 12B", "Torre de San Juan 13B", "Torre de San Juan 14B",
    "Torre de San Juan 15B", "Torre de San Juan 16B", "Torre de San Juan 17B", "Torre de San Juan 18B",
    "Torre de San Juan 19B", "Torre de San Juan 20B", "Torre de San Juan 21B", "Torre de San Juan 22B",
    "Torre de San Juan 23B", "Torre de San Juan 24B", "Torre de San Juan 25B", "Torre de San Juan 26B",
    "Torre de San Juan 27B", "Torre de San Juan 28B", "Torre de San Juan 29B", "Torre de San Juan 30B",
    "Torre de San Juan 31B", "Torre de San Juan 32B", "Torre de San Juan 33B", "Torre de San Juan 34B",
    "Torre de San Juan 35B", "Torre de San Juan 36B", "Torre de San Juan 37B", "Torre de San Juan 38B",
    "San javier 1", "San javier 2", "San javier 3", "San javier 4", "San javier 5", "San javier 6", "San javier 7",
    "San javier 8", "San javier 9", "San javier 10", "San javier 11", "San javier 12", "San javier 13",
    "San javier 14", "San javier 15", "San javier 16", "San javier 17", "San javier 18", "San javier 19",
    "San javier 20","San javier 21","San javier 22", "San javier 23", "San javier 24", "San javier 25",
    "San javier 26", "San javier 27", "San javier 28","San javier 29", "San javier 30", "San javier 31",
    "San javier 32", "San javier 33", "San javier 34","pago punto"
])

def add_address(nombre, envio_incluido=False):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO direcciones (nombre, envio_incluido) VALUES (?, ?)", (nombre, 1 if envio_incluido else 0))
        conn.commit()
    finally:
        conn.close()


def get_all_addresses():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM direcciones ORDER BY nombre COLLATE NOCASE")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_free_addresses():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM direcciones WHERE envio_incluido = 1 ORDER BY nombre COLLATE NOCASE")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def ensure_default_addresses():
    """Inserta direcciones por defecto si la tabla está vacía."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM direcciones")
    count = cursor.fetchone()[0]
    if count == 0:
        for addr in DEFAULT_ADDRESSES:
            envio = 1 if addr in DEFAULT_FREE else 0
            try:
                cursor.execute("INSERT OR IGNORE INTO direcciones (nombre, envio_incluido) VALUES (?, ?)", (addr, envio))
            except Exception:
                pass
        conn.commit()
    conn.close()

def add_product(nombre, precio, categoria="General", stock=0):
    """Añade un nuevo producto a la base de datos."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, precio, categoria, stock) VALUES (?, ?, ?, ?)",
                   (nombre, precio, categoria, stock))
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id

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
def record_sale(total, items_vendidos, cliente="", metodo_pago="", observaciones=None, split_payment=None):
    """Registra una nueva venta y guarda factura con observaciones.
    
    Args:
        split_payment: tuple (method1, method2, amount1, amount2) si es pago dividido, o None
    """
    conn = connect_db()
    cursor = conn.cursor()
    import datetime
    fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO ventas (fecha_hora, total) VALUES (?, ?)", (fecha_hora, total))
    venta_id = cursor.lastrowid
    
    # Guardar en tabla de facturas
    num_factura = str(venta_id).zfill(4)
    
    # Si es pago dividido, guardar ambos métodos en formato "METHOD1|AMOUNT1+METHOD2|AMOUNT2"
    if split_payment:
        method1, method2, amount1, amount2 = split_payment
        metodo_pago_guardado = f"{method1}|{amount1}+{method2}|{amount2}"
    else:
        metodo_pago_guardado = metodo_pago
    
    cursor.execute("INSERT INTO facturas (num_factura, fecha_hora, cliente, metodo_pago, valor_total) VALUES (?, ?, ?, ?, ?)",
                   (num_factura, fecha_hora, cliente, metodo_pago_guardado, total))

    for item in items_vendidos:
        producto_id = item['id']
        cantidad = item['cantidad']
        precio_unitario = item['precio']
        cursor.execute("INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                       (venta_id, producto_id, cantidad, precio_unitario))
        # Actualizar stock: restar la cantidad vendida a TODOS los productos
        # que pertenezcan a la misma categoría que el producto vendido.
        cursor.execute("SELECT categoria FROM productos WHERE id = ?", (producto_id,))
        row = cursor.fetchone()
        if row and row[0]:
            categoria = row[0]
            # Evitar stock negativo: usar CASE para mantener stock >= 0
            cursor.execute(
                "UPDATE productos SET stock = CASE WHEN stock - ? < 0 THEN 0 ELSE stock - ? END WHERE categoria = ?",
                (cantidad, cantidad, categoria)
            )
        else:
            # Si no se encuentra categoría, decrementamos únicamente el producto vendido
            cursor.execute("UPDATE productos SET stock = CASE WHEN stock - ? < 0 THEN 0 ELSE stock - ? END WHERE id = ?", (cantidad, cantidad, producto_id))
    
    # Guardar observaciones si existen
    if observaciones:
        for producto_nombre, obs in observaciones.items():
            if obs.strip():  # Solo guardar si hay observación
                cursor.execute("INSERT INTO observaciones_venta (venta_id, producto_nombre, observacion) VALUES (?, ?, ?)",
                               (venta_id, producto_nombre, obs.strip()))

    conn.commit()
    conn.close()
    return venta_id

def count_products():
    """Cuenta el número total de productos en la base de datos."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM productos")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_facturas():
    """Obtiene todas las facturas registradas con sus observaciones."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.num_factura, f.fecha_hora, f.cliente, f.metodo_pago, f.valor_total,
               GROUP_CONCAT(ov.observacion, ' | ') as observaciones
        FROM facturas f
        LEFT JOIN observaciones_venta ov ON f.id = ov.venta_id
        GROUP BY f.id
        ORDER BY f.id DESC
    """)
    facturas = cursor.fetchall()
    conn.close()
    return facturas


def get_factura_by_id(factura_id):
    """Obtiene una factura por su id, incluyendo observaciones concatenadas."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.num_factura, f.fecha_hora, f.cliente, f.metodo_pago, f.valor_total,
               GROUP_CONCAT(ov.observacion, ' | ') as observaciones
        FROM facturas f
        LEFT JOIN observaciones_venta ov ON f.id = ov.venta_id
        WHERE f.id = ?
        GROUP BY f.id
    """, (factura_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def update_factura(factura_id, cliente=None, metodo_pago=None, valor_total=None):
    """Actualiza campos editables de una factura."""
    conn = connect_db()
    cursor = conn.cursor()
    # Construir sentencia dinámica según los campos recibidos
    campos = []
    valores = []
    if cliente is not None:
        campos.append("cliente = ?")
        valores.append(cliente)
    if metodo_pago is not None:
        campos.append("metodo_pago = ?")
        valores.append(metodo_pago)
    if valor_total is not None:
        campos.append("valor_total = ?")
        valores.append(valor_total)

    if len(campos) == 0:
        conn.close()
        return

    sql = f"UPDATE facturas SET {', '.join(campos)} WHERE id = ?"
    valores.append(factura_id)
    cursor.execute(sql, tuple(valores))
    conn.commit()
    conn.close()


def delete_factura(factura_id):
    """Elimina una factura por su id."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM facturas WHERE id = ?", (factura_id,))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_tables()
    # Ejemplo de uso:
    # add_product("Hamburguesa Especial", 9900, "Hamburguesas")
    # add_product("Pechuga de Pollo", 10900, "Hamburguesas")
    # print(get_all_products())