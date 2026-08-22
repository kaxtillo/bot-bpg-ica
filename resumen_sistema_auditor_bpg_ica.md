# SISTEMA AUDITOR BPG ICA — Resolución 067449
## Plataforma integral de auditorías de Buenas Prácticas Ganaderas para predios de producción de leche

---

## 1. DESCRIPCIÓN GENERAL

El **Sistema Auditor BPG ICA** es una plataforma tecnológica diseñada para ejecutar, consolidar y dar seguimiento a las auditorías de **Buenas Prácticas Ganaderas (BPG)** en predios de producción de leche, conforme a la **Resolución 067449 de 2020 del Instituto Colombiano Agropecuario (ICA)** y la **Forma 3-852 Versión 6** (lista de chequeo oficial).

La plataforma permite evaluar predios mediante **62 criterios** organizados en 10 secciones, con cálculo automático de cumplimiento, emisión de concepto (Certificable/Aplazado), georreferenciación de predios, sincronización con Google Sheets y generación de mapas interactivos. Está diseñada para funcionar **sin conexión a internet** en campo (fincas del departamento del Cauca, Colombia) y sincronizar automáticamente cuando hay conectividad.

**Objetivo:** preparar a los productores ganaderos para la certificación oficial del ICA en Buenas Prácticas Ganaderas, mediante autoevaluaciones objetivas y seguimiento de los hallazgos.

---

## 2. CONTEXTO NORMATIVO

| Instrumento | Descripción |
|---|---|
| **Resolución 067449 de 2020 (ICA)** | Establece los requisitos sanitarios y de buenas prácticas para la obtención del registro de predios pecuarios dedicados a la producción de leche |
| **Forma 3-852 V6** | Lista de chequeo oficial con los 62 criterios de evaluación |
| **14 formatos NLM** | Registros oficiales complementarios (sanidad, identificación, bioseguridad, higiene del ordeño, medicamentos, alimentación, saneamiento, bienestar animal y personal) |

### Las 10 secciones evaluadas
1. **Sanidad Animal** (7 criterios) — plan sanitario, certificación de hatos libres, protocolos de aislamiento, registros de diagnósticos, instructivo de enfermedades de control oficial, área de enfermería, programa de mastitis
2. **Identificación** (2 criterios) — identificación individual de animales, registro/ficha individual
3. **Bioseguridad** (5 criterios) — delimitación del predio, registro de visitas, cuarentena, material genético, identificación de áreas
4. **Higiene del Ordeño** (9 criterios) — zona de espera, instalaciones fijas y móviles, servicios sanitarios, rutina de ordeño, equipos y utensilios, disposición de leche anormal, agua potable, conservación de la leche
5. **Tanque de Enfriamiento** (2 criterios) — cuarto del tanque, registro de temperatura
6. **Medicamentos Veterinarios** (12 criterios) — productos con registro ICA, vigencia, almacenamiento, sustancias prohibidas, tiempos de retiro, prescripción veterinaria, registros de tratamientos, equipos, inventarios, autorización, notificación de eventos adversos
7. **Alimentación Animal** (7 criterios) — alimentos con registro ICA, alimento medicado, prohibiciones alimentarias, subproductos, insumos agrícolas, inventario de alimentos, calidad del agua
8. **Saneamiento** (7 criterios) — limpieza, ubicación del predio, protección de fuentes hídricas, disposición de estiércol, manejo de residuos, almacenamiento de insumos, control de plagas
9. **Bienestar Animal** (9 criterios) — adaptación, superficies, agrupamiento social, estabulación, enfermedades y parásitos, alimentos y agua, sacrificio humanitario, manejo del dolor, relación hombre-animal
10. **Personal** (2 criterios) — capacitación en BPG, uso de implementos

---

## 3. METODOLOGÍA DE CÁLCULO (Forma 3-852 V6)

- Los criterios **NA (No Aplica) se excluyen del denominador** del cálculo.
- **Umbrales oficiales:**
  - **Fundamentales (F): 100%** — todos los criterios fundamentales deben cumplirse
  - **Mayores (My): ≥ 80%**
  - **Menores (Mn): ≥ 60%**
- **Concepto final:**
  - **CERTIFICABLE** — cumple los tres umbrales simultáneamente
  - **APLAZADO** — no cumple uno o más umbrales

El cálculo es 100% automático e idéntico en todas las vías de entrada (app, bot, terminal), lo que garantiza consistencia total y elimina errores humanos de aritmética.

---

## 4. ARQUITECTURA DEL SISTEMA

### 4.1 Tres vías de entrada, un solo punto de escritura

```
📱 App Android (APK, funciona offline)  ─┐
🤖 Bot de Telegram (@Auditor_ICA_bot)   ─┼→ Pipeline único de validación y cálculo
🖥️ Auditor local (terminal o formulario)─┘          ↓
                                        🗄️ Base de datos SQLite (único punto de escritura)
                                         ├── 📊 Google Sheets (registro oficial, sincronización bidireccional)
                                         └── 🗺️ Mapa UMap (georreferenciación, actualización automática)
```

### 4.2 Componentes

**a) App Android "Auditor BPG" (PWA + APK)**
- Funciona **100% sin internet** (criterios embebidos en el dispositivo)
- Registro del predio (7 datos) + 62 preguntas con botones táctiles SI/NO/NA
- Cálculo local inmediato del resultado con veredicto
- Almacenamiento local de auditorías (funciona en campo sin señal)
- **Sincronización automática** por WiFi hacia el servidor local (POST /api/auditorias) cuando hay conectividad
- Exportación de resultados en formato JSON

**b) Bot de Telegram @Auditor_ICA_bot**
- Auditoría conversacional guiada: registro inicial + 62 preguntas una a una
- Respuestas SI/NO/NA con validación
- Cálculo y guardado automáticos
- Consultas y seguimiento por chat ("¿cómo va El Arenal?")
- Notificaciones de actualización del sistema

**c) Auditor local (terminal)**
- `auditar.py` — auditoría interactiva en terminal, 100% local, sin dependencia de modelos de IA online
- `generar_formulario.py` — formulario CSV (Excel/imprimible) para llenar en campo
- Modo archivo: procesa formularios completados
- Recuperación de progreso (Ctrl+C guarda parcial)

**d) Base de datos SQLite (consolidación)**
- Tablas: `criterios` (62), `predios`, `auditorias`, `respuestas` (detalle SI/NO/NA)
- Sin duplicados (upsert por predio + fecha + concepto)
- Recalculable con umbrales oficiales

**e) Google Sheets (registro oficial)**
- Sincronización bidireccional hoja ↔ base local
- Formato real de la hoja: 89 columnas, criterios `C1.1|F`
- El registro oficial de auditorías vive en la nube

**f) Mapa UMap (georreferenciación)**
- Predios georreferenciados con marcadores de color según concepto (verde = certificable, rojo = aplazado)
- Popups con datos del predio, porcentajes y hallazgos
- Actualización automática cada hora (cron → GeoJSON en GitHub → UMap)

**g) Servidor API local**
- Endpoints: `GET /api/health`, `POST /api/auditorias`, `GET /api/predios`, `GET /api/auditorias`
- Recibe las auditorías de la app Android y las consolida directamente

### 4.3 Infraestructura
- Compilación automática del APK con **GitHub Actions** (workflow CI/CD)
- Repositorio público: github.com/kaxtillo/bot-bpg-ica
- App web instalable (PWA) alojada en el repositorio
- OAuth de Google para acceso a Sheets (token auto-renovable)

---

## 5. FLUJO DE TRABAJO EN CAMPO

1. **En la finca (sin señal):** el auditor abre la app en el celular, registra el predio (nombre, propietario, cédula, municipio, vereda, teléfono, GPS) y responde los 62 criterios con un toque (SI/NO/NA). El teléfono calcula el resultado al instante.
2. **Al tener conectividad:** pulsa "Sincronizar" → la auditoría viaja al servidor local → se consolida en la base de datos.
3. **Consolidación automática:** la base actualiza Google Sheets (registro oficial) y el mapa UMap (georreferenciación).
4. **Seguimiento:** consultas por Telegram o terminal: resumen global, detalle por predio, hallazgos pendientes.

---

## 6. ESTADO ACTUAL DE LA PLATAFORMA

**Predios evaluados (4):**

| Predio | Municipio | Vereda | Fundamentales | Mayores | Menores | Concepto |
|---|---|---|---|---|---|---|
| SAN JOSÉ 5 | Sotará | Piedra de León | 22/22 (100%) | 25/26 (96.2%) | 4/4 (100%) | ✅ Certificable |
| EL ARENAL | Puracé | Campamento | 23/23 (100%) | 24/25 (96.0%) | 4/4 (100%) | ✅ Certificable |
| EL ROSAL | Cajibío | La Unión | 20/20 (100%) | 27/28 (96.4%) | 5/5 (100%) | ✅ Certificable |
| SANTA BÁRBARA | Cajibío | Cairo | 19/24 (79.2%) | 22/29 (75.9%) | 5/5 (100%) | 🔴 Aplazado |

**Hallazgos típicos identificados:** certificación de hatos libres (brucelosis/tuberculosis), instalaciones de ordeño, monitoreo de calidad del agua, manejo de residuos.

---

## 7. SEGURIDAD Y BUENAS PRÁCTICAS

- **Nunca se suben credenciales al repositorio** (archivos OAuth excluidos vía .gitignore)
- Las claves API viven en variables de entorno
- Tokens de Google auto-renovables
- El APK distribuido es versión debug; para distribución pública se requiere firma de release
- Copias de seguridad automáticas del sistema (`backup_bot.sh`, conserva las 5 más recientes)

---

## 8. BENEFICIOS Y APLICACIONES

1. **Para el productor:** autoevaluación clara de su estado frente a la normativa ICA, con plan de acción derivado de los hallazgos
2. **Para el asesor/auditor:** herramientas de campo sin dependencia de conectividad, consolidación automática, seguimiento de evolución entre auditorías
3. **Para cooperativas y plantas lácteas:** diagnóstico estandarizado de proveedores (licencias B2B)
4. **Escalable:** la misma plataforma puede extenderse a otras certificaciones pecuarias y regiones

---

## 9. TECNOLOGÍA

- **Backend:** Python 3 (estándar, sin dependencias externas), SQLite
- **Frontend móvil:** PWA (HTML/CSS/JavaScript) + Capacitor para APK Android
- **Automatización:** GitHub Actions (CI/CD del APK), cron jobs
- **Integraciones:** Google Sheets API, Telegram Bot API, GitHub API, UMap/OpenStreetMap
- **IA conversacional:** Hermes Agent (DeepSeek) para el bot de Telegram

---

*Documento generado para NotebookLM — fuente de referencia del Sistema Auditor BPG ICA.*
