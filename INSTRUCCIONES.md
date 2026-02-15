# Gestión del Torneo de Fútbol — Guía de uso

## Tabla de contenidos
1. [Estructura del proyecto](#estructura-del-proyecto)
2. [Desarrollo local](#desarrollo-local)
3. [Crear un nuevo torneo](#crear-un-nuevo-torneo)
4. [Hacer cambios y subir a producción](#hacer-cambios-y-subir-a-producción)
5. [Migrar datos entre SQLite y Railway](#migrar-datos-entre-sqlite-y-railway)
6. [Conexión a la base de datos de Railway desde el Mac](#conexión-a-la-base-de-datos-de-railway-desde-el-mac)
7. [Variables de entorno](#variables-de-entorno)
8. [Comandos de emergencia](#comandos-de-emergencia)

---

## Estructura del proyecto

```
torneo_futbol/
├── app.py              # Aplicación Flask principal (modelos + rutas)
├── datos.py            # Script interactivo para crear torneos
├── migrar_datos.py     # Exportar/importar datos SQLite ↔ PostgreSQL
├── requirements.txt    # Dependencias Python
├── Procfile            # Comando de arranque para Railway (gunicorn)
├── torneo.db           # Base de datos local SQLite (no subir a git)
└── templates/          # Plantillas HTML
```

---

## Desarrollo local

### Primera vez (configurar el entorno)

```bash
cd ~/Desktop/torneo_futbol
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Activar el entorno virtual (cada vez que abres una terminal nueva)

```bash
cd ~/Desktop/torneo_futbol
source venv/bin/activate
```

Sabrás que está activo porque el prompt cambia a algo como:
```
(venv) alvaro@macbook-alvaro torneo_futbol %
```

Para desactivarlo cuando termines:
```bash
deactivate
```

### Arrancar el servidor local

```bash
# (con el venv activo)
python app.py
```

La app queda en: http://localhost:5001

Usa **SQLite local** (`torneo.db`) automáticamente si no hay `DATABASE_URL` definida.

---

## Crear un nuevo torneo

### En local (SQLite)

```bash
source venv/bin/activate
python datos.py
```

El script pregunta de forma interactiva:
- Nombre del torneo
- Número de grupos
- Equipos por grupo y sus nombres
- Hora de inicio y minutos entre partidos
- Número de campos
- Si habrá fase eliminatoria y/o consolación

Al final crea todos los grupos y partidos automáticamente.

### En Railway (PostgreSQL) — desde el Mac

```bash
source venv/bin/activate
DATABASE_URL="postgresql://postgres:<PASSWORD>@interchange.proxy.rlwy.net:18368/railway" python datos.py
```

> Sustituye `<PASSWORD>` por la contraseña real (ver sección Variables de entorno).

### Con `--reset` (borrar todo y empezar de cero)

```bash
# Local
python datos.py --reset

# Railway
DATABASE_URL="postgresql://..." python datos.py --reset
```

Pide confirmación antes de borrar. Útil para limpiar una BD de pruebas.

---

## Hacer cambios y subir a producción

Railway despliega automáticamente cada vez que hay un push a `main`.

```bash
git add .
git commit -m "Descripción del cambio"
git push origin main
```

Railway detecta el push, reinstala dependencias si cambia `requirements.txt` y reinicia el servidor con `gunicorn`.

---

## Migrar datos entre SQLite y Railway

Útil si tienes torneos en local y quieres llevarlos a producción, o viceversa.

### 1. Exportar datos locales a JSON

```bash
source venv/bin/activate
python migrar_datos.py exportar
```

Crea el fichero `backup_datos.json` en la carpeta del proyecto.

### 2. Importar el JSON en Railway

```bash
DATABASE_URL="postgresql://postgres:<PASSWORD>@interchange.proxy.rlwy.net:18368/railway" python migrar_datos.py importar
```

> **IMPORTANTE:** Solo funciona si la BD de Railway está vacía. Si ya tiene datos, el script lo detecta y no importa para evitar duplicados.

### Si necesitas reimportar (BD ya tiene datos)

Primero recrea las tablas vacías y luego importa:

```bash
# Paso 1: Recrear tablas vacías
DATABASE_URL="postgresql://postgres:<PASSWORD>@interchange.proxy.rlwy.net:18368/railway" python -c "
from app import app, db
with app.app_context():
    db.drop_all()
    db.create_all()
    print('Tablas recreadas')
"

# Paso 2: Importar
DATABASE_URL="postgresql://postgres:<PASSWORD>@interchange.proxy.rlwy.net:18368/railway" python migrar_datos.py importar
```

---

## Conexión a la base de datos de Railway desde el Mac

Railway tiene **dos URLs** para la base de datos:

| URL | Cuándo usarla |
|-----|---------------|
| `postgres.railway.internal` | Solo dentro de Railway (la app en producción) |
| `interchange.proxy.rlwy.net:18368` | Desde fuera (tu Mac, scripts locales) |

Siempre que ejecutes scripts en local contra Railway, usa la URL pública (`interchange.proxy.rlwy.net`).

### Ver las variables en Railway

1. Ir a [railway.com](https://railway.com)
2. Tu proyecto → servicio **web** → pestaña **Variables**
3. Ahí están `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`

La variable `DATABASE_PRIVATE_URL` también aparece — es la interna, no sirve desde el Mac.

---

## Variables de entorno

| Variable | Descripción | Valor en local | Valor en Railway |
|----------|-------------|----------------|------------------|
| `DATABASE_URL` | Conexión a la BD | No definida → usa SQLite | Lo pone Railway automáticamente |
| `SECRET_KEY` | Clave secreta Flask (sesiones) | `torneo-dev-secret-2024` (por defecto) | Una clave larga aleatoria |
| `ADMIN_PASSWORD` | Contraseña del panel admin | `admin1234` (por defecto) | La que hayas configurado |

> **En producción** cambia `SECRET_KEY` y `ADMIN_PASSWORD` por valores seguros desde el panel de Railway.

Para generar una `SECRET_KEY` segura:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Comandos de emergencia

### Ver qué hay en la BD de Railway

```bash
DATABASE_URL="postgresql://postgres:<PASSWORD>@interchange.proxy.rlwy.net:18368/railway" python -c "
from app import app, db, Torneo, Partido
with app.app_context():
    torneos = Torneo.query.all()
    for t in torneos:
        partidos = Partido.query.filter_by(torneo_id=t.id).count() if hasattr(Partido, 'torneo_id') else '?'
        print(f'Torneo {t.id}: {t.nombre}')
"
```

### Borrar todo en Railway (¡cuidado!)

```bash
DATABASE_URL="postgresql://postgres:<PASSWORD>@interchange.proxy.rlwy.net:18368/railway" python -c "
from app import app, db
with app.app_context():
    db.drop_all()
    db.create_all()
    print('BD limpia')
"
```

### Reiniciar el entorno local

```bash
rm torneo.db
python app.py  # Recrea la BD vacía al arrancar
```

### Railway CLI (opcional, para cuando tengas mala conexión web)

```bash
# Instalar
brew install railway

# Login
railway login

# Vincular al proyecto
railway link
# → Seleccionar workspace, proyecto y servicio

# Ver logs en tiempo real
railway logs

# Ejecutar un comando con las variables de Railway inyectadas
# OJO: inyecta DATABASE_URL interna, que solo funciona dentro de Railway
# Para scripts locales usa DATABASE_URL="..." directamente
railway run python datos.py
```
