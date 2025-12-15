# 🚀 **Guía de Deploy - Render.com**

## 📋 **Pasos para Deploy Gratuito:**

### 1. **Preparación local:**
```bash
# Verificar que todo funcione localmente
cd ml_similarity_api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### 2. **Subir a GitHub:**
```bash
# Crear repo en GitHub (si no existe)
git init
git add .
git commit -m "API ML LeyvaCars lista para deploy"
git remote add origin https://github.com/TU_USUARIO/leyvacarsmovil-ml-api.git
git push -u origin main
```

### 3. **Deploy en Render:**

1. **Ve a:** https://render.com (crear cuenta gratis)

2. **Conecta GitHub:** Autorizar acceso a tu repositorio

3. **Crear Web Service:**
   - **Name:** `leyvacarsmovil-ml-api`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`

4. **Variables de Entorno:**
   ```
   ENVIRONMENT=production
   FIREBASE_PROJECT_ID=leyvacarsmovil
   HOST=0.0.0.0
   ```

5. **Deploy:** Click "Deploy" ✨

### 4. **Actualizar Flutter:**
```dart
// Cambiar en similitud_service.dart:
static const String _mlApiBaseUrl = 'https://leyvacarsmovil-ml-api.onrender.com';
```

## 🎯 **Características del Plan Gratuito:**

- ✅ **750 horas/mes** (suficiente para desarrollo)
- ✅ **512 MB RAM** (ajustado para CLIP)
- ✅ **Deploy automático** desde GitHub
- ✅ **HTTPS gratuito**
- ✅ **Dominio incluido**: `tu-app.onrender.com`

## ⚡ **Ventajas vs PHP Hosting:**

| Característica | Render (Python) | InfinityFree (PHP) |
|---|---|---|
| **ML Libraries** | ✅ Completo | ❌ No soporta |
| **APIs complejas** | ✅ FastAPI | ⭐ Básico |
| **Auto-deploy** | ✅ GitHub | ❌ Manual |
| **HTTPS** | ✅ Automático | ⭐ Manual |
| **Escalabilidad** | ✅ Fácil | ❌ Limitado |

## 🔧 **Optimizaciones:**

- **Cold Start:** ~30-60s (normal en plan gratuito)
- **Keep Alive:** Configurar ping cada 14 min
- **Cache:** Los modelos se descargan una vez por deploy

## 🌐 **Alternativas por si Render no funciona:**

1. **Railway:** https://railway.app (más rápido)
2. **Fly.io:** https://fly.io (muy bueno para ML)
3. **PythonAnywhere:** https://pythonanywhere.com (específico Python)

¿Listo para el deploy? 🚀