from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import os
import logging
from typing import List, Optional
import time
from datetime import datetime

# Importar nuestros módulos
from src.similarity_engine import SimilarityEngine
from src.firestore_client import FirestoreClient
from src.models import SimilarityRequest, SimilarityResponse, ProductResult
from config import FIREBASE_PROJECT_ID

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Instancias globales
similarity_engine: Optional[SimilarityEngine] = None
firestore_client: Optional[FirestoreClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejar el ciclo de vida de la aplicación"""
    global similarity_engine, firestore_client
    
    logger.info("🚀 Iniciando LeyvaCars ML API...")
    
    try:
        # Usar configuración del archivo config.py
        dev_mode = False  # Usar Firebase real
        
        # Inicializar cliente Firestore
        logger.info(f"📊 Configurando Firestore para proyecto: {FIREBASE_PROJECT_ID}")
        firestore_client = FirestoreClient(project_id=FIREBASE_PROJECT_ID, dev_mode=dev_mode)
        
        # Inicializar motor de similitud
        logger.info("🤖 Cargando modelo CLIP...")
        similarity_engine = SimilarityEngine()
        
        # Sincronizar productos (demo o Firestore)
        logger.info("🔄 Sincronizando productos...")
        productos = await firestore_client.get_productos()
        
        if productos:
            await similarity_engine.sync_products(productos)
            logger.info("✅ API lista! Productos indexados: {}".format(
                similarity_engine.get_indexed_count()
            ))
        else:
            logger.warning("⚠️ No hay productos para indexar")
        
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")
        # En modo desarrollo, continuar aunque falle algo
        if 'dev_mode' not in locals() or not dev_mode:
            raise
        else:
            logger.info("🔧 Continuando en modo desarrollo...")
    
    yield  # La aplicación está ejecutándose
    
    # Cleanup al cerrar
    logger.info("🔄 Cerrando API...")

# Crear aplicación FastAPI con lifespan
app = FastAPI(
    title="LeyvaCars ML Similarity API",
    description="API de búsqueda por similitud de imágenes para autopartes",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS para permitir requests desde Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "LeyvaCars ML Similarity API",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Verificar estado de la API"""
    try:
        indexed_count = similarity_engine.get_indexed_count() if similarity_engine else 0
        firestore_status = "development_mode" if (firestore_client and firestore_client.dev_mode) else ("connected" if firestore_client else "disconnected")
        
        return {
            "status": "healthy",
            "mode": "development" if (firestore_client and firestore_client.dev_mode) else "production",
            "services": {
                "similarity_engine": "running" if similarity_engine else "not_loaded",
                "firestore": firestore_status,
                "indexed_products": indexed_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.post("/search-similar", response_model=SimilarityResponse)
async def search_similar_images(request: SimilarityRequest):
    """
    Buscar productos similares a una imagen
    """
    start_time = time.time()
    
    try:
        if not similarity_engine:
            raise HTTPException(status_code=503, detail="Similarity engine not initialized")
        
        logger.info(f"🔍 Buscando similares para: {request.image_url[:50]}...")
        
        # Realizar búsqueda de similitud
        results = await similarity_engine.search_similar(
            image_url=request.image_url,
            top_k=request.top_k,
            min_similarity=request.min_similarity
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Encontrados {len(results)} resultados en {processing_time:.2f}s")
        
        return SimilarityResponse(
            success=True,
            results=results,
            total_found=len(results),
            processing_time=processing_time,
            message=f"Found {len(results)} similar products"
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Error en búsqueda: {e}")
        
        return SimilarityResponse(
            success=False,
            results=[],
            total_found=0,
            processing_time=processing_time,
            message=f"Search failed: {str(e)}"
        )

@app.post("/sync-products")
async def sync_products(background_tasks: BackgroundTasks):
    """
    Sincronizar productos desde Firestore (en background)
    """
    try:
        if not firestore_client or not similarity_engine:
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        # Ejecutar en background para no bloquear
        background_tasks.add_task(perform_sync)
        
        return {
            "success": True,
            "message": "Product sync started in background",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Sync initiation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def perform_sync():
    """Realizar sincronización en background"""
    try:
        logger.info("🔄 Iniciando sincronización de productos...")
        productos = await firestore_client.get_productos()
        await similarity_engine.sync_products(productos)
        logger.info(f"✅ Sincronización completada: {len(productos)} productos")
    except Exception as e:
        logger.error(f"❌ Error en sincronización: {e}")

@app.get("/stats")
async def get_stats():
    """Obtener estadísticas de la API"""
    try:
        return {
            "indexed_products": similarity_engine.get_indexed_count() if similarity_engine else 0,
            "firestore_connection": "active" if firestore_client else "inactive",
            "model_loaded": similarity_engine is not None,
            "uptime": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 8000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🌟 Iniciando servidor en {HOST}:{PORT}")
    
    # Configurar para producción vs desarrollo
    is_production = os.getenv("ENVIRONMENT") == "production"
    
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=not is_production,  # Solo reload en desarrollo
        log_level="info",
        workers=1 if is_production else 1  # Usar 1 worker para ML
    )