import os
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from bson.errors import InvalidId
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from ChefEnProceso import ChefEnProceso

app = Flask(__name__)
app.secret_key =("tu_clave_ultra_secreta")
app.config["MAIL_SERVER"] ="smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] =True
app.config["MAIL_USERNAME"] = "astridvanessalopez0509@gmail.com"
app.config["MAIL_PASSWORD"] = "mzsk xksi tile kmfs"

connect = ChefEnProceso("mongodb+srv://Ricardo_idk:kiraymoster39@cluster0.ixvdcur.mongodb.net/?appName=Cluster0")
usuarios_collection = connect.usuarios
recetas_collection = connect.tareas
usuarios_collection.create_index("email", unique=True)


@app.context_processor
def inject_user():
    return {"user": session.get("user")}


def get_object_id(id):
    try:
        return ObjectId(id)
    except (InvalidId, TypeError):
        return None


def obtener_usuario(email, password):
    usuario = usuarios_collection.find_one({"email": email})
    if usuario and check_password_hash(usuario["password"], password):
        usuario["_id"] = str(usuario["_id"])
        return usuario
    return None


@app.route("/")
def inicio():
    return render_template("inicio.html")


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
                {"$set": {"reset_token": token, "reset_expiration": expiration}},
            )
            link = url_for("reset_password", token=token, _external=True)
            msg = MIMEText(
                f"Usa este enlace para resetear tu contraseña: {link}",
                _charset="utf-8",
            )
            msg["Subject"] = "Recupera tu contraseña"
            msg["From"] = app.config["MAIL_USERNAME"]
            msg["To"] = email

            try:
                if not app.config["MAIL_USERNAME"] or not app.config["MAIL_PASSWORD"]:
                    raise RuntimeError(
                        "Faltan MAIL_USERNAME o MAIL_PASSWORD en variables de entorno"
                    )

                with smtplib.SMTP(
                    app.config["MAIL_SERVER"], app.config["MAIL_PORT"]
                ) as server:
                    if app.config["MAIL_USE_TLS"]:
                        server.starttls()
                    server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
                    server.sendmail(
                        app.config["MAIL_USERNAME"], [email], msg.as_string()
                    )
            except Exception as e:
                print("Error enviando correo:", e)

        return "Si el correo existe, recibirás un enlace."
    return render_template("recuperar_contraseña.html")


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = usuarios_collection.find_one({"reset_token": token})
    if not user or user["reset_expiration"] < datetime.utcnow():
        return "El enlace ha expirado o no es válido."

    if request.method == "POST":
        nueva_contrasena = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if nueva_contrasena != confirm_password:
            return render_template(
                "reset_form.html", mensaje="Las contraseñas no coinciden"
            )

        hashed = generate_password_hash(nueva_contrasena)
        usuarios_collection.update_one(
            {"reset_token": token},
            {
                "$set": {"password": hashed},
                "$unset": {"reset_token": "", "reset_expiration": ""},
            },
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
            session["user"] = {"name": usuario["nombre"], "email": usuario["email"]}
            return redirect(url_for("recetario"))

        return render_template("inicio.html", mensaje="Usuario o contraseña incorrectos")

    return render_template("inicio.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("inicio"))


def crear_usuario(nombre, email, password, apellido):
    try:
        hashed = generate_password_hash(password)
        resultado = usuarios_collection.insert_one(
            {
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "password": hashed,
                "fecha_registro": datetime.now(),
                "activo": True,
            }
        )
        return str(resultado.inserted_id)
    except DuplicateKeyError:
        return None


@app.route("/crearcuenta", methods=["GET", "POST"])
def crear_cuenta():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        email = request.form.get("email")
        password = request.form.get("password")

        if not password:
            return "No se recibió la contraseña"

        id_usuario = crear_usuario(nombre, email, password, apellido)
        if id_usuario:
            session["user"] = {"name": nombre, "email": email}
            return redirect(url_for("recetario"))

        return "El correo ya está registrado"

    return render_template("formulario.html")


@app.route("/recetario")
def recetario():
    recetas = list(recetas_collection.find())
    return render_template("recetario.html", recetas=recetas)

@app.route("/buscar")
def buscar_recetas():
    query = {}
    q = request.args.get("q")
    dificultad = request.args.get("dificultad")
    tipo = request.args.get("tipo_alimentacion")

    if q:
        query["nombre_receta"] = {"$regex": q, "$options": "i"}
    if dificultad:
        query["dificultad"] = dificultad
    if tipo:
        query["tipo_alimentacion"] = tipo

    recetas = list(recetas_collection.find(query))
    return render_template("recetario.html", recetas=recetas, user=None)

@app.route("/crear_receta", methods=["POST"])
def crear_receta():
    receta = {
        "nombre": request.form.get("nombre"),
        "ingredientes": request.form.get("ingredientes"),
        "dificultad": request.form.get("dificultad"),
        "pasos": request.form.get("pasos"),
        "descripcion": request.form.get("descripcion"),
        "tiempo_preparacion": request.form.get("tiempo_preparacion"),
        "tiempo_coccion": request.form.get("tiempo_coccion"),
        "porciones": request.form.get("porciones"),
        "presentacion": request.form.get("presentacion"),
        "tips": request.form.get("tips"),
        "fecha_creacion": datetime.now(),
        "es_usuario": True,
        "creador": session["user"]["email"] if "user" in session else None
    }
    
    ingredientes_raw = request.form['ingredientes']  
    ingredientes = [i.strip() for i in ingredientes_raw.split(",")]
    receta["ingredientes"] = ingredientes
    recetas_collection.insert_one(receta)
    return redirect(url_for("recetario"))

@app.route("/eliminar_receta/<id>")
def eliminar_receta(id):
    object_id = get_object_id(id)
    if object_id:
        recetas_collection.delete_one({"_id": object_id})
    return redirect(url_for("recetario"))
@app.route("/editar_receta/<id>", methods=["GET", "POST"])
def editar_receta(id):
    object_id = get_object_id(id)
    if not object_id:
        return redirect(url_for("recetario"))

    receta = recetas_collection.find_one({"_id": object_id})
    if not receta:
        return redirect(url_for("recetario"))

    if request.method == "POST":

        ingredientes_raw = request.form.get("ingredientes", "")
        ingredientes = [i.strip() for i in ingredientes_raw.split(",")]

        nuevos_datos = {
            "nombre": request.form.get("nombre"),
            "ingredientes": ingredientes,
            "dificultad": request.form.get("dificultad"),
            "pasos": request.form.get("pasos"),
            "descripcion": request.form.get("descripcion"),
            "tiempo_preparacion": request.form.get("tiempo_preparacion"),
            "tiempo_coccion": request.form.get("tiempo_coccion"),
            "porciones": request.form.get("porciones"),
            "presentacion": request.form.get("presentacion"),
            "tips": request.form.get("tips"),
        }

        recetas_collection.update_one(
            {"_id": object_id},
            {"$set": {**nuevos_datos, "fecha_actualizacion": datetime.now()}},
        )
        return redirect(url_for("recetario"))
    

    receta["ingredientes"] = ", ".join(receta["ingredientes"])
    return render_template("editar_receta.html", receta=receta)



@app.route("/perfil")
def perfil():
    if "user" not in session:
        return redirect(url_for("login"))

    email = session["user"]["email"]
    usuario = usuarios_collection.find_one({"email": email})
    if not usuario:
        return redirect(url_for("login"))

    return render_template("perfil.html", usuario=usuario)


@app.route("/editarperfil", methods=["POST"])
def editarperfil():
    if "user" not in session:
        return redirect(url_for("login"))

    email = session["user"]["email"]
    usuario = usuarios_collection.find_one({"email": email})
    if not usuario:
        return redirect(url_for("login"))

    nombre = request.form.get("nombre")
    password = request.form.get("password")

    cambios = {}
    if nombre and nombre != usuario["nombre"]:
        cambios["nombre"] = nombre
    if password:
        cambios["password"] = generate_password_hash(password)

    if cambios:
        usuarios_collection.update_one({"email": email}, {"$set": cambios})
        session["user"]["name"] = cambios.get("nombre", session["user"]["name"])
        mensaje = "Cambios guardados correctamente"
        usuario.update(cambios)
    else:
        mensaje = "No se realizaron cambios"

    return render_template("perfil.html", usuario=usuario, mensaje=mensaje)

@app.route("/objetivo")
def objetivo():
    return render_template("objetivo.html")            

if __name__ == "__main__":
    app.run(debug=True)
