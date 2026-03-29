"""
Configuración de conexión a MongoDB para el proyecto de scraping de combustible.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timezone
import os


class DatabaseConfig:
    """
    Clase para gestionar la conexión y operaciones con MongoDB.
    """

    def __init__(self, host: str = "localhost", port: int = 27017,
                 db_name: str = "combustible_alzira",
                 collection_name: str = "precios_combustible",
                 username: str = None, password: str = None):
        """
        Inicializa la conexión a MongoDB.

        Args:
            host: Host de MongoDB (default: localhost)
            port: Puerto de MongoDB (default: 27017)
            db_name: Nombre de la base de datos
            collection_name: Nombre de la colección
            username: Usuario de MongoDB (opcional, por defecto usa MONGO_USER env)
            password: Contraseña de MongoDB (opcional, por defecto usa MONGO_PASS env)
        """
        self.host = os.getenv("MONGO_HOST", host)
        self.port = int(os.getenv("MONGO_PORT", port))
        self.db_name = db_name
        self.collection_name = collection_name
        self.username = os.getenv("MONGO_USER", username)
        self.password = os.getenv("MONGO_PASS", password)
        self.client = None
        self.db = None
        self.collection = None
        self._connect()

    def _connect(self) -> bool:
        """
        Establece la conexión con MongoDB.

        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario.
        """
        try:
            # Si hay credenciales, usar autenticación
            if self.username and self.password:
                self.client = MongoClient(
                    self.host,
                    self.port,
                    username=self.username,
                    password=self.password,
                    authSource="admin",
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000
                )
            else:
                self.client = MongoClient(
                    self.host,
                    self.port,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000
                )

            # Verificar conexión
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]

            # Crear índices para optimizar consultas
            self._create_indexes()

            print(f"[DB] Conectado exitosamente a MongoDB: {self.host}:{self.port}")
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"[DB] Error al conectar a MongoDB: {e}")
            return False

    def _create_indexes(self) -> None:
        """
        Crea índices en la colección para optimizar las consultas.
        """
        try:
            # Índice por timestamp para consultas temporales
            self.collection.create_index("timestamp")
            # Índice por nombre de gasolinera
            self.collection.create_index("nombre")
            # Índice compuesto para consultas por fecha y gasolinera
            self.collection.create_index([("timestamp", -1), ("nombre", 1)])
        except Exception as e:
            # Los índices son opcionales, no fallar si no se pueden crear
            pass

    def insert_precio(self, datos: dict) -> bool:
        """
        Inserta un registro de precio de combustible.

        Args:
            datos: Diccionario con los datos del precio

        Returns:
            bool: True si la inserción fue exitosa
        """
        try:
            if self.collection is None:
                print("[DB] Error: No hay conexión con la base de datos")
                return False

            # Añadir timestamp si no existe
            if "timestamp" not in datos:
                datos["timestamp"] = datetime.now(timezone.utc).isoformat()

            result = self.collection.insert_one(datos)
            print(f"[DB] Registro insertado con ID: {result.inserted_id}")
            return True

        except Exception as e:
            print(f"[DB] Error al insertar datos: {e}")
            return False

    def insert_precios_lote(self, registros: list) -> int:
        """
        Inserta múltiples registros de precios de combustible.

        Args:
            registros: Lista de diccionarios con los datos

        Returns:
            int: Número de registros insertados
        """
        try:
            if self.collection is None:
                print("[DB] Error: No hay conexión con la base de datos")
                return 0

            # Añadir timestamp a cada registro
            for registro in registros:
                if "timestamp" not in registro:
                    registro["timestamp"] = datetime.now(timezone.utc).isoformat()

            result = self.collection.insert_many(registros)
            print(f"[DB] {len(result.inserted_ids)} registros insertados")
            return len(result.inserted_ids)

        except Exception as e:
            print(f"[DB] Error al insertar lote de datos: {e}")
            return 0

    def get_ultimos_precios(self, limite: int = 100) -> list:
        """
        Obtiene los últimos precios registrados.

        Args:
            limite: Número máximo de registros a devolver

        Returns:
            list: Lista de documentos con los precios
        """
        try:
            if self.collection is None:
                return []

            cursor = self.collection.find().sort("timestamp", -1).limit(limite)
            return list(cursor)

        except Exception as e:
            print(f"[DB] Error al obtener precios: {e}")
            return []

    def get_precios_por_fecha(self, fecha_inicio: str, fecha_fin: str) -> list:
        """
        Obtiene precios en un rango de fechas.

        Args:
            fecha_inicio: Fecha de inicio (formato ISO 8601)
            fecha_fin: Fecha de fin (formato ISO 8601)

        Returns:
            list: Lista de documentos con los precios
        """
        try:
            if self.collection is None:
                return []

            from datetime import datetime
            query = {
                "timestamp": {
                    "$gte": fecha_inicio,
                    "$lte": fecha_fin
                }
            }
            cursor = self.collection.find(query).sort("timestamp", 1)
            return list(cursor)

        except Exception as e:
            print(f"[DB] Error al obtener precios por fecha: {e}")
            return []

    def get_gasolineras_unicas(self) -> list:
        """
        Obtiene la lista de gasolineras únicas.

        Returns:
            list: Lista de nombres de gasolineras
        """
        try:
            if self.collection is None:
                return []

            pipeline = [
                {"$group": {"_id": "$nombre"}},
                {"$sort": {"_id": 1}}
            ]
            cursor = self.collection.aggregate(pipeline)
            return [doc["_id"] for doc in cursor]

        except Exception as e:
            print(f"[DB] Error al obtener gasolineras: {e}")
            return []

    def get_ultimo_precio_por_gasolinera(self) -> list:
        """
        Obtiene el último precio registrado por cada gasolinera.

        Returns:
            list: Lista con el último precio de cada gasolinera
        """
        try:
            if self.collection is None:
                return []

            pipeline = [
                {"$sort": {"timestamp": -1}},
                {"$group": {
                    "_id": "$nombre",
                    "ultimo_precio": {"$first": "$$ROOT"}
                }},
                {"$replaceRoot": {"newRoot": "$ultimo_precio"}}
            ]
            cursor = self.collection.aggregate(pipeline)
            return list(cursor)

        except Exception as e:
            print(f"[DB] Error al obtener últimos precios: {e}")
            return []

    def close(self) -> None:
        """
        Cierra la conexión con MongoDB.
        """
        if self.client:
            self.client.close()
            print("[DB] Conexión cerrada")

    def __enter__(self):
        """Soporte para context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión al salir del context manager."""
        self.close()


# Función de prueba de conexión
def test_connection():
    """
    Función para probar la conexión a MongoDB.
    """
    print("Probando conexión a MongoDB...")
    db = DatabaseConfig()
    if db.collection is not None:
        print("✓ Conexión exitosa")
        print(f"  Base de datos: {db.db_name}")
        print(f"  Colección: {db.collection_name}")
        db.close()
        return True
    else:
        print("✗ Error de conexión")
        return False


if __name__ == "__main__":
    test_connection()