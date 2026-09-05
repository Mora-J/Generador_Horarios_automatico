from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from itertools import product
from typing import List, Optional, Union, Any

from pydantic.v1 import Field
import scraper
import os

app = FastAPI(title="Generador de Horarios")

class Bloque(BaseModel):
    dia: str
    inicio: float
    fin: float

    def choca_con(self, otro: 'Bloque') -> bool:
        if self.dia != otro.dia:
            return False
        return max(self.inicio, otro.inicio) < min(self.fin, otro.fin)

class Seccion(BaseModel):
    nombre: Optional[str] = "Sin Sección"
    nrc: Optional[Any] = "N/A"
    profesor: Optional[str] = "Por Asignar"
    bloques: List[Bloque] = Field(default_factory=list)

    def choca_con(self, otra: 'Seccion') -> bool:
        return any(b1.choca_con(b2) for b1 in self.bloques for b2 in otra.bloques)

class Materia(BaseModel):
    nombre: str
    secciones: List[Seccion] = Field(default_factory=list)

def horario_valido(combo: List[tuple]) -> bool:
    secciones = [item[1] for item in combo]
    for i in range(len(secciones)):
        for j in range(i + 1, len(secciones)):
            if secciones[i].choca_con(secciones[j]):
                return False
    return True

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

# Endpoint auxiliar para evitar errores 404 de clientes desactualizados
@app.get("/api/materias")
def obtener_materias():
    return []

@app.post("/api/estudiante/importar-cedula/{cedula}")
def importar_por_cedula(cedula: int):
    try:
        materias_extraidas = scraper.obtener_materias_ucab(cedula)
        if not materias_extraidas:
            raise HTTPException(status_code=404, detail="No se encontraron materias disponibles para esta cédula.")

        return {
            "status": "ok",
            "total_cargadas": len(materias_extraidas),
            "materias": materias_extraidas
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la consulta: {str(e)}")

@app.post("/api/combinaciones")
async def calcular_combinaciones(request: Request):
    try:
        body = await request.json()
    except Exception:
        return {"total": 0, "combinaciones": []}

    # Si viene como {"materias": [...]}, extraemos la lista; si viene como [...], lo usamos directo
    if isinstance(body, dict):
        materias = body.get("materias", [])
    elif isinstance(body, list):
        materias = body
    else:
        materias = []

    if not materias:
        return {"total": 0, "combinaciones": []}

    listas_opciones = []

    for mat in materias:
        nombre_materia = mat.get("nombre", "Sin Nombre")
        secciones_crudas = mat.get("secciones", [])
        secciones_procesadas = []

        for sec in secciones_crudas:
            bloques_procesados = []
            for b in sec.get("bloques", []):
                try:
                    dia = str(b.get("dia", "")).strip()
                    inicio = float(b.get("inicio", 0))
                    fin = float(b.get("fin", 0))
                    if dia and fin > inicio:
                        bloques_procesados.append(Bloque(dia=dia, inicio=inicio, fin=fin))
                except (ValueError, TypeError):
                    continue

            if bloques_procesados:
                secciones_procesadas.append(
                    Seccion(
                        nombre=str(sec.get("nombre", "Sin Sección")),
                        nrc=sec.get("nrc", "N/A"),
                        profesor=str(sec.get("profesor", "Por Asignar")),
                        bloques=bloques_procesados
                    )
                )

        if secciones_procesadas:
            opciones_materia = [(nombre_materia, sec) for sec in secciones_procesadas]
            listas_opciones.append(opciones_materia)

    if not listas_opciones:
        return {"total": 0, "combinaciones": []}

    producto = product(*listas_opciones)
    validas = []

    for combo in producto:
        if horario_valido(list(combo)):
            horario_formateado = []
            for item in combo:
                nombre_mat = item[0]
                sec = item[1]
                horario_formateado.append({
                    "materia": nombre_mat,
                    "seccion": sec.nombre,
                    "nrc": str(sec.nrc),
                    "profesor": sec.profesor,
                    "bloques": [{"dia": b.dia, "inicio": b.inicio, "fin": b.fin} for b in sec.bloques]
                })
            validas.append(horario_formateado)

    return {"total": len(validas), "combinaciones": validas}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)