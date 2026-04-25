
import os
import re

def fix_encoding():
    path = os.path.join('booking', 'forms.py')
    print(f"🔧 Reparando codificación de {path}")
    
    with open(path, 'rb') as f:
        content_bytes = f.read()
    
    # Intentar decodificar como utf-8 ignorando errores
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
    except:
        content_str = content_bytes.decode('utf-16', errors='ignore')

    # Eliminar nulos
    content_str = content_str.replace('\x00', '')
    
    # Escribir limpio
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content_str)
        
    print("✅ Archivo reparado y guardado como UTF-8.")

if __name__ == "__main__":
    fix_encoding()
