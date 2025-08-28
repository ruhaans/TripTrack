# trips/utils/urls.py (new helper)
from urllib.parse import urljoin
from django.conf import settings

def absolute_url(path: str) -> str:
    # path should come from reverse('name', args/kwargs=...)
    return urljoin(settings.APP_BASE_URL.rstrip("/") + "/", path.lstrip("/"))
