import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import jwt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as django_timezone
from django.views.decorators.http import require_POST

from .models import APIToken, Order, OrderSide, OrderStatus, Portfolio

logger = logging.getLogger(__name__)


def _fastapi_url(path: str) -> str:
    base = settings.FASTAPI_BASE_URL.rstrip("/")
    return f"{base}{path}"


def _get_user_token(user):
    active_token = APIToken.objects.filter(user=user, is_active=True, expires_at__gt=django_timezone.now()).first()
    if active_token:
        return active_token.token

    now = django_timezone.now()
    expires_at = now + timedelta(days=settings.JWT_EXPIRY_DAYS)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": expires_at,
        "iat": now,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    APIToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at,
    )
    return token


def _fetch_from_fastapi(path: str, user=None):
    try:
        headers = {}
        if user:
            token = _get_user_token(user)
            headers["Authorization"] = f"Bearer {token}"
        resp = httpx.get(_fastapi_url(path), headers=headers, timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"FastAPI request failed: {path} - {e}")
        return None


def _post_to_fastapi(path: str, user, json_data=None):
    token = _get_user_token(user)
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.post(_fastapi_url(path), json=json_data, headers=headers, timeout=5.0)
    return resp


def _delete_from_fastapi(path: str, user):
    token = _get_user_token(user)
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.delete(_fastapi_url(path), headers=headers, timeout=5.0)
    return resp


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome {user.username}! Account created.")
            return redirect("portfolio_list")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


@require_POST
def custom_logout(request):
    if request.user.is_authenticated:
        APIToken.objects.filter(user=request.user, is_active=True).update(is_active=False)
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def portfolio_list(request):
    portfolios = Portfolio.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard/portfolio_list.html", {"portfolios": portfolios})


@login_required
def portfolio_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        available_cash = request.POST.get("available_cash", "0")

        if not name:
            messages.error(request, "Portfolio name is required.")
            return render(request, "dashboard/portfolio_form.html", {"form_data": request.POST})

        try:
            cash = Decimal(available_cash)
        except Exception:
            messages.error(request, "Invalid cash amount.")
            return render(request, "dashboard/portfolio_form.html", {"form_data": request.POST})

        portfolio = Portfolio.objects.create(
            user=request.user,
            name=name,
            description=description or "description",
            available_cash=cash,
        )
        messages.success(request, f"Portfolio '{portfolio.name}' created.")
        return redirect("portfolio_detail", portfolio_id=portfolio.id)

    return render(request, "dashboard/portfolio_form.html", {"form_data": None})


@login_required
def portfolio_detail(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

    summary = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/summary", user=request.user)
    pnl_report = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/pnl", user=request.user)
    positions_data = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/positions", user=request.user)
    orders_data = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/orders", user=request.user)

    positions = (positions_data or {}).get("positions", [])
    orders = (orders_data or {}).get("orders", [])

    pending_orders = [o for o in orders if o.get("status") == OrderStatus.PENDING]
    executed_orders = [o for o in orders if o.get("status") == OrderStatus.EXECUTED]

    return render(request, "dashboard/portfolio_detail.html", {
        "portfolio": portfolio,
        "summary": summary,
        "pnl_report": pnl_report,
        "positions": positions,
        "pending_orders": pending_orders,
        "executed_orders": executed_orders,
        "all_orders": orders,
        "fastapi_available": summary is not None,
    })


@login_required
def portfolio_edit(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        if not name:
            messages.error(request, "Portfolio name is required.")
            return render(request, "dashboard/portfolio_form.html", {"form_data": request.POST, "portfolio": portfolio})
        portfolio.name = name
        portfolio.description = description or "description"
        portfolio.save()
        messages.success(request, "Portfolio updated.")
        return redirect("portfolio_detail", portfolio_id=portfolio.id)
    return render(request, "dashboard/portfolio_form.html", {"portfolio": portfolio})


@login_required
def portfolio_delete(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
    if request.method == "POST":
        name = portfolio.name
        portfolio.delete()
        messages.success(request, f"Portfolio '{name}' deleted.")
        return redirect("portfolio_list")
    return render(request, "dashboard/portfolio_confirm_delete.html", {"portfolio": portfolio})


@login_required
def order_create(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

    if request.method == "POST":
        symbol = request.POST.get("symbol", "").strip().upper()
        side = request.POST.get("side", "").upper()
        quantity = request.POST.get("quantity", "0")
        limit_price = request.POST.get("limit_price", "").strip()
        target = request.POST.get("target", "").strip()
        stoploss = request.POST.get("stoploss", "").strip()

        errors = []
        if not symbol:
            errors.append("Symbol is required.")
        if side not in ("BUY", "SELL"):
            errors.append("Side must be BUY or SELL.")
        try:
            qty = Decimal(quantity)
            if qty <= 0:
                errors.append("Quantity must be > 0.")
        except Exception:
            errors.append("Invalid quantity.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "dashboard/order_form.html", {"portfolio": portfolio, "form_data": request.POST})

        payload = {
            "portfolio_id": portfolio_id,
            "symbol": symbol,
            "side": side,
            "quantity": float(qty),
            "limit_price": float(limit_price) if limit_price else None,
            "target": float(target) if target else None,
            "stoploss": float(stoploss) if stoploss else None,
        }

        try:
            resp = _post_to_fastapi("/order", request.user, json_data=payload)
            if resp.status_code == 200:
                messages.success(request, f"Order placed: {side} {qty} {symbol}")
                return redirect("portfolio_detail", portfolio_id=portfolio_id)
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text or f"HTTP {resp.status_code}"
                messages.error(request, f"Order failed: {detail}")
        except httpx.ConnectError:
            messages.error(request, "FastAPI is not running. Start it with: uvicorn paper.main:app --reload")
        except httpx.TimeoutException:
            messages.error(request, "FastAPI request timed out.")
        except Exception as e:
            messages.error(request, f"Order error: {e}")

        return render(request, "dashboard/order_form.html", {"portfolio": portfolio, "form_data": request.POST})

    return render(request, "dashboard/order_form.html", {"portfolio": portfolio, "form_data": None})


@login_required
def order_cancel(request, portfolio_id, order_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
    if request.method == "POST":
        try:
            resp = _delete_from_fastapi(f"/order/{order_id}", request.user)
            if resp.status_code == 200:
                messages.success(request, "Order cancelled.")
            else:
                messages.error(request, resp.json().get("detail", "Failed to cancel order"))
        except Exception as e:
            messages.error(request, f"FastAPI unavailable: {e}")
    return redirect("portfolio_detail", portfolio_id=portfolio_id)


@login_required
def token_list(request):
    tokens = APIToken.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard/token_list.html", {"tokens": tokens})


@login_required
def token_generate(request):
    if request.method == "POST":
        now = django_timezone.now()
        expires_at = now + timedelta(days=settings.JWT_EXPIRY_DAYS)

        payload = {
            "user_id": request.user.id,
            "username": request.user.username,
            "exp": expires_at,
            "iat": now,
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        APIToken.objects.create(
            user=request.user,
            token=token,
            expires_at=expires_at,
        )
        messages.success(request, "New API token generated.")
        return redirect("token_list")
    return redirect("token_list")


@login_required
def token_revoke(request, token_id):
    if request.method == "POST":
        token = get_object_or_404(APIToken, id=token_id, user=request.user)
        token.is_active = False
        token.save()
        messages.success(request, "Token revoked.")
    return redirect("token_list")
