"""
Módulo de Diálogos de Usuario - PDF Master Pro
"""

import customtkinter as ctk

def show_add_field_dialog(app):
    """Muestra un diálogo para elegir dónde insertar un nuevo campo."""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Añadir Campo")
    dialog.geometry("350x250")
    dialog.transient(app)
    dialog.grab_set()

    ctk.CTkLabel(dialog, text="¿Dónde quieres poner el campo?", 
                  font=ctk.CTkFont(size=13, weight="bold"),
                  text_color=("black", "white")).pack(pady=(20, 10))

    positions = ["Al final"] + [f"Antes de: {row['entry'].get()[:20]}..." for row in app.field_rows if row['entry'].get()]
    pos_var = ctk.StringVar(value="Al final")
    
    pos_menu = ctk.CTkOptionMenu(dialog, values=positions, variable=pos_var,
                                 fg_color=("#E5E5EA", "#1A1B1C"), button_color=("#D1D1D6", "#2C2C2E"), 
                                 button_hover_color=("#C7C7CC", "#3A3A3C"), text_color=("black", "white"), corner_radius=10)
    pos_menu.pack(pady=10, padx=30, fill="x")

    def confirm():
        sel = pos_var.get()
        if sel == "Al final":
            app.add_field_row()
        else:
            idx = positions.index(sel) - 1
            app.add_field_row(index=idx)
        dialog.destroy()

    ctk.CTkButton(dialog, text="Confirmar Añadir", command=confirm, 
                  fg_color="#007AFF", hover_color="#0056b3", height=35, corner_radius=10,
                  font=ctk.CTkFont(weight="bold")).pack(pady=20, padx=30, fill="x")

def show_field_settings(app, current_row):
    """Muestra el diálogo de ajustes avanzados para un campo."""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Ajustes Avanzados del Campo")
    dialog.geometry("450x650")
    dialog.transient(app)
    dialog.grab_set()

    ctk.CTkLabel(dialog, text=f"Ajustes: {current_row['entry'].get()}", 
                  font=ctk.CTkFont(size=14, weight="bold"),
                  text_color=("black", "white")).pack(pady=(25, 5))

    # --- SECCIÓN: VALIDACIÓN ---
    ctk.CTkLabel(dialog, text="VALIDACIÓN Y RESTRICCIONES", 
                  font=ctk.CTkFont(size=11, weight="bold"), text_color=("#007AFF", "#007AFF")).pack(pady=(20, 10))
    
    req_var = ctk.BooleanVar(value=current_row['required'].get())
    ctk.CTkCheckBox(dialog, text="Campo Obligatorio (Required)", variable=req_var,
                     fg_color="#007AFF", checkbox_width=18, checkbox_height=18,
                     font=ctk.CTkFont(size=12)).pack(pady=5, padx=50, anchor="w")

    ctk.CTkLabel(dialog, text="Tipo de Validación Especial:", font=ctk.CTkFont(size=11)).pack(pady=(10, 2))
    val_types = ["Ninguno", "Email", "DNI/NIE", "Teléfono", "Numérico"]
    val_type_var = ctk.StringVar(value=current_row['validation'].get())
    val_menu = ctk.CTkOptionMenu(dialog, values=val_types, variable=val_type_var, width=280,
                                  fg_color=("#E5E5EA", "#1A1B1C"), button_color=("#D1D1D6", "#2C2C2E"), 
                                  text_color=("black", "white"), corner_radius=10)
    val_menu.pack(pady=5)

    # --- SECCIÓN: LÓGICA ---
    ctk.CTkLabel(dialog, text="LÓGICA CONDICIONAL", 
                  font=ctk.CTkFont(size=11, weight="bold"), text_color=("#007AFF", "#007AFF")).pack(pady=(30, 10))
    
    ctk.CTkLabel(dialog, text="Este campo solo será visible si:", 
                  font=ctk.CTkFont(size=11), text_color=("#8E8E93", "gray")).pack(pady=(0, 15))

    trigger_options = ["(Sin lógica)"]
    trigger_map = [] 
    
    for i, row in enumerate(app.field_rows):
        if row['frame'] == current_row['frame']: continue
        r_type = row['type'].get()
        if r_type in ["Dropdown", "Radio Buttons", "Checkbox"]:
            label = row['entry'].get() or f"Campo {i+1}"
            trigger_options.append(label)
            trigger_map.append({'index': i, 'label': label})

    choice_var = ctk.StringVar(value=trigger_options[0])
    val_var = ctk.StringVar(value="")

    current_logic = current_row['logic'].get()
    if "|" in current_logic:
        t_idx, t_val = current_logic.split("|")
        for m in trigger_map:
            if str(m['index']) == t_idx:
                choice_var.set(m['label'])
                val_var.set(t_val)

    ctk.CTkLabel(dialog, text="Campo Disparador:", text_color=("black", "white")).pack(pady=(10, 2))
    combo_trigger = ctk.CTkOptionMenu(dialog, values=trigger_options, variable=choice_var, width=280,
                                      fg_color=("#E5E5EA", "#1A1B1C"), button_color=("#D1D1D6", "#2C2C2E"), 
                                      text_color=("black", "white"), corner_radius=10)
    combo_trigger.pack(pady=5)

    ctk.CTkLabel(dialog, text="Valor que activa:", text_color=("black", "white")).pack(pady=(10, 2))
    val_entry = ctk.CTkEntry(dialog, placeholder_text="Ej: 'Sí', 'Urgente'...", textvariable=val_var, width=280,
                             fg_color=("#FFFFFF", "#1A1B1C"), border_color=("#E5E5EA", "#2C2C2E"), corner_radius=10,
                             text_color=("black", "white"), placeholder_text_color=("#8E8E93", "#8E8E93"))
    val_entry.pack(pady=5)

    def save_settings():
        current_row['required'].set(req_var.get())
        current_row['validation'].set(val_type_var.get())
        sel_label = choice_var.get()
        if sel_label == "(Sin lógica)":
            current_row['logic'].set("")
        else:
            trigger_idx = -1
            for m in trigger_map:
                if m['label'] == sel_label:
                    trigger_idx = m['index']
                    break
            if trigger_idx != -1 and val_var.get():
                current_row['logic'].set(f"{trigger_idx}|{val_var.get()}")

        # Feedback visual del botón ⚙
        has_settings = current_row['logic'].get() or current_row['required'].get() or current_row['validation'].get() != "Ninguno"
        if has_settings:
            current_row['logic_btn'].configure(fg_color="#007AFF", text_color="white")
        else:
            current_row['logic_btn'].configure(fg_color="transparent", text_color=("#8E8E93", "gray"))

        app.save_state_to_undo()
        app.update_preview()
        dialog.destroy()

    ctk.CTkButton(dialog, text="Guardar Cambios", command=save_settings, 
                  fg_color="#34C759", height=40, corner_radius=12,
                  font=ctk.CTkFont(weight="bold")).pack(pady=30)
