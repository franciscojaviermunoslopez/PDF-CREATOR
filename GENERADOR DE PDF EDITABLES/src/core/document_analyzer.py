"""
Analizador de documentos PDF para extracción automática de campos de formulario.
Detecta campos AcroForm existentes y patrones visuales de formularios.
Incluye detección avanzada de líneas horizontales usando OpenCV y PyMuPDF.
"""

import os
# Silenciar MuPDF
os.environ['FITZ_LOG_LEVEL'] = '0'

import fitz  # PyMuPDF
import cv2
import numpy as np
import re
from typing import List, Dict, Optional, Tuple
from PIL import Image
import io

try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.set_mupdf_warnings(False)
except:
    pass


class DocumentAnalyzer:
    """Analiza documentos PDF para extraer campos de formulario automáticamente."""
    
    # Patrones regex para detectar tipos de campos
    PATTERNS = {
        'nombre': r'(?i)(nombre|name|apellidos?|surname|first\s*name|last\s*name)',
        'email': r'(?i)(e-?mail|correo\s*electr[oó]nico)',
        'telefono': r'(?i)(tel[eé]fono|phone|m[oó]vil|celular|tel\.?)',
        'fecha': r'(?i)(fecha|date|nacimiento|birth)',
        'dni': r'(?i)(dni|nif|nie|documento|id|identification)',
        'direccion': r'(?i)(direcci[oó]n|address|calle|street)',
        'codigo_postal': r'(?i)(c[oó]digo\s*postal|zip|postal\s*code|cp)',
        'ciudad': r'(?i)(ciudad|city|localidad|poblaci[oó]n)',
        'provincia': r'(?i)(provincia|state|regi[oó]n)',
        'pais': r'(?i)(pa[ií]s|country)',
    }
    
    def __init__(self):
        """Inicializa el analizador."""
        self.detected_fields = []
        self.detected_title = None
        
    def analyze_pdf(self, pdf_path: str, progress_callback=None) -> Dict:
        """
        Analiza un PDF y extrae campos de formulario.
        """
        try:
            doc = fitz.open(pdf_path)
            
            # Intentar extraer campos AcroForm primero
            acroform_fields = self._extract_acroform_fields(doc)
            
            # Si no hay AcroForm, buscar patrones visuales
            if not acroform_fields:
                visual_fields = self._extract_visual_fields(doc, progress_callback)
                fields = visual_fields
                has_acroform = False
            else:
                fields = acroform_fields
                has_acroform = True
            
            # Detectar título del documento
            title = self._detect_title(doc)
            
            # Guardar número de páginas antes de cerrar
            page_count = len(doc)
            
            doc.close()
            
            return {
                'fields': fields,
                'title': title,
                'has_acroform': has_acroform,
                'page_count': page_count,
                'success': True
            }
            
        except Exception as e:
            return {
                'fields': [],
                'title': None,
                'has_acroform': False,
                'page_count': 0,
                'success': False,
                'error': str(e)
            }
    
    def _extract_acroform_fields(self, doc: fitz.Document) -> List[Dict]:
        """
        Extrae campos de un PDF con AcroForm.
        
        Args:
            doc: Documento PyMuPDF
            
        Returns:
            Lista de campos detectados
        """
        fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Obtener widgets (campos de formulario)
            widgets = page.widgets()
            
            for widget in widgets:
                field_name = widget.field_name or f"Campo {len(fields) + 1}"
                field_type = self._map_widget_type(widget.field_type)
                
                # Obtener posición del campo
                rect = widget.rect
                
                field_info = {
                    'label': field_name,
                    'type': field_type,
                    'abs_pos': {
                        'x': rect.x0,
                        'y': rect.y0,
                        'w': rect.width,
                        'h': rect.height,
                        'page': page_num
                    },
                    'column': 'full',
                    'options': [],
                    'required': False,
                    'validation': 'Ninguno'
                }
                
                # Si es dropdown o radio, extraer opciones
                if field_type in ['dropdown', 'radio']:
                    field_info['options'] = widget.field_value or []
                
                fields.append(field_info)
        
        return fields
    
    def _extract_visual_fields(self, doc: fitz.Document, progress_callback=None) -> List[Dict]:
        """
        Extrae campos detectando patrones visuales en el PDF.
        """
        fields = []
        import time
        
        total_pages = len(doc)
        for page_num in range(total_pages):
            if progress_callback:
                progress_callback(page_num + 1, total_pages)
            
            page = doc[page_num]
            
            # Detectar líneas horizontales usando AMBOS métodos
            # 1. PyMuPDF para líneas vectoriales
            vector_lines = self._detect_horizontal_lines_pymupdf(page)
            
            # 2. OpenCV para líneas dibujadas/rasterizadas
            opencv_lines = self._detect_horizontal_lines_opencv(page)
            
            # Combinar ambas detecciones y eliminar duplicados
            all_lines = self._merge_detected_lines(vector_lines, opencv_lines)
            
            # Extraer texto con posiciones
            text_instances = page.get_text("dict")
            
            # Buscar etiquetas de campos
            labels_found = []
            for block in text_instances.get("blocks", []):
                if block.get("type") == 0:  # Bloque de texto
                    for line in block.get("lines", []):
                        line_text = ""
                        line_bbox = line.get("bbox", [0, 0, 0, 0])
                        
                        # Obtener tamaño de fuente promedio de la línea
                        font_sizes = []
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                            font_sizes.append(span.get("size", 0))
                        
                        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0
                        
                        # Detectar si es una etiqueta de campo
                        label_info = self._extract_label_info(line_text, line_bbox, avg_font_size)
                        if label_info:
                            labels_found.append(label_info)
            
            # Asociar etiquetas con líneas horizontales
            for label_info in labels_found:
                label_text, label_bbox = label_info
                label_x0, label_y0, label_x1, label_y1 = label_bbox
                
                # Estrategia 1: Buscar línea a la derecha (mismo nivel vertical)
                closest_line = self._find_closest_line(
                    label_bbox, all_lines, search_right=True, search_below=False
                )
                
                # Estrategia 2: Si no hay línea a la derecha, buscar línea debajo
                if not closest_line:
                    closest_line = self._find_closest_line_below(label_bbox, all_lines)
                
                # Si encontramos una línea, usar sus coordenadas EXACTAS
                if closest_line:
                    line_x0, line_x1, line_y = closest_line
                    field_x = line_x0
                    # NO hacer ajustes aquí - pdf_generator.py hará la conversión correcta
                    # line_y es la posición de la línea desde el TOP de la página (PyMuPDF)
                    field_y = line_y  # Usar la coordenada Y de la línea directamente
                    field_w = line_x1 - line_x0
                    field_h = 20  # Altura estándar del campo
                else:
                    # Si no hay línea, estimar posición basada en la etiqueta
                    field_x = label_x1 + 5
                    field_y = label_y0
                    field_w = 150
                    field_h = label_y1 - label_y0
                
                field_type = self._determine_field_type(label_text)
                
                field_info = {
                    'label': label_text,
                    'type': field_type,
                    'abs_pos': {
                        'x': field_x,
                        'y': field_y,
                        'w': field_w,
                        'h': field_h,
                        'page': page_num
                    },
                    'column': 'full',
                    'options': [],
                    'required': False,
                    'validation': 'Ninguno'
                }
                fields.append(field_info)
        
        return fields
    
    def _detect_horizontal_lines_pymupdf(self, page: fitz.Page, debug=False) -> List[Tuple[float, float, float]]:
        """
        Detecta líneas horizontales usando PyMuPDF (para líneas vectoriales).
        
        Args:
            page: Página de PyMuPDF
            
        Returns:
            Lista de tuplas (x0, x1, y) representando líneas horizontales
        """
        lines = []
        paths = page.get_drawings()
        tolerance = 3  # Tolerancia para considerar una línea como horizontal
        
        for path in paths:
            items = path.get('items', [])
            for item in items:
                if item[0] == 'l':  # Línea
                    p1, p2 = item[1], item[2]
                    # Línea horizontal (Y similar)
                    if abs(p1.y - p2.y) < tolerance:
                        y = (p1.y + p2.y) / 2
                        x0, x1 = min(p1.x, p2.x), max(p1.x, p2.x)
                        # Solo líneas con longitud razonable (mínimo 30 puntos)
                        if x1 - x0 > 30:
                            lines.append((x0, x1, y))
                elif item[0] == 're':  # Rectángulo
                    # Algunos formularios usan rectángulos muy delgados como líneas
                    rect = item[1]
                    if rect.height < 3 and rect.width > 30:  # Rectángulo horizontal delgado
                        lines.append((rect.x0, rect.x1, rect.y1))
        
        return lines
    
    def _detect_horizontal_lines_opencv(self, page: fitz.Page) -> List[Tuple[float, float, float]]:
        """
        Detecta líneas horizontales usando OpenCV (para líneas rasterizadas/dibujadas).
        """
        try:
            # Reducimos a 100 DPI para mayor velocidad (suficiente para detectar líneas)
            target_dpi = 100
            zoom = target_dpi / 72.0
            
            # Limitar dimensiones máximas para evitar consumo masivo de memoria
            rect = page.rect
            if rect.width * zoom > 2500 or rect.height * zoom > 2500:
                zoom = 2500 / max(rect.width, rect.height)

            mat = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), annots=False)
            img_data = mat.tobytes("png")
            
            # Convertir a formato OpenCV
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return []
            
            # Convertir a escala de grises
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Aplicar umbral adaptativo para mejorar la detección
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Detectar bordes
            edges = cv2.Canny(thresh, 50, 150, apertureSize=3)
            
            # Detectar líneas usando HoughLinesP
            lines_detected = cv2.HoughLinesP(
                edges, 
                rho=1, 
                theta=np.pi/180, 
                threshold=100,
                minLineLength=50,  # Longitud mínima de línea
                maxLineGap=10      # Gap máximo entre segmentos
            )
            
            if lines_detected is None:
                return []
            
            # Filtrar solo líneas horizontales y convertir coordenadas
            horizontal_lines = []
            scale_factor = page.rect.width / img.shape[1]  # Factor de escala imagen->PDF
            
            for line in lines_detected:
                x1, y1, x2, y2 = line[0]
                
                # Verificar si es horizontal (diferencia Y pequeña)
                if abs(y2 - y1) < 5:  # Tolerancia de 5 píxeles
                    # Convertir coordenadas de imagen a coordenadas PDF
                    pdf_x0 = min(x1, x2) * scale_factor
                    pdf_x1 = max(x1, x2) * scale_factor
                    pdf_y = ((y1 + y2) / 2) * scale_factor
                    
                    # Solo líneas con longitud razonable
                    if pdf_x1 - pdf_x0 > 30:
                        horizontal_lines.append((pdf_x0, pdf_x1, pdf_y))
            
            return horizontal_lines
            
        except Exception as e:
            print(f"Error en detección OpenCV: {e}")
            return []
    
    def _merge_detected_lines(
        self, 
        vector_lines: List[Tuple[float, float, float]], 
        opencv_lines: List[Tuple[float, float, float]]
    ) -> List[Tuple[float, float, float]]:
        """
        Combina líneas detectadas por PyMuPDF y OpenCV, eliminando duplicados.
        
        Args:
            vector_lines: Líneas detectadas por PyMuPDF
            opencv_lines: Líneas detectadas por OpenCV
            
        Returns:
            Lista combinada sin duplicados
        """
        all_lines = vector_lines + opencv_lines
        
        if not all_lines:
            return []
        
        # Eliminar duplicados de forma eficiente (O(n log n))
        # Ordenar por Y para comparar solo con líneas en la misma altura
        all_lines.sort(key=lambda l: l[2])
        
        merged = []
        tolerance_y = 4  # Tolerancia vertical
        tolerance_x = 10  # Tolerancia horizontal
        
        for line in all_lines:
            x0, x1, y = line
            is_duplicate = False
            
            # Solo retroceder en merged para comparar con líneas cercanas en Y
            # Como merged también estará (parcialmente) ordenado por Y, buscamos solo los últimos
            for i in range(len(merged) - 1, -1, -1):
                ex0, ex1, ey = merged[i]
                
                # Si nos alejamos demasiado en Y, ya no habrá duplicados
                if y - ey > tolerance_y:
                    break
                
                # Verificar si es duplicado (misma posición Y y X similar)
                if abs(y - ey) < tolerance_y and abs(x0 - ex0) < tolerance_x and abs(x1 - ex1) < tolerance_x:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                merged.append(line)
        
        return merged
    
    def _find_closest_line(
        self, 
        label_bbox: Tuple[float, float, float, float], 
        lines: List[Tuple[float, float, float]],
        search_right: bool = True,
        search_below: bool = True
    ) -> Optional[Tuple[float, float, float]]:
        """
        Encuentra la línea más cercana a una etiqueta.
        
        Args:
            label_bbox: Bounding box de la etiqueta (x0, y0, x1, y1)
            lines: Lista de líneas detectadas
            search_right: Buscar líneas a la derecha de la etiqueta
            search_below: Buscar líneas debajo de la etiqueta
            
        Returns:
            Línea más cercana o None
        """
        label_x0, label_y0, label_x1, label_y1 = label_bbox
        label_center_y = (label_y0 + label_y1) / 2
        
        closest_line = None
        min_distance = float('inf')
        
        for line in lines:
            line_x0, line_x1, line_y = line
            
            # Calcular distancia vertical
            vertical_distance = abs(line_y - label_center_y)
            
            # Verificar condiciones de búsqueda
            is_right = line_x0 >= label_x0 - 10 if search_right else True
            is_below = line_y >= label_y0 - 5 if search_below else True
            
            # La línea debe estar cerca verticalmente
            if vertical_distance < 25 and is_right and is_below:
                # Calcular distancia total (combinando vertical y horizontal)
                horizontal_distance = max(0, line_x0 - label_x1)
                total_distance = vertical_distance + horizontal_distance * 0.5
                
                if total_distance < min_distance:
                    min_distance = total_distance
                    closest_line = line
        
        return closest_line
    
    def _find_closest_line_below(
        self, 
        label_bbox: Tuple[float, float, float, float], 
        lines: List[Tuple[float, float, float]]
    ) -> Optional[Tuple[float, float, float]]:
        """
        Encuentra la línea más cercana que está DEBAJO de una etiqueta.
        Útil para formularios donde la línea está debajo del texto de la etiqueta.
        
        Args:
            label_bbox: Bounding box de la etiqueta (x0, y0, x1, y1)
            lines: Lista de líneas detectadas
            
        Returns:
            Línea más cercana debajo o None
        """
        label_x0, label_y0, label_x1, label_y1 = label_bbox
        
        closest_line = None
        min_distance = float('inf')
        
        for line in lines:
            line_x0, line_x1, line_y = line
            
            # La línea debe estar DEBAJO de la etiqueta
            if line_y < label_y1:
                continue
            
            # Calcular distancia vertical (solo hacia abajo)
            vertical_distance = line_y - label_y1
            
            # Solo considerar líneas que están relativamente cerca (máximo 30 puntos abajo)
            if vertical_distance > 30:
                continue
            
            # La línea debe tener cierta superposición horizontal con la etiqueta
            # o estar cerca horizontalmente
            horizontal_overlap = min(line_x1, label_x1) - max(line_x0, label_x0)
            horizontal_distance = 0 if horizontal_overlap > 0 else min(
                abs(line_x0 - label_x1),
                abs(line_x1 - label_x0)
            )
            
            # Priorizar líneas que están directamente debajo
            if horizontal_distance < 50:  # Máximo 50 puntos de distancia horizontal
                total_distance = vertical_distance + horizontal_distance * 0.3
                
                if total_distance < min_distance:
                    min_distance = total_distance
                    closest_line = line
        
        return closest_line
    
    def _extract_label_info(self, text: str, bbox: Tuple[float, float, float, float], font_size: float = 0) -> Optional[Tuple[str, Tuple]]:
        """
        Extrae información de etiqueta si el texto parece ser una etiqueta de campo.
        Detecta tanto etiquetas con ':' como encabezados de tabla.
        
        Args:
            text: Texto a analizar
            bbox: Bounding box del texto
            font_size: Tamaño de fuente promedio del texto
            
        Returns:
            Tupla (label_text, bbox) o None
        """
        text = text.strip()
        
        # CASO 1: Etiquetas tradicionales que contienen ':'
        # Pueden ser "Nombre:" o "Nombre: (aclaración)"
        if ':' in text:
            # Extraer la parte antes de los dos puntos
            label = text.split(':')[0].strip()
            
            # Filtros básicos
            if not label or len(label) < 2 or len(label) > 60:
                return None
            
            # Excluir textos muy largos (más de 8 palabras son probablemente instrucciones)
            palabras = label.split()
            if len(palabras) > 8:
                return None
            
            # Si tiene paréntesis en la etiqueta misma, extraer solo la parte antes
            if '(' in label:
                label = label.split('(')[0].strip()
                if not label or len(label) < 2:
                    return None
            
            # Excluir si tiene paréntesis de cierre sin apertura (como "fiscales)")
            if ')' in label and '(' not in text.split(':')[0]:
                return None
            
            # Excluir títulos de sección muy comunes
            titulos_seccion = ['datos personales', 'datos fiscales', 'documentación solicitada', 
                              'información básica', 'información adicional', 'documentos requeridos']
            if label.lower() in titulos_seccion:
                return None
            
            # Palabras clave comunes de campos - siempre aceptar
            palabras_clave_campos = [
                'nombre', 'apellido', 'apellidos', 'email', 'correo', 'teléfono', 'telefono', 
                'móvil', 'movil', 'dni', 'nif', 'nie', 'fecha', 'sexo', 'edad', 'dirección', 
                'direccion', 'ciudad', 'provincia', 'país', 'pais', 'cp', 'código', 'codigo',
                'iban', 'cuenta', 'banco', 'empresa', 'cargo', 'puesto', 'departamento', 'n iban', 'seguridad social'
            ]
            
            label_lower = label.lower()
            for palabra_clave in palabras_clave_campos:
                if palabra_clave in label_lower:
                    return (label, bbox)  # Aceptar directamente
            
            return (label, bbox)
        
        # CASO 2: Encabezados de tabla y etiquetas sin ':' (como "Nombre", "Apellidos", etc.)
        else:
            label = text.strip()
            
            # Filtros básicos
            if not label or len(label) < 2 or len(label) > 25:
                return None
            
            # Máximo 4 palabras (encabezados son concisos)
            palabras = label.split()
            if len(palabras) > 4:
                return None
            
            # Excluir números solos o símbolos
            if label.isdigit() or len(label) == 1:
                return None
            
            # Excluir textos con paréntesis
            if '(' in label or ')' in label:
                return None
            
            # Excluir fragmentos de palabras (sufijos comunes)
            sufijos_excluir = ['ción', 'ducción', 'miento', 'mente', 'idad', 'ción.', 'ducción.', 'miento.']
            label_sin_punto = label.rstrip('.')
            if label.lower() in sufijos_excluir or label_sin_punto.lower() in sufijos_excluir:
                return None
            if label_sin_punto.lower().endswith('ción') and len(label_sin_punto) < 10:
                return None
            
            # Excluir palabras comunes que no son campos
            palabras_excluir = ['de', 'la', 'el', 'los', 'las', 'en', 'con', 'para', 'por', 'se', 'debe', 'y', 'o']
            if label.lower() in palabras_excluir:
                return None
            
            # IMPORTANTE: Permitir palabras clave comunes de campos incluso si no cumplen otros filtros
            # Esto asegura que "Nombre", "Apellidos", "Email", etc. siempre se detecten
            palabras_clave_campos = [
                'nombre', 'apellido', 'apellidos', 'email', 'correo', 'teléfono', 'telefono', 
                'móvil', 'movil', 'dni', 'nif', 'nie', 'fecha', 'sexo', 'edad', 'dirección', 
                'direccion', 'ciudad', 'provincia', 'país', 'pais', 'cp', 'código', 'codigo',
                'iban', 'cuenta', 'banco', 'empresa', 'cargo', 'puesto', 'departamento'
            ]
            
            # Si contiene una palabra clave, aceptar directamente
            label_lower = label.lower()
            for palabra_clave in palabras_clave_campos:
                if palabra_clave in label_lower:
                    return (label, bbox)
            
            # Si no es palabra clave, aplicar filtros de tamaño de fuente
            # Fuente pequeña a mediana (típica de encabezados de tabla y etiquetas)
            if font_size > 0:  # Solo aplicar si tenemos info de fuente
                if font_size > 14 or font_size < 5:
                    return None
            
            return (label, bbox)
    
    def _determine_field_type(self, text: str) -> str:
        """
        Determina el tipo de campo basado en el texto de la etiqueta.
        
        Args:
            text: Texto de la etiqueta
            
        Returns:
            Tipo de campo ('text', 'date', 'email', etc.)
        """
        text_lower = text.lower()
        
        # Verificar cada patrón
        for field_type, pattern in self.PATTERNS.items():
            if re.search(pattern, text_lower):
                # Mapear a tipos de la aplicación
                if field_type == 'nombre':
                    return 'text'
                elif field_type == 'email':
                    return 'text'
                elif field_type == 'telefono':
                    return 'text'
                elif field_type == 'fecha':
                    return 'date'
                elif field_type == 'dni':
                    return 'text'
                else:
                    return 'text'
        
        return 'text'
    
    def _detect_title(self, doc: fitz.Document) -> Optional[str]:
        """
        Detecta el título del documento.
        
        Args:
            doc: Documento PyMuPDF
            
        Returns:
            Título detectado o None
        """
        # Intentar obtener metadata
        metadata_title = doc.metadata.get('title')
        if metadata_title:
            return metadata_title
        
        # Buscar el texto más grande en la primera página
        if len(doc) > 0:
            page = doc[0]
            text_dict = page.get_text("dict")
            
            max_size = 0
            title_text = None
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Bloque de texto
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = span.get("size", 0)
                            text = span.get("text", "").strip()
                            
                            if size > max_size and len(text) > 5:
                                max_size = size
                                title_text = text
            
            return title_text
        
        return None
    
    def _map_widget_type(self, widget_type: int) -> str:
        """
        Mapea el tipo de widget de PyMuPDF al tipo de campo de la aplicación.
        
        Args:
            widget_type: Tipo de widget de PyMuPDF
            
        Returns:
            Tipo de campo de la aplicación
        """
        # Tipos de widget de PyMuPDF:
        # PDF_WIDGET_TYPE_BUTTON = 1
        # PDF_WIDGET_TYPE_CHECKBOX = 2
        # PDF_WIDGET_TYPE_RADIOBUTTON = 3
        # PDF_WIDGET_TYPE_TEXT = 4
        # PDF_WIDGET_TYPE_LISTBOX = 5
        # PDF_WIDGET_TYPE_COMBOBOX = 6
        # PDF_WIDGET_TYPE_SIGNATURE = 7
        
        type_map = {
            1: 'checkbox',  # Button
            2: 'checkbox',
            3: 'radio',
            4: 'text',
            5: 'dropdown',
            6: 'dropdown',
            7: 'signature'
        }
        
        return type_map.get(widget_type, 'text')
