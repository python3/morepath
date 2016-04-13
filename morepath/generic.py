import reg


@reg.dispatch('obj')
def path(obj):
    """Get the path and parameters for an object in its own application.
    """
    return None


@reg.dispatch(reg.match_class('cls', lambda cls: cls))
def class_path(cls, variables):
    """Get the path for a class.
    """
    return None


@reg.dispatch('obj')
def deferred_link_app(mounted, obj):
    return None


@reg.dispatch_external_predicates()
def view(obj, request):
    """Get the view that represents the obj in the context of a request.

    This view is a representation of the obj that can be rendered to
    a response. It may also return a Response directly. If a string is
    returned, the string is converted to a Response with the string as
    the response body.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.dispatch()
def settings():
    """Return current settings object.

    In it are sections, and inside of the sections are the setting values.
    If there is a ``logging`` section and a ``loglevel`` setting in it,
    this is how you would access it::

      settings().logging.loglevel

    """
    raise NotImplementedError  # pragma: nocoverage


@reg.dispatch()
def identify(request):
    """Returns an Identity or None if no identity can be found.

    Can also return NO_IDENTITY, but None is converted automatically
    to this.
    """
    return None


@reg.dispatch('identity')
def verify_identity(identity):
    """Returns True if the claimed identity can be verified.
    """
    return False


@reg.dispatch()
def remember_identity(response, request, identity):
    """Modify response so that identity is remembered by client.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.dispatch()
def forget_identity(response, request):
    """Modify response so that identity is forgotten by client.
    """
    raise NotImplementedError  # pragma: nocoverage


@reg.dispatch('identity', 'obj',
              reg.match_class('permission',
                              lambda permission: permission))
def permits(identity, obj, permission):
    """Returns True if identity has permission for model.

    identity can be the special NO_IDENTITY singleton; register for
    NoIdentity to handle this case separately.
    """
    return False


@reg.dispatch()
def load_json(request, json):
    """Load JSON as some object.

    Can return any Python object.
    """
    return json


@reg.dispatch('obj')
def dump_json(request, obj):
    """Dump an object as JSON.

    ``obj`` is any Python object, try to interpret it as JSON.

    The return value is JSON-serialized.
    """
    return obj


@reg.dispatch()
def link_prefix(request):
    """Returns a prefix that's added to every link generated by the request.
    """
    return request.application_url
