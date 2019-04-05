"""Api extension initialization"""

from collections import namedtuple

from webargs.flaskparser import abort  # noqa

from .spec import APISpecMixin
from .blueprint import Blueprint  # noqa
from .pagination import Page  # noqa
from .error_handler import ErrorHandlerMixin

__version__ = '0.14.0'

class Api(APISpecMixin, ErrorHandlerMixin):
    """Main class

    Provides helpers to build a REST API using Flask.

    :param Flask app: Flask application
    :param dict spec_kwargs: kwargs to pass to internal APISpec instance

    The ``spec_kwargs`` dictionary is passed as kwargs to the internal APISpec
    instance. **flask-rest-api** adds a few parameters to the original
    parameters documented in :class:`apispec.APISpec <apispec.APISpec>`:

    :param apispec.BasePlugin flask_plugin: Flask plugin
    :param apispec.BasePlugin marshmallow_plugin: Marshmallow plugin
    :param list|tuple extra_plugins: List of additional ``BasePlugin``
        instances
    :param str openapi_version: OpenAPI version. Can also be passed as
        application parameter `OPENAPI_VERSION`.

    This allows the user to override default Flask and marshmallow plugins.

    `title` and `version` APISpec parameters can't be passed here, they are set
    according to the app configuration.

    For more flexibility, additional spec kwargs can also be passed as app
    parameter `API_SPEC_OPTIONS`.
    """
    def __init__(self, name, app=None, *, spec_kwargs=None):
        self.name = name
        self._app = app
        self.spec = None
        # Use lists to enforce order
        self._schemas = []
        self._fields = []
        self._converters = []
        self._blueprints = []
        if app is not None:
            self.init_app(app, spec_kwargs=spec_kwargs, lazy_load_blp=False)

    def init_app(self, app, *, spec_kwargs=None, lazy_load_blp=True):
        """Initialize Api with application"""

        self._app = app

        # Register flask-rest-api in app extensions
        app.extensions = getattr(app, 'extensions', {})
        ext = app.extensions.setdefault('flask-rest-api', {})
        ext['ext_obj'] = self

        # Initialize spec
        self._init_spec(**(spec_kwargs or {}))

        # Initialize blueprint serving spec
        self._register_doc_blueprint()

        # Register error handlers
        self._register_error_handlers()

        # Register blueprints 
        if lazy_load_blp:
            self.lazy_load_blueprint()

    def blueprint(self, *args, **kwargs):
        reg_blp_options = kwargs.pop('reg_blp_options', {})
        blp = Blueprint(*args, api=self, **kwargs)
        self.add_blueprint(blp, reg_blp_options)

        return blp

    def add_blueprint(self, blp, reg_blp_options):
        if self._app is not None:
            self.register_blueprint(blp, **reg_blp_options)
        else:
            self._blueprints.append({'blp': blp, 'reg_blp_options': reg_blp_options})

    def lazy_load_blueprint(self):
        for blp_with_options in self._blueprints:
            self.register_blueprint(blp_with_options['blp'],
                                    **blp_with_options['reg_blp_options'])

    def register_blueprint(self, blp, **options):
        """Register a blueprint in the application

        Also registers documentation for the blueprint/resource

        :param Blueprint blp: Blueprint to register
        :param dict options: Keyword arguments overriding Blueprint defaults

        Must be called after app is initialized.
        """

        self._app.register_blueprint(blp, **options)

        # Register views in API documentation for this resource
        blp.register_views_in_doc(self._app, self.spec)

        # Add tag relative to this resource to the global tag list
        self.spec.tag({'name': blp.name, 'description': blp.description})
