import re

def parsear_correo_bdv(cuerpo_correo: str) -> dict:
    """
    Analiza el texto del correo del BDV de forma flexible con o sin acentos.
    """
    # Expresiones regulares mejoradas para aceptar opcionalmente los acentos (móvil/movil, teléfono/telefono)
    regex_monto = r"monto de VES\s*([0-9.,]+)"
    regex_telefono = r"tel[eé]fono\s*([0-9-]+)"
    regex_referencia = r"referencia\s*([0-9]+)"
    
    try:
        monto_raw = re.search(regex_monto, cuerpo_correo).group(1)
        monto = float(monto_raw.replace(".", "").replace(",", "."))
        
        telefono = re.search(regex_telefono, cuerpo_correo).group(1).replace("-", "")
        referencia_completa = re.search(regex_referencia, cuerpo_correo).group(1)
        referencia_clave = referencia_completa[-6:] 
        
        return {
            "status": "success",
            "referencia": referencia_clave,
            "monto": monto,
            "telefono": telefono
        }
    except AttributeError:
        return {"status": "error", "message": "No se pudo interpretar el formato del correo"}
