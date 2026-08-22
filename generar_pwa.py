#!/usr/bin/env python3
"""Genera iconos PNG (192/512) y embebe los 62 criterios en app/index.html."""
import json
import os
import sqlite3
import struct
import zlib

APP = os.path.expanduser("~/auditorias_bpg/app")

# 1) Embeber criterios
con = sqlite3.connect(os.path.expanduser("~/auditorias_bpg/auditorias_bpg.db"))
crit = con.execute(
    """SELECT id, nombre, tipo, articulo, pregunta FROM criterios
       ORDER BY CAST(substr(id,1,instr(id,'.')-1) AS INT), CAST(substr(id,instr(id,'.')+1) AS INT)"""
).fetchall()
con.close()
criterios = [{"id": c[0], "nombre": c[1], "tipo": c[2], "articulo": c[3], "pregunta": c[4]} for c in crit]
print(f"Criterios leidos: {len(criterios)}")

html_path = os.path.join(APP, "index.html")
html = open(html_path, encoding="utf-8").read()
html = html.replace("__CRITERIOS__", json.dumps(criterios, ensure_ascii=False))
open(html_path, "w", encoding="utf-8").write(html)
print("OK index.html con criterios embebidos")


def crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def chunk(tipo, data):
    return struct.pack(">I", len(data)) + tipo + data + struct.pack(">I", crc32(tipo + data))


def hacer_icono(path, size):
    def px(x, y):
        cx, cy = size / 2.0, size / 2.0
        d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        if d > size * 0.46:
            return (11, 61, 46, 255)
        return (201, 162, 39, 255)
    rows = b""
    for y in range(size):
        row = b"\x00"
        for x in range(size):
            row += bytes(px(x, y))
        rows += row
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(rows))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print(f"OK {path} ({size}x{size})")


hacer_icono(os.path.join(APP, "icon-192.png"), 192)
hacer_icono(os.path.join(APP, "icon-512.png"), 512)
print("Listo.")
