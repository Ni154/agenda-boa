import os, sys, pathlib, importlib.util
import uvicorn

HERE = pathlib.Path(__file__).resolve().parent
print(f"[run.py] CWD={os.getcwd()} | FILEDIR={HERE}")
print(f"[run.py] LIST HERE={list(HERE.iterdir())}")

server_path = HERE / "backend" / "server.py"
if not server_path.exists():
    server_path = (HERE.parent / "backend" / "server.py")
    print(f"[run.py] Trying parent: {server_path}")

if not server_path.exists():
    raise FileNotFoundError(f"Não achei backend/server.py em {HERE} nem no pai. Conteúdo: {list(HERE.iterdir())}")

spec = importlib.util.spec_from_file_location("server", str(server_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

try:
    app = getattr(module, "app")
except AttributeError as e:
    raise RuntimeError("Arquivo backend/server.py não expõe 'app' (FastAPI).") from e

port = int(os.environ.get("PORT", "8000"))
print(f"[run.py] Iniciando Uvicorn na porta {port}...")
uvicorn.run(app, host="0.0.0.0", port=port)
