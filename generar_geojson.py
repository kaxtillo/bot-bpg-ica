#!/usr/bin/env python3
"""
Genera predios_bpg_ica.geojson desde la base de consolidación de auditorías
BPG ICA. El GeoJSON alimenta un mapa UMap con datos remotos (auto-refresh).

Uso: python3 generar_geojson.py [ruta_salida]
Por defecto escribe en ~/auditorias_bpg/predios_bpg_ica.geojson
"""
import json
import os
import sqlite3
import sys

DB = os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db")
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/auditorias_bpg/predios_bpg_ica.geojson"
)

QUERY = """
    SELECT p.nombre, p.propietario, p.municipio, p.vereda, p.latitud, p.longitud,
           a.fecha, a.concepto, a.f_pct, a.my_pct, a.mn_pct,
           (SELECT group_concat(r.criterio_id || ' ' || c.nombre, '; ')
              FROM respuestas r JOIN criterios c ON c.id=r.criterio_id
              WHERE r.auditoria_id=a.id AND r.respuesta='NO') AS hallazgos
    FROM predios p
    LEFT JOIN auditorias a ON a.id = (SELECT id FROM auditorias
        WHERE predio_id=p.id ORDER BY fecha DESC, id DESC LIMIT 1)
    ORDER BY p.nombre
"""

COLOR = {"Certificable": "#2e7d32", "Aplazado": "#c62828"}


def main():
    con = sqlite3.connect(DB)
    features = []
    for nombre, prop, muni, vereda, lat, lon, fecha, concepto, fp, mp, mnp, hallazgos in con.execute(QUERY):
        if lat is None or lon is None:
            continue
        color = COLOR.get(concepto or "", "#1565c0")
        desc = (
            f"<b>{nombre}</b><br/>"
            f"Propietario: {prop or '—'}<br/>"
            f"{muni or '—'} · Vereda {vereda or '—'}<br/>"
            f"<b style='color:{color}'>{concepto or '—'}</b> ({fecha or '—'})<br/>"
            f"F {fp}% · My {mp}% · Mn {mnp}%"
        )
        if hallazgos:
            desc += f"<br/><i>Hallazgos: {hallazgos}</i>"
        features.append({
            "type": "Feature",
            "properties": {
                "nombre": nombre,
                "propietario": prop or "",
                "municipio": muni or "",
                "vereda": vereda or "",
                "auditoria": fecha or "",
                "concepto": concepto or "",
                "F": f"{fp}%" if fp is not None else "",
                "My": f"{mp}%" if mp is not None else "",
                "Mn": f"{mnp}%" if mnp is not None else "",
                "hallazgos": hallazgos or "",
                "marker-color": color,
                "description": desc,
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })
    con.close()

    geojson = {
        "type": "FeatureCollection",
        "name": "Predios BPG ICA - Cauca",
        "features": features,
    }
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"✅ GeoJSON actualizado: {SALIDA} ({len(features)} predios)")


if __name__ == "__main__":
    main()
