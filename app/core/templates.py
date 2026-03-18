from urllib.parse import quote

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

# Custom filter: URL-encode a plain string for safe use in query parameters.
# Usage in templates: {{ some_text | urlencode }}
templates.env.filters["urlencode"] = lambda v: quote(str(v), safe="")
