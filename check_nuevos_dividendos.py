import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json
import subprocess

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BVL_URL = "https://documents.bvl.com.pe/empresas/convjun1.htm"
STATE_FILE = "dividendos_vistos.json"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

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

def check_nuevos():
    response = requests.get(BVL_URL, timeout=30)
    response.encoding = "latin-1"
    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table")
    estado_actual = load_state()
    nuevos = []

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 9:
                empresa = cells[0].get_text(strip=True)
                fecha_junta = cells[1].get_text(strip=True)
                efec = cells[8].get_text(strip=True)

                if not empresa or not fecha_junta:
                    continue

                if efec in ["-.-", "", "-"]:
                    continue

                clave = f"{empresa}|{fecha_junta}"

                if clave not in estado_actual:
                    nuevos.append({
                        "empresa": empresa,
                        "fecha_junta": fecha_junta,
                        "monto": efec
                    })
                    estado_actual[clave] = {
                        "empresa": empresa,
                        "fecha_junta": fecha_junta,
                        "monto": efec,
                        "detectado": datetime.now().strftime("%d/%m/%Y")
                    }

    if nuevos:
        hoy = datetime.now().strftime("%d/%m/%Y")
        mensaje = f"<b>Nuevo dividendo anunciado en BVL</b>\n"
        mensaje += f"Detectado el {hoy}\n\n"
        for d in nuevos:
            mensaje += f"<b>{d['empresa']}</b>\n"
            mensaje += f"   Fecha de junta: {d['fecha_junta']}\n"
            mensaje += f"   Dividendo: {d['monto']}\n\n"
        mensaje += "Fuente: Bolsa de Valores de Lima"
        send_telegram(mensaje)
        print(f"Enviadas {len(nuevos)} nuevas alertas.")
    else:
        print("No hay nuevos dividendos anunciados hoy.")

    save_state(estado_actual)
    commit_state()

if __name__ == "__main__":
    check_nuevos()
