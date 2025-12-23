# Generador de PDF Editables

Aplicación profesional para crear y editar formularios PDF con campos editables.

## Características

- ✅ Creación de formularios PDF desde cero
- ✅ Importación de PDFs existentes con detección automática de campos
- ✅ Detección inteligente de líneas y etiquetas
- ✅ Soporte para múltiples tipos de campos (texto, fecha, checkbox, dropdown, etc.)
- ✅ Vista previa en tiempo real
- ✅ Exportación a múltiples formatos

## Estructura del Proyecto

```
GENERADOR DE PDF EDITABLES/
├── src/
│   ├── core/                 # Lógica principal
│   │   ├── document_analyzer.py
│   │   ├── pdf_generator.py
│   │   ├── pdf_generator_simple.py
│   │   └── preview_generator.py
│   ├── ui/                   # Interfaz gráfica
│   │   ├── app_pdf_generator.py
│   │   └── app_ui_dialogs.py
│   └── utils/                # Utilidades
│       ├── app_data_manager.py
│       └── templates_manager.py
├── tests/                    # Tests
│   └── test_pdf_analysis.py
├── config/                   # Configuración
├── main.py                   # Punto de entrada
└── README.md
```

## Instalación

```powershell
# Instalar dependencias
.\instalar_dependencias.ps1
```

## Uso

```powershell
# Ejecutar la aplicación
python main.py
```

## Dependencias

- Python 3.8+
- PyMuPDF (fitz)
- OpenCV
- ReportLab
- PyPDF
- Pillow
- tkinter

## Versión

2.0.0 - Refactorización completa con estructura profesional

## Autor

Grupo Copicanarias
