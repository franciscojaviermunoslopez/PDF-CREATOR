"""
Generador de Campos para PDF usando PyMuPDF (fitz)
-------------------------------------------------
Este módulo utiliza PyMuPDF para añadir campos AcroForm.
A diferencia de pypdf, fitz genera automáticamente los streams de apariencia (/AP),
lo que garantiza que el texto sea visible en Adobe Acrobat y otros visores.
"""

import fitz
import os

def añadir_campos_a_pdf(input_pdf_path, output_pdf_path, campos):
    """
    Añade campos interactivos a un PDF existente usando PyMuPDF.
    
    Args:
        input_pdf_path: Ruta del PDF original
        output_pdf_path: Ruta donde guardar el PDF con campos
        campos: Lista de campos con formato:
            {
                'label': 'Nombre del campo',
                'type': 'text' | 'checkbox' | 'dropdown' | etc.,
                'abs_pos': {'x': float, 'y': float, 'w': float, 'h': float, 'page': int},
                'font_size': int,
                'options': []
            }
    """
    print(f"🚀 Usando PyMuPDF para generar PDF compatible con Adobe...")
    
    # Abrir el documento
    doc = fitz.open(input_pdf_path)
    
    # IMPORTANTE: No tocamos los campos existentes, PyMuPDF los mantiene por defecto
    # al usar doc.save() sin opciones de limpieza agresivas.
    
    for idx, campo in enumerate(campos):
        abs_pos = campo.get('abs_pos')
        if not abs_pos:
            continue
            
        page_idx = abs_pos.get('page', 0)
        if page_idx >= len(doc):
            page_idx = len(doc) - 1
            
        page = doc[page_idx]
        
        # Coordenadas (fitz usa el mismo sistema que el editor: 0,0 arriba a la izquierda)
        rect = fitz.Rect(
            abs_pos['x'], 
            abs_pos['y'], 
            abs_pos['x'] + abs_pos['w'], 
            abs_pos['y'] + abs_pos['h']
        )
        
        # Crear el widget (campo)
        widget = fitz.Widget()
        widget.rect = rect
        widget.field_name = f"field_{idx}_{idx}"
        widget.field_label = campo.get('label', f"Campo {idx}")
        
        # Configurar tipo
        tipo = campo.get('type', 'text')
        if tipo == 'checkbox':
            widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        elif tipo == 'dropdown':
            widget.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
            widget.field_values = campo.get('options', [])
        elif tipo == 'multiline':
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_flags |= fitz.PDF_TX_FIELD_MULTILINE
        else:
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            
        # Propiedades visuales
        font_size = campo.get('font_size', 12)
        if font_size <= 0: font_size = 12
        
        widget.text_fontsize = font_size
        widget.text_font = "Helv"
        widget.text_color = (0, 0, 0) # Negro
        
        # Añadir el widget a la página
        page.add_widget(widget)
        print(f"  - Añadido campo: {widget.field_label} (Tamaño: {font_size})")

    # Guardar el PDF
    # clean=True ayuda a que Adobe lo lea mejor
    doc.save(output_pdf_path, deflate=True, clean=True)
    doc.close()
    
    print(f"✅ PDF exportado con PyMuPDF: {output_pdf_path}")
