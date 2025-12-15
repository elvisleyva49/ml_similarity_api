import os
import asyncio
import numpy as np
import requests
import hashlib
from PIL import Image
import faiss
import torch
import open_clip
from typing import List, Dict, Optional, Tuple
import logging
from io import BytesIO
from pathlib import Path
import time

from .models import FirestoreProduct, ProductResult

logger = logging.getLogger(__name__)

class SimilarityEngine:
    """Motor de similitud basado en CLIP + FAISS"""
    
    def __init__(self, cache_dir: str = "cache", model_name: str = "ViT-B-32"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Usar modelo más pequeño para deploy
        is_production = os.getenv("ENVIRONMENT") == "production"
        self.model_name = "RN50" if is_production else model_name
        
        self.model = None
        self.preprocess = None
        
        # FAISS index
        self.index = None
        self.product_metadata = {}  # product_id -> metadata
        self.indexed_urls = {}  # url_hash -> product_id
        
        logger.info(f"✅ Motor de similitud inicializado (modelo: {self.model_name}, lazy loading habilitado)")
        
    def _load_clip_model(self):
        """Cargar modelo CLIP (optimizado para producción)"""
        if self.model is not None:
            return  # Ya está cargado
            
        try:
            is_production = os.getenv("ENVIRONMENT") == "production"
            
            if is_production:
                # En producción usar el modelo MÁS PEQUEÑO disponible
                model_name = "RN50"  # ResNet50 - el más ligero
                pretrained = "openai"
                logger.info(f"🤖 Cargando modelo CLIP ultra-ligero para producción: {model_name}")
            else:
                model_name = self.model_name
                pretrained = 'laion2b_s34b_b79k'
                logger.info(f"🤖 Cargando modelo CLIP: {model_name}")
            
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                model_name, 
                pretrained=pretrained
            )
            self.model.eval()
            
            # Solo CPU en producción para ahorrar RAM
            if torch.cuda.is_available() and not is_production:
                self.model = self.model.cuda()
                logger.info("🚀 Usando GPU para CLIP")
            else:
                logger.info("💻 Usando CPU para CLIP")
                
            logger.info("✅ Modelo CLIP cargado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error cargando CLIP: {e}")
            raise
    
    def _get_cache_path(self, url: str) -> Path:
        """Generar path de cache para una URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.jpg"
    
    async def _download_image(self, url: str) -> Optional[Image.Image]:
        """Descargar y cachear imagen desde URL"""
        cache_path = self._get_cache_path(url)
        
        try:
            # Verificar si existe en cache
            if cache_path.exists():
                return Image.open(cache_path).convert("RGB")
            
            # Descargar imagen
            logger.debug(f"📥 Descargando: {url[:50]}...")
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'LeyvaCars-ML-API/1.0'
            })
            response.raise_for_status()
            
            # Guardar en cache y abrir
            with open(cache_path, 'wb') as f:
                f.write(response.content)
                
            image = Image.open(BytesIO(response.content)).convert("RGB")
            logger.debug(f"✅ Imagen descargada: {image.size}")
            
            return image
            
        except Exception as e:
            logger.error(f"❌ Error descargando imagen {url}: {e}")
            return None
    
    def _extract_features(self, image: Image.Image) -> np.ndarray:
        """Extraer características de una imagen usando CLIP"""
        try:
            # Cargar modelo si no está cargado (lazy loading)
            if self.model is None:
                self._load_clip_model()
            
            # Preprocesar imagen
            image_input = self.preprocess(image).unsqueeze(0)
            
            # Solo CPU en producción para ahorrar RAM
            is_production = os.getenv("ENVIRONMENT") == "production"
            if torch.cuda.is_available() and not is_production:
                image_input = image_input.cuda()
            
            # Extraer características
            with torch.no_grad():
                features = self.model.encode_image(image_input)
                features = features / features.norm(dim=1, keepdim=True)  # Normalizar
                
            return features.squeeze().cpu().numpy()
            
        except Exception as e:
            logger.error(f"Error extrayendo características: {e}")
            return None
    
    async def sync_products(self, productos: List[FirestoreProduct]):
        """Sincronizar productos desde Firestore"""
        logger.info(f"🔄 Sincronizando {len(productos)} productos...")
        
        features_list = []
        valid_products = []
        
        for i, producto in enumerate(productos):
            # Solo procesar productos con imagen
            if not producto.imagenUrl:
                continue
                
            logger.info(f"📷 Procesando {i+1}/{len(productos)}: {producto.nombre[:30]}...")
            
            # Descargar y extraer características
            image = await self._download_image(producto.imagenUrl)
            if image is None:
                logger.warning(f"⚠️ No se pudo procesar imagen: {producto.nombre}")
                continue
                
            features = self._extract_features(image)
            if features is None:
                continue
                
            features_list.append(features)
            valid_products.append(producto)
            
            # Guardar metadata
            self.product_metadata[producto.id] = {
                'nombre': producto.nombre,
                'marca': producto.marca,
                'modelo': producto.modelo,
                'imagen_url': producto.imagenUrl,
                'categoria': producto.categoria,
                'precio': producto.precio,
                'stock': producto.stock
            }
            
            # Mapear URL hash a product_id
            url_hash = hashlib.md5(producto.imagenUrl.encode()).hexdigest()
            self.indexed_urls[url_hash] = producto.id
        
        if not features_list:
            logger.warning("⚠️ No se pudieron procesar imágenes")
            return
            
        # Crear índice FAISS
        features_array = np.vstack(features_list)
        dimension = features_array.shape[1]
        
        # Usar IndexFlatIP para similitud coseno (producto punto)
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(features_array)
        
        logger.info(f"✅ Índice FAISS creado: {len(valid_products)} productos indexados")
        
        # Mapear índices FAISS a product_ids
        self.faiss_to_product = [p.id for p in valid_products]
    
    async def search_similar(
        self, 
        image_url: str, 
        top_k: int = 5, 
        min_similarity: float = 0.1
    ) -> List[ProductResult]:
        """Buscar productos similares a una imagen"""
        
        if self.index is None:
            raise Exception("Índice no inicializado. Ejecuta sync_products primero.")
        
        # Descargar imagen de consulta
        query_image = await self._download_image(image_url)
        if query_image is None:
            raise Exception("No se pudo descargar la imagen de consulta")
        
        # Extraer características
        query_features = self._extract_features(query_image)
        if query_features is None:
            raise Exception("No se pudieron extraer características de la imagen")
        
        # Buscar similares usando FAISS
        query_vector = query_features.reshape(1, -1)
        similarities, indices = self.index.search(query_vector, min(top_k * 2, len(self.faiss_to_product)))
        
        # Convertir a resultados
        results = []
        for rank, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
            # FAISS devuelve similitud coseno (mayor = más similar)
            similarity_score = float(similarity)
            
            if similarity_score < min_similarity:
                continue
                
            product_id = self.faiss_to_product[idx]
            metadata = self.product_metadata[product_id]
            
            result = ProductResult(
                product_id=product_id,
                nombre=metadata['nombre'],
                marca=metadata.get('marca'),
                modelo=metadata.get('modelo'),
                imagen_url=metadata['imagen_url'],
                similarity_score=similarity_score,
                rank=rank + 1,
                categoria=metadata.get('categoria'),
                precio=metadata.get('precio'),
                stock=metadata.get('stock')
            )
            
            results.append(result)
            
            if len(results) >= top_k:
                break
        
        logger.info(f"🎯 Encontrados {len(results)} productos similares")
        return results
    
    def get_indexed_count(self) -> int:
        """Obtener número de productos indexados"""
        return len(self.product_metadata)
    
    def clear_cache(self):
        """Limpiar cache de imágenes"""
        try:
            import shutil
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            logger.info("🗑️ Cache limpiado")
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")