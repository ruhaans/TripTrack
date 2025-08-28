# triptrack/utils.py
from urllib.parse import urljoin
from django.conf import settings

def absolute_url(path: str) -> str:
    """
    Build an absolute URL using APP_BASE_URL instead of request.build_absolute_uri.
    `path` should come from django.urls.reverse(...)
    """
    base = settings.APP_BASE_URL.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))
