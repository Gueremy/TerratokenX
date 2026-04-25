import os
import re

class RenderGuarantor:
    """
    Utility to maintain visual excellence and data robustness 
    across all Django templates in the project.
    """
    
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.stats = {'files_scanned': 0, 'fixes_applied': 0}
        
        # DEFINICIÓN DE REGLAS DE ORO
        self.rules = [
            # 1. Asegurar valores por defecto en inputs numéricos
            {
                'name': 'Robust Token Values',
                'pattern': r'value="{{ (proyecto\.tokens_totales|form\.tokens_totales\.value)(?!\|default) }}"',
                'replacement': 'value="{{ \\1|default_if_none:"1000" }}"'
            },
            {
                'name': 'Robust Price Values',
                'pattern': r'value="{{ (proyecto\.precio_token|form\.precio_token\.value)(?!\|default) }}"',
                'replacement': 'value="{{ \\1|default_if_none:"100" }}"'
            },
            
            # 2. Inyectar x-cloak en AlpineJS para evitar parpadeos
            {
                'name': 'Alpine Cloak',
                'pattern': r'x-show="([^"]+)"(?![^>]*x-cloak)',
                'replacement': 'x-show="\\1" x-cloak'
            },
            
            # 3. Estética de Inputs (Convertir inputs aburridos en Premium)
            {
                'name': 'Premium Input Styling',
                'pattern': r'class="form-control"(?!.*bg-dark)',
                'replacement': 'class="bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-emerald-500 outline-none transition-all"'
            },
            
            # 4. Corrección de Iconos Material
            {
                'name': 'Material Icon Polish',
                'pattern': r'class="material-icons"(?!.*text-)',
                'replacement': 'class="material-icons text-emerald-400"'
            }
        ]

    def scan_and_fix(self):
        print(f"🚀 Iniciando RenderGuarantor en: {self.root_dir}")
        
        template_dir = os.path.join(self.root_dir, 'booking', 'templates')
        
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    self.process_file(os.path.join(root, file))
        
        print("\n✨ Proceso Finalizado:")
        print(f"📂 Archivos escaneados: {self.stats['files_scanned']}")
        print(f"🛠️ Arreglos aplicados: {self.stats['fixes_applied']}")

    def process_file(self, file_path):
        self.stats['files_scanned'] += 1
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        file_made_changes = False
        
        for rule in self.rules:
            matches = re.findall(rule['pattern'], new_content)
            if matches:
                new_content = re.sub(rule['pattern'], rule['replacement'], new_content)
                count = len(matches)
                self.stats['fixes_applied'] += count
                file_made_changes = True
                print(f"  [FIX] {rule['name']} en {os.path.basename(file_path)} ({count} ocurrencias)")
        
        if file_made_changes:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

if __name__ == "__main__":
    # Ajustar a la ruta del proyecto
    project_path = os.getcwd()
    guarantor = RenderGuarantor(project_path)
    guarantor.scan_and_fix()
