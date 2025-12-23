"""
Editor Visual de PDF - Componente Interactivo

Este módulo implementa un editor visual para añadir campos a PDFs de forma interactiva.
El usuario puede hacer clic en el PDF para añadir campos y arrastrar para redimensionar.

Características:
- Vista previa del PDF con overlay interactivo
- Clic para añadir campos
- Arrastrar para redimensionar
- Propiedades editables en tiempo real
"""

import customtkinter as ctk
from tkinter import Canvas
from PIL import Image, ImageTk
from typing import List, Dict, Optional, Callable, Tuple
import logging

logger = logging.getLogger(__name__)


class FieldBox:
    """Representa un campo visual en el canvas"""
    
    def __init__(self, x: float, y: float, w: float, h: float, label: str = "Campo", page: int = 0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.label = label
        self.page = page
        self.selected = False
        self.canvas_id = None
        self.text_id = None
        
    def contains_point(self, px: float, py: float) -> bool:
        """Verifica si un punto está dentro del campo"""
        return (self.x <= px <= self.x + self.w and 
                self.y <= py <= self.y + self.h)
    
    def to_dict(self) -> Dict:
        """Convierte el campo a diccionario"""
        return {
            'label': self.label,
            'type': 'text',
            'abs_pos': {
                'x': self.x,
                'y': self.y,
                'w': self.w,
                'h': self.h,
                'page': self.page
            },
            'column': 'full',
            'required': False,
            'options': []
        }


class PDFVisualEditor(ctk.CTkFrame):
    """Editor visual interactivo para PDFs"""
    
    def __init__(
        self, 
        parent,
        pdf_image: Optional[Image.Image] = None,
        on_fields_changed: Optional[Callable[[List[Dict]], None]] = None
    ):
        """
        Inicializa el editor visual.
        
        Args:
            parent: Widget padre
            pdf_image: Imagen del PDF a editar
            on_fields_changed: Callback cuando cambian los campos
        """
        super().__init__(parent)
        
        self.pdf_image = pdf_image
        self.on_fields_changed = on_fields_changed
        self.fields: List[FieldBox] = []
        self.selected_field: Optional[FieldBox] = None
        self.drag_start: Optional[Tuple[float, float]] = None
        self.drag_mode: Optional[str] = None  # 'create', 'move', 'resize'
        self.creating_field: Optional[FieldBox] = None
        self.current_page: int = 0  # Página actual del PDF
        
        # Configuración
        self.field_color = "#3498db"
        self.selected_color = "#e74c3c"
        self.creating_color = "#2ecc71"
        self.field_alpha = 0.3
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz del editor"""
        # Crear contenedor para scrollbars
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        
        # Grid layout para canvas y scrollbars
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Canvas para el PDF y los campos
        self.canvas = Canvas(
            self.container,
            bg="#131313",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbars
        self.v_scrollbar = ctk.CTkScrollbar(self.container, orientation="vertical", command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar = ctk.CTkScrollbar(self.container, orientation="horizontal", command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        
        # Eventos del mouse
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        
        # Zoom / Scroll con rueda
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_mouse_wheel_h)
        
        # Cargar imagen si existe
        if self.pdf_image:
            self.load_pdf_image(self.pdf_image)
    
    def load_pdf_image(self, image: Image.Image):
        """
        Carga una imagen de PDF en el canvas.
        
        Args:
            image: Imagen PIL del PDF
        """
        self.pdf_image = image
        
        # Convertir a PhotoImage
        self.photo = ImageTk.PhotoImage(image)
        
        # Limpiar canvas
        self.canvas.delete("all")
        
        # Dibujar imagen
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        
        # Configurar región de desplazamiento
        self.canvas.config(scrollregion=(0, 0, image.width, image.height))
        
        # Redibujar campos existentes (solo de esta página)
        self._redraw_fields()
    
    def _on_mouse_move(self, event):
        """Maneja el movimiento del mouse para cambiar el cursor"""
        if self.drag_mode:
            return 
        
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Verificar si está sobre un campo
        for field in reversed(self.fields):
            if field.contains_point(x, y):
                # Verificar si está en el borde para resize
                edge_threshold = 10
                at_right_edge = abs(x - (field.x + field.w)) < edge_threshold
                at_bottom_edge = abs(y - (field.y + field.h)) < edge_threshold
                
                if at_right_edge or at_bottom_edge:
                    self.canvas.config(cursor="bottom_right_corner")
                else:
                    self.canvas.config(cursor="fleur")
                return
        
        # Cursor por defecto
        self.canvas.config(cursor="crosshair")
    
    def _on_mouse_down(self, event):
        """Maneja el botón del mouse presionado"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Verificar si se hizo clic en un campo existente
        clicked_field = None
        for field in reversed(self.fields):
            if field.contains_point(x, y):
                clicked_field = field
                break
        
        if clicked_field:
            # Seleccionar campo existente
            self.selected_field = clicked_field
            self.drag_start = (x, y)
            
            # Determinar modo de arrastre
            edge_threshold = 10
            at_right_edge = abs(x - (clicked_field.x + clicked_field.w)) < edge_threshold
            at_bottom_edge = abs(y - (clicked_field.y + clicked_field.h)) < edge_threshold
            
            if at_right_edge or at_bottom_edge:
                self.drag_mode = 'resize'
            else:
                self.drag_mode = 'move'
        else:
            # Empezar a crear nuevo campo
            self.drag_mode = 'create'
            self.drag_start = (x, y)
            self.creating_field = FieldBox(
                x=x, y=y, w=0, h=0,
                label=f"Campo {len(self.fields) + 1}",
                page=self.current_page
            )
            self.selected_field = None
        
        self._redraw_fields()
    
    def _on_mouse_drag(self, event):
        """Maneja el arrastre del mouse"""
        if not self.drag_start:
            return
        
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if self.drag_mode == 'create':
            # Actualizar tamaño del campo que se está creando
            start_x, start_y = self.drag_start
            self.creating_field.x = min(start_x, x)
            self.creating_field.y = min(start_y, y)
            self.creating_field.w = abs(x - start_x)
            self.creating_field.h = abs(y - start_y)
            
        elif self.drag_mode == 'move' and self.selected_field:
            # Mover campo
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            self.selected_field.x += dx
            self.selected_field.y += dy
            self.drag_start = (x, y)
            
        elif self.drag_mode == 'resize' and self.selected_field:
            # Redimensionar campo
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            new_w = max(50, self.selected_field.w + dx)
            new_h = max(20, self.selected_field.h + dy)
            self.selected_field.w = new_w
            self.selected_field.h = new_h
            self.drag_start = (x, y)
        
        self._redraw_fields()
    
    def _on_mouse_up(self, event):
        """Maneja la liberación del mouse"""
        if self.drag_mode == 'create' and self.creating_field:
            # Finalizar creación del campo
            # Solo añadir si tiene un tamaño mínimo
            if self.creating_field.w > 20 and self.creating_field.h > 10:
                self.fields.append(self.creating_field)
                self.selected_field = self.creating_field
                logger.info(f"Campo creado: {self.creating_field.label}")
                
                # Notificar cambios
                if self.on_fields_changed:
                    self.on_fields_changed(self.get_fields())
            
            self.creating_field = None
        
        elif self.drag_mode in ['move', 'resize']:
            # Notificar cambios después de mover/redimensionar
            if self.on_fields_changed:
                self.on_fields_changed(self.get_fields())
        
        self.drag_start = None
        self.drag_mode = None
        self.canvas.config(cursor="crosshair")
        self._redraw_fields()
    
    def _on_double_click(self, event):
        """Maneja el doble clic para editar propiedades"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        for field in self.fields:
            if field.contains_point(x, y):
                self._edit_field_properties(field)
                break
    
    def _redraw_fields(self):
        """Redibuja todos los campos en el canvas"""
        # Eliminar campos anteriores
        self.canvas.delete("field")
        
        # Dibujar cada campo de la página actual
        for field in self.fields:
            if field.page != self.current_page:
                continue
            color = self.selected_color if field == self.selected_field else self.field_color
            
            # Rectángulo del campo
            field.canvas_id = self.canvas.create_rectangle(
                field.x, field.y,
                field.x + field.w, field.y + field.h,
                outline=color,
                width=2,
                tags="field"
            )
            
            # Etiqueta del campo
            field.text_id = self.canvas.create_text(
                field.x + 5, field.y + field.h / 2,
                text=field.label,
                anchor="w",
                fill=color,
                font=("Arial", 10, "bold"),
                tags="field"
            )
        
        # Dibujar campo en creación
        if self.creating_field and self.creating_field.w > 0 and self.creating_field.h > 0:
            self.canvas.create_rectangle(
                self.creating_field.x, self.creating_field.y,
                self.creating_field.x + self.creating_field.w,
                self.creating_field.y + self.creating_field.h,
                outline=self.creating_color,
                width=2,
                dash=(5, 5),
                tags="field"
            )
    
    def _edit_field_properties(self, field: FieldBox):
        """
        Abre un diálogo para editar las propiedades del campo.
        
        Args:
            field: Campo a editar
        """
        # TODO: Implementar diálogo de propiedades
        # Por ahora, solo cambiar el nombre
        from tkinter import simpledialog
        new_label = simpledialog.askstring(
            "Editar Campo",
            "Nombre del campo:",
            initialvalue=field.label
        )
        
        if new_label:
            field.label = new_label
            self._redraw_fields()
            
            # Notificar cambios
            if self.on_fields_changed:
                self.on_fields_changed(self.get_fields())
    
        return [f.to_dict() for f in self.fields]
    
    def add_field_from_data(self, field_data: Dict):
        """
        Añade un campo individual desde un diccionario de datos.
        
        Args:
            field_data: Diccionario con los datos del campo
        """
        abs_pos = field_data.get('abs_pos', {})
        field = FieldBox(
            x=abs_pos.get('x', 0),
            y=abs_pos.get('y', 0),
            w=abs_pos.get('w', 150),
            h=abs_pos.get('h', 20),
            label=field_data.get('label', 'Campo'),
            page=abs_pos.get('page', 0)
        )
        self.fields.append(field)
        self._redraw_fields()

    def set_fields(self, fields: List[Dict]):
        """
        Establece los campos desde una lista de diccionarios.
        
        Args:
            fields: Lista de campos
        """
        self.fields.clear()
        
        for field_data in fields:
            abs_pos = field_data.get('abs_pos', {})
            field = FieldBox(
                x=abs_pos.get('x', 0),
                y=abs_pos.get('y', 0),
                w=abs_pos.get('w', 150),
                h=abs_pos.get('h', 20),
                label=field_data.get('label', 'Campo'),
                page=abs_pos.get('page', 0)
            )
            self.fields.append(field)
        
        self._redraw_fields()
    
    def clear_fields(self):
        """Elimina todos los campos"""
        self.fields.clear()
        self.selected_field = None
        self._redraw_fields()
        
        # Notificar cambios
        if self.on_fields_changed:
            self.on_fields_changed([])
    
    def delete_selected_field(self):
        """Elimina el campo seleccionado"""
        if self.selected_field:
            self.fields.remove(self.selected_field)
            self.selected_field = None
            self._redraw_fields()
            
            # Notificar cambios
            if self.on_fields_changed:
                self.on_fields_changed(self.get_fields())

    def _on_mouse_wheel(self, event):
        """Scroll vertical con la rueda del ratón"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_mouse_wheel_h(self, event):
        """Scroll horizontal con la rueda del ratón (Shift + MouseWheel)"""
        self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")
