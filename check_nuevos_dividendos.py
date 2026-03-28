import requests
from datetime import datetime
import os
import json
import subprocess
import re

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BVL_URL = "https://documents.bvl.com.pe/empresas/convjun1.htm"
STATE_FILE = "dividendos_vistos.json"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    r = requests.post(url, json=payload)
    print(f"Telegram: {r.status_code} - {r.text[:200]}")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def commit_state():
    subprocess.run(["git", "config", "user.email", "action@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "add", STATE_FILE], check=True)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", "Update dividendos vistos"], check=True)
        subprocess.run(["git", "push"], check=True)

def parse_dividendos():
    response = requests.get(BVL_URL, timeout=30)
    response.encoding = "latin-1"
    clean = re.sub(r'<[^>]+>', '', response.text)
    date_pat = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    amount_pat = re.compile(r'\d')
    dividendos = []
    for line in clean.splitlines():
        parts = [p.strip() for p in line.split('\t') if p.strip()]
        if len(parts) < 7:
            continue
        fecha_idx = next((i for i, p in enumerate(parts) if date_pat.match(p)), None)
        if fecha_idx is None or fecha_idx == 0:
            continue
        empresa = parts[0]
        efec = parts[-2]
        if efec in ["-.-", "-", ""] or not amount_pat.search(efec):
            continue
        dividendos.append({"empresa": empresa, "fecha_junta": parts[fecha_idx], "monto": efec})
    return dividendos

def check_nuevos():
    estado_actual = load_state()
    nuevos = []
    dividendos = parse_dividendos()
    print(f"Total con dividendo en pagina: {len(dividendos)}")
    for d in dividendos:
        print(f"  {d['empresa']} | {d['fecha_junta']} | {d['monto']}")
        clave = f"{d['empresa']}|{d['fecha_junta']}"
        if clave not in estado_actual:
            nuevos.append(d)
            estado_actual[clave] = {**d, "detectado": datetime.now().strftime("%d/%m/%Y")}
    if nuevos:
        hoy = datetime.now().strftime("%d/%m/%Y")
        for d in nuevos:
            msg = (
                f"Nuevo dividendo anunciado en BVL\n"
                f"Detectado el {hoy}\n\n"
                f"Empresa: {d['empresa']}\n"
                f"Fecha de junta: {d['fecha_junta']}\n"
                f"Dividendo: {d['monto']}\n\n"
                f"Fuente: Bolsa de Valores de Lima"
            )
            send_telegram(msg)
        print(f"Enviadas {len(nuevos)} nuevas alertas.")
    else:
        print("No hay nuevos dividendos anunciados.")
    save_state(estado_actual)
    commit_state()

if __name__ == "__main__":
    check_nuevos()
