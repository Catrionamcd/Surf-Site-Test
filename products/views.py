from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import Lower
from .models import Product, Category
from .forms import ProductForm
from checkout.models import Order, OrderLineItem

# Create your views here.


def all_products(request):
    """A view to show all products, including sorting and search queries """

    # """ First get full product list and annotate the sale price of each item """
    products = Product.objects.all()
    # products = Product.objects.all().annotate(sale_price=F('price') / 100 * (100 - F('category__sale_percent')))

    query = None
    categories = None
    sort = None
    direction = None

    if request.GET:
        if 'sort' in request.GET:
            sortkey = request.GET['sort']
            sort = sortkey
            if sortkey == 'name':
                sortkey = 'lower_name'
                products = products.annotate(lower_name=Lower('name'))
            if sortkey == 'category':
                sortkey = 'category__name'
            if 'direction' in request.GET:
                direction = request.GET['direction']
                if direction == 'desc':
                    sortkey = f'-{sortkey}'
            products = products.order_by(sortkey)

        if 'category' in request.GET:
            categories = request.GET['category'].split(',')
            products = products.filter(category__name__in=categories)
            categories = Category.objects.filter(name__in=categories)

        if 'q' in request.GET:
            query = request.GET['q']
            if not query:
                messages.error(request, "You didn't enter any search criteria!")
                return redirect(reverse('products'))
            
            queries = Q(name__icontains=query) | Q(description__icontains=query)
            products = products.filter(queries)

    current_sorting = f'{sort}_{direction}'

    context = {
        'products': products,
        'search_term': query,
        'current_categories': categories,
        'current_sorting': current_sorting,

    }

    return render(request, 'products/products.html', context)


def product_detail(request, product_id):
    """A view to show individual product details """

    product = get_object_or_404(Product, pk=product_id)
    """ Calculate product sale price which will be used if sale in progress """
    # sale_price = product.price / 100 * (100 - product.category.sale_percent)

    """ Get Product that was ordered the most while ordering this selected product """
    """ First get a list of all Orders that include this selected Product """
    orders_with_this_product = OrderLineItem.objects.filter(product=product_id).values_list('order',flat=True)
    """ Next get a list of Product Items ordered in all of the Orders retrieved above """
    all_products_in_these_orders = OrderLineItem.objects.filter(order__in=orders_with_this_product)
    """ Now Count how many times each product was ordered across all of these Orders """
    each_product_count = all_products_in_these_orders.values('product').order_by('product').annotate(num_ordered=Count('product'))
    """ Finally sequence from largest to smallest count """
    each_product_count_desc = each_product_count.all().order_by('-num_ordered')

    freq_bought_together = ""
    # print(product_id)
    # print(product)
    """ First check if any additional products in the list. Current product plus at least one other """
    """ Only interested in highest count so take from start of list """
    if len(each_product_count_desc) > 1:
        """ first check if current product is at start of list and if it is then take the next one on the list """
        if not each_product_count_desc[0]['product'] == product_id:
            """ Must have been order at least 3 times with this product to be considered as Frequently Bought Together """
            if each_product_count_desc[0]['num_ordered'] > 2:
                freq_bought_together_id = each_product_count_desc[0]['product']
                freq_bought_together = get_object_or_404(Product, pk=freq_bought_together_id)
        else:
            if each_product_count_desc[1]['num_ordered'] > 2:
                freq_bought_together_id = each_product_count_desc[1]['product']
                freq_bought_together = get_object_or_404(Product, pk=freq_bought_together_id)

    # print(len(each_product_count_desc))
    # print(each_product_count_desc[0]['product'], each_product_count_desc[0]['num_ordered'])

    # for key in each_product_count_desc:
    #     # for value in item.keys():
    #     print(key['product'], key['num_ordered'])


    context = {
        'product': product,
        # 'sale_price': sale_price,
        'freq_bought_together': freq_bought_together,
    }

    return render(request, 'products/product_detail.html', context)


@login_required
def add_product(request):
    """ Add a product to the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry, only store owners can do that.')
        return redirect(reverse('home'))
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Successfully added product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(request, 'Failed to add product. Please ensure the form is valid.')
    else:
        form = ProductForm()
    
    template = 'products/add_product.html'
    context = {
        'form': form,
    }

    return render(request, template, context)

@login_required
def edit_product(request, product_id):
    """ Edit a product in the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry, only store owners can do that.')
        return redirect(reverse('home'))

    product = get_object_or_404(Product, pk=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Successfully updated product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(request, 'Failed to update product. Please ensure the form is valid.')
    else:
        form = ProductForm(instance=product)
        messages.info(request, f'You are editing {product.name}')

    template = 'products/edit_product.html'
    context = {
        'form': form,
        'product': product,
    }

    return render(request, template, context)

@login_required
def delete_product(request, product_id):
    """ Delete a product from the store """
    if not request.user.is_superuser:
        messages.error(request, 'Sorry, only store owners can do that.')
        return redirect(reverse('home'))

    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    messages.success(request, 'Product deleted!')
    return redirect(reverse('products'))