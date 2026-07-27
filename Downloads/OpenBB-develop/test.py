# from openbb import obb

# # Ejemplo: Obtener datos de precios históricos de una acción (ej. Apple)
# data = obb.equity.price.historical(symbol="AAPL", provider="yfinance")

# # Convertir los resultados a un DataFrame de pandas para analizarlos
# df = data.to_df()

# print(df.head())

# from openbb import obb

# # Obtener opciones para una acción (ej. AAPL)
# options = obb.derivatives.options.chains(symbol="AAPL", provider="yfinance")
# df_options = options.to_df()

# print(df_options.head())

# Obtener datos de un índice o ETF (ej. SPY)
# from openbb import obb
# spy_data = obb.equity.price.historical(symbol="SPY", provider="yfinance")
# print(spy_data.to_df().tail())

# 

from openbb import obb
import pandas as pd

def analizar_petroleo_cl_5m(symbol: str = "CL=F"):
    print(f"--- Analizando Futuro CL (Petróleo) en Marco de 5 Minutos ---")
    
    # 1. Obtener datos intradía de 5 minutos
    try:
        data = obb.equity.price.historical(
            symbol=symbol, 
            provider="yfinance", 
            interval="5m"
        ).to_df()
    except Exception as e:
        print(f"Error al descargar datos de 5m: {e}")
        return

    if data.empty:
        print("No se obtuvieron datos intradía.")
        return

    close_prices = data["close"]
    
    # 2. Indicadores
    rsi_df = obb.technical.rsi(data=close_prices, target="close", length=14).to_df()
    ema_df = obb.technical.ema(data=close_prices, target="close", length=20).to_df()
    bb_df = obb.technical.bbands(data=close_prices, target="close", length=20, std=2.0).to_df()
    atr_df = obb.technical.atr(data=data, length=14).to_df()

    # 3. Extraer valores flotantes limpios para la última vela de 5m
    precio_actual = float(close_prices.iloc[-1])
    rsi_actual = float(rsi_df.iloc[-1].values[0]) if isinstance(rsi_df.iloc[-1], pd.Series) else float(rsi_df.iloc[-1])
    ema_actual = float(ema_df.iloc[-1].values[0]) if isinstance(ema_df.iloc[-1], pd.Series) else float(ema_df.iloc[-1])
    atr_actual = float(atr_df.iloc[-1].values[0]) if isinstance(atr_df.iloc[-1], pd.Series) else float(atr_df.iloc[-1])
    
    # Extraer columnas específicas de Bollinger
    bb_lower = float(bb_df["close_BBL_20_2.0"].iloc[-1])
    bb_middle = float(bb_df["close_BBM_20_2.0"].iloc[-1])
    bb_upper = float(bb_df["close_BBU_20_2.0"].iloc[-1])

    # 4. Imprimir métricas
    print(f"\n[ÚLTIMA VELA 5M]")
    print(f"Precio Actual:         ${precio_actual:.2f}")
    print(f"EMA 20 (Sesgo 5m):     ${ema_actual:.2f}")
    print(f"RSI (14):              {rsi_actual:.2f}")
    print(f"Bollinger Superior:    ${bb_upper:.2f}")
    print(f"Bollinger Inferior:    ${bb_lower:.2f}")
    print(f"ATR 5m (Riesgo vela):  ${atr_actual:.2f}\n")

    # 5. Lógica de Entrada / Salida Intradía
    if precio_actual <= bb_lower and rsi_actual < 32 and precio_actual > ema_actual:
        sl = precio_actual - (1.2 * atr_actual)
        tp = bb_middle
        print("🚀 ¡SEÑAL DE COMPRA RÁPIDA (LONG 5M)!")
        print(f"-> Entrada:    ${precio_actual:.2f}")
        print(f"-> Take Profit: ${tp:.2f} (Banda Media)")
        print(f"-> Stop Loss:   ${sl:.2f} (1.2x ATR)")

    elif precio_actual >= bb_upper and rsi_actual > 68 and precio_actual < ema_actual:
        sl = precio_actual + (1.2 * atr_actual)
        tp = bb_middle
        print("🔻 ¡SEÑAL DE VENTA RÁPIDA (SHORT 5M)!")
        print(f"-> Entrada:    ${precio_actual:.2f}")
        print(f"-> Take Profit: ${tp:.2f} (Banda Media)")
        print(f"-> Stop Loss:   ${sl:.2f} (1.2x ATR)")
    else:
        print("⏳ Estado: Sin disparador en la vela actual de 5m.")

if __name__ == "__main__":
    analizar_petroleo_cl_5m()