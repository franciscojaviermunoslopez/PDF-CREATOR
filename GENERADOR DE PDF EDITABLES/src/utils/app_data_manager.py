"""
Módulo de Gestión de Datos y Exportación - PDF Master Pro
"""

import os
import json
import csv
import io
from datetime import datetime
from tkinter import filedialog, messagebox

class DataManager:
    def __init__(self, history_file="history.json"):
        self.history_file = history_file
        self.history = []
        self.load_history()

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def save_history(self):
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            print(f"No se pudo guardar el historial: {e}")

    def add_to_history(self, file_path):
        item = {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        # Evitar duplicados recientes
        if not self.history or self.history[0]['path'] != file_path:
            self.history.insert(0, item)
            self.history = self.history[:40] # Mantener los últimos 40
            self.save_history()
        return self.history

    def clear_history(self):
        self.history = []
        if os.path.exists(self.history_file):
            os.remove(self.history_file)

class ExportManager:
    @staticmethod
    def export_to_excel(field_rows):
        campos = [row["entry"].get() for row in field_rows if row["entry"].get()]
        if not campos: return
        
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV para Excel", "*.csv")])
        if path:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(campos)
            messagebox.showinfo("Éxito", "Estructura para Excel exportada correctamente.")

    @staticmethod
    def export_to_word(titulo, field_rows):
        html = f"<html><body style='font-family: Arial;'><h1>{titulo}</h1><table border='1' width='100%'>"
        for row in field_rows:
            label = row["entry"].get()
            if label:
                html += f"<tr><td bgcolor='#f2f2f2' width='30%'><b>{label}</b></td><td>&nbsp;</td></tr>"
        html += "</table></body></html>"
        
        path = filedialog.asksaveasfilename(defaultextension=".doc", filetypes=[("Microsoft Word", "*.doc")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            messagebox.showinfo("Éxito", "Formulario exportado a formato Word.")

    @staticmethod
    def export_to_web(titulo, primary_color, field_rows):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{titulo}</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial; background: #eaeff2; display: flex; justify-content: center; padding: 20px; }}
                .form-card {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 800px; }}
                h1 {{ color: {primary_color}; border-bottom: 2px solid {primary_color}; padding-bottom: 10px; }}
                .section-title {{ background: #f8f9fa; padding: 10px; margin-top: 25px; border-left: 4px solid {primary_color}; font-weight: bold; }}
                .field-row {{ margin-bottom: 15px; }}
                .columns {{ display: flex; gap: 20px; }}
                .col {{ flex: 1; }}
                label {{ display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: #333; }}
                input, select, textarea {{ width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
                .btn {{ background: {primary_color}; color: white; border: none; padding: 12px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="form-card">
                <h1>{titulo}</h1>
                <form id="pdfForm">
        """
        
        in_columns = False
        for row in field_rows:
            label = row["entry"].get()
            if not label: continue
            ftype = row["type"].get()
            fcol = row["column"].get()
            cols = [o.strip() for o in row["options"].get().split(",") if o.strip()]

            if fcol == "Columna Izq" and not in_columns:
                html += '<div class="columns"><div class="col">'
                in_columns = True
            elif fcol == "Columna Der" and in_columns:
                html += '</div><div class="col">'
            elif fcol == "Ancho Completo" and in_columns:
                html += '</div></div>'
                in_columns = False

            if ftype == "Sección":
                html += f'<div class="section-title">{label}</div>'
            else:
                html += f'<div class="field-row"><label>{label}</label>'
                if ftype == "Dropdown":
                    html += f'<select><option></option>' + "".join([f'<option>{o}</option>' for o in cols]) + '</select>'
                elif ftype == "Radio Buttons":
                    for o in cols:
                        html += f'<div><input type="radio" name="{label}" value="{o}"> {o}</div>'
                elif ftype == "Checkbox":
                    html += f'<input type="checkbox" style="width: auto;"> {label}'
                elif ftype == "Multilínea":
                    html += '<textarea rows="4"></textarea>'
                else:
                    t_web = "date" if ftype == "Fecha" else "number" if ftype == "Número" else "text"
                    html += f'<input type="{t_web}">'
                html += '</div>'

        if in_columns: html += '</div></div>'
        html += """
                <button type="button" class="btn" onclick="alert('Formulario completado')">Enviar Formulario</button>
                </form>
            </div>
        </body>
        </html>
        """
        
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("Archivo Web", "*.html")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            messagebox.showinfo("Éxito", "Formulario web HTML generado.")
