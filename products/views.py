from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import Lower
from .models import Product, Category, SubCategory, ProductInventory, Brand, Colour
from .forms import ProductForm
from checkout.models import Order, OrderLineItem
from django.core.paginator import Paginator

# Create your views here.


def update_session(request):

    cat_checked = request.POST.getlist('cat_checked[]')
    cat_checked_num = list(map(int, cat_checked))

    cat_indeterminate = request.POST.getlist('cat_indeterminate[]')
    cat_indeterminate_num = list(map(int, cat_indeterminate))

    sub_checked = request.POST.getlist('sub_checked[]')
    sub_checked_num = list(map(int, sub_checked))

    brand_checked = request.POST.getlist('brand_checked[]')
    brand_checked_num = list(map(int, brand_checked))

    colour_checked = request.POST.getlist('colour_checked[]')
    colour_checked_num = list(map(int, colour_checked))

    gender_checked = request.POST.getlist('gender_checked[]')
    gender_checked_num = list(map(int, gender_checked))

    if request.is_ajax():      
        try:
            request.session['cat_checked'] = cat_checked_num
            request.session['cat_indeterminate'] = cat_indeterminate_num
            request.session['sub_checked'] = sub_checked_num
            request.session['brand_checked'] = brand_checked_num
            request.session['colour_checked'] = colour_checked_num
            request.session['gender_checked'] = gender_checked_num
        except KeyError:
            return HttpResponse('Error')
    else:
        raise Http404
    
    return HttpResponse("Success")


def all_products(request):
    """A view to show all products, including sorting and search queries """

    categories_list = Category.objects.all().annotate(subcat_count=Count('subcategory'))
    subcategories_list = SubCategory.objects.all()
    brands = Brand.objects.all()
    colours = Colour.objects.all()
    genders = Product.gender.field.choices

    cat_checked = request.session.get('cat_checked', [])
    cat_indeterminate = request.session.get('cat_indeterminate', [])
    sub_checked = request.session.get('sub_checked', [])
    brand_checked = request.session.get('brand_checked', [])
    colour_checked = request.session.get('colour_checked', [])
    gender_checked = request.session.get('gender_checked', [])

    # if NO categories, sub-categories, brands, or colours retrieved from session
    if cat_checked == [] and sub_checked == [] and brand_checked == [] and colour_checked == [] and gender_checked == []:
        # then select all categories, sub-categories, brands and colours for view (except gift cards)
        cat_checked = list(categories_list.exclude(giftcard_category=True).values_list('id', flat=True))
        sub_checked = list(subcategories_list.exclude(category__giftcard_category=True).values_list('id', flat=True))
        brand_checked = list(brands.values_list('id', flat=True))
        colour_checked = list(colours.values_list('id', flat=True))   
        gender_checked_string = list([gender[0] for gender in genders])
        gender_checked = list(map(int, gender_checked_string))
    # print("ALL GENDER: ", gender_checked)

    # """ First get full product list and annotate the sale price of each item """                
    products = Product.objects.all().exclude(obsolete=True
        ).exclude(Q(has_gender=True), ~Q(gender__in=gender_checked)
        ).filter(
            Q(category__in=cat_checked) | Q(subcategory__in=sub_checked),
            Q(brand__in=brand_checked)
        ).annotate(order_count=Count('orderlineitem'))
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

    product_count = products.count()
    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories_list': categories_list,
        # 'subcategories_list': subcategories_list,
        'brands': brands,
        'colours': colours,
        'genders': genders,
        'products': page_obj,
        'product_count': product_count,
        'search_term': query,
        'current_categories': categories,
        'current_sorting': current_sorting,
        'cat_checked': cat_checked,
        'cat_indeterminate': cat_indeterminate,
        'sub_checked': sub_checked,
        'brand_checked': brand_checked,
        'colour_checked': colour_checked,
        'gender_checked': gender_checked,
        'is_paginated': 8,
        'paginate_by': 8
    }
    paginate_by = 8
    return render(request, 'products/products.html', context)
 


def product_detail(request, product_id):
    """A view to show individual product details """
    
    product = get_object_or_404(Product, pk=product_id)
    """ Calculate product sale price which will be used if sale in progress """
    # sale_price = product.price / 100 * (100 - product.category.sale_percent)


    """ Get Product that was ordered the most while ordering this selected product """
    """ First get a list of all Orders that include this selected Product """
    orders_with_this_product = OrderLineItem.objects.filter(product=product_id).values_list('order',flat=True)
    """ Next get a list of Product Items ordered in all of the Orders retrieved above BUT not giftcards """
    all_products_in_these_orders = OrderLineItem.objects.filter(order__in=orders_with_this_product).exclude(product__category__giftcard_category=True).exclude(product__obsolete=True)
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

    """ if orders found for this product hide Admin product delete option in product page """ 
    product_has_no_orders = True
    if orders_with_this_product:
        product_has_no_orders = False

    # print(len(each_product_count_desc))
    # print(each_product_count_desc[0]['product'], each_product_count_desc[0]['num_ordered'])

    # for key in each_product_count_desc:
    #     # for value in item.keys():
    #     print(key['product'], key['num_ordered'])


    context = {
        'product': product,
        # 'sale_price': sale_price,
        'freq_bought_together': freq_bought_together,
        'product_has_no_orders': product_has_no_orders,
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