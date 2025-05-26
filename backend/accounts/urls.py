from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register', views.register, name='register'),
    path('login', views.user_login, name='login'),
    path('logout', views.user_logout, name='logout'),
    path('profile', views.get_user_profile, name='profile'),
    path('profile/update', views.update_user_profile, name='update_profile'),
]
