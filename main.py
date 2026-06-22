from fastapi import FastAPI, Form, HTTPException, status
from parser import parsear_correo_bdv
from database import inicializar_bd, obtener_conexion
from bcv import obtener_tasa_bcv
import sqlite3

app = FastAPI(
    title="Pasarela de Pagos BDV & POS SaaS",
    description="Sistema automatizado de conciliación bancaria y punto de venta multi-moneda.",
    version="1.0.0"
)

# Al arrancar la API en la nube, creamos el archivo de la base de datos automáticamente
@app.on_event("startup")
def startup_event():
    inicializar_bd()

# --- RUTA RAÍZ (BIENVENIDA) ---
@app.get("/", summary="Página de inicio del sistema")
async def inicio():
    """
    Ruta principal que elimina el error 'Not Found' en producción.
    """
    return {
        "sistema": "Pasarela de Pagos Automática BDV & POS SaaS",
        "estado": "Online/Producción",
        "servidor": "Render Cloud",
        "ingeniero": "Oswar",
        "mensaje": "Bienvenido. Ingresa a /docs para interactuar con el panel de la API."
    }

# --- MÓDULO FINANCIERO (CONCILIACIÓN) ---
@app.post("/webhook-banco", summary="Recibe y almacena el pago en la Base de Datos")
async def recibir_pago(
    subject: str = Form(...), 
    body_plain: str = Form(..., alias="body-plain")
):
    if "pago movil" not in subject.lower():
        return {"status": "ignored", "reason": "No es una notificación de pago móvil"}
    
    resultado = parsear_correo_bdv(body_plain)
    
    if resultado["status"] == "success":
        ref = resultado["referencia"]
        monto = resultado["monto"]
        tel = resultado["telefono"]
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO transacciones_bdv (referencia, monto, telefono) VALUES (?, ?, ?)",
                (ref, monto, tel)
            )
            conn.commit()
            print(f"\n[BD SQLITE] ¡Pago guardado en disco! Ref: {ref}")
        except sqlite3.IntegrityError:
            print(f"\n[AVISO] Intento de registrar referencia duplicada: {ref}")
        finally:
            conn.close()
            
    return resultado

@app.get("/verificar-pago/{referencia}", summary="La tienda online consulta la Base de Datos")
async def verificar_pago(referencia: str, monto_cliente: float):
    ref_clave = referencia[-6:]
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transacciones_bdv WHERE referencia = ?", (ref_clave,))
    pago_real = cursor.fetchone()
    conn.close()
    
    if not pago_real:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Pago no encontrado en los registros bancarios."
        )
        
    if pago_real["procesado"] == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Esta referencia de pago ya fue utilizada en otra compra."
        )
        
    if pago_real["monto"] != monto_cliente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"El monto no coincide. Registrado: {pago_real['monto']} VES."
        )
        
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("UPDATE transacciones_bdv SET procesado = 1 WHERE referencia = ?", (ref_clave,))
    conn.commit()
    conn.close()
    
    return {
        "status": "pago_verificado",
        "message": "El pago ha sido validado en base de datos. ¡Procesar orden!"
    }

# --- MÓDULO CAMBIARIO (TASACIÓN) ---
@app.get("/sistema/actualizar-tasa", summary="Sincroniza la tasa oficial con el BCV")
async def sincronizar_tasa():
    tasa_actual = obtener_tasa_bcv()
    
    if tasa_actual == 0.0:
        raise HTTPException(status_code=500, detail="No se pudo obtener la tasa del BCV.")
        
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO tasa_cambio (moneda, valor, actualizado_en) 
        VALUES ('USD', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(moneda) DO UPDATE SET valor = excluded.valor, actualizado_en = CURRENT_TIMESTAMP
    """, (tasa_actual,))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "tasa_actualizada",
        "moneda": "USD",
        "tasa_bcv": tasa_actual,
        "mensaje": "Tasa oficial sincronizada y guardada en disco."
    }

# --- MÓDULO COMERCIAL (INVENTARIO Y POS) ---
@app.post("/inventario/agregar", summary="Registra un artículo fijando su costo en dólares")
async def agregar_producto(codigo: str, nombre: str, costo_usd: float, margen_ganancia: float, stock: int):
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO productos (codigo_barras, nombre, costo_usd, margen_ganancia, stock)
            VALUES (?, ?, ?, ?, ?)
        """, (codigo, nombre, costo_usd, margen_ganancia, stock))
        conn.commit()
        return {"status": "success", "message": f"Producto '{nombre}' registrado con éxito."}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="El código de barras ya existe.")
    finally:
        conn.close()

@app.get("/pos/consultar-precio/{codigo}", summary="El Punto de Venta escanea y calcula el precio final")
async def consultar_precio_caja(codigo: str):
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM productos WHERE codigo_barras = ?", (codigo,))
    producto = cursor.fetchone()
    
    if not producto:
        conn.close()
        raise HTTPException(status_code=404, detail="Producto no registrado en inventario.")
        
    cursor.execute("SELECT valor FROM tasa_cambio WHERE moneda = 'USD'")
    tasa_registro = cursor.fetchone()
    conn.close()
    
    tasa_bcv = tasa_registro["valor"] if tasa_registro else 1.0
    
    costo = producto["costo_usd"]
    margen = producto["margen_ganancia"]
    
    precio_venta_usd = round(costo * (1 + (margen / 100)), 2)
    precio_venta_ves = round(precio_venta_usd * tasa_bcv, 2)
    
    return {
        "codigo": producto["codigo_barras"],
        "nombre": producto["nombre"],
        "stock_disponible": producto["stock"],
        "tasa_bcv_aplicada": tasa_bcv,
        "precios_venta": {
            "USD": precio_venta_usd,
            "VES": precio_venta_ves
        }
    }

@app.post("/pos/procesar-venta", summary="Registra la venta en caja y descuenta del inventario")
async def procesar_venta(codigo_barras: str, cantidad_a_vender: int, metodo_pago: str, referencia: str = None):
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM productos WHERE codigo_barras = ?", (codigo_barras,))
    producto = cursor.fetchone()
    
    if not producto:
        conn.close()
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
        
    if producto["stock"] < cantidad_a_vender:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {producto['stock']} unidades.")
        
    cursor.execute("SELECT valor FROM tasa_cambio WHERE moneda = 'USD'")
    tasa_registro = cursor.fetchone()
    tasa_bcv = tasa_registro["valor"] if tasa_registro else 1.0
    
    precio_usd = round(producto["costo_usd"] * (1 + (producto["margen_ganancia"] / 100)), 2)
    total_usd = round(precio_usd * cantidad_a_vender, 2)
    total_ves = round(total_usd * tasa_bcv, 2)
    
    if metodo_pago.upper() == "PAGO_MOVIL":
        if not referencia:
            conn.close()
            raise HTTPException(status_code=400, detail="Debe ingresar el número de referencia para transacciones por Pago Móvil.")
        
        ref_clave = referencia[-6:]
        cursor.execute("SELECT * FROM transacciones_bdv WHERE referencia = ? AND procesado = 0 AND monto >= ?", (ref_clave, total_ves))
        pago_banco = cursor.fetchone()
        
        if not pago_banco:
            conn.close()
            raise HTTPException(status_code=400, detail="El pago móvil indicado no existe en el banco o el monto es inferior al total.")
            
        cursor.execute("UPDATE transacciones_bdv SET procesado = 1 WHERE referencia = ?", (ref_clave,))

    nuevo_stock = producto["stock"] - cantidad_a_vender
    cursor.execute("UPDATE productos SET stock = ? WHERE codigo_barras = ?", (nuevo_stock, codigo_barras))
    
    cursor.execute("""
        INSERT INTO ventas (codigo_producto, cantidad, total_usd, total_ves, metodo_pago, referencia_pago)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (codigo_barras, cantidad_a_vender, metodo_pago.upper(), referencia))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "venta_completada",
        "factura": {
            "articulo": producto["nombre"],
            "cantidad_vendida": cantidad_a_vender,
            "stock_restante": nuevo_stock,
            "total_usd": total_usd,
            "total_ves": total_ves,
            "metodo_pago": metodo_pago.upper()
        }
    }
