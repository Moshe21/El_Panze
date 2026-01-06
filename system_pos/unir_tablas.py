import os
import re
from PyPDF2 import PdfReader
import db_manager


def extraer_info_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    lineas = []

    for page in reader.pages:
        t = page.extract_text()
        if t:
            lineas.extend([l.strip() for l in t.splitlines() if l.strip()])

    def buscar(prefijo):
        for i, l in enumerate(lineas):
            if prefijo in l:
                # Caso 1: valor en la misma línea
                valor = l.replace(prefijo, "").strip()
                if valor:
                    return valor

                # Caso 2: valor en la línea siguiente
                if i + 1 < len(lineas):
                    return lineas[i + 1].strip()
        return ""
    def buscar_num_factura():
        for i, l in enumerate(lineas):
            if "PEDIDO" in l or l.strip() == "#":
                # buscar el número en esta o en las siguientes líneas
                for j in range(i, min(i + 4, len(lineas))):
                    m = re.search(r"\d+", lineas[j])
                    if m:
                        return m.group()
        return ""
    # ===== DATOS GENERALES =====
    num_factura = buscar_num_factura()
    fecha = buscar("Fecha:")
    nom_cliente = buscar("Cliente:")
    direccion = buscar("Dirrecion:")
    metodo_pago = buscar("Método de pago:")

    # ===== PRODUCTOS =====
    productos = []
    leyendo = False

    cantidad = None
    producto = None

    for l in lineas:
        l = l.strip()

        if "Cantidad" in l:
            leyendo = True
            continue

        if "Total a pagar" in l:
            break

        if not leyendo:
            continue

        print("🔎 Analizando línea:", l)

        # 1️⃣ Cantidad
        if cantidad is None and re.fullmatch(r"\d+", l):
            cantidad = int(l)
            continue

        # 2️⃣ Producto
        if cantidad is not None and producto is None and not l.startswith("$"):
            producto = l
            continue

        # 3️⃣ Subtotal
        if cantidad is not None and producto is not None and "$" in l:
            subtotal = int(re.search(r"([\d\.]+)", l).group(1).replace(".", ""))
            valor_unitario = subtotal // cantidad

            productos.append((cantidad, producto, valor_unitario, subtotal))
            print("✅ Producto armado:", cantidad, producto, subtotal)

            cantidad = None
            producto = None

    # ===== TOTAL FACTURA =====
    total = 0
    for l in lineas:
        if l.startswith("Total a pagar"):
            total = int(re.search(r"\$([\d\.]+)", l).group(1).replace(".", ""))
            break

    # ===== OBSERVACIONES =====
    comentarios = ""

    if "Observaciones:" in lineas:
        idx = lineas.index("Observaciones:") + 1
        obs = []

        FRASES_EXCLUIDAS = [
            "Gracias por tu compra",
            "El sabor diferente",
            "de siempre"
        ]

        while idx < len(lineas):
            linea = lineas[idx].strip()

            # 🛑 Cortar si llega al mensaje final
            if linea.lower().startswith("gracias"):
                break

            # ❌ Saltar frases comerciales
            if any(frase.lower() in linea.lower() for frase in FRASES_EXCLUIDAS):
                idx += 1
                continue

            obs.append(linea)
            idx += 1

        comentarios = " | ".join(obs)

    return num_factura, fecha, nom_cliente, direccion, metodo_pago, total, comentarios, productos


def registrar_facturas_pdf_en_db():
    db_manager.create_facturas_pdf_table()
    carpeta = "facturas"

    for fname in os.listdir(carpeta):
        if not fname.lower().endswith(".pdf"):
            continue

        ruta = os.path.join(carpeta, fname)
        #print(f"📄 Procesando {fname}")

        num, fecha, cliente, dirr, metodo, total, obs, productos = extraer_info_pdf(ruta)
        print("🧪 PRODUCTOS EXTRAÍDOS:", productos)
        for cantidad, producto, unit, sub in productos:
            db_manager.insert_factura_pdf(
                num, fecha, cliente, dirr, metodo,
                cantidad, producto, unit, sub, total, obs
            )
            print("✅ Importada correctamentezzz")

        

   # print("🎉 PDFs importados a facturas_completas")


if __name__ == "__main__":
    registrar_facturas_pdf_en_db()
   