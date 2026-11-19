# Modulo 2: Red de afinidad de productos (Kruskal y Union-Find)

import pandas as pd

from estructuras import merge_sort

# Constante pedida en el Caso 3
CANTIDAD_CLUSTERS = 6


class UnionFind:
    def __init__(self, nodos):
        # Cada producto empieza siendo su propio padre (su propio grupo)
        self.padre = {nodo: nodo for nodo in nodos}
        self.rango = {nodo: 0 for nodo in nodos}

    def find(self, x):
        # Busca la raiz del grupo al que pertenece el producto x
        if self.padre[x] != x:
            self.padre[x] = self.find(self.padre[x])
        return self.padre[x]

    def union(self, x, y):
        # Une los grupos de dos productos si es que no estan juntos ya
        raiz_x = self.find(x)
        raiz_y = self.find(y)

        if raiz_x == raiz_y:
            return False  # Ya estaban en el mismo grupo, formaria ciclo

        # Unimos el arbol mas pequeno debajo del mas grande
        if self.rango[raiz_x] < self.rango[raiz_y]:
            self.padre[raiz_x] = raiz_y
        elif self.rango[raiz_x] > self.rango[raiz_y]:
            self.padre[raiz_y] = raiz_x
        else:
            self.padre[raiz_y] = raiz_x
            self.rango[raiz_x] += 1

        return True


def _extraer_ids_candidatos(candidatas):
    # Soporta DataFrame, diccionario o lista de SKUs/diccionarios desde M1
    if candidatas is None:
        return None
    if isinstance(candidatas, pd.DataFrame):
        for col in ("ID_SKU", "id_sku", "sku", "id"):
            if col in candidatas.columns:
                return list(candidatas[col].tolist())
        return None
    if isinstance(candidatas, dict):
        for clave in ("candidatas", "skus", "items", "ids_seleccionados", "seleccionados"):
            if clave in candidatas:
                return _extraer_ids_candidatos(candidatas[clave])
        return None

    ids = []
    for item in candidatas:
        if isinstance(item, dict):
            for clave in ("ID_SKU", "id_sku", "sku", "id"):
                if clave in item:
                    ids.append(item[clave])
                    break
        else:
            ids.append(item)
    return ids if ids else None


def construir_grafo_tickets(tickets, skus_candidatos=None):
    # Recorre los tickets para contar cuantas veces se compran juntos dos SKU
    nodos = set()
    pares_frecuencia = {}
    permitidos = set(skus_candidatos) if skus_candidatos is not None else None

    if permitidos is not None:
        # Aseguramos que todos los candidatos figuren como nodos aunque no tengan co-compras
        for sku in permitidos:
            nodos.add(sku)

    for ticket in tickets:
        # Quitamos repetidos dentro de un mismo ticket y filtramos por candidatos si aplica
        skus_unicos = sorted(
            list({sku for sku in ticket if permitidos is None or sku in permitidos}),
            key=lambda x: str(x),
        )
        for sku in skus_unicos:
            nodos.add(sku)

        # Armamos todas las parejas posibles dentro del ticket
        n = len(skus_unicos)
        for i in range(n):
            for j in range(i + 1, n):
                par = (skus_unicos[i], skus_unicos[j])
                pares_frecuencia[par] = pares_frecuencia.get(par, 0) + 1

    # Creamos las aristas con peso = 1 / frecuencia (mas compras juntos = menor peso)
    aristas = []
    for (sku1, sku2), freq in pares_frecuencia.items():
        peso = 1.0 / freq
        aristas.append((peso, sku1, sku2))

    nodos_ordenados = merge_sort(list(nodos), key=lambda x: str(x))
    return nodos_ordenados, aristas


def kruskal_clusters(nodos, aristas, k_clusters=CANTIDAD_CLUSTERS):
    # Ordenamos las aristas de menor a mayor peso usando merge_sort propio del M1
    aristas_ordenadas = merge_sort(list(aristas), key=lambda x: x[0])

    uf = UnionFind(nodos)
    mst = []

    # Paso 1: Armar el Arbol de Expansion Minima (MST)
    for peso, u, v in aristas_ordenadas:
        if uf.union(u, v):
            mst.append((peso, u, v))

    # Paso 2: Cortar las aristas mas pesadas para quedarnos con k_clusters grupos
    # Si el grafo tenia C componentes sueltas, necesitamos cortar (k_clusters - C) aristas
    componentes_iniciales = len(nodos) - len(mst)
    cortes_necesarios = max(0, k_clusters - componentes_iniciales)

    if cortes_necesarios > 0 and len(mst) >= cortes_necesarios:
        # Como el mst ya esta ordenado de menor a mayor peso, quitamos las ultimas
        aristas_finales = mst[:-cortes_necesarios]
    else:
        aristas_finales = mst

    # Paso 3: Volvemos a agrupar los nodos usando solo las aristas que quedaron
    uf_final = UnionFind(nodos)
    for peso, u, v in aristas_finales:
        uf_final.union(u, v)

    # Agrupamos los SKU por su raiz
    grupos_por_raiz = {}
    for nodo in nodos:
        raiz = uf_final.find(nodo)
        if raiz not in grupos_por_raiz:
            grupos_por_raiz[raiz] = []
        grupos_por_raiz[raiz].append(nodo)

    # Pasamos los grupos a indices limpios del 0 al 5 y creamos el diccionario para M4
    clusters = {}
    sku_to_cluster = {}
    for idx, lista_skus in enumerate(grupos_por_raiz.values()):
        clusters[idx] = lista_skus
        for sku in lista_skus:
            sku_to_cluster[sku] = idx

    return clusters, sku_to_cluster


def ejecutar_modulo_red(tickets, skus_candidatos=None):
    nodos, aristas = construir_grafo_tickets(tickets, skus_candidatos=skus_candidatos)
    clusters, sku_to_cluster = kruskal_clusters(nodos, aristas, CANTIDAD_CLUSTERS)

    # Impresion de la Salida S5 pedida en el trabajo
    print("\n" + "=" * 60)
    print("C3 VENTAS - S5. RESULTADO DE LA RED (M2)")
    print("=" * 60)
    print(f"Total productos analizados en tickets: {len(nodos)}")
    print(f"Total enlaces de co-compra detectados: {len(aristas)}")
    print(f"Clusters de afinidad generados: {len(clusters)}\n")

    for c_id, lista_skus in clusters.items():
        # Mostramos los primeros 8 para que no se llene toda la consola, y el total
        muestra = ", ".join(str(s) for s in lista_skus[:8])
        extra = f" ... (+{len(lista_skus) - 8} mas)" if len(lista_skus) > 8 else ""
        print(f"Cluster {c_id + 1} ({len(lista_skus)} SKUs): [{muestra}{extra}]")

    return clusters, sku_to_cluster


def ejecutar_m2(candidatas, tickets):
    skus_candidatos = _extraer_ids_candidatos(candidatas)
    clusters, sku_to_cluster = ejecutar_modulo_red(tickets, skus_candidatos=skus_candidatos)
    return {
        "clusters": clusters,
        "sku_to_cluster": sku_to_cluster,
    }