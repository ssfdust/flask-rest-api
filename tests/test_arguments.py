"""Test arguments parser"""

import marshmallow as ma

from flask import jsonify
from flask.views import MethodView

from flask_rest_api import Api, Blueprint
from flask_rest_api.arguments import NestedQueryArgsParser
from flask_rest_api.compat import MARSHMALLOW_VERSION_MAJOR

from io import BytesIO


class TestArgsParser():

    def test_args_parser_nested_query_arguments(self, app):
        api = Api(app)

        class CustomBlueprint(Blueprint):
            ARGUMENTS_PARSER = NestedQueryArgsParser()

        blp = CustomBlueprint('test', 'test', url_prefix='/test')

        class UserNameSchema(ma.Schema):
            if MARSHMALLOW_VERSION_MAJOR < 3:
                class Meta:
                    strict = True
            first_name = ma.fields.String()
            last_name = ma.fields.String()

        class UserSchema(ma.Schema):
            if MARSHMALLOW_VERSION_MAJOR < 3:
                class Meta:
                    strict = True
            user = ma.fields.Nested(UserNameSchema)

        @blp.route('/')
        class TestMethod(MethodView):
            @blp.arguments(UserSchema, location='query')
            def get(self, args):
                return jsonify(args)

        api.register_blueprint(blp)

        res = app.test_client().get('/test/', query_string={
            'user.first_name': 'Chuck', 'user.last_name': 'Norris'})

        assert res.json == {
            'user': {'first_name': 'Chuck', 'last_name': 'Norris'}}

    def test_args_parser_multipart_form_data(self, app):
        api = Api(app)

        blp = Blueprint('test', 'test', url_prefix='/test')

        class UploadField(ma.fields.Field):
            pass

        api.register_field(UploadField, 'string', 'binary')

        class ExtraArgSchema(ma.Schema):
            arg = ma.fields.String()

        class FormSchema(ma.Schema):
            if MARSHMALLOW_VERSION_MAJOR < 3:
                class Meta:
                    strict = True
            file = UploadField()
            filename = ma.fields.String(location='form')
            extra = ma.fields.Nested(ExtraArgSchema, location='form')

        @blp.route('/')
        class TestMethod(MethodView):
            @blp.arguments(FormSchema, location='files')
            def post(self, args):
                args['content'] = args.pop('file', None).read().decode('utf-8')
                return jsonify(args)

        api.register_blueprint(blp)

        filedata = (BytesIO(b'testinfo'), 'test')

        data = {
            'filename': 'test',
            'file': filedata,
        }

        res = app.test_client().post('/test/', data=data,
                                     content_type='multipart/form-data')

        assert res.json == {
            'filename': 'test',
            'content': 'testinfo',
        }
