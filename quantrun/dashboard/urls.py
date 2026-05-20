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
    path("tokens/", views.token_list, name="token_list"),
    path("tokens/generate/", views.token_generate, name="token_generate"),
    path("tokens/<int:token_id>/revoke/", views.token_revoke, name="token_revoke"),
    path("api/signup/", views.api_signup, name="api_signup"),
    path("api/login/", views.api_login, name="api_login"),
    path("api/logout/", views.api_logout, name="api_logout"),
    path("api/tokens/", views.api_token_list, name="api_token_list"),
    path("api/tokens/generate/", views.api_token_generate, name="api_token_generate"),
    path("api/tokens/<int:token_id>/revoke/", views.api_token_revoke, name="api_token_revoke"),
]
