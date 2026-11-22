
import time
import math
import pandas as pd

# CONSTANTES DEL CASO .
ESPACIO_MAX_CM = 1200
PRESUPUESTO_MAX_S = 30000.0
MIN_SKU_CATEGORIA = 2
BONO_VENTA_CRUZADA = 0.05
PRECIO_MIN_CAMPANIA = 5.0
PRECIO_MAX_CAMPANIA = 20.0


def medir_tiempo(funcion, *args, **kwargs):
    """Ejecuta una función y devuelve (resultado, tiempo en milisegundos)."""
    inicio = time.perf_counter()
    resultado = funcion(*args, **kwargs)
    fin = time.perf_counter()
    return resultado, (fin - inicio) * 1000


def normalizar_ids(ids):
    """Convierte una colección de IDs a un conjunto de enteros."""
    if ids is None:
        return set()
    return {int(x) for x in ids}


def calcular_metricas(skus, ids_seleccionados, clusters=None):
    """
    Calcula los indicadores de negocio para una selección de SKU

    Devuelve un diccionario con margen, espacio, inventario, categorías,
    bono y productos de campaña. Los nombres de columnas corresponden
    al archivo C3_skus.csv y al kit C3 del enunciado
    """
    requeridas = {
        "ID_SKU", "Categoria", "Precio_S", "Ventas_sem_u",
        "Frente_cm", "Inventario_S", "Margen_unit_S"
    }
    faltantes = requeridas - set(skus.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en skus: {sorted(faltantes)}")

    ids = normalizar_ids(ids_seleccionados)
    elegidos = skus[skus["ID_SKU"].astype(int).isin(ids)].copy()

    if elegidos.empty:
        margen = 0.0
        espacio = 0
        inventario = 0.0
        categorias = {}
    else:
        elegidos["Margen_semanal"] = (
            elegidos["Margen_unit_S"] * elegidos["Ventas_sem_u"]
        )
        margen = float(elegidos["Margen_semanal"].sum())
        espacio = int(elegidos["Frente_cm"].sum())
        inventario = float(elegidos["Inventario_S"].sum())
        categorias = (
            elegidos.groupby("Categoria")["ID_SKU"].count().astype(int).to_dict()
        )

    bono = calcular_bono(elegidos, clusters)
    campania = elegidos[
        elegidos["Precio_S"].between(PRECIO_MIN_CAMPANIA, PRECIO_MAX_CAMPANIA)
    ]["ID_SKU"].astype(int).tolist()

    return {
        "seleccionados": sorted(ids),
        "cantidad_sku": len(ids),
        "margen_base": margen,
        "bono_venta_cruzada": bono,
        "margen_total": margen + bono,
        "espacio_cm": espacio,
        "porcentaje_espacio": (espacio / ESPACIO_MAX_CM * 100),
        "inventario_s": inventario,
        "categorias": categorias,
        "categorias_cubiertas": len(categorias),
        "sku_campania": sorted(campania),
        "cumple_espacio": espacio <= ESPACIO_MAX_CM,
        "cumple_presupuesto": inventario <= PRESUPUESTO_MAX_S,
        "cumple_minimo_categoria": all(
            categorias.get(cat, 0) >= MIN_SKU_CATEGORIA
            for cat in skus["Categoria"].dropna().unique()
        ),
    }


def calcular_bono(elegidos, clusters):
    """Aplica +5% al margen de cada clúster con 3 o más SKU seleccionados."""
    if elegidos.empty or not clusters:
        return 0.0

    margen_por_id = {
        int(fila.ID_SKU): float(fila.Margen_unit_S * fila.Ventas_sem_u)
        for fila in elegidos.itertuples(index=False)
    }
    ids_elegidos = set(margen_por_id)
    bono = 0.0

    for cluster in clusters:
        ids_cluster = normalizar_ids(cluster)
        ids_comunes = ids_cluster & ids_elegidos
        if len(ids_comunes) >= 3:
            margen_cluster = sum(margen_por_id[x] for x in ids_comunes)
            bono += margen_cluster * BONO_VENTA_CRUZADA

    return bono


def analizar_complejidad():
   
    return [
        ("Medición de tiempos", "O(T)", "Depende del tiempo de la función medida"),
        ("Cálculo de métricas", "O(n + k)", "n SKU; k SKU seleccionados"),
        ("Agrupación/bono por clúster", "O(k + c)", "c = total de SKU recorridos en clústeres"),
        ("Comparación M3 vs M4", "O(1)", "Con métricas ya calculadas"),
    ]


def comparar_soluciones(skus, solucion_m3, solucion_m4, clusters=None):
    """Compara la solución de referencia M3 con la solución completa M4"""
    m3 = calcular_metricas(skus, solucion_m3, clusters)
    m4 = calcular_metricas(skus, solucion_m4, clusters)

    diferencia = m4["margen_total"] - m3["margen_total"]
    diferencia_pct = (
        (diferencia / m3["margen_total"]) * 100
        if m3["margen_total"] != 0 else 0.0
    )

    return {
        "M3": m3,
        "M4": m4,
        "diferencia_margen_s": diferencia,
        "diferencia_porcentual": diferencia_pct,
        "margen_dejado_de_ganar_s": max(0.0, m3["margen_base"] - m4["margen_base"]),
    }


def margen_por_categoria(skus):
    """Calcula margen semanal por centímetro para cada categoría"""
    datos = skus.copy()
    datos["Margen_semanal"] = datos["Margen_unit_S"] * datos["Ventas_sem_u"]
    resumen = datos.groupby("Categoria").agg(
        margen_semanal=("Margen_semanal", "sum"),
        frente_total_cm=("Frente_cm", "sum")
    )
    resumen["margen_por_cm"] = (
        resumen["margen_semanal"] / resumen["frente_total_cm"]
    )
    return resumen.sort_values("margen_por_cm", ascending=False)


def mostrar_resumen(comparacion):
    """Imprime la tabla de indicadores M3 vs M4 y las respuestas G1-G6."""
    m3 = comparacion["M3"]
    m4 = comparacion["M4"]

    print("\n" + "=" * 76)
    print("C3 MERCABARRIO - S8. COMPARACIÓN Y DECISIÓN (MÓDULO 5)")
    print("=" * 76)
    print(f"{'Indicador':32s} {'M3 mochila':>18s} {'M4 AG':>18s}")
    print("-" * 76)
    filas = [
        ("Margen semanal + bono (S/)", "margen_total"),
        ("Espacio utilizado (cm)", "espacio_cm"),
        ("Inventario (S/)", "inventario_s"),
        ("SKU seleccionados", "cantidad_sku"),
        ("Categorías cubiertas", "categorias_cubiertas"),
    ]
    for etiqueta, clave in filas:
        print(f"{etiqueta:32s} {m3[clave]:18,.2f} {m4[clave]:18,.2f}")

    print("-" * 76)
    print(f"Diferencia de margen: S/ {comparacion['diferencia_margen_s']:,.2f}")
    print(f"Diferencia porcentual: {comparacion['diferencia_porcentual']:.2f}%")
    print("\nRESPUESTAS A GERENCIA:")
    print(f"G1. SKU seleccionados por M4: {m4['cantidad_sku']}; margen semanal total: S/ {m4['margen_total']:,.2f}.")
    print(f"G3. Diferencia de margen base M3-M4: S/ {comparacion['margen_dejado_de_ganar_s']:,.2f}.")
    print(f"G5. Aporte del bono de venta cruzada: S/ {m4['bono_venta_cruzada']:,.2f}.")
    print(f"G6. SKU de campaña (S/ 5 a S/ 20) seleccionados: {len(m4['sku_campania'])}.")
    print("G2. Revisar clústeres mostrados por M2 para identificar productos afines.")
    print("G4. Revisar el ranking de margen por centímetro mostrado por M5.")
    print("=" * 76)


def guardar_grafico_escalabilidad(tamanos, tiempos_ms, ruta_salida):

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Aviso: matplotlib no está instalado; no se generó el gráfico.")
        return False

    if len(tamanos) != len(tiempos_ms) or len(tamanos) < 2:
        raise ValueError("Se requieren al menos dos pares de tamaño/tiempo.")

    base_n = tamanos[0]
    base_t = max(tiempos_ms[0], 0.001)
    teorica = [
        base_t * ((n * math.log2(max(n, 2))) /
                  (base_n * math.log2(max(base_n, 2))))
        for n in tamanos
    ]

    plt.figure()
    plt.plot(tamanos, tiempos_ms, marker="o", label="Tiempo medido")
    plt.plot(tamanos, teorica, linestyle="--", label="Referencia O(n log n)")
    plt.xlabel("Tamaño de entrada (n)")
    plt.ylabel("Tiempo (ms)")
    plt.title("Escalabilidad - C3 MercaBarrio")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(ruta_salida)
    plt.close()
    return True
