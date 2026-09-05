from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from itertools import product
from typing import List, Optional
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
    nombre: str
    nrc: Optional[int] = 0
    profesor: Optional[str] = "Por Asignar"
    bloques: List[Bloque]

    def choca_con(self, otra: 'Seccion') -> bool:
        return any(b1.choca_con(b2) for b1 in self.bloques for b2 in otra.bloques)

class Materia(BaseModel):
    nombre: str
    secciones: List[Seccion]

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

# Endpoint que solo consulta y devuelve los datos al usuario que lo pidió
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
        raise HTTPException(status_code=500, detail=f"Error interno durante la sincronización: {str(e)}")

# Endpoint para calcular combinaciones recibiendo directamente la lista del usuario actual
@app.post("/api/combinaciones")
def calcular_combinaciones(materias: List[Materia]):
    if not materias:
        return {"total": 0, "combinaciones": []}

    listas_opciones = []
    for mat in materias:
        if not mat.secciones:
            continue
        opciones_materia = [(mat.nombre, sec) for sec in mat.secciones]
        listas_opciones.append(opciones_materia)

    if not listas_opciones:
        return {"total": 0, "combinaciones": []}

    producto = product(*listas_opciones)
    validas = []

    for combo in producto:
        if horario_valido(list(combo)):
            horario_formateado = [
                {
                    "materia": item[0],
                    "seccion": item[1].nombre,
                    "nrc": item[1].nrc,
                    "profesor": item[1].profesor,
                    "bloques": [b.dict() for b in item[1].bloques]
                }
                for item in combo
            ]
            validas.append(horario_formateado)

    return {"total": len(validas), "combinaciones": validas}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)