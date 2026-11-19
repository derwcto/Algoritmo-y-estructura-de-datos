import csv
import os
import random
import statistics
import time

import matplotlib
import pandas as pd

from estructuras import merge_sort

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CAPACIDAD_GONDOLA_CM = 1200
PRESUPUESTO_S = 30000
MIN_SKU_POR_CATEGORIA = 2
NUM_CATEGORIAS = 8
BONO_CRUZADA = 0.05
UMBRAL_BONO_CLUSTER = 3
PROB_INICIAL_GEN = 0.25
NUM_CORRIDAS = 10
SEMILLAS_CORRIDAS = list(range(1, NUM_CORRIDAS + 1))

CATEGORIAS = [
    "Abarrotes",
    "Lacteos",
    "Bebidas",
    "Snacks",
    "Limpieza",
    "Cuidado",
    "Panaderia",
    "Congelados",
]

PENALTY_SPACE = 8000.0
PENALTY_BUDGET = 100.0
PENALTY_CAT = 150000.0

CONFIGURACIONES_M4 = [
    {"nombre": "Config_A", "pop_size": 100, "generations": 200, "pc": 0.8, "pm": 0.01, "elitism": 5, "k": 3},
    {"nombre": "Config_B", "pop_size": 150, "generations": 250, "pc": 0.75, "pm": 0.005, "elitism": 8, "k": 4},
    {"nombre": "Config_C", "pop_size": 80, "generations": 150, "pc": 0.85, "pm": 0.02, "elitism": 3, "k": 3},
]


def _normalizar_instancia(instancia):
    if isinstance(instancia, pd.DataFrame):
        df = instancia.copy()
        if "Margen_semanal" not in df.columns:
            df["Margen_semanal"] = df["Margen_unit_S"] * df["Ventas_sem_u"]
        if "Indice" not in df.columns:
            df["Indice"] = df["Margen_semanal"] / df["Frente_cm"].replace(0, 1)
        return df.to_dict("records")
    normalizados = []
    for fila in instancia:
        item = dict(fila)
        if "Margen_semanal" not in item:
            item["Margen_semanal"] = item["Margen_unit_S"] * item["Ventas_sem_u"]
        if "Indice" not in item:
            frente = item["Frente_cm"] if item["Frente_cm"] else 1
            item["Indice"] = item["Margen_semanal"] / frente
        normalizados.append(item)
    return normalizados


def _normalizar_clusters(clusters):
    if isinstance(clusters, dict):
        return dict(clusters)
    mapa = {}
    if isinstance(clusters, (list, tuple)):
        for idx, grupo in enumerate(clusters):
            if isinstance(grupo, dict):
                for sku_id, cl_id in grupo.items():
                    mapa[sku_id] = cl_id
            elif isinstance(grupo, (list, tuple, set)):
                for sku_id in grupo:
                    mapa[sku_id] = idx
    return mapa


def _evaluar(crom, instancia, sku_to_cluster, num_clusters, space_only):
    espacio = 0
    presup = 0
    margen = 0.0
    cat_count = {c: 0 for c in CATEGORIAS}
    cluster_sel_margen = {i: 0.0 for i in range(num_clusters)}
    cluster_count = {i: 0 for i in range(num_clusters)}

    for i, g in enumerate(crom):
        if g == 1:
            s = instancia[i]
            espacio += s["Frente_cm"]
            presup += s["Inventario_S"]
            margen += s["Margen_semanal"]
            cat = s["Categoria"]
            cat_count[cat] = cat_count.get(cat, 0) + 1
            cl = sku_to_cluster.get(s["ID_SKU"])
            if cl is not None and 0 <= cl < num_clusters:
                cluster_count[cl] += 1
                cluster_sel_margen[cl] += s["Margen_semanal"]

    bono = 0.0
    if not space_only:
        for cl in range(num_clusters):
            if cluster_count[cl] >= UMBRAL_BONO_CLUSTER:
                bono += BONO_CRUZADA * cluster_sel_margen[cl]

    total = margen + bono
    penalty = 0.0

    if espacio > CAPACIDAD_GONDOLA_CM:
        penalty += (espacio - CAPACIDAD_GONDOLA_CM) * PENALTY_SPACE

    if not space_only:
        if presup > PRESUPUESTO_S:
            penalty += (presup - PRESUPUESTO_S) * PENALTY_BUDGET
        for c in CATEGORIAS:
            if cat_count.get(c, 0) < MIN_SKU_POR_CATEGORIA:
                penalty += (MIN_SKU_POR_CATEGORIA - cat_count.get(c, 0)) * PENALTY_CAT

    fitness = total - penalty
    feasible = espacio <= CAPACIDAD_GONDOLA_CM
    if not space_only:
        feasible = (
            feasible
            and presup <= PRESUPUESTO_S
            and all(cat_count.get(c, 0) >= MIN_SKU_POR_CATEGORIA for c in CATEGORIAS)
        )

    info = {
        "espacio": espacio,
        "presup": presup,
        "margen": margen,
        "bono": bono,
        "total": total,
        "cat_count": cat_count,
        "feasible": feasible,
    }
    return fitness, info


def _construir_poblacion_inicial(instancia, pop_size, rng, space_only):
    n = len(instancia)
    population = []
    order = merge_sort(list(range(n)), key=lambda i: instancia[i]["Indice"], reverse=True)
    greedy = [0] * n
    sp = 0
    bp = 0.0
    for i in order:
        if sp + instancia[i]["Frente_cm"] <= CAPACIDAD_GONDOLA_CM:
            if space_only or bp + instancia[i]["Inventario_S"] <= PRESUPUESTO_S:
                greedy[i] = 1
                sp += instancia[i]["Frente_cm"]
                bp += instancia[i]["Inventario_S"]
    population.append(greedy)

    while len(population) < pop_size:
        crom = [1 if rng.random() < PROB_INICIAL_GEN else 0 for _ in range(n)]
        population.append(crom)

    return population


def ejecutar_ag(instancia, sku_to_cluster, config, seed, space_only=False):
    rng = random.Random(seed)
    n = len(instancia)
    num_clusters = max(sku_to_cluster.values()) + 1 if sku_to_cluster else 1
    pop_size = config["pop_size"]
    generations = config["generations"]
    pc = config["pc"]
    pm = config["pm"]
    elitism = config["elitism"]
    k = config["k"]

    population = _construir_poblacion_inicial(instancia, pop_size, rng, space_only)

    best_overall = None
    best_fitness = None
    history = []

    def tournament(fitnesses):
        cand = [rng.randrange(pop_size) for _ in range(k)]
        best = cand[0]
        for c in cand[1:]:
            if fitnesses[c] > fitnesses[best]:
                best = c
        return list(population[best])

    for _ in range(generations):
        fitnesses = []
        for crom in population:
            f, _ = _evaluar(crom, instancia, sku_to_cluster, num_clusters, space_only)
            fitnesses.append(f)

        paired = sorted(zip(fitnesses, population), key=lambda x: x[0], reverse=True)
        if best_fitness is None or paired[0][0] > best_fitness:
            best_fitness = paired[0][0]
            best_overall = list(paired[0][1])
        history.append(best_fitness)

        new_pop = [list(paired[i][1]) for i in range(min(elitism, pop_size))]
        while len(new_pop) < pop_size:
            p1 = tournament(fitnesses)
            p2 = tournament(fitnesses)
            if rng.random() < pc:
                child = [p1[i] if rng.random() < 0.5 else p2[i] for i in range(n)]
            else:
                child = list(p1)
            for i in range(n):
                if rng.random() < pm:
                    child[i] = 1 - child[i]
            new_pop.append(child)
        population = new_pop

    _, info = _evaluar(best_overall, instancia, sku_to_cluster, num_clusters, space_only)
    return {
        "best_fitness": best_fitness,
        "best_crom": best_overall,
        "history": history,
        "info": info,
        "seed": seed,
        "config": config,
    }


def ejecutar_m4(instancia, clusters, semilla_base, valor_m3=None):
    items = _normalizar_instancia(instancia)
    sku_to_cluster = _normalizar_clusters(clusters)
    rows = []
    resultados_config = {}
    best_run_global = None
    best_val_global = None

    for cfg in CONFIGURACIONES_M4:
        vals = []
        times = []
        best_run_cfg = None
        best_val_cfg = None

        for idx_corrida, seed in enumerate(SEMILLAS_CORRIDAS, start=1):
            t0 = time.perf_counter()
            res = ejecutar_ag(items, sku_to_cluster, cfg, seed, space_only=False)
            t1 = time.perf_counter()
            tiempo_ms = (t1 - t0) * 1000.0
            val = res["best_fitness"]
            vals.append(val)
            times.append(tiempo_ms)
            rows.append({
                "Configuracion": cfg["nombre"],
                "Corrida": idx_corrida,
                "Semilla": seed,
                "MejorValor": round(val, 2),
                "Tiempo_ms": round(tiempo_ms, 2),
                "Factible": res["info"]["feasible"],
            })
            if best_val_cfg is None or val > best_val_cfg:
                best_val_cfg = val
                best_run_cfg = res
            if best_val_global is None or val > best_val_global:
                best_val_global = val
                best_run_global = res

        resultados_config[cfg["nombre"]] = {
            "config": cfg,
            "mejor": max(vals),
            "promedio": sum(vals) / len(vals),
            "desviacion": statistics.pstdev(vals),
            "tiempo_promedio": sum(times) / len(times),
            "best_run": best_run_cfg,
            "vals": vals,
            "times": times,
        }

    os.makedirs("resultados", exist_ok=True)
    with open("resultados/corridas_M4.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Configuracion", "Corrida", "Semilla", "MejorValor", "Tiempo_ms", "Factible"],
        )
        writer.writeheader()
        writer.writerows(rows)

    hist = best_run_global["history"]
    plt.figure()
    plt.plot(range(1, len(hist) + 1), hist)
    plt.xlabel("Generacion")
    plt.ylabel("Mejor fitness")
    plt.title("Convergencia M4 (mejor corrida)")
    plt.tight_layout()
    plt.savefig("resultados/convergencia.png")
    plt.close()

    ag_space = ejecutar_ag(items, sku_to_cluster, CONFIGURACIONES_M4[0], SEMILLAS_CORRIDAS[0], space_only=True)
    dif_pct_espacio = None
    if valor_m3 is not None and valor_m3 != 0:
        dif_pct_espacio = ((ag_space["best_fitness"] - valor_m3) / valor_m3) * 100.0

    ids_seleccionados = [
        items[i]["ID_SKU"]
        for i, gen in enumerate(best_run_global["best_crom"])
        if gen == 1
    ]

    print("=" * 80)
    print("C3 VENTAS - S7. METAHEURISTICA (M4)")
    print("=" * 80)
    print(f"{'Config':<10}{'Mejor':>12}{'Promedio':>12}{'DesvStd':>12}{'Tiempo_ms':>12}")
    for name, rc in resultados_config.items():
        print(f"{name:<10}{rc['mejor']:>12.2f}{rc['promedio']:>12.2f}{rc['desviacion']:>12.2f}{rc['tiempo_promedio']:>12.2f}")
    print(f"AG solo espacio (fitness): {ag_space['best_fitness']:.2f}")
    if dif_pct_espacio is not None:
        print(f"Diferencia % AG solo espacio vs M3: {dif_pct_espacio:+.2f}%")
    print("Archivo: resultados/corridas_M4.csv (30 filas)")
    print("Archivo: resultados/convergencia.png")

    return {
        "seleccionados": ids_seleccionados,
        "ids_seleccionados": ids_seleccionados,
        "resultados_config": resultados_config,
        "best_run_global": best_run_global,
        "best_value_global": best_val_global,
        "ag_space": ag_space,
        "dif_pct_espacio": dif_pct_espacio,
        "rows": rows,
    }


def ejecutar_experimentos_m4(instancia, sku_to_cluster, semilla_base, valor_m3=None):
    return ejecutar_m4(instancia, sku_to_cluster, semilla_base, valor_m3=valor_m3)