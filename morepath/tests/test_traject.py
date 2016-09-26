import dectate
import morepath
from morepath.traject import (TrajectRegistry,
                              Node, Step, TrajectError,
                              is_identifier, parse_variables,
                              Path, create_path, parse_path,
                              normalize_path,
                              ParameterFactory)
from morepath.converter import Converter, IDENTITY_CONVERTER
import pytest
from webob.exc import HTTPBadRequest
import webob


def traject_consume():
    pass


class Root(object):
    pass


class Model(object):
    pass


class Special(object):
    pass


def test_name_step():
    step = Step('foo')
    assert step.s == 'foo'
    assert step.generalized == 'foo'
    assert step.parts == ('foo',)
    assert step.names == []
    assert step.converters == {}
    assert step.discriminator_info() == 'foo'

    assert not step.has_variables()
    variables = {}
    assert step.match('foo', variables, set())
    assert variables == {}
    assert not step.match('bar', variables, set())
    assert variables == {}


def test_variable_step():
    step = Step('{foo}')
    assert step.s == '{foo}'
    assert step.generalized == '{}'
    assert step.parts == ('', '')
    assert step.names == ['foo']
    assert step.converters == {}
    assert step.has_variables()
    assert step.discriminator_info() == '{}'

    variables = {}
    assert step.match('bar', variables, set(['foo']))
    assert variables == {'foo': 'bar'}
    # if we don't include it in the set we won't extract it
    variables = {}
    assert step.match('bar', variables, set())
    assert variables == {}


def test_mixed_step():
    step = Step('a{foo}b')
    assert step.s == 'a{foo}b'
    assert step.generalized == 'a{}b'
    assert step.parts == ('a', 'b')
    assert step.names == ['foo']
    assert step.converters == {}
    assert step.has_variables()
    assert step.discriminator_info() == 'a{}b'

    names = set(['foo'])

    variables = {}
    assert step.match('abarb', variables, names)
    assert variables == {'foo': 'bar'}

    variables = {}
    assert not step.match('ab', variables, names)
    assert not variables

    variables = {}
    assert not step.match('xbary', variables, names)
    assert not variables

    variables = {}
    assert not step.match('yabarbx', variables, names)
    assert not variables

    variables = {}
    assert not step.match('afoo', variables, names)
    assert not variables


def test_multi_mixed_step():
    step = Step('{foo}a{bar}')
    assert step.s == '{foo}a{bar}'
    assert step.generalized == '{}a{}'
    assert step.parts == ('', 'a', '')
    assert step.names == ['foo', 'bar']
    assert step.converters == {}
    assert step.has_variables()
    assert step.discriminator_info() == '{}a{}'


def test_converter():
    step = Step('{foo}', converters=dict(foo=Converter(int)))
    assert step.discriminator_info() == '{}'

    names = set(['foo'])

    variables = {}
    assert step.match('1', variables, names)
    assert variables == {'foo': 1}

    variables = {}
    assert not step.match('x', variables, names)
    assert not variables


def sorted_steps(l):
    steps = [Step(s) for s in l]
    return [step.s for step in sorted(steps)]


def test_steps_the_same():
    step1 = Step('{foo}')
    step2 = Step('{foo}')
    assert step1 == step2
    assert not step1 != step2
    assert not step1 < step2
    assert not step1 > step2
    assert step1 >= step2
    assert step1 <= step2


def test_step_different():
    step1 = Step('{foo}')
    step2 = Step('bar')
    assert step1 != step2
    assert not step1 == step2
    assert not step1 < step2
    assert step1 > step2
    assert step1 >= step2
    assert not step1 <= step2


def test_order_prefix_earlier():
    assert sorted_steps(['{foo}', 'prefix{foo}']) == [
        'prefix{foo}', '{foo}']


def test_order_postfix_earlier():
    assert sorted_steps(['{foo}', '{foo}postfix']) == [
        '{foo}postfix', '{foo}']


def test_order_prefix_before_postfix():
    assert sorted_steps(['{foo}', 'a{foo}', '{foo}a']) == [
        'a{foo}', '{foo}a', '{foo}']


def test_order_prefix_before_postfix2():
    assert sorted_steps(['{foo}', 'a{foo}', '{foo}b']) == [
        'a{foo}', '{foo}b', '{foo}']


def test_order_longer_prefix_before_shorter():
    assert sorted_steps(['ab{f}', 'a{f}']) == [
        'ab{f}', 'a{f}']


def test_order_longer_postfix_before_shorter():
    assert sorted_steps(['{f}ab', '{f}b']) == [
        '{f}ab', '{f}b']


def test_order_dont_care_variable_names():
    assert sorted_steps(['a{f}', 'ab{g}']) == [
        'ab{g}', 'a{f}']


def test_order_two_variables_before_one():
    assert sorted_steps(['{a}x{b}', '{a}']) == [
        '{a}x{b}', '{a}']


def test_order_two_variables_before_with_postfix():
    assert sorted_steps(['{a}x{b}x', '{a}x']) == [
        '{a}x{b}x', '{a}x']


def test_order_two_variables_before_with_prefix():
    assert sorted_steps(['x{a}x{b}', 'x{a}']) == [
        'x{a}x{b}', 'x{a}']


def test_order_two_variables_infix():
    assert sorted_steps(['{a}xyz{b}', '{a}xy{b}', '{a}yz{b}', '{a}x{b}',
                         '{a}z{b}', '{a}y{b}']) == [
        '{a}xyz{b}', '{a}yz{b}', '{a}z{b}', '{a}xy{b}', '{a}y{b}', '{a}x{b}']


def test_order_alphabetical():
    # reverse alphabetical
    assert sorted_steps(['a{f}', 'b{f}']) == [
        'b{f}', 'a{f}']
    assert sorted_steps(['{f}a', '{f}b']) == [
        '{f}b', '{f}a']


def test_invalid_step():
    with pytest.raises(TrajectError):
        Step('{foo')


def test_illegal_consecutive_variables():
    with pytest.raises(TrajectError):
        Step('{a}{b}')


def test_illegal_variable():
    with pytest.raises(TrajectError):
        Step('{a:int:int}')


def test_illegal_identifier():
    with pytest.raises(TrajectError):
        Step('{1}')


def test_unknown_converter():
    with pytest.raises(TrajectError):
        Step('{foo:blurb}')


def test_name_node():
    node = Node()
    step_node = node.add(Step('foo'))
    variables = {}
    assert node.resolve('foo', variables) is step_node
    assert not variables

    assert node.resolve('bar', variables) is None
    assert not variables


def test_variable_node():
    node = Node()

    step_node = node.add(Step('{x}'))
    step_node.model_args = set(['x'])
    variables = {}
    assert node.resolve('foo', variables) is step_node
    assert variables == {'x': 'foo'}

    variables = {}
    assert node.resolve('bar', variables) is step_node
    assert variables == {'x': 'bar'}


def test_mixed_node():
    node = Node()
    step_node = node.add(Step('prefix{x}postfix'))
    step_node.model_args = set(['x'])

    variables = {}
    assert node.resolve('prefixfoopostfix', variables) is step_node
    assert variables == {'x': 'foo'}

    variables = {}
    assert node.resolve('prefixbarpostfix', variables) is step_node
    assert variables == {'x': 'bar'}

    variables = {}
    assert node.resolve('prefixwhat', variables) is None
    assert variables == {}


def test_variable_node_specific_first():
    node = Node()
    x_node = node.add(Step('{x}'))
    x_node.model_args = set(['x'])

    prefix_node = node.add(Step('prefix{x}'))
    prefix_node.model_args = set(['x'])

    variables = {}
    assert node.resolve('what', variables) is x_node
    assert variables == {'x': 'what'}

    variables = {}
    assert node.resolve('prefixwhat', variables) is prefix_node
    assert variables == {'x': 'what'}


def test_variable_node_more_specific_first():
    node = Node()
    xy_node = node.add(Step('x{x}y'))
    xy_node.model_args = set(['x'])
    xay_node = node.add(Step('xa{x}y'))
    xay_node.model_args = set(['x'])
    ay_node = node.add(Step('a{x}y'))
    ay_node.model_args = set(['x'])

    variables = {}
    assert node.resolve('xwhaty', variables) is xy_node
    assert variables == {'x': 'what'}

    variables = {}
    assert node.resolve('xawhaty', variables) is xay_node
    assert variables == {'x': 'what'}

    variables = {}
    assert node.resolve('awhaty', variables) is ay_node
    assert variables == {'x': 'what'}


def test_variable_node_optional_colon():
    node = Node()
    x_node = node.add(Step('{x}'))
    x_node.model_args = set(['x'])
    xy_node = node.add(Step('{x}:{y}'))
    xy_node.model_args = set(['x', 'y'])

    variables = {}
    assert node.resolve('a', variables) is x_node
    assert variables == {'x': 'a'}

    variables = {}
    assert node.resolve('a:b', variables) is xy_node
    assert variables == {'x': 'a', 'y': 'b'}


def req(path):
    return morepath.Request({'PATH_INFO': path}, morepath.App())


def test_traject_simple():
    traject = TrajectRegistry()
    class abc(object):
        pass
    class abd(object):
        pass
    class xy():
        pass
    class xz():
        pass
    traject.add_pattern('a/b/c', abc)
    traject.add_pattern('a/b/d', abd)
    traject.add_pattern('x/y', xy)
    traject.add_pattern('x/z', xz)

    assert isinstance(traject.consume(req('a/b/c')), abc)
    assert isinstance(traject.consume(req('a/b/d')), abd)
    assert isinstance(traject.consume(req('x/y')), xy)
    assert isinstance(traject.consume(req('x/z')), xz)
    r = req('a/b/c/d')
    assert isinstance(traject.consume(r, abc))
    assert req.unconsumed == ['d']

    r = req('a/b/d/d')
    assert isinstance(traject.consume(r, abd))
    assert req.unconsumed == ['d']

    assert traject.consume(['c', 'b', 'a']) == ('abc', [], {})
    assert traject.consume(['d', 'b', 'a']) == ('abd', [], {})
    assert traject.consume(['y', 'x']) == ('xy', [], {})
    assert traject.consume(['z', 'x']) == ('xz', [], {})
    assert traject.consume(['d', 'c', 'b', 'a']) == ('abc', ['d'], {})
    assert traject.consume(['d', 'd', 'b', 'a']) == ('abd', ['d'], {})
    assert traject.consume(['3', '2', '1', 'y', 'x']) == (
        'xy', ['3', '2', '1'], {})
    assert traject.consume(['3', '2', '1']) == (None, ['3', '2', '1'], {})
    assert traject.consume(['b', 'a']) == (None, [], {})


def test_traject_variable_specific_first():
    traject = TrajectRegistry()
    traject.add_pattern('a/{x}/b', 'axb')
    traject.add_pattern('a/prefix{x}/b', 'aprefixxb')
    assert traject.consume(['b', 'lah', 'a']) == ('axb', [], {'x': 'lah'})
    assert traject.consume(['b', 'prefixlah', 'a']) == (
        'aprefixxb', [], {'x': 'lah'})


def test_traject_multiple_steps_with_variables():
    traject = TrajectRegistry()
    traject.add_pattern('{x}/{y}', 'xy')
    assert traject.consume(['y', 'x']) == ('xy', [], {'x': 'x', 'y': 'y'})


def test_traject_with_converter():
    traject = TrajectRegistry()
    traject.add_pattern('{x}', 'found', dict(x=Converter(int)))
    assert traject.consume(['1']) == ('found', [], {'x': 1})
    assert traject.consume(['foo']) == (None, ['foo'], {})


def test_traject_type_conflict():
    traject = TrajectRegistry()
    traject.add_pattern('{x}', 'found_int', dict(x=Converter(int)))
    with pytest.raises(TrajectError):
        traject.add_pattern('{x}', 'found_str', dict(x=Converter(str)))


def test_traject_type_conflict_default_type():
    traject = TrajectRegistry()
    traject.add_pattern('{x}', 'found_str')
    with pytest.raises(TrajectError):
        traject.add_pattern('{x}', 'found_int', dict(x=Converter(int)))


def test_traject_type_conflict_explicit_default():
    traject = TrajectRegistry()
    traject.add_pattern('{x}', 'found_explicit', dict(x=IDENTITY_CONVERTER))
    traject.add_pattern('{x}', 'found_implicit')
    # these add_pattern calls are equivalent so will not result in an error
    assert True


def test_traject_type_conflict_middle():
    traject = TrajectRegistry()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    with pytest.raises(TrajectError):
        traject.add_pattern('a/{x}/z', 'str')


def test_traject_no_type_conflict_middle():
    traject = TrajectRegistry()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    traject.add_pattern('a/{x}/z', 'int2', dict(x=Converter(int)))


def test_traject_greedy_middle_prefix():
    traject = TrajectRegistry()
    traject.add_pattern('a/prefix{x}/y', 'prefix')
    traject.add_pattern('a/{x}/z', 'no_prefix')

    assert traject.consume(['y', 'prefixX', 'a']) == ('prefix', [], {'x': 'X'})
    assert traject.consume(['z', 'prefixX', 'a']) == (None, ['z'], {'x': 'X'})
    assert traject.consume(['z', 'blah', 'a']) == (
        'no_prefix', [], {'x': 'blah'})


def test_traject_type_conflict_middle_end():
    traject = TrajectRegistry()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    with pytest.raises(TrajectError):
        traject.add_pattern('a/{x}', 'str')


def test_traject_no_type_conflict_middle_end():
    traject = TrajectRegistry()
    traject.add_pattern('a/{x}/y', 'int', dict(x=Converter(int)))
    traject.add_pattern('a/{x}', 'int2', dict(x=Converter(int)))
    assert True


def test_parse_path():
    assert parse_path(u'/a/b/c') == [u'a', u'b', u'c']


def test_parse_path_empty():
    assert parse_path(u'') == []


def test_parse_path_slash():
    assert parse_path(u'/') == []


def test_parse_path_no_slash():
    assert parse_path('a/b/c') == ['a', 'b', 'c']


def test_parse_path_end_slash():
    assert parse_path('a/b/c/') == ['a', 'b', 'c']


def test_parse_path_multi_slash():
    assert parse_path(u'/a/b/c') == parse_path(u'/a//b/c')
    assert parse_path(u'/a/b/c') == parse_path(u'/a///b/c')


def test_parse_path_dots():
    assert parse_path(u'/a/b/../c') == parse_path(u'/a/c')


def test_parse_path_single_dots():
    assert parse_path(u'/a/./b') == parse_path(u'/a/b')
    assert parse_path(u'./a/b') == parse_path(u'/a/b')


def test_parse_path_dots_start():
    assert parse_path(u'/../a/b') == parse_path(u'/a/b')


def test_create_path():
    assert create_path(['a', 'b', 'c']) == '/a/b/c'
    assert create_path([]) == '/'


def test_normalize_path():
    assert normalize_path('/a/..') == '/'
    assert normalize_path('/a/../../../../b') == '/b'
    assert normalize_path('/a/../c') == '/c'
    assert normalize_path('/a/../../a/') == '/a'
    assert normalize_path('/') == '/'
    assert normalize_path('') == '/'
    assert normalize_path('../../') == '/'
    assert normalize_path('../static//../app.py') == '/app.py'
    assert normalize_path('../a//b/') == '/a/b'
    assert normalize_path('/////a/////../b') == '/b'
    assert normalize_path('//foo') == '/foo'
    assert normalize_path('/a/b/c/../..') == '/a'
    assert normalize_path('/a/b/c/../../d') == '/a/d'


def test_identifier():
    assert is_identifier('a')
    not is_identifier('')
    assert is_identifier('a1')
    assert not is_identifier('1')
    assert is_identifier('_')
    assert is_identifier('_foo')
    assert is_identifier('foo')
    assert not is_identifier('.')


def test_parse_variables():
    assert parse_variables('No variables') == []
    assert parse_variables('The {foo} is the {bar}.') == ['foo', 'bar']
    with pytest.raises(TrajectError):
        parse_variables('{}')
    with pytest.raises(TrajectError):
        parse_variables('{1illegal}')


def consume(app, path):
    request = app.request(webob.Request.blank(path).environ)
    return traject_consume(app, request), request

paramfac = ParameterFactory({}, {}, [])


def test_traject_consume():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry
    traject.add_pattern('sub', (Model, paramfac))

    mount = app()

    found, request = consume(mount, 'sub')
    assert isinstance(found, Model)
    assert request.unconsumed == []


def test_traject_consume_parameter():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    class Model(object):
        def __init__(self, a):
            self.a = a

    get_param = ParameterFactory({'a': 0}, {'a': Converter(int)}, [])
    traject.add_pattern('sub', (Model, get_param))

    mount = app()

    found, request = consume(mount, 'sub?a=1')
    assert isinstance(found, Model)
    assert found.a == 1
    assert request.unconsumed == []
    found, request = consume(mount, 'sub')
    assert isinstance(found, Model)
    assert found.a == 0
    assert request.unconsumed == []


def test_traject_consume_model_factory_gets_request():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    class Model(object):
        def __init__(self, info):
            self.info = info

    def get_model(request):
        return Model(request.method)

    traject.add_pattern('sub', (get_model, paramfac))

    mount = app()

    found, request = consume(mount, 'sub')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    assert found.info == 'GET'


def test_traject_consume_not_found():
    class app(morepath.App):
        pass

    dectate.commit(app)

    found, request = consume(app(), 'sub')
    assert found is None
    assert request.unconsumed == ['sub']


def test_traject_consume_factory_returns_none():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    def get_model():
        return None

    traject.add_pattern('sub', (get_model, paramfac))

    found, request = consume(app(), 'sub')

    assert found is None
    assert request.unconsumed == ['sub']


def test_traject_consume_variable():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    def get_model(foo):
        result = Model()
        result.foo = foo
        return result

    traject.add_pattern('{foo}', (get_model, paramfac))

    found, request = consume(app(), 'something')
    assert isinstance(found, Model)
    assert found.foo == 'something'
    assert request.unconsumed == []


def test_traject_consume_view():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    def get_model(foo):
        result = Model()
        result.foo = foo
        return result

    traject.add_pattern('', (Root, paramfac))
    traject.add_pattern('{foo}', (get_model, paramfac))

    found, request = consume(app(), '+something')
    assert isinstance(found, Root)
    assert request.unconsumed == ['+something']


def test_traject_root():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    traject.add_pattern('', (Root, paramfac))

    found, request = consume(app(), '')
    assert isinstance(found, Root)
    assert request.unconsumed == []


def test_traject_consume_combination():

    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    def get_model(foo):
        result = Model()
        result.foo = foo
        return result

    traject.add_pattern('special', (Special, paramfac))
    traject.add_pattern('{foo}', (get_model, paramfac))

    mount = app()

    found, request = consume(mount, 'something')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    assert found.foo == 'something'

    found, request = consume(mount, 'special')
    assert isinstance(found, Special)
    assert request.unconsumed == []


def test_traject_nested():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry
    traject.add_pattern('a', (Model, paramfac))
    traject.add_pattern('a/b', (Special, paramfac))

    mount = app()

    found, request = consume(mount, 'a')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(mount, 'a/b')
    assert isinstance(found, Special)
    assert request.unconsumed == []


def test_traject_nested_not_resolved_entirely_by_consumer():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry
    traject.add_pattern('a', (Model, paramfac))

    mount = app()

    found, request = consume(mount, 'a')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(mount, 'a/b')
    assert isinstance(found, Model)
    assert request.unconsumed == ['b']


def test_traject_nested_with_variable():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    def get_model(id):
        result = Model()
        result.id = id
        return result

    def get_special(id):
        result = Special()
        result.id = id
        return result

    traject.add_pattern('{id}', (get_model, paramfac))
    traject.add_pattern('{id}/sub', (get_special, paramfac))

    mount = app()

    found, request = consume(mount, 'a')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(mount, 'b')
    assert isinstance(found, Model)
    assert request.unconsumed == []
    found, request = consume(mount, 'a/sub')
    assert isinstance(found, Special)
    assert request.unconsumed == []


def test_traject_with_multiple_variables():
    class app(morepath.App):
        pass

    dectate.commit(app)

    traject = app.config.path_registry

    def get_model(first_id):
        result = Model()
        result.first_id = first_id
        return result

    def get_special(first_id, second_id):
        result = Special()
        result.first_id = first_id
        result.second_id = second_id
        return result
    traject.add_pattern('{first_id}', (get_model, paramfac))
    traject.add_pattern('{first_id}/{second_id}', (get_special, paramfac))

    mount = app()

    found, request = consume(mount, 'a')
    assert isinstance(found, Model)
    assert found.first_id == 'a'
    assert not hasattr(found, 'second_id')
    assert request.unconsumed == []

    found, request = consume(mount, 'a/b')
    assert isinstance(found, Special)
    assert found.first_id == 'a'
    assert found.second_id == 'b'
    assert request.unconsumed == []


def test_traject_no_concecutive_variables():
    traject = TrajectRegistry()

    with pytest.raises(TrajectError):
        traject.add_pattern('{foo}{bar}', 'value')


def test_traject_no_duplicate_variables():
    traject = TrajectRegistry()

    with pytest.raises(TrajectError):
        traject.add_pattern('{foo}-{foo}', 'value')
    with pytest.raises(TrajectError):
        traject.add_pattern('{foo}/{foo}', 'value')


def test_interpolation_str():
    assert Path('{foo} is {bar}').interpolation_str() == '%(foo)s is %(bar)s'


def test_path_discriminator():
    p = Path('/foo/{x}/bar/{y}')
    assert p.discriminator() == 'foo/{}/bar/{}'


def fake_request(path):
    return webob.Request.blank(path)


def test_empty_parameter_factory():
    get_parameters = ParameterFactory({}, {}, [])
    assert get_parameters(fake_request('')) == {}
    # unexpected parameter is ignored
    assert get_parameters(fake_request('?a=A')) == {}


def test_single_parameter():
    get_parameters = ParameterFactory({'a': None}, {'a': Converter(str)}, [])
    assert get_parameters(fake_request('?a=A')) == {'a': 'A'}
    assert get_parameters(fake_request('')) == {'a': None}


def test_single_parameter_int():
    get_parameters = ParameterFactory({'a': None}, {'a': Converter(int)}, [])
    assert get_parameters(fake_request('?a=1')) == {'a': 1}
    assert get_parameters(fake_request('')) == {'a': None}
    with pytest.raises(HTTPBadRequest):
        get_parameters(fake_request('?a=A'))


def test_single_parameter_default():
    get_parameters = ParameterFactory({'a': 'default'}, {}, [])
    assert get_parameters(fake_request('?a=A')) == {'a': 'A'}
    assert get_parameters(fake_request('')) == {'a': 'default'}


def test_single_parameter_int_default():
    get_parameters = ParameterFactory({'a': 0}, {'a': Converter(int)}, [])
    assert get_parameters(fake_request('?a=1')) == {'a': 1}
    assert get_parameters(fake_request('')) == {'a': 0}
    with pytest.raises(HTTPBadRequest):
        get_parameters(fake_request('?a=A'))


def test_parameter_required():
    get_parameters = ParameterFactory({'a': None}, {}, ['a'])
    assert get_parameters(fake_request('?a=foo')) == {'a': 'foo'}
    with pytest.raises(HTTPBadRequest):
        get_parameters(fake_request(''))


def test_extra_parameters():
    get_parameters = ParameterFactory({'a': None}, {}, [], True)
    assert get_parameters(fake_request('?a=foo')) == {
        'a': 'foo',
        'extra_parameters': {}}
    assert get_parameters(fake_request('?b=foo')) == {
        'a': None,
        'extra_parameters': {'b': 'foo'}}
    assert get_parameters(fake_request('?a=foo&b=bar')) == {
        'a': 'foo',
        'extra_parameters': {'b': 'bar'}}
