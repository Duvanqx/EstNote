from flask import Flask, render_template, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask import request
from werkzeug.security import generate_password_hash , check_password_hash

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'estnote'

mysql = MySQL(app)

#Funciones Calculos

def notas_finales(id_materia, id_usuario):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT SUM(c.calificacion * c.porcentaje_materia / 100) AS nota_final FROM calificaciones c WHERE c.id_materia = %s AND id_usuario = %s",(id_materia,id_usuario))
    nota_final = cursor.fetchone()[0] or 0

    cursor.execute("SELECT id_periodo FROM materias WHERE id_materia = %s",(id_materia,))
    id_periodo_result = cursor.fetchone()

    if id_periodo_result:
        id_periodo = id_periodo_result[0]
        cursor.execute("INSERT INTO notas_materia_periodo (id_usuario, id_materia, id_periodo, nota_final) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE nota_final = VALUES(nota_final)",(id_usuario,id_materia,id_periodo, nota_final))
        mysql.connection.commit()
    else:
        print("Error: id_periodo no encontrado.")

    cursor.close()

def notas_periodos(id_periodo, id_usuario):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT SUM(n.nota_final * m.porcentaje_periodo / 100)  FROM notas_materia_periodo n JOIN materias m ON n.id_materia = m.id_materia WHERE m.id_periodo = %s AND n.id_usuario = %s",(id_periodo,id_usuario))
    nota_periodo = cursor.fetchone()[0] 


    cursor.execute("INSERT INTO notas_periodo (id_usuario, id_periodo, nota_periodo) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE nota_periodo = VALUES(nota_periodo)",(id_usuario,id_periodo, nota_periodo))
    mysql.connection.commit()

#Inicio

@app.route('/')
def index():
    if 'usuario_id' in session:
        return render_template('index.html', usuario=session['usuario'])
    return render_template('index.html', usuario=None)

#Autenticación

@app.route('/registro', methods=['POST', 'GET'])
def registro():
    if request.method == 'POST':
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        institucion = request.form['institucion']
        grado = request.form['grado']
        telefono = request.form['telefono']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        contraseña_hash = generate_password_hash(contraseña)

        cursor= mysql.connection.cursor()

        cursor.execute("INSERT INTO instituciones(nombre) VALUES (%s)",(institucion,))
        institucion = cursor.lastrowid
        cursor.execute("INSERT INTO grados(nombre) VALUES (%s)",(grado,))
        grado = cursor.lastrowid


        cursor.execute("INSERT INTO usuarios(id_institucion , id_grado , nombres, apellidos, telefono,  correo, contraseña ) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                       (institucion, grado, nombres,apellidos,telefono,correo,contraseña_hash ))
        mysql.connection.commit()
        cursor.close()

        session['usuario'] = nombres 


        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
        usuario= cursor.fetchone()
        cursor.close()

        if usuario and check_password_hash(usuario[7], contraseña):

            session['usuario_id'] = usuario[0]
            session['usuario'] = usuario[3]
            
            return redirect(url_for('index'))
        else:
            mensaje = 'Correo o contraseña incorrectos.'
        return render_template('login.html', mensaje= mensaje)

    return render_template('login.html')

#Periodos

@app.route('/periodo')
def periodo():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT p.id_periodo, p.nombre, p.fecha_inicio, p.fecha_fin, np.nota_periodo FROM periodos p LEFT JOIN notas_periodo np ON p.id_periodo = np.id_periodo AND np.id_usuario = %s WHERE p.id_usuario = %s", (session['usuario_id'], session['usuario_id']))

    periodos = cursor.fetchall()
    cursor.close()
    return render_template('periodos.html', periodos=periodos)

@app.route('/agregar_periodo', methods=['POST', 'GET']) 
def agregarPeriodo():
    mensaje = None
    if request.method == 'POST':
        nombre = request.form['nombre']
        inicio = request.form['inicio']
        fin = request.form['fin']
        
        cursor= mysql.connection.cursor()
        cursor.execute("INSERT INTO periodos( id_usuario , nombre, fecha_inicio, fecha_fin) VALUES ( %s, %s, %s, %s)",(session['usuario_id'], nombre,inicio,fin))
        mysql.connection.commit()

        cursor.close()
        mensaje =  'Periodo agregado con exito.'

    return render_template('agregarperiodo.html', mensaje=mensaje)

@app.route('/eliminar_periodo/<int:id_periodo>')
def eliminarPeriodo(id_periodo):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM periodos WHERE id_periodo = %s",(id_periodo,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('periodo'))

@app.route('/editar_periodo/<int:id_periodo>', methods=['GET','POST'])
def editarPeriodo(id_periodo):
    cursor = mysql.connection.cursor()
    if request.method=='POST':
        nombre = request.form['nombre']
        inicio = request.form['inicio']
        fin = request.form['fin']
        
        cursor.execute("UPDATE  periodos SET nombre=%s, fecha_inicio=%s , fecha_fin=%s  WHERE id_periodo=%s",(nombre,inicio,fin,id_periodo))
        mysql.connection.commit()
        return redirect(url_for('periodo'))
    
    cursor.execute("SELECT * FROM periodos WHERE id_periodo=%s",(id_periodo,))
    periodos = cursor.fetchone()
    
    notas_periodos(id_periodo, session['usuario_id'])


    cursor.close()
    return render_template('editarperiodo.html', periodo=periodos)

#Configuración de Asignaturas y Profesores

@app.route('/configuracion')
def configuracion():
   if 'usuario_id' not in session:
       return redirect(url_for('login'))
   
   cursor = mysql.connection.cursor()
   cursor.execute("SELECT p.id_profesor, p.nombre, COUNT(mp.id_materia) AS total_materias FROM profesores p LEFT JOIN materia_profesor mp ON p.id_profesor = mp.id_profesor WHERE p.id_usuario = %s GROUP BY p.id_profesor, p.nombre",(session['usuario_id'],))
   profesores = cursor.fetchall()
   cursor.close()
   return render_template("configuracion.html", profesores=profesores)

@app.route('/profesor', methods=['GET','POST'])
def agregarProfesor():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        telefono = request.form['telefono']

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO profesores(id_usuario , nombre, correo, telefono) VALUES (%s, %s,%s,%s)", (session['usuario_id'],nombre,correo,telefono))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('configuracion'))
    return render_template("agregarprofesor.html")

@app.route('/editar_profesor/<int:id_profesor>', methods = ['POST', 'GET'])
def editarProfesor(id_profesor):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM profesores WHERE id_usuario = %s AND id_profesor = %s",(session['usuario_id'],id_profesor))
    profesor = cursor.fetchone()

    if not profesor:
        return "Profesor no encontrado o acceso no autorizado", 404

    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        telefono = request.form['telefono']

        cursor.execute("UPDATE profesores SET nombre = %s, correo = %s, telefono = %s WHERE id_profesor = %s",(nombre, correo, telefono, id_profesor))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('configuracion'))
    return render_template("editarprofesor.html", profesor=profesor)

@app.route('/eliminar_profesor/<int:id_profesor>')
def eliminarProfesor(id_profesor):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM profesores WHERE id_profesor = %s",(id_profesor,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('configuracion'))

#Calificacioness

@app.route('/ver_materia/<int:id_materia>')
def verMateria(id_materia):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT id_materia, nombre FROM materias WHERE id_materia = %s AND id_usuario = %s", (id_materia,session['usuario_id']))
    materia = cursor.fetchone()

    cursor.execute("SELECT c.id_calificacion, c.titulo, t.nombre, c.calificacion, c.porcentaje_materia, c.fecha, c.descripcion, c.estado FROM calificaciones c JOIN tipos_calificacion t ON c.id_tipo = t.id_tipo WHERE c.id_materia = %s",(id_materia,))
    calificacion = cursor.fetchall()

    cursor.execute("SELECT m.nombre, n.nota_final FROM materias m JOIN notas_materia_periodo n ON m.id_materia  = n.id_materia WHERE n.id_usuario = %s AND n.id_materia = %s",(session['usuario_id'],id_materia))
    nota_materia = cursor.fetchone()


    cursor.close()

    if materia:
        return render_template('vermateria.html',materia=materia, calificacion=calificacion, id_materia=id_materia, nota_materia=nota_materia)
    else:
        return "Materia no encontrada",404

@app.route('/agregar_calificacion/<int:id_materia>', methods=['GET', 'POST'])
def agregarCalificacion(id_materia):

    cursor = mysql.connection.cursor()
    mensaje = None
    if request.method == 'POST':

        usuario = session['usuario_id']
        titulo = request.form['titulo']
        tipo = request.form['tipo']
        calificacion = request.form['calificacion']
        peso = request.form['peso']
        fecha = request.form['fecha']
        descripcion = request.form['descripcion']
        estado = request.form['estado']

        cursor.execute("SELECT id_tipo FROM tipos_calificacion WHERE nombre = %s",(tipo,))
        resultado = cursor.fetchone()

        if resultado:
            id_tipo = resultado[0]
        else:
            cursor.execute("INSERT INTO tipos_calificacion(nombre) VALUES (%s)",(tipo,))
            id_tipo = cursor.lastrowid

        cursor.execute("INSERT INTO calificaciones(id_materia, id_usuario, id_tipo, titulo, calificacion, porcentaje_materia, fecha, descripcion, estado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",(id_materia,usuario,id_tipo, titulo, calificacion,peso,fecha, descripcion, estado))
        mysql.connection.commit()

        mensaje = "Calificación agregada con exito."

    notas_finales(id_materia, session['usuario_id'])

    cursor.execute("SELECT id_periodo FROM materias WHERE id_materia = %s",(id_materia,))
    id_periodo = cursor.fetchone()[0]

    notas_periodos(id_periodo, session['usuario_id'])

    cursor.close()

    return render_template('agregarcalificacion.html', id_materia=id_materia, mensaje=mensaje)

@app.route('/eliminar_calificacion/<int:id_calificacion>')
def eliminarCalificacion(id_calificacion):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT id_materia FROM calificaciones WHERE id_calificacion = %s",(id_calificacion,))
    resultado = cursor.fetchone()

    if resultado:

        id_materia = resultado[0]

        cursor.execute("DELETE FROM calificaciones WHERE id_calificacion = %s", (id_calificacion,))
        mysql.connection.commit()

        notas_finales(id_materia, session['usuario_id'])
        cursor.close()

        return redirect( url_for('verMateria', id_materia=id_materia))
    
    else:
        cursor.close()
        return 'Calificación no encontrada',404

@app.route('/editar_calificacion/<int:id_calificacion>', methods=['GET','POST'])
def editarCalificacion(id_calificacion):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM calificaciones WHERE id_calificacion = %s",(id_calificacion,))
    calificaciones = cursor.fetchone()

    if request.method == 'POST':
        titulo = request.form['titulo']
        tipo = request.form['tipo']
        calificacion = request.form['calificacion']
        peso = request.form['peso']
        fecha = request.form['fecha']
        descripcion = request.form['descripcion']
        estado = request.form['estado']

        cursor.execute("SELECT id_tipo FROM tipos_calificacion WHERE nombre = %s", (tipo,))
        resultado = cursor.fetchone()

        if resultado:
            id_tipo = resultado[0]
        else:
            cursor.execute("INSERT INTO tipos_calificacion (nombre) VALUES (%s)",(tipo,))
            id_tipo = cursor.lastrowid

        cursor.execute("UPDATE calificaciones SET id_tipo = %s, titulo = %s, calificacion = %s, porcentaje_materia = %s, fecha = %s, descripcion = %s, estado = %s WHERE id_calificacion = %s",(id_tipo, titulo, calificacion,peso,fecha,descripcion,estado,id_calificacion))
        mysql.connection.commit()

        cursor.execute("SELECT id_materia FROM calificaciones WHERE id_calificacion = %s",(id_calificacion,))
        id_materia = cursor.fetchone()[0]

        notas_finales(id_materia, session['usuario_id'])

        cursor.execute("SELECT id_periodo FROM materias WHERE id_materia = %s",(id_materia,))
        id_periodo = cursor.fetchone()[0]

        notas_periodos(id_periodo, session['usuario_id'])

        return redirect(url_for('verMateria', id_materia=id_materia))
    return render_template("editarcalificacion.html", calificaciones=calificaciones)

#Materias

@app.route('/materias/<int:id_periodo>')
def materias(id_periodo):

    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT m.id_materia, m.nombre AS nombre_materia, m.porcentaje_periodo, a.nombre AS nombre_area, GROUP_CONCAT(p.nombre SEPARATOR ', ') AS profesores, n.nota_final FROM materias m JOIN areas_materia a ON m.id_area = a.id_area LEFT JOIN materia_profesor mp ON m.id_materia = mp.id_materia LEFT JOIN profesores p ON mp.id_profesor = p.id_profesor LEFT JOIN notas_materia_periodo n ON m.id_materia = n.id_materia AND n.id_usuario WHERE m.id_usuario = %s AND m.id_periodo = %s GROUP BY m.id_materia", (session['usuario_id'],id_periodo))
    materias = cursor.fetchall()

    cursor.close()
    return render_template('materias.html',materias=materias, id_periodo=id_periodo)

@app.route('/agregar_materias', methods=['POST','GET'] )
def agregarMaterias():
    mensaje = None

    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM periodos WHERE id_usuario = %s", (session["usuario_id"],))
    periodos = cursor.fetchall()

    cursor.execute("SELECT * FROM profesores WHERE id_usuario = %s",(session['usuario_id'],))
    profesores = cursor.fetchall()

    if request.method == 'POST':
        usuario = session['usuario_id']
        periodo = request.form['periodo']
        nombre = request.form['nombre']
        area = request.form['area']
        porcentajeMateria = request.form['porcentajeMateria']
        profesor = request.form['profesor']

        cursor.execute("SELECT id_area FROM areas_materia WHERE nombre = %s", (area,))
        resultado = cursor.fetchone()

        if resultado:
            id_area = resultado[0]
        else:
            cursor.execute("INSERT INTO areas_materia (nombre) VALUES (%s)", (area,))
            id_area = cursor.lastrowid

        cursor.execute("INSERT INTO materias ( id_usuario, id_periodo , nombre , id_area, porcentaje_periodo) VALUES ( %s, %s, %s, %s, %s)", 
                       ( usuario, periodo, nombre, id_area,  porcentajeMateria))
        id_materia = cursor.lastrowid
        
        cursor.execute("INSERT INTO materia_profesor(id_materia, id_profesor) VALUES (%s,%s)", (id_materia,profesor))
        mysql.connection.commit()

        cursor.execute("SELECT id_periodo FROM materias WHERE id_materia = %s",(id_materia,))
        id_periodo_result = cursor.fetchone()

        if id_periodo_result:
            id_periodo = id_periodo_result[0]
            notas_periodos(id_periodo, session['usuario_id'])

        cursor.close()
        mensaje = 'Materia agregada con exito.'


        
    return render_template('agregarmaterias.html', periodos=periodos, mensaje=mensaje, profesores=profesores)

@app.route('/eliminar_materia/<int:id_materia>')
def eliminarMateria(id_materia):
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT id_periodo FROM materias WHERE id_materia = %s",(id_materia,))
    resultado = cursor.fetchone()

    if resultado is None:
        return "Materia no encontrada",404
    
    id_periodo = resultado [0]

    cursor.execute("DELETE FROM materias WHERE id_materia = %s",(id_materia,))
    mysql.connection.commit()

    notas_periodos(id_periodo,session['usuario_id'])

    cursor.close()
    return redirect(url_for('materias',id_periodo=id_periodo))

@app.route('/editar_materia/<int:id_materia>', methods=['GET', 'POST'])
def editarMateria(id_materia):
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        area = request.form['area']
        porcentajeMateria = request.form['porcentajeMateria']
        profesor = request.form['profesor']

        cursor.execute("SELECT id_area FROM areas_materia WHERE nombre = %s", (area,))
        resultado = cursor.fetchone()

        if resultado:
            id_area = resultado[0]
        else:
            cursor.execute("INSERT INTO areas_materia(nombre) VALUES (%s)", (area,))
            id_area = cursor.lastrowid

        cursor.execute("UPDATE materias SET nombre = %s, id_area = %s, porcentaje_periodo = %s WHERE id_materia = %s", (nombre, id_area, porcentajeMateria, id_materia))
        mysql.connection.commit()

        cursor.execute("SELECT * FROM materia_profesor WHERE id_materia = %s",(id_materia,))
        registro_existente = cursor.fetchone()

        if registro_existente:
            cursor.execute("UPDATE materia_profesor SET id_profesor = %s WHERE id_materia = %s",(profesor, id_materia))
        else:
            cursor.execute("INSERT INTO materia_profesor (id_materia, id_profesor) VALUES (%s,%s)",(id_materia,profesor))
        mysql.connection.commit()


        cursor.execute("SELECT id_periodo FROM materias WHERE id_materia = %s",(id_materia,))
        id_periodo = cursor.fetchone()[0]

        notas_periodos(id_periodo,session['usuario_id'])

        return redirect(url_for('materias',id_periodo=id_periodo))
    
    cursor.execute("SELECT m.id_materia, m.nombre AS nombre_materia, m.porcentaje_periodo, a.nombre AS nombre_area, mp.id_profesor FROM materias m JOIN areas_materia a ON m.id_area = a.id_area LEFT JOIN materia_profesor mp ON m.id_materia = mp.id_materia WHERE m.id_materia = %s AND m.id_usuario = %s", (id_materia, session['usuario_id']))
    materia = cursor.fetchone()

    cursor.execute("SELECT * FROM profesores")
    profesores = cursor.fetchall()
    mysql.connection.commit()

    cursor.close()
    return render_template('editarmateria.html', materia=materia, profesores=profesores)



#Acerca de y Ayuda

@app.route('/acerca')
def acerca():
    return render_template('acerca.html', usuario=session.get('usuario'))

@app.route('/ayuda')
def ayuda():
    return render_template('ayuda.html', usuario=session.get('usuario'))



#Usuario y Cerrar Sesión

@app.route('/perfil')
def perfil_usuario():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT nombres, correo, telefono FROM usuarios WHERE id_usuario = %s", (session['usuario_id'],))
    data = cursor.fetchone()

    if data:
        return render_template('usuario.html',
                               usuario=data[0],
                               correo=data[1],
                               telefono=data[2])
    else:
        flash("No se encontró el perfil del usuario.", "error")
        return redirect(url_for('index'))  # O a otra página que tenga sentido



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8000, debug=True)

