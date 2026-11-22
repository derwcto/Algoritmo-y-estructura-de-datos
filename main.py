
from pathlib import Path
from datetime import datetime
import importlib
import sys
import time
import pandas as pd

from analisis import (
    medir_tiempo, comparar_soluciones, mostrar_resumen,
    margen_por_categoria, analizar_complejidad,
    guardar_grafico_escalabilidad
)

#CONSTANTES DEL PROYECTO 
CASO = "C3"
EMPRESA = "MercaBarrio"
GRUPO = "[COMPLETAR]"
SEMILLA_ASIGNADA = 2613  # Reemplazar por la semilla oficial
CARPETA_RESULTADOS = Path("resultados")
ARCHIVO_SKUS = Path("C3_skus.csv")
ARCHIVO_TICKETS = Path("C3_tickets.csv")


FUNCIONES_MODULOS = {
    "estructuras": "ejecutar_m1",
    "red": "ejecutar_m2",
    "referencia": "ejecutar_m3",
    "metaheuristica": "ejecutar_m4",
}


def titulo(texto):
    print("\n" + "=" * 76)
    print(texto)
    print("=" * 76)


def pedir_semilla():
    """Solicita una semilla positiva; Enter utiliza la semilla asignada."""
    while True:
        texto = input(
            f"Ingrese la semilla (Enter = {SEMILLA_ASIGNADA}): "
        ).strip()
        if texto == "":
            return SEMILLA_ASIGNADA
        if texto.isdigit() and int(texto) > 0:
            return int(texto)
        print("La semilla debe ser un entero positivo. Intente nuevamente.")


def cargar_datos(semilla):
    """
    Prioriza el kit oficial datos.py. Si no está disponible, usa los CSV
    entregados para este trabajo. En ambos casos devuelve (skus, tickets).
    """
    try:
        datos = importlib.import_module("datos")
        generador = getattr(datos, "generar_datos_c3")
        skus, tickets = generador(semilla)
        print("Origen de datos: kit oficial generar_datos_c3(semilla).")
        return skus, tickets
    except (ImportError, AttributeError):
        if not ARCHIVO_SKUS.exists() or not ARCHIVO_TICKETS.exists():
            raise FileNotFoundError(
                "No se encontró datos.py con generar_datos_c3 ni los CSV "
                "C3_skus.csv y C3_tickets.csv."
            )

        skus = pd.read_csv(ARCHIVO_SKUS)
        tabla_tickets = pd.read_csv(ARCHIVO_TICKETS)
        # El CSV contiene una fila por producto y un id_ticket por compra
        tickets = (
            tabla_tickets.groupby("id_ticket")["ID_SKU"]
            .apply(lambda serie: [int(x) for x in serie.tolist()])
            .tolist()
        )
        print("Origen de datos: archivos CSV proporcionados.")
        print("Aviso: con CSV, la semilla no modifica los datos.")
        return skus, tickets


def validar_datos(skus, tickets):
    columnas = {
        "ID_SKU", "Categoria", "Precio_S", "Ventas_sem_u",
        "Frente_cm", "Inventario_S", "Margen_unit_S"
    }
    faltantes = columnas - set(skus.columns)
    if faltantes:
        raise ValueError(f"El archivo de SKU no tiene estas columnas: {faltantes}")
    if len(skus) != 1500:
        print(f"Advertencia: se esperaban 1500 SKU y se recibieron {len(skus)}.")
    if len(tickets) != 3000:
        print(f"Advertencia: se esperaban 3000 tickets y se recibieron {len(tickets)}.")


def importar_modulo(nombre, funcion):
    try:
        modulo = importlib.import_module(nombre)
    except ImportError as error:
        raise ImportError(
            f"No se pudo importar {nombre}.py. Verifica que esté en la misma "
            f"carpeta que main.py. Detalle: {error}"
        )
    if not hasattr(modulo, funcion):
        raise AttributeError(
            f"{nombre}.py debe contener la función {funcion}(). "
            "Revisa el contrato de integración al final de este archivo."
        )
    return getattr(modulo, funcion)


def extraer_seleccion(resultado, nombre_modulo):
    """
    Normaliza la salida de M3/M4. Se acepta una lista de IDs o un diccionario
    con la clave 'seleccionados' (también 'ids_seleccionados').
    """
    if isinstance(resultado, (list, tuple, set)):
        return list(resultado)
    if isinstance(resultado, dict):
        if "seleccionados" in resultado:
            return list(resultado["seleccionados"])
        if "ids_seleccionados" in resultado:
            return list(resultado["ids_seleccionados"])
    raise TypeError(
        f"La salida de {nombre_modulo} debe ser una lista de ID_SKU o un "
        "diccionario con 'seleccionados'."
    )


def escribir_reporte(contenido):
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    ruta = CARPETA_RESULTADOS / "reporte_final.txt"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def ejecutar():
    inicio_total = time.perf_counter()
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    semilla = pedir_semilla()
    lineas_reporte = []

    def registrar(texto=""):
        print(texto)
        lineas_reporte.append(str(texto))

    titulo(f"{CASO} - {EMPRESA} | MOTOR DE DECISIÓN ALGORÍTMICA")
    registrar(f"Grupo: {GRUPO}")
    registrar(f"Semilla: {semilla}")
    registrar(f"Fecha y hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    #  DATOS 
    titulo("M1 - DATOS Y ESTRUCTURAS (S1-S4)")
    skus, tickets = cargar_datos(semilla)
    validar_datos(skus, tickets)
    registrar(f"S1. Registros SKU: {len(skus)} | Tickets: {len(tickets)}")
    registrar(f"Columnas: {', '.join(map(str, skus.columns))}")
    registrar("Primeras 5 filas:")
    registrar(skus.head().to_string(index=False))

    funcion_m1 = importar_modulo("estructuras", "ejecutar_m1")
    salida_m1, tiempo_m1 = medir_tiempo(funcion_m1, skus, tickets)
    registrar(f"M1 ejecutado en {tiempo_m1:.3f} ms.")
    registrar("S2-S4: revisar el detalle que imprime estructuras.py.")
    # Si M1 devuelve un DataFrame de candidatas, se conserva para M2-M4
    candidatas = skus
    if isinstance(salida_m1, dict) and isinstance(salida_m1.get("candidatas"), pd.DataFrame):
        candidatas = salida_m1["candidatas"]
    elif isinstance(salida_m1, pd.DataFrame):
        candidatas = salida_m1

    # -------------------- RED --------------------
    titulo("M2 - RED DE PRODUCTOS AFINES (S5)")
    funcion_m2 = importar_modulo("red", "ejecutar_m2")
    salida_m2, tiempo_m2 = medir_tiempo(funcion_m2, candidatas, tickets)
    registrar(f"M2 ejecutado en {tiempo_m2:.3f} ms.")
    registrar(f"Resultado M2: {salida_m2}")
    clusters = salida_m2.get("clusters", []) if isinstance(salida_m2, dict) else []

    # -------------------- REFERENCIA --------------------
    titulo("M3 - SOLUCIÓN DE REFERENCIA: MOCHILA 0/1 (S6)")
    funcion_m3 = importar_modulo("referencia", "ejecutar_m3")
    salida_m3, tiempo_m3 = medir_tiempo(funcion_m3, candidatas)
    ids_m3 = extraer_seleccion(salida_m3, "referencia.py")
    registrar(f"M3 ejecutado en {tiempo_m3:.3f} ms.")
    registrar(f"SKU seleccionados por M3: {len(ids_m3)}")
    registrar(f"Resultado M3: {salida_m3}")

    # -------------------- METAHEURÍSTICA --------------------
    titulo("M4 - ALGORITMO GENÉTICO (S7)")
    funcion_m4 = importar_modulo("metaheuristica", "ejecutar_m4")
    salida_m4, tiempo_m4 = medir_tiempo(funcion_m4, candidatas, clusters, semilla)
    ids_m4 = extraer_seleccion(salida_m4, "metaheuristica.py")
    registrar(f"M4 ejecutado en {tiempo_m4:.3f} ms.")
    registrar(f"SKU seleccionados por M4: {len(ids_m4)}")
    registrar(f"Resultado M4: {salida_m4}")

    # -------------------- ANÁLISIS --------------------
    titulo("M5 - ANÁLISIS, COMPARACIÓN Y DECISIÓN (S8)")
    comparacion = comparar_soluciones(skus, ids_m3, ids_m4, clusters)
    mostrar_resumen(comparacion)

    registrar("\nS8. INDICADORES M3 VS M4")
    registrar(f"M3: {comparacion['M3']}")
    registrar(f"M4: {comparacion['M4']}")
    registrar(f"Diferencia de margen: S/ {comparacion['diferencia_margen_s']:.2f}")
    registrar(f"Diferencia porcentual: {comparacion['diferencia_porcentual']:.2f}%")

    ranking = margen_por_categoria(skus)
    registrar("\nG4. Margen semanal por centímetro y categoría:")
    registrar(ranking.to_string())

    registrar("\nBig-O teórico de las funciones de análisis:")
    for nombre, complejidad, explicacion in analizar_complejidad():
        registrar(f"- {nombre}: {complejidad}. {explicacion}")

    # cálculo de métricas sobre prefijos del conjunto de SKU.
    tamanos = []
    tiempos = []
    for n in (150, 450, 900, len(skus)):
        muestra = skus.iloc[:n].copy()
        _, ms = medir_tiempo(
            lambda: muestra["Margen_unit_S"] * muestra["Ventas_sem_u"]
        )
        tamanos.append(n)
        tiempos.append(ms)
    try:
        guardado = guardar_grafico_escalabilidad(
            tamanos, tiempos, CARPETA_RESULTADOS / "escalabilidad.png"
        )
        registrar(f"Gráfico escalabilidad.png generado: {guardado}")
    except Exception as error:
        registrar(f"No se pudo generar escalabilidad.png: {error}")

    
    if comparacion["diferencia_margen_s"] >= 0:
        recomendacion = (
            f"RECOMENDACIÓN: considerar la selección M4 (AG), con margen "
            f"semanal estimado de S/ {comparacion['M4']['margen_total']:.2f}, "
            f"siempre que cumpla espacio, presupuesto y mínimo por categoría."
        )
    else:
        recomendacion = (
            f"RECOMENDACIÓN: revisar la selección M3 como referencia; M4 obtuvo "
            f"S/ {abs(comparacion['diferencia_margen_s']):.2f} menos de margen "
            f"en esta ejecución. Verificar restricciones y calibración del AG."
        )
    registrar("\n" + recomendacion)

    duracion = time.perf_counter() - inicio_total
    registrar(f"\nTiempo total: {duracion:.2f} segundos.")
    if duracion >= 300:
        registrar("ADVERTENCIA: el programa superó el límite de 5 minutos.")
    else:
        registrar("Tiempo de ejecución dentro del límite de 5 minutos.")

    ruta = escribir_reporte("\n".join(lineas_reporte))
    titulo("CIERRE")
    print(f"Proceso completo. Revise la carpeta {CARPETA_RESULTADOS}/")
    print(f"Reporte guardado en: {ruta}")


if __name__ == "__main__":
    ejecutar()





