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
   git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   cd TU_REPOSITORIO
   ```

2. **Crear y activar el entorno virtual:**
   
   En Windows (PowerShell / CMD):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
   
   En Linux o macOS:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   Crea un archivo `.env` en la raíz del proyecto basado en `.env.example`:
   ```env
   SUPABASE_URL=https://zmvecicbbxbpuhbnexiz.supabase.co/rest/v1
   SUPABASE_ANON_KEY=tu_clave_anonima_de_supabase_aqui
   ```

5. **Ejecutar la aplicación:**
   ```bash
   python main.py
   ```
   Abre tu navegador web e ingresa a [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

> ⚠️ **Aviso:** Proyecto de código abierto desarrollado con fines académicos y de optimización estudiantil. No almacena credenciales privadas ni modifica registros en los servidores de la universidad.
