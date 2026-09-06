from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from itertools import product
from typing import Dict, List, Optional, Union, Any, Tuple
import re
from pydantic.v1 import Field
import scraper
import os
import unicodedata

def limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn').upper().strip()

def normalizar_nombre_materia(nombre: str) -> str:
    n = limpiar_texto(nombre)
    # Quitar paréntesis con práctica/lab/taller
    n = re.sub(r"\s*\(\s*(PRACTICA|LAB|LABORATORIO|TALLER|TEORIA)[^\)]*\)", "", n)
    # Quitar prefijos comunes
    n = re.sub(r"^(LABORATORIO DE|LAB\. DE|LAB DE|LAB|PRACTICA DE|PRAC\. DE|PRAC DE|PRACTICA|PRAC|TALLER DE|TALLER)\s+", "", n)
    # Quitar sufijos sueltos
    n = re.sub(r"\s*-\s*(PRACTICA|LAB|LABORATORIO)\s*$", "", n)
    return re.sub(r"\s+", " ", n).strip()

def son_mismo_profesor(p1_raw: str, p2_raw: str) -> bool:
    # Mantener una sola regla de comparación para evitar aceptar solo el apellido.
    return profesores_coinciden(p1_raw, p2_raw)

def extraer_apellidos_y_nombres(texto_prof: str) -> Tuple[set, set]:
    """
    Descompone el nombre del profesor en tokens de apellidos y nombres.
    Maneja formato 'APELLIDOS, NOMBRES' o 'NOMBRES APELLIDOS'.
    """
    limpio = limpiar_texto(texto_prof)
    if not limpio:
        return set(), set()
    
    if "," in limpio:
        partes = limpio.split(",", 1)
        apellidos = set(re.findall(r"\b[A-Z]{3,}\b", partes[0]))
        nombres = set(re.findall(r"\b[A-Z]{3,}\b", partes[1]))
    else:
        tokens = re.findall(r"\b[A-Z]{3,}\b", limpio)
        if len(tokens) >= 2:
            # En español usualmente el último token es el apellido
            apellidos = {tokens[-1]}
            nombres = set(tokens[:-1])
        elif tokens:
            apellidos = {tokens[0]}
            nombres = set()
        else:
            apellidos, nombres = set(), set()
            
    return apellidos, nombres

def profesores_coinciden(prof1: str, prof2: str) -> bool:
    """
    Determina con rigor si prof1 y prof2 son la misma persona.
    """
    p1 = limpiar_texto(prof1)
    p2 = limpiar_texto(prof2)

    indefinidos = ["POR ASIGNAR", "SIN PROFESOR", "SIN PROF", "N/A"]
    if not p1 or not p2:
        return True

    p1_invalido = any(ind in p1 for ind in indefinidos) or len(p1) < 3
    p2_invalido = any(ind in p2 for ind in indefinidos) or len(p2) < 3

    # Si alguno no tiene profesor asignado, no bloqueamos esa combinación
    if p1_invalido or p2_invalido:
        return True

    # Caso 1: Cadenas idénticas
    if p1 == p2:
        return True

    # Caso 2: Uno está contenido en el otro (ej: "PEREZ, CARLOS" in "PEREZ GARCIA, CARLOS")
    if p1 in p2 or p2 in p1:
        return True

    apellidos1, nombres1 = extraer_apellidos_y_nombres(p1)
    apellidos2, nombres2 = extraer_apellidos_y_nombres(p2)

    # Coincidencia de al menos un apellido principal
    apellidos_comunes = apellidos1.intersection(apellidos2)
    if not apellidos_comunes:
        return False

    # Si ambos tienen nombres identificables, verificar que no tengan nombres contradictorios
    if nombres1 and nombres2:
        nombres_comunes = nombres1.intersection(nombres2)
        # Si comparten apellido y al menos un nombre, o al menos no se contradicen
        return len(nombres_comunes) >= 1

    # Si comparten apellido significativo
    return len(apellidos_comunes) >= 1

def validar_mismo_profesor_teoria_practica(combo: List[tuple]) -> bool:
    materias_por_base: Dict[str, List[tuple]] = {}

    for item in combo:
        nombre_materia = item[0]
        seccion = item[1]
        base = normalizar_nombre_materia(nombre_materia)

        # Acceso seguro al profesor tanto si seccion es objeto como si fuera dict
        if hasattr(seccion, "profesor"):
            prof = seccion.profesor or ""
        elif isinstance(seccion, dict):
            prof = seccion.get("profesor", "")
        else:
            prof = ""

        if base not in materias_por_base:
            materias_por_base[base] = []
        materias_por_base[base].append((nombre_materia, prof))

    # Validamos cada materia base que tenga más de 1 componente (ej. Teoría + Práctica)
    for base, lista in materias_por_base.items():
        if len(lista) > 1:
            prof_base = lista[0][1]
            for _, prof_comparar in lista[1:]:
                if not profesores_coinciden(prof_base, prof_comparar):
                    return False
    return True

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

def hay_choque_entre_bloques(b1: dict, b2: dict) -> bool:
    """Verifica si dos bloques individuales chocan en día y rango de hora."""
    if b1.get("dia") != b2.get("dia"):
        return False
    # Choque de intervalos: max(inicio1, inicio2) < min(fin1, fin2)
    return max(b1["inicio"], b2["inicio"]) < min(b1["fin"], b2["fin"])

def hay_choque_entre_secciones(s1: dict, s2: dict) -> bool:
    """Verifica si alguna hora de la sección 1 choca con la sección 2."""
    for b1 in s1.get("bloques", []):
        for b2 in s2.get("bloques", []):
            if hay_choque_entre_bloques(b1, b2):
                return True
    return False

@app.post("/api/combinaciones")
async def calcular_combinaciones(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        print(f"Error al leer JSON: {e}")
        return {"total": 0, "combinaciones": []}

    if isinstance(body, dict):
        materias = body.get("materias", [])
        mismo_profesor = bool(body.get("mismo_profesor", False))
    elif isinstance(body, list):
        materias = body
        mismo_profesor = False
    else:
        materias = []
        mismo_profesor = False

    print(f"\n==========================================")
    print(f"PETICION RECIBIDA:")
    print(f"-> Materias ({len(materias)}): {[m.get('nombre') for m in materias]}")
    print(f"-> mismo_profesor activo: {mismo_profesor}")

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
                        bloques_procesados.append({
                            "dia": dia,
                            "inicio": inicio,
                            "fin": fin
                        })
                except (ValueError, TypeError):
                    continue

            # Solo agregar la sección si tiene al menos un bloque de horario válido
            if bloques_procesados:
                secciones_procesadas.append({
                    "materia": nombre_materia,
                    "seccion": str(sec.get("nombre", "Sin Sección")),
                    "nrc": str(sec.get("nrc", "N/A")),
                    "profesor": str(sec.get("profesor", "Por Asignar")),
                    "bloques": bloques_procesados
                })

        if secciones_procesadas:
            listas_opciones.append(secciones_procesadas)

    if not listas_opciones:
        print("-> Ninguna materia tiene secciones con horarios válidos.")
        return {"total": 0, "combinaciones": []}

    # Generamos todas las combinaciones posibles
    producto = product(*listas_opciones)
    validas = []

    for combo in producto:
        # combo es una tupla de diccionarios: (seccion_mat1, seccion_mat2, ...)
        
        # 1. Validar que no haya choques de horario entre las materias seleccionadas
        choca = False
        n = len(combo)
        for i in range(n):
            for j in range(i + 1, n):
                if hay_choque_entre_secciones(combo[i], combo[j]):
                    choca = True
                    break
            if choca:
                break

        if choca:
            continue

        # 2. Validar coincidencia de profesor si el filtro está activo
        if mismo_profesor:
            # Agrupar por nombre base de la materia
            grupos_por_base = {}
            for s in combo:
                base = normalizar_nombre_materia(s["materia"])
                if base not in grupos_por_base:
                    grupos_por_base[base] = []
                grupos_por_base[base].append(s)

            descartar = False
            for base, lista_sec in grupos_por_base.items():
                if len(lista_sec) > 1:
                    prof_referencia = lista_sec[0]["profesor"]
                    for sec_otra in lista_sec[1:]:
                        if not son_mismo_profesor(prof_referencia, sec_otra["profesor"]):
                            descartar = True
                            break
                if descartar:
                    break

            if descartar:
                continue

        # Formatear el horario resultante
        horario = []
        for s in combo:
            horario.append({
                "materia": s["materia"],
                "seccion": s["seccion"],
                "nrc": s["nrc"],
                "profesor": s["profesor"],
                "bloques": s["bloques"]
            })
        validas.append(horario)

    print(f"-> Total combinaciones válidas calculadas: {len(validas)}")
    print(f"==========================================\n")

    return {"total": len(validas), "combinaciones": validas}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)