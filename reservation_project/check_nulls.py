
import os

def check_file():
    path = os.path.join('booking', 'forms.py')
    print(f"🔍 Analizando {path}...")
    
    with open(path, 'rb') as f:
        content = f.read()
        
    null_count = content.count(b'\x00')
    print(f"Bytes nulos encontrados: {null_count}")
    
    if null_count > 0:
        print("⚠️ ALERTA: El archivo está corrupto con bytes nulos.")
        # Mostrar dónde están los primeros nulos
        idx = content.find(b'\x00')
        print(f"Primer byte nulo en posición: {idx}")
        context = content[max(0, idx-20):min(len(content), idx+20)]
        print(f"Contexto alrededor del error: {context}")
    else:
        print("✅ El archivo está limpio de bytes nulos.")

if __name__ == "__main__":
    check_file()
