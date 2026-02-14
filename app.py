import os
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuración de la Base de Datos SQLite
db_path = os.path.join(os.path.dirname(__file__), 'torneo.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELOS DE DATOS ---
class Torneo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    grupos = db.relationship('Grupo', backref='torneo', lazy=True, cascade="all, delete-orphan")

class Grupo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    equipos = db.Column(db.Text, nullable=False) 
    torneo_id = db.Column(db.Integer, db.ForeignKey('torneo.id'), nullable=False)
    partidos = db.relationship('Partido', backref='grupo', lazy=True, cascade="all, delete-orphan")

class Partido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipo1 = db.Column(db.String(100))
    equipo2 = db.Column(db.String(100))
    goles1 = db.Column(db.Integer, default=0)
    goles2 = db.Column(db.Integer, default=0)
    ganador_penaltis = db.Column(db.String(100), nullable=True) 
    hora = db.Column(db.String(10)) 
    numero_campo = db.Column(db.Integer, default=1)
    en_curso = db.Column(db.Boolean, default=False)
    finalizado = db.Column(db.Boolean, default=False)
    codigo_partido = db.Column(db.String(10), nullable=True) 
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)
    
    inicio_ts = db.Column(db.Integer, default=0)
    segundos_transcurridos = db.Column(db.Integer, default=0)
    esta_pausado = db.Column(db.Boolean, default=True)
    eventos = db.relationship('EventoGol', backref='partido', lazy=True, cascade="all, delete-orphan")

class EventoGol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partido.id'), nullable=False)
    equipo = db.Column(db.String(100))
    dorsal = db.Column(db.String(10))
    minuto = db.Column(db.String(10))

class Goleador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dorsal = db.Column(db.String(10), nullable=False)
    equipo = db.Column(db.String(100), nullable=False)
    goles = db.Column(db.Integer, default=0)
    torneo_id = db.Column(db.Integer, db.ForeignKey('torneo.id'), nullable=False)

class ConfigCruce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    torneo_id = db.Column(db.Integer, db.ForeignKey('torneo.id'), nullable=False)
    hora = db.Column(db.String(10))
    numero_campo = db.Column(db.Integer)
    grupo_letra_1 = db.Column(db.String(5))
    posicion_1 = db.Column(db.Integer)  # 1-indexed (1=1º, 2=2º, ...)
    grupo_letra_2 = db.Column(db.String(5))
    posicion_2 = db.Column(db.Integer)  # 1-indexed


# Cruces por defecto para formato estándar F8 (4 grupos, 2 campos)
CONFIG_CRUCES_DEFAULT = [
    # Campo 1: Título (Oro)
    {"hora": "15:00", "campo": 1, "g1": "A", "p1": 0, "g2": "B", "p2": 1},
    {"hora": "15:25", "campo": 1, "g1": "B", "p1": 0, "g2": "A", "p2": 1},
    {"hora": "15:50", "campo": 1, "g1": "C", "p1": 0, "g2": "D", "p2": 1},
    {"hora": "16:15", "campo": 1, "g1": "D", "p1": 0, "g2": "C", "p2": 1},
    # Campo 2: Consolación (Plata)
    {"hora": "15:00", "campo": 2, "g1": "A", "p1": 2, "g2": "B", "p2": 3},
    {"hora": "15:25", "campo": 2, "g1": "B", "p1": 2, "g2": "A", "p2": 3},
    {"hora": "15:50", "campo": 2, "g1": "C", "p1": 2, "g2": "D", "p2": 3},
    {"hora": "16:15", "campo": 2, "g1": "D", "p1": 2, "g2": "C", "p2": 3},
]


with app.app_context():
    db.create_all()

# --- LÓGICA DE PROCESAMIENTO ---

def obtener_tablas(torneo_id):
    grupos = Grupo.query.filter_by(torneo_id=torneo_id).all()
    tablas = {}
    for g in grupos:
        # Solo calculamos tablas para los grupos de letras (A, B, C, D)
        if not g.nombre.startswith("Grupo"): continue
        
        lista_equipos = [e.strip() for e in g.equipos.split(',') if e.strip()]
        if not lista_equipos: continue
        
        stats = {e: {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "pts": 0} for e in lista_equipos}
        for p in g.partidos:
            if p.finalizado:
                e1, e2 = p.equipo1, p.equipo2
                if e1 in stats and e2 in stats:
                    stats[e1]["pj"] += 1; stats[e2]["pj"] += 1
                    stats[e1]["gf"] += p.goles1; stats[e1]["gc"] += p.goles2
                    stats[e2]["gf"] += p.goles2; stats[e2]["gc"] += p.goles1
                    if p.goles1 > p.goles2:
                        stats[e1]["pts"] += 3; stats[e1]["pg"] += 1; stats[e2]["pp"] += 1
                    elif p.goles2 > p.goles1:
                        stats[e2]["pts"] += 3; stats[e2]["pg"] += 1; stats[e1]["pp"] += 1
                    else:
                        stats[e1]["pts"] += 1; stats[e2]["pts"] += 1; stats[e1]["pe"] += 1; stats[e2]["pe"] += 1
        
        tablas[g.id] = sorted(stats.items(), key=lambda x: (x[1]['pts'], x[1]['gf']-x[1]['gc'], x[1]['gf']), reverse=True)
    return tablas

def actualizar_cruces_eliminatorias(torneo_id):
    tablas = obtener_tablas(torneo_id)
    grupos = Grupo.query.filter_by(torneo_id=torneo_id).all()

    mapa_letras = {}
    for g in grupos:
        # Extraemos la letra del nombre "Grupo A", "Grupo B", etc.
        if g.nombre.startswith("Grupo "):
            letra = g.nombre.replace("Grupo ", "").strip()
            if g.id in tablas:
                mapa_letras[letra] = [equipo for equipo, stats in tablas[g.id]]

    # CONFIGURACIÓN DE CRUCES: leer desde BD, o usar defaults si no hay configuración guardada
    registros = ConfigCruce.query.filter_by(torneo_id=torneo_id).all()
    if registros:
        # posicion_1/2 guardadas como 1-indexed → convertir a 0-indexed para acceder a listas
        config_cruces = {
            (r.hora, r.numero_campo): (r.grupo_letra_1, r.posicion_1 - 1, r.grupo_letra_2, r.posicion_2 - 1)
            for r in registros
        }
    else:
        config_cruces = {
            (c["hora"], c["campo"]): (c["g1"], c["p1"], c["g2"], c["p2"])
            for c in CONFIG_CRUCES_DEFAULT
        }

    partidos_totales = Partido.query.join(Grupo).filter(Grupo.torneo_id == torneo_id).all()

    for p in partidos_totales:
        if p.finalizado: continue 
        
        # Normalizar hora para comparación
        h = p.hora.strip() if p.hora else ""
        if ":" in h:
            partes = h.split(":")
            h = f"{int(partes[0])}:{int(partes[1]):02d}"

        # 1. CRUCES DESDE FASE DE GRUPOS (Cuartos)
        cruce = config_cruces.get((h, p.numero_campo))
        if cruce:
            l1, pos1, l2, pos2 = cruce
            # Solo actualizar si el nombre actual es un placeholder o está vacío
            if l1 in mapa_letras and len(mapa_letras[l1]) > pos1:
                p.equipo1 = mapa_letras[l1][pos1]
            if l2 in mapa_letras and len(mapa_letras[l2]) > pos2:
                p.equipo2 = mapa_letras[l2][pos2]

        # 2. CRUCES POR CÓDIGO (Semis y Finales)
        ganadores_codigos = {}
        for p_aux in partidos_totales:
            if p_aux.finalizado and p_aux.codigo_partido:
                if p_aux.goles1 > p_aux.goles2: gan = p_aux.equipo1
                elif p_aux.goles2 > p_aux.goles1: gan = p_aux.equipo2
                else: gan = p_aux.ganador_penaltis
                if gan:
                    ganadores_codigos[p_aux.codigo_partido.upper().strip()] = gan

        for cod, nombre_ganador in ganadores_codigos.items():
            if p.equipo1 and cod in p.equipo1.upper():
                p.equipo1 = nombre_ganador
            if p.equipo2 and cod in p.equipo2.upper():
                p.equipo2 = nombre_ganador

    db.session.commit()

# --- RUTAS DE NAVEGACIÓN ---

@app.route('/')
def index():
    torneos = Torneo.query.all()
    return render_template('index.html', torneos=torneos)

@app.route('/torneo/<int:t_id>')
def ver_torneo(t_id):
    t = Torneo.query.get_or_404(t_id)
    actualizar_cruces_eliminatorias(t_id)
    tablas = obtener_tablas(t_id)
    top_g = Goleador.query.filter_by(torneo_id=t_id).order_by(Goleador.goles.desc()).limit(15).all()
    return render_template('torneo.html', t=t, tablas=tablas, top=top_g)

@app.route('/partido/<int:p_id>')
def live(p_id):
    p = Partido.query.get_or_404(p_id)
    return render_template('partido.html', p=p, t_id=p.grupo.torneo_id)

@app.route('/publico')
def vista_publica():
    return render_template('publico.html')

@app.route('/editar_torneo/<int:torneo_id>', methods=['POST'])
def editar_torneo(torneo_id):
    # Buscar el torneo por ID
    torneo = Torneo.query.get_or_404(torneo_id)
    nuevo_nombre = request.form.get('nombre')
    
    if nuevo_nombre:
        torneo.nombre = nuevo_nombre
        db.session.commit()
    
    # Redirigir a la página de inicio (index)
    return redirect(url_for('index'))

@app.route('/eliminar_torneo/<int:torneo_id>')
def eliminar_torneo(torneo_id):
    # Buscar el torneo por ID
    torneo = Torneo.query.get_or_404(torneo_id)
    
    try:
        # Al eliminar el torneo, la base de datos debería estar configurada 
        # para eliminar en cascada, de lo contrario, borramos manualmente sus dependencias
        # si no tienes configurado cascade="all, delete-orphan" en los modelos:
        
        # 1. Borrar eventos de gol y goleadores asociados a partidos de este torneo
        # 2. Borrar partidos de los grupos del torneo
        # 3. Borrar grupos del torneo
        
        # Si tu modelo tiene las relaciones bien configuradas, basta con:
        db.session.delete(torneo)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar: {e}")
        
    return redirect(url_for('index'))

# --- RUTAS DE EDICIÓN ---

@app.route('/crear_torneo', methods=['POST'])
def crear_torneo():
    nombre = request.form.get('nombre')
    if nombre:
        nuevo_torneo = Torneo(nombre=nombre)
        db.session.add(nuevo_torneo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/configurar_cruces/<int:torneo_id>', methods=['GET', 'POST'])
def configurar_cruces(torneo_id):
    torneo = Torneo.query.get_or_404(torneo_id)
    if request.method == 'POST':
        # Borrar configuración anterior de este torneo
        ConfigCruce.query.filter_by(torneo_id=torneo_id).delete()
        horas = request.form.getlist('hora[]')
        campos = request.form.getlist('campo[]')
        g1s = request.form.getlist('g1[]')
        p1s = request.form.getlist('p1[]')
        g2s = request.form.getlist('g2[]')
        p2s = request.form.getlist('p2[]')
        for h, c, g1, p1, g2, p2 in zip(horas, campos, g1s, p1s, g2s, p2s):
            if h and c and g1 and p1 and g2 and p2:
                db.session.add(ConfigCruce(
                    torneo_id=torneo_id,
                    hora=h.strip(),
                    numero_campo=int(c),
                    grupo_letra_1=g1.strip().upper(),
                    posicion_1=int(p1),  # 1-indexed: 1=1º, 2=2º, etc.
                    grupo_letra_2=g2.strip().upper(),
                    posicion_2=int(p2),
                ))
        db.session.commit()
        actualizar_cruces_eliminatorias(torneo_id)
        return redirect(url_for('ver_torneo', t_id=torneo_id))

    # GET: cargar configuración actual (de BD o defaults)
    registros = ConfigCruce.query.filter_by(torneo_id=torneo_id).all()
    if registros:
        configs = registros
    else:
        # Mostrar defaults como objetos para el template (1-indexed para el usuario)
        configs = [
            type('obj', (object,), {
                'hora': c['hora'],
                'numero_campo': c['campo'],
                'grupo_letra_1': c['g1'],
                'posicion_1': c['p1'] + 1,
                'grupo_letra_2': c['g2'],
                'posicion_2': c['p2'] + 1,
            })()
            for c in CONFIG_CRUCES_DEFAULT
        ]
    return render_template('configurar_cruces.html', torneo=torneo, configs=configs)

@app.route('/eliminar_gol/<int:evento_id>', methods=['POST'])
def eliminar_gol(evento_id):
    evento = EventoGol.query.get_or_404(evento_id)
    partido = Partido.query.get(evento.partido_id)
    
    # 1. Descontar el gol del marcador del partido
    if evento.equipo == partido.equipo1:
        partido.goles1 = max(0, partido.goles1 - 1)
    else:
        partido.goles2 = max(0, partido.goles2 - 1)
    
    # 2. Descontar el gol de la tabla de goleadores
    goleador = Goleador.query.filter_by(
        dorsal=evento.dorsal, 
        equipo=evento.equipo, 
        torneo_id=partido.grupo.torneo_id
    ).first()
    
    if goleador:
        goleador.goles -= 1
        if goleador.goles <= 0:
            db.session.delete(goleador)
            
    # 3. Eliminar el evento
    db.session.delete(evento)
    db.session.commit()
    
    return jsonify({
        "status": "ok", 
        "goles1": partido.goles1, 
        "goles2": partido.goles2
    })

@app.route('/editar_partido/<int:partido_id>', methods=['GET', 'POST'])
def editar_partido(partido_id):
    p = Partido.query.get_or_404(partido_id)
    if request.method == 'POST':
        p.equipo1 = request.form.get('equipo1', p.equipo1)
        p.equipo2 = request.form.get('equipo2', p.equipo2)
        p.hora = request.form.get('hora', p.hora)
        p.numero_campo = int(request.form.get('numero_campo', p.numero_campo))
        
        if 'goles1' in request.form:
            p.goles1 = int(request.form.get('goles1', 0))
            p.goles2 = int(request.form.get('goles2', 0))
            estado = request.form.get('estado')
            if estado == 'finalizado':
                p.finalizado, p.en_curso = True, False
            elif estado == 'en_curso':
                p.finalizado, p.en_curso = False, True
            else:
                p.finalizado, p.en_curso = False, False
            p.ganador_penaltis = request.form.get('ganador_penaltis')
            if p.ganador_penaltis == "": p.ganador_penaltis = None

        db.session.commit()
        actualizar_cruces_eliminatorias(p.grupo.torneo_id)
        return redirect(url_for('ver_torneo', t_id=p.grupo.torneo_id))
    return render_template('editar_partido.html', partido=p)

@app.route('/finalizar/<int:p_id>', methods=['POST', 'GET'])
def finalizar(p_id):
    p = Partido.query.get_or_404(p_id)
    if request.method == 'POST':
        p.ganador_penaltis = request.form.get('ganador_penaltis')
    p.finalizado, p.en_curso = True, False
    db.session.commit()
    actualizar_cruces_eliminatorias(p.grupo.torneo_id)
    return redirect(url_for('ver_torneo', t_id=p.grupo.torneo_id))

# --- API ---

@app.route('/gol/<int:p_id>/<int:equipo_num>', methods=['POST'])
def registrar_gol(p_id, equipo_num):
    p = Partido.query.get_or_404(p_id)
    dorsal = request.form.get('dorsal')
    minuto = request.form.get('minuto')
    equipo_nombre = p.equipo1 if equipo_num == 1 else p.equipo2
    
    if equipo_num == 1: p.goles1 += 1
    else: p.goles2 += 1
        
    db.session.add(EventoGol(partido_id=p_id, equipo=equipo_nombre, dorsal=dorsal, minuto=minuto))
    gol_rec = Goleador.query.filter_by(dorsal=dorsal, equipo=equipo_nombre, torneo_id=p.grupo.torneo_id).first()
    if gol_rec: gol_rec.goles += 1
    else: db.session.add(Goleador(dorsal=dorsal, equipo=equipo_nombre, goles=1, torneo_id=p.grupo.torneo_id))
    
    db.session.commit()
    return jsonify({"goles1": p.goles1, "goles2": p.goles2})

@app.route('/actualizar_timer/<int:p_id>', methods=['POST'])
def actualizar_timer(p_id):
    p = Partido.query.get_or_404(p_id)
    p.segundos_transcurridos = int(request.form.get('segundos', 0))
    p.esta_pausado = request.form.get('pausado') == 'true'
    p.inicio_ts = int(time.time()) if not p.esta_pausado else 0
    p.en_curso = not p.esta_pausado
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route('/api/partidos_activos')
def api_partidos():
    campos = {}
    for i in [1, 2]:
        actual = Partido.query.filter_by(numero_campo=i, en_curso=True, finalizado=False).first()
        proximo = Partido.query.filter_by(numero_campo=i, en_curso=False, finalizado=False).order_by(Partido.hora).first()
        ultimo = Partido.query.filter_by(numero_campo=i, finalizado=True).order_by(Partido.id.desc()).first()
        campos[f'campo_{i}'] = {
            "actual": {"equipo1": actual.equipo1, "equipo2": actual.equipo2, "goles1": actual.goles1, "goles2": actual.goles2, "segundos_transcurridos": actual.segundos_transcurridos, "inicio_ts": actual.inicio_ts, "esta_pausado": actual.esta_pausado} if actual else None,
            "proximo": {"equipo1": proximo.equipo1, "equipo2": proximo.equipo2, "hora": proximo.hora} if proximo else None,
            "ultimo_finalizado": {"equipo1": ultimo.equipo1, "equipo2": ultimo.equipo2, "goles1": ultimo.goles1, "goles2": ultimo.goles2} if ultimo else None
        }
    return jsonify(campos)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)