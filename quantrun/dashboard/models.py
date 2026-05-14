from django.db import models
from decimal import Decimal
from django.contrib.auth.models import User


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=20000, default="description")
    available_cash = models.DecimalField(max_digits=15, decimal_places=5, default=Decimal('0.00000'))
    invested_cash = models.DecimalField( max_digits=15,decimal_places=5, default=Decimal('0.00000'))
    total_pnl = models.DecimalField( max_digits=15, decimal_places=5, default=Decimal('0.00000'))
    created_at = models.DateTimeField(auto_now_add=True)

class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    EXECUTED = "EXECUTED", "Executed"
    CANCELLED = "CANCELLED", "Cancelled"


class OrderSide(models.TextChoices):
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"


class Order(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="orders")
    symbol = models.CharField(max_length=30)
    side = models.CharField(max_length=10, choices=OrderSide.choices)
    quantity = models.DecimalField(max_digits=15,decimal_places=5, default=Decimal('0.00000'))
    limit_price = models.DecimalField( max_digits=15, decimal_places=5, default=Decimal('0.00000'))
    executed_price = models.DecimalField( max_digits=15,decimal_places=5, null=True,blank=True)
    target = models.DecimalField( max_digits=15, decimal_places=5, null=True, blank=True)
    stoploss = models.DecimalField( max_digits=15, decimal_places=5, null=True, blank=True )
    status = models.CharField( max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    symbol = models.CharField(max_length=30)
    side = models.CharField(max_length=10, choices=OrderSide.choices)
    quantity = models.DecimalField(max_digits=15,decimal_places=5, default=Decimal('0.00000'))
    average_price = models.DecimalField(max_digits=15, decimal_places=5)
    current_price = models.DecimalField(max_digits=15, decimal_places=5, default=Decimal(0.00000))
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=5, default=Decimal(0.00000))
    target = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    stoploss = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)