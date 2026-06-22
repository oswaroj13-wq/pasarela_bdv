import sqlite3

DATABASE_NAME = "pasarela.db"

def obtener_conexion():
    """Crea una conexión limpia a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    # Esto permite acceder a las columnas por su nombre como un diccionario
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_bd():
    """Crea la tabla de transacciones si no existe al arrancar el servidor."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacciones_bdv (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referencia TEXT UNIQUE NOT NULL,
        monto REAL NOT NULL,
        telefono TEXT,
        procesado INTEGER DEFAULT 0, -- 0 = Falso, 1 = Verdadero
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
        # Nueva tabla para registrar el historial de tasas de cambio
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasa_cambio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        moneda TEXT UNIQUE NOT NULL, -- "USD"
        valor REAL NOT NULL,        -- Ej: 45.50
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
        # Tabla de productos e inventario comercial
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        costo_usd REAL NOT NULL,      -- Costo base del producto en dólares
        margen_ganancia REAL NOT NULL, -- Porcentaje de ganancia (Ej: 30 para 30%)
        stock INTEGER NOT NULL DEFAULT 0,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Tabla para el histórico de ventas (Facturación)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_producto TEXT NOT NULL,
        cantidad INTEGER NOT NULL,
        total_usd REAL NOT NULL,
        total_ves REAL NOT NULL,
        metodo_pago TEXT NOT NULL, -- "EFECTIVO", "PAGO_MOVIL"
        referencia_pago TEXT,
        fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


    
    conn.commit()
    conn.close()
    print("[SISTEMA] Base de datos SQLite inicializada correctamente.")
