import importlib.util, pathlib, os, types, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/settings.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

def test_base_dir_is_parent_of_project_root():
    # BASE_DIR should be the parent of the directory containing settings.py
    expected = str(_MODULE_PATH.resolve().parent.parent)
    assert isinstance(target_module.BASE_DIR, str)
    assert target_module.BASE_DIR == expected
    # Ensure BASE_DIR exists on filesystem (the repository layout should include it)
    assert os.path.basename(target_module.BASE_DIR) != ''

def test_database_default_is_sqlite_and_name_points_to_base_dir():
    db = target_module.DATABASES
    assert isinstance(db, dict)
    assert 'default' in db
    default = db['default']
    assert default['ENGINE'] == 'django.db.backends.sqlite3'
    # NAME should be a path joining BASE_DIR and db.sqlite3
    assert default['NAME'].endswith(os.path.join('db.sqlite3'))
    # the full path should start with BASE_DIR
    assert os.path.abspath(default['NAME']).startswith(os.path.abspath(target_module.BASE_DIR))

def test_secret_key_and_debug_and_allowed_hosts():
    assert isinstance(target_module.SECRET_KEY, str)
    assert len(target_module.SECRET_KEY) > 0
    assert target_module.DEBUG is True
    assert isinstance(target_module.ALLOWED_HOSTS, list)
    # default ALLOWED_HOSTS is empty list in this settings file
    assert target_module.ALLOWED_HOSTS == []

def test_installed_apps_contains_core_and_third_party_apps():
    apps = target_module.INSTALLED_APPS
    assert isinstance(apps, list)
    # check presence of Django contrib apps
    assert 'django.contrib.auth' in apps
    assert 'django.contrib.admin' in apps
    # check presence of third-party apps
    assert 'corsheaders' in apps
    assert 'rest_framework' in apps
    # check presence of project apps
    assert 'conduit.apps.authentication' in apps
    assert 'conduit.apps.articles' in apps

def test_middleware_and_root_urlconf_and_wsgi_application():
    mw = target_module.MIDDLEWARE
    assert isinstance(mw, list)
    assert 'corsheaders.middleware.CorsMiddleware' in mw
    assert target_module.ROOT_URLCONF == 'conduit.urls'
    assert target_module.WSGI_APPLICATION == 'conduit.wsgi.application'

def test_templates_structure_and_context_processors():
    templates = target_module.TEMPLATES
    assert isinstance(templates, list)
    assert len(templates) >= 1
    tpl = templates[0]
    assert isinstance(tpl, dict)
    assert tpl.get('BACKEND') == 'django.template.backends.django.DjangoTemplates'
    opts = tpl.get('OPTIONS')
    assert isinstance(opts, dict)
    cps = opts.get('context_processors')
    assert isinstance(cps, list)
    assert 'django.template.context_processors.request' in cps
    assert 'django.template.context_processors.debug' in cps

def test_rest_framework_configuration():
    rf = target_module.REST_FRAMEWORK
    assert isinstance(rf, dict)
    assert rf.get('EXCEPTION_HANDLER') == 'conduit.apps.core.exceptions.core_exception_handler'
    assert rf.get('NON_FIELD_ERRORS_KEY') == 'error'
    # DEFAULT_AUTHENTICATION_CLASSES should be a tuple with JWT backend
    auth_classes = rf.get('DEFAULT_AUTHENTICATION_CLASSES')
    assert isinstance(auth_classes, tuple)
    assert 'conduit.apps.authentication.backends.JWTAuthentication' in auth_classes
    # pagination settings
    assert rf.get('DEFAULT_PAGINATION_CLASS') == 'rest_framework.pagination.LimitOffsetPagination'
    assert rf.get('PAGE_SIZE') == 20

def test_password_validators_structure():
    validators = target_module.AUTH_PASSWORD_VALIDATORS
    assert isinstance(validators, list)
    assert all(isinstance(v, dict) for v in validators)
    # each validator dict should have a NAME key with a string value
    for v in validators:
        assert 'NAME' in v
        assert isinstance(v['NAME'], str)
        assert len(v['NAME']) > 0

def test_cors_and_static_settings_and_auth_user_model():
    assert isinstance(target_module.CORS_ORIGIN_WHITELIST, tuple)
    assert 'localhost:4000' in target_module.CORS_ORIGIN_WHITELIST
    assert '0.0.0.0:4000' in target_module.CORS_ORIGIN_WHITELIST
    assert target_module.STATIC_URL == '/static/'
    assert target_module.AUTH_USER_MODEL == 'authentication.User'

def test_cors_whitelist_is_tuple_and_immutable():
    # Ensure the whitelist is a tuple and is immutable by item assignment
    wl = target_module.CORS_ORIGIN_WHITELIST
    assert isinstance(wl, tuple)
    with pytest.raises(TypeError):
        wl[0] = 'attempt-to-change'