"""Arguments parsing"""
from copy import deepcopy
from functools import wraps
import re

from webargs import core
from webargs.flaskparser import FlaskParser


class ArgumentsMixin:
    """Extend Blueprint to add arguments parsing feature"""

    ARGUMENTS_PARSER = FlaskParser()

    def arguments(
            self, schema, *, location='json', content_types=None,
            required=True, example=None, examples=None, **kwargs
    ):
        """Decorator specifying the schema used to deserialize parameters

        :param type|Schema schema: Marshmallow ``Schema`` class or instance
            used to deserialize and validate the argument.
        :param str location: Location of the argument.
        :param str content_types: Allowed content types for the argument.
            Should only be used in conjunction with ``json``, ``form`` or
            ``files`` location.
            The default value depends on the location and is set in
            ``Blueprint.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING``.
            This is only used for documentation purpose.
        :param bool required: Whether argument is required (default: True).
            This only affects `body` arguments as, in this case, the docs
            expose the whole schema as a `required` parameter.
            For other locations, the schema is turned into an array of
            parameters and their required value is inferred from the schema.
        :param dict example: Parameter example.
        :param list examples: List of parameter examples.
        :param dict kwargs: Keyword arguments passed to the webargs
            :meth:`use_args <webargs.core.Parser.use_args>` decorator used
            internally.

        The `example` and `examples` parameters are mutually exclusive and
        should only be used with OpenAPI 3 and when location is ``json``.

        See :doc:`Arguments <arguments>`.
        """
        # At this stage, put schema instance in doc dictionary. Il will be
        # replaced later on by $ref or json.
        parameters = {
            'in': location,
            'required': required,
            'schema': schema,
        }
        if content_types is not None:
            parameters['content_types'] = content_types
        if example is not None:
            parameters['example'] = example
        if examples is not None:
            parameters['examples'] = examples

        def decorator(func):

            @wraps(func)
            def wrapper(*f_args, **f_kwargs):
                return func(*f_args, **f_kwargs)

            # Add parameter to parameters list in doc info in function object
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, '_apidoc', {}))
            wrapper._apidoc.setdefault('parameters', []).append(parameters)

            locations = list(
                set([
                    f.metadata.get('location', location)
                    for f in schema._declared_fields.values()
                ])
            )

            # Call use_args (from webargs) to inject params in function
            return self.ARGUMENTS_PARSER.use_args(
                schema, locations=locations, **kwargs)(wrapper)

        return decorator


# Copied from webargs advanced usage custom parsers
# https://webargs.readthedocs.io/en/latest/advanced.html#custom-parsers
class NestedQueryArgsParser(FlaskParser):
    """Parses nested query args

    This parser handles nested query args. It expects nested levels
    delimited by a period and then deserializes the query args into a
    nested dict.

    For example, the URL query params `?name.first=John&name.last=Boone`
    will yield the following dict:

        {
            'name': {
                'first': 'John',
                'last': 'Boone',
            }
        }
    """
    def parse_querystring(self, req, name, field):
        return core.get_value(_structure_dict(req.args), name, field)


def _structure_dict(dict_):
    def structure_dict_pair(r, key, value):
        match = re.match(r'(\w+)\.(.*)', key)
        if match:
            if r.get(match.group(1)) is None:
                r[match.group(1)] = {}
            structure_dict_pair(r[match.group(1)], match.group(2), value)
        else:
            r[key] = value
    ret = {}
    for key, val in dict_.items():
        structure_dict_pair(ret, key, val)
    return ret
