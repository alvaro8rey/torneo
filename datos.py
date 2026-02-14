from app import app, db, Torneo, Grupo, Partido, EventoGol, Goleador
import os

def cargar():
    with app.app_context():
        try:
            db.create_all()
            # Limpiar datos previos para evitar duplicados o conflictos
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

        # Crear el Torneo
        t = Torneo(nombre="TORNEO CARNAVAL ALEVÍN F8 CATOIRA SD")
        db.session.add(t)
        db.session.commit()

        # Configuración de Grupos y Equipos
        # Mantenemos los nombres originales para que las plantillas los reconozcan
        grupos_data = {
            "A": "CATOIRA S.D., CROCHA CF, BARRO CF, XUVENTU AGUIÑO",
            "B": "CALDAS CF, RIVEIRA CF, CD ROIS, PORTONOVO SD",
            "C": "AROSA SC, EFM BOIRO, AT CUNTIS CF, VILAGARCIA SD A",
            "D": "CD ESTRADENSE, CD PORTAS, VILAGARCIA SD B, CD BAMIO",
            "Eliminatorias Título": "Fase Final Oro",
            "Eliminatorias Consolación": "Fase Final Plata",
            "Semifinales Título": "Semis Oro",
            "Semifinales Consolación": "Semis Plata",
            "Final Título": "Final Oro",
            "Final Consolación": "Final Plata"
        }

        g_objs = {}
        for clave, equipos in grupos_data.items():
            # Si es una sola letra (A, B, C, D), le ponemos "Grupo " delante
            nombre_mostrar = f"Grupo {clave}" if len(clave) == 1 else clave
            g = Grupo(nombre=nombre_mostrar, equipos=equipos, torneo_id=t.id)
            db.session.add(g)
            db.session.commit()
            g_objs[clave] = g

        # --- 1. PARTIDOS FASE DE GRUPOS ---
        partidos_fase = [
            ("A", "CATOIRA S.D.", "CROCHA CF", 1, "9:00"),
            ("A", "BARRO CF", "XUVENTU AGUIÑO", 2, "9:00"),
            ("B", "CALDAS CF", "RIVEIRA CF", 1, "9:25"),
            ("B", "CD ROIS", "PORTONOVO SD", 2, "9:25"),
            ("C", "AROSA SC", "EFM BOIRO", 1, "9:50"),
            ("C", "AT CUNTIS CF", "VILAGARCIA SD A", 2, "9:50"),
            ("D", "CD ESTRADENSE", "CD PORTAS", 1, "10:15"),
            ("D", "VILAGARCIA SD B", "CD BAMIO", 2, "10:15"),
            ("A", "CATOIRA S.D.", "BARRO CF", 1, "10:40"),
            ("A", "CROCHA CF", "XUVENTU AGUIÑO", 2, "10:40"),
            ("B", "CALDAS CF", "CD ROIS", 1, "11:05"),
            ("B", "RIVEIRA CF", "PORTONOVO SD", 2, "11:05"),
            ("C", "AROSA SC", "AT CUNTIS CF", 1, "11:30"),
            ("C", "EFM BOIRO", "VILAGARCIA SD A", 2, "11:30"),
            ("D", "CD ESTRADENSE", "VILAGARCIA SD B", 1, "11:55"),
            ("D", "CD PORTAS", "CD BAMIO", 2, "11:55"),
            ("A", "CATOIRA S.D.", "XUVENTU AGUIÑO", 1, "12:20"),
            ("A", "CROCHA CF", "BARRO CF", 2, "12:20"),
            ("B", "CALDAS CF", "PORTONOVO SD", 1, "12:45"),
            ("B", "RIVEIRA CF", "CD ROIS", 2, "12:45"),
            ("C", "AROSA SC", "VILAGARCIA SD A", 1, "13:10"),
            ("C", "EFM BOIRO", "AT CUNTIS CF", 2, "13:10"),
            ("D", "CD ESTRADENSE", "CD BAMIO", 1, "13:35"),
            ("D", "CD PORTAS", "VILAGARCIA SD B", 2, "13:35")
        ]

        for g_clave, e1, e2, campo, hora in partidos_fase:
            p = Partido(equipo1=e1, equipo2=e2, grupo_id=g_objs[g_clave].id, numero_campo=campo, hora=hora)
            db.session.add(p)

        # --- 2. ELIMINATORIAS Y FASES FINALES ---
        # Separamos Oro y Plata por sus nombres de grupo correspondientes
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
            ("Final Consolación", "GANADOR SC-1", "GANADOR SC-2", 2, "18:30", "F-PLATA")
        ]

        for g_clave, e1, e2, campo, hora, codigo in partidos_finales:
            p = Partido(equipo1=e1, equipo2=e2, grupo_id=g_objs[g_clave].id, numero_campo=campo, hora=hora, codigo_partido=codigo)
            db.session.add(p)
        
        db.session.commit()
        print("¡Calendario restaurado y corregido! Nombres compatibles con las vistas.")

if __name__ == "__main__":
    cargar()