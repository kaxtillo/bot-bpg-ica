import httpx, json, sys, time, subprocess, os, signal

# Iniciar servidor notebooklm-mcp en background
proc = subprocess.Popen(
    ["notebooklm-mcp", "--transport", "http", "--port", "8765", "--stateless"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
time.sleep(3)

# Verificar que el servidor está corriendo
poll = proc.poll()
if poll is not None:
    print("Error: servidor no inició")
    stdout, stderr = proc.communicate()
    print(stderr.decode())
    sys.exit(1)

print("Servidor NotebookLM MCP iniciado en puerto 8765")

try:
    # Obtener lista de herramientas disponibles
    r = httpx.post("http://127.0.0.1:8765/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }, timeout=10)
    print("\n=== HERRAMIENTAS DISPONIBLES ===")
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    if r.status_code != 200:
        print(f"Error HTTP: {r.status_code}")
        print(r.text)
except Exception as e:
    print(f"Error: {e}")

# Intentar listar cuadernos
try:
    r = httpx.post("http://127.0.0.1:8765/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "list_notebooks",
            "arguments": {}
        }
    }, timeout=15)
    print("\n=== CUADERNOS RECIENTES ===")
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error listing notebooks: {e}")

# Detener servidor
proc.kill()
print("\nServidor detenido")
