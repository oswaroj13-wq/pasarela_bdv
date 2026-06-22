import urllib.request
import re
import ssl

def obtener_tasa_bcv() -> float:
    """
    Versión blindada: Extrae el dólar oficial ignorando restricciones SSL.
    """
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Bypass para evitar errores de certificados SSL locales en entornos Windows
    contexto_ssl = ssl._create_unverified_context()
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12, context=contexto_ssl) as response:
            html = response.read().decode('utf-8')
        
        # 1. Buscamos primero el bloque completo contenedor del dólar
        bloque_dolar = re.search(r'id="dolar".*?</div>', html, re.DOTALL)
        
        if bloque_dolar:
            texto_bloque = bloque_dolar.group(0)
            # 2. Extraemos el número decimal (ej. 45,50 o 46.10) que esté dentro de ese bloque
            regex_numero = r"([0-9]+[.,][0-9]+)"
            numero_encontrado = re.search(regex_numero, texto_bloque)
            
            if numero_encontrado:
                tasa_raw = numero_encontrado.group(1)
                # Normalizar formato numérico estándar (quitar puntos de miles, cambiar coma por punto)
                if "," in tasa_raw and "." in tasa_raw:
                    tasa_raw = tasa_raw.replace(".", "")
                tasa_bcv = float(tasa_raw.replace(",", "."))
                return tasa_bcv
                
        # Alternativa de emergencia si cambiaron el ID "dolar"
        busqueda_directa = re.search(r'field-content">.*?([0-9]{2},[0-9]{2,4})\s*</span>', html)
        if busqueda_directa:
            return float(busqueda_directa.group(1).replace(",", "."))
            
        print("[SISTEMA] Estructura HTML irreconocible.")
        return 0.0
            
    except Exception as e:
        print(f"[ERROR CONEXIÓN] Falla crítica al conectar: {e}")
        return 0.0
