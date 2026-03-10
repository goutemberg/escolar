from .base import *
import os
import dj_database_url

DEBUG = 0

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL")
    )
}

CSRF_TRUSTED_ORIGINS = [
    "https://*.onrender.com",
    "https://nucleoescolar.com.br",
    "https://www.nucleoescolar.com.br",
    
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


DEBUG_PROPAGATE_EXCEPTIONS = True
