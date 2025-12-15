# 🔥 **Configuración Firebase (Opcional)**

La API puede funcionar en **modo desarrollo** sin Firebase para pruebas.

## 🚀 **Opción 1: Modo Desarrollo (Sin Firebase)**

La API ya está configurada para funcionar sin Firebase usando datos de prueba.

**Solo ejecuta:**
```bash
python app.py
```

## 🔥 **Opción 2: Conectar con Firebase**

### 1️⃣ **Obtener Credenciales**

1. Ir a [Firebase Console](https://console.firebase.google.com/)
2. Seleccionar tu proyecto LeyvaCars
3. Ir a **Configuración del proyecto** (ícono de engranaje)
4. Pestaña **Cuentas de servicio**
5. Clic en **Generar nueva clave privada**
6. Descargar el archivo JSON

### 2️⃣ **Configurar Credenciales**

1. **Renombrar** el archivo descargado a `serviceAccountKey.json`
2. **Colocar** en la carpeta `ml_similarity_api/`

```
ml_similarity_api/
├── serviceAccountKey.json  ← Aquí
├── app.py
└── src/
```

### 3️⃣ **Verificar Conexión**

```bash
python setup.py
```

## 🔧 **Estructura de Datos Firestore**

La API busca documentos en la colección `productos` con esta estructura:

```json
{
  "nombre": "Llanta Michelin 195/65 R15",
  "marca": "Michelin", 
  "modelo": "Energy Saver",
  "imagenUrl": "https://i.ibb.co/xyz/imagen.jpg",
  "categoria": "Llantas",
  "precio": 150.0,
  "stock": 10,
  "activo": true
}
```

## ⚠️ **Importante**

- El campo `imagenUrl` es **obligatorio**
- Solo se indexan productos con `activo: true`
- Las imágenes deben ser URLs públicas accesibles

## 🆘 **Troubleshooting**

**Error "Permission denied":**
- Verificar que la cuenta de servicio tenga permisos de lectura en Firestore

**Error "Collection not found":**
- Asegurarse de que existe la colección `productos` en Firestore

**Error "No products found":**
- Verificar que hay productos con `imagenUrl` válidas en Firestore