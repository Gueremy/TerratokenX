import os

def clean_models():
    file_path = os.path.join('booking', 'models.py')
    print(f"🧹 Limpiando {file_path}")
    
    with open(file_path, 'rb') as f:
        content = f.read()
        
    # Eliminar bytes nulos
    clean_content = content.replace(b'\x00', b'')
    
    # Escribir de nuevo
    with open(file_path, 'wb') as f:
        f.write(clean_content)
    
    print("✨ Archivo limpiado.")

if __name__ == "__main__":
    clean_models()
