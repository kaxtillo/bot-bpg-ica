#!/usr/bin/env python3
"""
Servidor API local para la app "Auditor BPG" — recibe auditorías del celular
y las consolida directo en la base de datos (sin archivos JSON intermedios).

Endpoints:
  GET  /api/health         → estado del servidor
  GET  /api/predios        → lista de predios registrados
  POST /api/auditorias     → recibe {predio, propietario, ..., detalle_puntos}
                             calcula, guarda y devuelve el reporte
  GET  /api/auditorias     → auditorías (resumen)

Uso:
  python3 servidor_api.py [puerto]          (por defecto 8200)
  # Desde el celular en la misma red wifi: http://IP_LAPTOP:8200
"""
import json
import os
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import date
from urllib.parse import urlparse

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")
GUARDAR = os.path.expanduser("~/auditorias_bpg/guardar_auditoria.py")
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8200

CAMPOS_PREDIO = ("predio", "propietario", "identificacion", "telefono", "email",
                 "departamento", "municipio", "vereda", "latitud", "longitud",
                 "rspp", "especie", "fin_zootecnico", "produccion", "total_animales")


def validar_payload(d):
    """Valida el payload de una auditoría. Devuelve (ok, error)."""
    if not isinstance(d, dict):
        return False, "el cuerpo debe ser un objeto JSON"
    predio = (d.get("predio") or "").strip()
    if not predio:
        return False, "falta el campo 'predio'"
    detalle = d.get("detalle_puntos")
    if not isinstance(detalle, dict) or not detalle:
        return False, "falta 'detalle_puntos' con las respuestas SI/NO/NA"
    invalidas = [k for k, v in detalle.items() if str(v).upper() not in ("SI", "NO", "NA")]
    if invalidas:
        return False, f"respuestas inválidas en: {', '.join(invalidas[:5])}"
    return True, None


class Handler(BaseHTTPRequestHandler):
    def _json(self, codigo, data):
        cuerpo = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self._json(204, {})

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/health":
            self._json(200, {"ok": True, "servicio": "Auditor BPG API", "fecha": date.today().isoformat()})
        elif ruta == "/api/predios":
            con = sqlite3.connect(DB)
            predios = [{"nombre": r[0], "propietario": r[1], "municipio": r[2]}
                       for r in con.execute("SELECT nombre, propietario, municipio FROM predios ORDER BY nombre")]
            con.close()
            self._json(200, {"predios": predios})
        elif ruta == "/api/auditorias":
            con = sqlite3.connect(DB)
            filas = con.execute(
                """SELECT a.id, p.nombre, a.fecha, a.concepto, a.f_pct, a.my_pct, a.mn_pct
                   FROM auditorias a JOIN predios p ON p.id=a.predio_id ORDER BY a.fecha DESC LIMIT 50"""
            ).fetchall()
            con.close()
            self._json(200, {"auditorias": [
                {"id": f[0], "predio": f[1], "fecha": f[2], "concepto": f[3],
                 "F": f[4], "My": f[5], "Mn": f[6]} for f in filas]})
        else:
            self._json(404, {"error": "ruta no encontrada"})

    def do_POST(self):
        ruta = urlparse(self.path).path
        if ruta != "/api/auditorias":
            self._json(404, {"error": "ruta no encontrada"})
            return
        try:
            largo = int(self.headers.get("Content-Length", 0))
            if largo <= 0 or largo > 2_000_000:
                self._json(400, {"error": "cuerpo vacío o demasiado grande"})
                return
            payload = json.loads(self.rfile.read(largo).decode("utf-8"))
        except Exception as e:
            self._json(400, {"error": f"JSON inválido: {e}"})
            return

        ok, err = validar_payload(payload)
        if not ok:
            self._json(400, {"error": err})
            return

        # normalizar: latitud/longitud sueltas si viene "gps"
        if payload.get("gps") and not payload.get("latitud"):
            try:
                lat, lon = payload["gps"].replace(" ", "").split(",")
                payload["latitud"], payload["longitud"] = float(lat), float(lon)
            except Exception:
                pass
        payload.setdefault("fecha", date.today().isoformat())
        payload.setdefault("departamento", "Cauca")

        # guardar con el pipeline oficial (cálculo + BD)
        tmp = "/tmp/auditoria_api.json"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        r = subprocess.run([sys.executable, GUARDAR, tmp], capture_output=True, text=True)
        if r.returncode != 0:
            self._json(500, {"error": "no se pudo guardar", "detalle": r.stderr[-300:]})
            return
        # extraer el id de auditoría del reporte
        import re
        m = re.search(r"auditoría #(\d+)", r.stdout)
        self._json(201, {
            "ok": True,
            "auditoria_id": int(m.group(1)) if m else None,
            "reporte": r.stdout.strip().splitlines()[-8:],
        })


def main():
    try:
        servidor = ThreadingHTTPServer(("0.0.0.0", PUERTO), Handler)
    except OSError as e:
        print(f"❌ No se pudo abrir el puerto {PUERTO}: {e}")
        sys.exit(1)
    print("═" * 50)
    print("  🌐 Servidor API Auditor BPG")
    print(f"  Puerto: {PUERTO}  (0.0.0.0 — accesible en la red local)")
    print("  Endpoints: /api/health · /api/predios · POST /api/auditorias")
    print("═" * 50)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Servidor detenido.")


if __name__ == "__main__":
    main()
