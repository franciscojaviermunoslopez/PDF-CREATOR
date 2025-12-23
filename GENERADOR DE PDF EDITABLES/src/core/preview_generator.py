from PIL import Image, ImageDraw, ImageFont
import os

def generar_preview_imagen(titulo, campos, logo_path=None, width_px=1200, config_visual=None, extra_images=None, bg_images=None, pdf_dims=None):
    """
    Genera una imagen PIL de alta resolución para la vista previa.
    """
    if not config_visual:
        config_visual = {
            'primary_color': '#2E86C1',
            'text_color': '#2C3e50',
            'font_name': 'Helvetica',
            'font_size_label': 12,
            'font_size_title': 18,
            'spacing': 70
        }
    # --- DETECCIÓN DE TAMAÑO DE PÁGINA ---
    if pdf_dims:
        page_w_pts, page_h_pts = pdf_dims
    elif bg_images and len(bg_images) > 0:
        bw, bh = bg_images[0].size
        # Fallback si no hay pdf_dims: asumir ancho Letter y calcular alto
        page_w_pts = 612.0
        page_h_pts = (bh / float(bw)) * 612.0
    else:
        page_w_pts, page_h_pts = 612.0, 792.0

    print(f"[PREVIEW] Usando base: {page_w_pts}x{page_h_pts} pts")
    scale = width_px / page_w_pts
    spacing_base = config_visual.get('spacing', 70)
    
    # Calcular Altura Necesaria Dinámicamente
    total_y_pts = 140 # Margen superior
    for campo in campos:
        tipo = campo.get('type', 'text')
        col = campo.get('column', 'full')
        if col == '2': continue 
        
        if tipo == 'section': total_y_pts += 50
        elif tipo == 'radio': total_y_pts += (len(campo.get('options', ['1','2'])) * 25 + spacing_base)
        elif tipo == 'multiline': total_y_pts += (spacing_base + 60)
        elif tipo == 'signature': total_y_pts += (spacing_base + 40)
        else: total_y_pts += spacing_base
    
    # Altura mínima de una página
    min_height_pts = page_h_pts
    height_pts = max(min_height_pts, total_y_pts + 100)
    height_px = int(height_pts * scale)
    
    img = Image.new('RGB', (width_px, height_px), color='white')
    draw = ImageDraw.Draw(img)
    
    # Pegar fondo PDF si existe
    if bg_images:
        for p, bg_img in enumerate(bg_images):
            py = int(p * page_h_pts * scale)
            if py < height_px:
                # Redimensionar fondo para ajustar al ancho del preview
                bg_w, bg_h = bg_img.size
                ratio = width_px / float(bg_w)
                target_h = int(bg_h * ratio)
                
                bg_resized = bg_img.resize((width_px, target_h), Image.Resampling.LANCZOS)
                img.paste(bg_resized, (0, py))

    # Dibujar indicadores de salto de página (líneas discontinuas cada page_h_pts)
    for p in range(1, int(height_pts // page_h_pts) + 1):
        py = int(p * page_h_pts * scale)
        for x in range(0, width_px, 20):
            draw.line([(x, py), (x+10, py)], fill=(200, 200, 200), width=1)
        draw.text((10, py - 20), f"Fin de Página {p}", fill=(180, 180, 180), font=ImageFont.load_default())

    # Indicador de PDF de fondo
    bg_pdf = config_visual.get('bg_pdf_path')
    if bg_pdf:
        bg_name = os.path.basename(bg_pdf)
        draw.text((10, 10), f"✓ FONDO PDF ACTIVO: {bg_name}", fill=(52, 199, 89), font=ImageFont.load_default())
    
    # Mapeo simple de nombres de fuentes de PDF a archivos de sistema (aproximación)
    font_files = {
        'Helvetica': 'arial.ttf',
        'Times': 'times.ttf',
        'Courier': 'cour.ttf'
    }
    font_file = font_files.get(config_visual.get('font_name', 'Helvetica'), 'arial.ttf')
    font_file_bold = font_file.replace('.ttf', 'bd.ttf') if 'arial' in font_file else font_file # Simplificación
    
    size_label = int(config_visual.get('font_size_label', 12) * scale)
    size_title = int(config_visual.get('font_size_title', 18) * scale)
    spacing_base = config_visual.get('spacing', 70)

    try:
        font_main_file = font_files.get(config_visual.get('font_name', 'Helvetica'), 'arial.ttf')
        font_bold = ImageFont.truetype(font_main_file.replace('.ttf', 'bd.ttf') if 'arial' in font_main_file else font_main_file, size_title)
        font_label = ImageFont.truetype(font_main_file, size_label)
        font_small = ImageFont.truetype(font_main_file, int(size_label * 0.8))
    except:
        font_bold = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_small = ImageFont.load_default()

    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    primary_color = hex_to_rgb(config_visual.get('primary_color', '#2E86C1'))
    text_color = hex_to_rgb(config_visual.get('text_color', '#2C3e50'))

    # Logo
    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path)
            # Leer posición desde config
            logo_pos = config_visual.get('logo_position', {'x': 50, 'y': 30})
            lx = int(logo_pos.get('x', 50) * scale)
            ly = int(logo_pos.get('y', 30) * scale)
            
            logo_img.thumbnail((int(180 * scale), int(100 * scale)), Image.Resampling.LANCZOS)
            img.paste(logo_img, (lx, ly))
        except: pass

    # Dibujar Imágenes Extras
    if extra_images:
        for img_data in extra_images:
            img_p = img_data.get('path')
            if img_p and os.path.exists(img_p):
                try:
                    ext_img = Image.open(img_p)
                    # Convertir coordenadas PDF (puntos) a píxeles de Preview
                    # x, y, w, h en puntos (612x792)
                    img_x = int(img_data.get('x', 50) * scale)
                    img_y = int(img_data.get('y', 200) * scale)
                    img_w = int(img_data.get('w', 100) * scale)
                    img_h = int(img_data.get('h', 100) * scale)
                    
                    ext_img.thumbnail((img_w, img_h), Image.Resampling.LANCZOS)
                    img.paste(ext_img, (img_x, img_y))
                except Exception as e:
                    print(f"Error cargando imagen extra en preview: {e}")

    # Título con Alineación
    align = config_visual.get('alignment', 'Izquierda')
    title_y = int(70 * scale)
    if align == 'Centro':
        draw.text((width_px // 2, title_y), titulo, fill=primary_color, font=font_bold, anchor="mm")
    elif align == 'Derecha':
        draw.text((width_px - int(50 * scale), title_y), titulo, fill=primary_color, font=font_bold, anchor="rm")
    else: # Izquierda
        draw.text((int(50 * scale), title_y), titulo, fill=primary_color, font=font_bold, anchor="lm")
        
    # draw.line([(int(50 * scale), int(100 * scale)), (width_px - int(50 * scale), int(100 * scale))], fill=primary_color, width=int(2 * scale))

    # Campos
    current_y = 140
    col_width_pts = (612 - 100) / 2
    col_width_px = int(col_width_pts * scale)

    for idx, campo in enumerate(campos):
        label = campo['label']
        tipo = campo.get('type', 'text')
        col_type = campo.get('column', 'full') # 'full', '1', '2'
        
        abs_pos = campo.get('abs_pos')
        if abs_pos:
            field_x = int(abs_pos['x'] * scale)
            # Y absoluta en el preview = (puntos_acumulados_paginas + y_en_pagina) * scale
            page_offset_pts = abs_pos.get('page', 0) * page_h_pts
            field_y = int((page_offset_pts + abs_pos['y']) * scale)
            field_w = int(abs_pos['w'] * scale)
            label_y = field_y + int(5 * scale) # Etiqueta dentro del campo, cerca del top
        else:
            # Coordenadas X basadas en columna (flujo normal)
            if col_type == '1':
                field_x = int(50 * scale)
                field_w = col_width_px - int(10 * scale)
            elif col_type == '2':
                field_x = int(50 * scale) + col_width_px + int(10 * scale)
                field_w = col_width_px - int(10 * scale)
            else:
                field_x = int(50 * scale)
                field_w = width_px - int(100 * scale)

            y_scaled = int(current_y * scale)
            label_y = y_scaled + int(10 * scale)
            field_y = y_scaled + int(35 * scale)

        if tipo == 'section':
            if col_type == '1': current_y += spacing_base
            text_y = y_scaled + int(20 * scale)
            draw.text((int(50 * scale), text_y), label.upper(), fill=primary_color, font=font_bold)
            draw.line([(int(50 * scale), text_y + int(25 * scale)), (width_px - int(50 * scale), text_y + int(25 * scale))], fill=primary_color, width=int(1 * scale))
            current_y += 45
            continue

        if tipo == 'date':
            draw.text((field_x, label_y), label, fill=text_color, font=font_label)
            for i, offset_pts in enumerate([50, 95, 140]):
                off_x = field_x + int(offset_pts * scale)
                draw.rectangle([off_x, field_y, off_x + int(30 * scale if i<2 else 50 * scale), field_y + int(20 * scale)], fill=(245, 250, 255))
                draw.line([(off_x, field_y + int(20 * scale)), (off_x + int(30 * scale if i<2 else 50 * scale), field_y + int(20 * scale))], fill='black')
                if i < 2: draw.text((off_x + int(35 * scale), field_y), "/", fill=text_color, font=font_small)
            if col_type != '1': current_y += spacing_base
        
        elif tipo == 'checkbox':
            draw.rectangle([field_x, label_y, field_x + int(18 * scale), label_y + int(18 * scale)], outline='black')
            draw.text((field_x + int(25 * scale), label_y), label, fill=text_color, font=font_label)
            if col_type != '1': current_y += (spacing_base * 0.7)
        
        elif tipo == 'dropdown':
            draw.text((field_x, label_y), label, fill=text_color, font=font_label)
            draw.rectangle([field_x, field_y, field_x + field_w, field_y + int(20 * scale)], outline=primary_color)
            if col_type != '1': current_y += spacing_base

        elif tipo == 'radio':
            draw.text((field_x, label_y), label, fill=text_color, font=font_label)
            options = campo.get('options', ['Opc 1', 'Opc 2'])
            for i, opt in enumerate(options):
                opt_y = field_y + (i * int(25 * scale))
                draw.ellipse([field_x + int(2 * scale), opt_y, field_x + int(14 * scale), opt_y + int(12 * scale)], outline='black')
                draw.text((field_x + int(20 * scale), opt_y), opt, fill=text_color, font=font_small)
            if col_type != '1': current_y += (len(options) * 25 + spacing_base)

        elif tipo == 'multiline':
            draw.text((field_x, label_y), label, fill=text_color, font=font_label)
            draw.rectangle([field_x, field_y, field_x + field_w, field_y + int(60 * scale)], outline='black', fill=(250, 252, 255))
            if col_type != '1': current_y += (spacing_base + 40)

        elif tipo == 'signature':
            draw.text((field_x, label_y), label, fill=text_color, font=font_label)
            line_y = field_y + int(40 * scale)
            draw.line([(field_x, line_y), (field_x + field_w, line_y)], fill='black', width=1)
            draw.text((field_x + int(5 * scale), line_y - int(15 * scale)), "(Firma Digital)", fill=(150, 150, 150), font=font_small)
            if col_type != '1': current_y += (spacing_base + 25)

        else: # Texto / Number
            draw.text((field_x, label_y), label, fill=text_color, font=font_label)
            draw.rectangle([field_x, field_y, field_x + field_w, field_y + int(20 * scale)], fill=(245, 250, 255), outline=(220, 230, 240))
            draw.line([(field_x, field_y + int(20 * scale)), (field_x + field_w, field_y + int(20 * scale))], fill=(100, 100, 100))
            if col_type != '1': current_y += spacing_base

    # Dibujar rectángulos visuales para campos absolutos (para facilitar selección)
    for idx, campo in enumerate(campos):
        abs_pos = campo.get('abs_pos')
        if abs_pos:
            field_x = int(abs_pos['x'] * scale)
            page_offset_pts = abs_pos.get('page', 0) * page_h_pts
            field_y = int((page_offset_pts + abs_pos['y']) * scale)
            field_w = int(abs_pos['w'] * scale)
            field_h = int(abs_pos['h'] * scale)
            
            # Dibujar rectángulo semi-transparente azul
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [field_x, field_y, field_x + field_w, field_y + field_h],
                fill=(0, 122, 255, 30),  # Azul semi-transparente
                outline=(0, 122, 255, 200),  # Borde azul
                width=2
            )
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    return img
