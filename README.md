# 🎓 Planificador y Generador de Horarios Universitarios (UCAB)

Herramienta web diseñada para estudiantes universitarios que automatiza la búsqueda de combinaciones óptimas de horarios semestrales libres de choques.

## 🚀 Características

- **Sincronización directa por Cédula:** Consulta las asignaturas proyectadas y electivas disponibles mediante el consumo directo de endpoints REST/RPC.
- **Detección de Códigos NRC:** Muestra los códigos de inscripción (NRC/CRN), profesor asignado y horas exactas.
- **Resolución de Conflictos:** Algoritmo de producto cartesiano con validación de restricciones temporales para descartar solapamientos de clases.
- **Filtrado Dinámico:** Selector interactivo para calcular opciones únicamente con las materias que deseas inscribir.
- **Exportación:**
  - Descarga en **CSV** con la lista consolidada de materias, profesores y códigos NRC.
  - Generación de **PDF** en formato horizontal con la cuadrícula completa del horario.

## 🛠️ Stack Tecnológico

- **Backend:** Python 3, FastAPI, Pydantic, Requests, python-dotenv.
- **Frontend:** Vanilla JavaScript, HTML5, Tailwind CSS, html2canvas, jsPDF.

## ⚙️ Configuración e Instalación Local

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/TU_USUARIO/TU_REPOSITORIO.git](https://github.com/TU_USUARIO/TU_REPOSITORIO.git)
   cd TU_REPOSITORIO
