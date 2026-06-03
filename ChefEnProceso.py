from datetime import datetime, timedelta
from typing import Dict, List, Optional

from bson.errors import InvalidId
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError


class ChefEnProceso:
    def __init__(self, uri: str = "mongodb://localhost:27017/"):
        """Inicializar conexión a MongoDB."""
        try:
            self.cliente = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.cliente.admin.command("ping")
            self.db = self.cliente["recetario"]
            self.tareas = self.db["recetas"]
            self.usuarios = self.db["usuarios"]
            self.guardar= self.db["recetas_guardadas"]
            self._crear_indices()
            print("Conectado a MongoDB")
        except ConnectionFailure:
            print("Error: no se pudo conectar a MongoDB")
            raise

    def _crear_indices(self):
        """Crear índices para mejorar rendimiento y búsquedas."""
        self.usuarios.create_index("email", unique=True)
        self.tareas.create_index([("usuario_id", 1), ("fecha_creacion", -1)])
        self.tareas.create_index("estado")
        self.tareas.create_index(
            [
                ("titulo", "text"),
                ("descripcion", "text"),
                ("nombre", "text"),
                ("ingredientes", "text"),
                ("pasos", "text"),
            ],
            default_language="spanish",
        )

    def _object_id(self, value: str) -> Optional[ObjectId]:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None

    def crear_usuario(self, nombre: str, email: str, contrasena: str) -> Optional[str]:
        """Crear un nuevo usuario."""
        try:
            resultado = self.usuarios.insert_one(
                {
                    "nombre": nombre,
                    "email": email,
                    "password": contrasena,
                    "fecha_registro": datetime.now(),
                    "activo": True,
                }
            )
            return str(resultado.inserted_id)
        except DuplicateKeyError:
            print(f"Error: el email {email} ya está registrado")
            return None

    def obtener_usuario(self, usuario_id: str) -> Optional[Dict]:
        """Obtener usuario por ID."""
        object_id = self._object_id(usuario_id)
        if not object_id:
            return None

        usuario = self.usuarios.find_one({"_id": object_id})
        if usuario:
            usuario["_id"] = str(usuario["_id"])
        return usuario

    def obtener_usuario2(self, email: str, contrasena: str) -> Optional[Dict]:
        """Obtener usuario por email y contraseña."""
        usuario = self.usuarios.find_one({"email": email, "password": contrasena})
        if usuario:
            usuario["_id"] = str(usuario["_id"])
        return usuario

    def crear_tarea(
        self,
        usuario_id: str,
        titulo: str,
        descripcion: str = "",
        fecha_limite: Optional[datetime] = None,
    ) -> Optional[str]:
        """Crear una nueva tarea para un usuario."""
        object_id = self._object_id(usuario_id)
        if not object_id or not self.obtener_usuario(usuario_id):
            print(f"Error: usuario {usuario_id} no existe")
            return None

        tarea = {
            "usuario_id": object_id,
            "titulo": titulo,
            "descripcion": descripcion,
            "estado": "pendiente",
            "fecha_creacion": datetime.now(),
            "fecha_limite": fecha_limite or datetime.now() + timedelta(days=7),
            "completada": False,
            "etiquetas": [],
        }

        resultado = self.tareas.insert_one(tarea)
        return str(resultado.inserted_id)

    def obtener_tareas_usuario(
        self, usuario_id: str, estado: Optional[str] = None
    ) -> List[Dict]:
        """Obtener tareas de un usuario, opcionalmente filtradas por estado."""
        object_id = self._object_id(usuario_id)
        if not object_id:
            return []

        filtro = {"usuario_id": object_id}
        if estado:
            filtro["estado"] = estado

        return [self._serializar_tarea(tarea) for tarea in self.tareas.find(filtro).sort("fecha_creacion", -1)]

    def actualizar_estado_tarea(self, tarea_id: str, nuevo_estado: str) -> bool:
        """Actualizar el estado de una tarea."""
        estados_validos = ["pendiente", "en_progreso", "completada", "cancelada"]
        object_id = self._object_id(tarea_id)
        if not object_id:
            return False

        if nuevo_estado not in estados_validos:
            print(f"Error: estado '{nuevo_estado}' no válido")
            return False

        resultado = self.tareas.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "estado": nuevo_estado,
                    "completada": nuevo_estado == "completada",
                    "fecha_actualizacion": datetime.now(),
                }
            },
        )
        return resultado.modified_count > 0

    def agregar_etiqueta(self, tarea_id: str, etiqueta: str) -> bool:
        """Agregar etiqueta a una tarea."""
        object_id = self._object_id(tarea_id)
        if not object_id:
            return False

        resultado = self.tareas.update_one(
            {"_id": object_id}, {"$addToSet": {"etiquetas": etiqueta}}
        )
        return resultado.modified_count > 0

    def eliminar_tarea(self, tarea_id: str) -> bool:
        """Eliminar una tarea."""
        object_id = self._object_id(tarea_id)
        if not object_id:
            return False

        resultado = self.tareas.delete_one({"_id": object_id})
        return resultado.deleted_count > 0

    def estadisticas_usuario(self, usuario_id: str) -> Dict:
        """Obtener estadísticas de tareas de un usuario."""
        object_id = self._object_id(usuario_id)
        if not object_id:
            return {"total": 0, "por_estado": {}, "ultima_actividad": None}

        pipeline = [
            {"$match": {"usuario_id": object_id}},
            {
                "$group": {
                    "_id": "$estado",
                    "cantidad": {"$sum": 1},
                    "fecha_ultima": {"$max": "$fecha_creacion"},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        estadisticas = {"total": 0, "por_estado": {}, "ultima_actividad": None}

        for resultado in self.tareas.aggregate(pipeline):
            estado = resultado["_id"]
            cantidad = resultado["cantidad"]
            estadisticas["por_estado"][estado] = cantidad
            estadisticas["total"] += cantidad

            if (
                not estadisticas["ultima_actividad"]
                or resultado["fecha_ultima"] > estadisticas["ultima_actividad"]
            ):
                estadisticas["ultima_actividad"] = resultado["fecha_ultima"]

        return estadisticas

    def buscar_tareas(self, texto: str) -> List[Dict]:
        """Buscar tareas o recetas por texto."""
        tareas = self.tareas.find({"$text": {"$search": texto}}).sort(
            [("score", {"$meta": "textScore"})]
        )
        return [self._serializar_tarea(tarea) for tarea in tareas]

    def tareas_urgentes(self, horas: int = 24) -> List[Dict]:
        """Encontrar tareas que vencen en las próximas N horas."""
        ahora = datetime.now()
        limite = ahora + timedelta(hours=horas)

        tareas = self.tareas.find(
            {
                "estado": {"$ne": "completada"},
                "fecha_limite": {"$gte": ahora, "$lte": limite},
            }
        ).sort("fecha_limite", 1)

        return [self._serializar_tarea(tarea) for tarea in tareas]

    def _serializar_tarea(self, tarea: Dict) -> Dict:
        tarea["_id"] = str(tarea["_id"])
        if "usuario_id" in tarea:
            tarea["usuario_id"] = str(tarea["usuario_id"])
        return tarea

    def cerrar_conexion(self):
        """Cerrar conexión a MongoDB."""
        if self.cliente:
            self.cliente.close()
            print("Conexión cerrada")
