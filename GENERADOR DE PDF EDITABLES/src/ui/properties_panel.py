"""
Panel de Propiedades para Campos
Permite configurar las propiedades de los campos seleccionados en el editor visual.
"""

import customtkinter as ctk
from typing import Callable, Optional

class PropertiesPanel(ctk.CTkFrame):
    """Panel lateral para editar propiedades de campos"""
    
    def __init__(self, parent, on_property_changed: Optional[Callable] = None):
        """
        Inicializa el panel de propiedades.
        
        Args:
            parent: Widget padre
            on_property_changed: Callback cuando cambia una propiedad
        """
        super().__init__(parent, fg_color="transparent")
        
        self.on_property_changed = on_property_changed
        self.current_field = None
        self._updating = False  # Flag para evitar loops
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz del panel"""
        # Título
        title_label = ctk.CTkLabel(
            self,
            text="Propiedades del Campo",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(10, 20), padx=10)
        
        # Scroll frame para propiedades
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Nombre del campo
        ctk.CTkLabel(scroll_frame, text="Nombre:", anchor="w").pack(fill="x", pady=(5, 2))
        self.name_entry = ctk.CTkEntry(scroll_frame, placeholder_text="Nombre del campo")
        self.name_entry.pack(fill="x", pady=(0, 10))
        self.name_entry.bind("<KeyRelease>", lambda e: self._on_property_change())
        
        # Tipo de campo
        ctk.CTkLabel(scroll_frame, text="Tipo:", anchor="w").pack(fill="x", pady=(5, 2))
        self.type_var = ctk.StringVar(value="text")
        self.type_menu = ctk.CTkOptionMenu(
            scroll_frame,
            variable=self.type_var,
            values=["text", "number", "date", "checkbox", "dropdown", "multiline", "signature", "radio"],
            command=self._on_type_change
        )
        self.type_menu.pack(fill="x", pady=(0, 10))
        
        # Tamaño de fuente
        ctk.CTkLabel(scroll_frame, text="Tamaño de fuente:", anchor="w").pack(fill="x", pady=(5, 2))
        self.font_size_var = ctk.StringVar(value="12")
        self.font_size_menu = ctk.CTkOptionMenu(
            scroll_frame,
            variable=self.font_size_var,
            values=["8", "10", "12", "14", "16", "18", "20"],
            command=lambda v: self._on_property_change()
        )
        self.font_size_menu.pack(fill="x", pady=(0, 10))
        
        # Campo obligatorio
        self.required_var = ctk.BooleanVar(value=False)
        self.required_check = ctk.CTkCheckBox(
            scroll_frame,
            text="Campo obligatorio",
            variable=self.required_var,
            command=self._on_property_change
        )
        self.required_check.pack(fill="x", pady=(5, 10))
        
        # Validación
        ctk.CTkLabel(scroll_frame, text="Validación:", anchor="w").pack(fill="x", pady=(5, 2))
        self.validation_var = ctk.StringVar(value="Ninguno")
        self.validation_menu = ctk.CTkOptionMenu(
            scroll_frame,
            variable=self.validation_var,
            values=["Ninguno", "Email", "DNI/NIE", "Teléfono", "Numérico"],
            command=lambda v: self._on_property_change()
        )
        self.validation_menu.pack(fill="x", pady=(0, 10))
        
        # Opciones (para dropdown/radio)
        ctk.CTkLabel(scroll_frame, text="Opciones (separadas por coma):", anchor="w").pack(fill="x", pady=(5, 2))
        self.options_entry = ctk.CTkEntry(scroll_frame, placeholder_text="Opción1, Opción2, Opción3")
        self.options_entry.pack(fill="x", pady=(0, 10))
        self.options_entry.bind("<KeyRelease>", lambda e: self._on_property_change())
        
        # Inicialmente ocultar opciones
        self.options_entry.pack_forget()
        
        # Mensaje de ayuda
        self.help_label = ctk.CTkLabel(
            scroll_frame,
            text="Selecciona un campo para editar sus propiedades",
            font=("Arial", 10),
            text_color="gray",
            wraplength=200
        )
        self.help_label.pack(pady=20)
    
    def _on_type_change(self, new_type):
        """Maneja el cambio de tipo de campo"""
        # Mostrar/ocultar opciones según el tipo
        if new_type in ["dropdown", "radio"]:
            self.options_entry.pack(fill="x", pady=(0, 10))
        else:
            self.options_entry.pack_forget()
        
        self._on_property_change()
    
    def _on_property_change(self):
        """Notifica cambios en las propiedades"""
        if self._updating or not self.current_field:
            return
        
        if self.on_property_changed:
            properties = self.get_properties()
            self.on_property_changed(properties)
    
    def set_field(self, field):
        """
        Establece el campo actual para editar.
        
        Args:
            field: FieldBox a editar, o None para limpiar
        """
        self._updating = True
        self.current_field = field
        
        if field:
            # Actualizar valores
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, field.label)
            
            self.type_var.set(field.type)
            self.font_size_var.set(str(field.font_size))
            self.required_var.set(field.required)
            self.validation_var.set(field.validation)
            
            # Opciones
            if field.options:
                self.options_entry.delete(0, "end")
                self.options_entry.insert(0, ", ".join(field.options))
            
            # Mostrar/ocultar opciones
            if field.type in ["dropdown", "radio"]:
                self.options_entry.pack(fill="x", pady=(0, 10))
            else:
                self.options_entry.pack_forget()
            
            self.help_label.pack_forget()
        else:
            # Limpiar
            self.name_entry.delete(0, "end")
            self.type_var.set("text")
            self.font_size_var.set("12")
            self.required_var.set(False)
            self.validation_var.set("Ninguno")
            self.options_entry.delete(0, "end")
            self.options_entry.pack_forget()
            self.help_label.pack(pady=20)
        
        self._updating = False
    
    def get_properties(self) -> dict:
        """
        Obtiene las propiedades actuales del panel.
        
        Returns:
            Diccionario con las propiedades
        """
        options_text = self.options_entry.get().strip()
        options = [opt.strip() for opt in options_text.split(",")] if options_text else []
        
        return {
            'label': self.name_entry.get(),
            'type': self.type_var.get(),
            'font_size': int(self.font_size_var.get()),
            'required': self.required_var.get(),
            'validation': self.validation_var.get(),
            'options': options
        }
