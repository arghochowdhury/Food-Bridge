from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("restaurant/", views.restaurant_dashboard, name="restaurant_dashboard"),
    path("restaurant/license/", views.restaurant_license, name="restaurant_license"),
    path("restaurant/food/add/", views.food_add, name="food_add"),
    path("restaurant/food/<int:pk>/edit/", views.food_edit, name="food_edit"),
    path("restaurant/food/<int:pk>/delete/", views.food_delete, name="food_delete"),

    path("hall/", views.hall_dashboard, name="hall_dashboard"),
    path("hall/find/", views.find_restaurants, name="find_restaurants"),
    path("hall/restaurant/<int:pk>/order/", views.place_order, name="place_order"),

    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/pdf/", views.order_pdf, name="order_pdf"),
    path("orders/<int:pk>/<str:action>/", views.order_action, name="order_action"),

    path("notifications/", views.notifications, name="notifications"),
    path("api/locations/", views.api_locations, name="api_locations"),
]
