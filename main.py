from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from itertools import product
from typing import List, Dict, Optional
import scraper

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

base_datos_materias: Dict[str, Materia] = {}

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

@app.get("/api/materias")
def obtener_materias():
    return list(base_datos_materias.values())

@app.post("/api/materias")
def agregar_materia(materia: Materia):
    nombre_normalizado = materia.nombre.strip()
    for nombre_existente in base_datos_materias.keys():
        if nombre_existente.lower() == nombre_normalizado.lower():
            raise HTTPException(status_code=400, detail=f"Ya existe una materia con el nombre '{nombre_normalizado}'")

    materia.nombre = nombre_normalizado
    base_datos_materias[nombre_normalizado] = materia
    return {"status": "ok", "materia": materia}

@app.delete("/api/materias/{nombre}")
def eliminar_materia(nombre: str):
    if nombre in base_datos_materias:
        del base_datos_materias[nombre]
        return {"status": "ok", "eliminado": nombre}
    raise HTTPException(status_code=404, detail="Materia no encontrada")

@app.post("/api/materias/importar-json")
def importar_json(materias: List[Materia]):
    nombres_vistos = set()
    nuevas = {}

    for m in materias:
        nombre = m.nombre.strip()
        if nombre.lower() in nombres_vistos:
            raise HTTPException(status_code=400, detail=f"El JSON contiene la materia repetida: '{nombre}'")
        nombres_vistos.add(nombre.lower())
        m.nombre = nombre
        nuevas[nombre] = m

    global base_datos_materias
    base_datos_materias = nuevas
    return {"status": "ok", "total_cargadas": len(base_datos_materias)}

@app.post("/api/estudiante/importar-cedula/{cedula}")
def importar_por_cedula(cedula: int):
    try:
        materias_extraidas = scraper.obtener_materias_ucab(cedula)
        if not materias_extraidas:
            raise HTTPException(status_code=404, detail="No se encontraron materias disponibles para esta cédula.")

        global base_datos_materias
        base_datos_materias = {
            m["nombre"]: Materia(**m) for m in materias_extraidas
        }

        return {
            "status": "ok",
            "total_cargadas": len(base_datos_materias),
            "materias": list(base_datos_materias.values())
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno durante la sincronización: {str(e)}")

# Recibe las materias que el alumno tiene marcadas con checkbox
@app.post("/api/combinaciones")
def calcular_combinaciones(materias_activas: Optional[List[str]] = None):
    if not base_datos_materias:
        return {"total": 0, "combinaciones": []}

    # Si se envían seleccionadas, usamos solo esas; si no, usamos todas
    materias_a_procesar = (
        [base_datos_materias[m] for m in materias_activas if m in base_datos_materias]
        if materias_activas is not None
        else list(base_datos_materias.values())
    )

    if not materias_a_procesar:
        return {"total": 0, "combinaciones": []}

    listas_opciones = []
    for mat in materias_a_procesar:
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
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)