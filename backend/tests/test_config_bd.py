from base_tests import BaseTest      # primero: fija DATABASE_URL en memoria antes de importar app

import unittest
from datetime import timedelta
from unittest.mock import patch
from sqlalchemy import text

from app import actualizar_columnas
from config_bd import url_base_de_datos, opciones_motor, describir_url, es_sqlite
from models import db, hoy_madrid


class TestUrlBaseDeDatos(unittest.TestCase):
    def test_sin_variable_usa_sqlite_local(self):
        self.assertEqual(url_base_de_datos({}, '/ruta/app_salud.db'), 'sqlite:////ruta/app_salud.db')

    def test_variable_vacia_usa_sqlite_local(self):
        self.assertEqual(url_base_de_datos({'DATABASE_URL': '  '}, 'x.db'), 'sqlite:///x.db')

    def test_la_variable_tiene_prioridad(self):
        self.assertEqual(url_base_de_datos({'DATABASE_URL': 'sqlite:///:memory:'}, 'x.db'), 'sqlite:///:memory:')

    def test_postgres_a_postgresql_con_driver(self):
        # Render, Heroku y otros dan "postgres://", pero SQLAlchemy solo entiende "postgresql://"
        url = url_base_de_datos({'DATABASE_URL': 'postgres://u:p@host/bd'}, 'x.db')
        self.assertEqual(url, 'postgresql+psycopg2://u:p@host/bd')

    def test_postgresql_recibe_el_driver_psycopg2(self):
        # Sin driver, SQLAlchemy 2.1 busca psycopg (v3), que no está instalado: la app no arrancaba en Render
        url = url_base_de_datos({'DATABASE_URL': 'postgresql://u:p@host/bd?sslmode=require'}, 'x.db')
        self.assertEqual(url, 'postgresql+psycopg2://u:p@host/bd?sslmode=require')

    def test_un_driver_explicito_se_respeta(self):
        url = 'postgresql+psycopg://u:p@host/bd'
        self.assertEqual(url_base_de_datos({'DATABASE_URL': url}, 'x.db'), url)

    def test_la_url_resultante_usa_el_dialecto_psycopg2(self):
        # Se comprueba con SQLAlchemy de verdad (sin conectar): el driver elegido es psycopg2
        from sqlalchemy.engine import make_url
        url = url_base_de_datos({'DATABASE_URL': 'postgres://u:p@host/bd'}, 'x.db')
        self.assertEqual(make_url(url).get_dialect().driver, 'psycopg2')


class TestOpcionesMotor(unittest.TestCase):
    def test_sqlite_conserva_sus_opciones(self):
        opciones = opciones_motor('sqlite:///app_salud.db')
        self.assertEqual(opciones['connect_args'], {'check_same_thread': False, 'timeout': 15})

    def test_postgres_no_lleva_opciones_de_sqlite(self):
        # check_same_thread rompe la conexión con PostgreSQL
        opciones = opciones_motor('postgresql://u:p@host/bd')
        self.assertNotIn('connect_args', opciones)
        self.assertTrue(opciones['pool_pre_ping'])
        self.assertLess(opciones['pool_recycle'], 300)

    def test_es_sqlite(self):
        self.assertTrue(es_sqlite('sqlite:///:memory:'))
        self.assertFalse(es_sqlite('postgresql://u:p@host/bd'))


class TestDescribirUrl(unittest.TestCase):
    def test_oculta_la_contrasena(self):
        texto = describir_url('postgresql://usuario:secreto123@host.example/bd')
        self.assertNotIn('secreto123', texto)
        self.assertIn('host.example', texto)

    def test_url_mal_escrita_no_lanza_error(self):
        self.assertIn('no válida', describir_url('esto no es una url'))


class TestActualizarColumnasSqlPortable(BaseTest):
    """actualizar_columnas() ya no usa 'DEFAULT 0' ni 'activa = 1' (PostgreSQL no los acepta con booleanos).
    Se comprueba que sigue actualizando una base antigua en SQLite."""

    def test_anade_columnas_y_rellena_la_fecha(self):
        db.drop_all()
        # tablas "de antes": sin las columnas que se añadieron en sprints posteriores
        db.session.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, nombre VARCHAR(100), rol VARCHAR(20))'))
        db.session.execute(text('CREATE TABLE registros_toma (id INTEGER PRIMARY KEY, titulo VARCHAR(100))'))
        db.session.execute(text('CREATE TABLE alarms (id INTEGER PRIMARY KEY, user_id INTEGER, titulo VARCHAR(100), '
                                'hora VARCHAR(5), es_repetitiva BOOLEAN, activa BOOLEAN)'))
        db.session.execute(text("INSERT INTO alarms (user_id, titulo, hora, es_repetitiva, activa) "
                                "VALUES (1, 'Activa', '08:00', 0, 1), (1, 'Pausada', '09:00', 0, 0)"))
        db.session.commit()

        actualizar_columnas()

        columnas = {fila[1] for fila in db.session.execute(text('PRAGMA table_info(alarms)'))}
        self.assertTrue({'fecha', 'dosis', 'dias_semana', 'eliminada', 'eliminada_en'} <= columnas)
        filas = {f.titulo: f for f in db.session.execute(
            text('SELECT titulo, fecha, eliminada FROM alarms')).fetchall()}
        self.assertEqual(filas['Activa'].fecha, hoy_madrid().isoformat())   # la activa recibe fecha
        self.assertIsNone(filas['Pausada'].fecha)                           # la pausada no
        self.assertFalse(filas['Activa'].eliminada)                         # DEFAULT FALSE: no eliminada

    def test_es_idempotente(self):
        actualizar_columnas()
        actualizar_columnas()     # una segunda vez no debe fallar ni duplicar columnas


class TestTituloAlarmaLargo(BaseTest):
    """La columna es VARCHAR(100): PostgreSQL rechaza un título más largo (SQLite no)."""

    def _crear(self, titulo):
        self.login('maria')
        manana = (hoy_madrid() + timedelta(days=1)).isoformat()
        return self.cliente.post('/api/alarmas', json={'titulo': titulo, 'hora': '08:00', 'fecha': manana})

    def test_titulo_de_100_caracteres_vale(self):
        self.assertEqual(self._crear('a' * 100).status_code, 201)

    def test_titulo_de_101_caracteres_da_400(self):
        r = self._crear('a' * 101)
        self.assertEqual(r.status_code, 400)
        self.assertIn('100', r.get_json()['error'])

    def test_no_se_guarda_la_alarma_rechazada(self):
        self.assertEqual(self._crear('a' * 101).status_code, 400)
        self.assertEqual(self.cliente.get('/api/mis-alarmas').get_json(), [])


class TestSalud(BaseTest):
    """/salud: healthcheck del servidor en la nube (Render lo consulta para saber si la app está viva)."""

    def test_responde_ok_sin_sesion(self):
        r = self.cliente.get('/salud')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {'ok': True})

    def test_no_devuelve_datos_personales(self):
        self.login('maria')
        self.assertEqual(self.cliente.get('/salud').get_json(), {'ok': True})

    def test_503_si_la_base_de_datos_no_responde(self):
        with patch('app.db.session.execute', side_effect=RuntimeError('sin conexión')):
            r = self.cliente.get('/salud')
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.get_json(), {'ok': False})


if __name__ == '__main__':
    unittest.main()
