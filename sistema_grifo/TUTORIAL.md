# 📘 Tutorial de PRECIAL — paso a paso

PRECIAL ayuda al administrador de un grifo a responder **tres preguntas**:

1. **¿A cuánto me cuesta realmente cada galón que vendo?** → Inventario **FIFO**
2. **¿Cuándo va a cambiar el precio mi proveedor, y si sube o baja?** → **Modelo 1** (Croston TSB)
3. **¿A qué precio debo vender hoy para ganar más sin perder clientes?** → **Modelo 2** (precio óptimo)

Trabaja con tres productos: **DB5** (Diésel B5), **GR** (Gasolina Regular 90) y **GP** (Gasolina Premium 95).

> 💡 Puede abrir PRECIAL desde la computadora, la tablet o el celular. En el celular, el menú está en el botón **›** (arriba a la izquierda).

---

## Paso 1 — Ingresar

1. Abra la dirección web de PRECIAL.
2. Escriba el **usuario** y la **contraseña** que le dio el administrador.
3. Pulse **Ingresar**.

Para salir, use **Cerrar sesión** al final del menú. Todos usan la misma cuenta y ven los mismos datos: si alguien registra una venta, los demás la ven también.

---

## Paso 2 — Cargar los datos (solo la primera vez)

Vaya a **📂 Importar datos**.

1. Pulse **Browse files** y seleccione **todos juntos** sus archivos:
   - `SIMULADO_grifo_resumen.xlsx` (compras de cisternas, precios del surtidor, inventario inicial)
   - `SIMULADO_ventas_consola.xlsx` (todas las ventas)
   - `VERDAD_OCULTA_simulacion.xlsx` (precios del proveedor, precio de mercado y ventas perdidas; sirve para la validación)
2. Pulse **Importar archivos** y espere (con muchas ventas puede tardar un minuto).
3. Lea el resumen: dice cuántos registros entraron de cada hoja y si algo se rechazó.

El sistema **reconoce solo** qué contiene cada hoja por su nombre y sus columnas. Si vuelve a importar un archivo del mismo tipo, **reemplaza** los datos anteriores de ese tipo.

**Formatos que acepta** (Excel o CSV):

| Datos | Columnas |
|---|---|
| Ventas | Fecha, Producto, Volumen_gal, Precio_venta (Importe opcional) |
| Compras de cisternas | Fecha_pedido, Fecha_llegada, Producto, Volumen_gal, Costo_galon, Proveedor |
| Precios del surtidor | Fecha_inicio, Producto, Precio_venta |
| Inventario inicial | Fecha, Producto, Stock_gal, Costo_promedio |

Al final de la página, en **Datos cargados actualmente**, puede ver qué hay en el sistema. Para empezar de cero use **⚠ Borrar todos los datos** (no se puede deshacer).

---

## Paso 3 — Mirar el resumen

Vaya a **🏠 Inicio**. Por cada producto verá:

- **Stock**: galones en el tanque y qué porcentaje está lleno.
- **Último precio de venta** y **costo FIFO actual**.
- **Margen actual**: cuánto gana sobre el costo real.
- **Alcanza para**: cuántos días durará el stock al ritmo de venta actual.

Abajo están las **alertas**: stock bajo, margen por debajo del mínimo y cambios de precio del proveedor que se acercan.

---

## Paso 4 — Registrar ventas y cisternas del día a día

**🧾 Ventas**: elija el producto y escriba los galones, el precio y la fecha y hora. Pulse **Registrar venta**. El sistema le dice el **costo FIFO** de esos galones y cuánto ganó.

**🚚 Compras**: cuando llega una cisterna, registre los galones, el costo por galón, la fecha de llegada y el proveedor.

Reglas que el sistema hace cumplir:
- No se puede vender más combustible del que hay en el tanque.
- No se puede recibir una cisterna que no quepa en el tanque.
- No se aceptan precios ni volúmenes negativos.
- Los movimientos deben ir en **orden de fecha** (FIFO lo necesita).

También puede subir muchas ventas o compras a la vez con el botón de importar de cada página.

---

## Paso 5 — Entender el inventario FIFO

Vaya a **🛢 Inventario**.

Cada fila de la tabla es una **cisterna que todavía tiene combustible**, con su propio costo. FIFO significa *"lo primero que entra es lo primero que sale"*: las ventas se descuentan **primero de la cisterna más antigua** (la de arriba).

**Ejemplo:** hay 2,000 gal que costaron S/ 22.50 y llegan 5,000 gal a S/ 23.10. Si vende 2,500 gal, el sistema toma 2,000 a S/ 22.50 y 500 a S/ 23.10. El costo real de esa venta es **S/ 22.62 por galón**, no S/ 23.10.

Así sabe su **costo real** y no fija el precio "a ojo".

---

## Paso 6 — ¿Cuándo cambiará el precio del proveedor? (Modelo 1)

Vaya a **⏰ Pronóstico (Modelo 1)**. Verá **un recuadro de color por producto**:

| Color | Significa | Qué hacer |
|---|---|---|
| 🟢 Verde | Faltan más de 7 días | No hay urgencia |
| 🟡 Amarillo | Faltan entre 3 y 7 días | Prepararse para ajustar precios |
| 🔴 Rojo | Faltan 0 a 2 días, o el cambio está retrasado | Revisar los precios **hoy** |

Cada recuadro dice:
- **EN X DÍAS → fecha**: cuándo se espera el próximo cambio. La fecha siempre es a futuro.
- **Probablemente SUBA / BAJE aproximadamente S/ X.XX/gal**: hacia dónde y cuánto.
- **Confianza**: **ALTA** si hay más de 15 cambios en el historial, **MEDIA** si hay de 8 a 15 y **BAJA** si hay menos de 8. Con confianza BAJA, use el pronóstico solo como referencia.

Si aparece *"⚠️ Según el patrón histórico, el cambio ya debería haber ocurrido"*, el proveedor está tardando más de lo normal y el cambio puede llegar en cualquier momento.

**Fecha actual**: normalmente es hoy. Puede cambiarla para simular qué habría dicho el sistema otro día.

En **Ver detalles técnicos ▼** están el gráfico del historial de precios, los parámetros del modelo y el error que tuvo en el pasado. No hace falta revisarlos para tomar decisiones.

---

## Paso 7 — ¿A qué precio vender? (Modelo 2)

Vaya a **💲 Precio óptimo (Modelo 2)**. Cada recuadro le da la decisión:

- **PRECIO RECOMENDADO**: el precio (terminado en 9, a la peruana) que deja la mayor utilidad.
- **Mantener este precio por X DÍAS**: hasta el próximo cambio estimado del proveedor (viene del Modelo 1). Ese día, vuelva a revisar.
- **Su costo actual (FIFO)**, **su margen** y la **utilidad diaria estimada**.
- **Comparación con márgenes fijos de 5 %, 8 % y 12 %**: cuánto ganaría más o menos y cuántos clientes perdería.

**Cómo decide el modelo:** si sube el precio, gana más por galón pero vende menos, porque algunos clientes se van a otro grifo. El modelo busca el punto de equilibrio respetando tres límites:
- el **margen mínimo** (por defecto 5 %),
- el **margen máximo** (por defecto 15 %),
- **no vender más combustible del que tiene** hasta la próxima cisterna.

Recuadro **verde** = todo en orden; **amarillo** = hay una advertencia (por ejemplo, el stock no alcanza); **rojo** = el margen está por debajo del mínimo.

> ⚠️ Las utilidades son estimaciones. Dependen de **κ (kappa)**, que mide qué tan sensibles son sus clientes al precio. En **Ver análisis completo ▼** puede probar otros valores de κ, ver la curva de utilidad y la tabla de sensibilidad.

---

## Paso 8 — Reportes

Vaya a **📈 Reportes**. Elija **Diario**, **Semanal** o **Mensual** y un producto.

- **Margen real**: calculado con el costo FIFO (lo que de verdad gana).
- **Margen esperado**: calculado con el costo de la última cisterna (lo que muchos administradores *creen* que ganan).

Si las dos líneas se separan, estaba vendiendo combustible comprado a otro precio sin darse cuenta.

Pulse **Preparar Excel del reporte** y luego **Descargar** para llevárselo a Excel.

---

## Paso 9 — Validación (para el artículo)

Vaya a **✅ Validación** y pulse **▶ Ejecutar validación**. Necesita haber cargado `VERDAD_OCULTA_simulacion.xlsx`.

- **Modelo 1**: en cada cambio de precio pasado, el modelo pronostica usando **solo los datos anteriores** y se mide cuánto se equivocó. Ese error se compara con el de usar el promedio simple.
- **Modelo 2**: se simulan los 6 meses con dos reglas de precio, **margen fijo 8 %** (lo habitual) y **precio óptimo**, con las mismas cisternas y la misma demanda. Así se ve cuál deja más utilidad.

Cada tabla trae una interpretación en lenguaje simple. Si el modelo **no** mejora algo, el sistema lo dice.

---

## Paso 10 — Exportar todo para el artículo

Vaya a **📊 Exportar artículo** y pulse **Generar exportación**. Cuando termine, pulse **⬇ Descargar exportaciones_articulo.zip**.

El ZIP contiene:

| Archivo | Para qué sección del artículo |
|---|---|
| `TABLAS_PARA_ARTICULO.xlsx` → Tabla 1: Estadísticas descriptivas | Planteamiento del problema |
| Tabla 2: Parámetros de los modelos | Metodología |
| Tabla 3: Resultados del Modelo 1 | Resultados |
| Tabla 4: Comparación de políticas | Resultados |
| Tabla 5: Resumen de conclusiones | Conclusiones |
| `graficos/fig01` a `fig06` (PNG a 300 DPI) | Figuras listas para insertar |
| `RESUMEN_RESULTADOS.txt` | Párrafos para copiar y pegar |

Cada tabla del Excel incluye título, notas, *"Fuente: Elaboración propia"* y un párrafo de interpretación.

---

## Paso 11 — Configuración

En **⚙ Configuración** puede cambiar la capacidad de los tanques, los márgenes mínimo y máximo, el margen fijo de comparación, κ por producto, el horizonte de planificación y el porcentaje para la alerta de stock bajo. Al guardar, todo se recalcula.

---

## Preguntas frecuentes

**¿Por qué el pronóstico dice "en 1 día" y está en rojo?**
Porque, según el historial, el cambio del proveedor ya debería haber ocurrido. Cargue precios más recientes para que el pronóstico se actualice.

**¿Por qué la confianza es BAJA?**
Hay pocos cambios de precio en el historial (menos de 8). Cargue más meses de datos.

**¿Se pierden los datos si cierro la página?**
No. Quedan guardados en el servidor hasta que alguien pulse *Borrar todos los datos*. (Si la app tiene configurada una base PostgreSQL, los datos sobreviven a los reinicios; abajo del menú dice "Datos guardados en PostgreSQL".)

**Importé y algunas ventas salieron "rechazadas".**
En ese momento no había stock suficiente (falta registrar una cisterna o el inventario inicial). El resumen de la importación dice cuántas fueron.

**¿Por qué el precio óptimo vende menos galones que el margen fijo?**
Porque gana más por galón. Es una decisión del negocio: el sistema muestra cuánto se gana y cuántos clientes se pierden para que usted elija.
