from flask import Flask, render_template, redirect, url_for, session
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

@app.route('/')
def index():
    if 'usuario' in session:
        return render_template('index.html', usuario=session['usuario'])
    return render_template('index.html', usuario=None)

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
        cursor.execute("INSERT INTO usuarios(nombres, apellidos, institucion, grado, telefono, correo, contraseña ) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                       (nombres,apellidos,institucion,grado,telefono,correo,contraseña_hash ))
        mysql.connection.commit()
        cursor.close()

        session['usuario'] = nombres 


        return redirect(url_for('index'))
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
            session['usuario'] = usuario[1]
            
            return redirect(url_for('index'))
        else:
            mensaje = 'Correo o contraseña incorrectos.'
        return render_template('login.html', mensaje= mensaje)

    return render_template('login.html')

@app.route('/periodo')
def periodo():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM periodos WHERE id_usuario = %s",(session['usuario_id'],))
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
        tipo = request.form['tipo']
        porcentajePeriodo = request.form['porcentajePeriodo']
        
        cursor= mysql.connection.cursor()
        cursor.execute("INSERT INTO periodos( id_usuario , nombre, fecha_inicio, fecha_fin, tipo, porcentaje_anual	) VALUES (%s, %s, %s, %s, %s, %s)",
                       (session['usuario_id'], nombre,inicio,fin,tipo,porcentajePeriodo))
        mysql.connection.commit()
        cursor.close()
        mensaje =  'Periodo agregado con exito.'
    return render_template('agregarperiodo.html', mensaje=mensaje)

@app.route('/eliminar_periodo/<int:id_periodo>')
def eliminarPeriodo(id_periodo):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM periodos WHERE id_periodo = %s",(id_periodo,))
    mysql.connection.commit()
    return redirect(url_for('periodo'))

@app.route('/editar_periodo/<int:id_periodo>', methods=['GET','POST'])
def editarPeriodo(id_periodo):
    cursor = mysql.connection.cursor()
    if request.method=='POST':
        nombre = request.form['nombre']
        inicio = request.form['inicio']
        fin = request.form['fin']
        tipo = request.form['tipo']
        porcentajePeriodo = request.form['porcentajePeriodo'] 
        
        cursor.execute("UPDATE  periodos SET nombre=%s, fecha_inicio=%s , fecha_fin=%s , tipo=%s , porcentaje_anual=%s WHERE id_periodo=%s",(nombre,inicio,fin,tipo,porcentajePeriodo, id_periodo))
        mysql.connection.commit()
        return redirect(url_for('periodo'))
    
    cursor.execute("SELECT * FROM periodos WHERE id_periodo=%s",(id_periodo,))
    periodos = cursor.fetchone()
    return render_template('editarperiodo.html', periodo=periodos)


@app.route('/ver_periodo')
def verPeriodo():
    periodo_id = request.args.get('periodo_id')
    usuario_id = session['usuario_id']
    
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM periodos")
    periodos = cursor.fetchall()

    if periodo_id:
        cursor.execute("SELECT * FROM materias WHERE id_usuario = %s AND id_periodo = %s", (usuario_id, periodo_id))
    else:
        cursor.execute("SELECT * FROM materias WHERE id_usuario = %s", (usuario_id,))


    materias = cursor.fetchall()
    cursor.close()

    return render_template('materias.html', materias=materias, periodos=periodos)


@app.route('/materias')
def materias():

    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM materias WHERE id_usuario = %s",(session['usuario_id'],))
    materias = cursor.fetchall()
    cursor.close()
    return render_template('materias.html',materias=materias)

@app.route('/agregar_materias', methods=['POST','GET'] )
def agregarMaterias():
    mensaje = None

    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM periodos WHERE id_usuario = %s", (session["usuario_id"],))
    periodos = cursor.fetchall()

    if request.method == 'POST':
        usuario = session['usuario_id']
        periodo = request.form['periodo']
        nombre = request.form['nombre']
        area = request.form['area']
        porcentajeMateria = request.form['porcentajeMateria']
        profesor = request.form['profesor']

        cursor.execute("INSERT INTO materias ( id_usuario, id_periodo , nombre , area, porcentaje_periodo, profesor) VALUES ( %s, %s, %s, %s, %s, %s)", 
                       ( usuario, periodo, nombre, area, porcentajeMateria, profesor))
        mysql.connection.commit()
        cursor.close()
        mensaje = 'Materia agregada con exito.'
    return render_template('agregarmaterias.html', periodos=periodos, mensaje=mensaje)

@app.route('/eliminar_materia/<int:id_materia>')
def eliminarMateria(id_materia):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM materias WHERE id_materia = %s",(id_materia,))
    mysql.connection.commit()
    return redirect(url_for('materias'))

@app.route('/editar_materia/<int:id_materia>', methods=['GET', 'POST'])
def editarMateria(id_materia):
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        area = request.form['area']
        porcentajeMateria = request.form['porcentajeMateria']
        profesor = request.form['profesor']

        cursor.execute("UPDATE materias SET nombre = %s, area = %s, porcentaje_periodo = %s, profesor = %s WHERE id_materia = %s", (nombre, area, porcentajeMateria, profesor, id_materia))
        mysql.connection.commit()
        return redirect(url_for('materias'))
    
    cursor.execute("SELECT * FROM materias WHERE id_materia = %s", (id_materia,))
    materias = cursor.fetchone()
    return render_template('editarmateria.html', materia=materias)




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)

