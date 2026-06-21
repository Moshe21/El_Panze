import sqlite3

conn = sqlite3.connect('data/pos_database.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('✓ Tablas en la base de datos:')
for table in tables:
    print(f'  - {table[0]}')

# Verificar estructura de cart_errores
print('\n✓ Estructura de tabla cart_errores:')
cursor.execute("PRAGMA table_info(cart_errores)")
columns = cursor.fetchall()
for col in columns:
    print(f'  - {col[1]}: {col[2]}')

conn.close()
