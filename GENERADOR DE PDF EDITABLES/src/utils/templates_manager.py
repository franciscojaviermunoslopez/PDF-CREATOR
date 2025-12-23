import json
import os

PREDEFINED_TEMPLATES = {
    "Formulario de inscripción": [
        {"label": "NOMBRE Y APELLIDOS:", "type": "text"},
        {"label": "DNI / NIE:", "type": "text"},
        {"label": "EMAIL:", "type": "text"},
        {"label": "TELÉFONO:", "type": "number"},
        {"label": "CURSO:", "type": "dropdown", "options": ["Python Básico", "Diseño Web", "Excel Avanzado"]},
        {"label": "Fecha:", "type": "date"}
    ],
    "Contrato básico": [
        {"label": "NOMBRE DEL CLIENTE:", "type": "text"},
        {"label": "DNI / CIF:", "type": "text"},
        {"label": "DESCRIPCIÓN DEL SERVICIO:", "type": "multiline"},
        {"label": "FECHA DE FIRMA:", "type": "date"},
        {"label": "FIRMA DEL CLIENTE:", "type": "signature"}
    ],
    "Hoja de registro": [
        {"label": "FECHA:", "type": "date"},
        {"label": "NOMBRE VISITANTE:", "type": "text"},
        {"label": "EMPRESA:", "type": "text"},
        {"label": "MOTIVO DE LA VISITA:", "type": "text"},
        {"label": "HORA DE ENTRADA:", "type": "number"},
        {"label": "FIRMA:", "type": "signature"}
    ],
    "Formulario de contacto": [
        {"label": "NOMBRE:", "type": "text"},
        {"label": "EMAIL:", "type": "text"},
        {"label": "ASUNTO:", "type": "dropdown", "options": ["Soporte", "Ventas", "Otro"]},
        {"label": "MENSAJE:", "type": "multiline"},
        {"label": "FECHA:", "type": "date"}
    ],
    "Registro Avanzado (Muestra)": [
        {"label": "DATOS PERSONALES", "type": "section"},
        {"label": "Nombre Completo", "type": "text", "column": "1"},
        {"label": "DNI / NIE", "type": "text", "column": "2"},
        {"label": "DATOS DE CONTACTO", "type": "section"},
        {"label": "Correo Electrónico", "type": "text", "column": "full"},
        {"label": "Teléfono Móvil", "type": "number", "column": "1"},
        {"label": "Ciudad", "type": "text", "column": "2"},
        {"label": "PREFERENCIAS", "type": "section"},
        {"label": "¿Deseas recibir noticias?", "type": "checkbox", "options": ["Sí"]},
        {"label": "Frecuencia", "type": "dropdown", "options": ["Semanal", "Mensual"], "logic": "7|Sí"}
    ]
}

def save_template(name, fields, visual_config, extra_images, folder="templates"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    clean_fields = []
    for f in fields:
        # Guardamos todo el diccionario del campo para no perder propiedades nuevas (columnas, lógica, etc)
        clean_fields.append(f)
        
    data = {
        "fields": clean_fields,
        "visual_config": visual_config,
        "extra_images": extra_images
    }
    
    path = os.path.join(folder, f"{name}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return path

def load_custom_template(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Soporte para formato antiguo si existe
        if isinstance(data, list):
            return {"fields": data, "visual_config": {}, "extra_images": []}
        
        # Asegurar que existan todas las claves
        if "fields" not in data: data["fields"] = []
        if "visual_config" not in data: data["visual_config"] = {}
        if "extra_images" not in data: data["extra_images"] = []
        
        return data

def list_custom_templates(folder="templates"):
    if not os.path.exists(folder):
        return []
    return [f.replace(".json", "") for f in os.listdir(folder) if f.endswith(".json")]
