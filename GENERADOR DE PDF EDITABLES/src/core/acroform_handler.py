"""
Manejador de AcroForm - Importación Directa de Campos PDF

Este módulo maneja la importación directa de campos AcroForm desde PDFs existentes,
eliminando la necesidad de detección automática fallida.

Características:
- Extracción de campos AcroForm existentes
- Conversión a formato interno de la aplicación
- Preservación de todas las propiedades del campo
"""

from pypdf import PdfReader
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AcroFormHandler:
    """Manejador para importar y procesar campos AcroForm de PDFs"""
    
    def __init__(self, pdf_path: str):
        """
        Inicializa el manejador con un PDF.
        
        Args:
            pdf_path: Ruta al archivo PDF
        """
        self.pdf_path = pdf_path
        self.reader = PdfReader(pdf_path)
        self.has_acroform = "/AcroForm" in self.reader.root_object
        
    def extract_fields(self) -> List[Dict]:
        """
        Extrae todos los campos AcroForm del PDF.
        
        Returns:
            Lista de campos con sus propiedades
        """
        if not self.has_acroform:
            logger.info(f"PDF {self.pdf_path} no tiene campos AcroForm")
            return []
        
        fields = []
        acroform = self.reader.root_object["/AcroForm"]
        
        if "/Fields" not in acroform:
            return []
        
        for field_ref in acroform["/Fields"]:
            field_obj = field_ref.get_object()
            field_data = self._extract_field_data(field_obj)
            if field_data:
                fields.append(field_data)
        
        logger.info(f"Extraídos {len(fields)} campos de {self.pdf_path}")
        return fields
    
    def _extract_field_data(self, field_obj) -> Optional[Dict]:
        """
        Extrae los datos de un campo AcroForm individual.
        
        Args:
            field_obj: Objeto de campo PDF
            
        Returns:
            Diccionario con datos del campo o None si no se puede extraer
        """
        try:
            # Nombre del campo
            field_name = field_obj.get("/T", "")
            if isinstance(field_name, bytes):
                field_name = field_name.decode('utf-8', errors='ignore')
            else:
                field_name = str(field_name)
            
            # Tipo de campo
            field_type = self._get_field_type(field_obj)
            
            # Rectángulo (posición y tamaño)
            rect = field_obj.get("/Rect")
            if not rect:
                return None
            
            # Página
            page_num = self._get_field_page(field_obj)
            
            # Valor por defecto
            default_value = self._get_field_value(field_obj)
            
            # Opciones (para dropdowns y radio buttons)
            options = self._get_field_options(field_obj)
            
            # Requerido
            is_required = self._is_field_required(field_obj)
            
            return {
                'label': field_name,
                'type': field_type,
                'abs_pos': {
                    'x': float(rect[0]),
                    'y': float(rect[1]),
                    'w': float(rect[2]) - float(rect[0]),
                    'h': float(rect[3]) - float(rect[1]),
                    'page': page_num
                },
                'default_value': default_value,
                'options': options,
                'required': is_required,
                'column': 'full'
            }
        except Exception as e:
            logger.error(f"Error extrayendo campo: {e}")
            return None
    
    def _get_field_type(self, field_obj) -> str:
        """Determina el tipo de campo"""
        ft = field_obj.get("/FT")
        if not ft:
            return "text"
        
        ft_str = str(ft)
        
        # Mapeo de tipos PDF a tipos internos
        type_map = {
            "/Tx": "text",      # Text field
            "/Btn": "checkbox", # Button (checkbox/radio)
            "/Ch": "dropdown",  # Choice (dropdown/listbox)
            "/Sig": "signature" # Signature
        }
        
        field_type = type_map.get(ft_str, "text")
        
        # Detectar multilínea
        if field_type == "text":
            ff = field_obj.get("/Ff", 0)
            if isinstance(ff, int) and (ff & 4096):  # Multiline flag
                field_type = "multiline"
        
        return field_type
    
    def _get_field_page(self, field_obj) -> int:
        """Obtiene el número de página del campo"""
        try:
            page_ref = field_obj.get("/P")
            if page_ref:
                for i, page in enumerate(self.reader.pages):
                    if page.indirect_reference == page_ref:
                        return i
        except:
            pass
        return 0
    
    def _get_field_value(self, field_obj) -> str:
        """Obtiene el valor por defecto del campo"""
        value = field_obj.get("/V", "")
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='ignore')
        return str(value) if value else ""
    
    def _get_field_options(self, field_obj) -> List[str]:
        """Obtiene las opciones para campos de selección"""
        options = []
        opt = field_obj.get("/Opt")
        if opt:
            for item in opt:
                if isinstance(item, bytes):
                    options.append(item.decode('utf-8', errors='ignore'))
                else:
                    options.append(str(item))
        return options
    
    def _is_field_required(self, field_obj) -> bool:
        """Determina si el campo es requerido"""
        ff = field_obj.get("/Ff", 0)
        if isinstance(ff, int):
            return bool(ff & 2)  # Required flag
        return False
    
    def get_page_dimensions(self, page_num: int = 0) -> Tuple[float, float]:
        """
        Obtiene las dimensiones de una página.
        
        Args:
            page_num: Número de página
            
        Returns:
            Tupla (ancho, alto) en puntos
        """
        if page_num < len(self.reader.pages):
            page = self.reader.pages[page_num]
            box = page.mediabox
            return (float(box.width), float(box.height))
        return (612.0, 792.0)  # Letter por defecto


def import_pdf_fields(pdf_path: str) -> Tuple[List[Dict], bool]:
    """
    Función de conveniencia para importar campos de un PDF.
    
    Args:
        pdf_path: Ruta al PDF
        
    Returns:
        Tupla (lista de campos, tiene_campos_acroform)
    """
    handler = AcroFormHandler(pdf_path)
    fields = handler.extract_fields()
    return fields, handler.has_acroform
