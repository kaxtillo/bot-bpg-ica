#!/usr/bin/env python3
from fpdf import FPDF
import os

OUTPUT = "/home/ubuntu/.openclaw/workspace/00_Lista_Chequeo_Normativa"

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=18)

# ============================================================
# PORTADA
# ============================================================
pdf.add_page()
pdf.set_font("Helvetica", "B", 16)
pdf.ln(30)
pdf.cell(0, 10, "INSTITUTO COLOMBIANO AGROPECUARIO - ICA", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 8, "PROTOCOLO DE RUTINA DE ORDENO DOCUMENTADA", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 6, "Resolucion 067449 del 08 de mayo de 2020", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Articulo 8.5 - Criterio 4.5 (FUNDAMENTAL)", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.line(60, pdf.get_y(), 150, pdf.get_y())
pdf.ln(10)

pdf.set_font("Helvetica", "", 9)
campos = [
    ("PREDIO:", "_____________________________________________"),
    ("PROPIETARIO:", "_____________________________________________"),
    ("MUNICIPIO:", "____________________  VEREDA: ____________________"),
    ("FECHA DE ELABORACION:", "____________________  VERSION: ____"),
    ("RESPONSABLE DE ORDENO:", "_____________________________________________"),
]
for label, val in campos:
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(40, 5, label)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, val, new_x="LMARGIN", new_y="NEXT")
pdf.ln(15)
pdf.set_font("Helvetica", "I", 8)
pdf.cell(0, 4, "Este protocolo debe estar disponible y visible para todo el personal durante la auditoria.", align="C")

# ============================================================
# PAGINA 1: PROCEDIMIENTO PASO A PASO
# ============================================================
pdf.add_page()
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 7, "PROCEDIMIENTO DE ORDENO - PASO A PASO", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

pasos = [
    ("PASO 1", "VERIFICACION VISUAL DE LA UBRE", 
     "Antes del ordeño, verifique visualmente cada ubre en busca de edema, heridas, inflamacion o signos de mastitis clinica. Los animales con anomalias deben ordeñarse al final o con equipo separado."),
    ("PASO 2", "PRUEBA DE FONDA O MASTITIS CLINICA",
     "Realice la prueba de fonda (CMT - California Mastitis Test) a cada cuarto. Registre los resultados. Los cuartos con reaccion positiva (+) deben marcarse y la leche debe descartarse."),
    ("PASO 3", "LAVADO Y SECADO DE UBres",
     "Lave cada ubre con agua limpia y jabón (o producto especifico para higiene de ubres). Seque con toalla de papel individual (un solo uso por animal). No use toallas compartidas."),
    ("PASO 4", "SELLADO DE PEZONES - PREDIPPING",
     "Aplique sellador predipping (desinfectante) en cada pezón. Deje actuar por al menos 30 segundos. Seque cada pezón con toalla individual."),
    ("PASO 5", "COLOCACION DE PEZONERAS",
     "Coloque las pezoneras dentro del minuto siguiente al secado (evitar que la ubre se contamine nuevamente). Evite la entrada de aire durante la colocacion."),
    ("PASO 6", "VERIFICACION DE FLUJO DE LECHE",
     "Verifique que el flujo de leche sea constante y que no haya deslizamiento o caida de pezoneras. Ajuste si es necesario. No sobre-ordene (tiempo maximo recomendado: 5-7 minutos)."),
    ("PASO 7", "RETIRO DE PEZONERAS",
     "Retire las pezoneras cortando el vacio (automatico o manualmente). No arranque las pezoneras con vacio. Aplique post-dipping inmediatamente despues del retiro."),
    ("PASO 8", "POST-DIPPING",
     "Aplique sellador post-ordeno (post-dipping) cubriendo al menos el 75% del pezon. Deje secar al aire. No lave los pezones despues de aplicar."),
    ("PASO 9", "FILTRADO Y ENFRIAMIENTO",
     "Filtre la leche inmediatamente. Enfriela a <= 4 grados C en las primeras 2 horas post-ordeno. Registre la temperatura."),
]

for paso in pasos:
    num, titulo, desc = paso
    y = pdf.get_y()
    if y > 245:
        pdf.add_page()
    
    pdf.set_fill_color(41, 65, 122)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, f"  {num}: {titulo}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4.5, f"     {desc}")
    pdf.ln(2)

# ============================================================
# PAGINA 2: LAVADO DE EQUIPOS
# ============================================================
pdf.add_page()
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 7, "LAVADO Y DESINFECCION DE EQUIPOS DE ORDENO", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

pdf.set_font("Helvetica", "B", 9)
pdf.cell(0, 5, "PROCEDIMIENTO DE LAVADO (post-ordeno):", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

pasos_lavado = [
    ("1.", "ENJUAGUE INICIAL", "con agua fria o tibia (no caliente, para evitar que la proteina se adhiera)"),
    ("2.", "LAVADO CON DETERGENTE ALCALINO", "recircule agua entre 60-70 grados C con detergente alcalino clorado por 10-15 minutos"),
    ("3.", "ENJUAGUE INTERMEDIO", "con agua limpia para remover residuos de detergente"),
    ("4.", "LAVADO CON DETERGENTE ACIDO", "recircule con detergente acido una vez por semana (o segun recomendacion del fabricante) para eliminar sarro y minerales"),
    ("5.", "ENJUAGUE FINAL", "con agua limpia, justo antes del siguiente ordeño"),
    ("6.", "DESMONTAR Y LAVAR MANUALMENTE", "las pezoneras, mangueras cortas y colectores deben desmontarse periodicamente y lavarse a mano"),
]

for paso in pasos_lavado:
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(5, 5, paso[0])
    pdf.cell(50, 5, paso[1])
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, paso[2], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

pdf.ln(3)

# Frecuencia de mantenimiento
pdf.set_font("Helvetica", "B", 9)
pdf.cell(0, 5, "FRECUENCIA DE MANTENIMIENTO:", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

pdf.set_font("Helvetica", "", 8)
items_mant = [
    "Cambio de pezoneras (lineas de leche): cada 1,500 a 2,500 ordenos o segun fabricante",
    "Limpieza de pulsadores: cada 3 meses",
    "Revision del sistema de vacio: cada 6 meses",
    "Calibracion del medidor de vacio: cada 12 meses",
    "Revision general por tecnicos: cada 6 meses (con certificacion)",
]
for item in items_mant:
    pdf.cell(5, 5, "")
    pdf.cell(0, 5, f"-  {item}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

# ============================================================
# PAGINA 3: CHECKLIST DIARIO
# ============================================================
pdf.add_page()
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 7, "CHECKLIST DIARIO DE VERIFICACION DE RUTINA", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)

headers = ["FECHA", "TURNO", "No. VACAS", "VOLUMEN", "TEMP SALIDA", "PRUEBA CMT REALIZADA", "NOVEDADES", "FIRMA"]
col_w = [14, 10, 14, 16, 16, 30, 48, 20]
pdf.set_font("Helvetica", "B", 6)
pdf.set_fill_color(41, 65, 122)
pdf.set_text_color(255, 255, 255)
for i, h in enumerate(headers):
    pdf.cell(col_w[i], 6, h, border=1, align="C", fill=True)
pdf.ln()
pdf.set_text_color(0, 0, 0)
pdf.set_font("Helvetica", "", 6)
for _ in range(7):
    for w in col_w:
        pdf.cell(w, 6, "", border=1)
    pdf.ln()

pdf.ln(5)
pdf.set_font("Helvetica", "B", 9)
pdf.cell(0, 5, "REGISTRO DE MANTENIMIENTO DE EQUIPOS:", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

headers2 = ["FECHA", "EQUIPO / COMPONENTE", "ACTIVIDAD REALIZADA", "TECNICO", "PROXIMO MANTENIMIENTO", "FIRMA"]
col_w2 = [14, 30, 48, 28, 34, 14]
pdf.set_font("Helvetica", "B", 6)
pdf.set_fill_color(41, 65, 122)
pdf.set_text_color(255, 255, 255)
for i, h in enumerate(headers2):
    pdf.cell(col_w2[i], 6, h, border=1, align="C", fill=True)
pdf.ln()
pdf.set_text_color(0, 0, 0)
pdf.set_font("Helvetica", "", 6)
for _ in range(6):
    for w in col_w2:
        pdf.cell(w, 6, "", border=1)
    pdf.ln()

pdf.ln(6)
pdf.set_font("Helvetica", "I", 8)
pdf.cell(0, 4, "Nota: Este protocolo debe ser conocido por todo el personal involucrado en el ordeño. Mantener visible en la sala de ordeño.", new_x="LMARGIN", new_y="NEXT")

# Guardar
path = os.path.join(OUTPUT, "Protocolo_Rutina_Ordeno.pdf")
pdf.output(path)
print(f"✅ Protocolo generado: {path}")
print(f"   Tamano: {os.path.getsize(path)} bytes, {pdf.page_no()} paginas")
