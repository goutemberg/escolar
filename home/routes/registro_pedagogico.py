from django.urls import path
from home.views.registro_pedagogico import (
    registro_pedagogico_view,
    salvar_registro_pedagogico,
    buscar_registros_pedagogicos,
)

app_name = "registro_pedagogico"

urlpatterns = [
    
    path(
        "registro-pedagogico/",
        registro_pedagogico_view,
        name="registro_pedagogico",
    ),
    path(
        "registro-pedagogico/salvar/",
        salvar_registro_pedagogico,
        name="salvar_registro_pedagogico",
    ),
    path(
        "api/registro-pedagogico/",
        buscar_registros_pedagogicos,
        name="buscar_registros_pedagogicos",
    ),
]
