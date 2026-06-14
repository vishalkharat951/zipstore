from .base import *

DEBUG = True

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-1r_kj!y)*0m0b$kc=*4nm$ftku%x*d2-)l1l80^pz&^9_&idvj',
)

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.localhost']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
        },
    }
}
