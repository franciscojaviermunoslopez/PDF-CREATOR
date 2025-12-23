import os

# Configuración de entorno para silenciar MuPDF
os.environ['FITZ_LOG_LEVEL'] = '0'

import fitz  # PyMuPDF
from PIL import Image
from pypdf import PdfReader

# Silenciar errores y advertencias de la librería MuPDF
try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.set_mupdf_warnings(False)
except:
    pass

def render_pdf_to_images(pdf_path, dpi=150):
    """
    Convierte todas las páginas de un PDF en una lista de imágenes PIL.
    """
    try:
        doc = fitz.open(pdf_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, annots=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
        return images
    except Exception as e:
        print(f"Error renderizando PDF: {e}")
        return []

def extract_pdf_fields_info(pdf_path):
    """
    Extrae información de los campos de un PDF para importar al editor.
    """
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        if not fields:
            return []
            
        extracted = []
        for name, data in fields.items():
            ft = data.get('/FT')
            ftype = "Texto"
            
            if ft == '/Btn':
                flags = data.get('/Ff', 0)
                if flags & 32768:
                    ftype = "Radio Buttons"
                else:
                    ftype = "Checkbox"
            elif ft == '/Ch':
                ftype = "Dropdown"
            elif ft == '/Sig':
                ftype = "Firma"
            elif ft == '/Tx':
                flags = data.get('/Ff', 0)
                if flags & 4096:
                    ftype = "Multilínea"
            
            # Intentar obtener opciones si es dropdown
            options = ""
            if ft == '/Ch' and '/Opt' in data:
                opts = data['/Opt']
                if isinstance(opts, list):
                    options = ", ".join([str(o) for o in opts])

            extracted.append({
                "label": name,
                "type": ftype,
                "options": options
            })
        return extracted
    except Exception as e:
        print(f"Error extrayendo campos: {e}")
        return []

def find_field_box_at(pdf_path, page_num, x_pts, y_pts):
    """
    Busca un recuadro vectorial (dibujo o líneas) en las coordenadas dadas.
    Retorna (x, y, w, h) en puntos PDF o None si no encuentra nada razonable.
    """
    try:
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            return None
            
        page = doc[page_num]
        
        # 1. Intentar con drawings (rectángulos vectoriales)
        drawings = page.get_drawings()
        best_box = None
        min_area = float('inf')
        
        for d in drawings:
            rect = d.get('rect')
            if not rect: continue
            
            if rect.x0 <= x_pts <= rect.x1 and rect.y0 <= y_pts <= rect.y1:
                area = rect.width * rect.height
                if area < min_area and area > 100:
                    min_area = area
                    best_box = {
                        "x": rect.x0,
                        "y": rect.y0,
                        "w": rect.width,
                        "h": rect.height
                    }
        
        if best_box:
            doc.close()
            return best_box
        
        # 2. Si no encontró drawings, buscar líneas cercanas
        # Obtener todas las líneas de la página
        paths = page.get_drawings()
        h_lines = []  # Líneas horizontales
        v_lines = []  # Líneas verticales
        
        tolerance = 5  # Tolerancia en puntos
        
        for path in paths:
            items = path.get('items', [])
            for item in items:
                if item[0] == 'l':  # Línea
                    p1, p2 = item[1], item[2]
                    # Línea horizontal (Y similar)
                    if abs(p1.y - p2.y) < tolerance:
                        y = (p1.y + p2.y) / 2
                        x1, x2 = min(p1.x, p2.x), max(p1.x, p2.x)
                        h_lines.append((x1, x2, y))
                    # Línea vertical (X similar)
                    elif abs(p1.x - p2.x) < tolerance:
                        x = (p1.x + p2.x) / 2
                        y1, y2 = min(p1.y, p2.y), max(p1.y, p2.y)
                        v_lines.append((x, y1, y2))
        
        print(f"[DETECT] Encontradas {len(h_lines)} líneas horizontales y {len(v_lines)} líneas verticales")
        
        # Buscar líneas que formen un recuadro alrededor del punto
        search_radius = 50  # Radio de búsqueda
        
        # Líneas horizontales arriba y abajo
        top_line = None
        bottom_line = None
        for x1, x2, y in h_lines:
            if x1 <= x_pts <= x2 and abs(y - y_pts) < search_radius:
                if y < y_pts:  # Línea arriba
                    if not top_line or y > top_line[2]:
                        top_line = (x1, x2, y)
                elif y > y_pts:  # Línea abajo
                    if not bottom_line or y < bottom_line[2]:
                        bottom_line = (x1, x2, y)
        
        # Líneas verticales izquierda y derecha
        left_line = None
        right_line = None
        for x, y1, y2 in v_lines:
            if y1 <= y_pts <= y2 and abs(x - x_pts) < search_radius:
                if x < x_pts:  # Línea izquierda
                    if not left_line or x > left_line[0]:
                        left_line = (x, y1, y2)
                elif x > x_pts:  # Línea derecha
                    if not right_line or x < right_line[0]:
                        right_line = (x, y1, y2)
        
        # Si encontramos al menos top y bottom, crear el recuadro
        if top_line and bottom_line:
            x0 = left_line[0] if left_line else top_line[0]
            x1 = right_line[0] if right_line else top_line[1]
            y0 = top_line[2]
            y1 = bottom_line[2]
            
            best_box = {
                "x": x0,
                "y": y0,
                "w": x1 - x0,
                "h": y1 - y0
            }
        
        doc.close()
        return best_box
    except Exception as e:
        print(f"Error detectando caja: {e}")
        return None
def get_pdf_dimensions(pdf_path):
    """
    Retorna (ancho, alto) de la primera página del PDF en puntos (1/72 pulgada).
    """
    try:
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            page = doc[0]
            w, h = page.rect.width, page.rect.height
            doc.close()
            return w, h
        doc.close()
    except Exception as e:
        print(f"Error obteniendo dimensiones: {e}")
    return 612.0, 792.0 # Fallback a Letter
def map_import_type(import_type):
    """Mapea el tipo de campo importado al tipo de visualización de la aplicación."""
    type_map = {
        'text': 'Texto', 'date': 'Fecha', 'checkbox': 'Checkbox',
        'dropdown': 'Dropdown', 'radio': 'Radio Buttons',
        'multiline': 'Multilínea', 'signature': 'Firma', 'number': 'Número'
    }
    return type_map.get(import_type, 'Texto')

def map_type_to_internal(display_type):
    """Mapea el tipo de visualización al tipo interno."""
    type_map = {
        'Texto': 'text', 'Fecha': 'date', 'Checkbox': 'checkbox',
        'Dropdown': 'dropdown', 'Radio Buttons': 'radio',
        'Multilínea': 'multiline', 'Firma': 'signature', 'Número': 'number'
    }
    return type_map.get(display_type, 'text')
