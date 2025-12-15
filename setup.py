"""
Script de inicialización para configurar la API ML
Ejecuta este script la primera vez para verificar que todo funcione
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.firestore_client import FirestoreClient
from src.similarity_engine import SimilarityEngine

async def setup_api():
    """Configurar y probar la API ML"""
    
    print("🚀 LeyvaCars ML API - Setup Inicial")
    print("=" * 50)
    
    try:
        # 1. Probar conexión a Firestore
        print("\n1️⃣ Probando conexión a Firestore...")
        firestore_client = FirestoreClient()
        
        if firestore_client.test_connection():
            print("✅ Firestore conectado correctamente")
        else:
            print("❌ Error conectando a Firestore")
            return False
        
        # 2. Cargar modelo CLIP
        print("\n2️⃣ Cargando modelo CLIP...")
        similarity_engine = SimilarityEngine()
        print("✅ Modelo CLIP cargado exitosamente")
        
        # 3. Obtener productos desde Firestore
        print("\n3️⃣ Obteniendo productos desde Firestore...")
        productos = await firestore_client.get_productos()
        print(f"✅ Obtenidos {len(productos)} productos con imágenes")
        
        if len(productos) == 0:
            print("⚠️  No se encontraron productos con imágenes en Firestore")
            print("   Asegúrate de tener productos con el campo 'imagenUrl'")
            return False
        
        # 4. Indexar productos (puede tomar tiempo)
        print("\n4️⃣ Indexando productos con CLIP + FAISS...")
        print("   (Esto puede tomar varios minutos la primera vez)")
        
        await similarity_engine.sync_products(productos)
        
        indexed_count = similarity_engine.get_indexed_count()
        print(f"✅ Indexados {indexed_count} productos exitosamente")
        
        # 5. Verificar que todo funciona
        print("\n5️⃣ Verificación final...")
        if indexed_count > 0:
            print("✅ API ML lista para uso!")
            print(f"📊 Productos indexados: {indexed_count}")
            print("🌐 Puedes iniciar la API con: python app.py")
            return True
        else:
            print("❌ No se pudieron indexar productos")
            return False
            
    except Exception as e:
        print(f"❌ Error durante setup: {e}")
        return False

def check_requirements():
    """Verificar dependencias"""
    print("🔍 Verificando dependencias...")
    
    required_packages = [
        'fastapi', 'torch', 'open_clip_torch', 
        'faiss-cpu', 'firebase_admin', 'requests'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Paquetes faltantes: {', '.join(missing)}")
        print("   Ejecuta: pip install -r requirements.txt")
        return False
    
    print("✅ Todas las dependencias están instaladas")
    return True

def check_firebase_credentials():
    """Verificar credenciales de Firebase"""
    cred_path = Path("serviceAccountKey.json")
    
    if not cred_path.exists():
        print("❌ No se encontró serviceAccountKey.json")
        print("   Descárgalo desde Firebase Console > Configuración > Cuentas de servicio")
        return False
    
    print("✅ Credenciales de Firebase encontradas")
    return True

async def main():
    """Función principal de setup"""
    
    # Verificaciones preliminares
    if not check_requirements():
        return
    
    if not check_firebase_credentials():
        return
    
    # Setup principal
    success = await setup_api()
    
    if success:
        print("\n🎉 Setup completado exitosamente!")
        print("\n📋 Próximos pasos:")
        print("   1. Ejecutar: python app.py")
        print("   2. Verificar: http://localhost:8000/health")
        print("   3. Usar desde Flutter app")
    else:
        print("\n💥 Setup falló. Revisa los errores arriba.")

if __name__ == "__main__":
    asyncio.run(main())