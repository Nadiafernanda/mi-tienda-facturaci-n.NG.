from django.urls import path

from . import views

urlpatterns = [
    path("", views.iniciar_sesion, name="login"),
    path("registro/", views.registrarse, name="registro"),
    path("logout/", views.cerrar_sesion, name="logout"),
]
