
from flask import Flask, render_template, request, url_for, redirect
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient("mongodb+srv://ricardorosal7335_db_user:kiraymoster39@cluster0.ixvdcur.mongodb.net/")
db = client["Recetario"]
usuarios_collection = db["usuarios"]


def obtener_usuario(email: str, contraseña: str) -> Optional[Dict]:
    usuario = usuarios_collection.find_one({"email": email, "contraseña": contraseña})
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
connect = ChefEnProceso(client)
if __name__ == "__main__":
    app.run(debug=True)
