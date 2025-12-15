from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Union
from datetime import datetime

class SimilarityRequest(BaseModel):
    """Request para búsqueda de similitud"""
    image_url: str
    top_k: int = 5
    min_similarity: float = 0.1
    
class ProductResult(BaseModel):
    """Resultado de un producto similar"""
    product_id: str
    nombre: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    imagen_url: str
    similarity_score: float
    rank: int
    categoria: Optional[str] = None
    precio: Optional[float] = None
    stock: Optional[int] = None
    
class SimilarityResponse(BaseModel):
    """Respuesta de búsqueda de similitud"""
    success: bool
    results: List[ProductResult]
    total_found: int
    processing_time: float
    message: str
    timestamp: datetime = datetime.now()

class FirestoreProduct(BaseModel):
    """Modelo de producto de Firestore"""
    id: str
    nombre: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    imagenUrl: Optional[str] = None
    categoria: Optional[str] = None
    precio: Optional[float] = None
    stock: Optional[int] = None
    fechaCreacion: Optional[Union[str, int]] = None  # Acepta timestamp o string
    activo: bool = True