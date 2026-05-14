import json
import logging
from decimal import Decimal

import httpx
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Order, OrderSide, OrderStatus, Portfolio

logger = logging.getLogger(__name__)


def _fastapi_url(path: str) -> str:
    base = settings.FASTAPI_BASE_URL.rstrip("/")
    return f"{base}{path}"


def _fetch_from_fastapi(path: str):
    try:
        resp = httpx.get(_fastapi_url(path), timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"FastAPI request failed: {path} - {e}")
        return None


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

    summary = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/summary")
    pnl_report = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/pnl")
    positions_data = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/positions")
    orders_data = _fetch_from_fastapi(f"/portfolio/{portfolio_id}/orders")

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
            resp = httpx.post(_fastapi_url("/order"), json=payload, timeout=5.0)
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
            resp = httpx.delete(_fastapi_url(f"/order/{order_id}"), timeout=5.0)
            if resp.status_code == 200:
                messages.success(request, "Order cancelled.")
            else:
                messages.error(request, resp.json().get("detail", "Failed to cancel order"))
        except Exception as e:
            messages.error(request, f"FastAPI unavailable: {e}")
    return redirect("portfolio_detail", portfolio_id=portfolio_id)
