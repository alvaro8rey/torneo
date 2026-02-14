from app import app, db, Torneo, Grupo, Partido, EventoGol, Goleador
import sys
import itertools


def preguntar_entero(mensaje, default=None, minimo=1, maximo=None):
    while True:
        sufijo = f" [{default}]" if default is not None else ""
        entrada = input(f"{mensaje}{sufijo}: ").strip()
        if entrada == "" and default is not None:
            return default
        try:
            valor = int(entrada)
            if valor < minimo:
                print(f"  → Debe ser al menos {minimo}.")
                continue
            if maximo is not None and valor > maximo:
                print(f"  → Debe ser como máximo {maximo}.")
                continue
            return valor
        except ValueError:
            print("  → Introduce un número entero.")


def preguntar_hora(mensaje, default="9:00"):
    while True:
        entrada = input(f"{mensaje} [{default}]: ").strip() or default
        partes = entrada.split(":")
        if len(partes) == 2:
            try:
                h, m = int(partes[0]), int(partes[1])
                if 0 <= h <= 23 and 0 <= m <= 59:
                    return f"{h}:{m:02d}"
            except ValueError:
                pass
        print("  → Formato de hora incorrecto. Usa HH:MM, por ejemplo 9:00 o 15:30.")


def siguiente_hora(hora_str, minutos):
    h, m = map(int, hora_str.split(":"))
    total = h * 60 + m + minutos
    return f"{total // 60}:{total % 60:02d}"


def generar_partidos_liga(equipos):
    """Genera todos los partidos de liga (todos contra todos) de un grupo."""
    return list(itertools.combinations(equipos, 2))


def cargar():
    with app.app_context():
        db.create_all()

        print("\n" + "="*50)
        print("   CREAR NUEVO TORNEO")
        print("="*50 + "\n")

        # --- NOMBRE DEL TORNEO ---
        while True:
            nombre_torneo = input("Nombre del torneo: ").strip()
            if nombre_torneo:
                break
            print("  → El nombre no puede estar vacío.")

        # --- ESTRUCTURA DEL TORNEO ---
        print()
        num_grupos = preguntar_entero("¿Cuántos grupos habrá?", default=4, minimo=2, maximo=8)

        # ¿Todos los grupos tienen el mismo número de equipos?
        mismos_equipos = input("¿Todos los grupos tienen el mismo número de equipos? (S/n) [S]: ").strip().lower()
        mismos_equipos = mismos_equipos != "n"

        equipos_por_grupo_default = 4
        if mismos_equipos:
            equipos_por_grupo_default = preguntar_entero(
                "¿Cuántos equipos por grupo?", default=4, minimo=2, maximo=8
            )

        # --- HORARIO ---
        print()
        print("--- Configuración de horario ---")
        hora_inicio = preguntar_hora("Hora de inicio de la fase de grupos", default="9:00")
        intervalo = preguntar_entero("Minutos entre partidos", default=25, minimo=5, maximo=120)
        num_campos = preguntar_entero("¿Cuántos campos de juego hay?", default=2, minimo=1, maximo=4)

        # --- EQUIPOS ---
        print()
        print("--- Equipos por grupo ---")
        print("(Pulsa Enter sin escribir nada para usar un placeholder)\n")

        letras_grupos = [chr(ord('A') + i) for i in range(num_grupos)]
        equipos_grupos = {}

        for letra in letras_grupos:
            print(f"  Grupo {letra}:")
            if mismos_equipos:
                n_equipos = equipos_por_grupo_default
            else:
                n_equipos = preguntar_entero(f"  ¿Cuántos equipos en el Grupo {letra}?", default=4, minimo=2, maximo=8)

            equipos = []
            for i in range(1, n_equipos + 1):
                nombre_eq = input(f"    Equipo {i}: ").strip()
                if not nombre_eq:
                    nombre_eq = f"EQUIPO {letra}{i}"
                equipos.append(nombre_eq.upper())
            equipos_grupos[letra] = equipos
            print()

        # --- ELIMINATORIAS ---
        print("--- Fase eliminatoria ---")
        hay_eliminatorias = input("¿Habrá fase eliminatoria? (S/n) [S]: ").strip().lower()
        hay_eliminatorias = hay_eliminatorias != "n"

        hay_consolacion = False
        hora_inicio_elim = "15:00"
        intervalo_elim = 25

        if hay_eliminatorias:
            hay_consolacion = input("¿Habrá fase de consolación (Plata)? (S/n) [S]: ").strip().lower()
            hay_consolacion = hay_consolacion != "n"
            hora_inicio_elim = preguntar_hora("Hora de inicio de eliminatorias", default="15:00")
            intervalo_elim = preguntar_entero("Minutos entre partidos eliminatorios", default=25, minimo=5, maximo=120)

        # =============================================
        # CREAR EN BASE DE DATOS
        # =============================================
        print("\nCreando torneo en la base de datos...")

        t = Torneo(nombre=nombre_torneo)
        db.session.add(t)
        db.session.commit()

        g_objs = {}

        # Grupos de fase regular
        for letra in letras_grupos:
            equipos_str = ", ".join(equipos_grupos[letra])
            g = Grupo(nombre=f"Grupo {letra}", equipos=equipos_str, torneo_id=t.id)
            db.session.add(g)
            db.session.commit()
            g_objs[letra] = g

        # Grupos de fase eliminatoria
        if hay_eliminatorias:
            fases_oro = ["Eliminatorias Título", "Semifinales Título", "Final Título"]
            fases_plata = ["Eliminatorias Consolación", "Semifinales Consolación", "Final Consolación"]

            for nombre_fase in fases_oro:
                g = Grupo(nombre=nombre_fase, equipos="Fase Oro", torneo_id=t.id)
                db.session.add(g)
                db.session.commit()
                g_objs[nombre_fase] = g

            if hay_consolacion:
                for nombre_fase in fases_plata:
                    g = Grupo(nombre=nombre_fase, equipos="Fase Plata", torneo_id=t.id)
                    db.session.add(g)
                    db.session.commit()
                    g_objs[nombre_fase] = g

        # --- GENERAR PARTIDOS DE FASE DE GRUPOS ---
        hora_actual = hora_inicio
        total_partidos_grupos = 0

        # Organizar por rondas (todos los grupos juegan en paralelo)
        rondas_por_grupo = {letra: generar_partidos_liga(equipos_grupos[letra]) for letra in letras_grupos}
        max_rondas = max(len(r) for r in rondas_por_grupo.values())

        for ronda_idx in range(max_rondas):
            campo_actual = 1
            for letra in letras_grupos:
                rondas = rondas_por_grupo[letra]
                if ronda_idx < len(rondas):
                    e1, e2 = rondas[ronda_idx]
                    p = Partido(
                        equipo1=e1, equipo2=e2,
                        grupo_id=g_objs[letra].id,
                        numero_campo=campo_actual,
                        hora=hora_actual
                    )
                    db.session.add(p)
                    total_partidos_grupos += 1
                    campo_actual = (campo_actual % num_campos) + 1
                    if campo_actual == 1:
                        hora_actual = siguiente_hora(hora_actual, intervalo)
            # Si cambiamos de ronda completa y no hemos avanzado hora todavía
            if num_campos >= num_grupos:
                hora_actual = siguiente_hora(hora_actual, intervalo)

        # --- GENERAR PARTIDOS ELIMINATORIOS ---
        total_partidos_elim = 0
        if hay_eliminatorias:
            hora_e = hora_inicio_elim
            campo_e = 1

            def nuevo_partido_elim(grupo_clave, e1, e2, campo, hora, codigo):
                nonlocal total_partidos_elim
                p = Partido(
                    equipo1=e1, equipo2=e2,
                    grupo_id=g_objs[grupo_clave].id,
                    numero_campo=campo,
                    hora=hora,
                    codigo_partido=codigo
                )
                db.session.add(p)
                total_partidos_elim += 1

            # Cuartos de final: 1 por par de grupos
            codigos_elim = []
            codigos_cons = []

            pares_grupos = [(letras_grupos[i], letras_grupos[i+1]) for i in range(0, len(letras_grupos)-1, 2)]

            for idx, (g1, g2) in enumerate(pares_grupos):
                cod_oro = f"E-{idx*2+1}"
                cod_oro2 = f"E-{idx*2+2}"
                nuevo_partido_elim("Eliminatorias Título", f"1º GRUPO {g1}", f"2º GRUPO {g2}", campo_e, hora_e, cod_oro)
                codigos_elim.append(cod_oro)
                campo_e = (campo_e % num_campos) + 1
                if campo_e == 1:
                    hora_e = siguiente_hora(hora_e, intervalo_elim)

                nuevo_partido_elim("Eliminatorias Título", f"1º GRUPO {g2}", f"2º GRUPO {g1}", campo_e, hora_e, cod_oro2)
                codigos_elim.append(cod_oro2)
                campo_e = (campo_e % num_campos) + 1
                if campo_e == 1:
                    hora_e = siguiente_hora(hora_e, intervalo_elim)

                if hay_consolacion:
                    cod_plata = f"EC-{idx*2+1}"
                    cod_plata2 = f"EC-{idx*2+2}"
                    nuevo_partido_elim("Eliminatorias Consolación", f"3º GRUPO {g1}", f"4º GRUPO {g2}", campo_e, hora_e, cod_plata)
                    codigos_cons.append(cod_plata)
                    campo_e = (campo_e % num_campos) + 1
                    if campo_e == 1:
                        hora_e = siguiente_hora(hora_e, intervalo_elim)

                    nuevo_partido_elim("Eliminatorias Consolación", f"3º GRUPO {g2}", f"4º GRUPO {g1}", campo_e, hora_e, cod_plata2)
                    codigos_cons.append(cod_plata2)
                    campo_e = (campo_e % num_campos) + 1
                    if campo_e == 1:
                        hora_e = siguiente_hora(hora_e, intervalo_elim)

            hora_e = siguiente_hora(hora_e, intervalo_elim)

            # Semifinales y finales Oro
            semis_oro = []
            for i in range(0, len(codigos_elim), 2):
                cod_semi = f"S-{i//2+1}"
                nuevo_partido_elim(
                    "Semifinales Título",
                    f"GANADOR {codigos_elim[i]}", f"GANADOR {codigos_elim[i+1]}",
                    1, hora_e, cod_semi
                )
                semis_oro.append(cod_semi)
                hora_e = siguiente_hora(hora_e, intervalo_elim)

            if len(semis_oro) >= 2:
                nuevo_partido_elim("Final Título", f"GANADOR {semis_oro[0]}", f"GANADOR {semis_oro[1]}", 1, hora_e, "F-ORO")
                hora_e = siguiente_hora(hora_e, intervalo_elim)
            elif len(semis_oro) == 1:
                # Sin semifinales, la final es directa
                nuevo_partido_elim("Final Título", f"GANADOR {codigos_elim[0]}", f"GANADOR {codigos_elim[1]}", 1, hora_e, "F-ORO")
                hora_e = siguiente_hora(hora_e, intervalo_elim)

            # Semifinales y finales Plata
            if hay_consolacion and codigos_cons:
                semis_plata = []
                for i in range(0, len(codigos_cons), 2):
                    cod_semi = f"SC-{i//2+1}"
                    nuevo_partido_elim(
                        "Semifinales Consolación",
                        f"GANADOR {codigos_cons[i]}", f"GANADOR {codigos_cons[i+1]}",
                        2, hora_e, cod_semi
                    )
                    semis_plata.append(cod_semi)
                    hora_e = siguiente_hora(hora_e, intervalo_elim)

                if len(semis_plata) >= 2:
                    nuevo_partido_elim("Final Consolación", f"GANADOR {semis_plata[0]}", f"GANADOR {semis_plata[1]}", 2, hora_e, "F-PLATA")
                elif semis_plata:
                    nuevo_partido_elim("Final Consolación", f"GANADOR {codigos_cons[0]}", f"GANADOR {codigos_cons[1]}", 2, hora_e, "F-PLATA")

        db.session.commit()

        print(f"\n✓ Torneo '{nombre_torneo}' creado con ID={t.id}")
        print(f"  · {num_grupos} grupos con {sum(len(v) for v in equipos_grupos.values())} equipos en total")
        print(f"  · {total_partidos_grupos} partidos de fase de grupos")
        if hay_eliminatorias:
            print(f"  · {total_partidos_elim} partidos de eliminatorias")
        print(f"\nPuedes editar los equipos y cruces desde la interfaz web.")
        print(f"  → http://localhost:5001/torneo/{t.id}\n")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    if reset:
        confirmar = input("⚠️  ATENCIÓN: --reset borrará TODOS los torneos existentes. ¿Continuar? (s/N): ")
        if confirmar.lower() != "s":
            print("Operación cancelada.")
            sys.exit(0)
        with app.app_context():
            db.create_all()
            EventoGol.query.delete()
            Goleador.query.delete()
            Partido.query.delete()
            Grupo.query.delete()
            Torneo.query.delete()
            db.session.commit()
            print("Base de datos limpiada.\n")

    cargar()
