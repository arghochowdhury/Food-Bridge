from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html

from .models import (ConventionHall, District, Division, FoodItem, Notification, Order,
                     OrderItem, PostOffice, Restaurant, Thana, Upazila, User)

PORTAL_URL = "https://etradelicense.gov.bd"


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


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("name", "trade_license_no", "verification_status", "owner", "district", "verified_at")
    list_filter = ("verification_status", "division")
    search_fields = ("name", "trade_license_no", "owner__username")
    readonly_fields = ("portal_link", "verified_at")
    actions = ["mark_verified", "mark_rejected"]

    @admin.display(description="License check")
    def portal_link(self, obj):
        return format_html(
            'Check this number on the <a href="{}" target="_blank" rel="noopener">e-Trade License portal</a>: <b>{}</b>',
            PORTAL_URL, obj.trade_license_no or "none entered")

    @admin.action(description="Mark selected restaurants as verified")
    def mark_verified(self, request, queryset):
        count = 0
        for r in queryset:
            r.verification_status = Restaurant.VERIFIED
            r.verified_at = timezone.now()
            r.verification_note = ""
            r.save()
            Notification.objects.create(
                user=r.owner, message="Your trade license was verified. You can now add food items and receive orders.")
            count += 1
        self.message_user(request, f"{count} restaurant(s) verified.")

    @admin.action(description="Reject selected restaurants (license could not be verified)")
    def mark_rejected(self, request, queryset):
        count = 0
        for r in queryset:
            r.verification_status = Restaurant.REJECTED
            r.verified_at = None
            r.verification_note = "License could not be verified. Please re-enter the correct number."
            r.save()
            Notification.objects.create(
                user=r.owner, message="Your trade license could not be verified. Please re-enter the correct number from your dashboard.")
            count += 1
        self.message_user(request, f"{count} restaurant(s) rejected.")


admin.site.register([Division, District, Upazila, Thana, PostOffice])
admin.site.register([ConventionHall, FoodItem, Notification])
