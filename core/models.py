from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    RESTAURANT = "restaurant"
    HALL = "hall"
    ROLE_CHOICES = [
        (RESTAURANT, "Restaurant admin"),
        (HALL, "Convention hall / NGO admin"),
    ]
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default=HALL)


# ---------- Location hierarchy ----------
class Division(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class District(models.Model):
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["name"]
        unique_together = ("division", "name")

    def __str__(self):
        return f"{self.name}, {self.division}"


class Upazila(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="upazilas")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["name"]
        unique_together = ("district", "name")

    def __str__(self):
        return f"{self.name}, {self.district.name}"


class Thana(models.Model):
    upazila = models.ForeignKey(Upazila, on_delete=models.CASCADE, related_name="thanas")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["name"]
        unique_together = ("upazila", "name")

    def __str__(self):
        return f"{self.name}, {self.upazila.name}"


class PostOffice(models.Model):
    thana = models.ForeignKey(Thana, on_delete=models.CASCADE, related_name="post_offices")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["name"]
        unique_together = ("thana", "name")

    def __str__(self):
        return f"{self.name}, {self.thana.name}"


class LocationMixin(models.Model):
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="+")
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="+")
    upazila = models.ForeignKey(Upazila, on_delete=models.PROTECT, related_name="+")
    thana = models.ForeignKey(Thana, on_delete=models.PROTECT, related_name="+")
    post_office = models.ForeignKey(PostOffice, on_delete=models.PROTECT, related_name="+")
    address = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    @property
    def location_text(self):
        parts = [self.address, self.post_office.name, self.thana.name,
                 self.upazila.name, self.district.name, self.division.name]
        return ", ".join(p for p in parts if p)


# ---------- Profiles ----------
class Restaurant(LocationMixin):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="restaurant")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ConventionHall(LocationMixin):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="hall")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name


# ---------- Food ----------
class FoodItem(models.Model):
    QUALITY_CHOICES = [("premium", "Premium"), ("standard", "Standard"), ("economy", "Economy")]
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES, default="standard")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit/plate (BDT)")
    quantity = models.PositiveIntegerField(default=0, help_text="Units currently in stock")
    image = models.ImageField(upload_to="foods/", blank=True)
    is_active = models.BooleanField(default=True, help_text="Show this item to customers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


# ---------- Orders ----------
class Order(models.Model):
    PENDING, CONFIRMED, REJECTED = "pending", "confirmed", "rejected"
    STATUS_CHOICES = [(PENDING, "Pending"), (CONFIRMED, "Confirmed"), (REJECTED, "Rejected")]

    hall = models.ForeignKey(ConventionHall, on_delete=models.CASCADE, related_name="orders")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
    guests = models.PositiveIntegerField()
    event_date = models.DateField()
    note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    food = models.ForeignKey(FoodItem, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    per_person = models.PositiveIntegerField()
    total_qty = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
