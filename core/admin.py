from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (ConventionHall, District, Division, FoodItem, Notification, Order,
                     OrderItem, PostOffice, Restaurant, Thana, Upazila, User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Food Bridge", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "hall", "restaurant", "guests", "status", "total", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline]


admin.site.register([Division, District, Upazila, Thana, PostOffice])
admin.site.register([Restaurant, ConventionHall, FoodItem, Notification])
