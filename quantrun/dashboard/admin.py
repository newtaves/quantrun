from django.contrib import admin
from .models import Portfolio, Order, Position

# Register your models here.
admin.site.register(Portfolio)
admin.site.register(Order)
admin.site.register(Position)