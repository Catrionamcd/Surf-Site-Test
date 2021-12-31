from .models import GiftCard
from django import template
register = template.Library()

@register.filter
def giftcards_in_order_line(giftcards, order_line_item):  
    giftcards = GiftCard.objects.filter(order_line_item=order_line_item)
    return giftcards