"""
Generador Simple de Campos para PDF
Solo añade campos interactivos a un PDF existente SIN modificar el contenido original.
"""

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, ArrayObject, TextStringObject, NumberObject, BooleanObject

def añadir_campos_a_pdf(input_pdf_path, output_pdf_path, campos):
    """
    Añade campos interactivos a un PDF existente SIN modificar el contenido.
    
    Args:
        input_pdf_path: Ruta del PDF original
        output_pdf_path: Ruta donde guardar el PDF con campos
        campos: Lista de campos con formato:
            {
                'label': 'Nombre del campo',
                'type': 'text' | 'checkbox' | 'dropdown' | etc.,
                'abs_pos': {'x': float, 'y': float, 'w': float, 'h': float, 'page': int},
                'options': [] (para dropdowns)
            }
    """
    
    # Leer PDF original
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    
    # Copiar todas las páginas tal cual
    for page in reader.pages:
        writer.add_page(page)
    
    # Obtener dimensiones de la primera página
    first_page = reader.pages[0]
    box = first_page.mediabox
    page_height = float(box.height)
    
    # Crear AcroForm si no existe
    if "/AcroForm" not in writer.root_object:
        writer.root_object.update({NameObject("/AcroForm"): DictionaryObject()})
    
    acroform = writer.root_object["/AcroForm"]
    
    # Configurar fuente con encoding Unicode para evitar problemas con espacios
    font_alias = "/F1"
    font_dict = DictionaryObject({
        NameObject(font_alias): DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica")
            # No especificar encoding, dejar que el visor use el por defecto
        })
    })
    
    acroform.update({
        NameObject("/DR"): DictionaryObject({NameObject("/Font"): font_dict}),
        NameObject("/DA"): TextStringObject(f"{font_alias} 12 Tf 0 g"),
        NameObject("/NeedAppearances"): BooleanObject(True),
        NameObject("/Fields"): ArrayObject()
    })
    
    # Añadir cada campo
    for idx, campo in enumerate(campos):
        abs_pos = campo.get('abs_pos')
        if not abs_pos:
            continue
        
        # Obtener página del campo
        page_idx = abs_pos.get('page', 0)
        if page_idx >= len(writer.pages):
            page_idx = len(writer.pages) - 1
        
        target_page = writer.pages[page_idx]
        
        # Convertir coordenadas: PyMuPDF (Y=0 arriba) -> PDF (Y=0 abajo)
        field_x = abs_pos['x']
        field_w = abs_pos['w']
        field_h = abs_pos['h']
        field_bottom_y = page_height - abs_pos['y']  # Línea inferior del campo
        
        # Rectángulo del campo [x1, y1, x2, y2]
        rect = [field_x, field_bottom_y - field_h, field_x + field_w, field_bottom_y]
        
        # Tipo de campo
        tipo = campo.get('type', 'text')
        field_type = "Tx"  # Por defecto texto
        
        # Mapear tipos a tipos de PDF
        if tipo in ['checkbox', 'radio']:
            field_type = "Btn"
        elif tipo == 'dropdown':
            field_type = "Ch"
        elif tipo == 'signature':
            field_type = "Sig"
        # date, number, multiline usan "Tx" (texto)
        
        # Nombre del campo - debe ser único y sin espacios (es interno, no se muestra)
        field_name = f"field_{idx}"
        
        # Obtener propiedades
        font_size = campo.get('font_size', 12)
        required = campo.get('required', False)
        validation = campo.get('validation', 'Ninguno')
        
        # Crear diccionario del campo
        field_dict = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject(f"/{field_type}"),
            NameObject("/T"): TextStringObject(field_name),
            NameObject("/Rect"): ArrayObject([NumberObject(x) for x in rect]),
            NameObject("/F"): NumberObject(4),
            NameObject("/P"): target_page.indirect_reference
        })
        
        # Configuración específica por tipo
        if field_type == "Tx":
            # Campos de texto (text, number, date, multiline)
            ff = 0
            if required:
                ff |= 2  # Required flag
            if tipo == 'multiline':
                ff |= 4096  # Multiline flag
            
            field_dict.update({
                NameObject("/DA"): TextStringObject(f"{font_alias} {font_size} Tf 0 g"),
                NameObject("/Ff"): NumberObject(ff),
                NameObject("/MaxLen"): NumberObject(1000)
            })
            
            # Validación JavaScript
            if validation != 'Ninguno' or tipo in ['number', 'date']:
                js_code = ""
                if tipo == 'number' or validation == 'Numérico':
                    js_code = 'if(event.value&&isNaN(event.value.replace(",","."))){app.alert("Debe ser numérico"); event.rc=false;}'
                elif validation == 'Email':
                    js_code = 'var re=/^[\\w-\\.]+@([\\w-]+\\.)+[\\w-]{2,4}$/; if(event.value&&!re.test(event.value)){app.alert("Email incorrecto"); event.rc=false;}'
                elif validation == 'DNI/NIE':
                    js_code = 'var re=/^[XYZ0-9][0-9]{7}[TRWAGMYFPDXBNJZSQVHLCKE]$/i; if(event.value&&!re.test(event.value)){app.alert("DNI inválido"); event.rc=false;}'
                elif validation == 'Teléfono':
                    js_code = 'var re=/^(\\+34|0034|34)?[6789]\\d{8}$/; if(event.value&&!re.test(event.value)){app.alert("Teléfono inválido"); event.rc=false;}'
                
                if js_code:
                    field_dict.update({
                        NameObject("/AA"): DictionaryObject({
                            NameObject("/V"): DictionaryObject({
                                NameObject("/S"): NameObject("/JavaScript"),
                                NameObject("/JS"): TextStringObject(js_code)
                            })
                        })
                    })
        
        elif field_type == "Ch":  # Dropdown
            options = campo.get('options', [])
            ff = 131072  # Combo box flag
            if required:
                ff |= 2
            
            field_dict.update({
                NameObject("/Opt"): ArrayObject([TextStringObject(o) for o in options]),
                NameObject("/DA"): TextStringObject(f"{font_alias} {font_size} Tf 0 g"),
                NameObject("/Ff"): NumberObject(ff)
            })
        
        elif field_type == "Btn":  # Checkbox o Radio
            ff = 0
            if required:
                ff |= 2
            if tipo == 'radio':
                ff |= 32768  # Radio button flag
            
            field_dict.update({
                NameObject("/V"): NameObject("/Off"),
                NameObject("/AS"): NameObject("/Off"),
                NameObject("/Ff"): NumberObject(ff),
                NameObject("/MK"): DictionaryObject({
                    NameObject("/CA"): TextStringObject("4")
                })
            })
        
        # Añadir campo a la página y al AcroForm
        field_ref = writer._add_object(field_dict)
        
        if "/Annots" not in target_page:
            target_page[NameObject("/Annots")] = ArrayObject()
        
        target_page["/Annots"].append(field_ref)
        acroform["/Fields"].append(field_ref)
    
    # Guardar PDF
    writer.write(output_pdf_path)
    print(f"✅ PDF con campos guardado: {output_pdf_path}")
