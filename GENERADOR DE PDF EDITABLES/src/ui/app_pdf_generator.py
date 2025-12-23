"""
PDF MASTER PRO - GENERADOR DE FORMULARIOS PDF EDITABLES
-------------------------------------------------------
Este módulo contiene la clase principal PDFGeneratorApp, que gestiona la UI y
la lógica de negocio para crear PDFs con campos AcroForm de alta calidad.

Características:
- Interfaz adaptativa (Modo Claro/Oscuro).
- Motor de previsualización en tiempo real.
- Sistema de plantillas persistentes.
- Generación masiva mediante CSV.
- Historial de documentos y sistema deshacer/rehacer.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageTk
import os
import csv
import io
from datetime import datetime
from src.core.pdf_generator import generar_pdf
from src.core.preview_generator import generar_preview_imagen
from src.utils.templates_manager import PREDEFINED_TEMPLATES, save_template, load_custom_template, list_custom_templates

# Nuevos módulos modularizados
from src.utils.app_models import *
from src.utils.app_data_manager import DataManager, ExportManager
from src.utils.app_email_logic import send_generated_pdf_email, test_smtp_connection
from src.ui.app_ui_dialogs import show_add_field_dialog, show_field_settings
from src.utils.app_pdf_utils import render_pdf_to_images, get_pdf_dimensions, map_import_type, map_type_to_internal
from src.core.document_analyzer import DocumentAnalyzer

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PDFGeneratorApp(ctk.CTkFrame):
    """
    Componente principal para la generación de formularios PDF editables con 
    interfaz premium adaptativa (Modo Claro/Oscuro).
    """
    def __init__(self, master, on_visual_editor_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_visual_editor_callback = on_visual_editor_callback
        
        # 1. Configuración básica del frame
        self._init_settings()
        
        # 2. Inicialización del estado interno y persistencia
        self._init_state()
        
        # 3. Construcción de la Interfaz de Usuario (UI) Adaptativa
        self._setup_main_layout()
        self._setup_sidebar()
        self._setup_editor_area()
        self._setup_preview_area()
        self._setup_keybindings()

        # 4. Carga inicial de datos y refresco visual
        self._load_initial_data()

    def _load_initial_data(self):
        """Carga los datos por defecto y el historial al arrancar."""
        # self.add_default_fields() # No cargar campos por defecto
        self.refresh_history_ui()
        self.update_preview()

    def _init_settings(self):
        """Configura los parámetros del frame y su grid."""
        # Grid principal del frame: Sidebar (0), Editor (1), Preview (2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _init_state(self):
        """Inicializa variables de control, historial y configuración visual."""
        self.after_id = None      # Para debouncing de vista previa
        self.logo_path = None     # Ruta del logo principal
        self.extra_images = []    # Imágenes adicionales: [{'path', 'x', 'y', 'w', 'h'}, ...]
        
        # Configuración Visual por Defecto (Look & Feel)
        self.config_visual = DEFAULT_CONFIG_VISUAL.copy()

        # Pilas para Deshacer / Rehacer
        self.undo_stack = []
        self.redo_stack = []
        self._block_state_capture = False

        # Gestor de Datos e Historial
        self.data_manager = DataManager()
        self.history = self.data_manager.history

        # Configuración de Email
        self.config_email = DEFAULT_CONFIG_EMAIL.copy()

        # Estado para Drag & Drop (Campos y Vista Previa)
        self._drag_data = {"widget": None, "y": 0, "index": None, "proxy": None}
        self._drag_preview = {"id": None, "type": None, "start_x": 0, "start_y": 0, "original_pos": (0, 0)}

        # Secciones colapsadas (guardamos el frame del row de la sección)
        self.collapsed_sections = set()

        # Cache de imágenes del PDF de fondo y dimensiones
        self.bg_images = []
        self.bg_pdf_dims = (612.0, 792.0) # Ancho, Alto en pts (Letter por defecto)
        self.design_mode = ctk.BooleanVar(value=False)

    def _setup_main_layout(self):
        """Establece los contenedores principales con colores adaptativos."""
        # Fondo dinámico (Silicon Valley en Claro / Black Edition en Oscuro)
        self.configure(fg_color=("#F5F5F7", "#0A0A0A"))
        
    def _setup_sidebar(self):
        """Construye el panel lateral y sus pestañas de configuración."""
        # Frame del Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, 
                                          fg_color=("#EBEBEF", "#0A0A0A"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1)

        # Logo / Título
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PDF MASTER", 
                                        font=ctk.CTkFont(size=22, weight="bold", family="Helvetica"),
                                        text_color=("black", "white"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Tabview Lateral (Estilo Uber/Apple Minimal Adaptive)
        self.sidebar_tabs = ctk.CTkTabview(self.sidebar_frame, width=260, corner_radius=10, 
                                           fg_color=("#EBEBEF", "#0A0A0A"),
                                           segmented_button_selected_color=("#FFFFFF", "#2C2C2E"),
                                           segmented_button_selected_hover_color=("#F5F5F7", "#3A3A3C"),
                                           segmented_button_unselected_color=("#EBEBEF", "#0A0A0A"),
                                           segmented_button_unselected_hover_color=("#D1D1D6", "#161617"),
                                           segmented_button_fg_color=("#EBEBEF", "#0A0A0A"))
        self.sidebar_tabs.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.sidebar_tabs._segmented_button.configure(font=ctk.CTkFont(size=11, weight="bold"),
                                                      text_color=("black", "white"))

        # Definición de Pestañas
        self.tab_config = self.sidebar_tabs.add("General")
        self.tab_visual = self.sidebar_tabs.add("Diseño")
        self.tab_images = self.sidebar_tabs.add("Imagen")
        self.tab_email = self.sidebar_tabs.add("Email")
        self.tab_templates = self.sidebar_tabs.add("Templ")
        self.tab_history = self.sidebar_tabs.add("Histo")
        self.tab_export = self.sidebar_tabs.add("Export")

        # Configuración de estilos para controles del sidebar
        self._setup_sidebar_controls()

    def _setup_sidebar_controls(self):
        """Configura los widgets dentro de cada pestaña del sidebar."""
        sb_entry = STYLE_SB_ENTRY
        sb_menu  = STYLE_SB_MENU
        sb_btn   = STYLE_SB_BTN

        # --- TAB: GENERAL ---
        ctk.CTkLabel(self.tab_config, text="Título del Formulario:", anchor="w", text_color=("black", "white")).pack(padx=10, pady=(10, 0), fill="x")
        self.title_entry = ctk.CTkEntry(self.tab_config, placeholder_text="Ej: DATOS...", **sb_entry)
        self.title_entry.pack(padx=10, pady=(0, 10), fill="x")
        self.title_entry.insert(0, "")
        self.title_entry.bind("<KeyRelease>", lambda e: self.request_preview_update())

        self.logo_btn = ctk.CTkButton(self.tab_config, text="Cambiar Logo", command=self.select_logo, **sb_btn)
        self.logo_btn.pack(padx=10, pady=10, fill="x")
        self.logo_preview_text = ctk.CTkLabel(self.tab_config, text="Sin logo", text_color="gray", font=ctk.CTkFont(size=10))
        self.logo_preview_text.pack(padx=10, pady=(0, 10))

        # Sección de fondo e importación eliminada como se pidió

        # --- TAB: DISEÑO (Visual) ---
        ctk.CTkLabel(self.tab_visual, text="Color Primario:", anchor="w", text_color=("black", "white")).pack(padx=10, pady=(10, 0), fill="x")
        self.color_btn = ctk.CTkButton(self.tab_visual, text="Seleccionar Color", 
                                       fg_color=self.config_visual['primary_color'], 
                                       hover_color=self.config_visual['primary_color'], 
                                       command=self.choose_color, corner_radius=10, text_color="white") # Texto blanco para botones coloridos
        self.color_btn.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(self.tab_visual, text="Tipografía:", anchor="w", text_color=("black", "white")).pack(padx=10, pady=(10, 0), fill="x")
        self.font_menu = ctk.CTkOptionMenu(self.tab_visual, values=["Helvetica", "Times", "Courier"], 
                                           command=self.change_visual_config, **sb_menu)
        self.font_menu.pack(padx=10, pady=(0, 10), fill="x")
        self.font_menu.set("Helvetica")

        ctk.CTkLabel(self.tab_visual, text="Espaciado (pt):", anchor="w", text_color=("black", "white")).pack(padx=10, pady=(10, 0), fill="x")
        self.spacing_slider = ctk.CTkSlider(self.tab_visual, from_=40, to=120, number_of_steps=8, 
                                            command=self.change_visual_config, 
                                            button_color=("#007AFF", "#FFFFFF"), button_hover_color=("#0056b3", "#E5E5EA"),
                                            fg_color=("#D1D1D6", "#2C2C2E"), progress_color=("#007AFF", "#555555"))
        self.spacing_slider.pack(padx=10, pady=(0, 10), fill="x")
        self.spacing_slider.set(70)

        ctk.CTkLabel(self.tab_visual, text="Tamaño Título / Etiqueta:", anchor="w", text_color=("black", "white")).pack(padx=10, pady=(10, 0), fill="x")
        self.size_frame = ctk.CTkFrame(self.tab_visual, fg_color="transparent")
        self.size_frame.pack(padx=10, fill="x")
        self.title_size_var = ctk.StringVar(value=str(self.config_visual['font_size_title']))
        self.title_size_menu = ctk.CTkOptionMenu(self.size_frame, values=["14", "16", "18", "20", "24", "28"], 
                                                 variable=self.title_size_var, command=self.change_visual_config, width=60, **sb_menu)
        self.title_size_menu.pack(side="left", padx=(0, 5))
        self.label_size_var = ctk.StringVar(value=str(self.config_visual['font_size_label']))
        self.label_size_menu = ctk.CTkOptionMenu(self.size_frame, values=["10", "11", "12", "14", "16"], 
                                                 variable=self.label_size_var, command=self.change_visual_config, width=60, **sb_menu)
        self.label_size_menu.pack(side="left")

        ctk.CTkLabel(self.tab_visual, text="Alineación:", anchor="w", text_color=("black", "white")).pack(padx=10, pady=(10, 0), fill="x")
        self.align_menu = ctk.CTkOptionMenu(self.tab_visual, values=["Izquierda", "Centro", "Derecha"], 
                                            command=self.change_visual_config, **sb_menu)
        self.align_menu.pack(padx=10, pady=(0, 10), fill="x")
        self.align_menu.set(self.config_visual.get('alignment', 'Izquierda'))

        ctk.CTkLabel(self.tab_visual, text="Tema de la App:", anchor="w", text_color=("black", "white")).pack(padx=10, pady=(10, 0), fill="x")
        self.theme_menu = ctk.CTkOptionMenu(self.tab_visual, values=["System", "Dark", "Light"], 
                                            command=lambda v: ctk.set_appearance_mode(v), **sb_menu)
        self.theme_menu.pack(padx=10, pady=(0, 10), fill="x")
        self.theme_menu.set("Dark")

        # --- TAB: IMÁGENES EXTRAS ---
        ctk.CTkLabel(self.tab_images, text="Añadir Imágenes (Firma, Sellos...)", 
                      font=ctk.CTkFont(size=11, weight="bold"), text_color=("black", "white")).pack(pady=5)
        self.add_img_btn = ctk.CTkButton(self.tab_images, text="+ Añadir Imagen", 
                                         command=self.add_extra_image, 
                                         fg_color="#34C759", hover_color="#28A745", # Apple Green
                                         text_color="#FFFFFF", corner_radius=10, font=ctk.CTkFont(weight="bold"))
        self.add_img_btn.pack(padx=10, pady=5, fill="x")
        
        self.images_scroll = ctk.CTkScrollableFrame(self.tab_images, height=300, 
                                                    fg_color=("#EBEBEF", "#0A0A0A"),
                                                    scrollbar_button_color="#2C2C2E",
                                                    scrollbar_button_hover_color="#3A3A3C")
        self.images_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # --- TAB: PLANTILLAS ---
        self.templates_scroll = ctk.CTkScrollableFrame(self.tab_templates, height=350, 
                                                       fg_color=("#EBEBEF", "#0A0A0A"),
                                                       scrollbar_button_color=("#D1D1D6", "#2C2C2E"),
                                                       scrollbar_button_hover_color=("#C7C7CC", "#3A3A3C"))
        self.templates_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_templates_list()

        self.save_tpl_btn = ctk.CTkButton(self.tab_templates, text="+ Guardar Actual", 
                                          command=self.save_current_as_template, 
                                          fg_color=("#D1D1D6", "#2C2C2E"), hover_color=("#C7C7CC", "#3A3A3C"),
                                          text_color=("black", "white"), corner_radius=10)
        self.save_tpl_btn.pack(padx=10, pady=10, fill="x")

        # --- TAB: EMAIL ---
        self._setup_email_tab()

        # --- TAB: EXPORTAR ---
        self._setup_export_tab()

    def _handle_visual_editor_click(self):
        """Maneja el clic en el botón de editor visual."""
        if self.on_visual_editor_callback:
            self.on_visual_editor_callback()
        else:
            messagebox.showinfo("Editor Visual", "Utiliza la pestaña 'Editor Visual' en la parte superior.")

    def _setup_email_tab(self):
        """Configura la pestaña de envío de correos electrónicos."""
        # Frame normal para evitar el scroll y ver todo de un vistazo
        container = ctk.CTkFrame(self.tab_email, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 1. Configuración Servidor
        ctk.CTkLabel(container, text="CONFIGURACIÓN SMTP", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#007AFF", "#007AFF")).pack(pady=(5, 2))
        
        self.smtp_entry = ctk.CTkEntry(container, placeholder_text="Servidor SMTP", corner_radius=10, border_width=1)
        self.smtp_entry.pack(padx=10, pady=2, fill="x")
        self.smtp_entry.insert(0, self.config_email.get('smtp_server', 'smtp.gmail.com'))
        
        port_user_frame = ctk.CTkFrame(container, fg_color="transparent")
        port_user_frame.pack(fill="x")
        
        self.port_entry = ctk.CTkEntry(port_user_frame, placeholder_text="Puerto", width=80, corner_radius=10, border_width=1)
        self.port_entry.grid(row=0, column=0, padx=(10, 5), pady=2)
        self.port_entry.insert(0, self.config_email.get('smtp_port', '587'))
        
        self.user_entry = ctk.CTkEntry(port_user_frame, placeholder_text="Tu Email", corner_radius=10, border_width=1)
        self.user_entry.grid(row=0, column=1, padx=(0, 10), pady=2, sticky="ew")
        port_user_frame.grid_columnconfigure(1, weight=1)

        self.pass_entry = ctk.CTkEntry(container, placeholder_text="Contraseña / App Token", show="*", corner_radius=10, border_width=1)
        self.pass_entry.pack(padx=10, pady=2, fill="x")
        
        # 2. Configuración Mensaje
        msg_area = ctk.CTkFrame(container, fg_color="transparent")
        msg_area.pack(fill="x", padx=10, pady=(15, 2))

        ctk.CTkLabel(msg_area, text="MENSAJE POR DEFECTO", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#007AFF", "#007AFF")).pack(pady=(0, 5))
        
        self.mail_to_entry = ctk.CTkEntry(msg_area, placeholder_text="Destinatario (Email)", corner_radius=10, border_width=1)
        self.mail_to_entry.pack(pady=2, fill="x")
        
        self.mail_sub_entry = ctk.CTkEntry(msg_area, placeholder_text="Asunto", corner_radius=10, border_width=1)
        self.mail_sub_entry.pack(pady=2, fill="x")
        self.mail_sub_entry.insert(0, self.config_email.get('subject', ''))
        
        # Altura compacta para evitar el desbordamiento
        self.mail_body_text = ctk.CTkTextbox(msg_area, height=130, corner_radius=12, border_width=1,
                                             fg_color=("#FFFFFF", "#252526"), text_color=("black", "white"),
                                             wrap="word", undo=True)
        self.mail_body_text.pack(pady=2, fill="x")
        self.mail_body_text.insert("1.0", self.config_email.get('body', ''))

        self.test_mail_btn = ctk.CTkButton(container, text="Guardar y Probar Conexión", 
                                           command=self._test_email_connection,
                                           fg_color=("#E5E5EA", "#2C2C2E"), hover_color=("#D1D1D6", "#3A3A3C"),
                                           text_color=("black", "white"), corner_radius=10)
        self.test_mail_btn.pack(padx=10, pady=(10, 10), fill="x")

    def _test_email_connection(self):
        """Intenta una conexión SMTP para validar los credenciales."""
        # Actualizar config desde UI
        self.config_email.update({
            'smtp_server': self.smtp_entry.get(),
            'smtp_port': self.port_entry.get(),
            'sender_email': self.user_entry.get(),
            'sender_password': self.pass_entry.get(),
            'subject': self.mail_sub_entry.get(),
            'body': self.mail_body_text.get("1.0", "end-1c")
        })
        
        ok, msg = test_smtp_connection(
            self.config_email['smtp_server'], 
            self.config_email['smtp_port'], 
            self.config_email['sender_email'], 
            self.config_email['sender_password']
        )
        if ok:
            messagebox.showinfo("Éxito", "Conexión SMTP exitosa. Credenciales correctos.")
        else:
            messagebox.showerror("Error SMTP", f"No se pudo conectar: {msg}")

    def _setup_export_tab(self):
        """Configura los widgets dentro de la pestaña de exportación."""
        export_container = ctk.CTkScrollableFrame(self.tab_export, 
                                                  fg_color=("#EBEBEF", "#0A0A0A"))
        export_container.pack(fill="both", expand=True)

        # 1. Card de Generación Masiva (Adaptativo - High Contrast)
        bulk_card = ctk.CTkFrame(export_container, corner_radius=12, border_width=1, 
                                 border_color=("#D1D1D6", "#2C2C2E"), fg_color=("#FFFFFF", "#131313"))
        bulk_card.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(bulk_card, text="📦 AUTOMATIZACIÓN", font=ctk.CTkFont(size=12, weight="bold"), 
                      text_color=("#2E86C1", "#5DADE2")).pack(pady=(10, 5))
        
        self.csv_btn = ctk.CTkButton(bulk_card, text="Generación Masiva (CSV)", 
                                     command=self.batch_generate_csv, 
                                     fg_color=("#F39C12", "#E67E22"), hover_color=("#E67E22", "#D35400"),
                                     height=35, corner_radius=8, font=ctk.CTkFont(weight="bold"),
                                     text_color="white") # Asegurar blanco en botón naranja
        self.csv_btn.pack(padx=20, pady=(0, 15), fill="x")

        # 2. Card de Otros Formatos (Adaptativo)
        format_card = ctk.CTkFrame(export_container, corner_radius=12, border_width=1, 
                                    border_color=("#D1D1D6", "#2C2C2E"), fg_color=("#FFFFFF", "#131313"))
        format_card.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(format_card, text="📄 OTROS FORMATOS", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        
        # Sub-contenedor para botones de exportar (Look minimalista Adaptativo)
        btn_style = {"fg_color": ("#E5E5EA", "#2C2C2E"), "text_color": ("black", "white"), "hover_color": ("#D1D1D6", "#3A3A3C")}
        
        self.exp_web_btn = ctk.CTkButton(format_card, text="Formulario Web (HTML)", 
                                         command=self.export_to_web, **btn_style)
        self.exp_web_btn.pack(padx=15, pady=5, fill="x")
        
        self.exp_word_btn = ctk.CTkButton(format_card, text="Formato Word (.doc)", 
                                          command=self.export_to_word, **btn_style)
        self.exp_word_btn.pack(padx=15, pady=5, fill="x")
        
        self.exp_excel_btn = ctk.CTkButton(format_card, text="Excel / CSV Structure", 
                                           command=self.export_to_excel, **btn_style)
        self.exp_excel_btn.pack(padx=15, pady=(5, 15), fill="x")

    def _setup_editor_area(self):
        """Configura el panel central donde se gestionan los campos del formulario."""
        # Frame del Editor con estilo 'Premium Slate'
        self.editor_frame = ctk.CTkFrame(self, corner_radius=20, 
                                         fg_color=("#FFFFFF", "#161617"), 
                                         border_width=1, border_color=("#E5E5EA", "#2C2C2E"))
        self.editor_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.editor_frame.grid_rowconfigure(1, weight=1)
        self.editor_frame.grid_columnconfigure(0, weight=1)

        # 1. Cabecera del Editor (Título + Botón Añadir)
        header_frame = ctk.CTkFrame(self.editor_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="ew")
        
        ctk.CTkLabel(header_frame, text="Estructura del Documento", 
                      font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        self.add_field_btn = ctk.CTkButton(header_frame, text="+ Añadir Campo", width=110, height=35,
                                           command=self.show_add_field_dialog, corner_radius=10,
                                           fg_color="#007AFF", hover_color="#0056b3",
                                           font=ctk.CTkFont(weight="bold"))
        self.add_field_btn.pack(side="right")

        # 2. Área de desplazamiento para los campos
        scrollbar_color = ("#D1D1D6", "#333333")
        scrollbar_hover = ("#C7C7CC", "#444444")
        self.fields_scroll = ctk.CTkScrollableFrame(self.editor_frame, 
                                                    fg_color=("#FFFFFF", "#161617"), 
                                                    scrollbar_button_color=scrollbar_color,
                                                    scrollbar_button_hover_color=scrollbar_hover)
        self.fields_scroll.grid(row=1, column=0, padx=10, pady=0, sticky="nsew")
        self.fields_scroll.grid_columnconfigure(0, weight=1)
        self.field_rows = []

        # 3. Footer (Botón de Generación Principal)
        self._setup_editor_footer()

    def _setup_editor_footer(self):
        """Configura el pie de página del editor con el botón de generar PDF."""
        footer_bg = ("#F2F2F7", "#1A1A1A")
        footer_frame = ctk.CTkFrame(self.editor_frame, height=60, corner_radius=15, fg_color=footer_bg)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        self.generate_btn = ctk.CTkButton(footer_frame, text="🚀 GENERAR PDF FINAL", 
                                          command=self.generate_pdf, height=45, corner_radius=10,
                                          fg_color="#007AFF", hover_color="#0056b3",
                                          font=ctk.CTkFont(size=14, weight="bold"))
        self.generate_btn.pack(side="left", pady=8, padx=(15, 5), expand=True, fill="x")

        self.gen_mail_btn = ctk.CTkButton(footer_frame, text="📧 GENERAR Y ENVIAR", 
                                           command=self.generate_and_send_email, height=45, corner_radius=10,
                                           fg_color="#5856D6", hover_color="#4845AC",
                                           font=ctk.CTkFont(size=14, weight="bold"))
        self.gen_mail_btn.pack(side="left", pady=8, padx=(5, 15), expand=True, fill="x")

    def _setup_preview_area(self):
        """Configura el panel lateral derecho para la vista previa del documento."""
        preview_bg = ("#E5E5EA", "#161617") # Look de banco de trabajo
        self.preview_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=preview_bg) 
        self.preview_frame.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)
        self.preview_frame.grid_rowconfigure(1, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        # Toolbar de Vista Previa
        toolbar = ctk.CTkFrame(self.preview_frame, fg_color="transparent", height=40)
        toolbar.grid(row=0, column=0, sticky="ew", padx=15, pady=5)
        
        ctk.CTkLabel(toolbar, text="👁️ VISTA PREVIA", 
                      font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

        self.design_switch = ctk.CTkSwitch(toolbar, text="Modo Diseño ✏️", variable=self.design_mode, 
                                           progress_color="#34C759", font=ctk.CTkFont(size=12))
        self.design_switch.pack(side="right", padx=10)

        # El "Papel" (Mockup visual del PDF en ScrollableArea)
        self.paper_frame = ctk.CTkScrollableFrame(self.preview_frame, fg_color="white", corner_radius=5)
        self.paper_frame.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="nsew")
        
        # El label que contendrá la imagen (proteger contra estiramiento raro)
        self.preview_canvas_label = ctk.CTkLabel(self.paper_frame, text="", fg_color="white")
        self.preview_canvas_label.pack(expand=True, fill="both")
        
        # Interactividad en Preview
        self.preview_canvas_label.bind("<Button-1>", self._on_preview_click)
        self.preview_canvas_label.bind("<B1-Motion>", self._on_preview_drag)
        self.preview_canvas_label.bind("<ButtonRelease-1>", self._on_preview_release)

    def _setup_keybindings(self):
        """Define los atajos de teclado globales para mejorar la productividad."""
        # Acciones principales
        self.bind("<Control-n>", lambda e: self.show_add_field_dialog())
        self.bind("<Control-g>", lambda e: self.generate_pdf())
        self.bind("<Control-s>", lambda e: self.save_current_as_template())
        
        # Historial (Deshacer / Rehacer)
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-Z>", lambda e: self.redo()) # Atajo alternativo para rehacer

    # =========================================================================
    # GESTIÓN DE PLANTILLAS Y PERSISTENCIA
    # =========================================================================

    def load_template_by_name(self, name, is_predefined=True):
        """Carga una plantilla (predefinida o personalizada) y aplica su estado a la UI."""
        self.save_state_to_undo()
        
        if is_predefined:
            if name in PREDEFINED_TEMPLATES:
                fields_data = PREDEFINED_TEMPLATES[name]
                # Normalizar formato de plantillas predefinidas al formato del estado completo
                normalized_fields = []
                for f in fields_data:
                    # Mapeo de tipos si es necesario
                    ftype_map_inv = {"text": "Texto", "date": "Fecha", "checkbox": "Checkbox", 
                                     "dropdown": "Dropdown", "radio": "Radio Buttons",
                                     "multiline": "Multilínea", "signature": "Firma", 
                                     "number": "Número", "section": "Sección"}
                    
                    raw_type = f.get("type", "text")
                    disp_type = ftype_map_inv.get(raw_type, "Texto")
                    
                    raw_col = f.get("column", "full")
                    disp_col = {"full": "Ancho Completo", "1": "Columna Izq", "2": "Columna Der"}.get(raw_col, "Ancho Completo")
                    
                    opts = f.get("options", [])
                    disp_opts = ",".join(opts) if isinstance(opts, list) else str(opts)

                    normalized_fields.append({
                        "label": f.get("label", ""),
                        "type": disp_type,
                        "options": disp_opts,
                        "column": disp_col,
                        "logic": f.get("logic", "")
                    })
                
                state = {
                    "title": name.upper(),
                    "fields": normalized_fields,
                    "visual": self.config_visual.copy(),
                    "images": [],
                    "logo": None
                }
                self._apply_state(state)
        else:
            path = os.path.join("templates", f"{name}.json")
            if os.path.exists(path):
                data = load_custom_template(path)
                state = {
                    "title": name.upper(),
                    "fields": data.get("fields", []),
                    "visual": data.get("visual_config", self.config_visual.copy()),
                    "images": data.get("extra_images", []),
                    "logo": data.get("logo", None)
                }
                self._apply_state(state)
        
        self.update_preview()

    def refresh_templates_list(self):
        """Refresca la lista de plantillas predefinidas y personalizadas en la UI."""
        # Limpiar contenedor actual
        for child in self.templates_scroll.winfo_children():
            child.destroy()

        # --- SECCIÓN: PREDEFINIDAS ---
        ctk.CTkLabel(self.templates_scroll, text="PREDEFINIDAS", 
                      font=ctk.CTkFont(size=10, weight="bold"), 
                      text_color=("black", "white")).pack(pady=(5, 2))
        
        for name in PREDEFINED_TEMPLATES.keys():
            btn = ctk.CTkButton(self.templates_scroll, text=name, height=24, font=ctk.CTkFont(size=11),
                                fg_color=("#FFFFFF", "#0A0A0A"), border_width=1, border_color=("#D1D1D6", "#2C2C2E"),
                                text_color=("black", "white"), hover_color=("#F5F5F7", "#161617"),
                                command=lambda n=name: self.load_template_by_name(n, is_predefined=True))
            btn.pack(fill="x", pady=1, padx=2)

        # --- SECCIÓN: MIS PLANTILLAS (Personalizadas) ---
        customs = list_custom_templates()
        if customs:
            ctk.CTkLabel(self.templates_scroll, text="MIS PLANTILLAS", 
                          font=ctk.CTkFont(size=10, weight="bold"), 
                          text_color=("#8E8E93", "#8E8E93")).pack(pady=(10, 2))
            for name in customs:
                f_row = ctk.CTkFrame(self.templates_scroll, fg_color="transparent")
                f_row.pack(fill="x")
                
                # Botón de carga
                btn = ctk.CTkButton(f_row, text=name, height=24, font=ctk.CTkFont(size=11),
                                    fg_color=("#D1D1D6", "#2E4053"), text_color=("black", "white"),
                                    command=lambda n=name: self.load_template_by_name(n, is_predefined=False))
                btn.pack(side="left", fill="x", expand=True, pady=1, padx=(2, 0))
                
                # Botón de eliminación
                del_tpl = ctk.CTkButton(f_row, text="🗑", width=20, height=24, fg_color="transparent", 
                                        text_color="#E74C3C", hover_color=("#FFEBEE", "#3D1C1C"),
                                        command=lambda n=name: self.delete_template_file(n))
                del_tpl.pack(side="right", padx=2)

    # =========================================================================
    # ESTADO Y DESHACER/REHACER
    # =========================================================================

    def save_state_to_undo(self):
        """
        Captura el estado actual de los campos y lo guarda en la pila de 'Deshacer'.
        Se dispara antes de cualquier cambio estructural significativo.
        """
        if self._block_state_capture: return
        
        state = self._capture_full_state()
        self.undo_stack.append(state)
        # Limitar tamaño de la pila
        if len(self.undo_stack) > 30: self.undo_stack.pop(0)
        self.redo_stack = []

    def undo(self):
        """Revierte al último estado guardado en la pila de deshacer."""
        if not self.undo_stack: return
        self._block_state_capture = True
        
        # Guardar el actual en redo antes de volver atrás
        current = self._capture_full_state()
        self.redo_stack.append(current)
        
        state = self.undo_stack.pop()
        self._apply_state(state)
        self._block_state_capture = False
        self.update_preview()

    def redo(self):
        """Avanza al siguiente estado guardado en la pila de rehacer."""
        if not self.redo_stack: return
        self._block_state_capture = True
        
        # Guardar el actual en undo antes de ir adelante
        current = self._capture_full_state()
        self.undo_stack.append(current)
        
        state = self.redo_stack.pop()
        self._apply_state(state)
        self._block_state_capture = False
        self.update_preview()

    def _capture_full_state(self):
        """Crea una instantánea serializable de toda la configuración actual."""
        fields = []
        for row in self.field_rows:
            fields.append({
                "label": row["entry"].get(),
                "type": row["type"].get(),
                "options": row["options"].get(),
                "column": row["column"].get(),
                "logic": row["logic"].get(),
                "required": row["required"].get(),
                "validation": row["validation"].get(),
                "abs_pos": row.get("abs_pos") # Guardar posición absoluta
            })
        return {
            "title": self.title_entry.get(),
            "fields": fields,
            "visual": self.config_visual.copy(),
            "images": [img.copy() for img in self.extra_images],
            "logo": self.logo_path
        }

    def _apply_state(self, state):
        """Aplica una instantánea de estado a la interfaz de usuario."""
        # Título
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, state["title"])
        
        # Limpiar campos actuales
        for row in self.field_rows:
            row["frame"].destroy()
        self.field_rows = []
        
        # Reconstruir campos
        for f in state["fields"]:
            self.add_field_row(
                default_text=f["label"], 
                default_type=f["type"], 
                default_options=f["options"], 
                default_column=f["column"],
                default_logic=f.get("logic", ""),
                default_required=f.get("required", False),
                default_validation=f.get("validation", "Ninguno"),
                abs_pos=f.get("abs_pos")
            )
        
        # Configuración Visual
        self.config_visual = state["visual"].copy()
        # Actualizar sliders/menús de la UI para que coincidan (Diseño)
        self.font_menu.set(self.config_visual['font_name'])
        self.spacing_slider.set(self.config_visual['spacing'])
        self.color_btn.configure(fg_color=self.config_visual['primary_color'])
        
        # Imágenes
        self.extra_images = [img.copy() for img in state["images"]]
        self.logo_path = state["logo"]
        self.refresh_images_ui()
        if self.logo_path:
            self.logo_preview_text.configure(text=os.path.basename(self.logo_path), text_color="#34C759")
        else:
            self.logo_preview_text.configure(text="Sin logo", text_color="gray")

        # Actualizar Label de PDF de fondo y recargar imágenes
        bg_path = self.config_visual.get('bg_pdf_path')
        if bg_path and os.path.exists(bg_path):
            self.bg_pdf_label.configure(text=f"Fondo: {os.path.basename(bg_path)}", text_color="#34C759")
            self.bg_images = render_pdf_to_images(bg_path)
            self.bg_pdf_dims = get_pdf_dimensions(bg_path)
        else:
            self.bg_pdf_label.configure(text="Sin PDF de fondo", text_color="gray")
            self.bg_images = []
            self.bg_pdf_dims = (612.0, 792.0)

    # =========================================================================
    # GESTIÓN DE CAMPOS DEL EDITOR
    # =========================================================================

    def add_default_fields(self):
        """Añade los campos iniciales de ejemplo al arrancar por primera vez."""
        self.add_field_row(default_text="DATOS DEL CLIENTE", default_type="Sección")
        self.add_field_row(default_text="Nombre Completo", default_type="Texto", default_column="Columna Izq")
        self.add_field_row(default_text="Fecha de Nacimiento", default_type="Fecha", default_column="Columna Der")
        self.add_field_row(default_text="Correo Electrónico", default_type="Texto")
        self.add_field_row(default_text="ESTADO DEL PEDIDO", default_type="Sección")
        self.add_field_row(default_text="Tipo de Servicio", default_type="Dropdown", default_options="Premium,Estándar,Básico")
        self.add_field_row(default_text="Acepto términos", default_type="Checkbox")

    # =========================================================================
    # UTILIDADES Y CONFIGURACIÓN VISUAL
    # =========================================================================

    def choose_color(self):
        """Abre un selector de color para cambiar el tono primario del PDF."""
        self.save_state_to_undo()
        # Usar el selector de colores nativo (Paleta)
        color_code = colorchooser.askcolor(title="Seleccionar Color Primario", initialcolor=self.config_visual['primary_color'])
        if color_code[1]: # color_code[1] es el valor hex
            self.config_visual['primary_color'] = color_code[1]
            # Actualizar el botón con el nuevo color (fg_color y hover_color)
            self.color_btn.configure(fg_color=color_code[1], hover_color=color_code[1])
            # Forzar actualización inmediata de la vista previa (sin debouncing)
            if self.after_id:
                self.after_cancel(self.after_id)
                self.after_id = None
            self.update_preview()

    def change_visual_config(self, *args):
        self.config_visual['font_name'] = self.font_menu.get()
        self.config_visual['spacing'] = int(self.spacing_slider.get())
        if hasattr(self, 'align_menu'):
            self.config_visual['alignment'] = self.align_menu.get()
        if hasattr(self, 'title_size_var'):
            self.config_visual['font_size_title'] = int(self.title_size_var.get())
        if hasattr(self, 'label_size_var'):
            self.config_visual['font_size_label'] = int(self.label_size_var.get())
        self.update_preview()

    def add_extra_image(self):
        self.save_state_to_undo()
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg")])
        if path:
            # Datos por defecto: abajo a la derecha, tamaño medio
            new_img = {
                'path': path,
                'x': 450,
                'y': 650,
                'w': 100,
                'h': 50
            }
            self.extra_images.append(new_img)
            self.refresh_images_ui()
            self.update_preview()

    def refresh_images_ui(self):
        for child in self.images_scroll.winfo_children():
            child.destroy()
        
        for idx, img_data in enumerate(self.extra_images):
            card_bg = ("#FFFFFF", "#131313")
            card_border = ("#D1D1D6", "#2C2C2E")
            frame = ctk.CTkFrame(self.images_scroll, corner_radius=12, border_width=1, 
                                 border_color=card_border, fg_color=card_bg)
            frame.pack(fill="x", pady=6, padx=5)
            
            name = os.path.basename(img_data['path'])
            ctk.CTkLabel(frame, text=name, font=ctk.CTkFont(size=10, weight="bold"), text_color=("black", "white")).pack(pady=4)
            
            # Estilo sutil para sliders y labels (Adaptativo)
            label_style = {"font": ctk.CTkFont(size=9), "text_color": ("#8E8E93", "#8E8E93")}
            
            ctk.CTkLabel(frame, text="Posición Horizontal (X):", **label_style).pack()
            sx = ctk.CTkSlider(frame, from_=0, to=600, number_of_steps=120, 
                               command=lambda v, i=idx: self.update_img_val(i, 'x', v))
            sx.set(img_data['x'])
            sx.pack(padx=15, fill="x", pady=(0, 5))
            
            ctk.CTkLabel(frame, text="Posición Vertical (Y):", **label_style).pack()
            sy = ctk.CTkSlider(frame, from_=0, to=800, number_of_steps=160, 
                               command=lambda v, i=idx: self.update_img_val(i, 'y', v))
            sy.set(img_data['y'])
            sy.pack(padx=15, fill="x", pady=(0, 5))

            ctk.CTkLabel(frame, text="Ancho (W):", **label_style).pack()
            sw = ctk.CTkSlider(frame, from_=20, to=300, number_of_steps=28, 
                               command=lambda v, i=idx: self.update_img_val(i, 'w', v))
            sw.set(img_data['w'])
            sw.pack(padx=15, fill="x", pady=(0, 10))
            
            del_btn = ctk.CTkButton(frame, text="✕", height=24, fg_color="transparent", 
                                    text_color="#FF3B30", hover_color=("#FFEBEE", "#3D1C1C"),
                                    font=ctk.CTkFont(weight="bold"))
            del_btn.configure(command=lambda i=idx: self.remove_extra_image(i)) # Configure after creation
            del_btn.pack(pady=(0, 10), padx=15, fill="x")

    def update_img_val(self, idx, key, value):
        self.extra_images[idx][key] = int(value)
        # Sincronizar alto proporcionalmente si es ancho (opcional, pero para no deformar)
        # if key == 'w': self.extra_images[idx]['h'] = int(value * 0.5) 
        self.request_preview_update()

    def adjust_img(self, idx, key, delta):
        # Mantenemos este para compatibilidad si hiciera falta, pero usamos update_img_val
        self.extra_images[idx][key] += delta
        self.update_preview()

    def remove_extra_image(self, idx):
        self.save_state_to_undo()
        self.extra_images.pop(idx)
        self.refresh_images_ui()
        self.update_preview()

    def save_current_as_template(self):
        name = self.title_entry.get().strip()
        if not name or name == "FORMULARIO DE DATOS PERSONALES":
            name = ctk.CTkInputDialog(text="Nombre de la plantilla:", title="Guardar Plantilla").get_input()
        
        if name:
            campos_to_save = []
            for row in self.field_rows:
                raw_type = row["type"].get()
                ftype = {
                    "Texto": "text", "Fecha": "date", "Checkbox": "checkbox",
                    "Dropdown": "dropdown", "Radio Buttons": "radio",
                    "Multilínea": "multiline", "Firma": "signature", "Número": "number",
                    "Sección": "section"
                }.get(raw_type, "text")
                
                raw_col = row["column"].get()
                fcol = {"Ancho Completo": "full", "1": "Columna Izq", "2": "Columna Der"}.get(raw_col, "full")
                
                opts = [o.strip() for o in row["options"].get().split(",") if o.strip()]
                campos_to_save.append({
                    "label": row["entry"].get(), 
                    "type": ftype, 
                    "options": opts,
                    "column": fcol,
                    "logic": row.get("logic", ctk.StringVar()).get()
                })
            
            save_template(name, campos_to_save, self.config_visual, self.extra_images)
            messagebox.showinfo("Éxito", f"Plantilla '{name}' guardada correctamente.")
            self.refresh_templates_list()

    def delete_template_file(self, name):
        if messagebox.askyesno("Confirmar", f"¿Borrar la plantilla '{name}'?"):
            os.remove(os.path.join("templates", f"{name}.json"))
            self.refresh_templates_list()

    def select_logo(self):
        """ Selecciona una imagen para usar como logo principal. """
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self.save_state_to_undo()
            self.logo_path = path
            self.logo_preview_text.configure(text=os.path.basename(path), text_color="#34C759")
            self.update_preview()

    def select_bg_pdf(self, path=None):
        """ Selecciona un PDF para usar como fondo (Watermark/Stamping). """
        if not path:
            path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        
        if path:
            self.save_state_to_undo()
            self.config_visual['bg_pdf_path'] = path
            
            try:
                # Obtener dimensiones reales del PDF
                self.bg_pdf_dims = get_pdf_dimensions(path)
                # Renderizar páginas para previsualización (72 DPI base)
                self.bg_images = render_pdf_to_images(path, dpi=72)
                self.update_preview()
                return True
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el PDF: {e}")
        return False

    # =========================================================================
    # DIÁLOGOS Y VENTANAS EMERGENTES
    # =========================================================================

    def show_add_field_dialog(self):
        show_add_field_dialog(self)

    def add_field_row(self, default_text="", default_type="Texto", index=None, default_options="", default_column="Ancho Completo", default_logic="", default_required=False, default_validation="Ninguno", request_layout=True, request_preview=True, **kwargs):
        if request_preview:
            self.save_state_to_undo()
        
        # El card del campo (Premium Gadget Look Adaptativo - High Contrast)
        row_bg = ("#FFFFFF", "#1A1B1C") 
        row_border = ("#D1D1D6", "#2C2C2E")
        row_frame = ctk.CTkFrame(self.fields_scroll, corner_radius=12, border_width=1, 
                                 border_color=row_border, fg_color=row_bg)
        row_frame.grid_columnconfigure(2, weight=1) 
        
        # Efecto Hover Sutil (Apple Highlight)
        row_frame.bind("<Enter>", lambda e: row_frame.configure(border_color="#007AFF", border_width=2))
        row_frame.bind("<Leave>", lambda e: row_frame.configure(border_color=row_border, border_width=1))

        # --- Col 0: Index y Handle de Drag (Look Apple/Adobe) ---
        idx_label = ctk.CTkLabel(row_frame, text=f"⁝⁝ {len(self.field_rows)+1}", 
                                  font=ctk.CTkFont(size=12, weight="bold"), 
                                  text_color=("#8E8E93", "#8E8E93"),
                                  cursor="fleur")
        idx_label.grid(row=0, column=0, padx=(15, 5))
        

        # --- Col 1: Info Principal (Look minimalista) ---
        entry = ctk.CTkEntry(row_frame, placeholder_text="Field Name...", border_width=0, 
                             fg_color="transparent", font=ctk.CTkFont(size=14, weight="bold"),
                             text_color=("black", "white"), placeholder_text_color=("#8E8E93", "#8E8E93"))
        if default_text: entry.insert(0, default_text)
        entry.grid(row=0, column=1, padx=10, sticky="ew")
        entry.bind("<KeyRelease>", lambda e: self.request_preview_update())

        # --- Col 2,3,4: Selectores estilizados ---
        ctrl_style = {"height": 32, "corner_radius": 10, "fg_color": ("#E5E5EA", "#2C2C2E"), 
                       "text_color": ("black", "white"), "button_color": ("#E5E5EA", "#2C2C2E"), 
                       "button_hover_color": ("#D1D1D6", "#3A3A3C")}
        
        types = ["Texto", "Fecha", "Checkbox", "Dropdown", "Radio Buttons", "Multilínea", "Firma", "Número", "Sección"]
        type_var = ctk.StringVar(value=default_type)
        type_menu = ctk.CTkOptionMenu(row_frame, values=types, variable=type_var, width=100, **ctrl_style)
        type_menu.grid(row=0, column=2, padx=5)

        cols = ["Ancho Completo", "Columna Izq", "Columna Der"]
        col_var = ctk.StringVar(value=default_column)
        col_menu = ctk.CTkOptionMenu(row_frame, values=cols, variable=col_var, width=110, command=lambda v: self.update_preview(), **ctrl_style)
        col_menu.grid(row=0, column=3, padx=5)

        options_entry = ctk.CTkEntry(row_frame, placeholder_text="Opciones...", width=110, height=32, 
                                     corner_radius=10, border_width=1, border_color=("#D1D1D6", "#2C2C2E"),
                                     fg_color=("#FFFFFF", "#1A1B1C"), text_color=("black", "white"),
                                     placeholder_text_color=("#8E8E93", "#8E8E93"))
        if default_options: options_entry.insert(0, default_options)
        options_entry.bind("<KeyRelease>", lambda e: self.request_preview_update())
        
        # --- Col 5: Borrado y Colapso ---
        # Botón de colapso para secciones (initially hidden or special)
        collapse_btn = ctk.CTkButton(row_frame, text=ICON_EXPANDED, width=30, height=30, 
                                     fg_color="transparent", text_color=("#8E8E93", "gray"),
                                     hover_color=("#E5E5EA", "#2C2C2E"),
                                     command=lambda: self.toggle_section(row_data))
        
        logic_btn = ctk.CTkButton(row_frame, text="⚙", width=30, height=30, fg_color="transparent", 
                                  text_color=("#8E8E93", "gray"), hover_color=("#E5E5EA", "#2C2C2E"), 
                                  command=lambda: self.show_field_settings(row_data))
        logic_btn.grid(row=0, column=5, padx=2)

        del_btn = ctk.CTkButton(row_frame, text="✕", width=30, height=30, fg_color="transparent", 
                                  text_color="#FF3B30", hover_color=("#FFEBEE", "#3D1C1C"),
                                  command=lambda: self.remove_field_row(row_frame))
        del_btn.grid(row=0, column=6, padx=(2, 15))

        def on_type_change(val):
            options_entry.grid_forget()
            col_menu.grid(row=0, column=3, padx=5)
            logic_btn.grid(row=0, column=5, padx=5)
            collapse_btn.grid_forget()
            
            if val == "Sección":
                col_menu.grid_forget()
                logic_btn.grid_forget()
                collapse_btn.grid(row=0, column=0, padx=(5, 0)) # Mover a la izquierda del idx
                idx_label.grid(row=0, column=1, padx=(5, 5))
                entry.configure(placeholder_text="CABECERA DE SECCIÓN", font=ctk.CTkFont(size=14, weight="bold"))
                row_frame.configure(fg_color=("#E5E5EA", "#131313")) 
            else:
                idx_label.grid(row=0, column=0, padx=(15, 5))
                entry.configure(placeholder_text="Nombre del campo...", font=ctk.CTkFont(size=14, weight="bold"))
                row_frame.configure(fg_color=row_bg)
                if val in ["Dropdown", "Radio Buttons"]:
                    options_entry.grid(row=0, column=4, padx=5)
            self.update_preview()

        type_menu.configure(command=on_type_change)
        
        logic_var = ctk.StringVar(value=default_logic)
        required_var = ctk.BooleanVar(value=default_required)
        validation_var = ctk.StringVar(value=default_validation)
        
        row_data = {
            "frame": row_frame, "entry": entry, "type": type_var, "options": options_entry,
            "column": col_var, "logic": logic_var, "required": required_var, "validation": validation_var,
            "logic_btn": logic_btn, "idx_label": idx_label, "collapse_btn": collapse_btn,
            "abs_pos": kwargs.get("abs_pos")
        }
        
        if row_data["abs_pos"]:
            # Pequeño indicador visual de que es posición absoluta
            abs_indicator = ctk.CTkLabel(row_frame, text="📍 ABS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#007AFF")
            abs_indicator.grid(row=0, column=7, padx=(0, 5))
            
            # Crear frame para controles de posición (segunda fila)
            pos_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            pos_frame.grid(row=1, column=0, columnspan=8, sticky="ew", padx=10, pady=(5, 5))
            
            # Variables para X, Y, W, H
            abs_x_var = ctk.IntVar(value=int(row_data["abs_pos"]["x"]))
            abs_y_var = ctk.IntVar(value=int(row_data["abs_pos"]["y"]))
            abs_w_var = ctk.IntVar(value=int(row_data["abs_pos"]["w"]))
            abs_h_var = ctk.IntVar(value=int(row_data["abs_pos"]["h"]))
            
            # Función para actualizar abs_pos cuando cambian los valores
            def update_abs_pos():
                row_data["abs_pos"]["x"] = abs_x_var.get()
                row_data["abs_pos"]["y"] = abs_y_var.get()
                row_data["abs_pos"]["w"] = abs_w_var.get()
                row_data["abs_pos"]["h"] = abs_h_var.get()
                self.request_preview_update()
            
            # Controles X, Y, W, H
            ctk.CTkLabel(pos_frame, text="X:", font=ctk.CTkFont(size=10)).grid(row=0, column=0, padx=(0, 2))
            x_spin = ctk.CTkEntry(pos_frame, textvariable=abs_x_var, width=60, font=ctk.CTkFont(size=10))
            x_spin.grid(row=0, column=1, padx=2)
            x_spin.bind("<FocusOut>", lambda e: update_abs_pos())
            x_spin.bind("<Return>", lambda e: update_abs_pos())
            
            ctk.CTkLabel(pos_frame, text="Y:", font=ctk.CTkFont(size=10)).grid(row=0, column=2, padx=(5, 2))
            y_spin = ctk.CTkEntry(pos_frame, textvariable=abs_y_var, width=60, font=ctk.CTkFont(size=10))
            y_spin.grid(row=0, column=3, padx=2)
            y_spin.bind("<FocusOut>", lambda e: update_abs_pos())
            y_spin.bind("<Return>", lambda e: update_abs_pos())
            
            ctk.CTkLabel(pos_frame, text="W:", font=ctk.CTkFont(size=10)).grid(row=0, column=4, padx=(5, 2))
            w_spin = ctk.CTkEntry(pos_frame, textvariable=abs_w_var, width=60, font=ctk.CTkFont(size=10))
            w_spin.grid(row=0, column=5, padx=2)
            w_spin.bind("<FocusOut>", lambda e: update_abs_pos())
            w_spin.bind("<Return>", lambda e: update_abs_pos())
            
            ctk.CTkLabel(pos_frame, text="H:", font=ctk.CTkFont(size=10)).grid(row=0, column=6, padx=(5, 2))
            h_spin = ctk.CTkEntry(pos_frame, textvariable=abs_h_var, width=60, font=ctk.CTkFont(size=10))
            h_spin.grid(row=0, column=7, padx=2)
            h_spin.bind("<FocusOut>", lambda e: update_abs_pos())
            h_spin.bind("<Return>", lambda e: update_abs_pos())

        # Bindings para Drag & Drop (Captura correcta de row_data)
        idx_label.bind("<Button-1>", lambda e, rd=row_data: self._on_drag_start(e, rd))
        idx_label.bind("<B1-Motion>", lambda e, rd=row_data: self._on_drag_motion(e, rd))
        idx_label.bind("<ButtonRelease-1>", lambda e, rd=row_data: self._on_drag_stop(e, rd))

        on_type_change(default_type)

        if index is None:
            self.field_rows.append(row_data)
        else:
            self.field_rows.insert(index, row_data)
        
        # Estado inicial de la lógica (Apple Blue si hay lógica)
        if logic_var.get():
             logic_btn.configure(fg_color="#007AFF", text_color="white")

        if request_layout:
            self.refresh_fields_layout()
        if request_preview:
            self.request_preview_update()
        return row_data

    def toggle_section(self, section_row):
        """Alterna el estado de colapso de una sección."""
        frame_id = section_row["frame"]
        if frame_id in self.collapsed_sections:
            self.collapsed_sections.remove(frame_id)
            section_row["collapse_btn"].configure(text=ICON_EXPANDED)
        else:
            self.collapsed_sections.add(frame_id)
            section_row["collapse_btn"].configure(text=ICON_COLLAPSED)
        
        self.refresh_fields_layout()

    def _on_drag_start(self, event, row_data):
        """Inicia el proceso de arrastre de una tarjeta de campo."""
        self._drag_data["widget"] = row_data["frame"]
        self._drag_data["y"] = event.y_root
        self._drag_data["index"] = self.field_rows.index(row_data)
        
        # Estilo de 'Arrastrando'
        row_data["frame"].configure(border_color="#007AFF", border_width=2)
        self.config(cursor="fleur")

    def _on_drag_motion(self, event, row_data):
        """Calcula el reordenamiento en tiempo real mientras se arrastra."""
        if not self._drag_data["widget"] or row_data not in self.field_rows: return
        
        # Detectar el widget debajo del ratón
        y_now = event.y_root
        delta = y_now - self._drag_data["y"]
        
        # Umbral sutil para el intercambio (Apple-style smoothness)
        if abs(delta) > 30:
            idx = self.field_rows.index(row_data)
            direction = 1 if delta > 0 else -1
            new_idx = idx + direction
            
            if 0 <= new_idx < len(self.field_rows):
                # Intercambio 'Vivo'
                self.field_rows[idx], self.field_rows[new_idx] = self.field_rows[new_idx], self.field_rows[idx]
                self.refresh_fields_layout()
                self._drag_data["y"] = y_now 

    def _on_drag_stop(self, event, row_data):
        """Finaliza el arrastre y guarda el estado para Deshacer."""
        if not self._drag_data["widget"]: return
        
        # Restaurar bordes si el row_data sigue siendo válido
        if row_data and "frame" in row_data:
            row_data["frame"].configure(border_color=("#D1D1D6", "#2C2C2E"), border_width=1)
        
        self._drag_data["widget"] = None
        self.config(cursor="")
        
        self.save_state_to_undo()
        self.update_preview()

    def reindex_fields(self):
        """Actualiza los números visuales de los campos tras un reordenamiento."""
        for i, row in enumerate(self.field_rows):
            row["idx_label"].configure(text=f"⁝⁝ {i+1}")


    def show_field_settings(self, current_row):
        show_field_settings(self, current_row)

    def refresh_fields_layout(self):
        """Actualiza el empaquetado de todos los campos respetando secciones colapsadas."""
        for row in self.field_rows:
            row["frame"].pack_forget()
            
        current_visible = True
        for row in self.field_rows:
            is_section = row["type"].get() == "Sección"
            
            if is_section:
                # Las secciones siempre se muestran
                row["frame"].pack(fill="x", pady=6, padx=15)
                # El estado de visibilidad para los siguientes hijos depende de si esta sección está colapsada
                current_visible = row["frame"] not in self.collapsed_sections
            else:
                # Los campos normales dependen del estado de la sección anterior
                if current_visible:
                    row["frame"].pack(fill="x", pady=6, padx=15)
                    
        self.reindex_fields()

    def clear_fields(self, request_layout=True, request_preview=True):
        """Elimina todos los campos del generador."""
        if request_preview:
            self.save_state_to_undo()
        for row in self.field_rows:
            row["frame"].destroy()
        self.field_rows.clear()
        if request_layout:
            self.refresh_fields_layout()
        if request_preview:
            self.update_preview()

    def remove_field_row(self, frame):
        self.save_state_to_undo()
        frame.destroy()
        self.field_rows = [row for row in self.field_rows if row["frame"] != frame]
        self.update_preview()


    def request_preview_update(self):
        if self.after_id:
            self.after_cancel(self.after_id)
        else:
            # Si no hay timer, es que es el inicio de un cambio. Guardamos estado.
            self.save_state_to_undo()
        self.after_id = self.after(300, self.update_preview)

    def update_preview(self):
        self.after_id = None
        titulo = self.title_entry.get()
        campos = []
        for row in self.field_rows:
            label = row["entry"].get()
            if not label: continue
            
            raw_type = row["type"].get()
            ftype = {
                "Texto": "text", "Fecha": "date", "Checkbox": "checkbox",
                "Dropdown": "dropdown", "Radio Buttons": "radio",
                "Multilínea": "multiline", "Firma": "signature", "Número": "number",
                "Sección": "section"
            }.get(raw_type, "text")
            
            raw_col = row["column"].get()
            fcol = {"Ancho Completo": "full", "Columna Izq": "1", "Columna Der": "2"}.get(raw_col, "full")

            opts = [o.strip() for o in row["options"].get().split(",") if o.strip()]
            campos.append({
                "label": label, 
                "type": ftype, 
                "options": opts, 
                "column": fcol, 
                "logic": row.get("logic", ctk.StringVar()).get(),
                "abs_pos": row.get("abs_pos")
            })

        # Generar imagen de preview de alta resolución
        display_w = 480
        img_pil = generar_preview_imagen(titulo, campos, self.logo_path, width_px=1400, config_visual=self.config_visual, extra_images=self.extra_images, bg_images=self.bg_images, pdf_dims=self.bg_pdf_dims)
        w_pil, h_pil = img_pil.size
        display_h = int(display_w * (h_pil / w_pil))
        
        # Guardar altura de página real para cálculos de coordenadas (basado en puntos reales del PDF)
        base_w, base_h = self.bg_pdf_dims
        self.last_page_h = (h_pil / float(w_pil)) * base_w

        self.last_display_h = display_h
        ctk_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(display_w, display_h)) 
        self.preview_canvas_label.configure(image=ctk_img)

    def _on_preview_click(self, event):
        """Detecta si se ha hecho clic sobre un campo absoluto, imagen o logo para arrastrarlo, o activa Modo Diseño."""
        # Dimensiones para cálculo de margen
        display_w = 480
        widget_w = self.preview_canvas_label.winfo_width()
        widget_h = self.preview_canvas_label.winfo_height()
        margin_x = max(0, (widget_w - display_w) / 2)
        margin_y = max(0, (widget_h - getattr(self, 'last_display_h', widget_h)) / 2)
        
        # Coordenadas relativas a la imagen
        img_x = event.x - margin_x
        img_y = event.y - margin_y
        
        # Convertir a puntos PDF
        scale_display_to_pdf = self.bg_pdf_dims[0] / display_w
        pdf_x = img_x * scale_display_to_pdf
        total_pdf_y = img_y * scale_display_to_pdf
        
        # 1. Verificar si el click está sobre un campo absoluto
        # Buscar el campo MÁS CERCANO al punto de click
        closest_field = None
        min_distance = float('inf')
        
        for idx, row in enumerate(self.field_rows):
            abs_pos = row.get("abs_pos")
            if abs_pos:
                page_h = self.bg_pdf_dims[1]
                page_offset_pts = abs_pos.get('page', 0) * page_h
                field_x = abs_pos['x']
                field_y = page_offset_pts + abs_pos['y']
                field_w = abs_pos['w']
                field_h = abs_pos['h']
                
                # Agregar margen de tolerancia para facilitar el click (30 puntos)
                tolerance = 30
                
                # Verificar si el click está dentro del campo (con tolerancia)
                if (field_x - tolerance <= pdf_x <= field_x + field_w + tolerance and 
                    field_y - tolerance <= total_pdf_y <= field_y + field_h + tolerance):
                    
                    # Calcular distancia al centro del campo
                    center_x = field_x + field_w / 2
                    center_y = field_y + field_h / 2
                    distance = ((pdf_x - center_x) ** 2 + (total_pdf_y - center_y) ** 2) ** 0.5
                    
                    # Guardar si es el más cercano
                    if distance < min_distance:
                        min_distance = distance
                        closest_field = (idx, abs_pos)
        
        # Si encontramos un campo cercano, seleccionarlo
        if closest_field:
            idx, abs_pos = closest_field
            # Desactivar Modo Diseño para evitar crear campos nuevos
            self.design_mode.set(False)
            # Seleccionar este campo para arrastrar
            self._drag_preview = {
                "id": f"field_{idx}",
                "type": "field",
                "field_idx": idx,
                "start_x": pdf_x,
                "start_y": total_pdf_y,
                "original_pos": (abs_pos['x'], abs_pos['y']),
                "original_size": (abs_pos['w'], abs_pos['h'])
            }
            return
        
        # 2. Si no hay campo absoluto, procesar Modo Diseño
        if self.design_mode.get():
            self._handle_design_click(event)
            return

        # Dimensiones para cálculo de margen
        display_w = 480
        widget_w = self.preview_canvas_label.winfo_width()
        widget_h = self.preview_canvas_label.winfo_height()
        margin_x = max(0, (widget_w - display_w) / 2)
        margin_y = max(0, (widget_h - getattr(self, 'last_display_h', widget_h)) / 2)

        # Convertir clic (display coord) -> PDF points
        scale_display_to_pdf = self.bg_pdf_dims[0] / display_w
        
        img_x = event.x - margin_x
        img_y = event.y - margin_y
        
        pdf_x = img_x * scale_display_to_pdf
        pdf_y = img_y * scale_display_to_pdf
        
        self._drag_preview["id"] = None
        
        # 1. Comprobar Imágenes Extras (Inverso para pillar la de 'arriba')
        for i, img_data in reversed(list(enumerate(self.extra_images))):
            x, y, w, h = img_data['x'], img_data['y'], img_data['w'], img_data['h']
            if x <= pdf_x <= x+w and y <= pdf_y <= y+h:
                self._drag_preview.update({
                    "id": i, "type": "extra", "start_x": event.x, "start_y": event.y,
                    "original_pos": (x, y)
                })
                return

        # 2. Comprobar Logo
        if self.logo_path:
            l_pos = self.config_visual.get('logo_position', {'x': 50, 'y': 30})
            lx, ly = l_pos['x'], l_pos['y']
            # Estimación del tamaño del logo (180x100 max)
            if lx <= pdf_x <= lx+180 and ly <= pdf_y <= ly+100:
                self._drag_preview.update({
                    "id": 0, "type": "logo", "start_x": event.x, "start_y": event.y,
                    "original_pos": (lx, ly)
                })

    def _handle_design_click(self, event):
        """Maneja el clic en el preview cuando el Modo Diseño está activo."""
        bg_path = self.config_visual.get('bg_pdf_path')
        if not bg_path:
            messagebox.showwarning("Modo Diseño", "Selecciona primero un PDF de fondo en la pestaña 'General'.")
            self.design_mode.set(False)
            return

        # 1. Obtener coordenadas del click respecto al widget
        click_x = event.x
        click_y = event.y

        # El CTkLabel puede centrar la imagen si es más grande que 480px
        # El ancho de la imagen en pantalla es fijo: 480
        display_w = 480
        widget_w = self.preview_canvas_label.winfo_width()
        widget_h = self.preview_canvas_label.winfo_height()
        
        # Calcular márgenes (CTkLabel centra la imagen si sobra espacio)
        margin_x = max(0, (widget_w - display_w) / 2)
        margin_y = max(0, (widget_h - getattr(self, 'last_display_h', widget_h)) / 2)
        
        # Ajustar coordenadas relativas a la imagen real
        img_x = click_x - margin_x
        img_y = click_y - margin_y
        
        scale_screen = display_w / self.bg_pdf_dims[0]
        pdf_x = img_x / scale_screen
        total_pdf_y = img_y / scale_screen
        
        page_h = self.bg_pdf_dims[1]
        page_num = int(total_pdf_y // page_h)
        page_click_y = total_pdf_y % page_h # Y desde el top de esa página

        # 2. Buscar caja en el PDF original
        box = find_field_box_at(bg_path, page_num, pdf_x, page_click_y)
        
        if box:
            self.add_field_row(
                default_text=f"Campo {len(self.field_rows) + 1}",
                abs_pos={**box, "page": page_num}
            )
        else:
            # Crear campo con posición estimada
            self.add_field_row(
                default_text=f"Campo {len(self.field_rows) + 1}",
                abs_pos={"x": pdf_x - 50, "y": page_click_y - 10, "w": 100, "h": 20, "page": page_num}
            )
        self.update_preview()

    def _on_preview_drag(self, event):
        """Mueve el elemento seleccionado en el preview."""
        if self._drag_preview["id"] is None: return
        
        display_w = 480
        widget_w = self.preview_canvas_label.winfo_width()
        widget_h = self.preview_canvas_label.winfo_height()
        margin_x = max(0, (widget_w - display_w) / 2)
        margin_y = max(0, (widget_h - getattr(self, 'last_display_h', widget_h)) / 2)
        
        # Coordenadas relativas a la imagen
        img_x = event.x - margin_x
        img_y = event.y - margin_y
        
        scale_display_to_pdf = self.bg_pdf_dims[0] / display_w
        pdf_x = img_x * scale_display_to_pdf
        total_pdf_y = img_y * scale_display_to_pdf
        
        # Calcular desplazamiento desde el inicio del arrastre
        dx = pdf_x - self._drag_preview["start_x"]
        dy = total_pdf_y - self._drag_preview["start_y"]
        
        ox, oy = self._drag_preview["original_pos"]
        new_x, new_y = max(0, ox + dx), max(0, oy + dy)

        if self._drag_preview["type"] == "field":
            # Mover campo absoluto
            idx = self._drag_preview["field_idx"]
            page_h = self.bg_pdf_dims[1]
            page_num = self.field_rows[idx]["abs_pos"].get('page', 0)
            page_offset = page_num * page_h
            
            # new_y es la coordenada Y absoluta (incluyendo offset de página)
            # Necesitamos restar el offset para obtener Y relativa a la página
            page_relative_y = (oy + dy) - page_offset
            
            self.field_rows[idx]["abs_pos"]["x"] = int(new_x)
            self.field_rows[idx]["abs_pos"]["y"] = int(page_relative_y)
        elif self._drag_preview["type"] == "extra":
            idx = self._drag_preview["id"]
            self.extra_images[idx]['x'] = int(new_x)
            self.extra_images[idx]['y'] = int(new_y)
        elif self._drag_preview["type"] == "logo":
            self.config_visual['logo_position'] = {'x': int(new_x), 'y': int(new_y)}

        self.update_preview()

    def _on_preview_release(self, event):
        """Finaliza el arrastre en el preview y guarda el estado."""
        if self._drag_preview["id"] is not None:
            self.save_state_to_undo()
            self.refresh_images_ui() # Actualizar inputs numéricos si están abiertos
        self._drag_preview["id"] = None

    # =========================================================================
    # LÓGICA DE GENERACIÓN Y EXPORTACIÓN
    # =========================================================================
    
    # Se eliminó open_visual_editor redundante. Se usa el integrado en PDF_MASTER_PRO.


    def generate_pdf(self):
        """Procesa los campos actuales y genera el archivo PDF final."""
        titulo = self.title_entry.get()
        if not titulo:
            messagebox.showerror("Error", "El título es obligatorio.")
            return

        campos = []
        for row in self.field_rows:
            label = row["entry"].get()
            if not label: continue
            
            raw_type = row["type"].get()
            ftype = {
                "Texto": "text", "Fecha": "date", "Checkbox": "checkbox",
                "Dropdown": "dropdown", "Radio Buttons": "radio",
                "Multilínea": "multiline", "Firma": "signature", "Número": "number",
                "Sección": "section"
            }.get(raw_type, "text")
            
            raw_col = row["column"].get()
            fcol = {"Ancho Completo": "full", "Columna Izq": "1", "Columna Der": "2"}.get(raw_col, "full")

            opts = [o.strip() for o in row["options"].get().split(",") if o.strip()]
            campos.append({
                "label": label, 
                "type": ftype, 
                "options": opts, 
                "column": fcol, 
                "logic": row.get("logic", ctk.StringVar()).get(),
                "required": row.get("required", ctk.BooleanVar()).get(),
                "validation": row.get("validation", ctk.StringVar()).get(),

                "abs_pos": row.get("abs_pos")

            })

        if not campos:
            messagebox.showerror("Error", "Debe agregar al menos un campo.")
            return

        output_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if output_path:
            try:
                generar_pdf(output_path, titulo, campos, self.logo_path, config_visual=self.config_visual, extra_images=self.extra_images, bg_pdf_path=self.config_visual.get('bg_pdf_path'))
                self.save_to_history(output_path)
                messagebox.showinfo("Éxito", f"PDF generado correctamente en:\n{output_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar el PDF:\n{e}")

    def generate_and_send_email(self):
        """Genera el PDF y lo envía automáticamente por correo según la configuración."""
        # 1. Validar configuración de email
        if not self.config_email['sender_email'] or not self.config_email['sender_password']:
            messagebox.showwarning("Configuración Requerida", "Por favor, configura tus credenciales de email en la pestaña 'Email' primero.")
            self.sidebar_tabs.set("Email")
            return

        # 2. Recopilar datos (Igual que generate_pdf pero sin diálogo de guardado)
        titulo = self.title_entry.get()
        campos = []
        for row in self.field_rows:
            label = row["entry"].get()
            if not label: continue
            raw_type = row["type"].get()
            ftype = {"Texto": "text", "Fecha": "date", "Checkbox": "checkbox", "Dropdown": "dropdown", "Radio Buttons": "radio", "Multilínea": "multiline", "Firma": "signature", "Número": "number", "Sección": "section"}.get(raw_type, "text")
            raw_col = row["column"].get()
            fcol = {"Ancho Completo": "full", "Columna Izq": "1", "Columna Der": "2"}.get(raw_col, "full")
            opts = [o.strip() for o in row["options"].get().split(",") if o.strip()]
            campos.append({
                "label": label, 
                "type": ftype, 
                "options": opts, 
                "column": fcol, 
                "logic": row.get("logic", ctk.StringVar()).get(),
                "required": row.get("required", ctk.BooleanVar()).get(),
                "validation": row.get("validation", ctk.StringVar()).get()
            })

        if not campos:
            messagebox.showerror("Error", "Debe agregar al menos un campo.")
            return

        # 3. Generar a archivo temporal
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"{titulo.replace(' ', '_')}.pdf")
        
        try:
            generar_pdf(temp_path, titulo, campos, self.logo_path, config_visual=self.config_visual, extra_images=self.extra_images)
            
            # 4. Enviar Email usando el nuevo módulo
            sub = self.mail_sub_entry.get()
            body = self.mail_body_text.get("1.0", "end-1c")
            to = self.mail_to_entry.get()
            
            ok, res = send_generated_pdf_email(self.config_email, temp_path, to, sub, body)
            if ok:
                messagebox.showinfo("Éxito", f"PDF generado y enviado correctamente a {res}")
                self.save_to_history(temp_path)
            else:
                messagebox.showerror("Error", f"Error en el envío: {res}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en el proceso de envío:\n{str(e)}")

    # --- UX: Filtro de Campos ---
    def filter_fields(self):
        query = self.search_entry.get().lower()
        for row in self.field_rows:
            label = row["entry"].get().lower()
            if query in label:
                row["frame"].pack(fill="x", padx=5, pady=2)
            else:
                row["frame"].pack_forget()

    # --- UX: Historial ---

    def refresh_history_ui(self):
        for widget in self.tab_history.winfo_children():
            widget.destroy()
        
        if not self.history:
            ctk.CTkLabel(self.tab_history, text="No hay PDFs generados", text_color=("#8E8E93", "#8E8E93")).pack(pady=20)
            return
        scroll = ctk.CTkScrollableFrame(self.tab_history, fg_color="transparent",
                                        scrollbar_button_color=("#D1D1D6", "#2C2C2E"),
                                        scrollbar_button_hover_color=("#C7C7CC", "#3A3A3C"))
        scroll.pack(fill="both", expand=True)

        for item in self.history:
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.pack(fill="x", pady=4, padx=5)
            
            btn = ctk.CTkButton(frame, text=f"{item['filename']}\n({item['date']})", 
                                font=ctk.CTkFont(size=10),
                                fg_color="transparent", text_color=("black", "white"), anchor="w",
                                hover_color=("#E5E5EA", "#1A1A1A"),
                                command=lambda p=item['path']: os.startfile(p))
            btn.pack(side="left", fill="x", expand=True)
            
            folder_btn = ctk.CTkButton(frame, text="📁", width=30, height=30, corner_radius=8,
                                       fg_color=("#E5E5EA", "#1A1A1B"), text_color=("black", "white"), 
                                       hover_color=("#D1D1D6", "#333333"),
                                       command=lambda p=item['path']: os.startfile(os.path.dirname(p)))
            folder_btn.pack(side="right", padx=2)
        
        ctk.CTkButton(self.tab_history, text="Limpiar Historial", fg_color="#FF3B30", 
                     text_color="#FFFFFF", corner_radius=10, height=35,
                     command=self.clear_history).pack(pady=10, padx=20, fill="x")

    def clear_history(self):
        if messagebox.askyesno("Confirmar", "¿Borrar todo el historial de PDFs?"):
            self.data_manager.clear_history()
            self.history = self.data_manager.history
            self.refresh_history_ui()

    def save_to_history(self, file_path):
        """Añade un archivo al historial y persiste el cambio."""
        self.history = self.data_manager.add_to_history(file_path)
        self.refresh_history_ui()

    # --- UX: Exportación ---
    def export_to_excel(self):
        ExportManager.export_to_excel(self.field_rows)

    def export_to_word(self):
        ExportManager.export_to_word(self.title_entry.get(), self.field_rows)

    def export_to_web(self):
        ExportManager.export_to_web(self.title_entry.get(), self.config_visual['primary_color'], self.field_rows)

    def batch_generate_csv(self):
        csv_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not csv_path: return
        
        try:
            with open(csv_path, 'rb') as f:
                raw_data = f.read()
            
            try:
                content = raw_data.decode('utf-8-sig').strip()
            except:
                content = raw_data.decode('latin-1', errors='replace').strip()
            
            if not content:
                messagebox.showerror("Error", "El archivo CSV está vacío.")
                return
            
            # Sniffer más agresivo
            sample = content[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
                delimiter = dialect.delimiter
            except:
                # Fallback manual basado en frecuencia
                counts = {d: sample.count(d) for d in [';', ',', '\t', '|']}
                delimiter = max(counts, key=counts.get)
            
            f_mem = io.StringIO(content)
            reader = csv.DictReader(f_mem, delimiter=delimiter)
            all_rows = [r for r in reader if any(r.values())] # Filtrar filas vacías
            columns = reader.fieldnames if reader.fieldnames else []
            
            if not columns:
                messagebox.showerror("Error", "No se detectaron cabeceras en el CSV.")
                return
            
            if not all_rows:
                messagebox.showwarning("Atención", "Se detectaron las cabeceras pero no hay filas de datos debajo.\n\nPor favor, asegúrate de que el CSV tenga datos a partir de la segunda fila.")
                return

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo procesar el CSV: {e}")
            return

        # Diálogo de mappeo
        dialog = ctk.CTkToplevel(self)
        dialog.title("Mapear Columnas CSV")
        dialog.geometry("400x500")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Asocia cada campo con una columna del CSV:", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=10, pady=5)

        mapping_vars = {}
        # Solo mapeamos campos que no sean secciones
        valid_fields = [row["entry"].get() for row in self.field_rows if row["type"].get() != "Sección" and row["entry"].get()]
        
        for field in valid_fields:
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            ctk.CTkLabel(frame, text=field, width=150, anchor="w").pack(side="left")
            
            var = ctk.StringVar(value="-- Ninguna --")
            menu = ctk.CTkOptionMenu(frame, values=["-- Ninguna --"] + columns, variable=var)
            menu.pack(side="right", fill="x", expand=True)
            mapping_vars[field] = var

        # Selector extra para el NOMBRE DEL ARCHIVO
        ctk.CTkLabel(dialog, text="Columna para NOMBRE del archivo:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        filename_col_var = ctk.StringVar(value="-- Autogenerado --")
        ctk.CTkOptionMenu(dialog, values=["-- Autogenerado --"] + columns, variable=filename_col_var).pack(pady=5, padx=20, fill="x")

        def start_batch():
            out_dir = filedialog.askdirectory(title="Carpeta de Destino")
            if not out_dir: return
            
            mapping = {f: v.get() for f, v in mapping_vars.items() if v.get() != "-- Ninguna --"}
            
            try:
                success_count = 0
                titulo_orig = self.title_entry.get()
                
                for i, row_data in enumerate(all_rows):
                    # Preparar campos con valores del CSV
                    campos_generar = []
                    for row in self.field_rows:
                        label = row["entry"].get()
                        if not label: continue
                        
                        ftype_raw = row["type"].get()
                        ftype = {
                            "Texto": "text", "Fecha": "date", "Checkbox": "checkbox",
                            "Dropdown": "dropdown", "Radio Buttons": "radio",
                            "Multilínea": "multiline", "Firma": "signature", "Número": "number",
                            "Sección": "section"
                        }.get(ftype_raw, "text")
                        
                        fcol_raw = row["column"].get()
                        fcol = {"Ancho Completo": "full", "Columna Izq": "1", "Columna Der": "2"}.get(fcol_raw, "full")
                        
                        opts = [o.strip() for o in row["options"].get().split(",") if o.strip()]
                        logic = row.get("logic", ctk.StringVar()).get()

                        # Valor por defecto o del CSV
                        val = ""
                        if label in mapping:
                            val = row_data.get(mapping[label], "")

                        campos_generar.append({
                            "label": label, "type": ftype, "options": opts, 
                            "column": fcol, "logic": logic, "default_value": val
                        })
                    
                    file_prefix = "PDF"
                    f_col = filename_col_var.get()
                    if f_col != "-- Autogenerado --":
                        val = str(row_data.get(f_col, "")).strip()
                        if val:
                            # Sanear nombre de archivo (quitar caracteres prohibidos)
                            for char in '<>:"/\\|?*': val = val.replace(char, '')
                            file_prefix = val[:50] # Limitar longitud

                    file_name = f"{file_prefix}_{success_count+1}_{datetime.now().strftime('%H%M%S')}.pdf"
                    dest = os.path.join(out_dir, file_name)
                    generar_pdf(dest, titulo_orig, campos_generar, self.logo_path, config_visual=self.config_visual, extra_images=self.extra_images)
                    self.save_to_history(dest)
                    success_count += 1
            
                messagebox.showinfo("Proceso Terminado", f"Se han generado {success_count} PDFs con éxito.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Error durante la generación: {e}")

        ctk.CTkButton(dialog, text="Comenzar Generación", command=start_batch, fg_color="green").pack(pady=10)
    

# Fin de PDFGeneratorApp




if __name__ == "__main__":
    # Bloque de prueba para ejecutar solo este frame
    root = ctk.CTk()
    root.title("Test Frame - PDFGeneratorApp")
    root.geometry("1400x850")
    app = PDFGeneratorApp(root)
    app.pack(fill="both", expand=True)
    root.mainloop()
