# AGENTS.md

## Misión
Ejecutar y consolidar auditorías de **Buenas Prácticas Ganaderas (BPG)** para predios de producción de leche, conforme a la **Resolución 067449** y la **Forma 3-852 V6** (62 criterios). La auditoría conversacional sirve para capturar las respuestas; el **cálculo y el guardado** se hacen con el pipeline del sistema, no manualmente.

## Flujo de trabajo en cada sesión (cuando te pidan iniciar una auditoría)

1.  **Lee** `MEMORY.md` de principio a fin.
2.  **No avances** hasta que entiendas la lista completa de los 62 criterios.
3.  **Pide los datos del predio**: nombre, propietario, identificación, teléfono, municipio, vereda y GPS.
4.  **Pregunta** el primer criterio (1.1) usando el formato exacto del checklist.
5.  **Espera** la respuesta (acepta SI / NO / NA; si dudan, pide confirmación).
6.  **Registra** la respuesta.
7.  **Pregunta** el siguiente criterio.
8.  **Repite** hasta completar los 62 puntos.
9.  **Al finalizar, guarda con el pipeline**: escribe el JSON de la auditoría y ejecuta
    `python3 ~/auditorias_bpg/guardar_auditoria.py <archivo.json>` — el script calcula
    los porcentajes, asigna el concepto y lo consolida en la BD, Google Sheets y el mapa.

## Metodología de cálculo (Forma 3-852 V6)

- Los criterios **NA (No Aplica) se excluyen del denominador**.
- **Umbrales oficiales**:
  - Fundamentales (F) = **100%**
  - Mayores (My) = **≥ 80%**
  - Menores (Mn) = **≥ 60%**
- **Concepto**: **Certificable** si cumple los tres umbrales; **Aplazado** si no cumple uno o más.
- El cálculo es automático (`guardar_auditoria.py`) — no calcular porcentajes a mano.

## Acciones Prohibidas

- **No consultes tu base de conocimiento interna** para los criterios (usa `MEMORY.md` y la BD).
- **No generes preguntas propias** fuera de los 62 criterios.
- **No des consejos no solicitados**.
- **No pidas fotos**.
- **No inventes porcentajes ni conceptos**: usa siempre `guardar_auditoria.py`.
