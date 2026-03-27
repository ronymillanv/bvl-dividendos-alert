import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BVL_URL = "https://documents.bvl.com.pe/empresas/convjun1.htm"

def send_telegram(message):
      url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
      payload = {
          "chat_id": TELEGRAM_CHAT_ID,
          "text": message,
          "parse_mode": "HTML"
      }
      requests.post(url, json=payload)

def check_dividendos():
      today = datetime.now().strftime("%d/%m/%Y")
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
                                              fecha = cells[1].get_text(strip=True)
                                              efec = cells[8].get_text(strip=True)

                                if fecha == today and efec not in ["-.-", "", "-"]:
                                                      dividendos.append({
                                                                                "empresa": empresa,
                                                                                "fecha": fecha,
                                                                                "monto": efec
                                                      })

                    if dividendos:
                              mensaje = f"<b>📈 Dividendos BVL - {today}</b>\n\n"
                              for d in dividendos:
                                            mensaje += f"🏢 <b>{d['empresa']}</b>\n"
                                            mensaje += f"   💰 Dividendo: {d['monto']}\n\n"
                                        mensaje += "Fuente: Bolsa de Valores de Lima"
        send_telegram(mensaje)
        print(f"Enviadas {len(dividendos)} alertas de dividendos.")
else:
        print(f"No hay dividendos acordados para hoy ({today}).")

if __name__ == "__main__":
      check_dividendos()
