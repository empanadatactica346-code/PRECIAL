# 🚀 Cómo publicar PRECIAL en internet con Railway

Al terminar, PRECIAL tendrá una dirección web (por ejemplo `https://precial.up.railway.app`) que cualquiera puede abrir desde la computadora, la tablet o el celular, entrando con **un solo usuario y contraseña**.

Tiempo aproximado: **15 minutos**. No necesita instalar nada en su computadora.

---

## 0. Lo que necesita

- La cuenta de GitHub donde está el código: `https://github.com/Elturbius12/PRECIAL`
- Una cuenta en **Railway** (https://railway.com). Puede crearla con su cuenta de GitHub.
- **Costo:** Railway ofrece un período de prueba gratuito. Después, una app pequeña como esta cuesta unos pocos dólares al mes en el plan *Hobby* (revise el precio vigente en https://railway.com/pricing).

---

## 1. Crear el proyecto en Railway

1. Entre a https://railway.com y pulse **Login** → **Login with GitHub**.
2. Pulse **New Project** → **Deploy from GitHub repo**.
3. Si es la primera vez, pulse **Configure GitHub App** y dele acceso al repositorio **PRECIAL**.
4. Elija **Elturbius12/PRECIAL**.

Railway detecta solo que es una app de Python y empieza a construirla. Las instrucciones de arranque ya están en el archivo `railway.json`, así que no tiene que configurar nada más aquí.

> El primer intento puede fallar o mostrar *"Falta configurar APP_USUARIO y APP_CLAVE"*. Es normal: eso se arregla en el paso 2.

---

## 2. Crear el usuario y la contraseña (OBLIGATORIO)

1. En Railway, haga clic en el servicio **PRECIAL** (el recuadro del proyecto).
2. Abra la pestaña **Variables**.
3. Pulse **New Variable** y agregue estas tres:

| Nombre | Valor | Para qué |
|---|---|---|
| `APP_USUARIO` | el usuario que quiera, ej. `grifo` | Usuario de acceso |
| `APP_CLAVE` | una contraseña segura, ej. `Precial-2026!` | Contraseña de acceso |
| `GRIFO_DATOS` | `/data` | Carpeta donde se guardan los datos (ver paso 3) |

4. Railway vuelve a desplegar la app solo.

> 🔒 La contraseña **no** está en el código ni en GitHub: solo existe en Railway. Para cambiarla, edite `APP_CLAVE` y espere a que la app se redespliegue.

---

## 3. Crear el disco para que los datos NO se borren (MUY IMPORTANTE)

Sin este paso, **cada vez que se actualiza la app se borran las ventas, compras y configuración**.

1. En el proyecto de Railway, haga **clic derecho** sobre el servicio PRECIAL (o use el botón **+ Create** / la paleta de comandos con `Ctrl + K`) y elija **Volume** / **Attach Volume**.
2. En **Mount path** escriba exactamente: `/data`
3. Confirme. Railway reinicia la app.

Desde ahora, todo lo que se importe o registre queda guardado en ese disco, aunque la app se reinicie o se actualice.

---

## 4. Obtener la dirección web

1. En el servicio PRECIAL, vaya a **Settings** → sección **Networking**.
2. Pulse **Generate Domain**.
3. Railway le da una dirección como `https://precial-production.up.railway.app`. Puede editar la primera parte para que quede algo como `precial.up.railway.app` (si está libre).

**Esa es la dirección que comparte con los demás usuarios.** Ábrala, ingrese con el usuario y la contraseña del paso 2 y vaya a **📂 Importar datos** para subir sus Excel.

---

## 5. (Opcional) Usar un dominio propio, ej. `www.precial.com`

Primero hay que **comprar el dominio** en un registrador (Namecheap, GoDaddy, Cloudflare, Punto.pe para `.pe`, etc.). Cuesta aproximadamente entre 10 y 40 dólares al año.

1. En Railway: **Settings → Networking → Custom Domain** y escriba su dominio, ej. `www.precial.com`.
2. Railway le muestra un registro **CNAME** (y a veces un registro **TXT** de verificación) con un valor como `xxxx.up.railway.app`.
3. Entre al panel de su registrador de dominio → **DNS** → agregue los registros **exactamente** como los muestra Railway.
4. Espere de unos minutos a unas horas. Cuando Railway muestre el dominio con ✅, ya funciona con **https** (el certificado de seguridad es automático y gratuito).

> Para usar el dominio sin `www` (solo `precial.com`), su registrador debe permitir *CNAME flattening* o registros *ALIAS* (Cloudflare lo permite). Si no, use `www.precial.com`.

---

## 6. Cómo se actualiza la app

Cada vez que se sube un cambio al repositorio de GitHub (rama `main`), Railway **vuelve a desplegar solo**. Los datos se conservan gracias al disco del paso 3.

---

## Problemas frecuentes

| Problema | Solución |
|---|---|
| La página dice *"Falta configurar APP_USUARIO y APP_CLAVE"* | Haga el paso 2. |
| Los datos desaparecen después de actualizar | Falta el disco del paso 3, o `GRIFO_DATOS` no es igual a la ruta del disco (`/data`). |
| *Application failed to respond* | Abra **Deployments → View logs**. Espere a que termine la construcción (la primera tarda de 3 a 5 minutos). |
| La importación del Excel grande tarda | Es normal con más de 100 mil ventas (alrededor de 1 minuto). No cierre la página. |
| Olvidé la contraseña | Railway → Variables → vea o cambie `APP_CLAVE`. |

---

## Probarla en su computadora (opcional)

```bash
pip install -r requirements.txt
streamlit run app_web.py
```

Se abre en `http://localhost:8501`. Sin variables configuradas, el acceso local es usuario `admin` y contraseña `admin`. Ese acceso por defecto **no funciona en Railway**.

---

# Alternativa: publicar en Render

Mismos pasos, otro panel (https://render.com → New → Web Service → repo PRECIAL):

| Campo | Valor |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0 --server.headless true` |
| Plan | Starter ($7/mes). El plan Free no tiene disco persistente y se duerme. |
| Variables | `APP_USUARIO`, `APP_CLAVE`, `GRIFO_DATOS=/data`, `PYTHON_VERSION=3.12.8` |
| Health Check Path | `/_stcore/health` |
| Disk | Mount Path `/data`, 1 GB (obligatorio para no perder los datos) |

El dominio propio se agrega en **Settings → Custom Domains**.

---

# Guardar los datos en una base PostgreSQL gratuita (recomendado en Render Free)

Con esto las ventas, compras, configuración y datos importados **sobreviven a los reinicios**, sin pagar disco. La app lo activa sola cuando existe la variable `DATABASE_URL`.

## Opción A — Neon (gratis, no vence) ✅ recomendada

1. Entre a https://neon.tech → **Sign up** (con GitHub).
2. Cree un proyecto (nombre `precial`, región la más cercana, ej. *US East*).
3. En el panel, pulse **Connect** y copie la cadena de conexión (empieza con `postgresql://...`).
4. En Render → su servicio → **Environment** → agregue:
   `DATABASE_URL` = la cadena copiada
5. Guarde. Render vuelve a desplegar.

## Opción B — PostgreSQL de Render (gratis, pero se borra a los 30 días)

1. Render → **New → PostgreSQL** → plan **Free**.
2. Cuando esté lista, copie la **Internal Database URL** (si ambos servicios están en la misma región) o la External.
3. En el servicio web → **Environment** → `DATABASE_URL` = esa URL.

> ⚠ La base gratuita de Render **expira a los 30 días** y luego se elimina. Si usa esta opción, anote la fecha o use Neon.

## Cómo comprobar que funciona

En el menú lateral de la app, debajo de la fecha, debe decir **"💾 Datos guardados en PostgreSQL"**. Si dice "archivos locales", falta `DATABASE_URL`; si dice "error", el mensaje indica el motivo (casi siempre una URL mal copiada).

Prueba definitiva: importe los Excel, pulse en Render **Manual Deploy → Deploy latest commit**, y vuelva a entrar: los datos deben seguir ahí.

> Con la base de datos configurada ya **no** necesita la carpeta `datos_iniciales` ni el disco de pago; no ponga `GRIFO_DATOS`.
