"""
Contenido de la guía de uso: una sola fuente para el tutorial de bienvenida
(interfaz/tutorial.py) y para el manual exportable (exportador/manual_word.py).

Cada sección: pantalla del menú, título, para qué sirve, elementos (botón o
zona → qué hace) y la decisión que ayuda a tomar.
"""

INTRO = ("PRECIAL ayuda al administrador de un grifo a decidir a qué precio vender cada combustible, "
         "cuándo revisar ese precio y cuándo pedir una cisterna. Calcula el costo real de cada galón "
         "(inventario FIFO), pronostica los cambios de precio del proveedor (Modelo 1, Croston TSB) y "
         "recomienda el precio que maximiza la utilidad (Modelo 2). Además genera el borrador del "
         "artículo científico con las tablas y figuras de sus datos. Todo funciona sin internet: "
         "los datos se guardan en la carpeta del programa.")

SECCIONES = [
    {"pantalla": "Inicio", "titulo": "Tablero de decisiones",
     "para_que": "Es la pantalla principal. Resume en un vistazo el estado del negocio y lo que debe "
                 "hacer HOY con cada combustible.",
     "elementos": [
         ("Indicadores superiores", "Ventas del periodo, utilidad bruta con costo FIFO, ganancia extra que "
                                    "habría dado el modelo frente a un margen fijo y número de decisiones urgentes."),
         ("Tarjeta de cada combustible", "Semáforo ACTUAR HOY (rojo) / ATENCIÓN (ámbar) / EN ORDEN (verde), "
                                         "precio recomendado y cuánto subir o bajar respecto al actual."),
         ("Bloque GERENCIAL", "Cuándo se espera el próximo cambio de precio del proveedor, si subirá o "
                              "bajará y con qué confianza."),
         ("Bloque OPERATIVA", "Barra de llenado del tanque, días de cobertura del stock y si debe pedir "
                              "cisterna hoy, en 24–48 h o si no hay urgencia."),
         ("Ver precio óptimo / Pronóstico", "Abren el detalle del Modelo 2 o del Modelo 1."),
         ("Importar datos", "Carga sus archivos Excel o CSV (ventas, compras, precios, inventario)."),
         ("Generar artículo", "Va a la pantalla que produce el borrador del artículo en Word."),
         ("Alertas y avisos", "Stock bajo, proveedor atrasado en su cambio y movimientos rechazados."),
         ("Cargar datos de ejemplo / Borrar todos los datos", "Prueban el sistema con 6 meses simulados o "
                                                              "lo dejan vacío para usar sus datos."),
     ],
     "decision": "Fijar el precio del día y decidir si se pide cisterna."},
    {"pantalla": "Ventas", "titulo": "Ventas",
     "para_que": "Registra ventas una por una o revisa las importadas.",
     "elementos": [("Registrar venta", "Fecha, producto, galones y precio de una venta nueva."),
                   ("Importar ventas (CSV/Excel)", "Carga el reporte de la consola de una sola vez."),
                   ("Tabla", "Últimas ventas con su costo FIFO, margen y utilidad calculados.")],
     "decision": "Controlar que cada venta deje margen positivo."},
    {"pantalla": "Compras", "titulo": "Compras (cisternas)",
     "para_que": "Registra cada cisterna recibida con su costo por galón.",
     "elementos": [("Registrar cisterna", "Fecha de llegada, producto, volumen, costo por galón y proveedor."),
                   ("Importar compras (CSV/Excel)", "Carga todas las cisternas de un archivo."),
                   ("Tabla de compras", "Estado de cada cisterna: aceptada o rechazada (por ejemplo, si "
                                        "supera la capacidad del tanque).")],
     "decision": "Verificar el costo de reposición y el abastecimiento."},
    {"pantalla": "Inventario", "titulo": "Inventario FIFO",
     "para_que": "Muestra los lotes que hay en cada tanque y el costo real del combustible que se vende.",
     "elementos": [("Lotes", "Cada cisterna con su volumen restante y costo; se vende primero la más antigua."),
                   ("Gráfico", "Evolución diaria del stock y del costo promedio.")],
     "decision": "Conocer el costo verdadero antes de fijar el precio."},
    {"pantalla": "Pronóstico (Modelo 1)", "titulo": "Modelo 1 — Pronóstico del proveedor",
     "para_que": "Predice cuándo cambiará el precio del proveedor y en qué dirección (Croston TSB).",
     "elementos": [("Tarjetas por producto", "Días hasta el próximo cambio, fecha estimada, dirección, "
                                             "monto aproximado y nivel de confianza."),
                   ("Fecha actual / Aplicar fecha / Hoy", "Simula otra fecha para ver qué habría dicho el modelo."),
                   ("Optimizar α y β automáticamente", "Elige los parámetros con menor error histórico; "
                                                       "«Recalcular» aplica los cambios."),
                   ("Últimos cambios y Backtest", "Historial de cambios del proveedor y qué tan bien habría "
                                                  "acertado el modelo en el pasado."),
                   ("Exportar tabla del Modelo 1", "Guarda los resultados en Excel.")],
     "decision": "Saber cuándo revisar el precio y anticipar subidas o bajadas."},
    {"pantalla": "Precio óptimo (Modelo 2)", "titulo": "Modelo 2 — Precio óptimo",
     "para_que": "Calcula el precio que deja la mayor utilidad respetando margen mínimo (5 %), máximo (15 %) "
                 "y el stock disponible.",
     "elementos": [("Tarjeta por producto", "Precio recomendado, hasta cuándo mantenerlo, costo FIFO, margen "
                                            "y utilidad diaria estimada."),
                   ("Comparación con márgenes fijos", "Cuánto ganaría de más o de menos con 5 %, 8 % o 12 %."),
                   ("Ver análisis completo", "Curva de utilidad, sensibilidad del precio y escenarios de "
                                             "elasticidad κ."),
                   ("Usar como horizonte los días hasta el próximo cambio", "Conecta el Modelo 2 con el "
                                                                            "pronóstico del Modelo 1."),
                   ("Recalcular / Exportar tabla del Modelo 2", "Aplica cambios y guarda en Excel.")],
     "decision": "Fijar el precio de venta con fundamento cuantitativo."},
    {"pantalla": "Reportes", "titulo": "Reportes",
     "para_que": "Resume ventas, compras y utilidad por día, semana o mes.",
     "elementos": [("Periodo y producto", "Filtros del reporte."),
                   ("Exportar a Excel", "Guarda el reporte para compartirlo.")],
     "decision": "Evaluar el desempeño del periodo y presentarlo a la gerencia."},
    {"pantalla": "Validación", "titulo": "Validación",
     "para_que": "Demuestra con evidencia si los modelos funcionan.",
     "elementos": [("▶ Ejecutar validación", "Corre el backtest y la simulación de políticas."),
                   ("Desempeño del Modelo 1", "Error en días del pronóstico frente a un promedio simple."),
                   ("Comparación de políticas (6 meses)", "Margen fijo 8 % vs precio óptimo: utilidad, "
                                                          "margen y quiebres de stock."),
                   ("Exportar validación completa", "Guarda todo en Excel.")],
     "decision": "Justificar ante la gerencia (y en el artículo) la adopción del sistema."},
    {"pantalla": "Exportar artículo", "titulo": "Exportar artículo",
     "para_que": "Genera en un clic todo el material para redactar el artículo.",
     "elementos": [("Exportar todo", "BORRADOR_ARTICULO.docx (artículo completo con resumen, metodología, "
                                     "resultados, matriz de decisiones y conclusiones), tablas en Excel, "
                                     "6 gráficos a 300 DPI y resumen en texto."),
                   ("Carpeta de destino", "Dónde se guardan los archivos."),
                   ("Calcular vista previa", "Revisa cada tabla y su interpretación antes de exportar.")],
     "decision": "Comunicar los resultados con cifras verificables."},
    {"pantalla": "Configuración", "titulo": "Configuración",
     "para_que": "Ajusta los parámetros del negocio y de los modelos.",
     "elementos": [("Capacidad de tanques", "Galones máximos por producto."),
                   ("Márgenes", "Mínimo, máximo y margen fijo de comparación."),
                   ("Elasticidad κ", "Sensibilidad de los clientes al precio."),
                   ("Guardar configuración / Restaurar valores por defecto", "Aplica o deshace los cambios.")],
     "decision": "Adaptar el sistema a la realidad de su grifo."},
]

AYUDA_FINAL = ("Puede repetir este tutorial con el botón «❓ Tutorial» del menú y exportar el manual "
               "completo en Word con «📘 Manual».")
