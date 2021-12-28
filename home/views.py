from django.shortcuts import render
from products.models import Category

# Create your views here.


def index(request):
    """A view to return the index page"""

    """ First check if any Sales in place """
    sale_in_progress = ""
    sale_categories = Category.objects.filter(sale_percent__gt=0)
    if len(sale_categories)>0:
        sale_in_progress = True


    return render(
        request, 
        'home/index.html', 
        {
            "sale_in_progress": sale_in_progress,
        },
    )
