import time
import requests
import yfinance as yf
import pandas as pd

# ==========================================
# CREDENCIALES DE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8904618394:AAHovRZSl_UdzLrgZ9ifCWNEksp5yMtHrew"
TELEGRAM_CHAT_ID = "1881139096"

def enviar_telegram(mensaje: str):
    """Envía una alerta directamente a tu Telegram."""
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

# Diccionario de activos a monitorear
ACTIVOS = {
    "ES=F": "S&P 500 Futures (ES)",
    "NQ=F": "Nasdaq Futures (NQ)"
}

def evaluar_cruce_ema200(ticker_symbol: str, nombre_activo: str):
    try:
        # Descargamos datos intradía de 5 minutos
        df = yf.download(tickers=ticker_symbol, period="5d", interval="5m", progress=False)
    except Exception as e:
        print(f"Error descargando datos para {ticker_symbol}: {e}")
        return

    if df.empty or len(df) < 201:
        print(f"[{ticker_symbol}] No hay suficientes datos para calcular la EMA 200.")
        return

    # Limpieza de nombres de columnas si vienen en MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]

    # Cálculo de la EMA 200
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # Precios y EMAs de la vela actual (iloc[-1]) y de la vela anterior (iloc[-2])
    precio_previo = float(df['close'].iloc[-2])
    ema_previa = float(df['ema200'].iloc[-2])

    precio_actual = float(df['close'].iloc[-1])
    ema_actual = float(df['ema200'].iloc[-1])

    hora_vela = df.index[-1]

    print(f"[{hora_vela}] {ticker_symbol} (5m) | Precio: ${precio_actual:.2f} | EMA200: ${ema_actual:.2f}")

    # ==========================================
    # DETECCIÓN DE CRUCES
    # ==========================================

    # 1. CRUCE ALCISTA (COMPRA)
    if precio_previo <= ema_previa and precio_actual > ema_actual:
        msg = (
            f"🚀 *¡ALERTA DE COMPRA - CRUCE EMA 200!*\n\n"
            f"• *Activo:* {nombre_activo} (`{ticker_symbol}`)\n"
            f"• *Temporalidad:* Vela de 5 Minutos\n"
            f"• *Acción Recomendada:* **COMPRAR (LONG)**\n\n"
            f"• *Precio de Cierre:* ${precio_actual:.2f}\n"
            f"• *Nivel EMA 200:* ${ema_actual:.2f}\n"
            f"• *Hora Vela:* `{hora_vela}`"
        )
        print(f"🔥 >>> CRUCE ALCISTA DETECTADO EN {ticker_symbol}! Enviando alerta...")
        enviar_telegram(msg)

    # 2. CRUCE BAJISTA (VENTA)
    elif precio_previo >= ema_previa and precio_actual < ema_actual:
        msg = (
            f"🔻 *¡ALERTA DE VENTA - CRUCE EMA 200!*\n\n"
            f"• *Activo:* {nombre_activo} (`{ticker_symbol}`)\n"
            f"• *Temporalidad:* Vela de 5 Minutos\n"
            f"• *Acción Recomendada:* **VENTAR (SHORT)**\n\n"
            f"• *Precio de Cierre:* ${precio_actual:.2f}\n"
            f"• *Nivel EMA 200:* ${ema_actual:.2f}\n"
            f"• *Hora Vela:* `{hora_vela}`"
        )
        print(f"🔥 >>> CRUCE BAJISTA DETECTADO EN {ticker_symbol}! Enviando alerta...")
        enviar_telegram(msg)

# ==========================================
# EJECUCIÓN CONTINUA CADA 5 MINUTOS
# ==========================================
if __name__ == "__main__":
    print("🤖 Bot de Monitoreo de EMA 200 (ES & NQ) Activado en VS Code.")
    print("Enviando mensaje de confirmación a Telegram...")

    enviar_telegram("🤖 *Bot ES / NQ (EMA 200 - 5M) Activado.*\nMonitoreando cruces de EMA 200 en tiempo real...")

    while True:
        for ticker, nombre in ACTIVOS.items():
            evaluar_cruce_ema200(ticker, nombre)
        
        # Espera 5 minutos (300 segundos) entre escaneos
        time.sleep(300)