from main.settings.base import *

DEBUG = True
SITE_ID = 2

MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)
INSTALLED_APPS += ("debug_toolbar",)
DEBUG_TOOLBAR = True
