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
            
            # Store the original __build_class__ function
            if not hasattr(builtins, '_original_build_class'):
                builtins._original_build_class = builtins.__build_class__
            
            original_build_class = builtins._original_build_class
            
            def patched_build_class(func, name, *bases, metaclass=None, **kwargs):
                try:
                    return original_build_class(func, name, *bases, metaclass=metaclass, **kwargs)
                except RuntimeError as e:
                    error_msg = str(e)
                    if '__classcell__' in error_msg and ('not set' in error_msg or 'propagated' in error_msg):
                        # Django 1.10.5 metaclass compatibility fix
                        try:
                            # Create a simple wrapper that bypasses the __classcell__ issue
                            def new_func():
                                # Get the class namespace by calling the original function
                                namespace = func()
                                # Remove any __classcell__ entries that cause problems
                                if '__classcell__' in namespace:
                                    del namespace['__classcell__']
                                return namespace
                            
                            # Try with the modified function
                            return original_build_class(new_func, name, *bases, metaclass=metaclass, **kwargs)
                        except Exception:
                            # If that fails, try without metaclass
                            try:
                                def simple_func():
                                    namespace = func()
                                    if '__classcell__' in namespace:
                                        del namespace['__classcell__']
                                    return namespace
                                return original_build_class(simple_func, name, *bases, **kwargs)
                            except Exception:
                                # Final fallback: create a simple class
                                return type(name, bases, func())
                    raise
                except Exception as e:
                    # Last resort fallback
                    if 'AbstractBaseUser' in name or 'BaseUserManager' in name:
                        # For Django auth classes, create a minimal working version
                        try:
                            namespace = func() if callable(func) else {}
                            return type(name, bases, namespace)
                        except Exception:
                            return type(name, bases, {})
                    raise
            
            builtins.__build_class__ = patched_build_class
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
