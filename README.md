# 🐄 Auditor BPG ICA — Resolución 067449

Sistema de **auditorías de Buenas Prácticas Ganaderas (BPG)** para predios de producción de leche, basado en la **Forma 3-852 V6** y la **Resolución 067449 del ICA** (Colombia).

Evaluación de **62 criterios** organizados en 10 secciones (Sanidad Animal, Identificación, Bioseguridad, Higiene del Ordeño, Tanque de Enfriamiento, Medicamentos Veterinarios, Alimentación Animal, Saneamiento, Bienestar Animal y Personal), con cálculo automático de cumplimiento:

| Tipo | Umbral |
|---|---|
| Fundamentales (F) | ≥ 90% |
| Mayores (My) | ≥ 80% |
| Menores (Mn) | ≥ 70% |

> Los criterios **NA (No Aplica) se excluyen del denominador**. El concepto final es **Certificable** o **Aplazado**.

---

## 📦 Componentes

### 1. 🤖 Bot de Telegram (@Auditor_ICA_bot)
Ejecuta auditorías conversacionales: registro del predio (7 datos) + las 62 preguntas una a una (SI/NO/NA), con cálculo y guardado automáticos. Corre sobre [Hermes Agent](https://hermes-agent.nousresearch.com/).

### 2. 🖥️ Auditoría local sin internet (`auditar.py`)
Auditoría 100% local, sin depender de IA online:
- **Modo interactivo:** `python3 auditar.py` — pregunta los 7 datos y las 62 preguntas en la terminal
- **Modo formulario:** `python3 auditar.py --archivo formulario.csv` — procesa un formulario llenado en campo (Excel/imprimible)
- `Ctrl+C` guarda el progreso parcial; se retoma después

### 3. 📱 App Android (PWA "Auditor BPG")
Aplicación web instalable (`app/`) que funciona **sin internet**:
- Registro del predio + 62 preguntas con botones grandes SI/NO/NA
- Cálculo local del resultado (porcentajes y concepto)
- Guarda auditorías en el dispositivo y exporta el JSON
- El JSON se envía al bot de Telegram para consolidar

### 4. 🗄️ Base de datos de consolidación (SQLite)
`auditorias_bpg.db` con 4 tablas:
- `criterios` — los 62 criterios (sección, tipo F/My/Mn, artículo, pregunta)
- `predios` — datos de los predios evaluados
- `auditorias` — resultados consolidados (conteos, % y concepto)
- `respuestas` — detalle SI/NO/NA por criterio y auditoría

### 5. 📊 Google Sheets (registro oficial)
Sincronización **bidireccional** con la hoja de cálculo oficial:
```bash
python3 sincronizar_hoja.py          # pull (hoja → BD) + push (BD → hoja)
python3 sincronizar_hoja.py --pull   # solo leer la hoja
```

### 6. 🗺️ Mapa UMap (georreferenciación)
Los predios se publican como GeoJSON en `mapa/predios_bpg_ica.geojson` y se cargan en un mapa UMap con actualización automática (cron horario → `subir_mapa.sh`).

---

## 🛠️ Scripts

| Script | Función |
|---|---|
| `crear_bd.py` | Crea la BD y siembra los 62 criterios |
| `auditar.py` | Auditoría local interactiva o desde formulario |
| `guardar_auditoria.py` | Cálculo automático y guardado desde JSON |
| `generar_formulario.py` | Genera el formulario CSV para campo |
| `consultar.py` | Consultas y seguimiento (resumen, detalle, hallazgos) |
| `importar_hoja.py` | Importa un CSV exportado de la hoja (idempotente) |
| `sincronizar_hoja.py` | Sincronización bidireccional con Google Sheets |
| `generar_geojson.py` | Genera el GeoJSON de predios para el mapa |
| `subir_mapa.sh` | Sube el GeoJSON a GitHub (cron horario) |
| `backup_bot.sh` | Respaldo completo del sistema |
| `generar_pwa.py` | Regenera la PWA con los criterios de la BD |

## 📁 Estructura

```
├── app/                    # PWA "Auditor BPG" (instalable en Android)
├── mapa/                   # GeoJSON de predios (alimenta el mapa UMap)
├── 00_Lista_Chequeo_Normativa/  …  10_Personal/   # Formatos NLM (14 PDFs)
├── auditorias/             # JSON de auditorías históricas
├── memory/                 # Memoria del bot anterior (OpenClaw)
├── AGENTS.md · SOUL.md · IDENTITY.md   # Configuración del agente
├── auditar.py · consultar.py · …       # Scripts del sistema
```

## 🚀 Uso rápido

```bash
# 1. Sembrar la base de datos (una vez)
python3 crear_bd.py

# 2. Auditar (local, sin internet)
python3 auditar.py

# 3. Consultar resultados
python3 consultar.py                    # resumen global
python3 consultar.py detalle "san jose 5"
python3 consultar.py hallazgos          # criterios en NO

# 4. Sincronizar con Google Sheets
python3 sincronizar_hoja.py

# 5. Actualizar el mapa
python3 generar_geojson.py
```

## 🔒 Seguridad

- **Nunca subir credenciales al repositorio.** Los archivos `credentials.json`, `token_final.json` y `oauth_state.json` (OAuth de Google) están excluidos vía `.gitignore` — si aparecen, revocar el token en [myaccount.google.com/security](https://myaccount.google.com/security).
- Las claves API viven en variables de entorno, no en el código.

## 📄 Normativa

- **Resolución 067449 de 2020** — ICA: requisitos para la certificación en BPG
- **Forma 3-852 V6** — lista de chequeo oficial (62 criterios)
- Formatos NLM originales en las carpetas `00_Lista_Chequeo_Normativa` a `10_Personal`
