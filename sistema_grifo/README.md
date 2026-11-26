# ⛽ PRECIAL — Gestión y optimización de precios para grifo

Software del curso **Modelos Cuantitativos y de Optimización** para una estación de combustible que vende **DB5** (Diésel B5), **GR** (Gasolina Regular 90) y **GP** (Gasolina Premium 95).

| Componente | Qué resuelve |
|---|---|
| **Inventario FIFO** | Conocer el costo real de cada galón vendido cuando en el tanque hay combustible comprado a distintos precios |
| **Modelo 1 — Croston TSB** | Pronosticar cuándo cambiará el precio del proveedor y si subirá o bajará |
| **Modelo 2 — Precio óptimo** | Calcular el precio de venta que maximiza la utilidad con restricciones de margen y stock |
| **Validación y exportación** | Backtest contra la verdad oculta, comparación de políticas y tablas y gráficos listos para el artículo |

## 📘 Documentación

- **[TUTORIAL.md](TUTORIAL.md)** — cómo usar la app paso a paso (también se ve dentro de la web, en la página *Tutorial*)
- **[DESPLIEGUE_RAILWAY.md](DESPLIEGUE_RAILWAY.md)** — cómo publicarla en internet con Railway, usuario y contraseña, disco persistente y dominio propio

## Versión web (recomendada)

```bash
pip install -r requirements.txt
streamlit run app_web.py
```

## Versión de escritorio (Windows)

```bash
pip install -r requisitos.txt
python principal.py
```

## Estructura

```
app_web.py              # App web (Streamlit) — la que corre en Railway
principal.py            # App de escritorio (customtkinter)
configuracion.py        # Parámetros (carpeta de datos configurable con GRIFO_DATOS)
modelos/                # FIFO, Croston TSB, precio óptimo y validación
datos/                  # Importación, persistencia en CSV y validación de datos
exportador/             # 5 tablas Excel, 6 gráficos PNG 300 DPI y resumen en texto
utilidades/             # Formatos, redondeo peruano (XX.X9) y tarjetas de decisión
interfaz/               # Pantallas de escritorio
railway.json            # Comando de arranque y verificación de salud para Railway
```

### Variables de entorno (web)

| Variable | Uso |
|---|---|
| `APP_USUARIO` / `APP_CLAVE` | Única cuenta de acceso (obligatorias en Railway) |
| `GRIFO_DATOS` | Carpeta persistente de datos (en Railway: `/data`, montada como volumen) |
| `TZ_GRIFO` | Zona horaria (por defecto `America/Lima`) |
