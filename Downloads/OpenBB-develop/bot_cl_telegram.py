import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask

# ==========================================
# 1. SERVIDOR FLASK (Para mantener Render despierto 24/7)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Multi-Mercado Unificado (ES, NQ, CL) Activo en Render", 200

def ejecutar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. CONFIGURACIÓN Y CREDENCIALES
# ==========================================
INTERVALO = "5m"
TEMPORALIDAD_DATOS = "5d"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8904618394:AAHovRZSl_UdzLrgZ9ifCWNEksp5yMtHrew")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1881139096")

def enviar_mensaje_telegram(mensaje: str):
    """Envía alertas directamente a Telegram."""
    if not TELEGRAM_BOT_TOKEN:
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

# ==========================================
# 3. ESTRATEGIA 1: ES y NQ (Cruces de EMA 200)
# ==========================================
def analizar_es_nq(ticker: str):
    nombre_activo = "S&P 500 (ES)" if ticker == "ES=F" else "NASDAQ (NQ)"
    print(f"Analizando {nombre_activo} (EMA 200)...")
    
    df = yf.download(tickers=ticker, period=TEMPORALIDAD_DATOS, interval=INTERVALO, progress=False)
    if df.empty or len(df) < 200:
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    precio_cierre_anterior = float(df['Close'].iloc[-3])
    ema_anterior = float(df['EMA_200'].iloc[-3])

    precio_cierre_actual = float(df['Close'].iloc[-2])
    ema_actual = float(df['EMA_200'].iloc[-2])

    # Cruce Alcista
    if precio_cierre_anterior < ema_anterior and precio_cierre_actual > ema_actual:
        msg = (
            f"🚀 *¡CRUCE ALCISTA EMA 200 (COMPRA)!*\n\n"
            f"• *Activo:* {nombre_activo} (`{ticker}`)\n"
            f"• *Precio Cierre:* `${precio_cierre_actual:.2f}`\n"
            f"• *EMA 200:* `${ema_actual:.2f}`"
        )
        enviar_mensaje_telegram(msg)

    # Cruce Bajista
    elif precio_cierre_anterior > ema_anterior and precio_cierre_actual < ema_actual:
        msg = (
            f"🔻 *¡CRUCE BAJISTA EMA 200 (VENTA)!*\n\n"
            f"• *Activo:* {nombre_activo} (`{ticker}`)\n"
            f"• *Precio Cierre:* `${precio_cierre_actual:.2f}`\n"
            f"• *EMA 200:* `${ema_actual:.2f}`"
        )
        enviar_mensaje_telegram(msg)

# ==========================================
# 4. ESTRATEGIA 2: PETRÓLEO CL (Bollinger + RSI + EMA20 + ATR)
# ==========================================
def calcular_indicadores_cl(df: pd.DataFrame) -> pd.DataFrame:
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()

    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df['bbm'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['bbu'] = df['bbm'] + (std * 2.0)
    df['bbl'] = df['bbm'] - (std * 2.0)

    # ATR 14
    high_low = df['high'] - df['low']
    high_cp = (df['high'] - df['close'].shift()).abs()
    low_cp = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()

    return df

def analizar_cl():
    print("Analizando PETRÓLEO (CL) con estrategia de Bollinger + RSI...")
    df = yf.download(tickers="CL=F", period=TEMPORALIDAD_DATOS, interval=INTERVALO, progress=False)
    if df.empty or len(df) < 20:
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [col.lower() for col in df.columns]
    df = calcular_indicadores_cl(df)

    precio_actual = float(df['close'].iloc[-1])
    rsi_actual = float(df['rsi'].iloc[-1])
    ema_actual = float(df['ema20'].iloc[-1])
    atr_actual = float(df['atr'].iloc[-1])
    bb_lower = float(df['bbl'].iloc[-1])
    bb_middle = float(df['bbm'].iloc[-1])
    bb_upper = float(df['bbu'].iloc[-1])

    # Condición de COMPRA en CL
    if precio_actual <= bb_lower and rsi_actual < 32 and precio_actual > ema_actual:
        sl = precio_actual - (1.2 * atr_actual)
        tp = bb_middle
        msg = (
            f"🚀 *¡ALERTA DE COMPRA EN PETRÓLEO (CL - 5M)!*\n\n"
            f"• *Entrada:* `${precio_actual:.2f}`\n"
            f"• *Take Profit:* `${tp:.2f}`\n"
            f"• *Stop Loss:* `${sl:.2f}`\n"
            f"• *RSI:* `{rsi_actual:.2f}`\n"
            f"• *EMA 20:* `${ema_actual:.2f}`"
        )
        enviar_mensaje_telegram(msg)

    # Condición de VENTA en CL
    elif precio_actual >= bb_upper and rsi_actual > 68 and precio_actual < ema_actual:
        sl = precio_actual + (1.2 * atr_actual)
        tp = bb_middle
        msg = (
            f"🔻 *¡ALERTA VENTA PETRÓLEO (CL)!*\n\n"
            f"• *Entrada:* `${precio_actual:.2f}`\n"
            f"• *Take Profit:* `${tp:.2f}`\n"
            f"• *Stop Loss:* `${sl:.2f}`\n"
            f"• *RSI:* `{rsi_actual:.2f}`\n"
            f"• *EMA 20:* `${ema_actual:.2f}`"
        )
        enviar_mensaje_telegram(msg)

# ==========================================
# 5. BUCLE GENERAL DE MONITOREO
# ==========================================
def bucle_monitoreo():
    enviar_mensaje_telegram("🤖 *Bot Multi-Estrategia Iniciado en Render (ES/NQ: EMA200 | CL: Bollinger+RSI)*")
    while True:
        try:
            # 1. Ejecuta estrategia EMA 200 en ES y NQ
            analizar_es_nq("ES=F")
            analizar_es_nq("NQ=F")

            # 2. Ejecuta estrategia de Reversión en Petróleo (CL)
            analizar_cl()

            time.sleep(60) # Revisa cada minuto
        except Exception as e:
            print(f"Error en bucle de trading: {e}")
            time.sleep(30)

# ==========================================
# 6. INICIO EN PARALELO
# ==========================================
if __name__ == "__main__":
    hilo_bot = threading.Thread(target=bucle_monitoreo)
    hilo_bot.daemon = True
    hilo_bot.start()

    ejecutar_servidor_web()