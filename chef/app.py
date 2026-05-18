import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, url_for, redirect
from pymongo import MongoClient
from typing import Optional, Dict
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

from ChefEnProceso import ChefEnProceso

app = Flask(__name__)

# Configuración de correo (usa variables de entorno en producción)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@gmail.com'
app.config['MAIL_PASSWORD'] = 'tu_password_app'
mail = Mail(app)

# Conexión a MongoDB Atlas
connect = ChefEnProceso("mongodb+srv://ricardorosal7335_db_user:kiraymoster39@cluster0.ixvdcur.mongodb.net/")
usuarios_collection = connect.usuarios
recetas_collection = connect.recetas_guardadas

def obtener_usuario(email: str, contraseña: str) -> Optional[Dict]:
    usuario = usuarios_collection.find_one({"email": email})
    if usuario and check_password_hash(usuario["password"], contraseña):
        usuario['_id'] = str(usuario['_id'])
        return usuario
    return None

@app.route("/")
def inicio():
    return render_template("nicio.html")

@app.route("/olvidaste", methods=["GET", "POST"])
def olvidaste():
    if request.method == "POST":
        email = request.form.get("email")
        user = usuarios_collection.find_one({"email": email})
        if user:
            token = str(uuid.uuid4())
            expiration = datetime.utcnow() + timedelta(hours=1)
            usuarios_collection.update_one(
                {"email": email},
                {"$set": {"reset_token": token, "reset_expiration": expiration}}
            )
            link = url_for("reset_password", token=token, _external=True)
            msg = Message("Recupera tu contraseña",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"Usa este enlace para resetear tu contraseña: {link}"
            mail.send(msg)
        return "Si el correo existe, recibirás un enlace."
    return render_template("recuperar_contraseña.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = usuarios_collection.find_one({"reset_token": token})
    if not user or user["reset_expiration"] < datetime.utcnow():
        return "El enlace ha expirado o no es válido."

    if request.method == "POST":
        nueva_contraseña = request.form.get("password")
        hashed = generate_password_hash(nueva_contraseña)
        usuarios_collection.update_one(
            {"reset_token": token},
            {"$set": {"password": hashed}, "$unset": {"reset_token": "", "reset_expiration": ""}}
        )
        return "Contraseña actualizada correctamente."
    
    return render_template("reset_form.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    contraseña = request.form.get("contraseña")

    usuario = obtener_usuario(email, contraseña)

    if usuario:
        return redirect(url_for("recetario"))  # asegúrate de definir esta ruta
    else:
        return render_template("nicio.html", mensaje="Usuario o contraseña incorrectos")

if __name__ == "__main__":
    app.run(debug=True)