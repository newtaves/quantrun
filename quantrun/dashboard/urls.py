from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("", views.portfolio_list, name="portfolio_list"),
    path("new/", views.portfolio_create, name="portfolio_create"),
    path("<int:portfolio_id>/", views.portfolio_detail, name="portfolio_detail"),
    path("<int:portfolio_id>/edit/", views.portfolio_edit, name="portfolio_edit"),
    path("<int:portfolio_id>/delete/", views.portfolio_delete, name="portfolio_delete"),
    path("<int:portfolio_id>/order/new/", views.order_create, name="order_create"),
    path("<int:portfolio_id>/order/<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
]
