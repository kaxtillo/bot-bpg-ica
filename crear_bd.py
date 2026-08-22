#!/usr/bin/env python3
"""
Seed de la base de datos de consolidación de auditorías BPG ICA (Res. 067449).
Crea ~/auditorias_bpg/auditorias_bpg.db con:
  - criterios  (62 criterios de la Forma 3-852 V6, desde Formato_Auditoria_BPG_62Criterios.xlsx)
  - predios    (predios evaluados)
  - auditorias (resultados consolidados)
  - respuestas (detalle SI/NO/NA por criterio)
Fuentes de migración: JSON auditoria_san_jose5.json + MEMORY.md del repo bot-bpg-ica.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime

REPO = os.path.expanduser("~/Proyectos/bot-bpg-ica")
DB_DIR = os.path.expanduser("~/auditorias_bpg")
DB = os.path.join(DB_DIR, "auditorias_bpg.db")

# ── 62 criterios (Forma 3-852 V6): (id, seccion, nombre, tipo, articulo, pregunta) ──
CRITERIOS = [
    ("1.1", 1, "Plan Sanitario", "F", "5.1.1", "¿El predio cuenta con un plan sanitario elaborado y suscrito por un Médico Veterinario o Médico Veterinario Zootecnista con matrícula profesional vigente?"),
    ("1.2", 1, "Certificación de Hatos Libres", "My", "5.1.2", "¿El predio cuenta con certificación oficial vigente que acredite el hato como libre de brucelosis y tuberculosis?"),
    ("1.3", 1, "Protocolo de Aislamiento", "F", "5.1.3", "¿El predio cuenta con un protocolo escrito de manejo y aislamiento de animales enfermos?"),
    ("1.4", 1, "Registro de Diagnósticos", "F", "5.1.4", "¿Se lleva un registro escrito de los diagnósticos de enfermedades y las mortalidades presentadas en el predio?"),
    ("1.5", 1, "Instructivo de Enfermedades", "F", "5.1.5", "¿Existe un instructivo visible para el reconocimiento y notificación de enfermedades de control oficial?"),
    ("1.6", 1, "Área de Enfermería", "F", "5.1.6", "¿El predio dispone de un área o potrero señalizado como sitio de enfermería o tratamiento?"),
    ("1.7", 1, "Programa de Mastitis", "F", "5.1.7", "¿El predio cuenta con un programa de prevención y control de mastitis documentado?"),
    ("2.1", 2, "Identificación de Animales", "F", "5.2.1", "¿Los animales están identificados de manera única e individual?"),
    ("2.2", 2, "Registro Individual", "My", "5.2.2", "¿Se lleva un registro o ficha individual para cada animal?"),
    ("3.1", 3, "Delimitación del Predio", "My", "5.3.1", "¿El predio cuenta con cercos, broches, puertas o mecanismos en buen estado, que permitan delimitar el predio?"),
    ("3.2", 3, "Registro de Visitas", "My", "5.3.2", "¿Se lleva un registro escrito de ingreso de personas y vehículos?"),
    ("3.3", 3, "Cuarentena", "My", "5.3.3", "¿El predio cuenta con un procedimiento de ingreso y aislamiento de animales con cuarentena no menor a 21 días?"),
    ("3.4", 3, "Material Genético", "Mn", "5.3.4", "¿El material genético proviene de centros de producción o importación autorizados por el ICA?"),
    ("3.5", 3, "Identificación de Áreas", "Mn", "5.3.5", "¿Cada área de producción (bodega, almacén, botiquín) está debidamente identificada en un lugar visible?"),
    ("4.1", 4, "Zona de Espera", "My", "6.1", "¿La zona de espera de los animales antes del ordeño está en condiciones higiénicas adecuadas?"),
    ("4.2", 4, "Instalaciones de Ordeño Fijo", "F", "6.2", "¿Las instalaciones de ordeño fijo tienen pisos, paredes y techos en buen estado?"),
    ("4.3", 4, "Instalaciones de Ordeño Móvil", "F", "6.3", "¿Las instalaciones de ordeño móvil en potrero están protegidas de la intemperie?"),
    ("4.4", 4, "Instalaciones Sanitarias", "Mn", "6.4", "¿El predio cuenta con servicios sanitarios adecuados para el personal?"),
    ("4.5", 4, "Rutina de Ordeño", "F", "6.5.1", "¿Existe un procedimiento documentado de la rutina de ordeño?"),
    ("4.6", 4, "Equipos y Utensilios", "F", "6.5.2,6.5.3,6.5.6", "¿Los equipos y utensilios de ordeño son apropiados, están limpios y almacenados correctamente?"),
    ("4.7", 4, "Disposición Leche Anormal", "F", "6.5.4", "¿La leche anormal y de retiro se descarta adecuadamente?"),
    ("4.8", 4, "Agua para Ordeño", "My", "6.5.5", "¿El agua utilizada para la rutina de ordeño es potable?"),
    ("4.9", 4, "Conservación de la Leche", "My", "6.5.7", "¿El sistema de almacenamiento mantiene la leche a temperatura adecuada?"),
    ("5.1", 5, "Cuarto del Tanque de Leche", "F", "7.1,7.2,7.3", "¿El tanque de enfriamiento está en un cuarto cerrado y dedicado únicamente para tal fin?"),
    ("5.2", 5, "Registro de Temperatura", "My", "7.5", "¿Se cuenta con un registro de temperatura que verifique el funcionamiento del tanque?"),
    ("6.1", 6, "Productos con Registro ICA", "F", "8.1", "¿Se utilizan únicamente productos veterinarios con registro ICA?"),
    ("6.2", 6, "Productos No Vencidos", "F", "8.2", "¿Los productos veterinarios están vigentes?"),
    ("6.3", 6, "Almacenamiento de Medicamentos", "My", "8.3,8.4,8.5", "¿Los medicamentos están almacenados según condiciones del rotulado?"),
    ("6.4", 6, "Sustancias Prohibidas", "F", "8.6", "¿No se utilizan sustancias prohibidas por el ICA?"),
    ("6.5", 6, "Materias Primas como Medicamentos", "F", "8.7", "¿No se suministran materias primas químicas directamente a los animales?"),
    ("6.6", 6, "Tiempos de Retiro", "F", "8.8", "¿Se respetan los tiempos de retiro consignados en los medicamentos?"),
    ("6.7", 6, "Prescripción Veterinaria", "F", "8.9,8.15", "¿Los tratamientos tienen prescripción escrita de MV o MVZ?"),
    ("6.8", 6, "Registros de Tratamientos", "F", "8.10", "¿Se lleva registro de los tratamientos realizados?"),
    ("6.9", 6, "Equipos de Administración", "My", "8.11,8.12", "¿Los equipos para la aplicación de medicamentos están limpios y se usan agujas desechables?"),
    ("6.10", 6, "Inventario de Productos", "My", "8.13", "¿Se lleva un control de inventario de productos veterinarios?"),
    ("6.11", 6, "Autorización para Aplicación", "My", "8.14", "¿El responsable de aplicar medicamentos cuenta con capacitación y autorización?"),
    ("6.12", 6, "Notificación de Eventos Adversos", "My", "8.16", "¿Se notifican al ICA los eventos adversos?"),
    ("7.1", 7, "Alimentos con Registro ICA", "F", "9.1", "¿Los alimentos comerciales cuentan con registro ICA y están bien almacenados?"),
    ("7.2", 7, "Alimento Medicado", "F", "9.2", "¿Utiliza alimentos para administrar medicamentos con registro ICA y fórmula médica?"),
    ("7.3", 7, "Prohibiciones Alimentarias", "F", "9.6,9.7", "¿No se utilizan harinas de carne, sangre y hueso?"),
    ("7.4", 7, "Subproductos", "My", "9.4", "¿Los subproductos están en buen estado y se registra su origen?"),
    ("7.5", 7, "Insumos Agrícolas", "F", "9.8,9.9", "¿Se emplean plaguicidas con registro ICA, respetando períodos de carencia?"),
    ("7.6", 7, "Inventario de Alimentos", "Mn", "9.10", "¿Se lleva inventario de alimentos y materias primas?"),
    ("7.7", 7, "Calidad del Agua", "My", "9.11,9.12,9.13", "¿Se realiza monitoreo anual de la calidad del agua para consumo animal?"),
    ("8.1", 8, "Limpieza de Áreas", "My", "10.1,10.4", "¿Las áreas, equipos y utensilios están limpios y ordenados?"),
    ("8.2", 8, "Ubicación del Predio", "My", "10.2", "¿El predio está ubicado en zonas alejadas de focos de contaminación?"),
    ("8.3", 8, "Protección de Fuentes Hídricas", "My", "10.3", "¿Se implementan acciones para proteger las fuentes de agua?"),
    ("8.4", 8, "Disposición de Estiércol", "My", "10.5", "¿Se utilizan métodos apropiados para la disposición de estiércol?"),
    ("8.5", 8, "Manejo de Residuos", "My", "10.6,10.7,10.8,10.15", "¿Los residuos sólidos se clasifican y disponen adecuadamente?"),
    ("8.6", 8, "Almacenamiento de Insumos", "My", "10.9,10.10", "¿Los alimentos, medicamentos y plaguicidas se almacenan en áreas separadas?"),
    ("8.7", 8, "Control de Plagas", "My", "10.12,10.13", "¿Se cuenta con un programa escrito de control de plagas y roedores?"),
    ("9.1", 9, "Adaptación de Animales", "My", "11.1.1", "¿Se realiza un proceso de adaptación para animales introducidos?"),
    ("9.2", 9, "Superficies y Espacio", "My", "11.1.2", "¿Las superficies permiten un desplazamiento seguro?"),
    ("9.3", 9, "Agrupamiento Social", "My", "11.1.3", "¿Se permite el agrupamiento social sin causar lesiones?"),
    ("9.4", 9, "Estabulación", "My", "11.1.4", "¿En estabulación, la ventilación y temperatura son adecuadas?"),
    ("9.5", 9, "Enfermedades y Parásitos", "My", "11.1.6", "¿Se controlan y tratan oportunamente las enfermedades de los animales?"),
    ("9.6", 9, "Alimentos y Agua", "My", "11.1.5", "¿Los animales tienen acceso suficiente a alimentos y agua?"),
    ("9.7", 9, "Sacrificio Humanitario", "My", "11.1.6", "¿Cuando es necesario, se aplica sacrificio humanitario?"),
    ("9.8", 9, "Manejo del Dolor", "F", "11.1.7", "¿En procedimientos dolorosos, se maneja el dolor en los animales?"),
    ("9.9", 9, "Relación Hombre-Animal", "My", "11.1.8", "¿El manejo promueve una relación positiva sin causar estrés en los animales?"),
    ("10.1", 10, "Capacitación del Personal", "F", "11.2.1", "¿El personal cuenta con capacitación en buenas prácticas ganaderas?"),
    ("10.2", 10, "Uso de Implementos", "Mn", "11.2.1", "¿El personal hace uso de los implementos necesarios?"),
]

# ── Datos migrados: San José 5 (JSON completo del repo) ──
SAN_JOSE5 = {
    "predio": "SAN JOSÉ 5",
    "propietario": "Edison Lozada Mensa",
    "identificacion": "1064676804",
    "telefono": "3105162252",
    "departamento": "Cauca",
    "municipio": "Sotará",
    "vereda": "Piedra de León",
    "latitud": 2.241723,
    "longitud": -76.554590,
    "rspp": "SI",
    "especie": "BOVINO LECHERO",
    "fin_zootecnico": "PRODUCCIÓN LECHE",
    "fecha": "2026-04-04",
    "concepto": "Certificable",
    "f_cumplidos": 22, "f_total": 22, "f_pct": 100.0,
    "my_cumplidos": 25, "my_total": 26, "my_pct": 96.15,
    "mn_cumplidos": 12, "mn_total": 12, "mn_pct": 100.0,
    "observaciones": "1.2: Requiere certificación oficial vigente de hato libre de brucelosis y tuberculosis; 7.7: Requiere implementar monitoreo anual de calidad del agua para consumo animal",
    "fuente": "JSON auditoria_san_jose5.json",
}

# EL ARENAL (resumen en MEMORY.md del repo; sin detalle por criterio)
EL_ARENAL = {
    "predio": "EL ARENAL",
    "propietario": "Francy Quira",
    "identificacion": "25852698",
    "departamento": "Cauca",
    "municipio": "Puracé",
    "vereda": "Campamento",
    "latitud": 2.454843,
    "longitud": -76.631613,
    "especie": "Bovina",
    "fin_zootecnico": "Leche",
    "produccion": 500,
    "total_animales": 50,
    "fecha": "2026-04-04",
    "concepto": "Certificable",
    "f_cumplidos": 22, "f_total": 23, "f_pct": 95.7,
    "my_cumplidos": 26, "my_total": 27, "my_pct": 96.3,
    "mn_cumplidos": 2, "mn_total": 2, "mn_pct": 100.0,
    "observaciones": "NO: 1.2 (My) Certificación hatos libres; 4.2 (F) Instalaciones ordeño fijo",
    "fuente": "MEMORY.md del repo bot-bpg-ica",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS criterios (
    id TEXT PRIMARY KEY,
    seccion INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('F','My','Mn')),
    articulo TEXT,
    pregunta TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS predios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    propietario TEXT,
    identificacion TEXT,
    telefono TEXT,
    email TEXT,
    departamento TEXT,
    municipio TEXT,
    vereda TEXT,
    latitud REAL,
    longitud REAL,
    rspp TEXT,
    especie TEXT,
    fin_zootecnico TEXT,
    produccion TEXT,
    total_animales INTEGER
);
CREATE TABLE IF NOT EXISTS auditorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    predio_id INTEGER NOT NULL REFERENCES predios(id),
    fecha TEXT NOT NULL,
    concepto TEXT NOT NULL,
    f_cumplidos INTEGER, f_total INTEGER, f_pct REAL,
    my_cumplidos INTEGER, my_total INTEGER, my_pct REAL,
    mn_cumplidos INTEGER, mn_total INTEGER, mn_pct REAL,
    observaciones TEXT,
    recomendaciones TEXT,
    fuente TEXT
);
CREATE TABLE IF NOT EXISTS respuestas (
    auditoria_id INTEGER NOT NULL REFERENCES auditorias(id),
    criterio_id TEXT NOT NULL REFERENCES criterios(id),
    respuesta TEXT NOT NULL CHECK (respuesta IN ('SI','NO','NA')),
    PRIMARY KEY (auditoria_id, criterio_id)
);
"""


def parse_pct(s):
    """'96.15%' -> 96.15"""
    try:
        return float(str(s).replace("%", "").strip())
    except Exception:
        return None


def main():
    os.makedirs(DB_DIR, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    # criterios (idempotente)
    n_crit = 0
    for c in CRITERIOS:
        con.execute(
            "INSERT OR IGNORE INTO criterios (id, seccion, nombre, tipo, articulo, pregunta) VALUES (?,?,?,?,?,?)",
            c,
        )
        n_crit += 1

    # San José 5: importar del JSON del repo si existe (autoritativo)
    sj_path = os.path.join(REPO, "auditoria_san_jose5.json")
    detalle = {}
    if os.path.exists(sj_path):
        with open(sj_path, encoding="utf-8") as f:
            j = json.load(f)
        detalle = j.get("detalle_puntos", {})
        # sobreescribir porcentajes si el JSON trae más
        if j.get("fundamentales_porcentaje"):
            SAN_JOSE5["f_pct"] = parse_pct(j["fundamentales_porcentaje"]) or SAN_JOSE5["f_pct"]
        if j.get("mayores_porcentaje"):
            SAN_JOSE5["my_pct"] = parse_pct(j["mayores_porcentaje"]) or SAN_JOSE5["my_pct"]
        if j.get("menores_porcentaje"):
            SAN_JOSE5["mn_pct"] = parse_pct(j["menores_porcentaje"]) or SAN_JOSE5["mn_pct"]
        if j.get("observaciones"):
            SAN_JOSE5["observaciones"] = j["observaciones"]
        r = j.get("resultados", {})
        for k in ("f_cumplidos", "f_total", "my_cumplidos", "my_total", "mn_cumplidos", "mn_total"):
            # derivar de cadenas tipo '22/22 = 100%' si están
            pass
        if r.get("criterios_fundamentales"):
            a, b = str(r["criterios_fundamentales"]).split("/")[0], str(r["criterios_fundamentales"]).split("/")[1].split(" ")[0]
            SAN_JOSE5["f_cumplidos"], SAN_JOSE5["f_total"] = int(a), int(b)
        if r.get("criterios_mayores"):
            a, b = str(r["criterios_mayores"]).split("/")[0], str(r["criterios_mayores"]).split("/")[1].split(" ")[0]
            SAN_JOSE5["my_cumplidos"], SAN_JOSE5["my_total"] = int(a), int(b)
        if r.get("criterios_menores"):
            a, b = str(r["criterios_menores"]).split("/")[0], str(r["criterios_menores"]).split("/")[1].split(" ")[0]
            SAN_JOSE5["mn_cumplidos"], SAN_JOSE5["mn_total"] = int(a), int(b)

    # predios
    def upsert_predio(p):
        cur = con.execute(
            """INSERT INTO predios (nombre, propietario, identificacion, telefono, email, departamento,
               municipio, vereda, latitud, longitud, rspp, especie, fin_zootecnico, produccion, total_animales)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(nombre) DO UPDATE SET propietario=excluded.propietario,
                 identificacion=excluded.identificacion, telefono=excluded.telefono, departamento=excluded.departamento,
                 municipio=excluded.municipio, vereda=excluded.vereda, latitud=excluded.latitud,
                 longitud=excluded.longitud, rspp=excluded.rspp, especie=excluded.especie,
                 fin_zootecnico=excluded.fin_zootecnico, produccion=excluded.produccion,
                 total_animales=excluded.total_animales""",
            (
                p["predio"], p.get("propietario"), p.get("identificacion"), p.get("telefono"), p.get("email"),
                p.get("departamento"), p.get("municipio"), p.get("vereda"), p.get("latitud"), p.get("longitud"),
                p.get("rspp"), p.get("especie"), p.get("fin_zootecnico"), p.get("produccion"),
                p.get("total_animales"),
            ),
        )
        return con.execute("SELECT id FROM predios WHERE nombre=?", (p["predio"],)).fetchone()[0]

    def upsert_auditoria(p, det=None):
        pid = upsert_predio(p)
        cur = con.execute(
            """INSERT INTO auditorias (predio_id, fecha, concepto, f_cumplidos, f_total, f_pct,
               my_cumplidos, my_total, my_pct, mn_cumplidos, mn_total, mn_pct, observaciones, fuente)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, p.get("fecha", datetime.now().strftime("%Y-%m-%d")), p["concepto"],
                p.get("f_cumplidos"), p.get("f_total"), p.get("f_pct"),
                p.get("my_cumplidos"), p.get("my_total"), p.get("my_pct"),
                p.get("mn_cumplidos"), p.get("mn_total"), p.get("mn_pct"),
                p.get("observaciones"), p.get("fuente"),
            ),
        )
        aid = cur.lastrowid
        if det:
            for cid, resp in det.items():
                if cid in {c[0] for c in CRITERIOS} and resp in ("SI", "NO", "NA"):
                    con.execute(
                        "INSERT OR REPLACE INTO respuestas (auditoria_id, criterio_id, respuesta) VALUES (?,?,?)",
                        (aid, cid, resp),
                    )
        return aid

    upsert_auditoria(SAN_JOSE5, detalle)
    upsert_auditoria(EL_ARENAL)  # sin detalle por criterio en la fuente

    con.commit()

    # ── verificación ──
    print("=== BASE DE DATOS CREADA ===")
    print(f"Ruta: {DB}")
    print(f"Criterios: {con.execute('SELECT COUNT(*) FROM criterios').fetchone()[0]}")
    print(f"Predios:   {con.execute('SELECT COUNT(*) FROM predios').fetchone()[0]}")
    print(f"Auditorías:{con.execute('SELECT COUNT(*) FROM auditorias').fetchone()[0]}")
    print(f"Respuestas:{con.execute('SELECT COUNT(*) FROM respuestas').fetchone()[0]}")
    print("\n=== AUDITORÍAS REGISTRADAS ===")
    for row in con.execute(
        """SELECT a.id, p.nombre, a.fecha, a.concepto, a.f_cumplidos||'/'||a.f_total, a.f_pct,
                  a.my_cumplidos||'/'||a.my_total, a.my_pct, a.mn_cumplidos||'/'||a.mn_total, a.mn_pct
           FROM auditorias a JOIN predios p ON p.id=a.predio_id ORDER BY a.fecha"""
    ):
        print(
            f"  #{row[0]} {row[1]:12s} {row[2]} | {row[3]:12s} | F {row[4]} ({row[5]}%) | "
            f"My {row[6]} ({row[7]}%) | Mn {row[8]} ({row[9]}%)"
        )
    print("\n=== HALLAZGOS (NO) SAN JOSÉ 5 ===")
    for row in con.execute(
        """SELECT r.criterio_id, c.nombre, c.tipo, c.articulo FROM respuestas r
           JOIN criterios c ON c.id=r.criterio_id
           JOIN auditorias a ON a.id=r.auditoria_id JOIN predios p ON p.id=a.predio_id
           WHERE p.nombre='SAN JOSÉ 5' AND r.respuesta='NO'"""
    ):
        print(f"  {row[0]} {row[1]} ({row[2]} - Art. {row[3]})")
    con.close()


if __name__ == "__main__":
    main()
