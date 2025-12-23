"""
Modelos y Configuración por Defecto - PDF Master Pro
"""

import customtkinter as ctk

# Tipos de campos permitidos y sus etiquetas visuales
FIELD_TYPES = ["Texto", "Fecha", "Checkbox", "Dropdown", "Radio Buttons", "Multilínea", "Firma", "Número", "Sección"]

# Mapeo de tipos de CustomTkinter a tipos de PDF internos
TYPE_MAP = {
    "Texto": "text", "Fecha": "date", "Checkbox": "checkbox",
    "Dropdown": "dropdown", "Radio Buttons": "radio",
    "Multilínea": "multiline", "Firma": "signature", "Número": "number",
    "Sección": "section"
}

# Configuración Visual por defecto
DEFAULT_CONFIG_VISUAL = {
    'primary_color': '#2E86C1',
    'text_color': '#2C3e50',
    'font_name': 'Helvetica',
    'font_size_label': 12,
    'font_size_title': 18,
    'spacing': 70,
    'logo_position': {'x': 50, 'y': 30},
    'alignment': 'Izquierda',
    'bg_pdf_path': None
}

# Configuración de Email por defecto
DEFAULT_CONFIG_EMAIL = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': '587',
    'sender_email': '',
    'sender_password': '',
    'subject': 'REVISIÓN DE DOCUMENTACIÓN: FORMULARIO GENERADO',
    'body': 'Hola,\n\nAdjuntamos el formulario PDF generado mediante nuestro sistema.\n\nSaludos.'
}

# Estilos comunes para widgets del sidebar
STYLE_SB_ENTRY = {"fg_color": ("#FFFFFF", "#1A1A1B"), "border_color": ("#D1D1D6", "#2C2C2E"), 
                  "corner_radius": 10, "text_color": ("black", "white")}

STYLE_SB_TEXTBOX = {"fg_color": ("#FFFFFF", "#1A1A1B"), "text_color": ("black", "white")}

STYLE_SB_MENU = {"fg_color": ("#FFFFFF", "#2C2C2E"), "button_color": ("#D1D1D6", "#2C2C2E"), 
                 "button_hover_color": ("#C7C7CC", "#3A3A3C"), "corner_radius": 10, "text_color": ("black", "white")}

STYLE_SB_BTN = {"fg_color": ("#D1D1D6", "#2C2C2E"), "hover_color": ("#C7C7CC", "#3A3A3C"), 
                 "corner_radius": 10, "text_color": ("black", "white")}

# Iconos para secciones colapsables
ICON_EXPANDED = "▼"
ICON_COLLAPSED = "▶"
