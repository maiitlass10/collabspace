from django.urls import re_path

from .consumers import DocumentConsumer

UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

websocket_urlpatterns = [
    # y-websocket connects to "<server url>/<room name>", without a trailing slash.
    re_path(rf"^ws/documents/(?P<document_id>{UUID})/?$", DocumentConsumer.as_asgi()),
]
