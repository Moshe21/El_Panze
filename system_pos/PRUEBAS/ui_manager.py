import tkinter as tk
from tkinter import ttk, messagebox
import db_manager
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime

subtotal= 0 

class POSApp:

    def __init__(self, root):
        self.root = root
        self.root.title("EL PANZE - Sistema POS")
        self.root.geometry("1024x768")
        self.create_widgets()
        self.cart = {}
        
        db_manager.create_tables()
        
        


    def create_widgets(self):

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # Sección de Productos (izquierda)
        products_frame = ttk.LabelFrame(main, text="Productos", padding="10")
        products_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main.grid_columnconfigure(0, weight=2)

        self.products_container = ttk.Frame(products_frame)
        self.products_container.pack(fill="both", expand=True)

        # Sección de Carrito (derecha)
        cart_frame = ttk.LabelFrame(main, text="Carrito de Compras", padding="10")
        cart_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        main.grid_columnconfigure(1, weight=1)

        self.cart_list = tk.Listbox(cart_frame, font=("Arial", 12), height=20)
        self.cart_list.pack(fill="both", expand=True)

        ttk.Button(cart_frame, text="Eliminar", command=self.remove_from_cart).pack(fill="x", pady=2)
        ttk.Button(cart_frame, text="Vaciar Carrito", command=self.clear_cart).pack(fill="x", pady=5)

        ttk.Label(cart_frame, text="TOTAL:").pack()
        self.total_label = ttk.Label(cart_frame, font=("Arial", 20, "bold"), text="$ 0")
        self.total_label.pack()

        ttk.Button(cart_frame, text="Procesar Venta", command=self.process_sale).pack(fill="x", pady=10)

        # Menú superior
        admin_menu = tk.Menu(self.root)
        self.root.config(menu=admin_menu)

        file_menu = tk.Menu(admin_menu, tearoff=0)
        admin_menu.add_cascade(label="Administración", menu=file_menu)

        file_menu.add_command(label="Gestionar Productos", command=self.manage_products)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)


        # --------- PRODUCTOS ---------
        products_frame = ttk.LabelFrame(main, text="Productos")
        products_frame.grid(row=0, column=0, sticky="nsew", padx=10)

        self.products_container = ttk.Frame(products_frame)
        self.products_container.pack(fill="both", expand=True)

        # --------- CARRITO ---------
        cart_frame = ttk.LabelFrame(main, text="Carrito de Compras")
        cart_frame.grid(row=0, column=1, sticky="nsew", padx=10)

        self.cart_list = tk.Listbox(cart_frame, font=("Arial", 12), height=20)
        self.cart_list.pack(fill="both", expand=True)

        ttk.Button(cart_frame, text="Eliminar", command=self.remove_from_cart).pack(fill="x")
        ttk.Button(cart_frame, text="Vaciar", command=self.clear_cart).pack(fill="x", pady=5)

        ttk.Label(cart_frame, text="TOTAL:").pack()
        self.total_label = ttk.Label(cart_frame, font=("Arial", 20, "bold"), text="$ 0")
        self.total_label.pack()

        ttk.Button(cart_frame, text="Procesar Venta", command=self.process_sale).pack(fill="x", pady=10)
        self.load_products()

        ttk.Button(cart_frame, text="Actualizar pagina", command=self.reload).pack(fill="x", pady=10)
    

    def reload(self):
        import os, sys
        if messagebox.askyesno("Reiniciar aplicación", "La aplicación se reiniciará. ¿Deseas continuar?"):
            # Cerrar la ventana principal
            try:
                self.root.destroy()
            except Exception:
                pass
            # Ruta al script main.py (misma carpeta que este archivo)
            main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
            # Reemplaza el proceso actual por una nueva instancia de Python ejecutando main.py
            os.execv(sys.executable, [sys.executable, main_path])

    
    # ------------------- VENTANA DE PRODUCTOS -------------------
    def manage_products(self):
        messagebox.showinfo("Gestión de productos", "Aquí puedes crear, editar o eliminar productos.")
        """Abre una nueva ventana para la gestión de productos."""
        manage_window = tk.Toplevel(self.root)
        manage_window.title("Gestionar Productos")
        manage_window.geometry("600x400")

        # Frame para añadir productos
        add_frame = ttk.LabelFrame(manage_window, text="Añadir Producto", padding="10")
        add_frame.pack(pady=10, fill=tk.X)

        ttk.Label(add_frame, text="Nombre:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.prod_name_entry = ttk.Entry(add_frame)
        self.prod_name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(add_frame, text="Precio:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.prod_price_entry = ttk.Entry(add_frame)
        self.prod_price_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(add_frame, text="Categoría:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.prod_category_entry = ttk.Entry(add_frame)
        self.prod_category_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(add_frame, text="Stock:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.prod_stock_entry = ttk.Entry(add_frame)
        self.prod_stock_entry.grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        self.prod_stock_entry.insert(0, "0") # Valor por defecto

        ttk.Button(add_frame, text="Añadir Producto", command=self._add_product_admin).grid(row=4, columnspan=2, pady=10)

        # Lista de productos (para visualizar y editar/eliminar)
        products_list_frame = ttk.LabelFrame(manage_window, text="Lista de Productos", padding="10")
        products_list_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.products_tree = ttk.Treeview(products_list_frame, columns=("ID", "Nombre", "Precio", "Categoría", "Stock"), show="headings")
        self.products_tree.heading("ID", text="ID")
        self.products_tree.heading("Nombre", text="Nombre")
        self.products_tree.heading("Precio", text="Precio")
        self.products_tree.heading("Categoría", text="Categoría")
        self.products_tree.heading("Stock", text="Stock")
        self.products_tree.column("ID", width=50)
        self.products_tree.column("Nombre", width=150)
        self.products_tree.column("Precio", width=80)
        self.products_tree.column("Categoría", width=100)
        self.products_tree.column("Stock", width=60)
        self.products_tree.pack(fill=tk.BOTH, expand=True)

        ttk.Button(products_list_frame, text="Actualizar Lista", command=self._load_products_admin).pack(pady=5)
        ttk.Button(products_list_frame, text="Eliminar Producto Seleccionado", command=self._delete_product_admin).pack(pady=5)
        


        self._load_products_admin() # Cargar productos al abrir la ventana de administración
        self.load_products()

    def _add_product_admin(self):
        name = self.prod_name_entry.get()
        price_str = self.prod_price_entry.get()
        category = self.prod_category_entry.get()
        stock_str = self.prod_stock_entry.get()

        if not name or not price_str:
            messagebox.showwarning("Advertencia", "Nombre y Precio son campos obligatorios.")
            return

        try:
            price = float(price_str)
            stock = int(stock_str)
        except ValueError:
            messagebox.showwarning("Advertencia", "Precio y Stock deben ser números válidos.")
            return

        db_manager.add_product(name, price, category, stock)
        messagebox.showinfo("Éxito", "Producto añadido correctamente.")
        self._load_products_admin()
        self.prod_name_entry.delete(0, tk.END)
        self.prod_price_entry.delete(0, tk.END)
        self.prod_category_entry.delete(0, tk.END)
        self.prod_stock_entry.delete(0, tk.END)
        self.prod_stock_entry.insert(0, "0")



    def _load_products_admin(self):
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
            products = db_manager.get_all_products()
        for product in products:
            self.products_tree.insert("", tk.END, values=product)
            self.load_products() # Recargar los botones en la ventana principal


    def _delete_product_admin(self):
        selected_item = self.products_tree.selection()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor, selecciona un producto para eliminar.")
            return

        product_id = self.products_tree.item(selected_item, 'values')[0]
        if messagebox.askyesno("Confirmar Eliminación", "¿Estás seguro de que quieres eliminar este producto?"):
            conn = db_manager.connect_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id=?", (product_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", "Producto eliminado correctamente.")
            self._load_products_admin()

 
    def load_categories(self):
        # Placeholder function: Replace with actual implementation
        print("Loading categories...")
        self.categories = []  # or fetch from a file/database

    

    def load_products(self):
        for widget in self.products_container.winfo_children():
            widget.destroy()

        productos = db_manager.get_all_products()

        row = col = 0
        for p in productos:
            id, name, price, cantidad, stock = p

            btext = f"{name}\n${price:,.0f}"

            btn = ttk.Button(
                self.products_container, text=btext,
                command=lambda product=p: self.add_to_cart(product)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, ipadx=15, ipady=10, sticky="nsew")

            col += 1
            if col == 3:
                col = 0
                row += 1

    def add_to_cart(self, product):
        pid, name, price, cantidad, stock = product

        if pid not in self.cart:
            self.cart[pid] = {"nombre": name, "precio": price, "cantidad": 1, "id": pid}
        else:
            self.cart[pid]["cantidad"] += 1

        self.update_cart_display()

    def update_cart_display(self):
        self.cart_list.delete(0, tk.END)
        total = 0

        for k, item in self.cart.items():
            subtotal = item["cantidad"] * item["precio"]
            total += subtotal
            self.cart_list.insert(tk.END, f"{item['nombre']} ({item['cantidad']} x ${item['precio']}) - ${subtotal}")

        self.total_label.config(text=f"$ {total:,.0f}")

    def remove_from_cart(self):
        sel = self.cart_list.curselection()
        if not sel:
            return

        index = sel[0]
        key = list(self.cart.keys())[index]

        del self.cart[key]
        self.update_cart_display()

    def clear_cart(self):
        self.cart = {}
        self.update_cart_display()

    # ------------------- PROCESAR VENTA -------------------

    def process_sale(self):
        if not self.cart:
            messagebox.showwarning("Carrito vacío", "Agrega productos antes de procesar.")
            return

        total = float(self.total_label.cget("text").replace("$", "").replace(",", ""))

        items = []
        for k, item in self.cart.items():
            items.append({
                "id": item["id"],
                "cantidad": item["cantidad"],
                "precio": item["precio"]
            })

        venta_id = db_manager.record_sale(total, items)

        self.generate_invoice_pdf(venta_id, items, total)

        messagebox.showinfo("Venta registrada", f"Venta #{venta_id} guardada con éxito.\nFactura generada.")
        self.clear_cart()

    # ------------------- FACTURA PDF -------------------

    def generate_invoice_pdf(self, venta_id, items, total, cliente="Cliente General",
                         metodo_pago="Efectivo", ruta_salida="factura.pdf"):
    
        # Datos generados automáticamente
        fecha = datetime.now().strftime("%d/%m/%Y")
        numero_pedido = str(venta_id).zfill(4)
        # 1 cm = 28,34645672 puntos
        c = canvas.Canvas(ruta_salida, pagesize=(215, 397))  # Tamaño personalizado en puntos (1 punto = 1/72 pulgadas)
        width=215 #tamaño impresión horizontal 7,59 cm
        height=397 #tamaño impresión vertical 14 cm
        
        y = height - 40

        # ENCABEZADO
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20, y, f"🧾 PEDIDO #{numero_pedido} — EL PANZE")
        y -= 30

        c.setFont("Helvetica-Bold", 11)
        c.drawString(20, y, "Fecha:")
        c.setFont("Helvetica", 11)
        c.drawString(60, y, f"{fecha}")
        y -= 10
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20, y, "Cliente:")
        c.setFont("Helvetica", 11)
        c.drawString(70, y, f"{cliente}")
        y -= 10
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20, y, "Método de pago:")
        c.setFont("Helvetica", 11)
        c.drawString(110, y, f"{metodo_pago}")
        y -= 30

        # TABLA
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20, y, "Cantidad")
        c.drawString(80, y, "Producto")
        c.drawString(160, y, "Total")
        y -= 10
        c.line(20, y, 200, y)
        y -= 10

        # ITEMS
        c.setFont("Helvetica-Bold", 10)

        for item in items:
            pid = item["id"]
            cantidad = item["cantidad"]
            precio_unitario = item["precio"]

            # OBTENER NOMBRE DEL PRODUCTO
            prod = db_manager.nombre_producto(pid)
            nombre_producto = prod[0]  # (nombre, precio)
            
            subtotal = cantidad * precio_unitario
            subtotal= int(subtotal)
            c.drawString(20, y, str(cantidad))
            c.drawString(80, y, nombre_producto)
            c.drawString(160, y, f"${subtotal:,}".replace(",", "."))

            y -= 15

            if y < 7:
                c.showPage()
                y = height - 7

        # TOTAL
        y -= 10
        c.line(20, y, 200, y)
        y -= 15

        c.setFont("Helvetica-Bold", 11)
        total= int( total)
        total_formateado = f"${total:,}".replace(",", ".")
        c.drawString(20, y, f"Total a pagar: {total_formateado} COP")

        # MENSAJE FINAL
        y -= 50
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20, y, "Gracias por tu compra 💛")
        y -= 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20, y, "“El sabor diferente de siempre.”")

        c.save()
        print(f"Factura generada: {ruta_salida}")


