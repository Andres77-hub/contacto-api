import os
import time
import requests
import yfinance as yf
import pandas as pd

# Configurar el proxy obligatorio de PythonAnywhere para cuentas gratuitas
os.environ['HTTP_PROXY'] = 'http://proxy.server:3128'
os.environ['HTTPS_PROXY'] = 'http://proxy.server:3128'

# ==========================================
# CREDENCIALES DE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8904618394:AAHovRZSl_UdzLrgZ9ifCWNEksp5yMtHrew"
TELEGRAM_CHAT_ID = "1881139096"

def enviar_telegram(mensaje: str):
    """Envía un mensaje usando el proxy de PythonAnywhere."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    proxies = {
        'http': 'http://proxy.server:3128',
        'https': 'http://proxy.server:3128',
    }
    try:
        response = requests.post(url, data=payload, proxies=proxies, timeout=10)
        if response.status_code != 200:
            print(f"❌ Error enviando a Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Excepción al conectar con Telegram: {e}")

# ==========================================
# CÁLCULO DE INDICADORES TÉCNICOS NATIVOS
# ==========================================
def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    # 1. EMA 20
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()

    # 2. RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # 3. Bollinger Bands (20, 2.0)
    df['bbm'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['bbu'] = df['bbm'] + (std * 2.0)
    df['bbl'] = df['bbm'] - (std * 2.0)

    # 4. ATR 14
    high_low = df['high'] - df['low']
    high_cp = (df['high'] - df['close'].shift()).abs()
    low_cp = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()

    return df

def analizar_y_notificar(symbol: str = "CL=F"):
    try:
        df = yf.download(tickers=symbol, period="5d", interval="5m", progress=False)
    except Exception as e:
        print(f"Error descargando datos: {e}")
        return

    if df.empty:
        print("No se recibieron datos de mercado.")
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [col.lower() for col in df.columns]

    df = calcular_indicadores(df)

    precio_actual = float(df['close'].iloc[-1])
    rsi_actual = float(df['rsi'].iloc[-1])
    ema_actual = float(df['ema20'].iloc[-1])
    atr_actual = float(df['atr'].iloc[-1])
    bb_lower = float(df['bbl'].iloc[-1])
    bb_middle = float(df['bbm'].iloc[-1])
    bb_upper = float(df['bbu'].iloc[-1])

    hora_actual = df.index[-1]
    print(f"[{hora_actual}] Evaluando 5m... Precio: ${precio_actual:.2f} | RSI: {rsi_actual:.1f} | EMA20: ${ema_actual:.2f}")

    # CONDICIÓN 1: COMPRA (LONG)
    if precio_actual <= bb_lower and rsi_actual < 32 and precio_actual > ema_actual:
        sl = precio_actual - (1.2 * atr_actual)
        tp = bb_middle
        msg = (
            f"🚀 *¡ALERTA DE COMPRA EN PETRÓLEO (CL - 5M)!*\n\n"
            f"• *Entrada:* ${precio_actual:.2f}\n"
            f"• *Take Profit:* ${tp:.2f}\n"
            f"• *Stop Loss:* ${sl:.2f}\n"
            f"• *RSI:* {rsi_actual:.2f}\n"
            f"• *EMA 20:* ${ema_actual:.2f}"
        )
        print(">>> Disparador alcanzado: Enviando señal de COMPRA a Telegram...")
        enviar_telegram(msg)

    # CONDICIÓN 2: VENTA (SHORT)
    elif precio_actual >= bb_upper and rsi_actual > 68 and precio_actual < ema_actual:
        sl = precio_actual + (1.2 * atr_actual)
        tp = bb_middle
        msg = (
            f"🔻 *¡ALERTA DE VENTA EN PETRÓLEO (CL - 5M)!*\n\n"
            f"• *Entrada:* ${precio_actual:.2f}\n"
            f"• *Take Profit:* ${tp:.2f}\n"
            f"• *Stop Loss:* ${sl:.2f}\n"
            f"• *RSI:* {rsi_actual:.2f}\n"
            f"• *EMA 20:* ${ema_actual:.2f}"
        )
        print(">>> Disparador alcanzado: Enviando señal de VENTA a Telegram...")
        enviar_telegram(msg)

# ==========================================
# BUCLE CONTINUO
# ==========================================
if __name__ == "__main__":
    print("🤖 Bot de Trading de Petróleo (CL) Activado.")
    print("Enviando mensaje de prueba a Telegram...")
    
    enviar_telegram("🤖 *Bot de Trading CL Activado en PythonAnywhere.*\nEscuchando el mercado cada 5 minutos...")
    
    while True:
        analizar_y_notificar()
        time.sleep(300)