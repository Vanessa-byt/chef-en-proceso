from flask import Flask, render_template, request, url_for, redirect
from pymongo import MongoClient
from typing import Optional, Dict


from ChefEnProceso import ChefEnProceso

app = Flask(__name__)


connect = ChefEnProceso("mongodb+srv://ricardorosal7335_db_user:kiraymoster39@cluster0.ixvdcur.mongodb.net/")


usuarios_collection = connect.usuarios


def obtener_usuario(email: str, contraseña: str) -> Optional[Dict]:

    usuario = usuarios_collection.find_one({"email": email, "password": contraseña})
    if usuario:
        usuario['_id'] = str(usuario['_id'])
    return usuario


@app.route("/")
def inicio():
    return render_template("nicio.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    contraseña = request.form.get("contraseña")

    usuario = obtener_usuario(email, contraseña)

    if usuario:
        return redirect(url_for("recetario"))
    else:
        return render_template("nicio.html", mensaje="Usuario o contraseña incorrectos")


if __name__ == "__main__":
    app.run(debug=True)
