"""
Módulo core: Funcionalidad principal del generador PDF
"""

from .document_analyzer import DocumentAnalyzer
from .pdf_generator import generar_pdf

__all__ = ['DocumentAnalyzer', 'generar_pdf']
