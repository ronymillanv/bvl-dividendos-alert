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


def check_dividendos():
    estado_actual = load_state()
    nuevos = []

    response = requests.get(BVL_URL, timeout=30)
    response.encoding = "latin-1"
    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table")

    dividendos = []
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 9:
                empresa = cells[0].get_text(strip=True)
                fecha_junta = cells[1].get_text(strip=True)
                efec = cells[8].get_text(strip=True)
                if efec not in ["-.-", "", "-"] and empresa:
                    dividendos.append({
                        "empresa": empresa,
                        "fecha_junta": fecha_junta,
                        "monto": efec
                    })

    print(f"Total con dividendo en pagina: {len(dividendos)}")
    for d in dividendos:
        print(f"  {d['empresa']} | {d['fecha_junta']} | {d['monto']}")

    hoy = datetime.now().strftime("%d/%m/%Y")
    for d in dividendos:
        clave = f"{d['empresa']}|{d['fecha_junta']}"
        if clave not in estado_actual:
            nuevos.append(d)
            estado_actual[clave] = {**d, "detectado": hoy}

    if nuevos:
        for d in nuevos:
            msg = (
                f"<b>Nuevo dividendo BVL</b>\n"
                f"Detectado el {hoy}\n\n"
                f"<b>Empresa:</b> {d['empresa']}\n"
                f"<b>Fecha de junta:</b> {d['fecha_junta']}\n"
                f"<b>Dividendo:</b> {d['monto']}\n\n"
                f"Fuente: Bolsa de Valores de Lima"
            )
            send_telegram(msg)
        print(f"Enviadas {len(nuevos)} nuevas alertas.")
    else:
        print("No hay nuevos dividendos anunciados.")

    save_state(estado_actual)
    commit_state()


if __name__ == "__main__":
    check_dividendos()
