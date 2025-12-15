import requests
import json
from typing import List, Dict, Optional
import logging
import os

from .models import FirestoreProduct

logger = logging.getLogger(__name__)

class FirestoreClient:
    """Cliente para interactuar con Firestore usando REST API (sin credenciales)"""
    
    def __init__(self, project_id: str = "leyvacarsmovil-4708a", dev_mode: bool = False):
        self.project_id = project_id
        self.collection_name = "productos"
        self.dev_mode = dev_mode
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
        
        if dev_mode:
            logger.info("🔧 Modo desarrollo activado - usando datos demo")
        else:
            logger.info(f"🔥 Conectando a Firestore: {project_id}")
    
    async def get_productos(self) -> List[FirestoreProduct]:
        """Obtener todos los productos activos de Firestore o datos de prueba"""
        
        # Si está en modo desarrollo, devolver datos de prueba
        if self.dev_mode:
            return self._get_demo_products()
        
        try:
            logger.info("📊 Obteniendo productos desde Firestore...")
            
            # Hacer request a Firestore REST API
            url = f"{self.base_url}/{self.collection_name}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                productos = []
                
                # Procesar documentos
                if "documents" in data:
                    for doc in data["documents"]:
                        try:
                            # Extraer ID del documento
                            doc_id = doc["name"].split("/")[-1]
                            fields = doc.get("fields", {})
                            
                            # Convertir campos de Firestore a formato Python
                            producto_data = self._convert_firestore_fields(fields)
                            producto_data["id"] = doc_id
                            
                            # Solo incluir productos activos con imagen
                            if producto_data.get("activo", True) and producto_data.get("imagenUrl"):
                                producto = FirestoreProduct(**producto_data)
                                productos.append(producto)
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Error procesando producto {doc_id}: {e}")
                            continue
                
                logger.info(f"✅ Obtenidos {len(productos)} productos válidos")
                return productos
            
            elif response.status_code == 403:
                logger.error("❌ Error 403: Verifica las reglas de Firestore")
                logger.info("💡 Las reglas deben permitir acceso de lectura público")
                return []
            else:
                logger.error(f"❌ Error Firestore: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo productos: {e}")
            return []
    
    def _convert_firestore_fields(self, fields: Dict) -> Dict:
        """Convertir campos de Firestore REST API a formato Python"""
        result = {}
        
        for key, value in fields.items():
            if "stringValue" in value:
                result[key] = value["stringValue"]
            elif "doubleValue" in value:
                result[key] = float(value["doubleValue"])
            elif "integerValue" in value:
                result[key] = int(value["integerValue"])
            elif "booleanValue" in value:
                result[key] = value["booleanValue"]
            elif "nullValue" in value:
                result[key] = None
            else:
                # Para otros tipos, intentar extraer el valor
                if len(value) == 1:
                    result[key] = list(value.values())[0]
                else:
                    result[key] = str(value)
        
        return result
    
    async def get_producto_by_id(self, product_id: str) -> Optional[FirestoreProduct]:
        """Obtener un producto específico por ID"""
        try:
            url = f"{self.base_url}/{self.collection_name}/{product_id}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                doc = response.json()
                fields = doc.get("fields", {})
                producto_data = self._convert_firestore_fields(fields)
                producto_data["id"] = product_id
                return FirestoreProduct(**producto_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo producto {product_id}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Probar conexión con Firestore"""
        if self.dev_mode:
            logger.info("✅ Modo desarrollo - Conexión simulada OK")
            return True
            
        try:
            # Intentar obtener la colección
            url = f"{self.base_url}/{self.collection_name}"
            response = requests.get(url, timeout=5)
            
            if response.status_code in [200, 404]:  # 404 es OK si la colección está vacía
                logger.info("✅ Conexión Firestore OK")
                return True
            else:
                logger.error(f"❌ Test de conexión falló: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Test de conexión falló: {e}")
            return False
    
    def _get_demo_products(self) -> List[FirestoreProduct]:
        """Productos de demostración para modo desarrollo"""
        logger.info("🔧 Cargando productos de demostración...")
        
        return [
            FirestoreProduct(
                id="demo1",
                nombre="Llanta Michelin 195/65 R15",
                marca="Michelin",
                modelo="Energy Saver",
                imagenUrl="https://i.ibb.co/example1.jpg",
                categoria="Llantas",
                precio=150.0,
                stock=10
            ),
            FirestoreProduct(
                id="demo2", 
                nombre="Amortiguador Delantero",
                marca="Monroe",
                modelo="OESpectrum",
                imagenUrl="https://i.ibb.co/example2.jpg",
                categoria="Suspensión",
                precio=80.0,
                stock=5
            ),
            FirestoreProduct(
                id="demo3",
                nombre="Faro Delantero LED",
                marca="Osram",
                modelo="LEDriving",
                imagenUrl="https://i.ibb.co/example3.jpg", 
                categoria="Iluminación",
                precio=120.0,
                stock=8
            )
        ]