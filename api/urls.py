from django.urls import include, path

urlpatterns = [
    path('', include('api.urls_auth')),
    path('', include('api.urls_turma')),
    path('', include('api.urls_chamada')),
    path("", include("api.urls_nota")),
]