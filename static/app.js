const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const HORA_INICIO = 7;
const HORA_FIN = 21;
const PX_POR_HORA = 60;

const COLORES = [
  "bg-blue-600 border-blue-700",
  "bg-emerald-600 border-emerald-700",
  "bg-purple-600 border-purple-700",
  "bg-amber-600 border-amber-700",
  "bg-rose-600 border-rose-700",
  "bg-cyan-600 border-cyan-700",
  "bg-indigo-600 border-indigo-700"
];

// Estado local exclusivo del navegador
let todasLasMaterias = [];
let materiasSeleccionadas = new Set();
let combinaciones = [];
let indiceActual = 0;
let mapaColoresMaterias = {};

function initRejilla() {
  const colHoras = document.getElementById("columna-horas");
  colHoras.innerHTML = "";
  for (let h = HORA_INICIO; h < HORA_FIN; h++) {
    const row = document.createElement("div");
    row.className = "border-b flex items-start justify-center pt-1 font-semibold text-xs text-slate-500";
    row.style.height = `${PX_POR_HORA}px`;
    row.textContent = `${h}:00`;
    colHoras.appendChild(row);
  }

  DIAS.forEach(dia => {
    const col = document.getElementById(`col-${dia}`);
    col.innerHTML = "";
    for (let h = HORA_INICIO; h < HORA_FIN; h++) {
      const linea = document.createElement("div");
      linea.className = "border-b border-slate-100 absolute w-full";
      linea.style.top = `${(h - HORA_INICIO) * PX_POR_HORA}px`;
      linea.style.height = `${PX_POR_HORA}px`;
      col.appendChild(linea);
    }
  });
}

function mostrarError(mensaje) {
  const box = document.getElementById("error-box");
  box.textContent = mensaje;
  box.classList.remove("hidden");
  setTimeout(() => box.classList.add("hidden"), 5000);
}

function mostrarInfo(mensaje) {
  const box = document.getElementById("info-box");
  box.textContent = mensaje;
  box.classList.remove("hidden");
  setTimeout(() => box.classList.add("hidden"), 4000);
}

function formatearHora(val) {
  const horas = Math.floor(val);
  const minutos = Math.round((val - horas) * 60);
  const hStr = String(horas).padStart(2, "0");
  const mStr = String(minutos).padStart(2, "0");
  return `${hStr}:${mStr}`;
}

async function cargarPorCedula() {
  const input = document.getElementById("cedula-input");
  const btn = document.getElementById("btn-cedula");
  const cedula = input.value.trim();

  if (!cedula) {
    mostrarError("Por favor ingresa un número de cédula.");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Cargando...";

  try {
    const res = await fetch(`/api/estudiante/importar-cedula/${cedula}`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      mostrarError(data.detail || "Error al consultar materias.");
      return;
    }

    // Guardar las materias que envió el backend
    todasLasMaterias = data.materias || [];
    materiasSeleccionadas.clear();

    // Asignar colores fijos por materia
    mapaColoresMaterias = {};
    todasLasMaterias.forEach((m, idx) => {
      mapaColoresMaterias[m.nombre] = COLORES[idx % COLORES.length];
    });

    // Renderizar la lista en el panel lateral y resetear vista
    renderizarListaMaterias();
    await recalcularCombinaciones();

    mostrarInfo(`Se cargaron ${data.total_cargadas} materias. Selecciona las que deseas cursar.`);
    input.value = "";
  } catch (err) {
    mostrarError("Error al conectar con el servidor.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Consultar";
  }
}

function renderizarListaMaterias() {
  document.getElementById("badge-total-materias").textContent = todasLasMaterias.length;
  const cont = document.getElementById("lista-materias");
  cont.innerHTML = "";

  todasLasMaterias.forEach(m => {
    const card = document.createElement("div");
    card.className = "border rounded p-2.5 bg-white text-xs shadow-xs space-y-1.5";

    const estaChecked = materiasSeleccionadas.has(m.nombre);

    let seccionesHTML = m.secciones.map(s => `
      <div class="text-slate-500 font-mono text-[11px] leading-tight mt-1">
        <span class="font-bold text-slate-800">NRC ${s.nrc || "N/A"}</span> • 
        <span class="font-semibold text-slate-700">${s.nombre}</span> 
        <span class="text-slate-400">(${s.profesor || "Sin prof."}):</span><br>
        ${s.bloques.map(b => `${b.dia} ${formatearHora(b.inicio)}-${formatearHora(b.fin)}`).join(", ")}
      </div>
    `).join("");

    card.innerHTML = `
      <div class="flex justify-between items-start">
        <label class="flex items-center gap-2 font-bold text-slate-800 cursor-pointer select-none">
          <input type="checkbox" ${estaChecked ? "checked" : ""} onchange="toggleMateria('${encodeURIComponent(m.nombre)}')" class="rounded text-blue-600 focus:ring-0">
          <span>${m.nombre}</span>
        </label>
        <button onclick="eliminarMateria('${encodeURIComponent(m.nombre)}')" class="text-rose-500 hover:text-rose-700 text-xs px-1 font-bold">✕</button>
      </div>
      <div class="pl-5 border-l-2 border-slate-100">${seccionesHTML}</div>
    `;
    cont.appendChild(card);
  });
}

function toggleMateria(nombreCodificado) {
  const nombre = decodeURIComponent(nombreCodificado);
  if (materiasSeleccionadas.has(nombre)) {
    materiasSeleccionadas.delete(nombre);
  } else {
    materiasSeleccionadas.add(nombre);
  }
  recalcularCombinaciones();
}

function seleccionarTodas(marcar) {
  if (marcar) {
    todasLasMaterias.forEach(m => materiasSeleccionadas.add(m.nombre));
  } else {
    materiasSeleccionadas.clear();
  }
  renderizarListaMaterias();
  recalcularCombinaciones();
}

async function recalcularCombinaciones() {
  // 1. Filtrar los objetos completos de las materias seleccionadas
  const materiasParaEnviar = todasLasMaterias.filter(m => materiasSeleccionadas.has(m.nombre));

  if (materiasParaEnviar.length === 0) {
    combinaciones = [];
    indiceActual = 0;
    actualizarVistaCombinacion();
    return;
  }

  // Sanitizar los datos para asegurar que los tipos sean exactamente los esperados por FastAPI
  const payloadLimpio = materiasParaEnviar.map(m => ({
    nombre: String(m.nombre),
    secciones: (m.secciones || []).map(s => ({
      nombre: String(s.nombre || "Sin Sección"),
      nrc: s.nrc !== undefined && s.nrc !== null ? String(s.nrc) : "N/A",
      profesor: String(s.profesor || "Por Asignar"),
      bloques: (s.bloques || []).map(b => ({
        dia: String(b.dia),
        inicio: parseFloat(b.inicio),
        fin: parseFloat(b.fin)
      }))
    }))
  }));

  try {
    const resCombos = await fetch("/api/combinaciones", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payloadLimpio)
    });

    if (!resCombos.ok) {
      const errData = await resCombos.json();
      console.error("Detalle del error 422:", errData);
      mostrarError("Error de validación al calcular combinaciones.");
      return;
    }

    const dataCombos = await resCombos.json();
    combinaciones = dataCombos.combinaciones || [];
    indiceActual = 0;

    actualizarVistaCombinacion();
  } catch (err) {
    console.error("Error de red:", err);
    mostrarError("Error al conectar con el servidor.");
  }
}

function agregarMateriaManual() {
  const nombre = document.getElementById("mat-nombre").value.trim();
  const secNombre = document.getElementById("sec-nombre").value.trim();
  const profesor = document.getElementById("sec-profesor").value.trim() || "Por Asignar";
  const dia = document.getElementById("sec-dia").value;
  const inicio = parseFloat(document.getElementById("sec-inicio").value);
  const fin = parseFloat(document.getElementById("sec-fin").value);

  if (!nombre || !secNombre) {
    mostrarError("Debes llenar el nombre de la materia y de la sección.");
    return;
  }
  if (inicio >= fin) {
    mostrarError("La hora de inicio debe ser menor que la hora de fin.");
    return;
  }

  const nuevaSeccion = {
    nombre: secNombre,
    nrc: 0,
    profesor: profesor,
    bloques: [{ dia: dia, inicio: inicio, fin: fin }]
  };

  const materiaExistente = todasLasMaterias.find(m => m.nombre.toLowerCase() === nombre.toLowerCase());
  if (materiaExistente) {
    materiaExistente.secciones.push(nuevaSeccion);
  } else {
    todasLasMaterias.push({
      nombre: nombre,
      secciones: [nuevaSeccion]
    });
    mapaColoresMaterias[nombre] = COLORES[todasLasMaterias.length % COLORES.length];
  }

  materiasSeleccionadas.add(nombre);

  document.getElementById("mat-nombre").value = "";
  document.getElementById("sec-nombre").value = "";
  document.getElementById("sec-profesor").value = "";

  renderizarListaMaterias();
  recalcularCombinaciones();
}

function eliminarMateria(nombreCodificado) {
  const nombre = decodeURIComponent(nombreCodificado);
  todasLasMaterias = todasLasMaterias.filter(m => m.nombre !== nombre);
  materiasSeleccionadas.delete(nombre);
  renderizarListaMaterias();
  recalcularCombinaciones();
}

function enviarJSON() {
  const raw = document.getElementById("json-input").value;
  try {
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) {
      mostrarError("El JSON debe ser una lista de materias.");
      return;
    }
    todasLasMaterias = data;
    materiasSeleccionadas.clear();

    mapaColoresMaterias = {};
    todasLasMaterias.forEach((m, idx) => {
      mapaColoresMaterias[m.nombre] = COLORES[idx % COLORES.length];
    });

    renderizarListaMaterias();
    recalcularCombinaciones();
    document.getElementById("json-input").value = "";
    mostrarInfo("Materias importadas exitosamente desde JSON.");
  } catch (e) {
    mostrarError("Formato JSON inválido.");
  }
}

function cambiarPagina(delta) {
  const nuevoIndice = indiceActual + delta;
  if (nuevoIndice >= 0 && nuevoIndice < combinaciones.length) {
    indiceActual = nuevoIndice;
    actualizarVistaCombinacion();
  }
}

function actualizarVistaCombinacion() {
  const total = combinaciones.length;
  const cantSeleccionadas = materiasSeleccionadas.size;

  if (cantSeleccionadas === 0) {
    document.getElementById("combos-titulo").textContent = "Sin materias seleccionadas";
    document.getElementById("combos-subtitulo").textContent = "Marca las casillas a la izquierda para armar tu horario.";
  } else {
    document.getElementById("combos-titulo").textContent = `Combinaciones encontradas: ${total}`;
    document.getElementById("combos-subtitulo").textContent = total > 0 
      ? `Mostrando combinación ${indiceActual + 1} de ${total} (para ${cantSeleccionadas} materias)`
      : `No hay combinaciones sin choque para las ${cantSeleccionadas} materias seleccionadas.`;
  }

  document.getElementById("page-indicator").textContent = `${total > 0 ? indiceActual + 1 : 0} / ${total}`;
  document.getElementById("btn-prev").disabled = indiceActual <= 0;
  document.getElementById("btn-next").disabled = indiceActual >= total - 1 || total === 0;

  DIAS.forEach(dia => {
    const col = document.getElementById(`col-${dia}`);
    col.querySelectorAll(".materia-card").forEach(el => el.remove());
  });

  if (total === 0) return;

  const horarioActual = combinaciones[indiceActual];

  horarioActual.forEach(item => {
    const color = mapaColoresMaterias[item.materia] || "bg-slate-700 border-slate-800";

    item.bloques.forEach(bloque => {
      const col = document.getElementById(`col-${bloque.dia}`);
      if (!col) return;

      const top = (bloque.inicio - HORA_INICIO) * PX_POR_HORA;
      const height = (bloque.fin - bloque.inicio) * PX_POR_HORA;

      const tarjeta = document.createElement("div");
      tarjeta.className = `materia-card absolute left-1 right-1 rounded border shadow-sm text-white z-10 ${color} p-1 overflow-hidden`;
      tarjeta.style.top = `${top + 1}px`;
      tarjeta.style.height = `${height - 2}px`;

      let profTexto = item.profesor || "Por Asignar";
      if (profTexto.includes(",")) {
        const partes = profTexto.split(",");
        const apellidos = partes[0].trim().split(" ")[0];
        const nombres = partes[1].trim().split(" ")[0];
        profTexto = `${nombres} ${apellidos}`;
      }

      tarjeta.innerHTML = `
        <div class="font-bold text-[13px] leading-tight text-white tracking-tight mb-0.5 truncate" title="${item.materia}">
          ${item.materia}
        </div>
        <div class="text-[11px] font-bold text-emerald-100 font-mono leading-tight">
          NRC: ${item.nrc || "N/A"}
        </div>
        <div class="text-[11px] text-amber-300 font-semibold leading-tight truncate">
          ${profTexto}
        </div>
        <div class="text-[10.5px] text-white/95 font-mono font-semibold leading-tight mt-auto pt-0.5">
          ${formatearHora(bloque.inicio)} - ${formatearHora(bloque.fin)}
        </div>
      `;

      col.appendChild(tarjeta);
    });
  });
}

function exportarCSVActual() {
  if (combinaciones.length === 0) {
    mostrarError("No hay combinación de horario activa para exportar.");
    return;
  }

  const horarioActual = combinaciones[indiceActual];
  const filas = [["Materia", "NRC", "Profesor", "Dia", "Hora Inicio", "Hora Fin"]];

  horarioActual.forEach(item => {
    item.bloques.forEach(b => {
      filas.push([
        `"${item.materia.replace(/"/g, '""')}"`,
        item.nrc || "N/A",
        `"${(item.profesor || 'Por Asignar').replace(/"/g, '""')}"`,
        b.dia,
        formatearHora(b.inicio),
        formatearHora(b.fin)
      ]);
    });
  });

  const contenidoCSV = "\uFEFF" + filas.map(f => f.join(",")).join("\n");
  const blob = new Blob([contenidoCSV], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const enlace = document.createElement("a");
  enlace.setAttribute("href", url);
  enlace.setAttribute("download", `horario_opcion_${indiceActual + 1}.csv`);
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
}

async function exportarPDFFull() {
  if (combinaciones.length === 0) {
    mostrarError("No hay un horario generado para exportar.");
    return;
  }

  const btnPdf = document.getElementById("btn-pdf");
  const textoOriginal = btnPdf.innerHTML;
  btnPdf.disabled = true;
  btnPdf.innerHTML = "<span>⏳</span> Generando PDF...";

  const calendarioEl = document.getElementById("contenedor-calendario");
  calendarioEl.scrollTop = 0;

  try {
    const canvas = await html2canvas(calendarioEl, {
      scale: 2.5,
      useCORS: true,
      backgroundColor: "#ffffff",
      scrollY: 0,
      scrollX: 0,
      onclone: (clonedDoc) => {
        const clonedCalendar = clonedDoc.getElementById("contenedor-calendario");
        if (clonedCalendar) {
          clonedCalendar.style.overflow = "visible";
          clonedCalendar.style.height = "auto";
          clonedCalendar.style.maxHeight = "none";
        }
        clonedDoc.querySelectorAll(".materia-card").forEach(el => {
          el.style.overflow = "visible";
        });
      }
    });

    const imgData = canvas.toDataURL("image/png");
    const { jsPDF } = window.jspdf;

    const pdf = new jsPDF("l", "mm", "a4");
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();

    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(13);
    pdf.setTextColor(15, 23, 42);
    pdf.text(`Horario Propuesto - Opción #${indiceActual + 1}`, 12, 11);

    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(8.5);
    pdf.setTextColor(100, 116, 139);
    pdf.text(`Total asignaturas: ${materiasSeleccionadas.size} | Horario universitario`, 12, 16);

    const marginX = 8;
    const startY = 19;
    const usableWidth = pageWidth - (marginX * 2);
    const usableHeight = pageHeight - startY - 6;

    const canvasAspectRatio = canvas.width / canvas.height;
    let renderWidth = usableWidth;
    let renderHeight = usableWidth / canvasAspectRatio;

    if (renderHeight > usableHeight) {
      renderHeight = usableHeight;
      renderWidth = usableHeight * canvasAspectRatio;
    }

    const renderX = marginX + (usableWidth - renderWidth) / 2;

    pdf.addImage(imgData, "PNG", renderX, startY, renderWidth, renderHeight, undefined, "FAST");
    pdf.save(`horario_opcion_${indiceActual + 1}.pdf`);
    
    mostrarInfo("PDF descargado correctamente.");
  } catch (err) {
    console.error(err);
    mostrarError("Error al generar el PDF.");
  } finally {
    btnPdf.disabled = false;
    btnPdf.innerHTML = textoOriginal;
  }
}

// Inicializa la cuadrícula limpia al cargar la página
initRejilla();