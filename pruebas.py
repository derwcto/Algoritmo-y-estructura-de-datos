

import pandas as pd
from analisis import (
    calcular_metricas, calcular_bono, comparar_soluciones,
    margen_por_categoria
)


def datos_prueba():
    return pd.DataFrame([
        {"ID_SKU": 1, "Categoria": "Abarrotes", "Precio_S": 10.0,
         "Ventas_sem_u": 100, "Frente_cm": 20, "Inventario_S": 500.0,
         "Margen_unit_S": 2.0},
        {"ID_SKU": 2, "Categoria": "Abarrotes", "Precio_S": 12.0,
         "Ventas_sem_u": 80, "Frente_cm": 20, "Inventario_S": 400.0,
         "Margen_unit_S": 3.0},
        {"ID_SKU": 3, "Categoria": "Bebidas", "Precio_S": 8.0,
         "Ventas_sem_u": 50, "Frente_cm": 15, "Inventario_S": 300.0,
         "Margen_unit_S": 1.5},
        {"ID_SKU": 4, "Categoria": "Bebidas", "Precio_S": 18.0,
         "Ventas_sem_u": 60, "Frente_cm": 15, "Inventario_S": 350.0,
         "Margen_unit_S": 2.0},
    ])


def test_metricas_margen_y_espacio():
    skus = datos_prueba()
    resultado = calcular_metricas(skus, [1, 2])
    assert resultado["cantidad_sku"] == 2
    assert resultado["margen_base"] == 440.0
    assert resultado["espacio_cm"] == 40
    assert resultado["inventario_s"] == 900.0


def test_bono_clúster_con_tres_sku():
    skus = datos_prueba()
    elegidos = skus[skus["ID_SKU"].isin([1, 2, 3])].copy()
    bono = calcular_bono(elegidos, [[1, 2, 3, 4]])
    margen = (2.0 * 100) + (3.0 * 80) + (1.5 * 50)
    assert abs(bono - margen * 0.05) < 1e-9


def test_comparacion_m3_m4():
    skus = datos_prueba()
    resultado = comparar_soluciones(skus, [1, 2], [1, 2, 3], [])
    assert resultado["M3"]["margen_base"] == 440.0
    assert resultado["M4"]["margen_base"] == 515.0
    assert resultado["diferencia_margen_s"] == 75.0


def test_ranking_categoria():
    ranking = margen_por_categoria(datos_prueba())
    assert "margen_por_cm" in ranking.columns
    assert len(ranking) == 2
    assert ranking["margen_por_cm"].iloc[0] >= ranking["margen_por_cm"].iloc[1]


if __name__ == "__main__":
    pruebas = [
        test_metricas_margen_y_espacio,
        test_bono_clúster_con_tres_sku,
        test_comparacion_m3_m4,
        test_ranking_categoria,
    ]
    correctas = 0
    for prueba in pruebas:
        prueba()
        print(f"OK: {prueba.__name__}")
        correctas += 1
    print(f"\n{correctas}/{len(pruebas)} pruebas superadas.")
