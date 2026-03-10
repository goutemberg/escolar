from django.urls import path
from .views.chamada import salvar_chamada_api, consultar_chamada_api, atualizar_chamada_api 

urlpatterns = [
    path('chamada/salvar/', salvar_chamada_api, name='salvar_chamada_api'),
    path('chamada/consultar/', consultar_chamada_api, name='consultar_chamada_api'),
    path('chamada/atualizar/<int:diario_id>/', atualizar_chamada_api, name='atualizar_chamada_api'),
]