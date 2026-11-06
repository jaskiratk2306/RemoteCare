from django.urls import path
from .views import login_view, logout_view, home_redirect_view

urlpatterns = [
    path('', home_redirect_view, name='home-redirect'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]

