from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, ArrayObject, TextStringObject, NumberObject, BooleanObject
import os

def generar_pdf(output_path, titulo, campos, logo_path=None, config_visual=None, extra_images=None, bg_pdf_path=None):
    """
    Genera un PDF editable basado en la configuración con soporte multi-página.
    
    Si detecta campos importados (con abs_pos) y un PDF de fondo, usa el generador
    simplificado que mantiene el PDF original y solo añade campos.
    """
    # MODO NORMAL: Generación completa (soporta background PDF y posiciones absolutas)
    print("[PDF GEN] Generando PDF...")
    
    if not config_visual:
        config_visual = {
            'primary_color': '#2E86C1',
            'text_color': '#2C3e50',
            'font_name': 'Helvetica',
            'font_size_label': 12,
            'font_size_title': 18,
            'spacing': 60
        }

    primary_color_hex = config_visual.get('primary_color', '#2E86C1')
    primary_color = colors.HexColor(primary_color_hex)
    text_color = colors.HexColor(config_visual.get('text_color', '#2C3e50'))
    font_main = config_visual.get('font_name', 'Helvetica')
    font_bold = f"{font_main}-Bold" if font_main in ['Helvetica', 'Times', 'Courier'] else font_main
    size_label = config_visual.get('font_size_label', 12)
    size_title = config_visual.get('font_size_title', 18)
    spacing_base = config_visual.get('spacing', 60)

    pdf_buffer = BytesIO()
    
    # --- DETECCION DE TAMAÑO DE PAGINA ---
    width, height = letter # Default
    bg_reader = None
    if bg_pdf_path and os.path.exists(bg_pdf_path):
        try:
            bg_reader = PdfReader(bg_pdf_path)
            if len(bg_reader.pages) > 0:
                box = bg_reader.pages[0].mediabox
                width = float(box.width)
                height = float(box.height)
                print(f"[PDF GEN] Detectado tamaño de fondo: {width}x{height}")
        except Exception as e:
            print(f"Error detectando tamaño de fondo: {e}")

    c = canvas.Canvas(pdf_buffer, pagesize=(width, height))
    current_page_idx = 0

    def dibujar_cabecera(canvas_obj, pagenum):
        # Dibujar Logo
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                img_w, img_h = img.getSize()
                aspect = img_h / float(img_w)
                logo_pos = config_visual.get('logo_position', {'x': 50, 'y': 30})
                logo_x = logo_pos.get('x', 50)
                logo_y_from_top = logo_pos.get('y', 30)
                max_logo_w, max_logo_h = 180, 100
                display_width = min(max_logo_w, img_w)
                display_height = display_width * aspect
                if display_height > max_logo_h:
                    display_height = max_logo_h
                    display_width = display_height / aspect

                real_y = height - logo_y_from_top - display_height
                canvas_obj.drawImage(img, logo_x, real_y, width=display_width, height=display_height, mask='auto')
            except Exception as e:
                print(f"Error logo: {e}")

        # Título y Página con Alineación
        canvas_obj.setFont(font_bold, size_title)
        canvas_obj.setFillColor(primary_color)
        display_title = titulo if pagenum == 0 else f"{titulo} (Cont.)"
        
        align = config_visual.get('alignment', 'Izquierda')
        if align == 'Centro':
            canvas_obj.drawCentredString(width / 2, height - 70, display_title)
        elif align == 'Derecha':
            canvas_obj.drawRightString(width - 50, height - 70, display_title)
        else: # Izquierda
            canvas_obj.drawString(50, height - 70, display_title)
        
        # Línea decorativa eliminada para lienzo en blanco
        # canvas_obj.setStrokeColor(primary_color)
        # canvas_obj.setLineWidth(2)
        # canvas_obj.line(50, height - 100, width - 50, height - 100)

    # Inicializar primera página
    dibujar_cabecera(c, current_page_idx)
    
    # Dibujar Imágenes Extras (Solo en la primera página por defecto)
    if extra_images:
        for img_data in extra_images:
            img_p = img_data.get('path')
            if img_p and os.path.exists(img_p):
                try:
                    img_x = img_data.get('x', 50)
                    img_y_from_top = img_data.get('y', 200)
                    img_w = img_data.get('w', 100)
                    img_h = img_data.get('h', 100)
                    real_y = height - img_y_from_top - img_h
                    c.drawImage(ImageReader(img_p), img_x, real_y, width=img_w, height=img_h, mask='auto')
                except: pass

    # Layout Setup
    start_y = height - 140
    current_y = start_y
    campos_info_acroform = []
    col_width = (width - 100) / 2

    for idx, campo in enumerate(campos):
        # DETECCIÓN DE SALTO DE PÁGINA
        # Margen inferior de seguridad (60-80px)
        if current_y < 120 and campo.get('type') != 'section':
            c.showPage()
            current_page_idx += 1
            dibujar_cabecera(c, current_page_idx)
            current_y = height - 140

        label = campo['label']
        tipo = campo.get('type', 'text')
        col_type = campo.get('column', 'full')
        
        # --- POSICIONAMIENTO ABSOLUTO ---
        abs_pos = campo.get('abs_pos') # {'x', 'y', 'w', 'h', 'page'} en pts
        if abs_pos:
            target_page_idx = abs_pos.get('page', 0)
            # Si el campo es para una página futura, saltar páginas si es necesario
            while current_page_idx < target_page_idx:
                c.showPage()
                current_page_idx += 1
                dibujar_cabecera(c, current_page_idx)
            
            field_x = abs_pos['x']
            field_w = abs_pos['w']
            field_h = abs_pos['h']
            
            # CONVERSIÓN DE COORDENADAS PyMuPDF -> ReportLab
            # PyMuPDF: Y=0 está ARRIBA, abs_pos['y'] es la posición de la LÍNEA desde arriba
            # ReportLab: Y=0 está ABAJO
            # 
            # La línea está en abs_pos['y'] desde el top
            # En ReportLab, esa línea está en: height - abs_pos['y']
            # El campo debe dibujarse CON LA LÍNEA EN EL BOTTOM del campo
            # Por lo tanto, field_bottom_y = height - abs_pos['y']
            field_bottom_y = height - abs_pos['y']
            
            # DEBUG: Imprimir coordenadas
            print(f"[PDF GEN] Campo absoluto:")
            print(f"  PyMuPDF: x={abs_pos['x']}, y={abs_pos['y']}, w={field_w}, h={field_h}")
            print(f"  Altura página: {height}")
            print(f"  ReportLab bottom_y: {field_bottom_y}")
            
            # current_y_field es la coordenada Y base para dibujar
            # Queremos que la línea esté en el bottom del campo
            current_y_field = field_bottom_y
            print(f"  current_y_field: {current_y_field}")
        else:
            if col_type == '1':
                field_x, field_w = 50, col_width - 10
            elif col_type == '2':
                field_x, field_w = 50 + col_width + 10, col_width - 10
            else:
                field_x, field_w = 50, width - 100
            current_y_field = current_y - 20 # Ajuste estándar
            field_h = 20

        is_required = campo.get('required', False)
        if is_required and tipo != 'section':
            c.setFont(font_bold, size_label)
            c.setFillColor(colors.red)
            c.drawString(field_x - 10, current_y_field + 5, "*")

        validation = campo.get('validation', 'Ninguno')

        if tipo == 'section':
            if not abs_pos and current_y < 180: # Más espacio para secciones
                c.showPage()
                current_page_idx += 1
                dibujar_cabecera(c, current_page_idx)
                current_y = height - 140
            
            if not abs_pos and col_type == '1': current_y -= spacing_base
            c.setFont(font_bold, size_title - 2)
            c.setFillColor(primary_color)
            c.drawString(field_x if abs_pos else 50, current_y_field if abs_pos else current_y - 20, label.upper())
            c.setStrokeColor(primary_color)
            c.setLineWidth(1)
            c.line(field_x if abs_pos else 50, (current_y_field if abs_pos else current_y - 20) - 5, width - 50, (current_y_field if abs_pos else current_y - 20) - 5)
            if not abs_pos: current_y -= 45
            continue

        base_field_info = {'page': current_page_idx, 'required': is_required}

        if tipo == 'date':
            c.setFont(font_bold, size_label)
            c.setFillColor(text_color)
            c.drawString(field_x, current_y_field + 5, label)
            # Dibujar líneas de fecha
            c.line(field_x + 50, current_y_field - 15, field_x + 80, current_y_field - 15)
            c.drawString(field_x + 85, current_y_field - 15, "/")
            c.line(field_x + 95, current_y_field - 15, field_x + 125, current_y_field - 15)
            c.drawString(field_x + 130, current_y_field - 15, "/")
            c.line(field_x + 140, current_y_field - 15, field_x + 190, current_y_field - 15)
            dv = str(campo.get('default_value', ''))
            d, m, y = dv.split('/') if '/' in dv and dv.count('/') == 2 else ('', '', '')
            campos_info_acroform.append({**base_field_info, 'name': f"date_{idx}_d", 'rect': [field_x + 50, current_y_field - 15, field_x + 80, current_y_field + 5], 'type': 'Tx', 'default_value': d})
            campos_info_acroform.append({**base_field_info, 'name': f"date_{idx}_m", 'rect': [field_x + 95, current_y_field - 15, field_x + 125, current_y_field + 5], 'type': 'Tx', 'default_value': m})
            campos_info_acroform.append({**base_field_info, 'name': f"date_{idx}_y", 'rect': [field_x + 140, current_y_field - 15, field_x + 190, current_y_field + 5], 'type': 'Tx', 'default_value': y})
            if not abs_pos and col_type != '1': current_y -= spacing_base

        elif tipo == 'checkbox':
            c.rect(field_x, current_y_field - field_h + 3, field_h - 2 if abs_pos else 18, field_h - 2 if abs_pos else 18)
            c.setFont(font_bold, size_label)
            c.setFillColor(text_color)
            c.drawString(field_x + 25, current_y_field - 10, label)
            campos_info_acroform.append({**base_field_info, 'name': f"check_{idx}", 'rect': [field_x, current_y_field - 15, field_x + 18, current_y_field + 3], 'type': 'Btn', 'default_value': campo.get('default_value', '')})
            if not abs_pos and col_type != '1': current_y -= (spacing_base * 0.7)

        elif tipo == 'dropdown':
            c.setFont(font_bold, size_label)
            c.setFillColor(text_color)
            c.drawString(field_x, current_y_field + 5, label)
            c.rect(field_x, current_y_field - 20, field_w, field_h)
            campos_info_acroform.append({**base_field_info, 'name': f"drop_{idx}", 'rect': [field_x, current_y_field - 20, field_x + field_w, current_y_field], 'type': 'Ch', 'options': campo.get('options', []), 'default_value': campo.get('default_value', '')})
            if not abs_pos and col_type != '1': current_y -= spacing_base

        elif tipo == 'multiline':
            c.setFont(font_bold, size_label)
            c.setFillColor(text_color)
            c.drawString(field_x, current_y_field + 5, label)
            h_multi = field_h if abs_pos else 60
            c.rect(field_x, current_y_field - h_multi, field_w, h_multi)
            campos_info_acroform.append({**base_field_info, 'name': f"multi_{idx}", 'rect': [field_x, current_y_field - h_multi, field_x + field_w, current_y_field], 'type': 'Tx', 'multiline': True, 'default_value': campo.get('default_value', '')})
            if not abs_pos and col_type != '1': current_y -= (spacing_base + 40)

        elif tipo == 'signature':
            c.setFont(font_bold, size_label)
            c.setFillColor(text_color)
            c.drawString(field_x, current_y_field + 5, label)
            h_sig = field_h if abs_pos else 45
            line_y = current_y_field - h_sig
            c.setDash(1, 2)
            c.line(field_x, line_y, field_x + field_w, line_y)
            c.setDash()
            campos_info_acroform.append({**base_field_info, 'name': f"sig_{idx}", 'rect': [field_x, line_y, field_x + field_w, line_y + h_sig], 'type': 'Sig'})
            if not abs_pos and col_type != '1': current_y -= (spacing_base + 25)

        elif tipo == 'number':
            c.setFont(font_bold, size_label)
            c.setFillColor(text_color)
            c.drawString(field_x, current_y_field + 5, label)
            c.line(field_x, current_y_field - 15, field_x + field_w, current_y_field - 15)
            campos_info_acroform.append({**base_field_info, 'name': f"num_{idx}", 'rect': [field_x, current_y_field - 15, field_x + field_w, current_y_field + 5], 'type': 'Tx', 'default_value': campo.get('default_value', ''), 'validation': 'Numérico'})
            if not abs_pos and col_type != '1': current_y -= spacing_base
            
        else: # Texto Normal
            c.setFont(font_bold, size_label)
            c.setFillColor(text_color)
            c.drawString(field_x, current_y_field + 5, label)
            c.line(field_x, current_y_field - 15, field_x + field_w, current_y_field - 15)
            campos_info_acroform.append({**base_field_info, 'name': f"f_{idx}", 'rect': [field_x, current_y_field - 15, field_x + field_w, current_y_field + 5], 'type': 'Tx', 'logic': campo.get('logic', ''), 'default_value': campo.get('default_value', ''), 'validation': validation})
            if not abs_pos and col_type != '1': current_y -= spacing_base

    c.save()
    pdf_buffer.seek(0)

    # PASO 2: AcroForm con pypdf y Mezcla de Fondo
    pdf_buffer.seek(0)
    reader = PdfReader(pdf_buffer)
    writer = PdfWriter()
    
    # El bg_reader ya fue cargado arriba para detectar el tamaño
    # (Ya no es necesario volver a cargarlo aquí si fue exitoso)

    for i, content_page in enumerate(reader.pages):
        if bg_reader:
            try:
                # Intentar mapear 1 a 1, o repetir la última página si el fondo es más corto
                bg_idx = i if i < len(bg_reader.pages) else len(bg_reader.pages) - 1
                bg_page = bg_reader.pages[bg_idx]
                
                # Fusionar fondo DEBAJO (over=False) del contenido generado
                # Nota: El contenido generado por ReportLab suele ser transparente
                content_page.merge_page(bg_page, over=False)
            except Exception as e:
                print(f"Error mezclando página {i}: {e}")
        
        writer.add_page(content_page)

    if "/AcroForm" not in writer.root_object:
        writer.root_object.update({NameObject("/AcroForm"): DictionaryObject()})
    acroform = writer.root_object["/AcroForm"]
    
    font_alias = "/F1"
    font_dict = DictionaryObject({NameObject(font_alias): DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject(f"/{font_main}"), NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})})
    acroform.update({NameObject("/DR"): DictionaryObject({NameObject("/Font"): font_dict}), NameObject("/DA"): TextStringObject(f"{font_alias} {size_label} Tf 0 g"), NameObject("/NeedAppearances"): BooleanObject(True), NameObject("/Fields"): ArrayObject()})

    real_names = [f['name'] for f in campos_info_acroform]

    for field in campos_info_acroform:
        target_page = writer.pages[field['page']]
        field_dict = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject(f"/{field['type']}"),
            NameObject("/T"): TextStringObject(field['name']),
            NameObject("/Rect"): ArrayObject([NumberObject(x) for x in field['rect']]),
            NameObject("/F"): NumberObject(4),
            NameObject("/P"): target_page.indirect_reference
        })

        # Lógica (AcroJS)
        aa_dict = DictionaryObject()
        logic = field.get('logic', '')
        if logic and "|" in logic:
            try:
                t_idx, t_val = logic.split("|")
                trigger_name = real_names[int(t_idx)]
                js = f'var t=this.getField("{trigger_name}"); if(t.value=="{t_val}"||(t.type=="checkbox"&&t.value!="Off")){{event.target.display=display.visible;}}else{{event.target.display=display.hidden;}}'
                aa_dict.update({NameObject("/C"): DictionaryObject({NameObject("/S"): NameObject("/JavaScript"), NameObject("/JS"): TextStringObject(js)})})
            except: pass

        val_type = field.get('validation', 'Ninguno')
        if val_type != 'Ninguno':
            js_v = ""
            if val_type == 'Email': js_v = 'var re=/^[\\w-\\.]+@([\\w-]+\\.)+[\\w-]{2,4}$/; if(event.value&&!re.test(event.value)){{app.alert("Email incorrecto"); event.rc=false;}}'
            elif val_type == 'DNI/NIE': js_v = 'var re=/^[XYZ0-9][0-9]{7}[TRWAGMYFPDXBNJZSQVHLCKE]$/i; if(event.value&&!re.test(event.value)){{app.alert("DNI inválido"); event.rc=false;}}'
            elif val_type == 'Teléfono': js_v = 'var re=/^(\\+34|0034|34)?[6789]\\d{8}$/; if(event.value&&!re.test(event.value)){{app.alert("Teléfono inválido"); event.rc=false;}}'
            elif val_type == 'Numérico': js_v = 'if(event.value&&isNaN(event.value.replace(",","."))){{app.alert("Debe ser numérico"); event.rc=false;}}'
            if js_v: aa_dict.update({NameObject("/V"): DictionaryObject({NameObject("/S"): NameObject("/JavaScript"), NameObject("/JS"): TextStringObject(js_v)})})

        if aa_dict: field_dict.update({NameObject("/AA"): aa_dict})

        ff = 0
        if field.get('required'): ff |= 2
        default_val = field.get('default_value', '')

        if field['type'] == 'Tx':
            field_dict.update({NameObject("/DA"): TextStringObject(f"{font_alias} {size_label} Tf 0 g")})
            if default_val: field_dict.update({NameObject("/V"): TextStringObject(str(default_val))})
            if field.get('multiline'): ff |= 4096
            field_dict.update({NameObject("/Ff"): NumberObject(ff)})
        elif field['type'] == 'Ch':
            opts = field.get('options', [])
            val = default_val if default_val in opts else (opts[0] if opts else "")
            field_dict.update({NameObject("/Opt"): ArrayObject([TextStringObject(o) for o in opts]), NameObject("/DA"): TextStringObject(f"{font_alias} {size_label} Tf 0 g"), NameObject("/V"): TextStringObject(val), NameObject("/Ff"): NumberObject(ff | 131072)})
        elif field['type'] == 'Btn':
            if field.get('radio'):
                is_selected = str(default_val).strip().lower() == str(field['opt_val']).strip().lower()
                field_dict.update({NameObject("/V"): NameObject(f"/{field['opt_val']}"), NameObject("/AS"): NameObject(f"/{field['opt_val']}" if is_selected else "/Off"), NameObject("/Ff"): NumberObject(ff | 32768 | 49152)})
            else:
                is_on = str(default_val).lower() in ['yes', 'true', '1', 'on', 'si', 'sí', 'x']
                field_dict.update({NameObject("/V"): NameObject("/Yes" if is_on else "/Off"), NameObject("/AS"): NameObject("/Yes" if is_on else "/Off"), NameObject("/Ff"): NumberObject(ff), NameObject("/MK"): DictionaryObject({NameObject("/CA"): TextStringObject("4")})})

        field_ref = writer._add_object(field_dict)
        if "/Annots" not in target_page: target_page[NameObject("/Annots")] = ArrayObject()
        target_page["/Annots"].append(field_ref)
        acroform["/Fields"].append(field_ref)

    writer.write(output_path)
    print(f"✅ PDF multi-página: {output_path}")
