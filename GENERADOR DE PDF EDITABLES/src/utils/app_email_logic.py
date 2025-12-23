"""
Módulo de Envío de Email - PDF Master Pro
"""

import smtplib
from email.message import EmailMessage
import os
from tkinter import messagebox
from src.core.pdf_generator import generar_pdf

def send_generated_pdf_email(config_email, temp_path, mail_to, subject, body):
    """
    Función encargada de enviar el PDF generado por correo electrónico.
    """
    try:
        msg = EmailMessage()
        msg['Subject'] = subject or config_email['subject']
        msg['From'] = config_email['sender_email']
        msg['To'] = mail_to or config_email['sender_email']
        msg.set_content(body)

        with open(temp_path, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=os.path.basename(temp_path))

        with smtplib.SMTP(config_email['smtp_server'], int(config_email['smtp_port'])) as server:
            server.starttls()
            server.login(config_email['sender_email'], config_email['sender_password'])
            server.send_message(msg)
        
        return True, msg['To']
    except Exception as e:
        return False, str(e)

def test_smtp_connection(server_addr, port, user, password):
    """
    Realiza una prueba rápida de conexión SMTP para validar credenciales.
    """
    try:
        with smtplib.SMTP(server_addr, int(port), timeout=10) as server:
            server.starttls()
            server.login(user, password)
        return True, "Conexión exitosa"
    except Exception as e:
        return False, str(e)
