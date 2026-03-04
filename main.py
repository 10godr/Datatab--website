import os
import re
import shutil
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="DataTab")

os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────
#  MODELOS
# ─────────────────────────────────────────────

class AnalizarRequest(BaseModel):
    columna: str
    rangos: Optional[List[str]] = []


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────

def read_file(filepath: str) -> pd.DataFrame:
    if filepath.lower().endswith('.csv'):
        return pd.read_csv(filepath)
    return pd.read_excel(filepath)


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}


def calcular_frecuencias(df: pd.DataFrame, columna: str):
    serie = df[columna].dropna()
    total = len(serie)
    es_numerica = pd.api.types.is_numeric_dtype(serie)
    conteo = serie.value_counts().reset_index()
    conteo.columns = ['valor', 'frecuencia']
    conteo['porcentaje'] = (conteo['frecuencia'] / total * 100).round(2)
    resultado = conteo.to_dict(orient='records')
    for r in resultado:
        r['valor'] = str(r['valor'])
    return resultado, es_numerica, total


def calcular_frecuencias_con_rangos(df: pd.DataFrame, columna: str, rangos_texto: List[str]):
    serie = df[columna].dropna()
    total = len(serie)
    resultado = []
    for rango in rangos_texto:
        rango = rango.strip()
        if not rango:
            continue
        etiqueta = rango
        m = re.match(r'^[<＜]\s*(\d+\.?\d*)$', rango)
        if m:
            val = float(m.group(1))
            frecuencia = int((serie < val).sum())
            resultado.append({'valor': etiqueta, 'frecuencia': frecuencia, 'porcentaje': round(frecuencia / total * 100, 2)})
            continue
        m = re.match(r'^(>=?|≥)\s*(\d+\.?\d*)$', rango)
        if m:
            op, val = m.group(1), float(m.group(2))
            frecuencia = int((serie >= val).sum() if op in ('>=', '≥') else (serie > val).sum())
            resultado.append({'valor': etiqueta, 'frecuencia': frecuencia, 'porcentaje': round(frecuencia / total * 100, 2)})
            continue
        m = re.match(r'^(\d+\.?\d*)\s*\+$', rango)
        if m:
            val = float(m.group(1))
            frecuencia = int((serie >= val).sum())
            resultado.append({'valor': etiqueta, 'frecuencia': frecuencia, 'porcentaje': round(frecuencia / total * 100, 2)})
            continue
        m = re.match(r'^(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)$', rango)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            frecuencia = int(((serie >= a) & (serie <= b)).sum())
            resultado.append({'valor': etiqueta, 'frecuencia': frecuencia, 'porcentaje': round(frecuencia / total * 100, 2)})
            continue
        resultado.append({'valor': etiqueta, 'frecuencia': 0, 'porcentaje': 0.0})
    return resultado, total


# ─────────────────────────────────────────────
#  RUTAS
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        return HTMLResponse("Formato no soportado (solo xlsx, xls, csv)", status_code=400)
    filepath = os.path.join("uploads", file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        read_file(filepath)
    except Exception as e:
        return HTMLResponse(f"Error al leer el archivo: {str(e)}", status_code=400)
    response = RedirectResponse(url="/analisis", status_code=303)
    response.set_cookie(key="filename", value=file.filename)
    return response


@app.get("/analisis", response_class=HTMLResponse)
async def analisis(request: Request, filename: Optional[str] = Cookie(None)):
    if not filename:
        return RedirectResponse(url="/")
    filepath = os.path.join("uploads", filename)
    if not os.path.exists(filepath):
        return RedirectResponse(url="/")
    try:
        df = read_file(filepath)
        columnas = df.columns.tolist()
        preview_rows = df.head(100).fillna('').values.tolist()
        total_filas = len(df)
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}", status_code=400)
    return templates.TemplateResponse("analisis.html", {
        "request": request,
        "filename": filename,
        "columnas": columnas,
        "preview_cols": columnas,
        "preview_rows": preview_rows,
        "total_filas": total_filas,
    })


@app.post("/api/analizar")
async def api_analizar(body: AnalizarRequest, filename: Optional[str] = Cookie(None)):
    if not filename:
        return JSONResponse({"error": "No hay archivo cargado"}, status_code=400)
    filepath = os.path.join("uploads", filename)
    if not os.path.exists(filepath):
        return JSONResponse({"error": "Archivo no encontrado"}, status_code=400)
    try:
        df = read_file(filepath)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if body.columna not in df.columns:
        return JSONResponse({"error": "Columna no encontrada"}, status_code=400)
    es_numerica = pd.api.types.is_numeric_dtype(df[body.columna].dropna())
    if body.rangos and es_numerica:
        frecuencias, total = calcular_frecuencias_con_rangos(df, body.columna, body.rangos)
    else:
        frecuencias, es_numerica, total = calcular_frecuencias(df, body.columna)
    return JSONResponse({
        "columna": body.columna,
        "total": total,
        "es_numerica": es_numerica,
        "frecuencias": frecuencias,
    })


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
