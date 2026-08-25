import sqlite3
import os

DATABASE_NAME = "data/pos_database.db" # <--- RUTA DE BASE DE DATOS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "pos_database.db")
# --- FACTURAS PDF EN BASE DE DATOS ---
# --- FACTURAS PDF EN BASE DE DATOS (estructura por producto) ---
def create_facturas_pdf_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas_completas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_factura TEXT,
            fecha TEXT,
            nom_cliente TEXT,
            direccion TEXT,
            metodo_pago TEXT,
            cantidad INTEGER,
            producto TEXT,
            valor_unitario REAL,
            subtotal REAL,
            total REAL,
            comentarios TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("🧾 INSERT REAL sad→")
def insert_factura_pdf(num_factura, fecha, nom_cliente, direccion, metodo_pago, cantidad, producto, valor_unitario, subtotal, total, comentarios=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO facturas_completas (num_factura, fecha, nom_cliente, direccion, metodo_pago, cantidad, producto, valor_unitario, subtotal, total, comentarios)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (num_factura, fecha, nom_cliente, direccion, metodo_pago, cantidad, producto, valor_unitario, subtotal, total, comentarios))
    
    conn.commit()
    conn.close()
    print("🧾 INSERT REAL →", num_factura, producto)

def get_all_facturas_completas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM facturas_completas")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return columns, rows
    except Exception:
        return [], []
    finally:
        conn.close()

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
        CREATE TABLE IF NOT EXISTS facturas_completas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_factura TEXT,
            fecha TEXT,
            nom_cliente TEXT,
            direccion TEXT,
            metodo_pago TEXT,
            cantidad INTEGER,
            producto TEXT,
            valor_unitario REAL,
            subtotal REAL,
            total REAL,
            comentarios TEXT
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
    # Tabla de direcciones/ciudades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS direcciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            envio_incluido INTEGER DEFAULT 0
        )
    ''')
    # Tablas para pedidos pendientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            client TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            nombre TEXT,
            precio REAL,
            cantidad INTEGER,
            FOREIGN KEY (order_id) REFERENCES pending_orders(id)
        )
    ''')
    # Tabla para configuración de saldos iniciales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_saldos (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nequi_inicial REAL DEFAULT 0,
            daviplata_inicial REAL DEFAULT 0,
            efectivo_inicial REAL DEFAULT 0
        )
    ''')
    # Si la columna efectivo_inicial no existe, agregarla (migración)
    try:
        cursor.execute("ALTER TABLE config_saldos ADD COLUMN efectivo_inicial REAL DEFAULT 0")
    except Exception:
        pass
    cursor.execute("INSERT OR IGNORE INTO config_saldos (id, nequi_inicial, daviplata_inicial, efectivo_inicial) VALUES (1, 0, 0, 0)")

    # Historial versionado de saldos iniciales. config_saldos se conserva por
    # compatibilidad con el resto de la aplicación.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saldos_iniciales_historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            nequi_inicial REAL NOT NULL DEFAULT 0,
            daviplata_inicial REAL NOT NULL DEFAULT 0,
            efectivo_inicial REAL NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        INSERT INTO saldos_iniciales_historial
            (fecha_hora, nequi_inicial, daviplata_inicial, efectivo_inicial)
        SELECT datetime('now', 'localtime'), nequi_inicial, daviplata_inicial, efectivo_inicial
        FROM config_saldos
        WHERE id = 1
          AND NOT EXISTS (SELECT 1 FROM saldos_iniciales_historial)
    ''')
    
    # Tabla para guardar errores del carrito
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart_errores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            producto_nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            cantidad INTEGER NOT NULL,
            subtotal REAL NOT NULL
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

def get_product(product_id):
    """Obtiene un producto por su identificador o devuelve None."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre, precio, categoria, stock FROM productos WHERE id = ?",
            (product_id,)
        )
        return cursor.fetchone()
    finally:
        conn.close()

def update_product(product_id, nombre, precio, categoria="General", stock=0):
    """Actualiza todos los campos editables de un producto."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE productos
            SET nombre = ?, precio = ?, categoria = ?, stock = ?
            WHERE id = ?
            """,
            (nombre, precio, categoria, stock, product_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def delete_product(product_id):
    """Elimina un producto y devuelve True cuando el registro existía."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM productos WHERE id = ?", (product_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

# Más funciones para actualizar, eliminar productos, registrar ventas, etc.
# Ejemplo:
def record_sale(total, items_vendidos, cliente="", direccion="", metodo_pago="", observaciones=None, split_payment=None):
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

    # Insertar en facturas_completas
    for item in items_vendidos:
        producto_id = item['id']
        producto_nombre = item['nombre']
        cantidad = item['cantidad']
        precio_unitario = item['precio']
        subtotal = cantidad * precio_unitario
        comentario = observaciones.get(producto_nombre, "") if observaciones else ""
        cursor.execute('''
            INSERT INTO facturas_completas (num_factura, fecha, nom_cliente, direccion, metodo_pago, cantidad, producto, valor_unitario, subtotal, total, comentarios)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (num_factura, fecha_hora, cliente, direccion, metodo_pago_guardado, cantidad, producto_nombre, precio_unitario, subtotal, total, comentario))
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
    
    conn.commit()
    conn.close()
    return num_factura

def count_products():
    """Cuenta el número total de productos en la base de datos."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM productos")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_facturas():
    """Obtiene todas las facturas registradas con observaciones y dirección."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT f.id, f.num_factura, f.fecha_hora, f.cliente, f.metodo_pago, f.valor_total
            FROM facturas AS f
            WHERE date(f.fecha_hora) BETWEEN date('now', 'localtime', '-1 day') AND date('now', 'localtime')
            ORDER BY f.fecha_hora;
        """)
        facturas = cursor.fetchall()
        
        # Agregar dirección y observaciones desde facturas_completas
        result = []
        for fact in facturas:
            fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total = fact
            
            # Obtener dirección (la primera única)
            cursor.execute("SELECT DISTINCT direccion FROM facturas_completas WHERE num_factura = ? AND direccion IS NOT NULL AND direccion != '' LIMIT 1", (num_factura,))
            dir_row = cursor.fetchone()
            direccion = dir_row[0] if dir_row else ""
            
            # Obtener observaciones
            cursor.execute("SELECT GROUP_CONCAT(comentarios, ' | ') FROM facturas_completas WHERE num_factura = ? AND comentarios IS NOT NULL AND comentarios != ''", (num_factura,))
            obs_row = cursor.fetchone()
            observaciones = obs_row[0] if obs_row and obs_row[0] else ""
            
            result.append((fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, direccion, observaciones))
        
        conn.close()
        return result
    except Exception as e:
        print(f"Error en get_all_facturas(): {e}")
        conn.close()
        return []


def get_factura_by_id(factura_id):
    """Obtiene una factura por su id, incluyendo observaciones y dirección concatenadas."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT f.id, f.num_factura, f.fecha_hora, f.cliente, f.metodo_pago, f.valor_total
            FROM facturas f
            WHERE f.id = ?
        """, (factura_id,))
        fact = cursor.fetchone()
        
        if not fact:
            conn.close()
            return None
        
        fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total = fact
        
        # Obtener dirección (la primera única)
        cursor.execute("SELECT DISTINCT direccion FROM facturas_completas WHERE num_factura = ? AND direccion IS NOT NULL AND direccion != '' LIMIT 1", (num_factura,))
        dir_row = cursor.fetchone()
        direccion = dir_row[0] if dir_row else ""
        
        # Obtener observaciones
        cursor.execute("SELECT GROUP_CONCAT(comentarios, ' | ') FROM facturas_completas WHERE num_factura = ? AND comentarios IS NOT NULL AND comentarios != ''", (num_factura,))
        obs_row = cursor.fetchone()
        observaciones = obs_row[0] if obs_row and obs_row[0] else ""
        
        conn.close()
        return (fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, direccion, observaciones)
    except Exception as e:
        print(f"Error en get_factura_by_id(): {e}")
        conn.close()
        return None


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

# --- FUNCIONES FALTANTES PARA PEDIDOS PENDIENTES Y SALDOS ---

def save_pending_order_db(name, items, client, address):
    conn = connect_db()
    cursor = conn.cursor()  
    cursor.execute("INSERT INTO pending_orders (name, client, address) VALUES (?, ?, ?)", 
                   (name, client, address))
    order_id = cursor.lastrowid
    for item in items:
        # items puede venir como dict o tuple dependiendo del origen, aseguramos manejo
        nombre = item.get('nombre') if isinstance(item, dict) else item[0]
        precio = item.get('precio') if isinstance(item, dict) else item[1]
        cantidad = item.get('cantidad') if isinstance(item, dict) else item[2]
        
        cursor.execute("INSERT INTO pending_order_items (order_id, nombre, precio, cantidad) VALUES (?, ?, ?, ?)", 
                       (order_id, nombre, precio, cantidad))
    conn.commit()
    conn.close()
    return order_id

def get_all_pending_orders():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, client, address, created_at FROM pending_orders ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_pending_order_items(order_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, precio, cantidad FROM pending_order_items WHERE order_id = ?", (order_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_pending_order(order_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_order_items WHERE order_id = ?", (order_id,))
    cursor.execute("DELETE FROM pending_orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

def _ensure_saldos_historial(cursor):
    """Crea el historial y migra la configuración actual cuando sea necesario."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saldos_iniciales_historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            nequi_inicial REAL NOT NULL DEFAULT 0,
            daviplata_inicial REAL NOT NULL DEFAULT 0,
            efectivo_inicial REAL NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_saldos (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nequi_inicial REAL DEFAULT 0,
            daviplata_inicial REAL DEFAULT 0,
            efectivo_inicial REAL DEFAULT 0
        )
    ''')
    try:
        cursor.execute("ALTER TABLE config_saldos ADD COLUMN efectivo_inicial REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    cursor.execute(
        "INSERT OR IGNORE INTO config_saldos "
        "(id, nequi_inicial, daviplata_inicial, efectivo_inicial) VALUES (1, 0, 0, 0)"
    )
    cursor.execute('''
        INSERT INTO saldos_iniciales_historial
            (fecha_hora, nequi_inicial, daviplata_inicial, efectivo_inicial)
        SELECT datetime('now', 'localtime'), nequi_inicial, daviplata_inicial, efectivo_inicial
        FROM config_saldos
        WHERE id = 1
          AND NOT EXISTS (SELECT 1 FROM saldos_iniciales_historial)
    ''')

def get_saldos_iniciales():
    """Devuelve Nequi, Daviplata y Efectivo de la versión más reciente."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        _ensure_saldos_historial(cursor)
        cursor.execute('''
            SELECT nequi_inicial, daviplata_inicial, efectivo_inicial
            FROM saldos_iniciales_historial
            ORDER BY id DESC
            LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.commit()
        return row if row else (0.0, 0.0, 0.0)
    finally:
        conn.close()

def set_saldos_iniciales(nequi, daviplata=None, efectivo=None):
    # Permitir llamada con una tupla/lista o con tres argumentos
    if daviplata is None and efectivo is None and isinstance(nequi, (tuple, list)) and len(nequi) == 3:
        nequi_val, daviplata_val, efectivo_val = nequi
    else:
        nequi_val = nequi
        daviplata_val = daviplata if daviplata is not None else 0.0
        efectivo_val = efectivo if efectivo is not None else 0.0
    nequi_val = float(nequi_val)
    daviplata_val = float(daviplata_val)
    efectivo_val = float(efectivo_val)
    conn = connect_db()
    try:
        cursor = conn.cursor()
        _ensure_saldos_historial(cursor)
        cursor.execute(
            "UPDATE config_saldos SET nequi_inicial = ?, daviplata_inicial = ?, efectivo_inicial = ? WHERE id = 1",
            (nequi_val, daviplata_val, efectivo_val)
        )
        from datetime import datetime
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO saldos_iniciales_historial
                (fecha_hora, nequi_inicial, daviplata_inicial, efectivo_inicial)
            VALUES (?, ?, ?, ?)
        ''', (fecha_hora, nequi_val, daviplata_val, efectivo_val))
        version_id = cursor.lastrowid
        conn.commit()
        return version_id
    finally:
        conn.close()

def get_saldos_iniciales_historial(limit=None, ultimos_dos_dias=False):
    """Devuelve el historial, opcionalmente limitado a hoy y al día anterior."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        _ensure_saldos_historial(cursor)
        query = '''
            SELECT f.id, f.fecha_hora, f.nequi_inicial,
                   f.daviplata_inicial, f.efectivo_inicial
            FROM saldos_iniciales_historial AS f
        '''
        if ultimos_dos_dias:
            query += '''
                WHERE date(f.fecha_hora) BETWEEN date('now', 'localtime', '-1 day')
                                               AND date('now', 'localtime')
            '''
        query += " ORDER BY f.id DESC"
        params = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (max(0, int(limit)),)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()

def actualizar_stock(stock_num):
    # Aumentar stock solo a los productos que tienen stock > 0
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE productos SET stock = stock + ? WHERE stock >= 0", (stock_num,))
        conn.commit()
    except Exception as e:
        print("Error al actualizar stock:", e)
    finally:
        conn.close()

# --- FUNCIONES PARA GUARDAR Y RECUPERAR ERRORES DEL CARRITO ---

def save_cart_error(cart_items):
    """Guarda los productos del carrito actual como error en la tabla cart_errores."""
    try:
        from datetime import datetime
        conn = connect_db()
        cursor = conn.cursor()
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for product_id, item_data in cart_items.items():
            nombre = item_data.get('nombre', '')
            precio = item_data.get('precio', 0)
            cantidad = item_data.get('cantidad', 0)
            subtotal = precio * cantidad
            
            cursor.execute('''
                INSERT INTO cart_errores (fecha_hora, producto_nombre, precio, cantidad, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (fecha_hora, nombre, precio, cantidad, subtotal))
        
        conn.commit()
        conn.close()
        print(f"✓ Carrito guardado como error: {len(cart_items)} productos")
    except Exception as e:
        print(f"Error al guardar carrito como error: {e}")

def get_all_cart_errores():
    """Recupera todos los errores del carrito (productos guardados con código 5263)."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, fecha_hora, producto_nombre, precio, cantidad, subtotal 
            FROM cart_errores 
            ORDER BY fecha_hora DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error al obtener errores del carrito: {e}")
        return []

def delete_cart_error(error_id):
    """Elimina un error del carrito por su ID."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart_errores WHERE id = ?", (error_id,))
        conn.commit()
        conn.close()
        print(f"✓ Error del carrito eliminado: {error_id}")
    except Exception as e:
        print(f"Error al eliminar error del carrito: {e}")

def delete_all_cart_errores():
    """Elimina todos los errores del carrito."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart_errores")
        conn.commit()
        conn.close()
        print("✓ Todos los errores del carrito han sido eliminados")
    except Exception as e:
        print(f"Error al eliminar todos los errores del carrito: {e}")


# --- VENTAS DE PRODUCTOS SIN STOCK ---

def _crear_tabla_ventas_agotados(cursor):
    """Crea la tabla si falta.

    Va aparte de create_tables() porque main.py la tiene comentada,
    asi que la tabla debe poder crearse sola en el primer uso.
    """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas_agotados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            num_factura TEXT,
            producto_nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio REAL NOT NULL,
            subtotal REAL NOT NULL
        )
    ''')


def registrar_venta_agotado(num_factura, items_agotados):
    """Registra los productos que se vendieron estando sin stock.

    items_agotados: lista de dicts con 'nombre', 'cantidad' y 'precio'.
    """
    if not items_agotados:
        return
    try:
        from datetime import datetime
        conn = connect_db()
        cursor = conn.cursor()
        _crear_tabla_ventas_agotados(cursor)
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in items_agotados:
            nombre = item.get('nombre', 'Desconocido')
            precio = item.get('precio', 0)
            cantidad = item.get('cantidad', 0)
            cursor.execute('''
                INSERT INTO ventas_agotados (fecha_hora, num_factura, producto_nombre, cantidad, precio, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (fecha_hora, num_factura, nombre, cantidad, precio, precio * cantidad))

        conn.commit()
        conn.close()
        print(f"⚠ Vendidos sin stock: {len(items_agotados)} producto(s) en factura {num_factura}")
    except Exception as e:
        print(f"Error al registrar venta de agotados: {e}")


def contar_ventas_agotados(fecha=None):
    """Cuenta unidades de productos vendidos sin stock.

    Sin fecha cuenta el dia de hoy. Devuelve 0 si algo falla.
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()
        _crear_tabla_ventas_agotados(cursor)
        if fecha is None:
            cursor.execute(
                "SELECT COALESCE(SUM(cantidad), 0) FROM ventas_agotados WHERE date(fecha_hora) = date('now', 'localtime')"
            )
        else:
            cursor.execute(
                "SELECT COALESCE(SUM(cantidad), 0) FROM ventas_agotados WHERE date(fecha_hora) = ?", (fecha,)
            )
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except Exception as e:
        print(f"Error al contar ventas de agotados: {e}")
        return 0


def get_ventas_agotados(fecha=None):
    """Detalle de los productos vendidos sin stock (hoy por defecto)."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        _crear_tabla_ventas_agotados(cursor)
        if fecha is None:
            cursor.execute('''
                SELECT id, fecha_hora, num_factura, producto_nombre, cantidad, precio, subtotal
                FROM ventas_agotados WHERE date(fecha_hora) = date('now', 'localtime')
                ORDER BY fecha_hora DESC
            ''')
        else:
            cursor.execute('''
                SELECT id, fecha_hora, num_factura, producto_nombre, cantidad, precio, subtotal
                FROM ventas_agotados WHERE date(fecha_hora) = ?
                ORDER BY fecha_hora DESC
            ''', (fecha,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error al obtener ventas de agotados: {e}")
        return []


# --- ASIGNACION DIFERIDA DEL METODO DE PAGO ---
# La venta se cierra sin metodo de pago y queda como PENDIENTE.
# El metodo se asigna despues desde "lista metodos de pago".

METODO_PENDIENTE = 'PENDIENTE'


def get_facturas_para_metodo_pago(fecha=None):
    """Facturas de hoy y ayer por defecto para asignarles método de pago.

    Las pendientes van primero; las ya asignadas quedan al final de la cola.
    Devuelve tuplas (num_factura, cliente, valor_total, metodo_pago, fecha_hora).
    """
    orden = """
        ORDER BY CASE WHEN f.metodo_pago IS NULL OR TRIM(f.metodo_pago) = ''
                       OR f.metodo_pago = 'PENDIENTE' THEN 0 ELSE 1 END,
                 f.fecha_hora
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()
        if fecha is None:
            cursor.execute("""
                SELECT f.num_factura, f.cliente, f.valor_total,
                       f.metodo_pago, f.fecha_hora
                FROM facturas AS f
                WHERE date(f.fecha_hora) BETWEEN date('now', 'localtime', '-1 day')
                                               AND date('now', 'localtime')
            """ + orden)
        else:
            cursor.execute("""
                SELECT f.num_factura, f.cliente, f.valor_total,
                       f.metodo_pago, f.fecha_hora
                FROM facturas AS f WHERE date(f.fecha_hora) = ?
            """ + orden, (fecha,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error al obtener facturas para metodo de pago: {e}")
        return []


def actualizar_metodo_pago(num_factura, metodo):
    """Asigna (o corrige) el metodo de pago de una factura ya registrada.

    Actualiza las DOS tablas: 'facturas' y 'facturas_completas'. Si solo se
    tocara una, las estadisticas del dia (que leen facturas_completas)
    seguirian mostrando la venta como PENDIENTE.
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE facturas SET metodo_pago = ? WHERE num_factura = ?", (metodo, num_factura))
        tocadas = cursor.rowcount
        cursor.execute("UPDATE facturas_completas SET metodo_pago = ? WHERE num_factura = ?", (metodo, num_factura))
        conn.commit()
        conn.close()
        # Sin simbolos fuera de ASCII: en consola cp1252 el print lanza
        # UnicodeEncodeError, el except lo atrapa y la funcion devolveria 0
        # aunque el UPDATE si se guardo.
        print("OK Factura %s -> %s" % (num_factura, metodo))
        return tocadas
    except Exception as e:
        print(f"Error al actualizar metodo de pago: {e}")
        return 0


def contar_facturas_pendientes(fecha=None):
    """Cuenta pendientes de hoy y ayer, o de una fecha específica."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cond = "metodo_pago IS NULL OR TRIM(metodo_pago) = '' OR metodo_pago = 'PENDIENTE'"
        if fecha is None:
            cursor.execute("""
                SELECT COUNT(*) FROM facturas AS f
                WHERE date(f.fecha_hora) BETWEEN date('now', 'localtime', '-1 day')
                                               AND date('now', 'localtime')
                  AND (%s)
            """ % cond)
        else:
            cursor.execute("SELECT COUNT(*) FROM facturas WHERE date(fecha_hora) = ? AND (%s)" % cond, (fecha,))
        n = cursor.fetchone()[0]
        conn.close()
        return n
    except Exception as e:
        print(f"Error al contar facturas pendientes: {e}")
        return 0


if __name__ == '__main__':
    create_tables()
    # Ejemplo de uso:
    # add_product("Hamburguesa Especial", 9900, "Hamburguesas")
    # add_product("Pechuga de Pollo", 10900, "Hamburguesas")
    # print(get_all_products())
