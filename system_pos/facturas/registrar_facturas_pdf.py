import os
import db_manager
from PyPDF2 import PdfReader
import re


def extraer_info_pdf_y_productos(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        # Extraer info general
        num_factura = re.search(r"PEDIDO\s*#?(\d+)", text, re.IGNORECASE)
        fecha = re.search(r"Fecha[:\s]+([\d/\-]+)", text, re.IGNORECASE)
        nom_cliente = re.search(r"Cliente[:\s]+([\w\s]+)", text, re.IGNORECASE)
        direccion = re.search(r"Dirrec?ion[:\s]+([\w\s\d\-#]+)", text, re.IGNORECASE)
        metodo_pago = re.search(r"M[eé]todo\s*de\s*pago[:\s]+([\w\s]+)", text, re.IGNORECASE)
        # Extraer tabla de productos
        productos = []
        tabla_match = re.search(r"Cantidad\s+Producto\s+Total(.+?)Total a pagar", text, re.DOTALL)
        if tabla_match:
            tabla = tabla_match.group(1)
            for linea in tabla.split("\n"):
                prod_match = re.match(r"\s*(\d+)\s+([\w\sáéíóúÁÉÍÓÚñÑ\-]+)\s+\$?([\d.,]+)", linea)
                if prod_match:
                    cantidad = int(prod_match.group(1))
                    producto = prod_match.group(2).strip()
                    valor_unitario = float(prod_match.group(3).replace(".", "").replace(",", ""))
                    total = cantidad * valor_unitario
                    productos.append({
                        "cantidad": cantidad,
                        "producto": producto,
                        "valor_unitario": valor_unitario,
                        "total": total
                    })
        return {
            "num_factura": num_factura.group(1) if num_factura else None,
            "fecha": fecha.group(1) if fecha else None,
            "nom_cliente": nom_cliente.group(1) if nom_cliente else None,
            "direccion": direccion.group(1) if direccion else None,
            "metodo_pago": metodo_pago.group(1) if metodo_pago else None,
            "productos": productos
        }
    except Exception as e:
        print(f"Error leyendo {pdf_path}: {e}")
        return {}


def registrar_facturas_pdf_en_db():
    db_manager.create_facturas_pdf_table()
    carpeta = "facturas" # <--- RUTA DE CARPETA FACTURAS
    for fname in os.listdir(carpeta): # <--- EJECUTA RUTA (LISTAR ARCHIVOS)
        if fname.lower().endswith(".pdf"):
            ruta = os.path.join(carpeta, fname) # <--- CONSTRUYE RUTA COMPLETA DEL ARCHIVO
            info = extraer_info_pdf_y_productos(ruta)
            print(f"Procesando archivo: {fname}")
            print(f"Info extraída: {info}")
            for prod in info.get("productos", []):
                print(f"Insertando producto: {prod}")
                db_manager.insert_factura_pdf(
                    info.get("num_factura"),
                    info.get("fecha"),
                    info.get("nom_cliente"),
                    info.get("direccion"),
                    info.get("metodo_pago"),
                    prod.get("cantidad"),
                    prod.get("producto"),
                    prod.get("valor_unitario"),
                    prod.get("total"), # subtotal
                    prod.get("total"), # total
                    "" # comentarios
                )
    print("Facturas PDF registradas en la base de datos.")

if __name__ == "__main__":
    registrar_facturas_pdf_en_db()
