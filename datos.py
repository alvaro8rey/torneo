from app import app, db, Torneo, Grupo, Partido, EventoGol, Goleador
import sys

def cargar(nombre_torneo=None, reset=False):
    """
    Carga un torneo nuevo con la estructura estándar F8.
    - nombre_torneo: nombre del torneo (se pregunta si no se pasa)
    - reset: si True, borra TODOS los torneos antes de insertar (usar con precaución)
    """
    with app.app_context():
        db.create_all()

        if reset:
            try:
                EventoGol.query.delete()
                Goleador.query.delete()
                Partido.query.delete()
                Grupo.query.delete()
                Torneo.query.delete()
                db.session.commit()
                print("Tablas limpiadas correctamente.")
            except Exception as e:
                db.session.rollback()
                print(f"Error al limpiar las tablas: {e}")
                return

        if not nombre_torneo:
            nombre_torneo = input("Nombre del torneo: ").strip()
            if not nombre_torneo:
                print("Nombre vacío. Operación cancelada.")
                return

        # Crear el Torneo
        t = Torneo(nombre=nombre_torneo)
        db.session.add(t)
        db.session.commit()
        print(f"Torneo '{t.nombre}' creado con ID={t.id}")

        # Configuración de Grupos y Equipos
        grupos_data = {
            "A": "EQUIPO A1, EQUIPO A2, EQUIPO A3, EQUIPO A4",
            "B": "EQUIPO B1, EQUIPO B2, EQUIPO B3, EQUIPO B4",
            "C": "EQUIPO C1, EQUIPO C2, EQUIPO C3, EQUIPO C4",
            "D": "EQUIPO D1, EQUIPO D2, EQUIPO D3, EQUIPO D4",
            "Eliminatorias Título": "Fase Final Oro",
            "Eliminatorias Consolación": "Fase Final Plata",
            "Semifinales Título": "Semis Oro",
            "Semifinales Consolación": "Semis Plata",
            "Final Título": "Final Oro",
            "Final Consolación": "Final Plata"
        }

        g_objs = {}
        for clave, equipos in grupos_data.items():
            nombre_mostrar = f"Grupo {clave}" if len(clave) == 1 else clave
            g = Grupo(nombre=nombre_mostrar, equipos=equipos, torneo_id=t.id)
            db.session.add(g)
            db.session.commit()
            g_objs[clave] = g

        # --- 1. PARTIDOS FASE DE GRUPOS (horario estándar F8) ---
        partidos_fase = [
            ("A", "EQUIPO A1", "EQUIPO A2", 1, "9:00"),
            ("A", "EQUIPO A3", "EQUIPO A4", 2, "9:00"),
            ("B", "EQUIPO B1", "EQUIPO B2", 1, "9:25"),
            ("B", "EQUIPO B3", "EQUIPO B4", 2, "9:25"),
            ("C", "EQUIPO C1", "EQUIPO C2", 1, "9:50"),
            ("C", "EQUIPO C3", "EQUIPO C4", 2, "9:50"),
            ("D", "EQUIPO D1", "EQUIPO D2", 1, "10:15"),
            ("D", "EQUIPO D3", "EQUIPO D4", 2, "10:15"),
            ("A", "EQUIPO A1", "EQUIPO A3", 1, "10:40"),
            ("A", "EQUIPO A2", "EQUIPO A4", 2, "10:40"),
            ("B", "EQUIPO B1", "EQUIPO B3", 1, "11:05"),
            ("B", "EQUIPO B2", "EQUIPO B4", 2, "11:05"),
            ("C", "EQUIPO C1", "EQUIPO C3", 1, "11:30"),
            ("C", "EQUIPO C2", "EQUIPO C4", 2, "11:30"),
            ("D", "EQUIPO D1", "EQUIPO D3", 1, "11:55"),
            ("D", "EQUIPO D2", "EQUIPO D4", 2, "11:55"),
            ("A", "EQUIPO A1", "EQUIPO A4", 1, "12:20"),
            ("A", "EQUIPO A2", "EQUIPO A3", 2, "12:20"),
            ("B", "EQUIPO B1", "EQUIPO B4", 1, "12:45"),
            ("B", "EQUIPO B2", "EQUIPO B3", 2, "12:45"),
            ("C", "EQUIPO C1", "EQUIPO C4", 1, "13:10"),
            ("C", "EQUIPO C2", "EQUIPO C3", 2, "13:10"),
            ("D", "EQUIPO D1", "EQUIPO D4", 1, "13:35"),
            ("D", "EQUIPO D2", "EQUIPO D3", 2, "13:35"),
        ]

        for g_clave, e1, e2, campo, hora in partidos_fase:
            p = Partido(equipo1=e1, equipo2=e2, grupo_id=g_objs[g_clave].id, numero_campo=campo, hora=hora)
            db.session.add(p)

        # --- 2. ELIMINATORIAS Y FASES FINALES ---
        partidos_finales = [
            # Título (Oro)
            ("Eliminatorias Título", "1º GRUPO A", "2º GRUPO B", 1, "15:00", "E-1"),
            ("Eliminatorias Título", "1º GRUPO B", "2º GRUPO A", 1, "15:25", "E-2"),
            ("Eliminatorias Título", "1º GRUPO C", "2º GRUPO D", 1, "15:50", "E-3"),
            ("Eliminatorias Título", "1º GRUPO D", "2º GRUPO C", 1, "16:15", "E-4"),
            ("Semifinales Título", "GANADOR E-1", "GANADOR E-2", 1, "16:40", "S-1"),
            ("Semifinales Título", "GANADOR E-3", "GANADOR E-4", 1, "17:20", "S-2"),
            ("Final Título", "GANADOR S-1", "GANADOR S-2", 1, "19:00", "F-ORO"),

            # Consolación (Plata)
            ("Eliminatorias Consolación", "3º GRUPO A", "4º GRUPO B", 2, "15:00", "EC-1"),
            ("Eliminatorias Consolación", "3º GRUPO B", "4º GRUPO A", 2, "15:25", "EC-2"),
            ("Eliminatorias Consolación", "3º GRUPO C", "4º GRUPO D", 2, "15:50", "EC-3"),
            ("Eliminatorias Consolación", "3º GRUPO D", "4º GRUPO C", 2, "16:15", "EC-4"),
            ("Semifinales Consolación", "GANADOR EC-1", "GANADOR EC-2", 2, "16:40", "SC-1"),
            ("Semifinales Consolación", "GANADOR EC-3", "GANADOR EC-4", 2, "17:20", "SC-2"),
            ("Final Consolación", "GANADOR SC-1", "GANADOR SC-2", 2, "18:30", "F-PLATA"),
        ]

        for g_clave, e1, e2, campo, hora, codigo in partidos_finales:
            p = Partido(equipo1=e1, equipo2=e2, grupo_id=g_objs[g_clave].id, numero_campo=campo, hora=hora, codigo_partido=codigo)
            db.session.add(p)

        db.session.commit()
        print(f"Torneo '{nombre_torneo}' cargado correctamente con {len(partidos_fase)} partidos de grupos y {len(partidos_finales)} de eliminatoria.")
        print(f"Recuerda editar los equipos y la configuración de cruces desde la interfaz web.")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    if reset:
        confirmar = input("⚠️  ATENCIÓN: --reset borrará TODOS los torneos existentes. ¿Continuar? (s/N): ")
        if confirmar.lower() != "s":
            print("Operación cancelada.")
            sys.exit(0)
    cargar(reset=reset)
