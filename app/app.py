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
            session['usuario'] = usuario[1]
            return redirect(url_for('index'))
        else:
            return 'Correo o contraseña incorrectos.'

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)

