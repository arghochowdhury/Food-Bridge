from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .forms import LEVELS, FoodItemForm, RegisterForm
from .models import (ConventionHall, District, Division, FoodItem, Notification, Order,
                     OrderItem, PostOffice, Restaurant, Thana, Upazila, User)
from .pdf import build_bill_pdf


# ---------------- helpers ----------------
def role_required(role):
    attr = "restaurant" if role == User.RESTAURANT else "hall"

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            profile = getattr(request.user, attr, None) if request.user.role == role else None
            if profile is None:
                if request.user.is_superuser:
                    return redirect("/admin/")
                messages.error(request, "You do not have access to that page.")
                return redirect("home")
            request.profile = profile
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def notify(user, message, order=None):
    Notification.objects.create(user=user, message=message, order=order)


def user_orders(user):
    qs = Order.objects.select_related("hall", "restaurant")
    return qs.filter(restaurant__owner=user) if user.role == User.RESTAURANT else qs.filter(hall__owner=user)


def clean_selection(source, defaults=None):
    sel = {}
    for lvl in LEVELS:
        val = source.get(lvl) if source is not None else None
        if val is None and defaults is not None:
            val = getattr(defaults, lvl + "_id", "")
        sel[lvl] = str(val) if val and str(val).isdigit() else ""
    return sel


# ---------------- public pages ----------------
def home(request):
    ctx = {"n_restaurants": Restaurant.objects.count(), "n_halls": ConventionHall.objects.count(),
           "n_orders": Order.objects.filter(status=Order.CONFIRMED).count()}
    return render(request, "home.html", ctx)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to Food Bridge! Your account is ready.")
        return redirect("dashboard")
    sel = clean_selection(request.POST if request.method == "POST" else None)
    return render(request, "register.html", {"form": form, "divisions": Division.objects.all(), "sel": sel})


@login_required
def dashboard(request):
    if request.user.role == User.RESTAURANT:
        return redirect("restaurant_dashboard")
    if request.user.is_superuser and not hasattr(request.user, "hall"):
        return redirect("/admin/")
    return redirect("hall_dashboard")


def api_locations(request):
    mapping = {"district": (District, "division_id"), "upazila": (Upazila, "district_id"),
               "thana": (Thana, "upazila_id"), "post_office": (PostOffice, "thana_id")}
    level, parent = request.GET.get("level"), request.GET.get("parent", "")
    if level not in mapping or not parent.isdigit():
        return JsonResponse({"results": []})
    model, field = mapping[level]
    return JsonResponse({"results": list(model.objects.filter(**{field: parent}).values("id", "name"))})


# ---------------- restaurant side ----------------
@role_required(User.RESTAURANT)
def restaurant_dashboard(request):
    r = request.profile
    items = r.items.all()
    orders = r.orders.select_related("hall")
    ctx = {"restaurant": r, "items": items,
           "n_items": items.count(),
           "n_pending": orders.filter(status=Order.PENDING).count(),
           "n_confirmed": orders.filter(status=Order.CONFIRMED).count(),
           "recent_orders": orders[:5]}
    return render(request, "restaurant_dashboard.html", ctx)


@role_required(User.RESTAURANT)
def food_add(request):
    form = FoodItemForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.restaurant = request.profile
        item.save()
        messages.success(request, f"{item.name} added to your menu.")
        return redirect("restaurant_dashboard")
    return render(request, "food_form.html", {"form": form, "title": "Add a food item"})


@role_required(User.RESTAURANT)
def food_edit(request, pk):
    item = get_object_or_404(FoodItem, pk=pk, restaurant=request.profile)
    form = FoodItemForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Food item updated.")
        return redirect("restaurant_dashboard")
    return render(request, "food_form.html", {"form": form, "title": f"Edit {item.name}"})


@role_required(User.RESTAURANT)
@require_POST
def food_delete(request, pk):
    item = get_object_or_404(FoodItem, pk=pk, restaurant=request.profile)
    item.delete()
    messages.success(request, "Food item deleted.")
    return redirect("restaurant_dashboard")


@role_required(User.RESTAURANT)
@require_POST
def order_action(request, pk, action):
    order = get_object_or_404(Order, pk=pk, restaurant=request.profile)
    if order.status != Order.PENDING:
        messages.info(request, "This order has already been handled.")
        return redirect("order_detail", pk=pk)

    if action == "reject":
        order.status = Order.REJECTED
        order.save(update_fields=["status"])
        notify(order.hall.owner, f"Order #{order.pk} was declined by {order.restaurant.name}.", order)
        messages.success(request, "Order rejected.")
        return redirect("order_detail", pk=pk)

    if action != "confirm":
        raise PermissionDenied

    with transaction.atomic():
        items = list(order.items.all())
        foods = {f.id: f for f in FoodItem.objects.select_for_update()
                 .filter(id__in=[i.food_id for i in items if i.food_id])}
        short = [i.name for i in items
                 if i.food_id not in foods or not foods[i.food_id].is_active
                 or foods[i.food_id].quantity < i.total_qty]
        if short:
            messages.error(request, "Not enough stock for: " + ", ".join(short) +
                           ". Update your stock or reject this order.")
            return redirect("order_detail", pk=pk)
        for i in items:
            f = foods[i.food_id]
            f.quantity -= i.total_qty
            f.save(update_fields=["quantity"])
        order.status = Order.CONFIRMED
        order.save(update_fields=["status"])
        notify(order.hall.owner,
               f"Order #{order.pk} was confirmed by {order.restaurant.name}. Your bill is ready to download.", order)
    messages.success(request, "Order confirmed and stock updated.")
    return redirect("order_detail", pk=pk)


# ---------------- hall side ----------------
@role_required(User.HALL)
def hall_dashboard(request):
    orders = user_orders(request.user)
    ctx = {"hall": request.profile, "recent_orders": orders[:5],
           "n_pending": orders.filter(status=Order.PENDING).count(),
           "n_confirmed": orders.filter(status=Order.CONFIRMED).count(),
           "n_total": orders.count()}
    return render(request, "hall_dashboard.html", ctx)


@role_required(User.HALL)
def find_restaurants(request):
    hall = request.profile
    has_query = any(request.GET.get(l) for l in LEVELS)
    sel = clean_selection(request.GET if has_query else None, defaults=hall)

    base = Restaurant.objects.annotate(
        stock_items=Count("items", filter=Q(items__quantity__gt=0, items__is_active=True))
    ).filter(stock_items__gt=0).select_related("post_office", "thana", "upazila", "district", "division")

    qs = base
    for lvl in reversed(LEVELS):
        if sel[lvl]:
            qs = base.filter(**{lvl + "_id": sel[lvl]})
            break
    nearby = []
    if sel["district"]:
        nearby = base.filter(district_id=sel["district"]).exclude(pk__in=[r.pk for r in qs])
    return render(request, "find_restaurants.html", {
        "divisions": Division.objects.all(), "sel": sel,
        "restaurants": qs, "nearby": nearby})


@role_required(User.HALL)
def place_order(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    foods = restaurant.items.filter(is_active=True, quantity__gt=0)

    if request.method == "POST":
        errors, lines = [], []
        try:
            guests = int(request.POST.get("guests", "0"))
        except ValueError:
            guests = 0
        event_date = parse_date(request.POST.get("event_date", "") or "")
        if guests < 1:
            errors.append("Enter the number of guests (at least 1).")
        if not event_date or event_date < timezone.localdate():
            errors.append("Choose an event date that is today or later.")
        for f in foods:
            try:
                per_person = int(request.POST.get(f"pp_{f.id}") or 0)
            except ValueError:
                per_person = 0
            if per_person > 0 and guests > 0:
                need = per_person * guests
                if need > f.quantity:
                    errors.append(f"{f.name}: you need {need} but only {f.quantity} are in stock.")
                lines.append((f, per_person, need))
        if not lines:
            errors.append("Select at least one food item.")
        if not errors:
            with transaction.atomic():
                order = Order.objects.create(hall=request.profile, restaurant=restaurant, guests=guests,
                                             event_date=event_date, note=request.POST.get("note", "")[:500])
                total = Decimal("0")
                for f, per_person, need in lines:
                    line_total = f.price * need
                    OrderItem.objects.create(order=order, food=f, name=f.name, unit_price=f.price,
                                             per_person=per_person, total_qty=need, line_total=line_total)
                    total += line_total
                order.total = total
                order.save(update_fields=["total"])
                notify(restaurant.owner,
                       f"New order #{order.pk} from {request.profile.name}: {guests} guests, BDT {total:,.2f}.", order)
            messages.success(request, f"Order sent to {restaurant.name}. Total: BDT {total:,.2f}.")
            return redirect("order_detail", pk=order.pk)
        for e in errors:
            messages.error(request, e)

    return render(request, "place_order.html", {"restaurant": restaurant, "foods": foods,
                                                "today": timezone.localdate().isoformat()})


@role_required(User.HALL)
def order_pdf(request, pk):
    order = get_object_or_404(Order, pk=pk, hall=request.profile)
    if order.status != Order.CONFIRMED:
        messages.error(request, "The bill is available after the restaurant confirms the order.")
        return redirect("order_detail", pk=pk)
    response = HttpResponse(build_bill_pdf(order), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="FoodBridge-Bill-{order.pk}.pdf"'
    return response


# ---------------- shared ----------------
@login_required
def order_list(request):
    return render(request, "order_list.html", {"orders": user_orders(request.user)})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("hall", "restaurant"), pk=pk)
    if request.user.id not in (order.hall.owner_id, order.restaurant.owner_id):
        raise PermissionDenied
    return render(request, "order_detail.html", {"order": order, "items": order.items.all()})


@login_required
def notifications(request):
    items = list(request.user.notifications.select_related("order")[:100])
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, "notifications.html", {"items": items})
