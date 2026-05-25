import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, url_for, redirect, session
from pymongo.errors import DuplicateKeyError
from typing import Optional, Dict
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

from ChefEnProceso import ChefEnProceso

app = Flask(__name__)
app.config["SECRET_KEY"] = "tu_clave_secreta"   # clave secreta para sesiones

# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@gmail.com'
app.config['MAIL_PASSWORD'] = 'tu_password_app'
mail = Mail(app)

# Conexión a MongoDB
connect = ChefEnProceso("mongodb+srv://Ricardo_idk:kiraymoster39@cluster0.ixvdcur.mongodb.net/?appName=Cluster0")
usuarios_collection = connect.usuarios
recetas_collection = connect.tareas
usuarios_collection.create_index("email", unique=True)

# Inyectar usuario en todas las plantillas
@app.context_processor
def inject_user():
    return dict(user=session.get("user"))

def obtener_usuario(email: str, password: str) -> Optional[Dict]:
    usuario = usuarios_collection.find_one({"email": email})
    if usuario and check_password_hash(usuario["password"], password):
        usuario['_id'] = str(usuario['_id'])
        return usuario
    return None

@app.route("/")
def inicio():
    return render_template("nicio.html")

@app.route("/recetario")
def recetario():
    return render_template("recetario.html")

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

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        usuario = obtener_usuario(email, password)

        if usuario:
            session["user"] = {
                "name": usuario["nombre"],
                "email": usuario["email"],
                "picture": "/static/default-avatar.png"
            }
            return redirect(url_for("recetario"))
        else:
            return render_template("nicio.html", mensaje="Usuario o contraseña incorrectos")
    else:
        return render_template("formulario_login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("inicio"))

def crear_usuario(nombre: str, email: str, password: str, apellido: str) -> Optional[str]:
    try:
        hashed = generate_password_hash(password)
        resultado = usuarios_collection.insert_one({
            "nombre": nombre,
            "apellido": apellido,
            "email": email,
            "password": hashed,
            "fecha_registro": datetime.now(),
            "activo": True
        })
        print("✅ Usuario insertado en MongoDB")
        return str(resultado.inserted_id)
    except DuplicateKeyError:
        print(f"❌ Error: El email {email} ya está registrado")
        return None

@app.route("/crearcuenta", methods=["GET", "POST"])
def crear_cuenta():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        email = request.form.get("email")
        password = request.form.get("password")

        if not password:
            return "❌ No se recibió la contraseña"

        id_usuario = crear_usuario(nombre, email, password, apellido)
        if id_usuario:
            # Guardar sesión al crear cuenta
            session["user"] = {
                "name": nombre,
                "email": email,
                "picture": "/static/default-avatar.png"
            }
            return redirect(url_for("recetario"))
        else:
            return "❌ El correo ya está registrado"
    else:
        return render_template("formulario.html")

if __name__ == "__main__":
    app.run(debug=True)