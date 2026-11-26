"""
Inventario FIFO (First In, First Out) por capas de costo.

Cada cisterna que llega crea una "capa" en el tanque con su propio costo
por galón. Las ventas consumen primero la capa más antigua; si una venta
cruza dos capas, su costo es el promedio ponderado de los galones usados.
"""


class ErrorInventario(Exception):
    """Error de negocio del inventario (sin stock, capacidad excedida, etc.)."""


class TanqueFIFO:
    """Tanque de un producto con sus capas de costo FIFO."""

    TOLERANCIA = 1e-6

    def __init__(self, producto, capacidad_maxima, guardar_historial=True):
        """
        producto: código (DB5, GR o GP)
        capacidad_maxima: galones que caben en el tanque
        guardar_historial: si es False no guarda cada movimiento (más rápido)
        """
        self.producto = producto
        self.capacidad_maxima = float(capacidad_maxima)
        self.capas = []                 # [{fecha, volumen_restante, costo_galon, volumen_original}]
        self.historial_movimientos = []
        self.guardar_historial = guardar_historial
        self.ultimo_error = ""
        self._stock = 0.0               # stock en caché para no sumar siempre

    # ------------------------------------------------------------ entradas
    def agregar_cisterna(self, fecha, volumen, costo_galon, origen="cisterna"):
        """
        Agrega una nueva capa al final del tanque.
        Devuelve True si se aceptó; False si se rechazó (motivo en ultimo_error).
        """
        self.ultimo_error = ""
        if volumen is None or volumen <= 0:
            self.ultimo_error = "El volumen debe ser mayor que cero."
            return False
        if costo_galon is None or costo_galon <= 0:
            self.ultimo_error = "El costo por galón debe ser mayor que cero."
            return False
        espacio = self.capacidad_maxima - self._stock
        if volumen > espacio + self.TOLERANCIA:
            self.ultimo_error = (
                f"La cisterna ({volumen:,.1f} gal) excede el espacio libre del tanque "
                f"({espacio:,.1f} gal de {self.capacidad_maxima:,.0f})."
            )
            return False

        self.capas.append({
            "fecha": fecha,
            "volumen_restante": float(volumen),
            "costo_galon": float(costo_galon),
            "volumen_original": float(volumen),
            "origen": origen,
        })
        self._stock += float(volumen)
        if self.guardar_historial:
            self.historial_movimientos.append({
                "fecha": fecha, "tipo": "ENTRADA", "origen": origen,
                "volumen": float(volumen), "costo_galon": float(costo_galon),
                "stock_resultante": self._stock,
            })
        return True

    # ------------------------------------------------------------- salidas
    def registrar_venta(self, fecha, volumen_vendido, precio_venta_galon):
        """
        Descuenta la venta empezando por la capa más antigua.
        Lanza ErrorInventario si no hay stock suficiente o datos inválidos.
        Devuelve {fecha, volumen, precio_venta, costo_promedio, margen,
                  utilidad, capas_usadas}.
        """
        if volumen_vendido is None or volumen_vendido <= 0:
            raise ErrorInventario("El volumen vendido debe ser mayor que cero.")
        if precio_venta_galon is None or precio_venta_galon <= 0:
            raise ErrorInventario("El precio de venta debe ser mayor que cero.")
        if volumen_vendido > self._stock + self.TOLERANCIA:
            raise ErrorInventario(
                f"Stock insuficiente de {self.producto}: se pidió {volumen_vendido:,.2f} gal "
                f"y solo hay {self._stock:,.2f} gal."
            )

        pendiente = float(volumen_vendido)
        costo_total = 0.0
        capas_usadas = []
        while pendiente > self.TOLERANCIA and self.capas:
            capa = self.capas[0]
            tomado = min(pendiente, capa["volumen_restante"])
            capa["volumen_restante"] -= tomado
            pendiente -= tomado
            costo_total += tomado * capa["costo_galon"]
            capas_usadas.append({
                "fecha_capa": capa["fecha"], "volumen": tomado,
                "costo_galon": capa["costo_galon"],
            })
            if capa["volumen_restante"] <= self.TOLERANCIA:
                self.capas.pop(0)       # capa agotada

        vendido = float(volumen_vendido) - max(pendiente, 0.0)
        self._stock = max(self._stock - vendido, 0.0)
        costo_promedio = costo_total / vendido if vendido > 0 else 0.0
        margen = precio_venta_galon - costo_promedio
        resultado = {
            "fecha": fecha,
            "volumen": vendido,
            "precio_venta": float(precio_venta_galon),
            "costo_promedio": costo_promedio,
            "margen": margen,
            "utilidad": margen * vendido,
            "capas_usadas": capas_usadas,
        }
        if self.guardar_historial:
            self.historial_movimientos.append({
                "fecha": fecha, "tipo": "SALIDA", "origen": "venta",
                "volumen": vendido, "costo_galon": costo_promedio,
                "stock_resultante": self._stock,
            })
        return resultado

    # ------------------------------------------------------------ consultas
    def stock_actual(self):
        """Galones disponibles (suma de las capas)."""
        return self._stock

    def costo_promedio_actual(self):
        """Costo promedio ponderado del combustible que queda en el tanque."""
        if self._stock <= self.TOLERANCIA:
            return 0.0
        return self.valor_inventario() / self._stock

    def costo_capa_mas_antigua(self):
        """Costo de la capa que se venderá primero."""
        return self.capas[0]["costo_galon"] if self.capas else 0.0

    def costo_capa_mas_reciente(self):
        """Costo de la última cisterna recibida que aún tiene stock."""
        return self.capas[-1]["costo_galon"] if self.capas else 0.0

    def detalle_capas(self):
        """Copia de las capas actuales (de la más antigua a la más reciente)."""
        return [dict(c) for c in self.capas]

    def valor_inventario(self):
        """Valor en soles: Σ volumen_restante × costo_galon."""
        return sum(c["volumen_restante"] * c["costo_galon"] for c in self.capas)

    def porcentaje_lleno(self):
        """Fracción de la capacidad ocupada (0 a 1)."""
        if self.capacidad_maxima <= 0:
            return 0.0
        return min(self._stock / self.capacidad_maxima, 1.0)
