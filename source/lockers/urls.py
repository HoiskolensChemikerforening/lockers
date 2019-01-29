from django.urls import path, re_path

from lockers import views

app_name = "lockers"

urlpatterns = [
    path("", views.view_lockers, name="index"),
    path("<int:page>", views.view_lockers, name="detail"),
    path("registrer/<int:number>", views.register_locker, name="registrer"),
    path("aktiver/<uuid:code>", views.activate_ownership, name="activate"),
    path("administrer/slett/<int:locker_number>/", views.clear_locker, name="force-remove"),
    path("administrer", views.manage_lockers, name="administrate"),
    re_path(r"^administrer/#(?P<anchor>[-_\w]+)$", views.manage_lockers, name="administrate"),
    path("mine-skap", views.my_lockers, name="mineskap"),
]
