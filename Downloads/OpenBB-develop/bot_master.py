import time
import requests
import pandas as pd
import yfinance as yf

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
# Activos a monitorear (E-mini S&P 500 y E-mini Nasdaq)
TICKERS = ["ES=F", "NQ=F"]

# Periodo de tiempo y temporalidad de velas (ej. "1h", "4h", "1d")
INTERVALO = "4h"
TEMPORALIDAD_DATOS = "60d"

# Configuración del Bot de Telegram (Reemplaza con tus credenciales)
TELEGRAM_BOT_TOKEN = "8904618394:AAHovRZSl_UdzLrgZ9ifCWNEksp5yMtHrew"
TELEGRAM_CHAT_ID = "1881139096"

# ==========================================
# 2. FUNCIONES BÁSICAS
# ==========================================
def enviar_mensaje_telegram(mensaje: str):
    """Envía un mensaje de alerta a tu chat de Telegram."""
    if TELEGRAM_BOT_TOKEN == "TU_BOT_TOKEN_AQUI":
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
    precio_cierre_anterior = df['Close'].iloc[-3]
    ema_anterior = df['EMA_200'].iloc[-3]

    precio_cierre_actual = df['Close'].iloc[-2]
    ema_actual = df['EMA_200'].iloc[-2]

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

# ==========================================
# 3. BUCLE PRINCIPAL DE EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    enviar_mensaje_telegram("🤖 *Bot de Trading Iniciado Correctamente en VS Code*")
    
    # Bucle infinito para monitoreo periódico (ej. cada 15 minutos)
    SEGUNDOS_ESPERA = 900 
    
    while True:
        try:
            for ticker in TICKERS:
                analizar_cruce(ticker)
            print(f"Esperando {SEGUNDOS_ESPERA // 60} minutos para el siguiente análisis...\n")
            time.sleep(SEGUNDOS_ESPERA)
        except KeyboardInterrupt:
            print("\nBot detenido manualmente por el usuario.")
            break
        except Exception as e:
            print(f"Error inesperado en el ciclo: {e}")
            time.sleep(60)