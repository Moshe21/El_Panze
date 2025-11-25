import tkinter as tk
from tkinter import ttk, messagebox
import db_manager



class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("El Panze - Sistema POS")
        self.root.geometry("1024x768")

        self.cart = {}

        # Cargar imagen de fondo
        #self.background_image = None
        self.bg_label = None
        #self.load_background_image()

        # Estilos (movidos aquí para asegurar que los estilos se definan antes de que los widgets los usen)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabel', background='white', font=('Arial', 12))

        self.style.configure('Product.TButton', font=('Arial', 10, 'bold'), foreground='black',
                             background='white', borderwidth=2, relief="solid", padding=5)
        self.style.map('Product.TButton',
                       foreground=[('active', 'white'), ('!disabled', 'black')],
                       background=[('active', '#5CB85C'), ('!disabled', 'white')])

        self.style.configure('Category.TButton', font=('Arial', 12, 'bold'), foreground='white', background='#4A90E2')
        self.style.map('Category.TButton', background=[('active', '#3A7ADF')])

        self.style.configure('Action.TButton', font=('Arial', 12, 'bold'), foreground='white', background='#A9D18E')
        self.style.map('Action.TButton', background=[('active', '#8BC34A')])


        self.create_widgets()

        # **CORRECCIÓN IMPORTANTE AQUÍ:**
        # Llama a update_idletasks para asegurar que todos los widgets creados por create_widgets()
        # estén completamente renderizados y sus gestores de geometría hayan sido procesados.
        self.root.update_idletasks()
    
        self.load_categories()
        self.display_products_by_category()

    
    
    def display_products_by_category(self, category_name=""):
        for widget in self.product_buttons_frame.winfo_children():
            widget.destroy()

        products = db_manager.get_all_products()
        filtered_products = [p for p in products if p[3] == category_name]  # p[3] es la categoría

        row, col = 0, 0
        for product in filtered_products:
            product_id, name, price, category, stock = product
            button_text = f"{name}\n${price:,.0f}"
            btn = ttk.Button(self.product_buttons_frame, text=button_text,
                            command=lambda p=(product_id, name, price): self.add_to_cart(p))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            col += 1
            if col > 3:
                col = 0
                row += 1

    def create_widgets(self):
        # Marco principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sección de Productos (izquierda)
        products_frame = ttk.LabelFrame(main_frame, text="Productos", padding="10")
        products_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=2) # Más espacio para productos

        self.product_buttons_frame = ttk.Frame(products_frame)
        self.product_buttons_frame.pack(fill=tk.BOTH, expand=True)

        # Sección de Carrito y Total (derecha)
        cart_frame = ttk.LabelFrame(main_frame, text="Carrito de Compras", padding="10")
        cart_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(1, weight=1)

        self.cart_listbox = tk.Listbox(cart_frame, height=15, font=('Arial', 12))
        self.cart_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Button(cart_frame, text="Eliminar del Carrito", command=self.remove_from_cart).pack(fill=tk.X, pady=2)

        total_frame = ttk.Frame(cart_frame)
        total_frame.pack(fill=tk.X, pady=10)
        ttk.Label(total_frame, text="Total:").pack(side=tk.LEFT)
        self.total_label = ttk.Label(total_frame, text="$ 0.00", font=('Arial', 16, 'bold'))
        self.total_label.pack(side=tk.RIGHT)

        # Botones de Acción (al final)
        action_buttons_frame = ttk.Frame(cart_frame)
        action_buttons_frame.pack(fill=tk.X, pady=10)

        ttk.Button(action_buttons_frame, text="Realizar Venta", command=self.process_sale, style='TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(action_buttons_frame, text="Vaciar Carrito", command=self.clear_cart, style='TButton').pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)

        # Menú de administración (opcional, podría ser una ventana separada)
        admin_menu = tk.Menu(self.root)
        self.root.config(menu=admin_menu)
        file_menu = tk.Menu(admin_menu, tearoff=0)
        admin_menu.add_cascade(label="Administración", menu=file_menu)
        file_menu.add_command(label="Gestionar Productos", command=self.manage_products)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)

        

    def load_products(self):
        """Carga los productos de la base de datos y crea botones."""
        for widget in self.product_buttons_frame.winfo_children():
            widget.destroy() # Limpiar botones existentes

        products = db_manager.get_all_products()
        row, col = 0, 0
        for product in products:
            product_id, name, price, category, stock = product
            button_text = f"{name}\n${price:,.0f}" # Formatear precio
            btn = ttk.Button(self.product_buttons_frame, text=button_text,
                             command=lambda p=(product_id, name, price): self.add_to_cart(p))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            col += 1
            if col > 3: # 4 botones por fila
                col = 0
                row += 1
        self.product_buttons_frame.grid_columnconfigure(tuple(range(col)), weight=1) # Ajustar columnas

    def add_to_cart(self, product):
        """Añade un producto al carrito."""
        product_id, name, price = product
        if product_id in self.cart:
            self.cart[product_id]['cantidad'] += 1
        else:
            self.cart[product_id] = {'nombre': name, 'precio': price, 'cantidad': 1, 'id': product_id}
        self.update_cart_display()

    def remove_from_cart(self):
        """Elimina un producto seleccionado del carrito."""
        selected_indices = self.cart_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Advertencia", "Por favor, selecciona un producto para eliminar.")
            return

        index = selected_indices[0]
        item_text = self.cart_listbox.get(index)
        # Extraer el ID del producto de alguna manera, o reconstruir el carrito para no depender del texto
        # Para simplificar, asumiremos que el orden en el Listbox coincide con alguna lista interna temporal
        # Una mejor implementación sería almacenar los IDs directamente en el Listbox o en una estructura de datos.
        
        # Una forma rudimentaria de obtener el ID del producto del texto:
        # Se asume que el formato es "Nombre del Producto (Cantidad x Precio) - Total"
        # Esto es frágil. Lo ideal es tener un diccionario o lista con los objetos de producto en el carrito.
        
        # Para una implementación más robusta, podemos iterar sobre self.cart
        cart_items_list = list(self.cart.keys())
        if index < len(cart_items_list):
            product_id_to_remove = cart_items_list[index]
            del self.cart[product_id_to_remove]
            self.update_cart_display()
        else:
            messagebox.showerror("Error", "Error al eliminar el producto. Inténtalo de nuevo.")


    def update_cart_display(self):
        """Actualiza la lista del carrito y el total."""
        self.cart_listbox.delete(0, tk.END)
        total = 0
        for product_id, item_data in self.cart.items():
            subtotal = item_data['cantidad'] * item_data['precio']
            self.cart_listbox.insert(tk.END, f"{item_data['nombre']} ({item_data['cantidad']} x ${item_data['precio']:,.0f}) - ${subtotal:,.0f}")
            total += subtotal
        self.total_label.config(text=f"$ {total:,.0f}")

    def clear_cart(self):
        """Vacía el carrito de compras."""
        self.cart = {}
        self.update_cart_display()

    def process_sale(self):
        """Procesa la venta y la registra en la base de datos."""
        if not self.cart:
            messagebox.showwarning("Advertencia", "El carrito está vacío. No hay venta que procesar.")
            return

        total_venta = float(self.total_label.cget("text").replace('$', '').replace(',', ''))
        
        # Preparar los items para el registro en la BD
        items_to_record = []
        for product_id, item_data in self.cart.items():
            items_to_record.append({
                'id': item_data['id'],
                'cantidad': item_data['cantidad'],
                'precio': item_data['precio']
            })

        try:
            venta_id = db_manager.record_sale(total_venta, items_to_record)
            messagebox.showinfo("Venta Exitosa", f"Venta registrada con ID: {venta_id}\nTotal: ${total_venta:,.0f}")
            self.clear_cart()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar la venta: {e}")

    def manage_products(self):
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

    