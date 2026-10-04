from flask import Flask, render_template

# Inicializamos la aplicación Flask
app = Flask(__name__)

# Ruta principal: Muestra la pantalla del paciente (El botón SOS de Laura)
@app.route('/')
def inicio():
    # Intenta cargar la página de Laura si existe, si no, muestra un mensaje
    try:
        return render_template('paciente.html')
    except:
        return "<h1>Servidor Flask funcionando</h1><p>Aquí se cargará el HTML de Laura (paciente.html) cuando te lo entregue.</p>"

# Ruta secundaria: Muestra la pantalla del supervisor (El panel de Sofía)
@app.route('/supervisor')
def supervisor():
    # Intenta cargar la página de Sofía si existe, si no, muestra un mensaje
    try:
        return render_template('supervisor.html')
    except:
        return "<h1>Panel de Supervisor</h1><p>Aquí se cargará el HTML de Sofía (supervisor.html) cuando te lo entregue.</p>"

if __name__ == '__main__':
    # Arrancamos el servidor en modo desarrollo
    app.run(debug=True)
