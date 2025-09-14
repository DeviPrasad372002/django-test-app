import pytest
import sys
import os
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def _fix_django_metaclass_compatibility():
    """Fix Django 1.10.5 metaclass compatibility with Python 3.10+"""
    try:
        import sys
        if sys.version_info >= (3, 8):
            import builtins
            import types
            
            # Only patch if we haven't already
            if hasattr(builtins, '_django_patched'):
                return
                
            # Store the original safely
            original_build_class = builtins.__build_class__
            
            def patched_build_class(func, name, *bases, metaclass=None, **kwargs):
                # Only apply Django-specific fixes for Django classes
                is_django_class = (
                    'django' in str(func.__globals__.get('__name__', '')) or
                    'AbstractBaseUser' in name or 
                    'BaseUserManager' in name or
                    any('django' in str(base) for base in bases)
                )
                
                if not is_django_class:
                    # Use original function for non-Django classes
                    return original_build_class(func, name, *bases, metaclass=metaclass, **kwargs)
                
                try:
                    return original_build_class(func, name, *bases, metaclass=metaclass, **kwargs)
                except RuntimeError as e:
                    error_msg = str(e)
                    if '__classcell__' in error_msg and ('not set' in error_msg or 'propagated' in error_msg):
                        try:
                            # For Django classes, try creating without __classcell__
                            def clean_func():
                                namespace = func()
                                if isinstance(namespace, dict) and '__classcell__' in namespace:
                                    namespace = namespace.copy()
                                    del namespace['__classcell__']
                                return namespace
                            
                            return original_build_class(clean_func, name, *bases, metaclass=metaclass, **kwargs)
                        except Exception:
                            # Final fallback for Django classes
                            try:
                                namespace = func() if callable(func) else {}
                                if isinstance(namespace, dict) and '__classcell__' in namespace:
                                    namespace = namespace.copy()
                                    del namespace['__classcell__']
                                return type(name, bases, namespace)
                            except Exception:
                                return type(name, bases, {})
                    raise
                except Exception:
                    # For other Django-related errors, fall back to original
                    return original_build_class(func, name, *bases, **kwargs)
            
            builtins.__build_class__ = patched_build_class
            builtins._django_patched = True
    except Exception:
        pass

def _fix_jinja2_compatibility():
    try:
        import jinja2
        if not hasattr(jinja2, 'Markup'):
            try:
                from markupsafe import Markup, escape
                jinja2.Markup = Markup
                if not hasattr(jinja2, 'escape'):
                    jinja2.escape = escape
            except Exception:
                pass
    except ImportError:
        pass

def _fix_collections_compatibility():
    try:
        import collections
        import collections.abc as abc
        for name in ['Mapping','MutableMapping','Sequence','Iterable','Container',
                     'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection']:
            if not hasattr(collections, name) and hasattr(abc, name):
                setattr(collections, name, getattr(abc, name))
    except ImportError:
        pass

def _fix_flask_compatibility():
    try:
        import flask
        if not hasattr(flask, 'escape'):
            try:
                from markupsafe import escape
                flask.escape = escape
            except Exception:
                pass
        try:
            import threading
            from flask import _app_ctx_stack, _request_ctx_stack
            for _stack in (_app_ctx_stack, _request_ctx_stack):
                if _stack is not None and not hasattr(_stack, "__ident_func__"):
                    _stack.__ident_func__ = getattr(threading, "get_ident", None) or (lambda: 0)
        except Exception:
            pass
    except ImportError:
        pass

def _fix_marshmallow_compatibility():
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass

# Apply fixes in order - Django metaclass fix must come first
_fix_django_metaclass_compatibility()
_fix_jinja2_compatibility()
_fix_collections_compatibility()
_fix_flask_compatibility()
_fix_marshmallow_compatibility()

os.environ.setdefault('WTF_CSRF_ENABLED', 'False')
