# DataTab 

Aplicación web para análisis estadístico de archivos Excel.

---

# Cómo ejecutar el proyecto en tu PC

### 1. Instalar dependencias (solo la primera vez)
Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
py -m pip install fastapi uvicorn[standard] pandas openpyxl python-multipart jinja2
```

# 2. Ejecutar el servidor
```bash
py main.py
```

# 3. Abrir en el navegador
Ve a: **http://localhost:5000**

---

# Estructura del proyecto
```
datatab/
├── main.py               ← Backend (Flask + Pandas)
├── requirements.txt      ← Dependencias Python
├── uploads/              ← Aquí se guardan los archivos subidos
└── templates/
    ├── index.html        ← Página de carga
    └── analisis.html     ← Página de análisis
```

---

## Funcionalidades
- Subir archivos Excel (.xlsx, .xls) y CSV
- Seleccionar cualquier columna del archivo
- Tabla de frecuencias y porcentajes automática
- Definir rangos personalizados para datos numéricos (ej: <30, 30-39, 40+)
- Gráfico de barras interactivo
- Vista completa de los datos del archivo
- Modo oscuro / claro
- Diseño responsive (funciona en celular y PC)
