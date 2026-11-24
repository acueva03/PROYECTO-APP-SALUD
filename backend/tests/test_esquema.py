import unittest
from sqlalchemy import text
from base_tests import BaseTest
from esquema import comprobar_esquema
from models import db


class TestEsquema(BaseTest):
    def test_esquema_correcto(self):
        comprobar_esquema(db)

    def test_detecta_columna_que_falta(self):
        db.drop_all()
        db.session.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, nombre VARCHAR(100))'))
        db.session.commit()
        with self.assertRaises(RuntimeError) as cm:
            comprobar_esquema(db)
        self.assertIn('users.username', str(cm.exception))


if __name__ == '__main__':
    unittest.main()