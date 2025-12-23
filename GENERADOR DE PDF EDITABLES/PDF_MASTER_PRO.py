"""
PDF MASTER PRO - APLICACIÓN UNIFICADA
-------------------------------------
Punto de entrada principal que integra el Generador Avanzado y el Editor Visual.
"""

import customtkinter as ctk
from tkinter import messagebox
import os
import threading

# Configuración de entorno para silenciar la librería MuPDF (debe hacerse antes de importar fitz)
os.environ['FITZ_LOG_LEVEL'] = '0'

import fitz
from PIL import Image

# Silenciar errores y advertencias de la librería MuPDF de forma global
try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.set_mupdf_warnings(False)
except:
    pass

from src.ui.app_pdf_generator import PDFGeneratorApp
from src.ui.visual_editor import PDFVisualEditor
from src.utils.preview_cache import get_pdf_preview
from src.utils.app_pdf_utils import map_import_type, map_type_to_internal

class PDFMasterPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración de la ventana
        self.title("PDF MASTER PRO - Unificado")
        self.geometry("1500x950")
        ctk.set_appearance_mode("Dark")
        
        # Contenedor principal con pestañas
        self.tabview = ctk.CTkTabview(self, corner_radius=10, 
                                     fg_color=("#F5F5F7", "#0A0A0A"),
                                     segmented_button_selected_color=("#007AFF", "#007AFF"),
                                     segmented_button_selected_hover_color=("#0056B3", "#0056B3"),
                                     segmented_button_unselected_color=("#EBEBEF", "#1A1A1A"))
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Pestañas
        self.tab_gen = self.tabview.add("Generador Avanzado")
        self.tab_edit = self.tabview.add("Editor Visual")
        
        # 1. Instanciar Generador Avanzado
        self.app_generator = PDFGeneratorApp(
            self.tab_gen, 
            on_visual_editor_callback=lambda: self.tabview.set("Editor Visual")
        )
        self.app_generator.pack(fill="both", expand=True)
        
        # 2. Setup Editor Visual
        self._setup_editor_tab()
        
        # Configurar cambio de pestaña para sincronización inicial
        self.tabview.configure(command=self._on_tab_change)

    def _setup_editor_tab(self):
        """Configura el layout de la pestaña del editor visual."""
        # Frame de herramientas superior
        self.toolbar = ctk.CTkFrame(self.tab_edit, height=50, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=10, pady=5)
        
        # Indicador de estado
        self.status_label = ctk.CTkLabel(self.toolbar, text="Sincronizado", 
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color="#34C759")
        self.status_label.pack(side="left", padx=10)
        
        self.btn_open = ctk.CTkButton(self.toolbar, text="📂 Abrir PDF de Fondo", 
                                     command=self.select_pdf,
                                     fg_color="#3A3A3C", hover_color="#4A4A4C", width=160)
        self.btn_open.pack(side="left", padx=5)

        # Navegación
        self.nav_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        self.nav_frame.pack(side="left", padx=30)

        self.btn_prev = ctk.CTkButton(self.nav_frame, text="◀", width=40, command=self._prev_page)
        self.btn_prev.pack(side="left", padx=2)
        
        self.page_label = ctk.CTkLabel(self.nav_frame, text="Página: 1/1", font=ctk.CTkFont(size=12, weight="bold"))
        self.page_label.pack(side="left", padx=10)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="▶", width=40, command=self._next_page)
        self.btn_next.pack(side="left", padx=2)

        # Botones de Acción
        self.btn_sync = ctk.CTkButton(self.toolbar, text="📥 Aplicar al Generador", 
                                     command=self.sync_to_generator,
                                     fg_color="#34C759", hover_color="#28A745",
                                     font=ctk.CTkFont(weight="bold"), width=140)
        self.btn_sync.pack(side="right", padx=5)

        self.btn_refresh = ctk.CTkButton(self.toolbar, text="🔄 Recargar", 
                                        command=self.sync_from_generator,
                                        fg_color="#5856D6", hover_color="#4745A0", width=100)
        self.btn_refresh.pack(side="right", padx=5)

        self.btn_export = ctk.CTkButton(self.toolbar, text="📝 Exportar PDF", 
                                       command=self.export_pdf_from_visual,
                                       fg_color="#007AFF", hover_color="#0056b3",
                                       font=ctk.CTkFont(weight="bold"), width=120)
        self.btn_export.pack(side="right", padx=5)
        
        # --- Controles Estilo Documento ---
        self.doc_toolbar = ctk.CTkFrame(self.tab_edit, height=45, fg_color="transparent")
        self.doc_toolbar.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(self.doc_toolbar, text="Título:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(5, 2))
        self.edit_title_entry = ctk.CTkEntry(self.doc_toolbar, placeholder_text="Título del documento...", width=250)
        self.edit_title_entry.pack(side="left", padx=5)
        self.edit_title_entry.bind("<KeyRelease>", lambda e: self._sync_title_to_gen())

        # Controles de Estilo
        self.align_var = ctk.StringVar(value="Izquierda")
        self.align_menu = ctk.CTkOptionMenu(self.doc_toolbar, values=["Izquierda", "Centro", "Derecha"], 
                                            variable=self.align_var, command=self._sync_style_to_gen, width=100)
        self.align_menu.pack(side="left", padx=5)
        
        self.font_size_var = ctk.StringVar(value="18")
        self.font_size_menu = ctk.CTkOptionMenu(self.doc_toolbar, values=["14", "16", "18", "20", "24", "28"], 
                                                variable=self.font_size_var, command=self._sync_style_to_gen, width=70)
        self.font_size_menu.pack(side="left", padx=5)
        
        self.color_btn = ctk.CTkButton(self.doc_toolbar, text="Color", width=60, command=self._pick_color)
        self.color_btn.pack(side="left", padx=5)

        # Editor Visual Canvas
        self.visual_editor = PDFVisualEditor(self.tab_edit)
        self.visual_editor.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Estado interno del editor
        self.current_page = 0
        self.total_pages = 1

    def _on_tab_change(self):
        """Maneja el evento de cambio de pestaña."""
        target = self.tabview.get()
        if target == "Editor Visual":
            # Si entramos al editor, sincronizamos automáticamente desde el generador
            self.sync_from_generator()
            self._sync_from_ui()
        elif target == "Generador Avanzado":
            # Si volvemos, tal vez avisar si hubo cambios no guardados?
            # Por ahora lo dejamos manual o automático al presionar "Aplicar"
            pass

    def _update_page_info(self):
        self.page_label.configure(text=f"Página: {self.current_page + 1}/{self.total_pages}")
        # Cargar imagen de la página actual
        bg_pdf_path = self.app_generator.config_visual.get('bg_pdf_path')
        if bg_pdf_path and os.path.exists(bg_pdf_path):
            image = get_pdf_preview(bg_pdf_path, page_num=self.current_page, dpi=150)
            if image:
                self.visual_editor.current_page = self.current_page
                self.visual_editor.load_pdf_image(image)
        else:
            # Mostrar página en blanco (Letter size at 150 DPI)
            blank = Image.new('RGB', (1275, 1650), color='white')
            from PIL import ImageDraw
            draw = ImageDraw.Draw(blank)
            draw.rectangle([0, 0, 1274, 1649], outline=(230, 230, 230), width=1)
            self.visual_editor.current_page = self.current_page
            self.visual_editor.load_pdf_image(blank)
            self.total_pages = 1

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_page_info()

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_page_info()

    def select_pdf(self):
        """Abre el diálogo para seleccionar un PDF de fondo y detecta campos."""
        if self.app_generator.select_bg_pdf():
            bg_path = self.app_generator.config_visual.get('bg_pdf_path')
            if bg_path:
                # Actualizar información de páginas
                try:
                    doc = fitz.open(bg_path)
                    self.total_pages = len(doc)
                    doc.close()
                except:
                    self.total_pages = 1
                
                self.current_page = 0
                self.status_label.configure(text="🔍 Detectando campos...", text_color="#FF9500")
                
                # Ejecutar detección en un hilo separado para no bloquear la UI
                def run_analysis():
                    try:
                        from src.core.document_analyzer import DocumentAnalyzer
                        analyzer = DocumentAnalyzer()
                        
                        def progress(current, total):
                            self.after(0, lambda: self.status_label.configure(
                                text=f"🔍 Analizando pág. {current}/{total}...", 
                                text_color="#FF9500"
                            ))
                        
                        result = analyzer.analyze_pdf(bg_path, progress_callback=progress)
                        # Volver al hilo principal para mostrar resultados
                        self.after(100, lambda: self._handle_analysis_result(result, bg_path))
                    except Exception as e:
                        print(f"Error en análisis: {e}")
                        self.after(100, lambda: self.status_label.configure(text=f"Error en detección", text_color="red"))
                
                threading.Thread(target=run_analysis, daemon=True).start()

    def _handle_analysis_result(self, result, bg_path):
        """Procesa los resultados de la detección de campos."""
        if result.get('success') and result.get('fields'):
            num_fields = len(result['fields'])
            msg = f"Se han detectado {num_fields} campos en el PDF.\n\n¿Deseas importarlos automáticamente?"
            if messagebox.askyesno("Campos Detectados", msg):
                # Limpiar campos actuales (Modo Batch)
                self.app_generator.clear_fields(request_layout=False, request_preview=False)
                
                # Importar campos de forma progresiva (Chunks de 10)
                fields = result['fields']
                
                if result.get('title'):
                    self.app_generator.title_entry.delete(0, "end")
                    self.app_generator.title_entry.insert(0, result['title'])
                
                self._import_fields_sequentially(fields, 0, bg_path)
                return # El resto se hace en la recursión
        
        # Si no hay campos o el usuario dijo no
        self._update_page_info()
        self.status_label.configure(text=f"PDF Cargado: {os.path.basename(bg_path)}", text_color="#34C759")

    def _import_fields_sequentially(self, fields, start_idx, bg_path):
        """Añade campos en bloques para mantener la UI fluida pero rápida."""
        chunk_size = 50 # Bloques más grandes para mayor velocidad
        total = len(fields)
        end_idx = min(start_idx + chunk_size, total)
        
        for i in range(start_idx, end_idx):
            f = fields[i]
            # Solo redibujar en el último campo de la ÚLTIMA tanda
            is_global_last = (i == total - 1)
            self.app_generator.add_field_row(
                default_text=f['label'],
                default_type=map_import_type(f['type']),
                default_options=",".join(f.get('options', [])),
                abs_pos=f.get('abs_pos'),
                request_layout=is_global_last,
                request_preview=is_global_last
            )
            
        if end_idx < total:
            self.status_label.configure(text=f"📥 Importando campos ({end_idx}/{total})...", text_color="#007AFF")
            # Delay mínimo de 1ms para no bloquear pero ir al máximo
            self.after(1, lambda: self._import_fields_sequentially(fields, end_idx, bg_path))
        else:
            self._update_page_info()
            self.status_label.configure(text=f"PDF Cargado: {os.path.basename(bg_path)}", text_color="#34C759")

    def sync_from_generator(self):
        """Carga los campos y el PDF del Generador Avanzado al Editor Visual."""
        bg_pdf_path = self.app_generator.config_visual.get('bg_pdf_path')
        
        if not bg_pdf_path or not os.path.exists(bg_pdf_path):
            self.status_label.configure(text="Sin PDF de fondo", text_color="#FF9500")
            return

        try:
            # Obtener número de páginas
            doc = fitz.open(bg_pdf_path)
            self.total_pages = len(doc)
            doc.close()
            
            # Limpiar editor visual
            self.visual_editor.clear_fields()
            
            # Cargar imagen inicial si es necesario
            self._update_page_info()
            
            # Cargar campos
            scale_factor = 150.0 / 72.0
            fields_loaded = 0
            
            # Recopilar todos los campos del generador avanzado
            for row in self.app_generator.field_rows:
                abs_pos = row.get("abs_pos")
                if abs_pos:
                    self.visual_editor.add_field_from_data({
                        'label': row["entry"].get(),
                        'type': map_type_to_internal(row["type"].get()),
                        'options': [o.strip() for o in row["options"].get().split(",") if o.strip()],
                        'abs_pos': {
                            'x': abs_pos['x'] * scale_factor,
                            'y': abs_pos['y'] * scale_factor,
                            'w': abs_pos['w'] * scale_factor,
                            'h': abs_pos['h'] * scale_factor,
                            'page': abs_pos.get('page', 0)
                        }
                    })
                    fields_loaded += 1
                else:
                    # Campo sin posición absoluta: Colocar en una posición "flotante" por defecto en la página 0
                    self.visual_editor.add_field_from_data({
                        'label': row["entry"].get(),
                        'type': map_type_to_internal(row["type"].get()),
                        'options': [o.strip() for o in row["options"].get().split(",") if o.strip()],
                        'abs_pos': {
                            'x': 50,
                            'y': 50 + (fields_loaded * 30),
                            'w': 150,
                            'h': 20,
                            'page': 0
                        }
                    })
                    fields_loaded += 1
            
            self.visual_editor._redraw_fields()
            self.status_label.configure(text=f"Cargados {fields_loaded} campos", text_color="#34C759")
            
        except Exception as e:
            messagebox.showerror("Error de Sincronización", f"No se pudo sincronizar:\n{str(e)}")

    def sync_to_generator(self, request_preview=True):
        """Aplica los cambios realizados en el Editor Visual de vuelta al Generador Avanzado."""
        fields = self.visual_editor.get_fields()
        
        # Limpiar campos actuales en el generador (Modo Batch)
        self.app_generator.clear_fields(request_layout=False, request_preview=False)
        
        # Factor de escala inverso (de 150 DPI a 72 DPI)
        scale_factor = 72.0 / 150.0
        total = len(fields)
        
        for i, field in enumerate(fields):
            abs_pos = field.get('abs_pos')
            if abs_pos:
                scaled_abs_pos = {
                    'x': abs_pos['x'] * scale_factor,
                    'y': abs_pos['y'] * scale_factor,
                    'w': abs_pos['w'] * scale_factor,
                    'h': abs_pos['h'] * scale_factor,
                    'page': abs_pos.get('page', 0)
                }
                
                # Solo redibujar en el último campo
                is_last = (i == total - 1)
                self.app_generator.add_field_row(
                    default_text=field.get('label', ''),
                    default_type=map_import_type(field.get('type', 'text')),
                    default_column='Ancho Completo',
                    default_options=",".join(field.get('options', [])),
                    abs_pos=scaled_abs_pos,
                    request_layout=is_last,
                    request_preview=is_last and request_preview
                )
        
        self.status_label.configure(text="Sincronizado con Generador", text_color="#34C759")

    def export_pdf_from_visual(self):
        """Sincroniza y exporta el PDF directamente."""
        # 1. Sincronizar campos (sin preview para ir rápido)
        self.sync_to_generator(request_preview=False)
        
        # 2. Sincronizar título y estilos
        self._sync_title_to_gen()
        self._sync_style_to_gen()
        
        # 3. Disparar generación
        self.status_label.configure(text="Generando PDF...", text_color="#007AFF")
        self.app_generator.generate_pdf()
        self.status_label.configure(text="Exportado", text_color="#34C759")

    def _sync_title_to_gen(self):
        self.app_generator.title_entry.delete(0, "end")
        self.app_generator.title_entry.insert(0, self.edit_title_entry.get())
        self.app_generator.update_preview()

    def _sync_style_to_gen(self, *args):
        self.app_generator.config_visual['alignment'] = self.align_var.get()
        self.app_generator.config_visual['font_size_title'] = int(self.font_size_var.get())
        # Sincronizar UI del generador
        if hasattr(self.app_generator, 'align_menu'):
            self.app_generator.align_menu.set(self.align_var.get())
        if hasattr(self.app_generator, 'title_size_var'):
            self.app_generator.title_size_var.set(self.font_size_var.get())
        self.app_generator.update_preview()

    def _pick_color(self):
        from tkinter import colorchooser
        color = colorchooser.askcolor(title="Seleccionar Color")[1]
        if color:
            self.app_generator.config_visual['primary_color'] = color
            self.app_generator.color_btn.configure(fg_color=color, hover_color=color)
            self.app_generator.update_preview()

    def _sync_from_ui(self):
        """Sincroniza los controles de la pestaña Editor Visual desde el Generador."""
        self.edit_title_entry.delete(0, "end")
        self.edit_title_entry.insert(0, self.app_generator.title_entry.get())
        
        align = self.app_generator.config_visual.get('alignment', 'Izquierda')
        self.align_var.set(align)
        
        size = str(self.app_generator.config_visual.get('font_size_title', 18))
        self.font_size_var.set(size)

if __name__ == "__main__":
    app = PDFMasterPro()
    app.mainloop()
