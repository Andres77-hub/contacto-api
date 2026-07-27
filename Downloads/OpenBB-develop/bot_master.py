import os
import time
import threading
import requests
import yfinance as yf
import pandas as pd
from flask import Flask

# ==========================================
# SERVIDOR WEB PARA RENDER & UPTIMEROBOT
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Multi-Mercado (CL, ES, NQ) funcionando correctamente.", 200

def run_web_server():
    # Render asigna dinámicamente un puerto a través de la variable de entorno PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# CREDENCIALES DE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8904618394:AAHovRZSl_UdzLrgZ9ifCWNEksp5yMtHrew"
TELEGRAM_CHAT_ID = "1881139096"

def enviar_telegram(mensaje: str):
    """Envía un mensaje a Telegram directamente (sin proxies)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ Error enviando a Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Excepción al conectar con Telegram: {e}")

# ==========================================
# 1. ESTRATEGIA PETRÓLEO (CL)
# ==========================================
def analizar_cl():
    try:
        df = yf.download(tickers="CL=F", period="5d", interval="5m", progress=False)
        if df.empty: return

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [col.lower() for col in df.columns]

        # Indicadores
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        df['bbm'] = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        df['bbu'] = df['bbm'] + (std * 2.0)
        df['bbl'] = df['bbm'] - (std * 2.0)

        tr = pd.concat([
            df['high'] - df['low'], 
            (df['high'] - df['close'].shift()).abs(), 
            (df['low'] - df['close'].shift()).abs()
        ], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()

        precio = float(df['close'].iloc[-1])
        rsi = float(df['rsi'].iloc[-1])
        ema = float(df['ema20'].iloc[-1])
        atr = float(df['atr'].iloc[-1])
        bbl, bbm, bbu = float(df['bbl'].iloc[-1]), float(df['bbm'].iloc[-1]), float(df['bbu'].iloc[-1])

        hora = df.index[-1]
        print(f"[{hora}] [CL=F] Precio: ${precio:.2f} | RSI: {rsi:.1f}")

        # Compras / Ventas CL
        if precio <= bbl and rsi < 32 and precio > ema:
            msg = f"🚀 *¡ALERTA COMPRA PETRÓLEO (CL)!*\n\n• Entrada: ${precio:.2f}\n• TP: ${bbm:.2f}\n• SL: ${precio - (1.2 * atr):.2f}"
            enviar_telegram(msg)
        elif precio >= bbu and rsi > 68 and precio < ema:
            msg = f"🔻 *¡ALERTA VENTA PETRÓLEO (CL)!*\n\n• Entrada: ${precio:.2f}\n• TP: ${bbm:.2f}\n• SL: ${precio + (1.2 * atr):.2f}"
            enviar_telegram(msg)

    except Exception as e:
        print(f"Error evaluando CL: {e}")

# ==========================================
# 2. ESTRATEGIA FUTUROS ES & NQ (EMA 200)
# ==========================================
ACTIVOS_EMA = {"ES=F": "S&P 500 (ES)", "NQ=F": "Nasdaq (NQ)"}

def analizar_ema200(symbol: str, nombre: str):
    try:
        df = yf.download(tickers=symbol, period="5d", interval="5m", progress=False)
        if df.empty or len(df) < 201: return

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [col.lower() for col in df.columns]

        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

        precio_prev = float(df['close'].iloc[-2])
        ema_prev = float(df['ema200'].iloc[-2])
        precio_act = float(df['close'].iloc[-1])
        ema_act = float(df['ema200'].iloc[-1])
        hora = df.index[-1]

        print(f"[{hora}] [{symbol}] Precio: ${precio_act:.2f} | EMA200: ${ema_act:.2f}")

        # Cruce Alcista
        if precio_prev <= ema_prev and precio_act > ema_act:
            msg = (
                f"🚀 *¡CRUCE ALCISTA EMA 200 (COMPRA)!*\n\n"
                f"• *Activo:* {nombre} (`{symbol}`)\n"
                f"• *Precio Cierre:* ${precio_act:.2f}\n"
                f"• *EMA 200:* ${ema_act:.2f}"
            )
            enviar_telegram(msg)

        # Cruce Bajista
        elif precio_prev >= ema_prev and precio_act < ema_act:
            msg = (
                f"🔻 *¡CRUCE BAJISTA EMA 200 (VENTA)!*\n\n"
                f"• *Activo:* {nombre} (`{symbol}`)\n"
                f"• *Precio Cierre:* ${precio_act:.2f}\n"
                f"• *EMA 200:* ${ema_act:.2f}"
            )
            enviar_telegram(msg)

    except Exception as e:
        print(f"Error evaluando {symbol}: {e}")

# ==========================================
# BUCLE PRINCIPAL
# ==========================================
if __name__ == "__main__":
    # 1. Iniciar servidor Flask en segundo plano
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # 2. Notificación de inicio
    print("🤖 Bot Multi-Mercado Activado (CL, ES, NQ).")
    enviar_telegram("🤖 *Bot Multi-Mercado Activado en Render.*\nMonitoreando CL, ES y NQ cada 5 minutos...")

    # 3. Bucle de análisis continuo
    while True:
        # Evaluamos Petróleo
        analizar_cl()
        
        # Evaluamos ES y NQ
        for sym, nom in ACTIVOS_EMA.items():
            analizar_ema200(sym, nom)
            
        time.sleep(300)