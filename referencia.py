import time
import pandas as pd

CAPACIDAD_GONDOLA_CM = 1200
PRESUPUESTO_S = 30000
MIN_SKU_POR_CATEGORIA = 2
NUM_CATEGORIAS = 8
BONO_CRUZADA = 0.05


def _normalizar_items(instancia):
    if isinstance(instancia, pd.DataFrame):
        df = instancia.copy()
        if "Margen_semanal" not in df.columns:
            df["Margen_semanal"] = df["Margen_unit_S"] * df["Ventas_sem_u"]
        return df.to_dict("records")
    items = []
    for fila in instancia:
        item = dict(fila)
        if "Margen_semanal" not in item:
            item["Margen_semanal"] = item["Margen_unit_S"] * item["Ventas_sem_u"]
        items.append(item)
    return items


def mochila_01(items, capacidad):
    n = len(items)
    dp = [[0] * (capacidad + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w = items[i - 1]["Frente_cm"]
        v = items[i - 1]["Margen_semanal"]
        for c in range(capacidad + 1):
            dp[i][c] = dp[i - 1][c]
            if w <= c:
                cand = dp[i - 1][c - w] + v
                if cand > dp[i][c]:
                    dp[i][c] = cand
    selected = []
    c = capacidad
    for i in range(n, 0, -1):
        if dp[i][c] != dp[i - 1][c]:
            selected.append(i - 1)
            c -= items[i - 1]["Frente_cm"]
    selected.reverse()
    return dp[n][capacidad], selected


def fuerza_bruta_mochila(items, capacidad):
    n = len(items)
    mejor = 0
    mejor_mask = 0
    for mask in range(1 << n):
        peso = 0
        valor = 0
        for i in range(n):
            if mask & (1 << i):
                peso += items[i]["Frente_cm"]
                valor += items[i]["Margen_semanal"]
        if peso <= capacidad and valor > mejor:
            mejor = valor
            mejor_mask = mask
    selected = [i for i in range(n) if mejor_mask & (1 << i)]
    return mejor, selected


def ejecutar_m3(instancia, semilla=None):
    items = _normalizar_items(instancia)
    t0 = time.perf_counter()
    valor, selected = mochila_01(items, CAPACIDAD_GONDOLA_CM)
    t1 = time.perf_counter()
    tiempo_ms = (t1 - t0) * 1000.0
    ids_seleccionados = [items[i]["ID_SKU"] for i in selected]

    print("=" * 80)
    print("C3 VENTAS - S6. SOLUCION DE REFERENCIA (M3)")
    print("=" * 80)
    print(f"Valor funcion objetivo (margen semanal): {valor:.2f}")
    print(f"SKU elegidos: {len(selected)}")
    print(f"IDs: {ids_seleccionados}")
    print(f"Tiempo (ms): {tiempo_ms:.3f}")

    return {
        "items": items,
        "selected": selected,
        "seleccionados": ids_seleccionados,
        "ids_seleccionados": ids_seleccionados,
        "value": valor,
        "time_ms": tiempo_ms,
    }


def procesar_m3(instancia, semilla=None):
    return ejecutar_m3(instancia, semilla)