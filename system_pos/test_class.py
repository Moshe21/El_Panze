import os
import tkinter as tk
from tkinter import ttk, messagebox
import db_manager
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import subprocess
from PIL import Image, ImageTk, ImageFilter




class DailyStatisticsWindow(tk.Toplevel):
    """Ventana para mostrar estadísticas detalladas de ventas del día por método de pago."""
    def __init__(self, parent, metodos_pago, fecha):
        super().__init__(parent)
        self.title("Estadísticas Detalladas del Día")
        self.geometry("1400x600")
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

            # Separar facturas en dos listas: pago punto y resto
            facturas_pago_punto = []
            facturas_otros = []
            for factura in datos['facturas']:
                # La dirección está en la posición 3 o 4 según estructura, revisar y ajustar si necesario
                # Estructura: (id, num_factura, fecha_hora, cliente, metodo_pago, valor_total, observaciones, ...)
                # Pero para facturas_completas: (id, num_factura, fecha, nom_cliente, direccion, metodo_pago, ...)
                # Usamos try para soportar ambas
                
                direccion = factura[4]
                if not (isinstance(direccion, str) and direccion.strip().lower() == "pago punto"):
                    facturas_otros.append(factura)

                else :
                    facturas_pago_punto.append(factura)
                

            # Crear dos frames dentro de la pestaña: uno para pago punto, otro para el resto
            frame_pago_punto = ttk.LabelFrame(tab, text="Facturas con dirección 'pago punto'", padding="5")
            frame_pago_punto.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            frame_otros = ttk.LabelFrame(tab, text="Facturas con otras direcciones", padding="5")
            frame_otros.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Datos para cada tabla
            datos_pago_punto = dict(datos)
            datos_pago_punto['facturas'] = facturas_pago_punto
            datos_pago_punto['cantidad'] = len(facturas_pago_punto)
            datos_pago_punto['total'] = sum(f[5] for f in facturas_pago_punto) if facturas_pago_punto else 0

            datos_otros = dict(datos)
            datos_otros['facturas'] = facturas_otros
            datos_otros['cantidad'] = len(facturas_otros)
            datos_otros['total'] = sum(f[5] for f in facturas_otros) if facturas_otros else 0

            # Crear tablas
            self.crear_tabla_metodo(frame_pago_punto, metodo_pago, datos_pago_punto)
            self.crear_tabla_metodo(frame_otros, metodo_pago, datos_otros)
    
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
        table_frame.pack(side=tk.LEFT, expand=True, padx=10, pady=10)

        # Crear Treeview con columna de check
        columns = ("ID", "Nº Factura", "Hora", "Check", "Cliente", "Total", "Observaciones")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
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

        # Agregar datos a la tabla
        for idx, factura in enumerate(datos['facturas']):
            fact_id, num_factura, fecha_hora, cliente, metodo, valor_total, observaciones = factura
            hora = fecha_hora.split(" ")[1] if " " in fecha_hora else fecha_hora
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



if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("200x200")
    root.title("Ventana Principal (Root)")
    
    def show_daily_statistics(parent):
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

        def show_statistics_for_date(fecha_str):
            columns, rows = db_manager.get_all_facturas_completas()
            
            # Filtrar por fecha
            rows_filtered = [r for r in rows if str(r[2]).startswith(fecha_str)]
            
            if not rows_filtered:
                messagebox.showinfo("Información", f"No hay datos para la fecha {fecha_str}")
                return

            metodos_pago = {}
            
            # Agrupar por factura para evitar duplicados de totales (ya que facturas_completas tiene items)
            facturas_map = {}
            for row in rows_filtered:
                # Indices: 0:id, 1:num, 2:fecha, 3:cli, 4:dir, 5:metodo, 6:cant, 7:prod, 8:unit, 9:sub, 10:total, 11:obs
                num_factura = row[1]
                if num_factura not in facturas_map:
                    facturas_map[num_factura] = {'info': row, 'obs': set()}
                if row[11]:
                    facturas_map[num_factura]['obs'].add(str(row[11]))
                    
            # Procesar facturas únicas
            for num, data in facturas_map.items():
                row = data['info']
                obs_str = " | ".join(data['obs'])
                # Tupla (7 elementos): (id, num, fecha, cliente, direccion, total, obs)
                factura_tuple = (row[0], row[1], row[2], row[3], row[4], row[10], obs_str)
                
                metodo_pago_str = row[5]
                total_val = row[10]
                
                # Manejo de pagos divididos
                if metodo_pago_str and '|' in metodo_pago_str and '+' in metodo_pago_str:
                    try:
                        for parte in metodo_pago_str.split('+'):
                            m_nombre, m_monto = parte.split('|')
                            m_nombre, m_monto = m_nombre.strip(), float(m_monto)
                            metodos_pago.setdefault(m_nombre, {'cantidad': 0, 'total': 0, 'facturas': []})
                            metodos_pago[m_nombre]['cantidad'] += 1
                            metodos_pago[m_nombre]['total'] += m_monto
                            metodos_pago[m_nombre]['facturas'].append(factura_tuple)
                    except: pass
                else:
                    m_nombre = metodo_pago_str if metodo_pago_str else "Sin Método"
                    metodos_pago.setdefault(m_nombre, {'cantidad': 0, 'total': 0, 'facturas': []})
                    metodos_pago[m_nombre]['cantidad'] += 1
                    metodos_pago[m_nombre]['total'] += total_val
                    metodos_pago[m_nombre]['facturas'].append(factura_tuple)
            
            DailyStatisticsWindow(parent, metodos_pago, fecha_str)

        DateSelectionModal(parent, show_statistics_for_date)

    show_daily_statistics(root)
    root.mainloop()
