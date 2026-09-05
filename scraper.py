import os
from dotenv import load_dotenv
import requests
import re
from typing import List, Dict, Any

# Carga las variables del archivo .env local si existe
load_dotenv()

# Lee desde variables de entorno (del sistema, de Render o del .env)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zmvecicbbxbpuhbnexiz.supabase.co/rest/v1")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

if not SUPABASE_ANON_KEY:
    print("[AVISO] SUPABASE_ANON_KEY no está configurada como variable de entorno.")
    
HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Origin": "https://zmvecicbbxbpuhbnexiz.supabase.co",
    "Referer": "https://zmvecicbbxbpuhbnexiz.supabase.co/"
}

DIAS_MAP = {
    "monday": "Lunes",
    "tuesday": "Martes",
    "wednesday": "Miércoles",
    "thursday": "Jueves",
    "friday": "Viernes",
    "saturday": "Sábado",
    "sunday": "Domingo"
}

def hora_a_decimal(hora_str: str) -> float:
    h, m = map(int, hora_str.split(":"))
    return round(h + (m / 60.0), 2)

def parsear_bloques_dia(dia_nombre: str, valor_campo: str) -> List[Dict[str, Any]]:
    if not valor_campo:
        return []
    bloques = []
    patron = r"(\d{2}:\d{2})_(\d{2}:\d{2})"
    coincidencias = re.findall(patron, valor_campo)
    for inicio_str, fin_str in coincidencias:
        bloques.append({
            "dia": dia_nombre,
            "inicio": hora_a_decimal(inicio_str),
            "fin": hora_a_decimal(fin_str)
        })
    return bloques

def obtener_materias_ucab(cedula: int, carrera_id: int = 2) -> List[Dict[str, Any]]:
    # 1. Proyecciones
    url_proy = f"{SUPABASE_URL}/rpc/er_get_student_projections"
    resp_proy = requests.post(url_proy, headers=HEADERS, json={"p_cedula": cedula}, timeout=10)
    if resp_proy.status_code != 200:
        raise ValueError(f"Error consultando cédula ({resp_proy.status_code}): {resp_proy.text}")

    materias_proyectadas = [s["id"] for s in resp_proy.json().get("subjects", [])]

    # 2. Electivas
    url_elec = f"{SUPABASE_URL}/materia_carrera?select=materia:materia_id(mat_cod)&carrera_id=eq.{carrera_id}&mat_sec_is_elective=eq.true"
    resp_elec = requests.get(url_elec, headers=HEADERS, timeout=10)
    materias_electivas = []
    if resp_elec.status_code == 200:
        materias_electivas = [item["materia"]["mat_cod"] for item in resp_elec.json() if item.get("materia")]

    todos_los_ids = list(dict.fromkeys(materias_proyectadas + materias_electivas))
    if not todos_los_ids:
        return []

    # 3. Horarios reales
    url_horarios = f"{SUPABASE_URL}/rpc/er_get_subject_schedules"
    resp_horarios = requests.post(url_horarios, headers=HEADERS, json={"p_mat_ids": todos_los_ids}, timeout=15)
    if resp_horarios.status_code != 200:
        raise ValueError(f"Error consultando horarios ({resp_horarios.status_code}): {resp_horarios.text}")

    oferta_cruda = resp_horarios.json()

    materias_dict: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for row in oferta_cruda:
        materia_nombre = row.get("subject_name", "").strip()
        sec_num = row.get("section", 1)
        modalidad = row.get("modality", "")
        profesor = row.get("professor") or "Por Asignar"
        sec_key = f"Sec {sec_num} ({modalidad})"
        crn = row.get("crn", 0)

        bloques = []
        for dia_en, dia_es in DIAS_MAP.items():
            valor_dia = row.get(dia_en)
            bloques.extend(parsear_bloques_dia(dia_es, valor_dia))

        if not bloques:
            continue

        if materia_nombre not in materias_dict:
            materias_dict[materia_nombre] = {}

        if sec_key not in materias_dict[materia_nombre]:
            materias_dict[materia_nombre][sec_key] = {
                "nombre": sec_key,
                "nrc": crn,
                "profesor": profesor,
                "bloques": []
            }

        materias_dict[materia_nombre][sec_key]["bloques"].extend(bloques)

    resultado = []
    for mat_nom, secciones in materias_dict.items():
        resultado.append({
            "nombre": mat_nom,
            "secciones": list(secciones.values())
        })

    return resultado