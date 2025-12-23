"""
Caché de Previsualizaciones - Optimización de Rendimiento

Este módulo implementa un sistema de caché para previsualizaciones de PDF,
mejorando dramáticamente el rendimiento de la aplicación.

Características:
- Caché en memoria de imágenes renderizadas
- Lazy loading de páginas
- Gestión automática de memoria
"""
import os
# Silenciar MuPDF
os.environ['FITZ_LOG_LEVEL'] = '0'

import fitz  # PyMuPDF
from PIL import Image
import io
import threading
from typing import Optional, Callable, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Silenciar errores y advertencias de la librería MuPDF (C/C++)
try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.set_mupdf_warnings(False)
except:
    pass


class PreviewCache:
    """Caché inteligente para previsualizaciones de PDF"""
    
    def __init__(self, max_cache_size: int = 50):
        """
        Inicializa el caché.
        
        Args:
            max_cache_size: Número máximo de páginas en caché
        """
        self.cache: Dict[str, Image.Image] = {}
        self.max_cache_size = max_cache_size
        self.access_order = []
        self.lock = threading.Lock()
    
    def get_preview(
        self, 
        pdf_path: str, 
        page_num: int = 0, 
        dpi: int = 150,
        force_refresh: bool = False
    ) -> Optional[Image.Image]:
        """
        Obtiene una vista previa de una página PDF.
        
        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página
            dpi: Resolución de renderizado
            force_refresh: Forzar re-renderizado
            
        Returns:
            Imagen PIL o None si hay error
        """
        cache_key = f"{pdf_path}_{page_num}_{dpi}"
        
        with self.lock:
            # Verificar caché
            if not force_refresh and cache_key in self.cache:
                # Actualizar orden de acceso
                if cache_key in self.access_order:
                    self.access_order.remove(cache_key)
                self.access_order.append(cache_key)
                
                logger.debug(f"Cache HIT: {cache_key}")
                return self.cache[cache_key]
        
        # Renderizar nueva imagen
        logger.debug(f"Cache MISS: {cache_key} - Renderizando...")
        image = self._render_page(pdf_path, page_num, dpi)
        
        if image:
            with self.lock:
                # Añadir al caché
                self.cache[cache_key] = image
                self.access_order.append(cache_key)
                
                # Limpiar caché si está lleno
                self._cleanup_cache()
        
        return image
    
    def get_preview_async(
        self,
        pdf_path: str,
        page_num: int,
        callback: Callable[[Optional[Image.Image]], None],
        dpi: int = 150
    ):
        """
        Obtiene una vista previa de forma asíncrona.
        
        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página
            callback: Función a llamar con la imagen
            dpi: Resolución de renderizado
        """
        def render_and_callback():
            image = self.get_preview(pdf_path, page_num, dpi)
            callback(image)
        
        thread = threading.Thread(target=render_and_callback, daemon=True)
        thread.start()
    
    def _render_page(
        self, 
        pdf_path: str, 
        page_num: int, 
        dpi: int
    ) -> Optional[Image.Image]:
        """
        Renderiza una página PDF a imagen.
        
        Args:
            pdf_path: Ruta al PDF
            page_num: Número de página
            dpi: Resolución
            
        Returns:
            Imagen PIL o None
        """
        try:
            doc = fitz.open(pdf_path)
            
            if page_num >= len(doc):
                logger.error(f"Página {page_num} no existe en {pdf_path}")
                return None
            
            page = doc[page_num]
            
            # Calcular zoom para DPI deseado
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            # Renderizar (Evitamos annots=True para prevenir errores de 'appearance stream')
            pix = page.get_pixmap(matrix=mat, alpha=False, annots=False)
            
            # Convertir a PIL Image
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            
            doc.close()
            
            return image
            
        except Exception as e:
            logger.error(f"Error renderizando {pdf_path} página {page_num}: {e}")
            return None
    
    def _cleanup_cache(self):
        """Limpia el caché si excede el tamaño máximo"""
        while len(self.cache) > self.max_cache_size:
            # Eliminar el elemento menos recientemente usado
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.cache:
                del self.cache[oldest_key]
                logger.debug(f"Cache cleanup: Eliminado {oldest_key}")
    
    def clear(self):
        """Limpia todo el caché"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            logger.info("Caché limpiado completamente")
    
    def get_cache_stats(self) -> Dict:
        """Obtiene estadísticas del caché"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_cache_size,
                'keys': list(self.cache.keys())
            }


# Instancia global del caché
_global_cache = PreviewCache()


def get_pdf_preview(
    pdf_path: str, 
    page_num: int = 0, 
    dpi: int = 150
) -> Optional[Image.Image]:
    """
    Función de conveniencia para obtener vista previa con caché global.
    
    Args:
        pdf_path: Ruta al PDF
        page_num: Número de página
        dpi: Resolución
        
    Returns:
        Imagen PIL o None
    """
    return _global_cache.get_preview(pdf_path, page_num, dpi)


def get_pdf_preview_async(
    pdf_path: str,
    page_num: int,
    callback: Callable[[Optional[Image.Image]], None],
    dpi: int = 150
):
    """
    Función de conveniencia para obtener vista previa asíncrona.
    
    Args:
        pdf_path: Ruta al PDF
        page_num: Número de página
        callback: Función a llamar con la imagen
        dpi: Resolución
    """
    _global_cache.get_preview_async(pdf_path, page_num, callback, dpi)


def clear_preview_cache():
    """Limpia el caché global de previsualizaciones"""
    _global_cache.clear()
