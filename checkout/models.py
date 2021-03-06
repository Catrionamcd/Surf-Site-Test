import uuid

from django.db import models
from django.db.models import Sum
from django.conf import settings

from django_countries.fields import CountryField

from products.models import Product, ProductInventory
from profiles.models import UserProfile

from django import template
register = template.Library()


class Order(models.Model):
    order_number = models.CharField(max_length=32, null=False, editable=False)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='orders')
    full_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.EmailField(max_length=254, null=False, blank=False)
    phone_number = models.CharField(max_length=20, null=False, blank=False)
    country = CountryField(blank_label='Country *', null=False, blank=False)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    town_or_city = models.CharField(max_length=40, null=False, blank=False)
    street_address1 = models.CharField(max_length=80, null=False, blank=False)
    street_address2 = models.CharField(max_length=80, null=True, blank=True)
    county = models.CharField(max_length=80, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    delivery_cost = models.DecimalField(max_digits=6, decimal_places=2, null=False, default=0)
    order_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    original_bag = models.TextField(null=False, blank=False, default='')
    stripe_pid = models.CharField(max_length=254, null=False, blank=False, default='')

    def _generate_order_number(self):
        """
        Generate a random, unique order number using UUID
        """
        return uuid.uuid4().hex.upper()

    def update_total(self):
        """
        Update grand total each time a line item is added,
        accounting for delivery costs.
        """
        self.order_total = self.lineitems.aggregate(Sum('lineitem_total'))['lineitem_total__sum'] or 0
        if self.order_total < settings.FREE_DELIVERY_THRESHOLD:
            self.delivery_cost = self.order_total * settings.STANDARD_DELIVERY_PERCENTAGE / 100
        else:
            self.delivery_cost = 0
        self.grand_total = self.order_total + self.delivery_cost
        self.save()

    def save(self, *args, **kwargs):
        """
        Override the original save method to set the order number
        if it hasn't been set already.
        """
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderLineItem(models.Model):
    order = models.ForeignKey(Order, null=False, blank=False, on_delete=models.CASCADE, related_name='lineitems')
    product = models.ForeignKey(Product, null=False, blank=False, on_delete=models.CASCADE)
    product_inventory = models.ForeignKey(ProductInventory, null=True, blank=True, on_delete=models.CASCADE)
    product_size = models.CharField(max_length=2, null=True, blank=True) # XS, S, M, L, XL
    quantity = models.IntegerField(null=False, blank=False, default=0)
    lineitem_total = models.DecimalField(max_digits=6, decimal_places=2, null=False, blank=False, editable=False)

    def save(self, *args, **kwargs):
        """
        Override the original save method to set the lineitem total
        and update the order total.
        """
        if self.product.category.sale_percent > 0:
            self.lineitem_total = self.product.get_sale_price() * self.quantity
        else:
            self.lineitem_total = self.product.price * self.quantity
        super().save(*args, **kwargs)

        """ Now check if a Gift Card item purchase and create a Giftcard entry """
        if self.product.category.giftcard_category:
            for i in range(self.quantity):
                gift_card = GiftCard(
                    giftcard_value = self.product.price,
                    giftcard_value_remaining = self.product.price,
                    order_line_item = self,
                )
                gift_card.save()

    def __str__(self):
        return f'SKU {self.product.sku} on order {self.order.order_number} desc {self.product.name}'


class GiftCard(models.Model):
    giftcard_code = models.CharField(max_length=8, null=False, editable=False)
    giftcard_value = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    giftcard_value_remaining = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    order_line_item = models.ForeignKey(OrderLineItem, null=False, blank=False, on_delete=models.CASCADE, related_name='Giftcards')

    def __str__(self):
        return self.giftcard_code

    def _generate_giftcard_code(self):
        """
        Generate a random, unique giftcard code using UUID
        """
        return uuid.uuid4().hex[:8].upper()

    def save(self, *args, **kwargs):
        """
        Override the original save method to set the giftcard code
        if it hasn't been set already.
        """
        if not self.giftcard_code:
            self.giftcard_code = self._generate_giftcard_code()
        super().save(*args, **kwargs)

    # @register.filter
    # def giftcards_in_order_line(giftcards, order_line_item):  
    #     giftcards = GiftCard.filter(order_line_item=order_line_item)
    #     return giftcards
    #     # return giftcards.filter(order_line_item=order_line_item)
