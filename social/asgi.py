"""
ASGI config for social project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import django # <-- ADD THIS LINE

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social.settings")

# ----------------------------------------------------
# 1. Initialize Django App Registry
# This must happen BEFORE importing any code (like routing) that uses models.
django.setup() # <-- ADD THIS LINE
# ----------------------------------------------------

# 2. Import Channel and app-dependent components AFTER setup()
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import core.routing # <-- MOVE THIS IMPORT DOWN HERE

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            core.routing.websocket_urlpatterns
        )
    ),
})