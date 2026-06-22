import re

def parsear_correo_bnc(cuerpo_correo: str) -> dict:
    """
    Analiza el texto plano del correo del BNC y extrae los datos clave.
    """
    # Expresiones regulares flexibles adaptadas al formato de correos del BNC
    regex_monto = r"(?:Monto|monto)(?:\s*:\s*|\s+de\s+VES\s*)([0-9.,]+)"
    regex_referencia = r"(?:Referencia|referencia|Nro\.\s*Operaci[oó]n)(?:\s*:\s*|\s+)([0-9]+)"
    regex_telefono = r"(?:Celular|Tel[eé]fono)(?:\s*origen\s*:\s*|\s+)([0-9-]+)"
    
    try:
        # 1. Extraer y limpiar el monto (quitar puntos de miles y cambiar coma por punto decimal)
        monto_match = re.search(regex_monto, cuerpo_correo)
        if not monto_match:
            return {"status": "error", "message": "No se encontró el monto."}
            
        monto_raw = monto_match.group(1)
        if "." in monto_raw and "," in monto_raw:
            monto_raw = monto_raw.replace(".", "")
        monto = float(monto_raw.replace(",", "."))
        
        # 2. Extraer referencia bancaria
        ref_match = re.search(regex_referencia, cuerpo_correo)
        if not ref_match:
            return {"status": "error", "message": "No se encontró la referencia."}
        referencia_completa = ref_match.group(1)
        referencia_clave = referencia_completa[-6:] # Mantenemos los últimos 6 dígitos estándar
        
        # 3. Extraer teléfono
        tel_match = re.search(regex_telefono, cuerpo_correo)
        telefono = tel_match.group(1).replace("-", "") if tel_match else "00000000000"
        
        return {
            "status": "success",
            "referencia": referencia_clave,
            "monto": monto,
            "telefono": telefono
        }
    except Exception as e:
        return {"status": "error", "message": f"Falla al interpretar correo BNC: {str(e)}"}
