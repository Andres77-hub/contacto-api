import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask

# ==========================================
# 1. SERVIDOR FLASK (Para Render / Health Check)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot de Trading Activo 24/7 en Render", 200

def ejecutar_servidor_web():
    # Render asigna dinámicamente un puerto en la variable PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. CONFIGURACIÓN INICIAL Y CREDENCIALES
# ==========================================
TICKERS = ["ES=F", "NQ=F"]
INTERVALO = "4h"
TEMPORALIDAD_DATOS = "60d"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8904618394:AAHovRZSl_UdzLrgZ9ifCWNEksp5yMtHrew")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1881139096")

# ==========================================
# 3. FUNCIONES BÁSICAS DE TRADING
# ==========================================
def enviar_mensaje_telegram(mensaje: str):
    """Envía un mensaje de alerta a tu chat de Telegram."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "TU_BOT_TOKEN_AQUI":
        print(f"[ALERTA LOCAL]: {mensaje}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

def calcular_ema_200(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula la EMA de 200 periodos sobre el precio de cierre."""
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

def analizar_cruce(ticker: str):
    """Obtiene datos del activo y evalúa si hubo cruce con la EMA 200."""
    print(f"Analizando {ticker}...")
    df = yf.download(tickers=ticker, period=TEMPORALIDAD_DATOS, interval=INTERVALO, progress=False)
    
    if df.empty or len(df) < 200:
        print(f"Insuficientes datos para calcular EMA 200 en {ticker}.")
        return

    df = calcular_ema_200(df)

    # Última vela cerrada (penúltimo registro) y la anterior
    precio_cierre_anterior = float(df['Close'].iloc[-3])
    ema_anterior = float(df['EMA_200'].iloc[-3])

    precio_cierre_actual = float(df['Close'].iloc[-2])
    ema_actual = float(df['EMA_200'].iloc[-2])

    # Detección de Cruce Alcista (Cierre cruza de abajo hacia arriba)
    if precio_cierre_anterior < ema_anterior and precio_cierre_actual > ema_actual:
        mensaje = (
            f"🚀 *ALERTA ALCISTA EN {ticker}*\n\n"
            f"El precio ha cruzado por **ENCIMA** de la EMA 200 ({INTERVALO}).\n"
            f"• Precio Cierre: `{precio_cierre_actual:.2f}`\n"
            f"• EMA 200: `{ema_actual:.2f}`"
        )
        enviar_mensaje_telegram(mensaje)

    # Detección de Cruce Bajista (Cierre cruza de arriba hacia abajo)
    elif precio_cierre_anterior > ema_anterior and precio_cierre_actual < ema_actual:
        mensaje = (
            f"🔻 *ALERTA BAJISTA EN {ticker}*\n\n"
            f"El precio ha cruzado por **DEBAJO** de la EMA 200 ({INTERVALO}).\n"
            f"• Precio Cierre: `{precio_cierre_actual:.2f}`\n"
            f"• EMA 200: `{ema_actual:.2f}`"
        )
        enviar_mensaje_telegram(mensaje)
    else:
        print(f"Sin cruce en {ticker}. Precio: {precio_cierre_actual:.2f} | EMA 200: {ema_actual:.2f}")

def bucle_monitoreo():
    """Bucle infinito que ejecuta el análisis de trading cada 15 min."""
    enviar_mensaje_telegram("🤖 *Bot de Trading Iniciado Correctamente con Servidor Web*")
    SEGUNDOS_ESPERA = 900 
    
    while True:
        try:
            for ticker in TICKERS:
                analizar_cruce(ticker)
            print(f"Esperando {SEGUNDOS_ESPERA // 60} minutos para el siguiente análisis...\n")
            time.sleep(SEGUNDOS_ESPERA)
        except Exception as e:
            print(f"Error inesperado en el ciclo: {e}")
            time.sleep(60)

# ==========================================
# 4. EJECUCIÓN EN PARALELO
# ==========================================
if __name__ == "__main__":
    # Lanza el bot de trading en un hilo en segundo plano (daemon thread)
    hilo_bot = threading.Thread(target=bucle_monitoreo)
    hilo_bot.daemon = True
    hilo_bot.start()

    # Ejecuta el servidor Flask en el hilo principal (lo que busca Render)
    ejecutar_servidor_web()