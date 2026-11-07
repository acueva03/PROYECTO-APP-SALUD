import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'   # SIEMPRE antes de importar app

import unittest
from app import app
from models import db, User


class BaseTest(unittest.TestCase):

    def setUp(self):
        uri = app.config['SQLALCHEMY_DATABASE_URI']
        if ':memory:' not in uri:
            raise RuntimeError(f'¡Los tests apuntan a una BD real! ({uri})')

        app.config['TESTING'] = True
        self.cliente = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()

        self.maria = User(nombre='María', username='maria', rol='dependiente')
        self.alberto = User(nombre='Alberto', username='alberto', rol='supervisor')
        for u in (self.maria, self.alberto):
            u.set_password('1234')
        self.alberto.dependientes.append(self.maria)
        db.session.add_all([self.maria, self.alberto])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, username, password='1234'):
        return self.cliente.post('/login', data={'username': username, 'password': password})