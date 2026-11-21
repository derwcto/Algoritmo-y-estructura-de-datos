import bisect
import pandas as pd


class _NodoAVL:
    def __init__(self, clave, datos):
        self.clave = clave
        self.datos = datos
        self.izquierda = None
        self.derecha = None
        self.altura = 1


class ArbolAVL:
    def __init__(self):
        self.raiz = None
        self.cantidad = 0

    def obtener_altura(self, nodo):
        if nodo is None:
            return 0
        return nodo.altura

    def _actualizar_altura(self, nodo):
        nodo.altura = 1 + max(
            self.obtener_altura(nodo.izquierda),
            self.obtener_altura(nodo.derecha),
        )

    def obtener_balance(self, nodo):
        if nodo is None:
            return 0
        return self.obtener_altura(nodo.izquierda) - self.obtener_altura(nodo.derecha)

    def _rotar_derecha(self, y):
        x = y.izquierda
        subarbol_derecho_x = x.derecha

        x.derecha = y
        y.izquierda = subarbol_derecho_x

        self._actualizar_altura(y)
        self._actualizar_altura(x)
        return x

    def _rotar_izquierda(self, x):
        y = x.derecha
        subarbol_izquierdo_y = y.izquierda

        y.izquierda = x
        x.derecha = subarbol_izquierdo_y

        self._actualizar_altura(x)
        self._actualizar_altura(y)
        return y

    def _insertar(self, nodo, clave, datos):
        if nodo is None:
            self.cantidad += 1
            return _NodoAVL(clave, datos)

        if clave < nodo.clave:
            nodo.izquierda = self._insertar(nodo.izquierda, clave, datos)
        elif clave > nodo.clave:
            nodo.derecha = self._insertar(nodo.derecha, clave, datos)
        else:
            nodo.datos = datos
            return nodo

        self._actualizar_altura(nodo)
        balance = self.obtener_balance(nodo)

        if balance > 1 and clave < nodo.izquierda.clave:
            return self._rotar_derecha(nodo)

        if balance < -1 and clave > nodo.derecha.clave:
            return self._rotar_izquierda(nodo)

        if balance > 1 and clave > nodo.izquierda.clave:
            nodo.izquierda = self._rotar_izquierda(nodo.izquierda)
            return self._rotar_derecha(nodo)

        if balance < -1 and clave < nodo.derecha.clave:
            nodo.derecha = self._rotar_derecha(nodo.derecha)
            return self._rotar_izquierda(nodo)

        return nodo

    def insertar(self, clave, datos):
        self.raiz = self._insertar(self.raiz, clave, datos)

    def buscar(self, clave):
        actual = self.raiz
        while actual is not None:
            if clave == actual.clave:
                return actual.datos
            if clave < actual.clave:
                actual = actual.izquierda
            else:
                actual = actual.derecha
        return None

    def inorden(self):
        recorrido = []

        def _recorrer(nodo):
            if nodo is None:
                return
            _recorrer(nodo.izquierda)
            recorrido.append((nodo.clave, nodo.datos))
            _recorrer(nodo.derecha)

        _recorrer(self.raiz)
        return recorrido


def _mezclar(izquierda, derecha, obtener_valor, descendente):
    resultado = []
    i = 0
    j = 0

    while i < len(izquierda) and j < len(derecha):
        val_izq = obtener_valor(izquierda[i])
        val_der = obtener_valor(derecha[j])
        tomar_izq = (val_izq >= val_der) if descendente else (val_izq <= val_der)
        if tomar_izq:
            resultado.append(izquierda[i])
            i += 1
        else:
            resultado.append(derecha[j])
            j += 1

    while i < len(izquierda):
        resultado.append(izquierda[i])
        i += 1

    while j < len(derecha):
        resultado.append(derecha[j])
        j += 1

    return resultado


def ordenar_merge_sort(elementos, obtener_valor, descendente=False):
    if len(elementos) <= 1:
        return list(elementos)

    medio = len(elementos) // 2
    izquierda = ordenar_merge_sort(elementos[:medio], obtener_valor, descendente)
    derecha = ordenar_merge_sort(elementos[medio:], obtener_valor, descendente)
    return _mezclar(izquierda, derecha, obtener_valor, descendente)


def merge_sort(elementos, key=None, reverse=False, obtener_valor=None, descendente=None):
    extractor = (
        obtener_valor
        if obtener_valor is not None
        else (key if key is not None else (lambda x: x))
    )
    es_desc = descendente if descendente is not None else reverse
    return ordenar_merge_sort(elementos, obtener_valor=extractor, descendente=es_desc)


def buscar_binaria(claves_ordenadas, objetivo):
    indice = bisect.bisect_left(claves_ordenadas, objetivo)
    if indice < len(claves_ordenadas) and claves_ordenadas[indice] == objetivo:
        return indice
    return -1


def _margen_semanal_sku(fila):
    margen_unit = float(fila.get("Margen_unit_S", 0.0) or 0.0)
    ventas_sem = float(fila.get("Ventas_sem_u", 0.0) or 0.0)
    return margen_unit * ventas_sem


def ejecutar_m1(skus, tickets):
    registros = skus.to_dict(orient="records")

    arbol_avl = ArbolAVL()
    for fila in registros:
        id_sku = int(fila["ID_SKU"])
        arbol_avl.insertar(id_sku, fila)

    print(
        f"[S2 - AVL] Nodos: {arbol_avl.cantidad} | "
        f"Altura: {arbol_avl.obtener_altura(arbol_avl.raiz)} | "
        f"Balance raíz: {arbol_avl.obtener_balance(arbol_avl.raiz)}"
    )

    ordenados_margen = ordenar_merge_sort(
        registros,
        obtener_valor=_margen_semanal_sku,
        descendente=True,
    )
    top_3 = ordenados_margen[:3]
    if top_3:
        detalle_top = ", ".join(
            f"SKU {int(item['ID_SKU'])} (S/ {_margen_semanal_sku(item):.2f})"
            for item in top_3
        )
        print(f"[S3 - Ordenamiento MergeSort] Top 3 margen semanal: {detalle_top}")

    ordenados_id = ordenar_merge_sort(
        registros,
        obtener_valor=lambda item: int(item["ID_SKU"]),
        descendente=False,
    )
    ids_ordenados = [int(item["ID_SKU"]) for item in ordenados_id]

    ids_muestra = [int(item["ID_SKU"]) for item in registros[:3]]
    coincidencias = 0
    for sku_id in ids_muestra:
        pos = buscar_binaria(ids_ordenados, sku_id)
        if pos != -1 and arbol_avl.buscar(sku_id) is not None:
            coincidencias += 1

    ausentes_verificados = sum(
        1
        for id_inexistente in (-1, 999999999)
        if buscar_binaria(ids_ordenados, id_inexistente) == -1
    )
    print(
        f"[S4 - Búsqueda Binaria] Encontrados {coincidencias}/{len(ids_muestra)} "
        f"IDs existentes | Ausentes validados: {ausentes_verificados}/2"
    )

    conteo_tickets = {}
    for ticket in tickets:
        for id_item in ticket:
            sku_num = int(id_item)
            conteo_tickets[sku_num] = conteo_tickets.get(sku_num, 0) + 1

    df_candidatas = pd.DataFrame(ordenados_margen)[list(skus.columns)].copy()

    return {
        "candidatas": df_candidatas,
        "avl": arbol_avl,
        "ids_ordenados": ids_ordenados,
        "conteo_tickets": conteo_tickets,
    }