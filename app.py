
from flask import Flask, render_template, request, url_for, redirect
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient("mongodb://localhost:27017/")
db = client["usuariosDB"]                
usuarios_collection = db["usuarios"]     
tareas_collection = db["tareas"]


def obtener_usuario(email: str, contraseña: str) -> Optional[Dict]:
    usuario = usuarios_collection.find_one({"email": email, "contraseña": contraseña})
    if usuario:
        usuario['_id'] = str(usuario['_id'])
    return usuario


if __name__ == "__main__":
    app.run(debug=True)
