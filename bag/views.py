from django.shortcuts import render

# Create your Bag views here.


def view_bag(request):
    """A view that renders the Bag contents page"""

    return render(request, 'bag/bag.html')

