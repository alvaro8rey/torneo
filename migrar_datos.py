"""
migrar_datos.py — Migración SQLite → PostgreSQL (Railway)
==========================================================

USO:

  1. EXPORTAR datos actuales (ejecutar en local antes de subir a Railway):
       python migrar_datos.py exportar

     Crea el fichero 'backup_datos.json' con todos los datos del torneo.

  2. IMPORTAR en Railway (ejecutar UNA SOLA VEZ tras el primer deploy):
       railway run python migrar_datos.py importar

     Lee 'backup_datos.json' e inserta los datos en la BD de destino
     (SQLite o PostgreSQL según DATABASE_URL).
"""

import json
import os
import sys

# ── Bootstrap de la app (sin levantar el servidor) ────────────────────────────
from app import app, db
from app import Torneo, Grupo, Partido, EventoGol, Goleador, ConfigCruce, ConfigGlobal

BACKUP_FILE = os.path.join(os.path.dirname(__file__), 'backup_datos.json')


# ── EXPORTAR ───────────────────────────────────────────────────────────────────

def exportar():
    with app.app_context():
        data = {
            'torneos':      [row2dict(t) for t in Torneo.query.all()],
            'grupos':       [row2dict(g) for g in Grupo.query.all()],
            'partidos':     [row2dict(p) for p in Partido.query.all()],
            'eventos_gol':  [row2dict(e) for e in EventoGol.query.all()],
            'goleadores':   [row2dict(g) for g in Goleador.query.all()],
            'config_cruces':[row2dict(c) for c in ConfigCruce.query.all()],
            'config_global':[row2dict(c) for c in ConfigGlobal.query.all()],
        }

    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in data.values())
    print(f"✓ Exportados {total} registros → {BACKUP_FILE}")
    for tabla, registros in data.items():
        print(f"  {tabla}: {len(registros)}")


# ── IMPORTAR ───────────────────────────────────────────────────────────────────

def importar():
    if not os.path.exists(BACKUP_FILE):
        print(f"✗ No se encuentra {BACKUP_FILE}")
        print("  Ejecuta primero: python migrar_datos.py exportar")
        sys.exit(1)

    with open(BACKUP_FILE, encoding='utf-8') as f:
        data = json.load(f)

    with app.app_context():
        db.create_all()

        # Comprobar que la BD está vacía para no duplicar datos
        if Torneo.query.first():
            print("✗ La base de datos ya tiene datos. No se importará para evitar duplicados.")
            print("  Si quieres reimportar, borra primero los datos manualmente.")
            sys.exit(1)

        print("Importando datos...")

        # Insertar en orden respetando las claves foráneas
        _bulk_insert(Torneo,      data['torneos'],       'torneos');      db.session.flush()
        _bulk_insert(Grupo,       data['grupos'],        'grupos');       db.session.flush()
        _bulk_insert(Partido,     data['partidos'],      'partidos');     db.session.flush()
        _bulk_insert(EventoGol,   data['eventos_gol'],   'eventos_gol');  db.session.flush()
        _bulk_insert(Goleador,    data['goleadores'],    'goleadores');   db.session.flush()
        _bulk_insert(ConfigCruce, data['config_cruces'], 'config_cruces');db.session.flush()
        _bulk_insert(ConfigGlobal,data['config_global'], 'config_global');db.session.flush()

        db.session.commit()

        # Sincronizar las secuencias de ID en PostgreSQL
        _reset_sequences()

        print("✓ Importación completada")


def _bulk_insert(model, rows, nombre):
    if not rows:
        print(f"  {nombre}: 0 registros (vacío)")
        return
    for row in rows:
        db.session.add(model(**row))
    print(f"  {nombre}: {len(rows)} registros")


def _reset_sequences():
    """
    En PostgreSQL los IDs se gestionan con secuencias. Tras una inserción
    manual con IDs explícitos hay que actualizarlas para que el próximo
    INSERT auto-incremente correctamente.
    """
    from sqlalchemy import inspect as sa_inspect
    url = str(db.engine.url)
    if not url.startswith('postgresql'):
        return  # SQLite no necesita esto

    tablas = {
        'torneo':       'torneo_id_seq',
        'grupo':        'grupo_id_seq',
        'partido':      'partido_id_seq',
        'evento_gol':   'evento_gol_id_seq',
        'goleador':     'goleador_id_seq',
        'config_cruce': 'config_cruce_id_seq',
        'config_global':'config_global_id_seq',
    }
    with db.engine.connect() as conn:
        for tabla, seq in tablas.items():
            try:
                conn.execute(
                    db.text(f"SELECT setval('{seq}', COALESCE(MAX(id),1)) FROM {tabla}")
                )
                conn.commit()
            except Exception:
                pass  # Si la tabla/secuencia no existe, ignorar
    print("  Secuencias PostgreSQL actualizadas")


# ── HELPERS ────────────────────────────────────────────────────────────────────

def row2dict(row):
    """Convierte un objeto SQLAlchemy en dict serializable."""
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


# ── MAIN ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('exportar', 'importar'):
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == 'exportar':
        exportar()
    else:
        importar()
