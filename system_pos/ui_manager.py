import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import db_manager
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import subprocess
from PIL import Image, ImageTk, ImageFilter


def _rounded_widget_bg(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return PALETTE_BG1


def _rounded_rect(canvas_widget, x1, y1, x2, y2, radius, **kwargs):
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1,
        x2, y1 + radius, x2, y2 - radius, x2, y2,
        x2 - radius, y2, x1 + radius, y2, x1, y2,
        x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas_widget.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class RoundedButton(tk.Canvas):
    """Botón redondeado que conserva la paleta y el comportamiento originales."""

    def __init__(self, master, text, command=None, width=120, height=34,
                 fill="#733F34", foreground="#FFFFFF",
                 hover_fill="#5A3028", radius=11, font=("Arial", 10, "bold")):
        super().__init__(master, width=width, height=height, bg=_rounded_widget_bg(master),
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=1)
        self.label, self.command = text, command
        self.fill_color, self.hover_fill = fill, hover_fill
        self.foreground, self.radius, self.text_font = foreground, radius, font
        self.hovered = False
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._activate)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)
        self.after_idle(self._draw)

    def _draw(self, _event=None):
        self.delete("all")
        width, height = max(8, self.winfo_width()), max(8, self.winfo_height())
        fill = self.hover_fill if self.hovered else self.fill_color
        _rounded_rect(self, 2, 2, width - 2, height - 2, self.radius, fill=fill, outline=fill)
        self.create_text(width / 2, height / 2, text=self.label, fill=self.foreground,
                         font=self.text_font, justify="center")

    def _enter(self, _event):
        self.hovered = True
        self._draw()

    def _leave(self, _event):
        self.hovered = False
        self._draw()

    def _activate(self, _event=None):
        self.focus_set()
        if self.command:
            self.command()


class RoundedProductButton(tk.Canvas):
    """Botón de producto original con esquinas redondeadas."""

    def __init__(self, master, product, image, command, sold_out=False):
        super().__init__(master, width=160, height=126, bg=_rounded_widget_bg(master),
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=1)
        self.product, self.photo = product, image
        self.command, self.sold_out = command, sold_out
        self.hovered = False
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._activate)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)
        self.after_idle(self._draw)

    def _draw(self, _event=None):
        self.delete("all")
        width, height = max(20, self.winfo_width()), max(20, self.winfo_height())
        if self.sold_out:
            fill = "#5A4038" if self.hovered else "#3B2B26"
            foreground = "#C9B9A8"
        else:
            fill = "#F39A2E" if self.hovered else "#FFAD43"
            foreground = "#FFFFFF"
        _rounded_rect(self, 2, 2, width - 2, height - 2, 14,
                      fill=fill, outline="#733F34", width=1)
        if self.photo:
            self.create_image(width / 2, 38, image=self.photo)
        product_id, name, price, category, stock = self.product
        name_size = 8 if len(name) > 18 else 10
        self.create_text(10, 76, anchor="nw", text=name, width=max(80, width - 20),
                         fill=foreground, font=("Arial", name_size, "bold"))
        self.create_text(10, height - 8, anchor="sw", text=f"${price:,.0f}",
                         fill=foreground, font=("Arial", 10, "bold"))
        if self.sold_out:
            self.create_text(width - 8, height - 8, anchor="se", text="AGOTADO",
                             fill=foreground, font=("Arial", 8, "bold"))

    def _enter(self, _event):
        self.hovered = True
        self._draw()

    def _leave(self, _event):
        self.hovered = False
        self._draw()

    def _activate(self, _event=None):
        self.focus_set()
        if self.command:
            self.command()

# Paleta global (basada en logo.png)
PALETTE_BG1 = "#D7C6AA"  # Fondo principal claro
PALETTE_BG2 = "#D7C6AA"  # Fondo secundario
PALETTE_ACCENT = '#733F34'  # Acento suave
PALETTE_DARK = '#733F34'  # Marrón oscuro
PALETTE_DARK2 = "#FFFFFF"  # fondo blanco


class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("El Panze - Sistema POS 4.2")
        # Ocupa toda la pantalla
        self.root.state('zoomed')
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")

        self.cart = {}
        self.productos_agotados = set()  # ids de productos sin stock (se pueden vender igual)
        self.ultima_factura = None  # Guardar datos de la última factura impresa
        self.saved_carts = {}  # Carritos temporales guardados {nombre: {product_id: {...}}}
        self.current_cart_name = "Carrito Principal"  # Nombre del carrito actual
        # Saldos iniciales y totales acumulados (en memoria)
        self.saldo_nequi_inicio = 0.0
        self.saldo_daviplata_inicio = 0.0
        self.saldo_nequi_total = 0.0
        self.saldo_daviplata_total = 0.0
        # Control de modo pro
        self.modo_pro_activo = False

        # Contador de usos del código "5263"
        self.codigo_VACIAR_count = 0

        # Cargar saldos iniciales desde la base de datos
        try:
            nequi_db, daviplata_db = db_manager.get_saldos_iniciales()
            self.saldo_nequi_inicio = nequi_db
            self.saldo_daviplata_inicio = daviplata_db
        except Exception:
            pass

        # Cargar imagen de fondo
        #self.background_image = None
        #self.bg_label = None
        #imagen_fondo = "asset/logo.png"
        #self.load_background_image( imagen_fondo)
        
            


        # Paleta basada en logo.png
        self.PALETTE_BG1 = "#D7C6AA"  # Fondo principal claro
        self.PALETTE_BG2 = "#D7C6AA"  # Fondo secundario
        self.PALETTE_BG3 = "#FFAD43"  # Fondo secundario
        self.PALETTE_ACCENT = '#733F34'  # Acento suave
        self.PALETTE_DARK = '#733F34'  # Marrón oscuro
        self.PALETTE_DARK2 = "#FFFFFF"  # Burdeos oscuro

        # Estilos globales (usar 'clam' para mejor control visual)
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        # Fondo raíz
        try:
            self.root.configure(bg=self.PALETTE_BG1)
        except Exception:
            pass

        # Frames y labels
        self.style.configure('TFrame', background=self.PALETTE_BG1, foreground=self.PALETTE_DARK)
        self.style.configure('TLabel', background=self.PALETTE_BG1, foreground=self.PALETTE_DARK, font=('Arial', 12))
        self.style.configure('TLabelFrame', background=self.PALETTE_BG1, foreground=self.PALETTE_DARK)

        # Botones
        # Use dark colors only for text; backgrounds should remain light/accent
        self.style.configure('TButton', font=('Arial', 11, 'bold'), foreground=self.PALETTE_DARK2, background=self.PALETTE_ACCENT, padding=6)
        self.style.map('TButton', background=[('active', self.PALETTE_ACCENT), ('!disabled', self.PALETTE_ACCENT)],
                        foreground=[('active', 'white'), ('!disabled', self.PALETTE_DARK2)])

        # Botón de producto con estilo propio
        self.style.configure('Product.TButton', font=('Arial', 10, 'bold'), foreground=self.PALETTE_DARK, background=self.PALETTE_BG3, borderwidth=1, relief='raised', padding=6)
        self.style.map('Product.TButton', background=[('active', self.PALETTE_ACCENT), ('!disabled', self.PALETTE_BG3)])

        # Producto agotado: se ve oscuro pero sigue siendo clickeable
        self.PALETTE_AGOTADO = '#3B2B26'
        self.PALETTE_AGOTADO_TXT = '#C9B9A8'
        self.style.configure('Agotado.TButton', font=('Arial', 10, 'bold'), foreground=self.PALETTE_AGOTADO_TXT, background=self.PALETTE_AGOTADO, borderwidth=1, relief='sunken', padding=6)
        self.style.map('Agotado.TButton', background=[('active', '#5A4038'), ('!disabled', self.PALETTE_AGOTADO)],
                        foreground=[('active', '#FFFFFF'), ('!disabled', self.PALETTE_AGOTADO_TXT)])

        # Botones de categoría/acción
        self.style.configure('Category.TButton', font=('Arial', 12, 'bold'), foreground=self.PALETTE_DARK2, background=self.PALETTE_ACCENT)
        self.style.map('Category.TButton', background=[('active', self.PALETTE_ACCENT)])
        # Los botones de acción usan fondo de acento y texto oscuro; evitar fondos oscuros
        self.style.configure('Action.TButton', font=('Arial', 12, 'bold'), foreground=self.PALETTE_DARK2, background=self.PALETTE_ACCENT)
        self.style.map('Action.TButton', background=[('active', self.PALETTE_BG2)])

        # Entradas
        self.style.configure('TEntry', fieldbackground=self.PALETTE_BG2, background=self.PALETTE_BG2, foreground=self.PALETTE_DARK)

        # Treeview
        self.style.configure('Treeview', background=self.PALETTE_BG2, fieldbackground=self.PALETTE_BG2, foreground=self.PALETTE_DARK, font=('Arial', 10))
        self.style.configure('Treeview.Heading', background=self.PALETTE_ACCENT, foreground=self.PALETTE_DARK2, font=('Arial', 10, 'bold'))
        # La selección debe usar un color de acento (no los marrones oscuros)
        self.style.map('Treeview', background=[('selected', self.PALETTE_ACCENT)], foreground=[('selected', self.PALETTE_DARK2)])


        self.create_widgets()
        

        # Establecer fondo de madera extraído del logo (si existe)
        try:
            # Llamar después de crear widgets para que las dimensiones estén disponibles
            self.set_wood_background(os.path.join('assets', 'logo.png')) # <--- RUTA DE IMAGEN DE FONDO
            # Actualizar al cambiar el tamaño de la ventana
            self.root.bind('<Configure>', lambda e: self.set_wood_background(os.path.join('assets', 'logo.png'))) # <--- RUTA DE IMAGEN DE FONDO
        except Exception:
            pass

        # Cargar productos
        self.load_products()

    
    def set_wood_background(self, image_path):
        """Carga `image_path`, aplica un filtro sutil y lo usa como fondo escalado.
        Si la ventana aún no tiene tamaño, usa el tamaño de pantalla.
        """
        try:
            if not os.path.exists(image_path): # <--- VERIFICA RUTA DE IMAGEN
                return
            # Asegurar que dimensiones están disponibles
            self.root.update_idletasks()
            w = max(1, self.root.winfo_width())
            h = max(1, self.root.winfo_height())

            img = Image.open(image_path).convert('RGB') # <--- EJECUTA RUTA (ABRIR IMAGEN)
            # Escalar manteniendo aspecto y luego recortar al tamaño de la ventana
            img = img.resize((w, h), Image.LANCZOS)
            # Aplicar leve desenfoque para que no compita con elementos UI
            try:
                img = img.filter(ImageFilter.GaussianBlur(radius=1))
            except Exception:
                pass

            self.background_image = ImageTk.PhotoImage(img)
            if not hasattr(self, 'bg_label') or self.bg_label is None:
                self.bg_label = tk.Label(self.root, image=self.background_image, bd=0)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                # Enviar al fondo
                self.bg_label.lower()
            else:
                self.bg_label.config(image=self.background_image)
                self.bg_label.lower()
        except Exception as e:
            print(f"No se pudo establecer fondo madera: {e}")
        
        
    
    def load_background_image(self, imagen_fondo):
        
        try:
            img = Image.open(imagen_fondo) # <--- EJECUTA RUTA (ABRIR IMAGEN)
            img = img.resize((self.root.winfo_screenwidth(), self.root.winfo_screenheight()), Image.LANCZOS)
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
            try:
                stock_val = int(stock) if stock is not None else 0
            except Exception:
                stock_val = 0
            if stock_val < 0:   # saldo negativo: no se muestra
                continue
            agotado = stock_val == 0
            if agotado:
                self.productos_agotados.add(product_id)
            else:
                self.productos_agotados.discard(product_id)
            btn = RoundedProductButton(
                self.product_buttons_frame, product, None,
                command=lambda p=(product_id, name, price): self.add_to_cart(p),
                sold_out=agotado
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            col += 1
            if col > 3:
                col = 0
                row += 1

    def create_widgets(self, products=None):
        if products is None:
            try:
                products = db_manager.count_products()
            except Exception:
                products = 0

        # Marco principal
        main_frame = ttk.Frame(self.root, padding="0", borderwidth=10, relief="solid")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=1)

        # Sección de Productos (izquierda)
        if products >= 0:
            products_frame = ttk.LabelFrame(main_frame, text="Productos", padding="0", borderwidth=10, relief="solid")
            products_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

            # Canvas y Scrollbar para productos
            canvas = tk.Canvas(products_frame, bg=self.PALETTE_BG1, highlightthickness=0)
            scrollbar = ttk.Scrollbar(products_frame, orient="vertical", command=canvas.yview)
            
            self.product_buttons_frame = ttk.Frame(canvas)
            self.product_buttons_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas_window = canvas.create_window((0, 0), window=self.product_buttons_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Ajustar ancho del frame interno al cambiar tamaño del canvas
            def on_canvas_configure(event):
                canvas.itemconfig(canvas_window, width=event.width)
            canvas.bind("<Configure>", on_canvas_configure)

            # Scroll con rueda del ratón
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            canvas.bind("<MouseWheel>", _on_mousewheel)
            self.product_buttons_frame.bind("<MouseWheel>", _on_mousewheel)

        # Sección de Carrito y Total (derecha)
        cart_frame = ttk.LabelFrame(main_frame, text="Carrito de Compras", padding="0", borderwidth=10, relief="solid")
        cart_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")


        # Frame para carrito y controles de cantidad
        cart_listbox_frame = ttk.Frame(cart_frame)
        cart_listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.cart_listbox = tk.Listbox(cart_listbox_frame, height=15, font=('Arial', 12), bg=PALETTE_BG2, fg=PALETTE_DARK, highlightbackground=PALETTE_BG1)
        self.cart_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        

        RoundedButton(cart_frame, "Eliminar del Carrito", self.remove_from_cart).pack(fill=tk.X, pady=2)
        # Frame para botones + y -
        qty_btns_frame = ttk.Frame(cart_listbox_frame)
        qty_btns_frame.pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.increase_btn = RoundedButton(qty_btns_frame, "+", self.increase_cart_item_qty, width=38, height=34)
        self.increase_btn.pack(pady=(10,2))
        self.decrease_btn = RoundedButton(qty_btns_frame, "-", self.decrease_cart_item_qty, width=38, height=34)
        self.decrease_btn.pack(pady=(2,10))
        # Total
        total_frame = ttk.Frame(cart_frame)
        total_frame.pack(fill=tk.X, pady=10)
        ttk.Label(total_frame, text="Total:").pack(side=tk.LEFT)
        self.total_label = ttk.Label(total_frame, text="$ 0.00", font=('Arial', 16, 'bold'))
        self.total_label.pack(side=tk.RIGHT)

        # Contador de productos vendidos sin stock (se actualiza tras cada venta)
        self.agotados_label = ttk.Label(cart_frame, text="", font=('Arial', 10, 'bold'))
        self.agotados_label.pack(fill=tk.X)
        self.actualizar_contador_agotados()

        # Botones de Acción (al final)
        action_buttons_frame = ttk.Frame(cart_frame)
        action_buttons_frame.pack(fill=tk.X, pady=10)

        RoundedButton(action_buttons_frame, "Realizar Venta", self.process_sale).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        RoundedButton(action_buttons_frame, "Vaciar Carrito", self.confirm_clear_cart).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)

        # Botones para guardar/cargar carritos
        cart_management_frame = ttk.Frame(cart_frame)
        cart_management_frame.pack(fill=tk.X, pady=5)
        
        RoundedButton(cart_management_frame, "💾 Guardar Carrito", self.save_current_cart).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        RoundedButton(cart_management_frame, "📂 Cargar Carrito", self.show_load_cart_modal).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=2)
        RoundedButton(
                    cart_frame,
                    "🕒 Pedidos pendientes",
                    lambda: PendingOrdersModal(self.root, self)
                ).pack(fill=tk.X, pady=4)

        RoundedButton(cart_frame, "Actualizar pagina", self.reload).pack(fill="x", pady=10)
    


        # Menú de administración (opcional, podría ser una ventana separada)
        admin_menu = tk.Menu(self.root, bg=PALETTE_BG2, fg=PALETTE_DARK, activebackground=PALETTE_ACCENT)
        self.root.config(menu=admin_menu)
        file_menu = tk.Menu(admin_menu, tearoff=0, bg=PALETTE_BG2, fg=PALETTE_DARK, activebackground=PALETTE_ACCENT)
        admin_menu.add_cascade(label="Administración", menu=file_menu)
        file_menu.add_command(label="Gestionar Productos", command=self.manage_products)
        file_menu.add_command(label="rellenar stock", command=self.rellenar_stock)
        file_menu.add_separator()
        file_menu.add_command(label="Ver Facturas", command=self.view_facturas)
        file_menu.add_command(label="Estadísticas del Día", command=self.show_daily_statistics)
        file_menu.add_command(label="Configurar Saldos Iniciales", command=self.set_initial_balances)
        file_menu.add_separator()
        file_menu.add_command(label="Reimprimir última factura", command=self.show_reprint_modal)
        file_menu.add_separator()
        file_menu.add_command(label="crear factura empresa", command=self.crear_factura_empresa)
        file_menu.add_command(label="modo pro", command=self.modo_pro)
        file_menu.add_command(label="Exportar Facturas PDF (Excel)", command=self.export_facturas_completas_excel)
        file_menu.add_command(label="Lista de Errores", command=self._show_cart_errors_with_password)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)

        
    def increase_cart_item_qty(self):
        """Aumenta la cantidad del producto seleccionado en el carrito."""
        selected_indices = self.cart_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        cart_items_list = list(self.cart.keys())
        if index < len(cart_items_list):
            product_id = cart_items_list[index]
            self.cart[product_id]['cantidad'] += 1
            self.update_cart_display()

    def decrease_cart_item_qty(self):
        """Disminuye la cantidad del producto seleccionado en el carrito."""
        selected_indices = self.cart_listbox.curselection()
        if not selected_indices:
            return
        index = selected_indices[0]
        cart_items_list = list(self.cart.keys())
        if index < len(cart_items_list):
            product_id = cart_items_list[index]
            if self.cart[product_id]['cantidad'] > 1:
                self.cart[product_id]['cantidad'] -= 1
            else:
                # Si la cantidad llega a 0, eliminar el producto
                del self.cart[product_id]
            self.update_cart_display()

    def _imprimir_factura(self, ruta_salida):
        """Imprime la factura 2 veces."""
        impresora = "POS-58"
        
        try:
            comando = [
                r"C:\Users\Panze\Documents\GitHub\El_Panze\system_pos\SumatraPDF-3.5.2-64.exe", # <--- RUTA EJECUTABLE SUMATRA PDF
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
            main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py")) # <--- RUTA DEL SCRIPT PRINCIPAL
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
        self.productos_agotados = set()
        for product in products:
            product_id, name, price, category, stock = product
            # Stock 0  -> se muestra oscuro, se puede vender igual y queda registrado.
            # Stock < 0 -> saldo negativo: no se muestra.
            try:
                stock_val = int(stock) if stock is not None else 0
            except Exception:
                stock_val = 0
            if stock_val < 0:
                continue
            agotado = stock_val == 0
            if agotado:
                self.productos_agotados.add(product_id)

            # Intentar cargar imagen desde assets con varios nombres/fallbacks
            img_path_candidates = [
                f"assets/{product_id}.png", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{product_id}.jpg", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{product_id}.jpeg", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{name}.png", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{name}.jpg", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{name.replace(' ', '_')}.jpeg", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{name.replace(' ', '_')}.png", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{name.replace(' ', '_')}.jpg", # <--- RUTA CANDIDATA IMAGEN
                f"assets/{name.replace(' ', '_')}.jpeg", # <--- RUTA CANDIDATA IMAGEN
            ]

            photo = None
            for ppath in img_path_candidates:
                try:
                    if os.path.exists(ppath): # <--- VERIFICA RUTA IMAGEN
                        img = Image.open(ppath) # <--- EJECUTA RUTA (ABRIR IMAGEN)
                        img = img.convert('RGBA')
                        img = img.resize((96, 72), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        # Guardar referencia
                        self.product_images[product_id] = photo
                        break
                except Exception:
                    photo = None

            btn = RoundedProductButton(
                self.product_buttons_frame, product, photo,
                command=lambda p=(product_id, name, price): self.add_to_cart(p),
                sold_out=agotado
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            col += 1
            if col > 3: # 4 botones por fila
                col = 0
                row += 1
        if col > 0:  # Only configure if there are columns
            self.product_buttons_frame.grid_columnconfigure(tuple(range(col)), weight=1)

    def actualizar_contador_agotados(self):
        """Refresca el contador de productos vendidos sin stock hoy."""
        if not hasattr(self, 'agotados_label'):
            return
        try:
            n = db_manager.contar_ventas_agotados()
        except Exception:
            n = 0
        if n:
            self.agotados_label.config(text=f"⚠ Vendidos sin stock hoy: {n}", foreground='#B00020')
        else:
            self.agotados_label.config(text="", foreground=self.PALETTE_DARK)

    def add_to_cart(self, product):
        """Añade un producto al carrito."""
        product_id, name, price = product
        if product_id in self.cart:
            self.cart[product_id]['cantidad'] += 1
        else:
            self.cart[product_id] = {'nombre': name, 'precio': price, 'cantidad': 1, 'id': product_id}
        if product_id in self.productos_agotados:
            self.cart[product_id]['agotado'] = True
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
            # Guardar el producto eliminado en la tabla cart_errores
            try:
                item_data = self.cart.get(product_id_to_remove)
                if item_data:
                    single = {product_id_to_remove: dict(item_data)}
                    db_manager.save_cart_error(single)
            except Exception:
                # No interrumpir la eliminación si falla el guardado
                pass

            # Eliminar el producto del carrito y actualizar la vista
            try:
                del self.cart[product_id_to_remove]
            except Exception:
                messagebox.showerror("Error", "Error al eliminar el producto. Inténtalo de nuevo.")
                return
            self.update_cart_display()
        else:
            messagebox.showerror("Error", "Error al eliminar el producto. Inténtalo de nuevo.")


    def update_cart_display(self):
        """Actualiza la lista del carrito y el total."""
        self.cart_listbox.delete(0, tk.END)
        total = 0
        for product_id, item_data in self.cart.items():
            subtotal = item_data['cantidad'] * item_data['precio']
            marca = "⚠ " if item_data.get('agotado') else ""
            self.cart_listbox.insert(tk.END, f"{marca}{item_data['nombre']} ({item_data['cantidad']} x ${item_data['precio']:,.0f}) - ${subtotal:,.0f}")
            total += subtotal
        self.total_label.config(text=f"$ {total:,.0f}")

    def confirm_clear_cart(self):
        """Pide contraseña antes de vaciar el carrito."""
        password = simpledialog.askstring("Contraseña requerida", "Ingrese la contraseña para vaciar el carrito:", show='*', parent=self.root)
        if password is None:
            return
        # Aceptar las contraseñas válidas y manejar la especial '5263'
        if password == "9874+":
            self.clear_cart()
        elif password == "5263":    
            self.codigo_VACIAR_count += 1
            self.cart_error()
        else:
            messagebox.showerror("Contraseña incorrecta", "La contraseña ingresada no es correcta.")

    def clear_cart(self):
        """Vacía el carrito de compras."""
        self.cart = {}
        self.update_cart_display()

    def cart_error(self):
        """Guarda los productos del carrito actual como error en la BD y luego limpia el carrito."""
        if not self.cart:
            messagebox.showwarning("Carrito vacío", "No hay productos para guardar como error.")
            return
        
        try:
            # Guardar carrito como error en la base de datos
            db_manager.save_cart_error(self.cart)
            # Limpiar el carrito
            self.clear_cart()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el carrito: {e}")

    def List_errores(self):
        """Muestra la tabla de errores del carrito visualmente en una nueva ventana."""
        try:
            errores = db_manager.get_all_cart_errores()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los errores: {e}")
            return
        
        if not errores:
            messagebox.showinfo("Sin errores", "No hay errores del carrito registrados.")
            return
        
        # Crear ventana para mostrar los errores
        error_window = tk.Toplevel(self.root)
        error_window.title("Lista de Errores del Carrito")
        error_window.geometry("900x500")
        error_window.transient(self.root)
        
        # Frame superior con botones
        btn_frame = ttk.Frame(error_window)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Button(btn_frame, text="🔄 Actualizar", command=lambda: self._refresh_cart_errors(error_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Eliminar Seleccionado", command=lambda: self._delete_selected_error(error_tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Eliminar Todo", command=self._delete_all_errors).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✖️ Cerrar", command=error_window.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Crear Treeview para mostrar los errores
        tree_frame = ttk.Frame(error_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        error_tree = ttk.Treeview(tree_frame, 
                                   columns=("ID", "Fecha/Hora", "Producto", "Precio", "Cantidad", "Subtotal"),
                                   show="headings",
                                   yscrollcommand=scrollbar.set,
                                   height=15)
        scrollbar.config(command=error_tree.yview)
        
        # Configurar columnas
        error_tree.heading("ID", text="ID")
        error_tree.heading("Fecha/Hora", text="Fecha/Hora")
        error_tree.heading("Producto", text="Producto")
        error_tree.heading("Precio", text="Precio")
        error_tree.heading("Cantidad", text="Cantidad")
        error_tree.heading("Subtotal", text="Subtotal")
        
        error_tree.column("ID", width=30)
        error_tree.column("Fecha/Hora", width=150)
        error_tree.column("Producto", width=300)
        error_tree.column("Precio", width=80)
        error_tree.column("Cantidad", width=80)
        error_tree.column("Subtotal", width=100)
        
        error_tree.pack(fill=tk.BOTH, expand=True)
        
        # Poblar la tabla con datos
        self._populate_cart_errors(error_tree, errores)
        
        # Guardar referencia de la tabla para el contexto
        error_tree.tag_configure('oddrow', background=self.PALETTE_BG2)
        error_tree.tag_configure('evenrow', background=self.PALETTE_BG1)
    
    def _populate_cart_errors(self, tree, errores):
        """Llena la tabla de errores con los datos."""
        for i, error in enumerate(errores):
            error_id, fecha_hora, producto_nombre, precio, cantidad, subtotal = error
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert("", tk.END, iid=error_id, values=(
                error_id,
                fecha_hora,
                producto_nombre,
                f"${precio:,.0f}",
                cantidad,
                f"${subtotal:,.0f}"
            ), tags=(tag,))
    
    def _refresh_cart_errors(self, window):
        """Actualiza la lista de errores del carrito."""
        # Eliminar y recrear la ventana de errores
        window.destroy()
        self.List_errores()
    
    def _delete_selected_error(self, tree):
        """Elimina el error seleccionado de la tabla."""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Por favor, selecciona un error para eliminar.")
            return
        
        error_id = selected[0]
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar este error?"):
            try:
                db_manager.delete_cart_error(error_id)
                tree.delete(error_id)
                messagebox.showinfo("Éxito", "Error eliminado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el error: {e}")
    
    def _delete_all_errors(self):
        """Elimina todos los errores del carrito."""
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar TODOS los errores del carrito?"):
            try:
                db_manager.delete_all_cart_errores()
                messagebox.showinfo("Éxito", "Todos los errores han sido eliminados.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar los errores: {e}")

    def _show_cart_errors_with_password(self):
        """Pide contraseña antes de mostrar la lista de errores del carrito."""
        password = simpledialog.askstring("Contraseña requerida", "Ingrese la contraseña para acceder a la lista de errores:", show='*', parent=self.root)
        if password is None:
            return
        
        if password == "9874+":
            self.List_errores()
        else:
            messagebox.showerror("Contraseña incorrecta", "La contraseña ingresada no es correcta.")

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
            self.clear_cart()
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        ttk.Button(btn_frame, text="Guardar", command=save_with_name).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def save_pending_order(self, client, address):
        if not self.cart:
            messagebox.showwarning("Vacío", "No hay productos para guardar.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Guardar Pedido Pendiente")
        dialog.geometry("400x170")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Nombre del pedido:", font=('Arial', 11, 'bold')).pack(pady=10)
        entry = ttk.Entry(dialog)
        entry.pack(fill=tk.X, padx=20)
        entry.focus()

        def guardar():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning("Error", "Ingresa un nombre.")
                return

            # Guardar en base de datos
            import db_manager
            print(f"[DEBUG] Guardando pedido pendiente: name={name}, client={client}, address={address}, cart={self.cart}")
            items = []
            for k, v in self.cart.items():
                item = {
                    'nombre': v.get('nombre', k),
                    'precio': v.get('precio', 0),
                    'cantidad': v.get('cantidad', 1)
                }
                items.append(item)
            print(f"[DEBUG] Items a guardar: {items}")
            db_manager.save_pending_order_db(name, items, client, address)

            messagebox.showinfo("Guardado", f"Pedido '{name}' guardado en la base de datos.")
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, pady=15, padx=20)

        ttk.Button(btns, text="💾 Guardar", command=guardar).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(btns, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)
        


    def show_load_cart_modal(self):
        """Muestra modal para seleccionar un carrito guardado."""
        if not self.saved_carts:
            messagebox.showinfo("Sin carritos", "No hay carritos guardados.")
            return
        
        LoadCartModal(self.root, self.saved_carts, self.load_saved_cart, app=self)

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

   # ...existing code...
    def rellenar_stock(self):
        """Abre una ventana para establecer el stock de todos los productos."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Rellenar Stock")
        dialog.geometry("350x180")
        dialog.transient(self.root)
        dialog.grab_set()

        frm = ttk.Frame(dialog, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Ingrese el stock para todos los productos:", font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0, 10))
        
        entry = ttk.Entry(frm, font=('Arial', 12), width=20)
        entry.pack(fill=tk.X, pady=5)
        entry.focus()

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill=tk.X, pady=20)

        def ejecutar_update():
            stock_valor = entry.get().strip()
            if not stock_valor:
                messagebox.showwarning("Error", "Ingresa un número de stock.")
                return
            try:
                stock_num = int(stock_valor)
            except ValueError:
                messagebox.showerror("Error", "El valor debe ser un número entero.")
                return

            try:
                # Usar la función de db_manager si existe
                if hasattr(db_manager, 'actualizar_stock'):
                    # asumir signature: actualizar_stock(stock_num)
                    db_manager.actualizar_stock(stock_num)
                else:
                    # Fallback: ejecutar SQL directamente usando connect_db()
                    conn = db_manager.connect_db()
                    cur = conn.cursor()
                    cur.execute("UPDATE productos SET stock = ?", (stock_num,))
                    conn.commit()
                    conn.close()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el stock: {e}")
                return

            # Recargar vistas si existen
            try:
                if hasattr(self, '_load_products_admin'):
                    self._load_products_admin()
            except Exception:
                pass
            try:
                if hasattr(self, 'load_products'):
                    self.load_products()
            except Exception:
                pass

            messagebox.showinfo("Éxito", f"Stock actualizado a {stock_num} para todos los productos.")
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Ejecutar", command=ejecutar_update).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)
# ...existing code...


    def view_facturas(self):
        """Abre una nueva ventana para visualizar todas las facturas."""
        FacturasWindow(self.root, app=self)

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
            """Obtener facturas completas, filtrar por fecha y agregar totales por método.
            Acepta estructuras de columnas dinámicas devueltas por
            `db_manager.get_all_facturas_completas()`.
            """
            try:
                columns, rows = db_manager.get_all_facturas_completas()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudieron cargar las facturas: {e}")
                return

            if not rows:
                messagebox.showinfo("Estadísticas", f"No hay facturas registradas para {fecha_str}.")
                return

            # Normalizar nombres de columnas para buscar índices útiles
            cols = [str(c).strip().lower() for c in columns]

            def find_index(candidates):
                for cand in candidates:
                    cand_norm = cand.lower()
                    for i, name in enumerate(cols):
                        if cand_norm == name or cand_norm in name or name in cand_norm:
                            return i
                return None

            date_idx = find_index(['fecha', 'fecha_hora', 'fecha_venta', 'date', 'created_at'])
            metodo_idx = find_index(['metodo_pago', 'metodo', 'payment_method', 'pago', 'forma_pago'])
            total_idx = find_index(['valor_total', 'total', 'monto', 'valor', 'amount', 'importe'])

            # Fallbacks si no se detectan columnas (mantener compatibilidad con esquema antiguo)
            if date_idx is None:
                date_idx = 2
            if metodo_idx is None:
                metodo_idx = 4
            if total_idx is None:
                total_idx = 5

            # Filtrar filas por fecha (comparando prefijo YYYY-MM-DD)
            facturas_filtradas = []
            for row in rows:
                try:
                    fecha_val = str(row[date_idx])
                except Exception:
                    continue
                if fecha_val.startswith(fecha_str):
                    facturas_filtradas.append(row)

            if not facturas_filtradas:
                messagebox.showinfo("Estadísticas", f"No hay facturas registradas para {fecha_str}.")
                return

            # Agrupar las filas por número de factura para procesar cada factura una sola vez
            metodos_pago = {}
            facturas_por_num = {}
            for fila in facturas_filtradas:
                # intentar obtener num_factura (índice 1 normalmente)
                try:
                    num = str(fila[1])
                except Exception:
                    num = str(fila)
                if num not in facturas_por_num:
                    facturas_por_num[num] = []
                facturas_por_num[num].append(fila)

            # Procesar cada factura (agrupada) una sola vez
            for num_factura, filas in facturas_por_num.items():
                # Buscar el metodo_pago y el total entre las filas de la misma factura
                metodo_pago_raw = ''
                total_factura = None
                for r in filas:
                    try:
                        if not metodo_pago_raw and r[metodo_idx]:
                            metodo_pago_raw = r[metodo_idx]
                    except Exception:
                        pass
                    if total_factura is None:
                        try:
                            if r[total_idx] is not None:
                                total_factura = float(r[total_idx])
                        except Exception:
                            try:
                                total_factura = float(str(r[total_idx]).replace(',',''))
                            except Exception:
                                total_factura = None

                metodo_pago = str(metodo_pago_raw).strip() if metodo_pago_raw else ''
                if total_factura is None:
                    total_factura = 0.0

                # Si el pago está dividido con formato METHOD|AMOUNT(+...)
                if metodo_pago and '|' in metodo_pago and '+' in metodo_pago:
                    partes = [p.strip() for p in metodo_pago.split('+') if p.strip()]
                    for part in partes:
                        try:
                            method, amount_str = part.split('|', 1)
                            method = method.strip() or '(Sin Método)'
                            # limpiar coma y espacios
                            amount = float(amount_str.replace(',', '').strip())
                        except Exception:
                            method = part or '(Sin Método)'
                            try:
                                amount = float(part.split('|')[-1])
                            except Exception:
                                amount = 0.0
                        if method not in metodos_pago:
                            metodos_pago[method] = {'total': 0.0, 'cantidad': 0, 'facturas': []}
                        metodos_pago[method]['total'] += amount
                        metodos_pago[method]['cantidad'] += 1
                        metodos_pago[method]['facturas'].append((filas[0], amount))
                else:
                    method = metodo_pago or '(Sin Método)'
                    if method not in metodos_pago:
                        metodos_pago[method] = {'total': 0.0, 'cantidad': 0, 'facturas': []}
                    metodos_pago[method]['total'] += total_factura
                    metodos_pago[method]['cantidad'] += 1
                    metodos_pago[method]['facturas'].append((filas[0], total_factura))

            # Construir mensaje resumen
            mensaje = f"ESTADÍSTICAS DE VENTAS - {fecha_str}\n"
            mensaje += "=" * 50 + "\n\n"
            suma_total = 0.0
            for metodo in sorted(metodos_pago.keys(), key=lambda s: s.lower()):
                datos = metodos_pago[metodo]
                total = datos['total']
                cantidad = datos['cantidad']
                suma_total += total
                mensaje += f"{metodo}:\n"
                mensaje += f"  • Cantidad de ventas: {cantidad}\n"
                mensaje += f"  • Total: ${total:,.0f}\n\n"

            mensaje += "=" * 50 + "\n"
            mensaje += f"TOTAL GENERAL: ${suma_total:,.0f}"

            # Totales específicos (Nequi/Daviplata/Efectivo) desde el agregado
            total_nequi = sum(v.get('total', 0) for k, v in metodos_pago.items() if (k or '').strip().lower() == 'nequi')
            total_daviplata = sum(v.get('total', 0) for k, v in metodos_pago.items() if (k or '').strip().lower() == 'daviplata')
            total_efectivo = sum(v.get('total', 0) for k, v in metodos_pago.items() if (k or '').strip().lower() == 'efectivo')

            saldo_nequi_inicio = getattr(self, 'saldo_nequi_inicio', 0.0)
            saldo_daviplata_inicio = getattr(self, 'saldo_daviplata_inicio', 0.0)
            saldo_efectivo_inicio = getattr(self, 'saldo_efectivo_inicio', 0.0)
            final_nequi = saldo_nequi_inicio + total_nequi
            final_daviplata = saldo_daviplata_inicio + total_daviplata
            final_efectivo = saldo_efectivo_inicio + total_efectivo

            mensaje += "\n\nSaldos (inicio / ventas del día / final):\n"
            mensaje += f"Nequi: ${saldo_nequi_inicio:,.0f} / ${total_nequi:,.0f} / ${final_nequi:,.0f}\n"
            mensaje += f"Daviplata: ${saldo_daviplata_inicio:,.0f} / ${total_daviplata:,.0f} / ${final_daviplata:,.0f}\n"
            mensaje += f"Efectivo: ${saldo_efectivo_inicio:,.0f} / ${total_efectivo:,.0f} / ${final_efectivo:,.0f}\n"

            messagebox.showinfo("Estadísticas", mensaje)

            # Mostrar ventana detallada
            DailyStatisticsWindow(self.root, metodos_pago, fecha_str)

        # Abrir modal de selección de fecha
        DateSelectionModal(self.root, show_statistics_for_date)

    def set_initial_balances(self):
        """Muestra un modal para configurar los saldos iniciales de Nequi y Daviplata y los guarda en la base de datos."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Saldos Iniciales")
        dialog.geometry("320x180")
        dialog.transient(self.root)
        dialog.grab_set()

        # Cargar valores actuales desde la base de datos

        try:
            nequi_db, daviplata_db, efectivo_db = db_manager.get_saldos_iniciales()
        except Exception:
            nequi_db, daviplata_db, efectivo_db = getattr(self, 'saldo_nequi_inicio', 0.0), getattr(self, 'saldo_daviplata_inicio', 0.0), getattr(self, 'saldo_efectivo_inicio', 0.0)

        ttk.Label(dialog, text="Saldo inicial Nequi:").pack(pady=(10, 2), anchor='w', padx=12)
        nequi_entry = ttk.Entry(dialog)
        nequi_entry.pack(fill=tk.X, padx=12)
        nequi_entry.insert(0, f"{nequi_db}")

        ttk.Label(dialog, text="Saldo inicial Daviplata:").pack(pady=(10, 2), anchor='w', padx=12)
        daviplata_entry = ttk.Entry(dialog)
        daviplata_entry.pack(fill=tk.X, padx=12)
        daviplata_entry.insert(0, f"{daviplata_db}")

        ttk.Label(dialog, text="Saldo inicial Efectivo:").pack(pady=(10, 2), anchor='w', padx=12)
        efectivo_entry = ttk.Entry(dialog)
        efectivo_entry.pack(fill=tk.X, padx=12)
        efectivo_entry.insert(0, f"{efectivo_db}")

        def save_balances():
            try:
                nequi_val = float(nequi_entry.get() or 0)
                daviplata_val = float(daviplata_entry.get() or 0)
                efectivo_val = float(efectivo_entry.get() or 0)
            except ValueError:
                messagebox.showerror("Error", "Introduce valores numéricos válidos.")
                return
            self.saldo_nequi_inicio = nequi_val
            self.saldo_daviplata_inicio = daviplata_val
            self.saldo_efectivo_inicio = efectivo_val
            try:
                db_manager.set_saldos_iniciales((nequi_val, daviplata_val, efectivo_val))
            except Exception as e:
                messagebox.showwarning("Advertencia", f"No se pudo guardar en la base de datos: {e}")
            messagebox.showinfo("Saldos guardados", "Saldos iniciales actualizados correctamente.")
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=12, padx=12)
        ttk.Button(btn_frame, text="Guardar", command=save_balances).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def generate_statistics_pdf(self, fecha_str, metodos_pago, suma_total, nequi_inicio=0.0, daviplata_inicio=0.0):
        """Genera un PDF con las estadísticas del día, incluyendo saldos iniciales y finales."""
        try:
            if not os.path.exists("estadisticas"):
                os.makedirs("estadisticas")
            pdf_name = f"estadisticas/estadisticas_{fecha_str}.pdf"
            c = canvas.Canvas(pdf_name, pagesize=(595, 842))
            width, height = 595, 842
            y = height - 40

            c.setFont("Helvetica-Bold", 18)
            c.drawString(50, y, "ESTADÍSTICAS DE VENTAS")
            y -= 30

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"Fecha: {fecha_str}")
            y -= 30

            c.line(50, y, 545, y)
            y -= 20

            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, "Resumen por Método de Pago:")
            y -= 20

            c.setFont("Helvetica", 10)
            for metodo in sorted(metodos_pago.keys()):
                datos = metodos_pago[metodo]
                total = datos['total']
                cantidad = datos['cantidad']
                c.drawString(70, y, f"• {metodo}:")
                y -= 15
                c.drawString(90, y, f"Cantidad de ventas: {cantidad}")
                y -= 12
                c.drawString(90, y, f"Total: ${total:,.0f}")
                y -= 18

            c.line(50, y, 545, y)
            y -= 20

            # Totales y saldos específicos para Nequi/Daviplata/Efectivo
            total_nequi = sum(v.get('total', 0) for k, v in metodos_pago.items() if (k or '').strip().lower() == 'nequi')
            total_daviplata = sum(v.get('total', 0) for k, v in metodos_pago.items() if (k or '').strip().lower() == 'daviplata')
            total_efectivo = sum(v.get('total', 0) for k, v in metodos_pago.items() if (k or '').strip().lower() == 'efectivo')
            # Permitir que se pase saldo_efectivo_inicio como argumento opcional
            saldo_efectivo_inicio = 0.0
            import inspect
            args = inspect.getfullargspec(self.generate_statistics_pdf).args
            if 'saldo_efectivo_inicio' in args:
                try:
                    saldo_efectivo_inicio = locals().get('saldo_efectivo_inicio', 0.0)
                except Exception:
                    saldo_efectivo_inicio = 0.0
            else:
                saldo_efectivo_inicio = getattr(self, 'saldo_efectivo_inicio', 0.0)
            final_nequi = nequi_inicio + total_nequi
            final_daviplata = daviplata_inicio + total_daviplata
            final_efectivo = saldo_efectivo_inicio + total_efectivo

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"TOTAL GENERAL: ${suma_total:,.0f}")
            y -= 20

            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, "Saldos Nequi / Daviplata / Efectivo:")
            y -= 16
            c.setFont("Helvetica", 10)
            c.drawString(70, y, f"Nequi - Inicio: ${nequi_inicio:,.0f}  Ventas: ${total_nequi:,.0f}  Final: ${final_nequi:,.0f}")
            y -= 14
            c.drawString(70, y, f"Daviplata - Inicio: ${daviplata_inicio:,.0f}  Ventas: ${total_daviplata:,.0f}  Final: ${final_daviplata:,.0f}")
            y -= 14
            c.drawString(70, y, f"Efectivo - Inicio: ${saldo_efectivo_inicio:,.0f}  Ventas: ${total_efectivo:,.0f}  Final: ${final_efectivo:,.0f}")
            y -= 20

            c.setFont("Helvetica", 9)
            c.drawString(50, y, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            c.drawString(50, y - 15, "El Panze - Sistema POS")

            c.save()
            messagebox.showinfo("PDF Generado", f"Estadísticas guardadas en:\n{pdf_name}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF: {e}")

    def manage_products(self):
        """Abre el CRUD completo para crear, consultar, editar y eliminar productos."""
        if hasattr(self, 'manage_window') and self.manage_window.winfo_exists():
            self.manage_window.lift()
            self.manage_window.focus_force()
            return

        self.manage_window = tk.Toplevel(self.root)
        self.manage_window.title("Gestionar Productos")
        self.manage_window.geometry("900x610")
        self.manage_window.minsize(760, 520)
        self.manage_window.transient(self.root)
        self.admin_editing_product_id = None
        self.prod_image_path = None

        add_frame = ttk.LabelFrame(self.manage_window, text="Datos del producto", padding="12")
        add_frame.pack(padx=12, pady=(12, 6), fill=tk.X)
        add_frame.grid_columnconfigure(1, weight=1)
        add_frame.grid_columnconfigure(3, weight=1)

        ttk.Label(add_frame, text="Nombre:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.prod_name_entry = ttk.Entry(add_frame)
        self.prod_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(add_frame, text="Precio:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.prod_price_entry = ttk.Entry(add_frame)
        self.prod_price_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(add_frame, text="Categoría:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.prod_category_entry = ttk.Entry(add_frame)
        self.prod_category_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.prod_category_entry.insert(0, "General")

        ttk.Label(add_frame, text="Stock:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.prod_stock_entry = ttk.Entry(add_frame)
        self.prod_stock_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        self.prod_stock_entry.insert(0, "0")

        ttk.Label(add_frame, text="Imagen (opcional):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        RoundedButton(add_frame, "Seleccionar imagen", self.select_product_image, width=150).grid(
            row=2, column=1, padx=5, pady=5, sticky="w"
        )
        self.prod_image_preview = ttk.Label(add_frame)
        self.prod_image_preview.grid(row=2, column=2, padx=5, pady=5, sticky="w")

        form_actions = ttk.Frame(add_frame)
        form_actions.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        RoundedButton(form_actions, "Nuevo / Limpiar", self._clear_product_admin).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4)
        )
        RoundedButton(form_actions, "Crear producto", self._add_product_admin).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=4
        )
        RoundedButton(form_actions, "Guardar cambios", self._update_product_admin).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0)
        )

        products_list_frame = ttk.LabelFrame(
            self.manage_window,
            text="Productos — selecciona una fila para editar",
            padding="10"
        )
        products_list_frame.pack(padx=12, pady=6, fill=tk.BOTH, expand=True)
        tree_container = ttk.Frame(products_list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.products_tree = ttk.Treeview(
            tree_container,
            columns=("ID", "Nombre", "Precio", "Categoría", "Stock"),
            show="headings",
            selectmode="browse"
        )
        self.products_tree.heading("ID", text="ID")
        self.products_tree.heading("Nombre", text="Nombre")
        self.products_tree.heading("Precio", text="Precio")
        self.products_tree.heading("Categoría", text="Categoría")
        self.products_tree.heading("Stock", text="Stock")
        self.products_tree.column("ID", width=55, minwidth=45, anchor=tk.CENTER, stretch=False)
        self.products_tree.column("Nombre", width=260, minwidth=150)
        self.products_tree.column("Precio", width=110, minwidth=85, anchor=tk.E)
        self.products_tree.column("Categoría", width=170, minwidth=100)
        self.products_tree.column("Stock", width=80, minwidth=60, anchor=tk.CENTER)
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=tree_scroll.set)
        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.products_tree.bind("<<TreeviewSelect>>", self._select_product_admin)

        list_actions = ttk.Frame(products_list_frame)
        list_actions.pack(fill=tk.X, pady=(8, 0))
        RoundedButton(list_actions, "Actualizar lista", self._load_products_admin).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4)
        )
        RoundedButton(list_actions, "Eliminar seleccionado", self._delete_product_admin).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=4
        )
        RoundedButton(list_actions, "Cerrar", self.manage_window.destroy).pack(
            side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0)
        )

        self._load_products_admin()
        self.prod_name_entry.focus_set()

    def _parse_product_admin_form(self):
        name = self.prod_name_entry.get().strip()
        category = self.prod_category_entry.get().strip() or "General"
        price_text = self.prod_price_entry.get().strip().replace("$", "").replace(" ", "")
        stock_text = self.prod_stock_entry.get().strip()

        if not name or not price_text:
            messagebox.showwarning("Datos incompletos", "Nombre y precio son obligatorios.")
            return None

        # Admite formatos colombianos como 12.000 y 12.000,50.
        if "." in price_text and "," in price_text:
            if price_text.rfind(",") > price_text.rfind("."):
                price_text = price_text.replace(".", "").replace(",", ".")
            else:
                price_text = price_text.replace(",", "")
        elif "," in price_text:
            decimals = len(price_text.rsplit(",", 1)[1])
            price_text = price_text.replace(",", "" if decimals == 3 else ".")
        elif "." in price_text and len(price_text.rsplit(".", 1)[1]) == 3:
            price_text = price_text.replace(".", "")

        try:
            price = float(price_text)
            stock = int(stock_text or "0")
        except ValueError:
            messagebox.showwarning("Datos inválidos", "Precio y stock deben ser números válidos.")
            return None
        return name, price, category, stock

    def _save_product_admin_image(self, product_id):
        image_path = getattr(self, 'prod_image_path', None)
        if not image_path:
            return True
        try:
            assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            img = Image.open(image_path).convert('RGBA')
            img.thumbnail((300, 225), Image.LANCZOS)
            img.save(os.path.join(assets_dir, f"{product_id}.png"), format='PNG')
            if hasattr(self, 'product_images'):
                self.product_images.pop(product_id, None)
            return True
        except Exception as e:
            messagebox.showwarning("Imagen", f"El producto se guardó, pero la imagen falló: {e}")
            return False

    def _add_product_admin(self):
        values = self._parse_product_admin_form()
        if values is None:
            return
        name, price, category, stock = values
        try:
            product_id = db_manager.add_product(name, price, category, stock)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo añadir el producto: {e}")
            return
        self._save_product_admin_image(product_id)
        messagebox.showinfo("Éxito", "Producto añadido correctamente.")
        self._load_products_admin()
        self._clear_product_admin()

    def _update_product_admin(self):
        if self.admin_editing_product_id is None:
            messagebox.showwarning("Selecciona un producto", "Selecciona una fila antes de guardar cambios.")
            return
        values = self._parse_product_admin_form()
        if values is None:
            return
        name, price, category, stock = values
        product_id = self.admin_editing_product_id
        try:
            updated = db_manager.update_product(product_id, name, price, category, stock)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar el producto: {e}")
            return
        if not updated:
            messagebox.showwarning("No encontrado", "El producto ya no existe.")
            self._load_products_admin()
            self._clear_product_admin()
            return
        self._save_product_admin_image(product_id)
        messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
        self._load_products_admin(select_id=product_id)

    def _clear_product_admin(self):
        self.admin_editing_product_id = None
        for entry in (
            self.prod_name_entry,
            self.prod_price_entry,
            self.prod_category_entry,
            self.prod_stock_entry,
        ):
            entry.delete(0, tk.END)
        self.prod_category_entry.insert(0, "General")
        self.prod_stock_entry.insert(0, "0")
        self.prod_image_path = None
        self.prod_image_preview.config(image='')
        if hasattr(self, 'products_tree'):
            self.products_tree.selection_remove(self.products_tree.selection())
        self.prod_name_entry.focus_set()

    def _select_product_admin(self, _event=None):
        selection = self.products_tree.selection()
        if not selection:
            return
        values = self.products_tree.item(selection[0], 'values')
        if not values:
            return
        product_id, name, price, category, stock = values
        self.admin_editing_product_id = int(product_id)
        entries = (
            (self.prod_name_entry, name),
            (self.prod_price_entry, price),
            (self.prod_category_entry, category or "General"),
            (self.prod_stock_entry, stock),
        )
        for entry, value in entries:
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
        self.prod_image_path = None
        self.prod_image_preview.config(image='')


    def _load_products_admin(self, select_id=None):
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        products = db_manager.get_all_products()
        for product in products:
            product_id, name, price, category, stock = product
            price_display = f"${price:,.0f}"
            iid = self.products_tree.insert(
                "", tk.END, iid=str(product_id),
                values=(product_id, name, price_display, category or "General", stock)
            )
            if select_id is not None and int(product_id) == int(select_id):
                self.products_tree.selection_set(iid)
                self.products_tree.focus(iid)
                self.products_tree.see(iid)
        self.load_products()


    def select_product_image(self):
        """Abre un diálogo para seleccionar una imagen y muestra un preview pequeño."""
        from tkinter import filedialog
        try:
            path = filedialog.askopenfilename( # <--- EJECUTA RUTA (SELECCIONAR ARCHIVO)
                title="Seleccionar imagen del producto",
                filetypes=[
                    ("Imágenes PNG", "*.png"),
                    ("Imágenes JPEG", "*.jpg;*.jpeg"),
                    ("GIF", "*.gif"),
                    ("BMP", "*.bmp"),
                    ("Todos los archivos", "*.*")
                ]
            )
        except Exception:
            path = None

        if not path:
            return

        self.prod_image_path = path
        try:
            img = Image.open(path) # <--- EJECUTA RUTA (ABRIR IMAGEN)
            img = img.convert('RGBA')
            img.thumbnail((96, 72), Image.LANCZOS)
            self.prod_image_preview_photo = ImageTk.PhotoImage(img)
            self.prod_image_preview.config(image=self.prod_image_preview_photo)
        except Exception as e:
            messagebox.showwarning("Imagen", f"No se pudo cargar la imagen: {e}")

    def _delete_product_admin(self):
        selected_item = self.products_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selecciona un producto", "Selecciona el producto que deseas eliminar.")
            return

        values = self.products_tree.item(selected_item[0], 'values')
        product_id = int(values[0])
        product_name = values[1]
        if product_id in self.cart:
            messagebox.showwarning(
                "Producto en el carrito",
                "Retira este producto del carrito actual antes de eliminarlo."
            )
            return
        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar definitivamente '{product_name}'?\n\nEsta acción no se puede deshacer."
        ):
            return
        try:
            deleted = db_manager.delete_product(product_id)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el producto: {e}")
            return
        if deleted:
            if hasattr(self, 'product_images'):
                self.product_images.pop(product_id, None)
            messagebox.showinfo("Éxito", "Producto eliminado correctamente.")
        else:
            messagebox.showwarning("No encontrado", "El producto ya no existe.")
        self._load_products_admin()
        self._clear_product_admin()

    def crear_factura_empresa(self):
        import tkinter.filedialog
        factura_path = tkinter.filedialog.askopenfilename(initialdir="facturas", title="Seleccionar factura", filetypes=(('CSV Files', '*.csv'), ('Todos los archivos', '*.*'))) # <--- EJECUTA RUTA (SELECCIONAR FACTURA)
        if not factura_path:
            return
        # Leer datos de la factura seleccionada
        import csv
        datos_factura = {}
        productos = []
        try:
            with open(factura_path, newline='', encoding='utf-8') as f: # <--- EJECUTA RUTA (LEER ARCHIVO)
                reader = csv.DictReader(f)
                for row in reader:
                    productos.append(row)
            if productos:
                datos_factura = productos[0]
        except Exception as e:
            tk.messagebox.showerror("Error", f"No se pudo leer la factura: {e}")
            return

        # Crear ventana de edición
        win = tk.Toplevel(self.root)
        win.title("Crear Factura Empresa")
        win.geometry("800x600")
        win.configure(bg=self.PALETTE_BG1)

        # Campos principales (editable)
        campos = [
            ("Fecha de venta", datos_factura.get("fecha", "")),
            ("Dirección", datos_factura.get("direccion", "")),
            ("Cliente", datos_factura.get("cliente", "")),
            ("NIT", datos_factura.get("nit", "")),
            ("num_factura", datos_factura.get("num_factura", "")),
        ]
        self.factura_vars = {}
        for i, (label, valor) in enumerate(campos):
            tk.Label(win, text=label, bg=self.PALETTE_BG1, font=("Arial", 12, "bold")).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            var = tk.StringVar(value=valor)
            tk.Entry(win, textvariable=var, font=("Arial", 12), width=40).grid(row=i, column=1, padx=10, pady=5)
            self.factura_vars[label] = var

        # Tabla de productos (editable)
        frame_tabla = tk.LabelFrame(win, text="Productos", bg=self.PALETTE_BG1, font=("Arial", 12, "bold"))
        frame_tabla.grid(row=len(campos), column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        cols = ["Cantidad", "Nombre", "Valor unitario", "Valor total"]
        for j, col in enumerate(cols):
            tk.Label(frame_tabla, text=col, bg=self.PALETTE_BG1, font=("Arial", 11, "bold")).grid(row=0, column=j, padx=5, pady=5)
        self.product_entries = []
        for i, prod in enumerate(productos):
            row_entries = []
            for j, campo in zip(range(4), ["cantidad", "nombre", "valor_unitario", "valor_total"]):
                var = tk.StringVar(value=prod.get(campo, ""))
                e = tk.Entry(frame_tabla, textvariable=var, font=("Arial", 11), width=15)
                e.grid(row=i+1, column=j, padx=5, pady=2)
                row_entries.append(var)
            self.product_entries.append(row_entries)

        # Botón para guardar/descargar PDF (diseño similar al PDF de ejemplo)
        def guardar_pdf():
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            import tempfile
            datos = {k: v.get() for k, v in self.factura_vars.items()}
            productos_pdf = []
            for row in self.product_entries:
                productos_pdf.append({
                    "cantidad": row[0].get(),
                    "nombre": row[1].get(),
                    "valor_unitario": row[2].get(),
                    "valor_total": row[3].get(),
                })
            # Crear PDF temporal
            pdf_path = tempfile.mktemp(suffix="_factura_empresa.pdf") # <--- RUTA TEMPORAL PDF
            c = canvas.Canvas(pdf_path, pagesize=letter) # <--- EJECUTA RUTA (CREAR PDF)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 750, "FACTURA EMPRESA")
            c.setFont("Helvetica", 12)
            c.drawString(50, 730, f"Fecha de venta: {datos.get('Fecha de venta', '')}")
            c.drawString(50, 710, f"Dirección: {datos.get('Dirección', '')}")
            c.drawString(50, 690, f"Cliente: {datos.get('Cliente', '')}")
            c.drawString(50, 670, f"NIT: {datos.get('NIT', '')}")
            c.drawString(50, 650, f"Número de factura: {datos.get('num_factura', '')}")
            # Tabla productos
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, 630, "Productos:")
            c.setFont("Helvetica", 11)
            y = 610
            c.drawString(50, y, "Cantidad")
            c.drawString(120, y, "Nombre")
            c.drawString(350, y, "Valor unitario")
            c.drawString(470, y, "Valor total")
            y -= 20
            for prod in productos_pdf:
                c.drawString(50, y, str(prod["cantidad"]))
                c.drawString(120, y, prod["nombre"])
                c.drawString(350, y, prod["valor_unitario"])
                c.drawString(470, y, prod["valor_total"])
                y -= 20
                if y < 100:
                    c.showPage()
                    y = 750
            c.save() # <--- EJECUTA RUTA (GUARDAR PDF)
            tk.messagebox.showinfo("PDF generado", f"Factura PDF guardada en: {pdf_path}")

        tk.Button(win, text="Guardar como PDF", command=guardar_pdf, font=("Arial", 12, "bold"), bg=self.PALETTE_ACCENT, fg="white").grid(row=len(campos)+2, column=0, columnspan=2, pady=20)

    def export_facturas_completas_excel(self):
        import csv
        from tkinter import filedialog
        
        columns, rows = db_manager.get_all_facturas_completas()
        
        if not rows:
            messagebox.showinfo("Información", "No hay datos en la tabla 'facturas_completas'.")
            return

        filename = filedialog.asksaveasfilename(
            title="Exportar Facturas Completas a Excel",
            defaultextension=".csv",
            filetypes=[("Archivo CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        
        if filename:
            try:
                # Se usa utf-8-sig para compatibilidad con Excel y delimitador ';'
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(columns)
                    writer.writerows(rows)
                messagebox.showinfo("Éxito", f"Se exportó correctamente a:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def modo_pro(self):
        """Muestra el estado y exige contraseña para cambiar el modo pro."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Modo Pro")
        dialog.geometry("420x290")
        dialog.transient(self.root)
        dialog.grab_set()

        # Encabezado
        ttk.Label(dialog, text="Control de Modo Pro", font=('Arial', 14, 'bold')).pack(pady=20)
        
        # Estado actual
        estado_texto = "Activado" if self.modo_pro_activo else "Desactivado"
        estado_label = ttk.Label(dialog, text=f"Estado actual: {estado_texto}", font=('Arial', 11))
        estado_label.pack(pady=10)

        # Descripción
        ttk.Label(dialog, text="El modo pro habilita los botones de editar y eliminar\nen la ventana de facturas.", font=('Arial', 9), justify=tk.CENTER).pack(pady=10)

        # La contraseña se valida al cambiar el estado.
        password_frame = ttk.Frame(dialog)
        password_frame.pack(fill=tk.X, padx=25, pady=(5, 10))
        ttk.Label(password_frame, text="Contraseña:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 8))
        password_entry = ttk.Entry(password_frame, show='*', font=('Arial', 11))
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        password_entry.focus_set()

        # Frame de botones
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=15)

        def password_correcta():
            if password_entry.get() == "2684":
                return True
            messagebox.showerror(
                "Contraseña incorrecta",
                "La contraseña de Modo Pro no es correcta.",
                parent=dialog
            )
            password_entry.selection_range(0, tk.END)
            password_entry.focus_set()
            return False

        def activar_modo_pro():
            if not password_correcta():
                return
            self.modo_pro_activo = True
            estado_label.config(text="Estado actual: Activado")
            password_entry.delete(0, tk.END)
            messagebox.showinfo("Modo Pro", "✓ Modo Pro activado correctamente.\nLos botones de editar y eliminar están habilitados.", parent=dialog)

        def desactivar_modo_pro():
            if not password_correcta():
                return
            self.modo_pro_activo = False
            estado_label.config(text="Estado actual: Desactivado")
            password_entry.delete(0, tk.END)
            messagebox.showinfo("Modo Pro", "✗ Modo Pro desactivado correctamente.\nLos botones de editar y eliminar están deshabilitados.", parent=dialog)

        RoundedButton(btn_frame, "✓ Activar", activar_modo_pro).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        RoundedButton(btn_frame, "✗ Desactivar", desactivar_modo_pro).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        RoundedButton(btn_frame, "Cerrar", dialog.destroy).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        password_entry.bind('<Return>', lambda _event: activar_modo_pro())

    def load_categories(self):
        # Función placeholder: Reemplazar con implementación real
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
            def on_payment_method(method_or_tuple, amount_paid, change):
                items = []
                for k, item in self.cart.items():
                    items.append({
                        "id": item["id"],
                        "nombre": item["nombre"],
                        "cantidad": item["cantidad"],
                        "precio": item["precio"]
                    })
                
                # Detectar si es pago dividido (tupla) o pago simple (string)
                if isinstance(method_or_tuple, tuple):
                    # Pago dividido: (method1, method2, amount1, amount2)
                    method1, method2, amount1, amount2 = method_or_tuple
                    payment_info = f"{method1} (${amount1:,.0f}) + {method2} (${amount2:,.0f})".replace(",", ".")
                    method_display = method1  # Para register_sale usaremos el primer método
                    is_split = True
                    split_data = (method1, method2, amount1, amount2)
                else:
                    # Pago simple
                    method_display = method_or_tuple
                    payment_info = f"{method_display} (${total_with_shipping:,.0f})".replace(",", ".")
                    is_split = False
                    split_data = None
                
                # Modal 3: Capturar observaciones de cada producto
                def on_observations_saved(observations):
                    try:
                        items_agotados = [
                            {'nombre': it['nombre'], 'cantidad': it['cantidad'], 'precio': it['precio']}
                            for it in items
                            if self.cart.get(it['id'], {}).get('agotado')
                        ]

                        num_factura = db_manager.record_sale(total_with_shipping, items, cliente=client, direccion=address, metodo_pago=method_display, observaciones=observations, split_payment=split_data)

                        try:
                            db_manager.registrar_venta_agotado(num_factura, items_agotados)
                        except Exception as e:
                            print(f"Error registrando ventas de agotados: {e}")

                        # Recargar productos en UI para reflejar el stock nuevo
                        try:
                            self.load_products()
                        except Exception as e:
                            print(f"Error recargando productos: {e}")
                        self.actualizar_contador_agotados()

                        # Generar factura con detalles de pago, dirección y observaciones
                        try:
                            if is_split:
                                method1, method2, amount1, amount2 = split_data
                                self.generate_invoice_pdf(num_factura, items, total_with_shipping, cliente=client, dirrecion=address, 
                                                        metodo_pago=method_display, cambio=change, observaciones=observations,
                                                        split_payment=(method1, method2, amount1, amount2))
                            else:
                                self.generate_invoice_pdf(num_factura, items, total_with_shipping, cliente=client, dirrecion=address, 
                                                        metodo_pago=method_display, cambio=change, observaciones=observations)
                        except Exception as e:
                            messagebox.showerror("Error en PDF/Impresión", f"La venta se registró pero hubo error al generar/imprimir factura: {e}")

                        messagebox.showinfo("Venta Registrada", f"Venta #{num_factura} completada con éxito.\nDirección: {address}\nMétodo: {payment_info}")
                        self.clear_cart()
                        
                        # Abrir ventana de facturas para mostrar la nueva factura
                        #try:
                        #    FacturasWindow(self.root, app=self)
                        #except Exception as e:
                        #    print(f"Error abriendo FacturasWindow: {e}")
                            
                    except Exception as e:
                        messagebox.showerror("Error en la venta", f"No se pudo completar la venta: {e}")
                        print(f"Error completo en on_observations_saved: {e}")
                        import traceback
                        traceback.print_exc()
                
                ObservationsModal(self.root, items, on_observations_saved, app=self)
            
            PaymentMethodModal( self.root, total_with_shipping, on_payment_method,  app=self, client=client, address=address)
        
        AddressModal(self.root, on_address_selected)
       
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # ------------------- FACTURA PDF -------------------

    def generate_invoice_pdf(self, num_factura, items, total, cliente="Cliente General", dirrecion="Sin Dirección",
                         metodo_pago="Efectivo", cambio=0, observaciones=None, ruta_salida="factura.pdf",Image_path="assets/logo_impresora.jpg", split_payment=None):
    
        # Crear carpeta de facturas si no existe
        import os
        if not os.path.exists("facturas"): # <--- VERIFICA RUTA CARPETA FACTURAS
            os.makedirs("facturas") # <--- CREA RUTA CARPETA FACTURAS
        
        # Datos generados automáticamente
        fecha = datetime.now().strftime("%d/%m/%Y")
        numero_pedido = num_factura
        ruta_salida=f"facturas/factura{num_factura}.pdf" # <--- RUTA ARCHIVO PDF FACTURA
        # 1 cm = 28,34645672 puntos
        c = canvas.Canvas(ruta_salida, pagesize=(136, 397))  # Tamaño personalizado en puntos (1 punto = 1/72 pulgadas) # <--- EJECUTA RUTA (CREAR PDF)
        width=136 #tamaño impresión horizontal 4,8 cm
        height=397 #tamaño impresión vertical 14 cm
    
        y = height - 10

        # ENCABEZADO
       
        c.drawImage(Image_path, 0, y - 98, width=120, height=93, preserveAspectRatio=None, mask='auto') # <--- EJECUTA RUTA (DIBUJAR IMAGEN EN PDF)
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
        # Mostrar método o métodos divididos
        if split_payment:
            method1, method2, amount1, amount2 = split_payment
            metodo_texto = f"{method1}: ${amount1:,.0f} + {method2}: ${amount2:,.0f}".replace(",", ".")
        else:
            metodo_texto = f"{metodo_pago}"
        c.drawString(67, y, metodo_texto[:50])  # Limitar a 50 caracteres
        y -= 10
        if split_payment and len(metodo_texto) > 50:
            c.setFont("Helvetica", 7)
            c.drawString(67, y, metodo_texto[50:])
            y -= 10
        y -= 20

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
        c.save() # <--- EJECUTA RUTA (GUARDAR PDF)
        print(f"Factura generada: {ruta_salida}")
        
        # Guardar datos de la última factura para reimprimir si es necesario
        self.ultima_factura = {
            'num_factura': num_factura,
            'ruta': ruta_salida,
            'items': items,
            'total': total,
            'cliente': cliente,
            'dirrecion': dirrecion,
            'metodo_pago': metodo_pago,
            'cambio': cambio
        }
        
        # Imprimir factura principal
       # try:
        #    self._imprimir_factura(ruta_salida)
        #except Exception as e:
        #    messagebox.showwarning("Impresión", f"No se pudo imprimir la factura: {e}")

        # Preguntar si desea una copia adicional
        if messagebox.askyesno("sin factura", "seleciona no,'Si deseas imprimir la factura"):
             print("sin factura")
        else:    
            try:
                self._imprimir_factura(ruta_salida)
            except Exception as e:
                messagebox.showwarning("Impresión", f"No se pudo imprimir la copia: {e}")

    
#ttk.Radiobutton(copias_frame, text="1 copia", variable=self.copias_var, value=1).pack(side=tk.LEFT, padx=10)
        #ttk.Radiobutton(copias_frame, text="2 copias", variable=self.copias_var, value=2).pack(side=tk.LEFT, padx=10)
        
# #








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
        
        # Cargar direcciones desde la base de datos (si está vacía, se siembran las por defecto)
        try:
            db_manager.ensure_default_addresses()
            self.direcciones = db_manager.get_all_addresses()
        except Exception:
            # Fallback mínimo si hay problemas con la DB
            self.direcciones = ["Sin conexión a DB"]
        
        try:
            self.free_addresses = db_manager.get_free_addresses()
        except Exception:
            self.free_addresses = []
        
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
        #ttk.Button(button_frame, text="X Cancelar", command=self.cancel, width=20).pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
    
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
                    self.info_label.config(text="🚚 Costo de envío: $3.000", foreground="red")
                    self.shipping_cost = 0
            else:
                # Dirección personalizada (no en la lista)
                self.info_label.config(text="🚚 Costo de envío: $3.000", foreground="red")
                self.shipping_cost = 0
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
    def __init__(self, parent, total, callback, app, client, address):
        super().__init__(parent)
        self.app = app
        self.client = client
        self.address = address
        self.callback = callback
        self.total = total
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
        ttk.Button(button_frame, text="🔀 PAGO DIVIDIDO", command=self.select_split_payment).pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="💾 Guardar pedido pendiente", command=lambda: self.app.save_pending_order(
                            client=self.client if hasattr(self, 'client') and self.client else getattr(self.app, 'client', ''),
                            address=self.address if hasattr(self, 'address') and self.address else getattr(self.app, 'address', ''),
                            payment_method=getattr(self, 'selected_method', None)  # Asegúrate de pasar el método de pago si lo tienes
                            )
                  ).pack(fill=tk.X, pady=5)

        # Botón Volver
        ttk.Button(button_frame, text="⬅ Volver", command=self.on_back).pack(fill=tk.X, pady=5)

    def on_back(self):
        self.destroy()
        # Volver al modal anterior (dirección)
        # Se asume que process_sale vuelve a llamar AddressModal
        if hasattr(self.app, 'process_sale'):
            self.app.process_sale()


    def select_payment(self, method):
        if method == 'EFECTIVO':
            self.destroy()
            CashPaymentModal(self.master, self.total, self.callback, app=self.app)
        else:
            self.callback(method, self.total, 0)
            self.destroy()
    
    def select_split_payment(self):
        """Abre modal para pago dividido entre dos métodos."""
        self.destroy()
        SplitPaymentModal(self.master, self.total, self.callback)

class CashPaymentModal(tk.Toplevel):
    """Modal para pago en efectivo."""
    def __init__(self, parent, total, callback, app=None):
        super().__init__(parent)
        self.title("Pago en Efectivo")
        self.geometry("450x600")
        self.resizable(False, False)
        self.callback = callback
        self.total = total
        self.app = app
        
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
        #ttk.Button(button_frame, text="X Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        # Botón Volver
        ttk.Button(button_frame, text="⬅ Volver", command=self.on_back).pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    def on_back(self):
        self.destroy()
        # Volver al modal anterior (método de pago)
        if self.app and hasattr(self.app, 'process_sale'):
            self.app.process_sale()
    
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

class SplitPaymentModal(tk.Toplevel):
    """Modal para pago dividido entre dos métodos de pago."""
    def __init__(self, parent, total, callback):
        super().__init__(parent)
        self.title("Pago Dividido")
        self.geometry("500x500")
        self.resizable(False, False)
        self.callback = callback
        self.total = total
        self.method1 = None
        self.amount1 = 0
        self.method2 = None
        self.amount2 = 0
        self.current_step = 1  # 1 o 2
        
        self.create_widgets()
        self.transient(parent)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        ttk.Label(main_frame, text="Pago Dividido", font=('Arial', 16, 'bold')).pack(pady=10)
        ttk.Label(main_frame, text=f"Total a pagar: ${self.total:,.0f}".replace(",", "."), 
                  font=('Arial', 12)).pack(pady=10)
        
        # Frame para mostrar progreso
        self.progress_label = ttk.Label(main_frame, text="Paso 1 de 2: Selecciona primer método de pago", 
                                        font=('Arial', 10, 'italic'))
        self.progress_label.pack(pady=10)
        
        # Frame para los botones de método de pago
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.pack(fill=tk.BOTH, expand=True, pady=15)
        
        self.show_method_selection(1)
    
    def show_method_selection(self, step):
        """Muestra la selección de método para el paso indicado."""
        # Limpiar frame anterior
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        
        self.current_step = step
        self.progress_label.config(text=f"Paso {step} de 2: Selecciona el método de pago #{step}")
        
        ttk.Button(self.button_frame, text="💵 EFECTIVO", 
                   command=lambda: self.select_method(step, 'EFECTIVO')).pack(fill=tk.X, pady=5)
        ttk.Button(self.button_frame, text="💳 NEQUI", 
                   command=lambda: self.select_method(step, 'NEQUI')).pack(fill=tk.X, pady=5)
        ttk.Button(self.button_frame, text="💳 DAVIPLATA", 
                   command=lambda: self.select_method(step, 'DAVIPLATA')).pack(fill=tk.X, pady=5)
    
    def select_method(self, step, method):
        """Selecciona el método y pide el monto."""
        if step == 1:
            self.method1 = method
            if method == 'EFECTIVO':
                self.show_amount_input(1)
            else:
                # Para métodos digitales, permitir ingresar monto
                self.show_amount_input(1)
        elif step == 2:
            self.method2 = method
            if method == 'EFECTIVO':
                self.show_amount_input(2)
            else:
                self.show_amount_input(2)
    
    def show_amount_input(self, step):
        """Muestra input para capturar monto del pago."""
        # Limpiar frame
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        
        remaining = self.total - (self.amount1 if step == 2 else 0)
        
        ttk.Label(self.button_frame, text=f"¿Cuánto pagas con {self.method1 if step == 1 else self.method2}?", 
                  font=('Arial', 12, 'bold')).pack(pady=10)
        ttk.Label(self.button_frame, text=f"Monto pendiente: ${remaining:,.0f}".replace(",", "."), 
                  font=('Arial', 10)).pack(pady=5)
        
        amount_entry = ttk.Entry(self.button_frame, font=('Arial', 12), width=25)
        amount_entry.pack(pady=10, ipady=5)
        amount_entry.focus()
        
        def confirm_amount():
            try:
                amount = float(amount_entry.get().replace(".", ""))
                
                if step == 1:
                    if amount <= 0 or amount > self.total:
                        messagebox.showwarning("Error", f"El monto debe estar entre 0 y ${self.total:,.0f}")
                        return
                    self.amount1 = amount
                    remaining_for_step2 = self.total - self.amount1
                    
                    # Pasar al siguiente paso
                    self.show_method_selection(2)
                elif step == 2:
                    remaining = self.total - self.amount1
                    if amount <= 0 or amount > remaining + 1:  # +1 para permitir pequeños redondes
                        messagebox.showwarning("Error", f"El monto debe estar entre 0 y ${remaining:,.0f}")
                        return
                    self.amount2 = amount
                    
                    # Completar el pago dividido
                    self.complete_split_payment()
            except ValueError:
                messagebox.showwarning("Error", "Por favor ingresa un monto válido.")
        
        ttk.Button(self.button_frame, text="Confirmar", command=confirm_amount).pack(pady=10, ipadx=20)
    
    def complete_split_payment(self):
        """Completa el pago dividido y devuelve los datos al callback."""
        # Pasar datos como tupla: (method1, method2, amount1, amount2)
        self.callback((self.method1, self.method2, self.amount1, self.amount2), None, None)
        self.destroy()

class ObservationsModal(tk.Toplevel):
    """Modal para capturar observaciones de cada producto en el carrito."""
    def __init__(self, parent, items, callback, app=None):
        super().__init__(parent)
        self.title("Observaciones de Productos")
        self.geometry("600x400")
        self.resizable(True, True)
        self.callback = callback
        self.items = items
        self.app = app
        self.observations_entries = {}
        
        self.create_widgets()
        self.bind("<Return>", lambda e: self.save_observations() if e.widget == self else None)
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
            obs_text = tk.Text(item_frame, height=3, width=50, font=('Arial', 9), bg=PALETTE_BG2, fg=PALETTE_DARK)
            obs_text.pack(fill=tk.X)
            
            self.observations_entries[product_name] = obs_text
        
        # Empacar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 15))
        
        # Frame inferior con botones
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=15, pady=15)
        
        ttk.Button(button_frame, text="✓ Guardar y Continuar", command=self.save_observations).pack( padx=5, fill=tk.X, expand=True)
       # ttk.Button(button_frame, text="X Cancelar", command=self.destroy).pack( padx=5, fill=tk.X, expand=True)
        # Botón Volver
        #
        ttk.Button(button_frame, text="⬅ Volver", command=self.on_back).pack( fill=tk.X, pady=5)

    def on_back(self):
        self.destroy()
        # Volver al modal anterior (método de pago)
        # Se asume que process_sale vuelve a llamar PaymentMethodModal
        if self.app and hasattr(self.app, 'process_sale'):
            self.app.process_sale()
    
    def save_observations(self):
        """Guarda todas las observaciones y cierra el modal."""
        observations = {}
        for product_name, text_widget in self.observations_entries.items():
            observations[product_name] = text_widget.get("1.0", tk.END).strip()
        self.destroy()  # Cerrar el modal inmediatamente al oprimir el botón
        self.callback(observations)







class LoadCartModal(tk.Toplevel):
    """Modal para seleccionar un carrito guardado para cargar."""
    def __init__(self, parent, saved_carts, callback, app=None):
        super().__init__(parent)
        self.title("Cargar Carrito")
        self.geometry("400x350")
        self.resizable(True, False)
        self.saved_carts = saved_carts
        self.callback = callback
        self.app = app
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
        
        self.listbox = tk.Listbox(frame, font=('Arial', 11), yscrollcommand=scrollbar.set, bg=PALETTE_BG2, fg=PALETTE_DARK, highlightbackground=PALETTE_BG1)
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
       #ttk.Button(btn_frame, text="Eliminar", command=self.delete_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(btn_frame, text="Realizar Venta", command=self.app.process_sale if self.app else self._no_app_error, style='TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
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

    def _no_app_error(self):
        messagebox.showerror("Error", "No se puede procesar la venta desde aquí porque no se pasó la instancia de la aplicación.")
    
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


class PendingOrdersModal(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Pedidos Pendientes")
        self.geometry("520x400")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="📦 Pedidos Pendientes", font=('Arial', 14, 'bold')).pack(pady=10)

        self.listbox = tk.Listbox(self, font=('Arial', 11))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        self.orders = []
        self.load_orders()

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=15, pady=10)

        ttk.Button(btns, text="🔄 Cargar", command=self.load_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(btns, text="🗑️ Eliminar", command=self.delete_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(btns, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT)

    def load_orders(self):
        self.listbox.delete(0, tk.END)
        self.orders.clear()

        # Usar db_manager en lugar de self.app.cursor
    
        rows = db_manager.get_all_pending_orders()
        for row in rows:
            self.orders.append(row)
            self.listbox.insert(tk.END, f"{row[1]} - {row[2]}")

    def load_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return

        # Obtener el nombre del carrito seleccionado
        cart_name = list(self.saved_carts.keys())[sel[0]]
        cart_data = self.saved_carts[cart_name]

        # Actualizar variables temporales en la app
        self.app.current_pending_order = {
            "name": cart_data.get("name", cart_name),
            "items": cart_data.get("items", {}),
            "client": cart_data.get("client", ""),
            "address": cart_data.get("address", "")
        }

        # Actualizar el carrito y datos en la app
        self.app.cart.clear()
        for k, v in cart_data.get("items", {}).items():
            self.app.cart[k] = v
        self.app.client = cart_data.get("client", "")
        self.app.address = cart_data.get("address", "")

        self.app.update_cart_display()

        total = self.app.calculate_total() if hasattr(self.app, 'calculate_total') else sum(item['precio'] * item['cantidad'] for item in self.app.cart.values())

        # Abrir el modal de método de pago
        PaymentMethodModal(
            self.app.root,
            total,
            callback=lambda m, *args, **kwargs: None,
            app=self.app,
            client=self.app.client,
            address=self.app.address
        )

        self.destroy()

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return

        order_id = self.orders[sel[0]][0]

        if messagebox.askyesno("Eliminar", "Eliminar este pedido pendiente?"):
           
            db_manager.delete_pending_order(order_id)
            self.load_orders()

class FacturasWindow(tk.Toplevel):
    """Ventana para visualizar y gestionar todas las facturas."""
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.title("Panel de Facturas")
        self.geometry("1000x600")
        self.resizable(True, True)
        self.app = app  # Referencia a la instancia de POSApp
        
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
            columns=("ID", "Num. Factura", "Fecha/Hora", "Cliente", "Método Pago", "Total", "Dirección", "Observaciones"),
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
        self.facturas_tree.heading("Dirección", text="Dirección")
        self.facturas_tree.heading("Observaciones", text="Observaciones")
        
        # Configurar ancho de columnas
        self.facturas_tree.column("ID", width=40, anchor="center")
        self.facturas_tree.column("Num. Factura", width=100, anchor="center")
        self.facturas_tree.column("Fecha/Hora", width=140, anchor="center")
        self.facturas_tree.column("Cliente", width=120, anchor="w")
        self.facturas_tree.column("Método Pago", width=100, anchor="center")
        self.facturas_tree.column("Total", width=90, anchor="e")
        self.facturas_tree.column("Dirección", width=150, anchor="w")
        self.facturas_tree.column("Observaciones", width=180, anchor="w")
        
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
        try:
            # Limpiar tabla
            for item in self.facturas_tree.get_children():
                self.facturas_tree.delete(item)
            
            # Obtener facturas
            facturas = db_manager.get_all_facturas()
            print(f"Facturas obtenidas: {len(facturas)}")  # Debug
            
            if not facturas:
                self.stats_label.config(text="No hay facturas registradas")
                return
            
            # Insertar en tabla
            total_ventas = 0
            for factura in facturas:
                try:
                    fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, direccion, observaciones = factura
                    
                    # Formatear total
                    try:
                        valor_total = float(valor_total)
                        total_formateado = f"${valor_total:,.0f}".replace(",", ".")
                    except (ValueError, TypeError):
                        total_formateado = "$0"
                        valor_total = 0
                    
                    # Las observaciones y dirección ya vienen concatenadas de la BD
                    observaciones_texto = observaciones if observaciones and observaciones.strip() else "-"
                    direccion_texto = direccion if direccion and direccion.strip() else "-"
                    
                    self.facturas_tree.insert("", tk.END, values=(
                        fact_id,
                        num_factura,
                        fecha_hora,
                        cliente if cliente else "No especificado",
                        metodo_pago if metodo_pago else "No especificado",
                        total_formateado,
                        direccion_texto,
                        observaciones_texto[:100] if observaciones_texto != "-" else "-"
                    ))
                    total_ventas += valor_total
                except ValueError as e:
                    print(f"Error desempaquetando factura: {e} - Factura: {factura}")
                    continue
            
            # Actualizar estadísticas
            total_facturas = len(facturas)
            total_formateado = f"${total_ventas:,.0f}".replace(",", ".")
            self.stats_label.config(
                text=f"Total de facturas: {total_facturas} | Ingresos totales: {total_formateado} COP"
            )
        except Exception as e:
            print(f"Error en load_facturas(): {e}")
            messagebox.showerror("Error", f"Error al cargar facturas: {e}")
    
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
                writer.writerow(['ID', 'Nº Factura', 'Fecha/Hora', 'Cliente', 'Método Pago', 'Total', 'Dirección', 'Observaciones'])
                
                for factura in facturas:
                    fact_id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, direccion, observaciones = factura
                    writer.writerow([
                        fact_id,
                        num_factura,
                        fecha_hora,
                        cliente if cliente else "No especificado",
                        metodo_pago if metodo_pago else "No especificado",
                        f"${valor_total:,.0f}".replace(",", "."),
                        direccion if direccion else "-",
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
            
            # Habilitar botones solo si modo pro está activo
            if self.app and self.app.modo_pro_activo:
                self.edit_btn.config(state='normal')
                self.delete_btn.config(state='normal')
            else:
                self.edit_btn.config(state='disabled')
                self.delete_btn.config(state='disabled')
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
        self.lb = tk.Listbox(master, height=8, font=('Arial', 10), bg=PALETTE_BG2, fg=PALETTE_DARK, selectmode=tk.SINGLE)
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
        
        ttk.Label(info_frame, text=f"Número de Venta: #{self.ultima_factura['num_factura']}", 
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
                    r"C:\Users\Panze\Documents\GitHub\El_Panze\system_pos\SumatraPDF-3.5.2-64.exe", # <--- RUTA EJECUTABLE SUMATRA PDF
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
        self.geometry("1500x900")
        self.resizable(True, True)
        
        self.metodos_pago = metodos_pago
        self.fecha = fecha
        
        self.create_widgets()
        self.transient(parent)

    def _get_direccion(self, factura):
        try:
            if factura is None:
                return None
            if len(factura) >= 11:
                return factura[4]
            return None
        except Exception:
            return None

    def _get_total(self, factura):
        try:
            if factura is None:
                return 0.0
            if len(factura) >= 11:
                return float(factura[10] or 0)
            return float(factura[5] or 0)
        except Exception:
            try:
                return float(str(factura[5]).replace(',',''))
            except Exception:
                return 0.0

    def _unpack_factura(self, factura):
        """Normaliza una fila de factura a la tupla:
        (id, num_factura, fecha_hora, cliente, metodo, valor_total, observaciones)
        Soporta filas de `facturas` (7 cols) y `facturas_completas` (>=11 cols).
        """
        try:
            if factura is None:
                return (None, None, None, None, None, 0.0, None)
            if len(factura) >= 11:
                fact_id = factura[0]
                num_factura = factura[1]
                fecha_hora = factura[2]
                cliente = factura[3]
                metodo = factura[5] if len(factura) > 5 else None
                # total suele estar en la columna 10
                try:
                    valor_total = float(factura[10] or 0)
                except Exception:
                    try:
                        valor_total = float(str(factura[10]).replace(',',''))
                    except Exception:
                        valor_total = 0.0
                observaciones = factura[11] if len(factura) > 11 else None
                return (fact_id, num_factura, fecha_hora, cliente, metodo, valor_total, observaciones)
            # Caso clásico: 7 campos (id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, observaciones)
            if len(factura) == 7:
                try:
                    valor_total = float(factura[5] or 0)
                except Exception:
                    try:
                        valor_total = float(str(factura[5]).replace(',',''))
                    except Exception:
                        valor_total = 0.0
                return (factura[0], factura[1], factura[2], factura[3], factura[4], valor_total, factura[6])
            # Fallback: intentar usar índices conocidos
            fact_id = factura[0]
            num_factura = factura[1] if len(factura) > 1 else None
            fecha_hora = factura[2] if len(factura) > 2 else None
            cliente = factura[3] if len(factura) > 3 else None
            metodo = factura[4] if len(factura) > 4 else None
            valor_total = 0.0
            if len(factura) > 5:
                try:
                    valor_total = float(factura[5] or 0)
                except Exception:
                    pass
            observaciones = factura[-1] if len(factura) > 0 else None
            return (fact_id, num_factura, fecha_hora, cliente, metodo, valor_total, observaciones)
        except Exception:
            return (None, None, None, None, None, 0.0, None)
    
    def create_widgets(self):
        # Frame superior con título y fecha
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=15, pady=10)

        ttk.Label(top_frame, text=f"Estadísticas Detalladas - {self.fecha}", 
                  font=('Arial', 16, 'bold')).pack(side=tk.LEFT)

        # Frame con tabs para cada método de pago
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        

        # Usar métodos de instancia para extraer campos según formato de factura

        # Crear una pestaña para cada método de pago
        for metodo_pago in sorted(self.metodos_pago.keys()):
            datos = self.metodos_pago[metodo_pago]
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=f"{metodo_pago} ({datos['cantidad']})")
            self.crear_encabezado(tab, metodo_pago, datos)

            # Separar facturas en dos listas: pago punto y resto
            facturas_pago_punto = []
            facturas_otros = []
            # Cada entrada en datos['facturas'] puede ser o bien una fila raw o una tupla (fila, amount)
            for entry in datos['facturas']:
                if isinstance(entry, (list, tuple)) and len(entry) >= 2 and isinstance(entry[1], (int, float)):
                    fila_row = entry[0]
                else:
                    fila_row = entry
                direccion = self._get_direccion(fila_row)
                if isinstance(direccion, str) and direccion.strip().lower() == "pago punto":
                    facturas_pago_punto.append(entry)
                else:
                    facturas_otros.append(entry)


            # Crear dos frames dentro de la pestaña: uno para pago punto, otro para el resto
            frame_pago_punto = ttk.LabelFrame(tab, text="Facturas con dirección 'pago punto'", padding="5")
            frame_pago_punto.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            frame_otros = ttk.LabelFrame(tab, text="Facturas con otras direcciones", padding="5")
            frame_otros.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Datos para cada tabla
            
            datos_otros = dict(datos)
            datos_otros['facturas'] = facturas_otros
            datos_otros['cantidad'] = len(facturas_otros)
            total_otros = 0.0
            for entry in facturas_otros:
                if isinstance(entry, (list, tuple)) and len(entry) >= 2 and isinstance(entry[1], (int, float)):
                    total_otros += float(entry[1])
                else:
                    total_otros += float(self._get_total(entry) or 0.0)
            datos_otros['total'] = total_otros

            datos_pago_punto = dict(datos)
            datos_pago_punto['facturas'] = facturas_pago_punto
            datos_pago_punto['cantidad'] = len(facturas_pago_punto)
            total_pago_punto = 0.0
            for entry in facturas_pago_punto:
                if isinstance(entry, (list, tuple)) and len(entry) >= 2 and isinstance(entry[1], (int, float)):
                    total_pago_punto += float(entry[1])
                else:
                    total_pago_punto += float(self._get_total(entry) or 0.0)
            datos_pago_punto['total'] = total_pago_punto


            # Crear tablas
            self.crear_tabla_metodo(frame_otros, metodo_pago, datos_otros)
            self.crear_tabla_metodo(frame_pago_punto, metodo_pago, datos_pago_punto)
            
    def crear_encabezado(self, parent_frame, metodo_pago, datos):
        # frame superior
        summary_frame = ttk.LabelFrame(parent_frame, text="Resumen", padding="10")
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(summary_frame, text=f"Cantidad de ventas: {datos['cantidad']}", font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=20)
        ttk.Label(summary_frame, text=f"Total: ${datos['total']:,.0f}", font=('Arial', 11, 'bold'), foreground='green').pack(side=tk.LEFT, padx=20)
        saldo_pendiente_var = tk.StringVar()
        saldo_pendiente_var.set(f"Saldo Pendiente: ${datos['total']:,.0f}")
        saldo_pendiente_label = ttk.Label(summary_frame, textvariable=saldo_pendiente_var, font=('Arial', 11, 'bold'), foreground='red')
        saldo_pendiente_label.pack(side=tk.LEFT, padx=20)


    def crear_tabla_metodo(self, parent_frame, metodo_pago, datos):
        """Crea una tabla con las facturas de un método de pago específico, cada una con su propio saldo y checks."""
        # Frame superior con resumen
        summary_frame = ttk.LabelFrame(parent_frame, text="Resumen", padding="10")
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(summary_frame, text=f"Cantidad de ventas: {datos['cantidad']}", font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=20)
        ttk.Label(summary_frame, text=f"Total: ${datos['total']:,.0f}", font=('Arial', 11, 'bold'), foreground='green').pack(side=tk.LEFT, padx=20)
        saldo_pendiente_var = tk.StringVar()
        saldo_pendiente_var.set(f"Saldo Pendiente: ${datos['total']:,.0f}")
        saldo_pendiente_label = ttk.Label(summary_frame, textvariable=saldo_pendiente_var, font=('Arial', 11, 'bold'), foreground='red')
        saldo_pendiente_label.pack(side=tk.LEFT, padx=20)

        # Frame con tabla de facturas
        table_frame = ttk.LabelFrame(parent_frame, text=f"Facturas - {metodo_pago}", padding="10")
        table_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # Crear Treeview con columna de check
        columns = ("ID", "Nº Factura", "Hora", "Check", "Cliente", "Total", "Observaciones")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)
        tree.heading("ID", text="ID")
        tree.heading("Nº Factura", text="Nº Factura")
        tree.heading("Hora", text="Hora")
        tree.heading("Check", text="Check")
        tree.heading("Cliente", text="Cliente")
        tree.heading("Total", text="Total")
        tree.heading("Observaciones", text="Observaciones")
        tree.column("ID", width=50)
        tree.column("Nº Factura", width=80)
        tree.column("Hora", width=80)
        tree.column("Check", width=60, anchor="center")
        tree.column("Cliente", width=120)
        tree.column("Total", width=100)
        tree.column("Observaciones", width=250)

        # Estado de checks: dict item_id -> bool
        check_states = {}
        check_valores = {}

        # Agregar datos a la tabla (una sola fila por número de factura)
        seen_invoices = set()
        for idx, entry in enumerate(datos['facturas']):
            # entry puede ser (fila_row, amount) o una fila raw
            if isinstance(entry, (list, tuple)) and len(entry) >= 2 and isinstance(entry[1], (int, float)):
                factura_row = entry[0]
                valor_total = float(entry[1])
            else:
                factura_row = entry
                valor_total = float(self._get_total(factura_row) or 0.0)

            fact_id, num_factura, fecha_hora, cliente, metodo, _, observaciones = self._unpack_factura(factura_row)
            inv_key = str(num_factura)
            if inv_key in seen_invoices:
                continue
            seen_invoices.add(inv_key)

            hora = ''
            try:
                hora = fecha_hora.split(" ")[1] if fecha_hora and " " in fecha_hora else (fecha_hora or '')
            except Exception:
                hora = fecha_hora or ''

            obs_display = (observaciones[:50] + "...") if observaciones and len(observaciones) > 50 else (observaciones or "-")
            item_id = tree.insert("", tk.END, values=(
                fact_id,
                num_factura,
                hora,
                "✗",  # Inicialmente desmarcado
                cliente if cliente else "No especificado",
                f"${valor_total:,.0f}".replace(",", "."),
                obs_display
            ))
            check_states[item_id] = False
            check_valores[item_id] = valor_total

        # Agregar scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def on_tree_click(event):
            region = tree.identify("region", event.x, event.y)
            if region != "cell":
                return
            col = tree.identify_column(event.x)
            if col != "#4":  # Columna Check
                return
            row_id = tree.identify_row(event.y)
            if not row_id:
                return
            # Alternar estado
            current = check_states.get(row_id, False)
            new_state = not current
            check_states[row_id] = new_state
            tree.set(row_id, "Check", "✓" if new_state else "✗")
            # Actualizar saldo pendiente
            total = datos['total']
            checked_sum = sum(check_valores[iid] for iid, checked in check_states.items() if checked)
            saldo = total - checked_sum
            saldo_pendiente_var.set(f"Saldo Pendiente: ${saldo:,.0f}")

        tree.bind("<Button-1>", on_tree_click)
