import tkinter as tk
import db_manager
import ui_manager
import os

if __name__ == "__main__":
    # Asegurarse de que la carpeta 'data' exista
    if not os.path.exists('data'): # <--- VERIFICA RUTA DE CARPETA DATA
        os.makedirs('data') # <--- CREA RUTA DE CARPETA DATA

    db_manager.create_tables() # Inicializa la base de datos y tablas

    root = tk.Tk()
    #app = POSApp(root)
    app = ui_manager.POSApp(root)
    root.mainloop()