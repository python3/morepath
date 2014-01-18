import morepath
from morepath import setup
from morepath.request import Response
from morepath.converter import Converter

from werkzeug.test import Client
import pytest


def test_simple_path_one_step():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self):
            pass

    @app.model(model=Model, path='simple')
    def get_model():
        return Model()

    @app.view(model=Model)
    def default(request, model):
        return "View"

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('/simple')
    assert response.data == 'View'

    response = c.get('/simple/link')
    assert response.data == '/simple'


def test_simple_path_two_steps():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self):
            pass

    @app.model(model=Model, path='one/two')
    def get_model():
        return Model()

    @app.view(model=Model)
    def default(request, model):
        return "View"

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('/one/two')
    assert response.data == 'View'

    response = c.get('/one/two/link')
    assert response.data == '/one/two'


def test_variable_path_one_step():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, name):
            self.name = name

    @app.model(model=Model, path='{name}')
    def get_model(name):
        return Model(name)

    @app.view(model=Model)
    def default(request, model):
        return "View: %s" % model.name

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('/foo')
    assert response.data == 'View: foo'

    response = c.get('/foo/link')
    assert response.data == '/foo'


def test_variable_path_two_steps():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, name):
            self.name = name

    @app.model(model=Model, path='document/{name}')
    def get_model(name):
        return Model(name)

    @app.view(model=Model)
    def default(request, model):
        return "View: %s" % model.name

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('/document/foo')
    assert response.data == 'View: foo'

    response = c.get('/document/foo/link')
    assert response.data == '/document/foo'


def test_variable_path_two_variables():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, name, version):
            self.name = name
            self.version = version

    @app.model(model=Model, path='{name}-{version}')
    def get_model(name, version):
        return Model(name, version)

    @app.view(model=Model)
    def default(request, model):
        return "View: %s %s" % (model.name, model.version)

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('foo-one')
    assert response.data == 'View: foo one'

    response = c.get('/foo-one/link')
    assert response.data == '/foo-one'


def test_variable_path_explicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.model(model=Model, path='{id}',
               converters=dict(id=Converter(int)))
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(request, model):
        return "View: %s (%s)" % (model.id, type(model.id))

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('1')
    assert response.data == "View: 1 (<type 'int'>)"

    response = c.get('/1/link')
    assert response.data == '/1'

    response = c.get('broken')
    assert response.status == '404 NOT FOUND'


def test_variable_path_implicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.model(model=Model, path='{id}')
    def get_model(id=0):
        return Model(id)

    @app.view(model=Model)
    def default(request, model):
        return "View: %s (%s)" % (model.id, type(model.id))

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('1')
    assert response.data == "View: 1 (<type 'int'>)"

    response = c.get('/1/link')
    assert response.data == '/1'

    response = c.get('broken')
    assert response.status == '404 NOT FOUND'


def test_url_parameter_explicit_converter():
    config = setup()
    app = morepath.App(testing_config=config)

    class Model(object):
        def __init__(self, id):
            self.id = id

    @app.model(model=Model, path='/',
               converters=dict(id=Converter(int)))
    def get_model(id):
        return Model(id)

    @app.view(model=Model)
    def default(request, model):
        return "View: %s (%s)" % (model.id, type(model.id))

    @app.view(model=Model, name='link')
    def link(request, model):
        return request.link(model)

    config.commit()

    c = Client(app, Response)

    response = c.get('/?id=1')
    assert response.data == "View: 1 (<type 'int'>)"

    response = c.get('/link?id=1')
    assert response.data == '/?id=1'

    response = c.get('/?id=broken')
    assert response.status == '400 BAD REQUEST'
