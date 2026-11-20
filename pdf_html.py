#!/usr/bin/env python3
"""
pdf_html.py — Renderiza HTML a PDF con el primer motor disponible.

Orden: WeasyPrint (Python, sin navegador) → chromium → brave.
Motivo: el sistema cambió de herramientas (chromium desapareció de /usr/bin y el
modo headless de Brave falla por el sandbox), así que los scripts no deben depender
de un binario concreto. WeasyPrint es el más estable aquí: puro Python + pango/cairo.

Uso:
    from pdf_html import html_a_pdf
    ok, motor = html_a_pdf(html, "/ruta/salida.pdf")
"""
import os
import subprocess
import tempfile

NAVEGADORES = ["chromium", "chromium-browser", "brave", "google-chrome-stable", "/usr/sbin/brave"]


def _weasyprint(html, salida):
    try:
        from weasyprint import HTML
    except ImportError:
        return False
    try:
        HTML(string=html).write_pdf(salida)
        return os.path.exists(salida) and os.path.getsize(salida) > 0
    except Exception:
        return False


def _navegador(html, salida):
    perfil = os.path.join(tempfile.gettempdir(), "pdf-html-profile")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        ruta = f.name
    try:
        for exe in NAVEGADORES:
            if os.path.sep in exe and not os.path.exists(exe):
                continue
            for flag in ("--headless=new", "--headless"):
                try:
                    subprocess.run([exe, flag, "--no-sandbox", "--disable-gpu", "--no-first-run",
                                    "--disable-extensions", "--user-data-dir=" + perfil,
                                    "--no-pdf-header-footer", "--virtual-time-budget=5000",
                                    "--print-to-pdf=" + salida, "file://" + ruta],
                                   capture_output=True, text=True, timeout=120)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
                if os.path.exists(salida) and os.path.getsize(salida) > 0:
                    return True
        return False
    finally:
        try:
            os.unlink(ruta)
        except OSError:
            pass


def html_a_pdf(html, salida):
    """Devuelve (ok, nombre_del_motor)."""
    os.makedirs(os.path.dirname(os.path.abspath(salida)) or ".", exist_ok=True)
    if os.path.exists(salida):
        os.unlink(salida)
    if _weasyprint(html, salida):
        return True, "weasyprint"
    if _navegador(html, salida):
        return True, "navegador"
    return False, "ninguno"
