# home/urls/__init__.py
from home.routes.chamada import urlpatterns as chamada_urls
from home.routes.turmas import urlpatterns as turmas_urls

urlpatterns = chamada_urls + turmas_urls