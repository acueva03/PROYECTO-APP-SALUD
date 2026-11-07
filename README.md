# PROYECTO APP SALUD

## 1. Descripción General del Proyecto

Esta aplicación es una plataforma diseñada para supervisar la salud, gestionar hábitos diarios y conectar a familiares dependientes con sus respectivos supervisores. La app ofrece un entorno completo y seguro, centrado en las siguientes características clave:

- Permite a los usuarios crear un perfil propio en la aplicación con sus datos básicos (nombre, edad, peso) y configurar alarmas o recordatorios para organizar su rutina diaria.
- Integra herramientas para registrar métricas de salud (como horas de sueño y estado de ánimo) con el fin de generar estadísticas sobre la evolución del usuario.
- Su principal valor reside en la seguridad y la conexión en tiempo real, integrando un botón SOS en la app para situaciones críticas y un panel interactivo para que los supervisores conozcan el estado de las alertas al instante.

## 2. Organización del Equipo

Para mantener el desarrollo alineado con los objetivos de la app, el equipo se ha dividido en los siguientes roles:

- **Product Owner (*Javier*):** Responsable de gestionar y priorizar las Historias de Usuario, asegurando que se respeta la planificación (de mayor a menor).
- **Scrum Master (*Alberto*):** Facilitador del proceso que ayuda al equipo a superar bloqueos técnicos, especialmente en los retos de conexión iniciales de la app.
- **Equipo de Desarrollo:** Encargados de implementar la lógica y construir la interfaz visual de la aplicación. Esta conformado por: ***Andrés Cuevas, Javier Monfort, Laura Ávila, Alberto Vilches y Sofía Puebla***.

La coordinación se ha mantenido mediante los siguientes eventos ágiles:

- **Sprint Planning:** Reunión al inicio de cada ciclo de 2 semanas para planificar los retos técnicos.
- **Daily Scrum:** Sincronización diaria rápida para revisar logros, objetivos del día y obstáculos.
- **Review & Retrospective:** Reflexión del trabajo al finalizar cada Sprint para comprobar el código y el funcionamiento de la app.

## 3. Guía para Desarrolladores

El sistema divide sus tareas en dos partes fundamentales para el correcto funcionamiento de la aplicación:

- **Motor Interno:** Utiliza Python como lenguaje principal junto con Flask, un entorno de trabajo que gestiona toda la lógica, cuentas y datos, permitiendo crear una experiencia interactiva fluida.
- **Interfaz de la App:** Emplea HTML5, CSS3 y JavaScript para construir la interfaz visual de la aplicación, garantizando que sea accesible y funcione de manera transversal.
- **Herramientas:** El proyecto se desarrollará en el editor Visual Studio Code.

El proyecto ha sido gestionado bajo un marco de trabajo ágil adaptado, basado en Scrum.

- El desarrollo de la app se ha estructurado en **Sprints de 2 semanas** cada uno.
- El desarrollo se aborda comenzando por los retos de conexión y comunicación más complejos de la aplicación, como manejar nuevos lenguajes de programación, finalizando con las estructuras de registro más sencillas.

### Estructura del proyecto

```
backend/     Servidor Flask: app.py (rutas y API), models.py (base de datos SQLite),
             validaciones.py, vinculos.py, esquema.py, backup_bd.py, seed.py y los tests (test_*.py)
frontend/
  templates/ Pantallas HTML (login, registro, paciente, supervisor, vincular, supervisor_salud)
  static/    JavaScript y CSS de cada pantalla
doc/         Documentación del proyecto (incluido el documento de riesgos)
.github/     Integración continua (tests y ESLint)
```

Archivos de JavaScript relevantes: `conexion.js` (pantalla del paciente: SOS y alarmas), `supervisor.js` (panel de alertas),
`salud.js` (datos y peso del paciente), `graficos.js` y `supervisor_salud.js` (gráficos de salud del supervisor),
`reloj.js` (aviso de reloj desajustado) y `vinculos_*.js` (código y QR de vinculación).

### Reglas de trabajo

- Toda columna nueva de la base de datos se añade en `models.py` **y** en `actualizar_columnas()` en el mismo commit.
- Antes de ejecutar los tests, haz una copia de seguridad: `python3 backend/backup_bd.py`.
- Los tests usan una base de datos en memoria (`base_tests.py` lo comprueba) y nunca deben tocar `app_salud.db`.
- Cada funcionalidad nueva lleva, como mínimo, 3 tests.

## 4. Guía para Usuarios (Cómo usar la app)

Si eres un nuevo usuario o supervisor, esta aplicación está diseñada para acompañarte en tu día a día. Cualquier persona puede crear su cuenta desde **Crear una cuenta** (elige si eres paciente o supervisor) e iniciar sesión con su nombre de usuario.

- **Usuarios Dependientes**: Podréis crear alarmas sencillas o repetitivas (como beber agua o tomar una medicación), pulsar el botón SOS si os encontráis en una emergencia, consultar vuestros datos de salud y registrar vuestro peso. Para que un familiar os supervise, generad un código de vinculación (o enseñadle el QR): caduca a los 10 minutos y solo sirve una vez.
- **Usuarios Supervisores**: Podréis vincular vuestra cuenta a la de un familiar dependiente escribiendo su código o escaneando su QR, para establecer un seguimiento constante de sus rutinas. Además, tendréis un panel donde veréis las alertas médicas de manera instantánea y los recordatorios sin confirmar.
- **Gráficos de salud (supervisores)**: desde el panel, el botón **Ver gráficos de salud** abre en otra pestaña la evolución del peso, el porcentaje de tomas confirmadas de los últimos 14 días y el registro de medicamentos del paciente. Es una pantalla de solo consulta. Mantened abierta la pestaña del panel: es la que hace sonar las alertas SOS.
- **Aviso de reloj**: si la hora del móvil de un paciente difiere más de 5 minutos de la del servidor, la pantalla del paciente muestra un aviso para que la corrija, porque las alarmas suenan según el reloj del móvil.

## 5. Instalación y Ejecución del Entorno

Para ejecutar el código Python que da el enlace a la web con Flask, en la terminal de VS Code hay que poner los comandos:

1. Crear y activar el entorno virtual (solo la primera vez se crea):
   - `python3 -m venv venv`
   - `source venv/bin/activate`
2. Instalar las dependencias: `pip install -r backend/requirements.txt`
3. Crear los datos de prueba (solo la primera vez): `python3 backend/seed.py`
   Crea dos usuarios de ejemplo: `alberto` (supervisor) y `maria` (paciente), ambos con contraseña `1234`.
4. Arrancar la aplicación: `python3 backend/app.py` y abrir http://127.0.0.1:5000

### Pruebas

1. `python3 backend/backup_bd.py` (copia de seguridad de la base de datos)
2. `cd backend`
3. Todas a la vez: `python3 -m unittest discover -p "test_*.py" -v`
4. O una a una, por ejemplo:
   - `python3 -m unittest test_app -v`
   - `python3 -m unittest test_registro -v`
   - `python3 -m unittest test_vinculos -v`
   - `python3 -m unittest test_reloj -v`
   - `python3 -m unittest test_supervisor_salud -v`

Las pruebas de JavaScript se comprueban con ESLint (`npm install` y después `npx eslint`), y el mismo análisis y los tests se ejecutan automáticamente en GitHub Actions en cada push.

## 6. Documentación

- **[Wiki del proyecto](https://github.com/acueva03/PROYECTO-APP-SALUD/wiki)**: páginas detalladas de cada funcionalidad.
- **Carpeta [`doc/`](doc)**: documento de riesgos y resto de documentación del Sprint.

(Añadiremos aquí las instrucciones detalladas paso a paso sobre cómo instalar y utilizar nuestra app).
