from django.urls import path
from home.views.reset_senha import (
    reset_senha,
    nova_senha,
)

app_name = "reset_senha"

urlpatterns = [
    path('reset-senha/', reset_senha, name='reset_senha'),
    path('nova-senha/<str:token>/', nova_senha, name='nova_senha'),
]









