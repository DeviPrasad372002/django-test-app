import importlib.util, pathlib, os, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/settings.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_base_dir_points_two_levels_up_from_file():
    module_file = pathlib.Path(target_module.__file__).resolve()
    expected = str(module_file.parent.parent)
    assert target_module.BASE_DIR == expected
    # Expect the BASE_DIR to exist and be a directory in the repository
    assert pathlib.Path(target_module.BASE_DIR).is_dir()


def test_secret_key_and_debug_and_allowed_hosts():
    assert isinstance(target_module.SECRET_KEY, str)
    assert len(target_module.SECRET_KEY) > 10
    assert target_module.DEBUG is True
    assert isinstance(target_module.ALLOWED_HOSTS, list)
    assert target_module.ALLOWED_HOSTS == []


def test_installed_apps_contains_expected_entries():
    apps = target_module.INSTALLED_APPS
    assert isinstance(apps, list)
    # Check a sampling of expected app entries
    expected_entries = [
        'django.contrib.admin',
        'django.contrib.auth',
        'rest_framework',
        'conduit.apps.articles',
        'conduit.apps.authentication',
    ]
    for entry in expected_entries:
        assert entry in apps


def test_middleware_and_root_wsgi_settings():
    assert isinstance(target_module.MIDDLEWARE, list)
    assert 'django.middleware.security.SecurityMiddleware' in target_module.MIDDLEWARE
    assert target_module.ROOT_URLCONF == 'conduit.urls'
    assert target_module.WSGI_APPLICATION == 'conduit.wsgi.application'


def test_templates_structure_and_context_processors():
    templates = target_module.TEMPLATES
    assert isinstance(templates, list)
    assert len(templates) >= 1
    tpl0 = templates[0]
    assert tpl0.get('BACKEND') == 'django.template.backends.django.DjangoTemplates'
    assert tpl0.get('APP_DIRS') is True
    options = tpl0.get('OPTIONS')
    assert isinstance(options, dict)
    cps = options.get('context_processors')
    assert isinstance(cps, list)
    # check some commonly expected context processors
    assert 'django.template.context_processors.debug' in cps
    assert 'django.template.context_processors.request' in cps


def test_database_settings_sqlite_name_and_engine():
    dbs = target_module.DATABASES
    assert 'default' in dbs
    default = dbs['default']
    assert default['ENGINE'] == 'django.db.backends.sqlite3'
    expected_name = os.path.join(target_module.BASE_DIR, 'db.sqlite3')
    assert default['NAME'] == expected_name


def test_auth_password_validators_structure():
    validators = target_module.AUTH_PASSWORD_VALIDATORS
    assert isinstance(validators, list)
    # Should have the four default validators
    names = [v.get('NAME') for v in validators]
    assert 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' in names
    assert 'django.contrib.auth.password_validation.MinimumLengthValidator' in names
    assert 'django.contrib.auth.password_validation.CommonPasswordValidator' in names
    assert 'django.contrib.auth.password_validation.NumericPasswordValidator' in names
    assert len(names) == 4


def test_internationalization_and_static_url():
    assert target_module.LANGUAGE_CODE == 'en-us'
    assert target_module.TIME_ZONE == 'UTC'
    assert target_module.USE_I18N is True
    assert target_module.USE_L10N is True
    assert target_module.USE_TZ is True
    assert target_module.STATIC_URL == '/static/'


def test_cors_and_auth_user_model_and_rest_framework_settings():
    cors = target_module.CORS_ORIGIN_WHITELIST
    assert isinstance(cors, tuple)
    assert '0.0.0.0:4000' in cors
    assert 'localhost:4000' in cors
    assert target_module.AUTH_USER_MODEL == 'authentication.User'

    rf = target_module.REST_FRAMEWORK
    assert isinstance(rf, dict)
    assert rf.get('EXCEPTION_HANDLER') == 'conduit.apps.core.exceptions.core_exception_handler'
    assert rf.get('NON_FIELD_ERRORS_KEY') == 'error'
    assert rf.get('DEFAULT_PAGINATION_CLASS') == 'rest_framework.pagination.LimitOffsetPagination'
    assert rf.get('PAGE_SIZE') == 20
    auth_classes = rf.get('DEFAULT_AUTHENTICATION_CLASSES')
    assert isinstance(auth_classes, tuple)
    assert 'conduit.apps.authentication.backends.JWTAuthentication' in auth_classes


def test_no_unexpected_mutation_of_module_attributes():
    # Accessing attributes should not raise; verify a representative set
    attrs = [
        'BASE_DIR', 'SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 'INSTALLED_APPS',
        'MIDDLEWARE', 'ROOT_URLCONF', 'TEMPLATES', 'WSGI_APPLICATION',
        'DATABASES', 'AUTH_PASSWORD_VALIDATORS', 'LANGUAGE_CODE',
        'STATIC_URL', 'CORS_ORIGIN_WHITELIST', 'AUTH_USER_MODEL', 'REST_FRAMEWORK'
    ]
    for a in attrs:
        assert hasattr(target_module, a)
        assert getattr(target_module, a) is not None


def test_templates_options_missing_keys_raise_keyerror_when_accessed_directly():
    # Ensure that requesting a non-existent top-level template entry raises KeyError if using dict access
    tpl = target_module.TEMPLATES[0]
    with pytest.raises(KeyError):
        _ = tpl['NON_EXISTENT_KEY']  # direct dict access should raise KeyError, demonstrating type is dict-like for missing keys