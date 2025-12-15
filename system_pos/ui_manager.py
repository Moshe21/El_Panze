import os
import tkinter as tk
from tkinter import ttk, messagebox
import db_manager
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import subprocess
from PIL import Image, ImageTk


class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("El Panze - Sistema POS 4.2")
        self.root.geometry("1024x768")

        self.cart = {}
        self.ultima_factura = None  # Guardar datos de la última factura impresa
        self.saved_carts = {}  # Carritos temporales guardados {nombre: {product_id: {...}}}
        self.current_cart_name = "Carrito Principal"  # Nombre del carrito actual

        # Cargar imagen de fondo
        #self.background_image = None
        #self.bg_label = None
        #imagen_fondo = "asset/logo.png"
        #self.load_background_image( imagen_fondo)
        
            


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

        self.style.configure('Category.TButton', font=('Arial', 12, 'bold'), foreground='#4A90E2', background='#4A90E2')
        self.style.map('Category.TButton', background=[('active', '#3A7ADF')])

        self.style.configure('Action.TButton', font=('Arial', 12, 'bold'), foreground='#A9D18E', background='#A9D18E')
        self.style.map('Action.TButton', background=[('active', '#8BC34A')])


        self.create_widgets()
        

        # **CORRECCIÓN IMPORTANTE AQUÍ:**
        # Llama a update_idletasks para asegurar que todos los widgets creados por create_widgets()
        # estén completamente renderizados y sus gestores de geometría hayan sido procesados.
        self.load_products()
        
        
    
    def load_background_image(self, imagen_fondo):
        
        try:
            img = Image.open(imagen_fondo)
            img = img.resize((self.root.winfo_screenwidth(), self.root.winfo_screenheight()), Image.ANTIALIAS)
            self.background_image = ImageTk.PhotoImage(img)
            if self.bg_label is None:
                self.bg_label = tk.Label(self.root, image=self.background_image)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.bg_label.config(image=self.background_image)
        except Exception as e:
            print(f"No se pudo cargar la imagen de fondo: {e}")


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

    def create_widgets(self,products= db_manager.count_products()):
        # Marco principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sección de Productos (izquierda)
        if products >= 0:
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

        # Botones para guardar/cargar carritos
        cart_management_frame = ttk.Frame(cart_frame)
        cart_management_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(cart_management_frame, text="💾 Guardar Carrito", command=self.save_current_cart).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(cart_management_frame, text="📂 Cargar Carrito", command=self.show_load_cart_modal).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=2)

        ttk.Button(cart_frame, text="Actualizar pagina", command=self.reload).pack(fill="x", pady=10)
    


        # Menú de administración (opcional, podría ser una ventana separada)
        admin_menu = tk.Menu(self.root)
        self.root.config(menu=admin_menu)
        file_menu = tk.Menu(admin_menu, tearoff=0)
        admin_menu.add_cascade(label="Administración", menu=file_menu)
        file_menu.add_command(label="Gestionar Productos", command=self.manage_products)
        file_menu.add_command(label="Ver Facturas", command=self.view_facturas)
        file_menu.add_command(label="Estadísticas del Día", command=self.show_daily_statistics)
        file_menu.add_separator()
        file_menu.add_command(label="Reimprimir última factura", command=self.show_reprint_modal)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)

        

    def _imprimir_factura(self, ruta_salida):
        """Imprime la factura 2 veces."""
        impresora = "POS-58"
        
        try:
            comando = [
                r"C:\Users\Panze\Documents\GitHub\El_Panze\system_pos\SumatraPDF-3.5.2-64.exe",
                "-print-to", impresora,
                "-silent",
                ruta_salida
            ]
            subprocess.run(comando, shell=True)
            print(f"Copia impresa correctamente.")
        except Exception as e:
            print(f"Error al imprimir copia : {e}")

    def show_reprint_modal(self):
        """Muestra un modal para reimprimir la última factura."""
        if not self.ultima_factura:
            messagebox.showwarning("Sin factura", "No hay ninguna factura para reimprimir.")
            return
        
        ReprintModal(self.root, self.ultima_factura, self._imprimir_factura)

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


    def load_products(self):
        """Carga los productos de la base de datos y crea botones."""
        for widget in self.product_buttons_frame.winfo_children():
            widget.destroy() # Limpiar botones existentes
        products = db_manager.get_all_products()
        # Mantener referencias a las imágenes para evitar que el garbage collector las elimine
        if not hasattr(self, 'product_images'):
            self.product_images = {}
        row, col = 0, 0
        for product in products:
            product_id, name, price, category, stock = product
            # Ocultar productos sin stock
            try:
                stock_val = int(stock) if stock is not None else 0
            except Exception:
                stock_val = 0
            if stock_val <= 0:
                continue
            button_text = f"{name}\n${price:,.0f}" # Formatear precio

            # Intentar cargar imagen desde assets con varios nombres/fallbacks
            img_path_candidates = [
                f"assets/{product_id}.png",
                f"assets/{product_id}.jpg",
                f"assets/{product_id}.jpeg",
                f"assets/{name}.png",
                f"assets/{name}.jpg",
                f"assets/{name}.jpeg",
                f"assets/{name.replace(' ', '_')}.png",
                f"assets/{name.replace(' ', '_')}.jpg",
                f"assets/{name.replace(' ', '_')}.jpeg",
            ]

            photo = None
            for ppath in img_path_candidates:
                try:
                    if os.path.exists(ppath):
                        img = Image.open(ppath)
                        img = img.convert('RGBA')
                        img = img.resize((96, 72), Image.ANTIALIAS)
                        photo = ImageTk.PhotoImage(img)
                        # Guardar referencia
                        self.product_images[product_id] = photo
                        break
                except Exception:
                    photo = None

            if photo:
                btn = ttk.Button(self.product_buttons_frame, text=button_text, image=photo, compound='top',
                                 command=lambda p=(product_id, name, price): self.add_to_cart(p))
            else:
                btn = ttk.Button(self.product_buttons_frame, text=button_text,
                                 command=lambda p=(product_id, name, price): self.add_to_cart(p))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            col += 1
            if col > 3: # 4 botones por fila
                col = 0
                row += 1
        if col > 0:  # Only configure if there are columns
            self.product_buttons_frame.grid_columnconfigure(tuple(range(col)), weight=1)

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

    def save_current_cart(self):
        """Guarda el carrito actual con un nombre temporal."""
        if not self.cart:
            messagebox.showwarning("Carrito vacío", "No hay productos para guardar.")
            return
        
        # Pedir nombre para el carrito
        dialog = tk.Toplevel(self.root)
        dialog.title("Guardar Carrito")
        dialog.geometry("350x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Nombre del carrito:", font=('Arial', 10)).pack(pady=10)
        entry = ttk.Entry(dialog, font=('Arial', 10))
        entry.pack(fill=tk.X, padx=15, pady=5)
        entry.focus()
        
        def save_with_name():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning("Nombre vacío", "Debes ingresar un nombre para el carrito.")
                return
            # Guardar una copia del carrito actual
            self.saved_carts[name] = dict(self.cart)
            messagebox.showinfo("Guardado", f"Carrito '{name}' guardado exitosamente.")
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        ttk.Button(btn_frame, text="Guardar", command=save_with_name).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def show_load_cart_modal(self):
        """Muestra modal para seleccionar un carrito guardado."""
        if not self.saved_carts:
            messagebox.showinfo("Sin carritos", "No hay carritos guardados.")
            return
        
        LoadCartModal(self.root, self.saved_carts, self.load_saved_cart)

    def load_saved_cart(self, cart_name):
        """Carga un carrito guardado."""
        if cart_name not in self.saved_carts:
            messagebox.showerror("Error", "El carrito no existe.")
            return
        
        if self.cart and not messagebox.askyesno("Confirmar", "El carrito actual tiene items. ¿Deseas reemplazarlo?"):
            return
        
        self.cart = dict(self.saved_carts[cart_name])
        self.current_cart_name = cart_name
        self.update_cart_display()
        messagebox.showinfo("Éxito", f"Carrito '{cart_name}' cargado.")

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

    def view_facturas(self):
        """Abre una nueva ventana para visualizar todas las facturas."""
        FacturasWindow(self.root)

    def show_daily_statistics(self):
        """Abre un selector de fecha y muestra estadísticas para la fecha elegida."""
        # Modal simple para seleccionar fecha (YYYY-MM-DD)
        class DateSelectionModal(tk.Toplevel):
            def __init__(self, parent, callback):
                super().__init__(parent)
                self.title("Seleccionar Fecha")
                self.geometry("360x140")
                self.resizable(False, False)
                self.callback = callback
                self.transient(parent)
                self.grab_set()

                frm = ttk.Frame(self, padding=10)
                frm.pack(fill=tk.BOTH, expand=True)

                ttk.Label(frm, text="Ingrese la fecha (YYYY-MM-DD):").pack(anchor='w')
                self.entry = ttk.Entry(frm)
                from datetime import date
                self.entry.insert(0, date.today().strftime("%Y-%m-%d"))
                self.entry.pack(fill=tk.X, pady=6)

                btn_frame = ttk.Frame(frm)
                btn_frame.pack(fill=tk.X, pady=6)
                ttk.Button(btn_frame, text="Hoy", command=self.set_today).pack(side=tk.LEFT, padx=4)
                ttk.Button(btn_frame, text="Ayer", command=self.set_yesterday).pack(side=tk.LEFT, padx=4)
                ttk.Button(btn_frame, text="Ver", command=self.on_ok).pack(side=tk.RIGHT, padx=4)
                ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=4)

            def set_today(self):
                from datetime import date
                self.entry.delete(0, tk.END)
                self.entry.insert(0, date.today().strftime("%Y-%m-%d"))

            def set_yesterday(self):
                from datetime import date, timedelta
                self.entry.delete(0, tk.END)
                self.entry.insert(0, (date.today() - timedelta(days=1)).strftime("%Y-%m-%d"))

            def on_ok(self):
                fecha = self.entry.get().strip()
                # Validar formato
                from datetime import datetime
                try:
                    datetime.strptime(fecha, "%Y-%m-%d")
                except Exception:
                    messagebox.showerror("Fecha inválida", "Usa el formato YYYY-MM-DD")
                    return
                self.callback(fecha)
                self.destroy()

        # Callback que calcula y muestra estadísticas para la fecha dada
        def show_statistics_for_date(fecha_str):
            from datetime import datetime
            facturas = db_manager.get_all_facturas()
            facturas_filtradas = [f for f in facturas if f[2].startswith(fecha_str)]
            if not facturas_filtradas:
                messagebox.showinfo("Estadísticas", f"No hay facturas registradas para {fecha_str}.")
                return

            metodos_pago = {}
            for factura in facturas_filtradas:
                fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, observaciones = factura
                if metodo_pago not in metodos_pago:
                    metodos_pago[metodo_pago] = {'total': 0, 'cantidad': 0, 'facturas': []}
                metodos_pago[metodo_pago]['total'] += valor_total
                metodos_pago[metodo_pago]['cantidad'] += 1
                metodos_pago[metodo_pago]['facturas'].append(factura)

            mensaje = f"ESTADÍSTICAS DE VENTAS - {fecha_str}\n"
            mensaje += "=" * 50 + "\n\n"
            suma_total = 0
            for metodo in sorted(metodos_pago.keys()):
                datos = metodos_pago[metodo]
                total = datos['total']
                cantidad = datos['cantidad']
                suma_total += total
                mensaje += f"{metodo}:\n"
                mensaje += f"  • Cantidad de ventas: {cantidad}\n"
                mensaje += f"  • Total: ${total:,.0f}\n\n"

            mensaje += "=" * 50 + "\n"
            mensaje += f"TOTAL GENERAL: ${suma_total:,.0f}"

            messagebox.showinfo("Estadísticas", mensaje)
            DailyStatisticsWindow(self.root, metodos_pago, fecha_str)

        # Abrir modal de selección de fecha
        DateSelectionModal(self.root, show_statistics_for_date)

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

        ttk.Label(add_frame, text="Imagen (opcional):").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        ttk.Button(add_frame, text="Seleccionar Imagen", command=self.select_product_image).grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        self.prod_image_preview = ttk.Label(add_frame)
        self.prod_image_preview.grid(row=5, column=0, columnspan=2, pady=(5,8))

        ttk.Button(add_frame, text="Añadir Producto", command=self._add_product_admin).grid(row=6, columnspan=2, pady=10)

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
        image_path = getattr(self, 'prod_image_path', None)

        if not name or not price_str:
            messagebox.showwarning("Advertencia", "Nombre y Precio son campos obligatorios.")
            return

        try:
            price = float(price_str)
            stock = int(stock_str)
        except ValueError:
            messagebox.showwarning("Advertencia", "Precio y Stock deben ser números válidos.")
            return

        try:
            product_id = db_manager.add_product(name, price, category, stock)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo añadir el producto: {e}")
            return

        # Si se seleccionó una imagen, generar y guardar thumbnail en assets/{id}.png
        if image_path:
            try:
                from PIL import Image
                if not os.path.exists('assets'):
                    os.makedirs('assets')
                img = Image.open(image_path)
                img = img.convert('RGBA')
                img.thumbnail((300, 225), Image.ANTIALIAS)
                dest_path = os.path.join('assets', f"{product_id}.png")
                img.save(dest_path, format='PNG')
            except Exception as e:
                messagebox.showwarning("Imagen", f"No se pudo procesar la imagen: {e}")

        messagebox.showinfo("Éxito", "Producto añadido correctamente.")
        self._load_products_admin()
        self.prod_name_entry.delete(0, tk.END)
        self.prod_price_entry.delete(0, tk.END)
        self.prod_category_entry.delete(0, tk.END)
        self.prod_stock_entry.delete(0, tk.END)
        self.prod_stock_entry.insert(0, "0")
        # Limpiar selección de imagen y preview
        self.prod_image_path = None
        if hasattr(self, 'prod_image_preview_photo'):
            try:
                self.prod_image_preview.config(image='')
            except Exception:
                pass


    def _load_products_admin(self):
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        products = db_manager.get_all_products()
        for product in products:
            self.products_tree.insert("", tk.END, values=product)
        self.load_products() # Recargar los botones en la ventana principal


    def select_product_image(self):
        """Abre un diálogo para seleccionar una imagen y muestra un preview pequeño."""
        from tkinter import filedialog
        try:
            path = filedialog.askopenfilename(title="Seleccionar imagen del producto",
                                              filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp;*.gif" )])
        except Exception:
            path = None

        if not path:
            return

        self.prod_image_path = path
        try:
            img = Image.open(path)
            img = img.convert('RGBA')
            img.thumbnail((96, 72), Image.ANTIALIAS)
            self.prod_image_preview_photo = ImageTk.PhotoImage(img)
            self.prod_image_preview.config(image=self.prod_image_preview_photo)
        except Exception as e:
            messagebox.showwarning("Imagen", f"No se pudo cargar la imagen: {e}")

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

     # ------------------- PROCESAR VENTA -------------------

    def process_sale(self):
        """Procesa la venta con modales de dirección y pago."""
        if not self.cart:
            messagebox.showwarning("Carrito vacío", "Agrega productos antes de procesar.")
            return

        total = float(self.total_label.cget("text").replace("$", "").replace(",", ""))

        # Modal 1: Seleccionar dirección
        def on_address_selected(address, shipping_cost, client):
            total_with_shipping = total + shipping_cost
            
            # Modal 2: Seleccionar método de pago
            def on_payment_method(method, amount_paid, change):
                items = []
                for k, item in self.cart.items():
                    items.append({
                        "id": item["id"],
                        "nombre": item["nombre"],
                        "cantidad": item["cantidad"],
                        "precio": item["precio"]
                    })
                
                # Modal 3: Capturar observaciones de cada producto
                def on_observations_saved(observations):
                    venta_id = db_manager.record_sale(total_with_shipping, items, cliente=client, metodo_pago=method, observaciones=observations)

                    # Recargar productos en UI para ocultar los que quedaron sin stock
                    try:
                        self.load_products()
                    except Exception:
                        pass

                    # Generar factura con detalles de pago, dirección y observaciones
                    self.generate_invoice_pdf(venta_id, items, total_with_shipping, cliente=client, dirrecion=address, metodo_pago=method, cambio=change, observaciones=observations)

                    messagebox.showinfo("Venta Registrada", f"Venta #{venta_id} completada con éxito.\nDirección: {address}\nMétodo: {method}")
                    self.clear_cart()
                
                ObservationsModal(self.root, items, on_observations_saved)
            
            PaymentMethodModal(self.root, total_with_shipping, on_payment_method)
        
        AddressModal(self.root, on_address_selected)
       
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # ------------------- FACTURA PDF -------------------

    def generate_invoice_pdf(self, venta_id, items, total, cliente="Cliente General", dirrecion="Sin Dirección",
                         metodo_pago="Efectivo", cambio=0, observaciones=None, ruta_salida="factura.pdf",Image_path="assets/logo_impresora.jpg"):
    
        # Crear carpeta de facturas si no existe
        import os
        if not os.path.exists("facturas"):
            os.makedirs("facturas")
        
        # Datos generados automáticamente
        fecha = datetime.now().strftime("%d/%m/%Y")
        numero_pedido = str(venta_id).zfill(4)
        ruta_salida=f"facturas/factura{str(venta_id).zfill(4)}.pdf"
        # 1 cm = 28,34645672 puntos
        c = canvas.Canvas(ruta_salida, pagesize=(136, 397))  # Tamaño personalizado en puntos (1 punto = 1/72 pulgadas)
        width=136 #tamaño impresión horizontal 4,8 cm
        height=397 #tamaño impresión vertical 14 cm
    
        y = height - 10

        # ENCABEZADO
       
        c.drawImage(Image_path, 0, y - 98, width=120, height=93, preserveAspectRatio=None, mask='auto')
        y -= 120

        c.setFont("Helvetica-Bold", 10)
        c.drawString(0, y, f"🧾 PEDIDO #{numero_pedido}")
        y -= 30

        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, y, "Fecha:")
        c.setFont("Helvetica", 8)
        c.drawString(30, y, f"{fecha}")
        y -= 10
        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, y, "Cliente:")
        c.setFont("Helvetica", 8)
        c.drawString(35, y, f"{cliente}")
        y -= 10

        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, y, "Dirrecion:")
        c.setFont("Helvetica", 8)
        c.drawString(40, y, f"{dirrecion}")
        y -= 10
        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, y, "Método de pago:")
        c.setFont("Helvetica", 8)
        c.drawString(67, y, f"{metodo_pago}")
        y -= 30

        # TABLA
        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, y, "Cantidad")
        c.drawString(54, y, "Producto")
        c.drawString(109, y, "Total")
        y -= 10
        c.line(0, y, 136, y)
        y -= 10

        # ITEMS
        c.setFont("Helvetica-Bold", 7)
        
        # Create a product lookup dictionary
        all_products = db_manager.get_all_products()
        product_dict = {p[0]: p[1] for p in all_products}  # {id: nombre}

        for item in items:
            pid = item["id"]
            cantidad = item["cantidad"]
            precio_unitario = item["precio"]

            # OBTENER NOMBRE DEL PRODUCTO
            nombre_producto = product_dict.get(pid, "Producto Desconocido")
            
            subtotal = cantidad * precio_unitario
            subtotal= int(subtotal)
            c.drawString(0, y, str(cantidad))
            c.drawString(14, y, nombre_producto)
            c.drawString(109, y, f"${subtotal:,}".replace(",", "."))

            y -= 15

            if y < 7:
                c.showPage()
                y = height - 7

        # TOTAL
        y -= 10
        c.line(0, y, 136, y)
        y -= 15

        c.setFont("Helvetica-Bold", 8)
        total= int( total)
        total_formateado = f"${total:,}".replace(",", ".")
        c.drawString(0, y, f"Total a pagar: {total_formateado} COP")
        y -= 15
        
        # CAMBIO (si aplica)
        if cambio > 0:
            cambio = int(cambio)
            cambio_formateado = f"${cambio:,}".replace(",", ".")
            c.setFont("Helvetica-Bold", 8)
            c.drawString(0, y, f"Cambio: {cambio_formateado} COP")
            y -= 15

        # Observaciones
        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, y, "Observaciones:")
        y -= 10

        # Mostrar observaciones de los productos que se vendieron
        if observaciones:
            c.setFont("Helvetica-Bold", 7)
            for producto_nombre, obs in observaciones.items():
                if obs.strip():  # Solo mostrar si hay observación
                    c.drawString(0, y, f"{producto_nombre}:")
                    y -= 8
                    c.setFont("Helvetica", 7)
                    # Ajustar texto largo en múltiples líneas
                    palabras = obs.split()
                    linea = ""
                    for palabra in palabras:
                        if len(linea + palabra) < 16:  # Aproximadamente 16 caracteres por línea
                            linea += palabra + " "
                        else:
                            if linea:
                                c.drawString(5, y, linea.strip())
                                y -= 8
                            linea = palabra + " "
                    if linea:
                        c.drawString(5, y, linea.strip())
                        y -= 8
                    c.setFont("Helvetica-Bold", 7)
                    y -= 2

            if y < 7:
                c.showPage()
                y = height - 7

        y -= 15
        # MENSAJE FINAL
        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, y, "Gracias por tu compra!")
        y -= 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(27, y, "“El sabor diferente")
        y -= 10
        c.setFont("Helvetica-Bold", 10)
        c.drawString(27, y, "     de siempre.”")
        y -= 10
        c.save()
        print(f"Factura generada: {ruta_salida}")
        
        # Guardar datos de la última factura para reimprimir si es necesario
        self.ultima_factura = {
            'venta_id': venta_id,
            'ruta': ruta_salida,
            'items': items,
            'total': total,
            'cliente': cliente,
            'dirrecion': dirrecion,
            'metodo_pago': metodo_pago,
            'cambio': cambio
        }
        
        # Preguntar si desea sacar copia
        if messagebox.askyesno("Imprimir Factura", "¿Deseas sacar copia de la factura?"):
            self._imprimir_factura(ruta_salida)  
            self._imprimir_factura(ruta_salida)
        else:      
            self._imprimir_factura(ruta_salida)


#ttk.Radiobutton(copias_frame, text="1 copia", variable=self.copias_var, value=1).pack(side=tk.LEFT, padx=10)
        #ttk.Radiobutton(copias_frame, text="2 copias", variable=self.copias_var, value=2).pack(side=tk.LEFT, padx=10)
        
# #















class LoadCartModal(tk.Toplevel):
    """Modal para seleccionar un carrito guardado para cargar."""
    def __init__(self, parent, saved_carts, callback):
        super().__init__(parent)
        self.title("Cargar Carrito")
        self.geometry("400x350")
        self.resizable(True, False)
        self.saved_carts = saved_carts
        self.callback = callback
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
    
    def create_widgets(self):
        ttk.Label(self, text="Carritos Guardados", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Listbox con carritos
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(frame, font=('Arial', 11), yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        # Llenar listbox con carritos guardados
        for cart_name in self.saved_carts.keys():
            items_count = len(self.saved_carts[cart_name])
            self.listbox.insert(tk.END, f"{cart_name} ({items_count} productos)")
        
        # Botones
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ttk.Button(btn_frame, text="Cargar", command=self.load_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)
    
    def load_selected(self):
        """Carga el carrito seleccionado."""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Seleccionar", "Selecciona un carrito primero.")
            return
        
        cart_name = list(self.saved_carts.keys())[selection[0]]
        self.callback(cart_name)
        self.destroy()
    
    def delete_selected(self):
        """Elimina el carrito seleccionado."""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Seleccionar", "Selecciona un carrito primero.")
            return
        
        cart_name = list(self.saved_carts.keys())[selection[0]]
        if messagebox.askyesno("Eliminar", f"¿Deseas eliminar el carrito '{cart_name}'?"):
            del self.saved_carts[cart_name]
            self.listbox.delete(selection[0])
            messagebox.showinfo("Eliminado", f"Carrito '{cart_name}' eliminado.")


class ObservationsModal(tk.Toplevel):
    """Modal para capturar observaciones de cada producto en el carrito."""
    def __init__(self, parent, items, callback):
        super().__init__(parent)
        self.title("Observaciones de Productos")
        self.geometry("600x400")
        self.resizable(True, True)
        self.callback = callback
        self.items = items
        self.observations_entries = {}
        
        self.create_widgets()
        self.transient(parent)
        self.grab_set()
    
    def create_widgets(self):
        # Frame superior con título
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ttk.Label(top_frame, text="Agregar Observaciones a los Productos", font=('Arial', 14, 'bold')).pack(anchor='w')
        ttk.Label(top_frame, text="(Opcional - deja en blanco si no hay observaciones)", font=('Arial', 9, 'italic')).pack(anchor='w')
        
        # Frame con scroll para los productos
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Crear campo de texto para cada producto
        for item in self.items:
            product_name = item.get("nombre", "Producto Desconocido")
            cantidad = item.get("cantidad", 1)
            
            # Frame para cada producto
            item_frame = ttk.LabelFrame(scrollable_frame, text=f"{product_name} (x{cantidad})", padding="10")
            item_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Text widget para observaciones
            obs_text = tk.Text(item_frame, height=3, width=50, font=('Arial', 9))
            obs_text.pack(fill=tk.X)
            
            self.observations_entries[product_name] = obs_text
        
        # Empacar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 15))
        
        # Frame inferior con botones
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=15, pady=15)
        
        ttk.Button(button_frame, text="✓ Guardar y Continuar", command=self.save_observations).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(button_frame, text="✕ Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
    
    def save_observations(self):
        """Guarda todas las observaciones y cierra el modal."""
        observations = {}
        for product_name, text_widget in self.observations_entries.items():
            observations[product_name] = text_widget.get("1.0", tk.END).strip()
        
        self.callback(observations)
        self.destroy()


class FacturasWindow(tk.Toplevel):
    """Ventana para visualizar y gestionar todas las facturas."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Panel de Facturas")
        self.geometry("1000x600")
        self.resizable(True, True)
        
        self.create_widgets()
        self.selected_factura_id = None
        self.load_facturas()
        self.transient(parent)
    
    def create_widgets(self):
        # Frame superior con título y botones de acción
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ttk.Label(top_frame, text="Historial de Facturas", font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        
        action_frame = ttk.Frame(top_frame)
        action_frame.pack(side=tk.RIGHT)

        ttk.Button(action_frame, text="🔄 Actualizar", command=self.load_facturas).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📊 Exportar a CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        self.edit_btn = ttk.Button(action_frame, text="✏️ Editar", command=self.edit_selected_factura, state='disabled')
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        self.delete_btn = ttk.Button(action_frame, text="🗑️ Eliminar", command=self.delete_selected_factura, state='disabled')
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="❌ Cerrar", command=self.destroy).pack(side=tk.LEFT, padx=5)
        
        # Frame para la tabla
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Crear Treeview con barras de desplazamiento
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        self.facturas_tree = ttk.Treeview(
            table_frame, 
            columns=("ID", "Num. Factura", "Fecha/Hora", "Cliente", "Método Pago", "Total", "Observaciones"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        vsb.config(command=self.facturas_tree.yview)
        hsb.config(command=self.facturas_tree.xview)
        
        # Configurar encabezados
        self.facturas_tree.heading("ID", text="ID")
        self.facturas_tree.heading("Num. Factura", text="Nº Factura")
        self.facturas_tree.heading("Fecha/Hora", text="Fecha/Hora")
        self.facturas_tree.heading("Cliente", text="Cliente")
        self.facturas_tree.heading("Método Pago", text="Método Pago")
        self.facturas_tree.heading("Total", text="Total")
        self.facturas_tree.heading("Observaciones", text="Observaciones")
        
        # Configurar ancho de columnas
        self.facturas_tree.column("ID", width=40, anchor="center")
        self.facturas_tree.column("Num. Factura", width=100, anchor="center")
        self.facturas_tree.column("Fecha/Hora", width=150, anchor="center")
        self.facturas_tree.column("Cliente", width=150, anchor="w")
        self.facturas_tree.column("Método Pago", width=120, anchor="center")
        self.facturas_tree.column("Total", width=100, anchor="e")
        self.facturas_tree.column("Observaciones", width=200, anchor="w")
        
        # Colocar en grid
        self.facturas_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Vincular selección para habilitar botones
        self.facturas_tree.bind("<<TreeviewSelect>>", self.on_select_factura)
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Frame inferior con estadísticas
        stats_frame = ttk.LabelFrame(self, text="Estadísticas", padding="10")
        stats_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.stats_label = ttk.Label(stats_frame, text="", font=('Arial', 10))
        self.stats_label.pack(anchor='w')
    
    def load_facturas(self):
        """Carga todas las facturas de la base de datos."""
        # Limpiar tabla
        for item in self.facturas_tree.get_children():
            self.facturas_tree.delete(item)
        
        # Obtener facturas
        facturas = db_manager.get_all_facturas()
        
        # Insertar en tabla
        total_ventas = 0
        for factura in facturas:
            fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, observaciones = factura
            # Formatear total
            total_formateado = f"${valor_total:,.0f}".replace(",", ".")
            
            # Las observaciones ya vienen concatenadas de la BD
            observaciones_texto = observaciones if observaciones else "-"
            
            self.facturas_tree.insert("", tk.END, values=(
                fact_id,
                num_factura,
                fecha_hora,
                cliente if cliente else "No especificado",
                metodo_pago if metodo_pago else "No especificado",
                total_formateado,
                observaciones_texto[:100] if observaciones_texto != "-" else "-"  # Limitar a 100 caracteres
            ))
            total_ventas += valor_total
        
        # Actualizar estadísticas
        total_facturas = len(facturas)
        total_formateado = f"${total_ventas:,.0f}".replace(",", ".")
        self.stats_label.config(
            text=f"Total de facturas: {total_facturas} | Ingresos totales: {total_formateado} COP"
        )
    
    def export_csv(self):
        """Exporta las facturas a un archivo CSV."""
        import csv
        from datetime import datetime
        
        try:
            facturas = db_manager.get_all_facturas()
            
            # Crear nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"facturas_export_{timestamp}.csv"
            
            # Escribir CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['ID', 'Nº Factura', 'Fecha/Hora', 'Cliente', 'Método Pago', 'Total', 'Observaciones'])
                
                for factura in facturas:
                    fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, observaciones = factura
                    writer.writerow([
                        fact_id,
                        num_factura,
                        fecha_hora,
                        cliente if cliente else "No especificado",
                        metodo_pago if metodo_pago else "No especificado",
                        f"${valor_total:,.0f}".replace(",", "."),
                        observaciones if observaciones else "-"
                    ])
            
            messagebox.showinfo("Éxito", f"Facturas exportadas a: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar las facturas: {e}")


    def on_select_factura(self, event):
        """Maneja la selección en la tabla de facturas para habilitar acciones."""
        selection = self.facturas_tree.selection()
        if selection:
            values = self.facturas_tree.item(selection[0])['values']
            try:
                self.selected_factura_id = int(values[0])
            except Exception:
                self.selected_factura_id = None
            self.edit_btn.config(state='normal')
            self.delete_btn.config(state='normal')
        else:
            self.selected_factura_id = None
            self.edit_btn.config(state='disabled')
            self.delete_btn.config(state='disabled')

    def edit_selected_factura(self):
        """Abre modal para editar la factura seleccionada."""
        if not getattr(self, 'selected_factura_id', None):
            messagebox.showwarning("Seleccionar", "Seleccione una factura primero.")
            return
        factura = db_manager.get_factura_by_id(self.selected_factura_id)
        if not factura:
            messagebox.showerror("Error", "Factura no encontrada.")
            return
        EditFacturaModal(self, factura, callback=self.load_facturas)

    def delete_selected_factura(self):
        """Elimina la factura seleccionada tras confirmación."""
        if not getattr(self, 'selected_factura_id', None):
            messagebox.showwarning("Seleccionar", "Seleccione una factura primero.")
            return
        if not messagebox.askyesno("Eliminar factura", "¿Deseas eliminar la factura seleccionada? Esta acción no se puede deshacer."):
            return
        try:
            db_manager.delete_factura(self.selected_factura_id)
            messagebox.showinfo("Eliminada", "Factura eliminada correctamente.")
            self.load_facturas()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la factura: {e}")


class EditFacturaModal(tk.Toplevel):
    """Modal para editar campos básicos de una factura."""
    def __init__(self, parent, factura, callback=None):
        super().__init__(parent)
        self.title("Editar Factura")
        self.geometry("620x660")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.callback = callback

        self.factura = factura
        self.fact_id = factura[0]
        num_factura = factura[1]
        fecha_hora = factura[2]
        cliente = factura[3] if factura[3] else ""
        metodo = factura[4] if factura[4] else ""
        valor = factura[5] if factura[5] else 0

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text=f"Nº Factura: {num_factura}", font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0,8))
        ttk.Label(frm, text=f"Fecha: {fecha_hora}", font=('Arial', 9)).pack(anchor='w', pady=(0,10))

        ttk.Label(frm, text="Cliente:").pack(anchor='w')
        self.entry_cliente = ttk.Entry(frm)
        self.entry_cliente.insert(0, cliente)
        self.entry_cliente.pack(fill=tk.X, pady=4)

        ttk.Label(frm, text="Método de Pago:").pack(anchor='w')
        self.entry_metodo = ttk.Entry(frm)
        self.entry_metodo.insert(0, metodo)
        self.entry_metodo.pack(fill=tk.X, pady=4)

        ttk.Label(frm, text="Total (sin formato):").pack(anchor='w')
        self.entry_total = ttk.Entry(frm)
        # Mostrar total sin formateo (entero)
        try:
            self.entry_total.insert(0, str(int(valor)))
        except Exception:
            self.entry_total.insert(0, str(valor))
        self.entry_total.pack(fill=tk.X, pady=4)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill=tk.X, pady=(12,0))

        ttk.Button(btn_frame, text="Guardar", command=self.save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=6)

    def save(self):
        cliente = self.entry_cliente.get().strip()
        metodo = self.entry_metodo.get().strip()
        total_str = self.entry_total.get().strip()
        import re
        digits = re.sub(r'[^\d]', '', total_str)
        try:
            total = float(digits) if digits else 0.0
        except Exception:
            total = 0.0

        try:
            db_manager.update_factura(self.fact_id, cliente=cliente, metodo_pago=metodo, valor_total=total)
            messagebox.showinfo("Guardado", "Factura actualizada correctamente.")
            if self.callback:
                self.callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar la factura: {e}")


class AutocompleteEntry(ttk.Entry):
    """Entry con autocompletado y listbox flotante."""
    def __init__(self, master, lista_opciones, callback_on_select=None, callback_on_change=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.lista = lista_opciones
        self.callback_on_select = callback_on_select
        self.callback_on_change = callback_on_change
        self.var = tk.StringVar()
        self.config(textvariable=self.var)

        self.var.trace("w", self._on_text_change)
        self.listbox_visible = False

        # Listbox flotante
        self.lb = tk.Listbox(master, height=8, font=('Arial', 10), bg='white', selectmode=tk.SINGLE)
        self.lb.bind("<<ListboxSelect>>", self._seleccionar_item)
        self.bind("<Down>", self._down_key)
        self.bind("<Escape>", self._hide_listbox)
        self.bind("<Return>", self._confirm_selection)

    def _on_text_change(self, *args):
        """Se ejecuta cuando el usuario escribe."""
        if self.callback_on_change:
            self.callback_on_change(self.var.get())
        self._filtrar_lista(*args)

    def _filtrar_lista(self, *args):
        texto = self.var.get().lower()

        # Ocultar si está vacío
        if texto == "":
            if self.listbox_visible:
                self.lb.place_forget()
                self.listbox_visible = False
            return

        # Filtrar lista
        datos_filtrados = [item for item in self.lista if texto in item.lower()]

        # Si no hay coincidencias -> ocultar
        if len(datos_filtrados) == 0:
            if self.listbox_visible:
                self.lb.place_forget()
                self.listbox_visible = False
            return

        # Actualizar Listbox
        self.lb.delete(0, tk.END)
        for item in datos_filtrados:
            self.lb.insert(tk.END, item)

        # Mostrar debajo del entry
        if not self.listbox_visible:
            self.winfo_toplevel().update_idletasks()
            x = self.winfo_x()
            y = self.winfo_y() + self.winfo_height()
            self.lb.place(x=x, y=y, width=self.winfo_width(), height=150)
            self.listbox_visible = True

    def _seleccionar_item(self, event):
        if not self.listbox_visible:
            return

        index = self.lb.curselection()
        if index:
            valor = self.lb.get(index)
            self.var.set(valor)
            if self.callback_on_select:
                self.callback_on_select(valor)

        self.lb.place_forget()
        self.listbox_visible = False

    def _down_key(self, event):
        """Cuando presiona ↓ se mueve al Listbox."""
        if self.listbox_visible:
            self.lb.focus()
            self.lb.selection_set(0)

    def _hide_listbox(self, event=None):
        """Oculta el listbox al presionar Escape."""
        if self.listbox_visible:
            self.lb.place_forget()
            self.listbox_visible = False

    def _confirm_selection(self, event=None):
        """Confirma la selección con Enter."""
        if self.listbox_visible:
            index = self.lb.curselection()
            if index:
                valor = self.lb.get(index)
                self.var.set(valor)
                if self.callback_on_select:
                    self.callback_on_select(valor)
                self.lb.place_forget()
                self.listbox_visible = False


class AddressModal(tk.Toplevel):
    """Modal para seleccionar dirección de envío con autocompletado."""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Seleccionar Dirección")
        self.geometry("600x450")
        self.resizable(False, False)
        self.callback = callback
        self.selected_address = None
        self.shipping_cost = 0
        
        self.direcciones = [
            "Batará", "Aracari", "Milano", "Ibis", "Amazilia", "Jilguero", "Alondra", "Tángara", "Andaríos", "Frontino",
            "Sie 1", "Sie 2", "Sie 3", "Sie 4","andarios",
            "Tángara", "", "Frontino",'bosques alizos','bosques arrayan ','altamorada',
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
        
        self.free_addresses = [
            "Batará", "Aracari", "Milano", "Ibis", "Amazilia", "Jilguero", "Andaríos",
            "Tángara", "", "Frontino",'bosques alizos','bosques arrayan ','altamorada',
            "andarios","Taller Motos",
            "Sie 1", "Sie 2", "Sie 3", "Sie 4",
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
        
        self.create_widgets()
        self.transient(parent)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # informacion del cliente
        ttk.Label(main_frame, text="Nombre cliente", font=('Arial', 14, 'bold')).pack(pady=10)
        
        self.client = ttk.Entry(main_frame, font=('Arial', 11), width=50)
        self.client.pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Seleccionar Dirección", font=('Arial', 14, 'bold')).pack(pady=10)
        ttk.Label(main_frame, text="Escribe para filtrar:", font=('Arial', 10)).pack(anchor='w', pady=(10, 5))
        
        # Entry con autocompletado
        self.address_entry = AutocompleteEntry(main_frame, self.direcciones, 
                                               callback_on_select=self.on_address_selected,
                                               callback_on_change=self.on_address_changed,
                                               font=('Arial', 11), width=50)
        self.address_entry.pack(fill=tk.X, pady=5)
        
        # Label de información (costo de envío)
        self.info_label = ttk.Label(main_frame, text="", foreground="green", font=('Arial', 10))
        self.info_label.pack(pady=10)
        
        # Label de dirección seleccionada
        self.selected_label = ttk.Label(main_frame, text="Dirección seleccionada: Ninguna", 
                                        font=('Arial', 10, 'italic'), foreground="blue")
        self.selected_label.pack(pady=10)
        
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(button_frame, text="✓ Confirmar", command=self.confirm_address, width=20).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(button_frame, text="✕ Cancelar", command=self.cancel, width=20).pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
    
    def on_address_changed(self, address):
        """Se ejecuta cuando el usuario escribe cualquier texto en el entry."""
        address = address.strip()
        
        if address:  # Si hay algo escrito
            # Actualizar el label con cualquier texto que escriba
            self.selected_label.config(text=f"Dirección seleccionada: {address}")
            self.selected_address = address
            
            # Validar si está en la lista de direcciones
            if address in self.direcciones:
                if address in self.free_addresses:
                    self.info_label.config(text="✓ Envío incluido", foreground="green")
                    self.shipping_cost = 0
                else:
                    self.info_label.config(text="🚚 Costo de envío: $3.000", foreground="orange")
                    self.shipping_cost = 3000
            else:
                # Dirección personalizada (no en la lista)
                self.info_label.config(text="🚚 Costo de envío: $3.000", foreground="orange")
                self.shipping_cost = 3000
        else:
            # Si está vacío, limpiar
            self.selected_label.config(text="Dirección seleccionada: Ninguna")
            self.info_label.config(text="", foreground="green")
            self.selected_address = None
            self.shipping_cost = 0
    
    def on_address_selected(self, address):
        """Se ejecuta cuando selecciona una dirección del autocompletado (legacy, mantenido para compatibilidad)."""
        self.on_address_changed(address)
    
    def confirm_address(self):
        self.callback(self.selected_address, self.shipping_cost, self.client.get())
        self.destroy()
    
    def cancel(self):
        self.destroy()
class PaymentMethodModal(tk.Toplevel):
    """Modal para seleccionar método de pago."""
    def __init__(self, parent, total, callback):
        super().__init__(parent)
        self.title("¿Cómo deseas pagar?")
        self.geometry("400x450")
        self.resizable(False, False)
        self.callback = callback
        self.total = total
        
        self.create_widgets()
        self.transient(parent)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        ttk.Label(main_frame, text="¿Cómo deseas pagar?", font=('Arial', 14, 'bold')).pack(pady=10)
        ttk.Label(main_frame, text=f"Total: ${self.total:,.0f}", font=('Arial', 12)).pack(pady=10)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        ttk.Button(button_frame, text="💵 EFECTIVO", command=lambda: self.select_payment('EFECTIVO')).pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="💳 NEQUI", command=lambda: self.select_payment('NEQUI')).pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="💳 DAVIPLATA", command=lambda: self.select_payment('DAVIPLATA')).pack(fill=tk.X, pady=5)
        
    def select_payment(self, method):
        if method == 'EFECTIVO':
            self.destroy()
            CashPaymentModal(self.master, self.total, self.callback)
        else:
            self.callback(method, self.total, 0)
            self.destroy()


class CashPaymentModal(tk.Toplevel):
    """Modal para pago en efectivo."""
    def __init__(self, parent, total, callback):
        super().__init__(parent)
        self.title("Pago en Efectivo")
        self.geometry("450x600")
        self.resizable(False, False)
        self.callback = callback
        self.total = total
        
        self.create_widgets()
        self.transient(parent)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        ttk.Label(main_frame, text="Pago en Efectivo", font=('Arial', 16, 'bold')).pack(pady=10)
        ttk.Label(main_frame, text=f"Total a pagar: ${self.total:,.0f}".replace(",", "."), font=('Arial', 12, 'bold')).pack(pady=10)
        
        ttk.Label(main_frame, text="¿Con cuánto vas a pagar?").pack(anchor='w', pady=(10, 5))
        self.amount_entry = ttk.Entry(main_frame, font=('Arial', 12))
        self.amount_entry.pack(fill=tk.X, pady=5)
        self.amount_entry.bind("<KeyRelease>", self.calculate_change)
        
        ttk.Label(main_frame, text="Tu cambio:").pack(anchor='w', pady=(10, 5))
        self.change_label = ttk.Label(main_frame, text="$0", font=('Arial', 12, 'bold'), foreground='green')
        self.change_label.pack(anchor='w', pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(button_frame, text="Confirmar Pago", command=self.confirm_payment).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=5)
    
    def calculate_change(self, event=None):
        try:
            # Obtener el valor sin formato
            amount_str = self.amount_entry.get().replace(".", "")
            amount = float(amount_str) if amount_str else 0
            
            # Calcular cambio
            change = max(0, amount - self.total)
            
            # Formatear con miles y actualizar label de cambio
            change_formatted = f"${change:,.0f}".replace(",", ".")
            self.change_label.config(text=change_formatted)
            
            # Formatear entrada con miles mientras escribes
            if amount > 0:
                amount_formatted = f"{amount:,.0f}".replace(",", ".")
                # Solo actualizar si es diferente (evita loops)
                if self.amount_entry.get() != amount_formatted:
                    self.amount_entry.delete(0, tk.END)
                    self.amount_entry.insert(0, amount_formatted)
        except ValueError:
            self.change_label.config(text="$0")
    
    def confirm_payment(self):
        try:
            amount = float(self.amount_entry.get().replace(".", ""))
            if amount < self.total:
                messagebox.showwarning("Error", "El monto debe ser mayor o igual al total.")
                return
            change = amount - self.total
            self.callback('EFECTIVO', amount, change)
            self.destroy()
        except ValueError:
            messagebox.showwarning("Error", "Por favor ingresa un monto válido.")


class ReprintModal(tk.Toplevel):
    """Modal para reimprimir la última factura."""
    def __init__(self, parent, ultima_factura, print_callback):
        super().__init__(parent)
        self.title("Reimprimir Factura")
        self.geometry("700x500")
        self.resizable(False, False)
        self.ultima_factura = ultima_factura
        self.print_callback = print_callback
        
        self.create_widgets()
        self.transient(parent)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        ttk.Label(main_frame, text="Reimprimir Factura", font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Información de la factura
        info_frame = ttk.LabelFrame(main_frame, text="Datos de la Factura", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(info_frame, text=f"Número de Venta: #{str(self.ultima_factura['venta_id']).zfill(4)}", 
                  font=('Arial', 11, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(info_frame, text=f"Cliente: {self.ultima_factura['cliente']}", 
                  font=('Arial', 10)).pack(anchor='w', pady=2)
        ttk.Label(info_frame, text=f"Dirección: {self.ultima_factura['dirrecion']}", 
                  font=('Arial', 10)).pack(anchor='w', pady=2)
        ttk.Label(info_frame, text=f"Método de pago: {self.ultima_factura['metodo_pago']}", 
                  font=('Arial', 10)).pack(anchor='w', pady=2)
        ttk.Label(info_frame, text=f"Total: ${self.ultima_factura['total']:,.0f}".replace(",", "."), 
                  font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        
        # Selector de copias
        ttk.Label(main_frame, text="¿Cuántas copias deseas?", font=('Arial', 11)).pack(pady=10)
        
        self.copias_var = tk.IntVar(value=2)
        copias_frame = ttk.Frame(main_frame)
        copias_frame.pack(pady=10)
        
        ttk.Radiobutton(copias_frame, text="1 copia", variable=self.copias_var, value=1).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(copias_frame, text="2 copias", variable=self.copias_var, value=2).pack(side=tk.LEFT, padx=10)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(button_frame, text="🖨️ Imprimir", command=self.imprimir).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
    
    def imprimir(self):
        """Imprime la factura el número de copias seleccionadas."""
        copias = self.copias_var.get()
        impresora = "POS-58"
        ruta = self.ultima_factura['ruta']
        
        for copia in range(copias):
            try:
                comando = [
                    r"C:\Users\Panze\Documents\GitHub\El_Panze\system_pos\SumatraPDF-3.5.2-64.exe",
                    "-print-to", impresora,
                    "-silent",
                    ruta
                ]
                subprocess.run(comando, shell=True)
                print(f"Copia {copia + 1} de {copias} impresa correctamente.")
            except Exception as e:
                print(f"Error al imprimir copia {copia + 1}: {e}")
                messagebox.showerror("Error", f"Error al imprimir copia {copia + 1}: {e}")
                return
        
        messagebox.showinfo("Éxito", f"Se imprimieron {copias} copia(s) correctamente.")
        self.destroy()


class DailyStatisticsWindow(tk.Toplevel):
    """Ventana para mostrar estadísticas detalladas de ventas del día por método de pago."""
    def __init__(self, parent, metodos_pago, fecha):
        super().__init__(parent)
        self.title("Estadísticas Detalladas del Día")
        self.geometry("1000x600")
        self.resizable(True, True)
        
        self.metodos_pago = metodos_pago
        self.fecha = fecha
        
        self.create_widgets()
        self.transient(parent)
    
    def create_widgets(self):
        # Frame superior con título y fecha
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ttk.Label(top_frame, text=f"Estadísticas Detalladas - {self.fecha}", 
                  font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        
        # Frame con tabs para cada método de pago
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Crear una pestaña para cada método de pago
        for metodo_pago in sorted(self.metodos_pago.keys()):
            datos = self.metodos_pago[metodo_pago]
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=f"{metodo_pago} ({datos['cantidad']})")
            
            self.crear_tabla_metodo(tab, metodo_pago, datos)
    
    def crear_tabla_metodo(self, parent_frame, metodo_pago, datos):
        """Crea una tabla con las facturas de un método de pago específico."""
        # Frame superior con resumen
        summary_frame = ttk.LabelFrame(parent_frame, text="Resumen", padding="10")
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(summary_frame, text=f"Cantidad de ventas: {datos['cantidad']}", 
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=20)
        ttk.Label(summary_frame, text=f"Total: ${datos['total']:,.0f}", 
                  font=('Arial', 11, 'bold'), foreground='green').pack(side=tk.LEFT, padx=20)
        
        # Frame con tabla de facturas
        table_frame = ttk.LabelFrame(parent_frame, text=f"Facturas - {metodo_pago}", padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Crear Treeview
        tree = ttk.Treeview(table_frame, columns=("ID", "Nº Factura", "Hora", "Cliente", "Total", "Observaciones"), 
                           show="headings", height=15)
        
        # Configurar encabezados
        tree.heading("ID", text="ID")
        tree.heading("Nº Factura", text="Nº Factura")
        tree.heading("Hora", text="Hora")
        tree.heading("Cliente", text="Cliente")
        tree.heading("Total", text="Total")
        tree.heading("Observaciones", text="Observaciones")
        
        # Configurar ancho de columnas
        tree.column("ID", width=50)
        tree.column("Nº Factura", width=80)
        tree.column("Hora", width=80)
        tree.column("Cliente", width=120)
        tree.column("Total", width=100)
        tree.column("Observaciones", width=250)
        
        # Agregar datos a la tabla
        for factura in datos['facturas']:
            fact_id, num_factura, fecha_hora, cliente, metodo, valor_total, observaciones = factura
            
            # Extraer solo la hora de fecha_hora
            hora = fecha_hora.split(" ")[1] if " " in fecha_hora else fecha_hora
            
            # Limitar observaciones a 50 caracteres para visualización
            obs_display = (observaciones[:50] + "...") if observaciones and len(observaciones) > 50 else (observaciones or "-")
            
            tree.insert("", tk.END, values=(
                fact_id,
                num_factura,
                hora,
                cliente if cliente else "No especificado",
                f"${valor_total:,.0f}".replace(",", "."),
                obs_display
            ))
        
        # Agregar scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


