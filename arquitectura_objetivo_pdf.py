#!/usr/bin/env python3
"""
arquitectura_objetivo_pdf.py — Documento de arquitectura objetivo y plan de fases
para llevar la plataforma Auditor BPG de prueba de concepto a operación nacional.

Uso: arquitectura_objetivo_pdf.py [--salida ruta.pdf]
"""
import argparse, datetime, json, os, sqlite3, sys

BASE = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(BASE, "auditorias_bpg.db")

CSS = """<style>
@page{size:A4 portrait;margin:15mm 13mm 16mm 13mm;
  @bottom-left{content:"Arquitectura objetivo · Auditor BPG ICA 067449";font-size:7.5pt;color:#7a8a84}
  @bottom-right{content:"Página " counter(page) " de " counter(pages);font-size:7.5pt;color:#7a8a84}}
*{box-sizing:border-box}
body{font-family:'DejaVu Sans',Arial,sans-serif;color:#1b2b26;margin:0;font-size:9.6pt;line-height:1.45}
.portada{background:#0B3D2E;color:#fff;padding:22px 24px;border-radius:5px;margin-bottom:14px}
.portada .b{font-size:10.5pt;opacity:.95}
.portada h1{margin:4px 0 6px;font-size:20pt}
.portada .s{font-size:11pt;opacity:.92}
.portada .m{font-size:8.6pt;opacity:.85;margin-top:10px;border-top:1px solid rgba(255,255,255,.35);padding-top:7px}
h2{font-size:12.5pt;color:#0B3D2E;margin:16px 0 6px;border-bottom:1.5px solid #0B3D2E;padding-bottom:3px;page-break-after:avoid}
h3{font-size:10.2pt;color:#155443;margin:11px 0 4px;page-break-after:avoid}
p{margin:4px 0 6px;text-align:justify}
table{width:100%;border-collapse:collapse;margin:5px 0 8px}
thead{display:table-header-group}
tr{page-break-inside:avoid}
th,td{border:1px solid #c3cfc9;padding:3.5px 5px;font-size:8.6pt;vertical-align:top}
th{background:#eef3f0;text-align:left;font-size:7.9pt;text-transform:uppercase;letter-spacing:.3px}
td.k{width:30%;background:#f8faf9;font-weight:600}
td.c{text-align:center;white-space:nowrap}
ul,ol{margin:4px 0 7px 16px;padding:0}li{margin-bottom:2.5px}
code{font-family:'DejaVu Sans Mono',monospace;font-size:8.3pt;background:#eef2f0;padding:0 2px;border-radius:2px}
/* diagrama de capas */
.capa{width:100%;border-collapse:separate;border-spacing:5px 3px;margin:3px 0}
.capa td.tit{width:19%;background:#0B3D2E;color:#fff;font-weight:700;font-size:8.2pt;padding:7px 6px;border-radius:3px;vertical-align:middle;text-align:center;border:0}
.capa td.bx{background:#f4f8f6;border:1px solid #9fb8ae;border-radius:3px;font-size:8pt;padding:6px;vertical-align:top}
.capa td.bx b{display:block;font-size:8.3pt;color:#0B3D2E;margin-bottom:1px}
.capa td.bx span{color:#4d625b;font-size:7.6pt;line-height:1.3;display:block}
.flecha{text-align:center;color:#0B3D2E;font-size:11pt;line-height:1;margin:1px 0}
.aviso{border-left:4px solid #C62828;background:#fdf3f2;padding:7px 10px;margin:7px 0;font-size:8.8pt}
.ok{border-left:4px solid #2E7D32;background:#f2f8f3;padding:7px 10px;margin:7px 0;font-size:8.8pt}
.info{border-left:4px solid #1565C0;background:#f2f6fc;padding:7px 10px;margin:7px 0;font-size:8.8pt}
.nota{font-size:8.2pt;color:#546e64;margin-top:3px}
.fase{background:#0B3D2E;color:#fff;font-size:9pt;font-weight:700;padding:4px 8px;border-radius:3px;display:block;margin:8px 0 3px;page-break-after:avoid}
</style>"""


def datos():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = lambda s: con.execute(s).fetchone()[0]
    d = {
        "predios": q("SELECT COUNT(*) FROM predios"),
        "auditorias": q("SELECT COUNT(*) FROM auditorias"),
        "respuestas": q("SELECT COUNT(*) FROM respuestas"),
        "criterios": q("SELECT COUNT(*) FROM criterios"),
        "municipios": q("SELECT COUNT(DISTINCT municipio) FROM predios"),
        "veredas": q("SELECT COUNT(DISTINCT vereda) FROM predios"),
        "seguimiento": q("SELECT COUNT(*) FROM seguimiento"),
        "gps": q("SELECT COUNT(*) FROM predios WHERE latitud IS NOT NULL"),
        "tam_kb": round(os.path.getsize(DB) / 1024),
    }
    _ah = datetime.datetime.now()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    d["fecha"] = f"{_ah.day} de {meses[_ah.month - 1]} de {_ah.year}"
    return d


def capa(titulo, cajas):
    """cajas: lista de (titulo, detalle). Devuelve el HTML de una fila del diagrama."""
    tds = "".join("<td class='bx'><b>" + t + "</b><span>" + det + "</span></td>" for t, det in cajas)
    return ("<table class='capa'><tr><td class='tit'>" + titulo + "</td>" + tds + "</tr></table>")


def construir(d):
    H = []
    A = H.append

    A("<div class='portada'><div class='b'>DOCUMENTO DE ARQUITECTURA OBJETIVO</div>"
      "<h1>Auditor BPG en operación nacional</h1>"
      "<div class='s'>De prueba de concepto validada a plataforma institucional</div>"
      "<div class='m'>Buenas Prácticas Ganaderas · Resolución ICA 067449 · Forma 3-852 V6<br>"
      + d["fecha"] + " · Documento técnico para revisión de los líderes del proceso</div></div>")

    # 1
    A("<h2>1. Propósito y alcance</h2>")
    A("<p>Este documento define la arquitectura objetivo y la ruta de implementación para llevar el "
      "<b>Auditor BPG</b> de su estado actual —prueba de concepto funcional en campo— a una plataforma "
      "capaz de operar a nivel nacional, y establece las brechas técnicas e institucionales que deben "
      "cerrarse en cada fase.</p>")
    A("<p>Se entiende por <b>operación nacional</b> la capacidad de atender simultáneamente a productores y "
      "auditores en cualquier departamento, con disponibilidad sostenida, trazabilidad probatoria de cada "
      "evaluación, cumplimiento de la normativa colombiana de protección de datos y seguridad digital, e "
      "interoperabilidad con los sistemas de información del Instituto.</p>")
    A("<div class='info'><b>Alcance.</b> El documento cubre arquitectura de aplicación, datos, seguridad, "
      "interoperabilidad, operación en campo, observabilidad y plan de fases. No define el modelo de "
      "contratación ni el presupuesto: esos elementos se derivan de este documento con el área "
      "administrativa.</div>")

    # 2
    A("<h2>2. Punto de partida: lo que ya está demostrado</h2>")
    A("<p>La prueba de concepto no es un prototipo de laboratorio: ha sido usada en fincas reales, sin "
      "conectividad, y sus resultados son verificables. Las siguientes cifras corresponden al estado del "
      "sistema a la fecha de emisión y se obtienen de la propia base de datos.</p>")
    A("<table><tr><td class='k'>Cobertura actual</td><td>" + str(d["predios"]) + " predios · " +
      str(d["municipios"]) + " municipios · " + str(d["veredas"]) + " veredas · " +
      str(d["gps"]) + "/" + str(d["predios"]) + " con georreferenciación</td></tr>"
      "<tr><td class='k'>Volumen de datos</td><td>" + str(d["auditorias"]) + " auditorías · " +
      f"{d['respuestas']:,}".replace(",", ".") + " respuestas a criterios · " + str(d["criterios"]) +
      " criterios evaluados</td></tr>"
      "<tr><td class='k'>Seguimiento</td><td>" + str(d["seguimiento"]) +
      " hallazgos con responsable, plazo y evidencia</td></tr>"
      "<tr><td class='k'>Base de datos</td><td>SQLite, " + str(d["tam_kb"]) +
      " KB, respaldo diario automático</td></tr></table>")
    A("<h3>2.1 Capacidades ya resueltas</h3>")
    A("<ul>"
      "<li><b>Captura sin conectividad</b> en finca, con consolidación posterior automática.</li>"
      "<li><b>Cálculo único y auditable:</b> el concepto y los porcentajes se derivan siempre de las respuestas "
      "SI/NO/NA; nunca de valores declarados. Umbrales de la norma aplicados de forma uniforme.</li>"
      "<li><b>Trazabilidad por criterio y por fuente</b>, con conservación de visitas históricas en archivo aparte.</li>"
      "<li><b>Plan de acción</b> derivado de cada hallazgo, priorizado por obligatoriedad, con documento imprimible.</li>"
      "<li><b>Publicación de consulta</b> con indicadores, mapa y ficha por predio, sin datos personales expuestos.</li>"
      "<li><b>Reportería reproducible</b> en PDF generada desde el estado real del sistema.</li>"
      "<li><b>Operación desatendida</b> con sincronización programada y avisos únicamente ante novedades o errores.</li>"
      "</ul>")
    A("<h3>2.2 Brechas frente a una operación nacional</h3>")
    A("<table><thead><tr><th>Dimensión</th><th>Estado actual (piloto)</th><th>Requerido (nacional)</th><th>Prioridad</th></tr></thead><tbody>"
      "<tr><td>Seguridad de acceso</td><td>API local sin autenticación; CORS abierto</td>"
      "<td>Autenticación por roles, tokens de corta vida, TLS obligatorio, WAF</td><td class='c'>Crítica</td></tr>"
      "<tr><td>Base de datos</td><td>SQLite en un solo equipo</td>"
      "<td>PostgreSQL gestionado con réplica y recuperación a un punto en el tiempo</td><td class='c'>Crítica</td></tr>"
      "<tr><td>Valor probatorio</td><td>Sin firma ni bitácora inmutable</td>"
      "<td>Folio, sello de tiempo y registro inmutable de accesos y cambios</td><td class='c'>Alta</td></tr>"
      "<tr><td>Identidad</td><td>Sin usuarios ni roles</td>"
      "<td>SSO institucional para funcionarios y autenticación ciudadana para productores</td><td class='c'>Alta</td></tr>"
      "<tr><td>Calidad del dato</td><td>Municipio y vereda como texto libre, normalizados en servidor</td>"
      "<td>Catálogos cerrados y oficiales (DANE, RSPP)</td><td class='c'>Alta</td></tr>"
      "<tr><td>Continuidad</td><td>Respaldo diario sin prueba de restauración</td>"
      "<td>RTO/RPO definidos, restauración probada, plan de continuidad</td><td class='c'>Alta</td></tr>"
      "<tr><td>Interoperabilidad</td><td>API interna sin versionado</td>"
      "<td>API versionada y documentada; integración con RSPP y sistemas del Instituto</td><td class='c'>Media</td></tr>"
      "<tr><td>Observabilidad</td><td>Consultas manuales de estado</td>"
      "<td>Monitoreo, alertas, logs centralizados y tablero de operación</td><td class='c'>Media</td></tr>"
      "<tr><td>Adopción formal</td><td>Herramienta de trabajo del asesor</td>"
      "<td>Procedimiento adoptado por acto administrativo</td><td class='c'>Crítica</td></tr>"
      "</tbody></table>")

    # 3
    A("<h2>3. Principios de diseño</h2>")
    A("<ol>"
      "<li><b>El dato oficial se calcula, no se declara.</b> Un solo punto de cálculo para toda la organización; "
      "ninguna interfaz puede escribir porcentajes ni conceptos.</li>"
      "<li><b>El campo manda.</b> La arquitectura se diseña para la finca sin señal, no para la oficina con fibra.</li>"
      "<li><b>La norma se parametriza.</b> Criterios, umbrales y versiones del formulario son configuración versionada, "
      "no código: si cambia la resolución, las auditorías anteriores conservan su interpretación.</li>"
      "<li><b>Trazabilidad por defecto.</b> Todo cambio de estado deja rastro de quién, cuándo y con qué evidencia.</li>"
      "<li><b>Privacidad en el diseño.</b> El canal público expone solo lo agregado; los datos personales se reducen, "
      "se separan y se protegen desde el origen.</li>"
      "<li><b>Un núcleo, dos servicios.</b> La certificación oficial y el servicio al productor comparten el mismo "
      "núcleo de criterios y datos, pero se despliegan y escalan por separado.</li>"
      "<li><b>Interoperar antes que reemplazar.</b> La plataforma se integra con los registros existentes del Instituto "
      "en lugar de crear maestros paralelos.</li>"
      "<li><b>Operación observable.</b> Si no se puede medir disponibilidad, latencia y calidad del dato, no se puede "
      "sostener un servicio nacional.</li>"
      "</ol>")

    # 4 arquitectura
    A("<h2>4. Arquitectura objetivo</h2>")
    A("<h3>4.1 Vista de capas</h3>")
    A("<p>El sistema se organiza en cuatro capas funcionales y un conjunto de servicios transversales. El sentido "
      "de dependencia es siempre descendente: la captura no conoce la base de datos, y el núcleo no conoce las "
      "interfaces.</p>")
    A(capa("CAPTURA", [
        ("App móvil offline", "Formulario versionado, firma del productor, fotos georreferenciadas, cola local"),
        ("Portal del productor", "Autoauditoría guiada, consulta de su plan de acción"),
        ("Carga asistida", "Oficinas y técnicos: XLSX/CSV para jornadas masivas")]))
    A("<div class='flecha'>▼</div>")
    A(capa("SERVICIOS", [
        ("API de negocio", "REST versionada, autenticada, con límites de tasa y paginación"),
        ("Identidad y roles", "SSO institucional · autenticación ciudadana para productores"),
        ("Motor normativo", "Catálogo de criterios y umbrales versionado por acto administrativo"),
        ("Auditorías y evidencias", "Validación, cálculo único, folio, sello de tiempo"),
        ("Sincronización", "Lotes idempotentes y resolución de conflictos")]))
    A("<div class='flecha'>▼</div>")
    A(capa("DATOS", [
        ("PostgreSQL", "Réplica de lectura, recuperación a un punto en el tiempo, respaldos cifrados"),
        ("Objetos (evidencias)", "Fotos y firmas con ciclo de vida y control de acceso"),
        ("Catálogos maestros", "Municipios DANE, veredas, especies, predios del RSPP"),
        ("Réplica analítica", "Indicadores sin cargar la base transaccional")]))
    A("<div class='flecha'>▼</div>")
    A(capa("CONSUMO", [
        ("Dashboard público", "Indicadores agregados y consulta por predio, sin datos personales"),
        ("Geoservicio", "Capa de predios para mapas institucionales"),
        ("Documentos", "Planes de acción, actas y listados en PDF con folio"),
        ("API para el Instituto", "Consulta de resultados por parte de otros sistemas")]))
    A("<h3>4.2 Servicios transversales</h3>")
    A("<table><thead><tr><th>Servicio</th><th>Función</th><th>Requisito mínimo</th></tr></thead><tbody>"
      "<tr><td>Observabilidad</td><td>Disponibilidad, latencia, errores y métricas de negocio</td>"
      "<td>Alertas a operación; retención de logs según política</td></tr>"
      "<tr><td>Seguridad perimetral</td><td>WAF, TLS, filtrado de origen, límites de tasa</td>"
      "<td>Endurecimiento revisado antes de exponer el servicio</td></tr>"
      "<tr><td>Gestión de secretos</td><td>Custodia de credenciales y rotación</td>"
      "<td>Bóveda; ningún secreto en código ni en archivos del servidor</td></tr>"
      "<tr><td>Bitácora inmutable</td><td>Registro append-only de accesos y cambios de estado</td>"
      "<td>Sellado periódico y verificación de integridad</td></tr>"
      "<tr><td>Respaldo y continuidad</td><td>Copias cifradas y restauración probada</td>"
      "<td>Prueba documentada con periodicidad definida</td></tr>"
      "</tbody></table>")
    A("<h3>4.3 Un núcleo de datos, dos servicios</h3>")
    A("<p>La misma base de criterios y el mismo motor de cálculo sostienen dos operaciones con volúmenes y "
      "exigencias distintas. Separarlas evita sobredimensionar la certificación oficial y, a la vez, evita que "
      "el volumen del servicio al productor degrade la operación institucional.</p>")
    A("<table><thead><tr><th>Servicio</th><th>Usuarios</th><th>Volumen esperado</th><th>Exigencia dominante</th></tr></thead><tbody>"
      "<tr><td><b>Certificación oficial</b></td><td>Auditores y supervisores del Instituto</td>"
      "<td>Cientos de predios al año</td><td>Trazabilidad probatoria y valor legal del registro</td></tr>"
      "<tr><td><b>Servicio al productor</b></td><td>Productores, gremios, asistentes técnicos</td>"
      "<td>Miles de evaluaciones al año</td><td>Disponibilidad, facilidad de uso y bajo costo por usuario</td></tr>"
      "</tbody></table>")
    A("<div class='ok'><b>Ventaja de esta separación.</b> El productor puede autoevaluarse sin tocar el expediente "
      "oficial; cuando la visita oficial ocurre, el auditor parte de información ya capturada y verificada. El "
      "esfuerzo de campo se reduce sin perder control institucional.</div>")

    # 5 seguridad
    A("<h2>5. Seguridad y cumplimiento normativo</h2>")
    A("<table><thead><tr><th>Requisito</th><th>Implementación esperada</th></tr></thead><tbody>"
      "<tr><td>Modelo de Seguridad y Privacidad de la Información (MinTIC, Resolución 02277 de 2025)</td>"
      "<td>Análisis de riesgos, políticas documentadas, plan de seguridad y privacidad vigente</td></tr>"
      "<tr><td>Protección de datos personales (Ley 1581 de 2012 y Decreto 1377 de 2013)</td>"
      "<td>Autorización del titular, aviso de privacidad, finalidad, retención y atención de derechos; "
      "cédula y geolocalización tratadas como dato personal</td></tr>"
      "<tr><td>Registro Nacional de Bases de Datos (SIC)</td>"
      "<td>Inscripción de las bases y actualización ante cambios</td></tr>"
      "<tr><td>Reporte de incidentes de seguridad</td><td>Procedimiento con reporte a la SIC dentro del término legal</td></tr>"
      "<tr><td>Control de acceso</td><td>Roles: productor, auditor, supervisor, administrador; segundo factor para funcionarios; "
      "principio de mínimo privilegio y revisión periódica</td></tr>"
      "<tr><td>Aseguramiento técnico</td><td>Pruebas de penetración y análisis de vulnerabilidades periódicos; gestión de parches con plazo</td></tr>"
      "<tr><td>Integridad probatoria</td><td>Folio por auditoría, sello de tiempo y bitácora inmutable con verificación de integridad</td></tr>"
      "<tr><td>Ambientes</td><td>Desarrollo, pruebas y producción separados; datos anonimizados en pruebas</td></tr>"
      "</tbody></table>")
    A("<div class='aviso'><b>Condición de entrada.</b> Ninguna exposición fuera de la red interna debe hacerse antes de "
      "cerrar autenticación, TLS y control de origen. Hoy la API del piloto es abierta: es aceptable mientras permanezca "
      "en una red controlada, y es inaceptable en cualquier escenario nacional.</div>")

    # 6 interoperabilidad
    A("<h2>6. Interoperabilidad</h2>")
    A("<ul>"
      "<li><b>API versionada y documentada</b> (especificación OpenAPI), con autenticación, límites de tasa y paginación.</li>"
      "<li><b>Integración con el Registro Sanitario de Predios Pecuarios (RSPP)</b> para tomar el maestro de predios y "
      "productores en lugar de replicarlo; la identidad del predio debe ser la oficial.</li>"
      "<li><b>Catálogos cerrados</b>: municipios y veredas según codificación DANE, especies y tipos de explotación "
      "según catálogo del Instituto. Esto elimina de raíz los errores de grafía que hoy se corrigen en el servidor.</li>"
      "<li><b>Formatos de salida</b> que la entidad ya utiliza (Excel, PDF, CSV) para no imponer herramientas nuevas.</li>"
      "<li><b>Eventos</b> de alta, actualización y cierre de auditoría para que otros sistemas reaccionen sin consultar "
      "manualmente.</li>"
      "</ul>")

    # 7 operación en campo
    A("<h2>7. Operación en campo</h2>")
    A("<table><thead><tr><th>Requisito</th><th>Criterio de aceptación</th></tr></thead><tbody>"
      "<tr><td>Funcionamiento sin conectividad</td><td>Jornada completa de visitas sin señal, con consolidación posterior verificada</td></tr>"
      "<tr><td>Sincronización idempotente</td><td>Reintentos y envíos duplicados no generan registros repetidos</td></tr>"
      "<tr><td>Dispositivos</td><td>Compatibilidad con Android 8 o superior de gama media y baja; aplicación ligera</td></tr>"
      "<tr><td>Distribución y actualización</td><td>Paquete firmado; actualización controlada y versionada</td></tr>"
      "<tr><td>Versionado del formulario</td><td>Cada auditoría registra la versión con la que fue diligenciada</td></tr>"
      "<tr><td>Evidencia</td><td>Foto georreferenciada y firma del productor cuando el procedimiento lo exija</td></tr>"
      "<tr><td>Seguridad del dispositivo</td><td>Cifrado local y borrado remoto ante pérdida</td></tr>"
      "</tbody></table>")

    # 8 observabilidad
    A("<h2>8. Observabilidad y soporte</h2>")
    A("<ul>"
      "<li>Tablero de operación con disponibilidad, latencia, errores y volumen por regional.</li>"
      "<li>Alertas automáticas ante caída del servicio, respaldo fallido o acumulación de sincronizaciones pendientes.</li>"
      "<li>Logs centralizados con retención definida y acceso restringido.</li>"
      "<li>Mesa de ayuda con niveles, tiempos de respuesta comprometidos y base de conocimiento.</li>"
      "<li>Ambiente de capacitación con datos ficticios para formación de auditores por regional.</li>"
      "</ul>")

    # 9 plan de fases
    A("<h2>9. Plan de implementación por fases</h2>")
    A("<p>Cada fase tiene un criterio de salida verificable: no se avanza por calendario, sino por cumplimiento. "
      "Las duraciones son estimaciones preliminares sujetas a revisión con el área de tecnología y la oficina de "
      "proyectos del Instituto.</p>")

    fases = [
        ("FASE 0 · Preparación y aseguramiento", "2 a 3 meses",
         ["Concepto jurídico y de tecnología sobre el registro digital",
          "Análisis de impacto en privacidad y política de tratamiento de datos",
          "Comité técnico que valide la interpretación de los criterios",
          "Cierre de brechas del piloto: autenticación, TLS, control de origen",
          "Arquitectura detallada aprobada y plan de capacidad"],
         "Procedimiento y criterios validados por escrito; brechas críticas cerradas"),
        ("FASE 1 · Piloto regional controlado", "4 a 6 meses",
         ["Migración a PostgreSQL con réplica y respaldos gestionados",
          "Identidad y roles; SSO para funcionarios",
          "App firmada y distribuida por canal controlado",
          "Catálogos cerrados en el formulario",
          "Piloto en uno o dos departamentos con meta definida de predios",
          "Bitácora inmutable y folio por auditoría"],
         "Meta de predios cumplida con trazabilidad completa; cero incidentes de seguridad graves; "
         "disponibilidad medida y sostenida"),
        ("FASE 2 · Expansión multi-regional", "6 a 9 meses",
         ["Integración con RSPP y catálogos oficiales",
          "Prueba de carga con la concurrencia esperada por jornada",
          "Mesa de ayuda y formación regional",
          "Monitoreo, alertas y tablero de operación",
          "Adopción del procedimiento por acto administrativo",
          "Documentación técnica y manuales de usuario"],
         "Cinco a ocho departamentos operando; indicadores de calidad del dato dentro de meta; "
         "soporte con tiempos de respuesta cumplidos"),
        ("FASE 3 · Operación nacional", "6 a 12 meses",
         ["Alta disponibilidad en más de una zona",
          "API pública documentada para integración institucional",
          "Reportería oficial y salidas hacia otros sistemas",
          "Auditoría externa de seguridad",
          "Modelo de sostenibilidad y gobierno del dato",
          "Evaluación de certificación del sistema de gestión de seguridad"],
         "Cobertura nacional con acuerdos de nivel de servicio cumplidos y auditoría externa sin hallazgos críticos"),
    ]
    for titulo, dur, act, salida in fases:
        A("<div class='fase'>" + titulo + " · " + dur + "</div>")
        A("<table><tr><td class='k'>Actividades</td><td><ul style='margin:0 0 0 14px'>"
          + "".join("<li>" + a + "</li>" for a in act) + "</ul></td></tr>"
          "<tr><td class='k'>Criterio de salida</td><td>" + salida + "</td></tr></table>")

    # 10 indicadores
    A("<h2>10. Indicadores de éxito</h2>")
    A("<table><thead><tr><th>Indicador</th><th>Qué mide</th><th>Meta sugerida</th></tr></thead><tbody>"
      "<tr><td>Disponibilidad del servicio</td><td>Operación continua</td><td>≥ 99,5 % mensual</td></tr>"
      "<tr><td>Consolidación de una evaluación</td><td>Del envío en campo al dato disponible</td><td>≤ 15 minutos</td></tr>"
      "<tr><td>Auditorías con evidencia completa</td><td>Calidad del registro</td><td>≥ 95 %</td></tr>"
      "<tr><td>Duplicados detectados</td><td>Integridad del maestro de predios</td><td>&lt; 1 %</td></tr>"
      "<tr><td>Predios con catálogo cerrado</td><td>Calidad de la captura</td><td>100 %</td></tr>"
      "<tr><td>Emisión del plan de acción</td><td>Oportunidad para el productor</td><td>≤ 24 horas tras la visita</td></tr>"
      "<tr><td>Restauración verificada</td><td>Capacidad real de recuperación</td><td>Prueba exitosa por trimestre</td></tr>"
      "<tr><td>Incidentes de seguridad con datos personales</td><td>Riesgo materializado</td><td>0</td></tr>"
      "<tr><td>Satisfacción de auditores y productores</td><td>Adopción real</td><td>≥ 80 % favorable</td></tr>"
      "</tbody></table>")

    # 11 riesgos
    A("<h2>11. Riesgos principales y mitigación</h2>")
    A("<table><thead><tr><th>Riesgo</th><th>Impacto</th><th>Mitigación</th></tr></thead><tbody>"
      "<tr><td>El procedimiento no se adopta formalmente</td><td>El registro digital no tiene valor institucional</td>"
      "<td>Acto administrativo en la Fase 0, antes de invertir en infraestructura</td></tr>"
      "<tr><td>Maestro de predios desactualizado o inconsistente</td><td>Duplicados y trazabilidad débil</td>"
      "<td>Integración con RSPP y regla única de identidad del predio</td></tr>"
      "<tr><td>Conectividad rural insuficiente</td><td>Pérdida de información en campo</td>"
      "<td>Diseño offline probado, sincronización idempotente y validación en el dispositivo</td></tr>"
      "<tr><td>Exposición de datos personales</td><td>Sanctón y pérdida de confianza</td>"
      "<td>Minimización, cifrado, roles, bitácora y pruebas de penetración</td></tr>"
      "<tr><td>Cambio normativo</td><td>Auditorías históricas mal interpretadas</td>"
      "<td>Criterios y umbrales versionados; cada auditoría conserva su versión</td></tr>"
      "<tr><td>Rotación de auditores</td><td>Pérdida de conocimiento</td>"
      "<td>Procedimiento documentado, ambiente de capacitación y criterios explícitos</td></tr>"
      "<tr><td>Dependencia de un único proveedor o persona</td><td>Riesgo operativo</td>"
      "<td>Repositorio institucional, documentación y transferencia de conocimiento</td></tr>"
      "</tbody></table>")

    # 12 factores críticos
    A("<h2>12. Factores críticos de éxito</h2>")
    A("<div class='aviso'><b>La tecnología no es el cuello de botella.</b> Un despliegue nacional se detiene por "
      "falta de decisión institucional, por indefinición sobre la propiedad del dato o por ausencia de formación "
      "en terreno; no por capacidad de cómputo.</div>")
    A("<ul>"
      "<li><b>Un dueño institucional del dato</b> y del procedimiento, con facultad de decisión.</li>"
      "<li><b>Adopción formal</b> del procedimiento digital por acto administrativo.</li>"
      "<li><b>Comité técnico</b> que resuelva interpretaciones de los criterios, con actas.</li>"
      "<li><b>Plan de formación</b> por regional y material de apoyo reutilizable.</li>"
      "<li><b>Presupuesto plurianual</b> para infraestructura, soporte y auditoría de seguridad.</li>"
      "<li><b>Gobierno del cambio normativo</b>: quién actualiza criterios, cómo se versiona y cómo se comunica.</li>"
      "</ul>")

    A("<h2>Anexo. Inventario técnico del piloto</h2>")
    A("<table><thead><tr><th>Elemento</th><th>Descripción</th></tr></thead><tbody>"
      "<tr><td>Núcleo de cálculo</td><td><code>guardar_auditoria.py</code>: único punto de escritura de porcentajes y concepto</td></tr>"
      "<tr><td>Consolidación de fuentes</td><td><code>procesar_kobo.py</code>, <code>importar_hoja.py</code>, API local, consola</td></tr>"
      "<tr><td>Publicación</td><td>Dashboard HTML estático, capa geográfica GeoJSON, hoja de cálculo institucional</td></tr>"
      "<tr><td>Documentos</td><td><code>generar_plan_accion.py</code>, <code>reporte_periodo_pdf.py</code>, "
      "<code>listado_predios_pdf.py</code>, <code>pdf_html.py</code></td></tr>"
      "<tr><td>Seguimiento</td><td><code>seguimiento.py</code>: estados, responsables, plazos y evidencia</td></tr>"
      "<tr><td>Verificación</td><td><code>verificar_kobo.py</code>, <code>revisar_duplicados_kobo.py</code>, respaldos diarios</td></tr>"
      "<tr><td>Automatización</td><td>Importación periódica, sincronización diaria y publicación desatendida</td></tr>"
      "</tbody></table>")
    A("<p class='nota'>Documento técnico de referencia para la revisión de los líderes del proceso. Las cifras de "
      "cobertura corresponden al estado del sistema a la fecha de emisión. No constituye certificación oficial del "
      "ICA ni compromiso contractual. Los datos personales de productores se omiten de acuerdo con la Ley 1581 de 2012.</p>")

    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            "<title>Arquitectura objetivo · Auditor BPG</title>" + CSS + "</head><body>"
            + "".join(H) + "</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=os.path.join(BASE, "Arquitectura_Objetivo_Auditor_BPG.pdf"))
    a = ap.parse_args()
    d = datos()
    html = construir(d)
    os.makedirs(os.path.expanduser("~/.hermes/cache/scratch"), exist_ok=True)
    open(os.path.expanduser("~/.hermes/cache/scratch/arquitectura.html"), "w", encoding="utf-8").write(html)
    sys.path.insert(0, BASE)
    from pdf_html import html_a_pdf
    ok, motor = html_a_pdf(html, a.salida)
    if not ok:
        print("ERROR: ningún motor de PDF disponible")
        return 1
    print("PDF:", a.salida, "(motor:", motor + ")")
    print(f"contexto: {d['predios']} predios · {d['auditorias']} auditorías · {d['municipios']} municipios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
