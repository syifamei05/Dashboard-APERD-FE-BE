from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.db import models
from django.db.models import Min, Max, Sum
from django.db.models.functions import TruncMonth, TruncYear
import json
from datetime import datetime, timedelta
from django.db import IntegrityError

from .models import Aperd, Product, ProductData

# from django.contrib.auth.decorators import login_required

from .forms import AperdForm, ProductForm, ProductDataForm


# Create your views here.

def loginPage(request):
    page = 'login'

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except:
            messages.error(request, 'User does not exist')
            return render(request, 'login.html', {'page': page})

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username OR password does not exist')

    # Clear any existing success messages before rendering login page
    storage = messages.get_messages(request)
    storage.used = True

    context = {'page': page}
    return render(request, 'login.html', context)

def logoutUser(request):
    logout(request) # Bkl delete session tokennya
    return redirect('login')

def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    aperds = Aperd.objects.filter(name__icontains=q)
    aperd_count = aperds.count()

    # Calculate totals for each APERD
    aperd_data = []
    total_aum_all = 0
    total_noa_all = 0

    for aperd in aperds:
        total_aum = ProductData.objects.filter(
            product__aperd=aperd
        ).aggregate(
            total_aum=Sum('aum')
        )['total_aum'] or 0

        total_noa = ProductData.objects.filter(
            product__aperd=aperd
        ).aggregate(
            total_noa=Sum('noa')
        )['total_noa'] or 0

        total_aum_all += total_aum
        total_noa_all += total_noa

        aperd_data.append({
            'name': aperd.name,
            'aum': float(total_aum),
            'noa': int(total_noa)
        })

    # Prepare chart data
    chart_data = {
        'labels': [data['name'] for data in aperd_data],
        'aum_values': [data['aum'] for data in aperd_data],
        'noa_values': [data['noa'] for data in aperd_data]
    }

    context = {
        'aperds': aperds,
        'aperd_count': aperd_count,
        'chart_data': json.dumps(chart_data),
        'total_aum': "{:,.2f}".format(total_aum_all),  # Format with commas and 2 decimal places
        'total_noa': "{:,}".format(total_noa_all)      # Format with commas
    }
    return render(request, 'myapp/home.html', context)


def aperd(request, pk):
    aperd = get_object_or_404(Aperd, id=pk)
    
    # Add product search functionality
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    products = Product.objects.filter(
        aperd=aperd,
        name__icontains=q
    )
    
    # Get filter parameters
    view_type = request.GET.get('view_type', 'year')
    time_range = request.GET.get('time_range', '5')

    # Get all product data for this APERD
    product_data = ProductData.objects.filter(product__aperd=aperd)

    # Apply time range filter if needed
    if time_range != 'all':
        years = int(time_range)
        start_date = datetime.now() - timedelta(days=365 * years)
        product_data = product_data.filter(date__gte=start_date)

    # Group and aggregate data based on view type
    if view_type == 'month':
        aggregated_data = product_data.annotate(
            period=TruncMonth('date')
        ).values('period').annotate(
            total_aum=Sum('aum'),
            total_noa=Sum('noa')
        ).order_by('period')
    else:  # year
        aggregated_data = product_data.annotate(
            period=TruncYear('date')
        ).values('period').annotate(
            total_aum=Sum('aum'),
            total_noa=Sum('noa')
        ).order_by('period')

    # Prepare chart data
    chart_data = {
        'labels': [d['period'].strftime('%b %Y' if view_type == 'month' else '%Y') for d in aggregated_data],
        'aum_values': [float(d['total_aum']) for d in aggregated_data],
        'noa_values': [int(d['total_noa']) for d in aggregated_data]
    }

    context = {
        'aperd': aperd,
        'products': products,  # This will now be filtered products
        'chart_data': json.dumps(chart_data),
        'view_type': view_type,
        'time_range': time_range
    }
    
    return render(request, 'myapp/aperd.html', context)

def addAperd(request):
    if request.method == 'POST':
        form = AperdForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = AperdForm()
    
    context = {'form': form}
    return render(request, 'myapp/addEditAperd.html', context) 

def editAperd(request,pk):
    aperd = Aperd.objects.get(id=pk)
    form = AperdForm(instance=aperd)
    # Pake instance biar nanti bkl akses id yang mau diedit
    # dan gak bakal buat room baru

    if request.method == 'POST':
        form = AperdForm(request.POST, instance=aperd)
        # Sama kyk reasoning di atas, ditambah instance biar
        # nanti dia edit room sesuai sm id dan bukan nambah
        # room baru.

        aperd.name = request.POST.get('name')
        aperd.pic = request.POST.get('pic')
        aperd.progress = request.POST.get('progress')
        aperd.desc = request.POST.get('desc')
        aperd.save()

        return redirect('home')
    
        # if form.is_valid():
        #     form.save()
        #     return redirect('home')

    context = {'form': form, 'aperd': aperd}
    return render(request, 'myapp/addEditAperd.html', context)

def deleteAperd(request, pk):
    aperd = Aperd.objects.get(id=pk)

    if request.method == 'POST':
        aperd.delete()
        return redirect('home')
    
    return render(request, 'myapp/delete.html', {'obj': aperd})   

def product(request, pk):
    product = Product.objects.get(id=pk)
    aperd = product.aperd

    # Get filter parameters
    view_type = request.GET.get('view_type', 'year')  # Default to yearly view
    time_range = request.GET.get('time_range', '5')   # Default to last 5 years

    # Base queryset
    data_query = ProductData.objects.filter(product=product)

    # Apply time range filter
    if time_range != 'all':
        years = int(time_range)
        start_date = datetime.now() - timedelta(days=365 * years)
        data_query = data_query.filter(date__gte=start_date)

    # Apply view type aggregation
    if view_type == 'month':
        data_query = data_query.annotate(
            period=TruncMonth('date')
        ).values('period').annotate(
            total_aum=models.Avg('aum'),
            total_noa=models.Avg('noa')
        ).order_by('period')
    else:  # year
        data_query = data_query.annotate(
            period=TruncYear('date')
        ).values('period').annotate(
            total_aum=models.Avg('aum'),
            total_noa=models.Avg('noa')
        ).order_by('period')

    # Prepare chart data
    chart_data = {
        'labels': [d['period'].strftime('%b %Y' if view_type == 'month' else '%Y') for d in data_query],
        'aum_values': [float(d['total_aum']) for d in data_query],
        'noa_values': [int(d['total_noa']) for d in data_query]
    }

    context = {
        'product': product,
        'aperd': aperd,
        'chart_data': json.dumps(chart_data),
        'view_type': view_type,
        'time_range': time_range,
        'product_data': ProductData.objects.filter(product=product).order_by('-date')
    }
    
    return render(request, 'myapp/product.html', context)

def addProduct(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            return redirect('aperd', pk=product.aperd.id)
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'title': 'Add New Product'  # Add title to context
    }
    return render(request, 'myapp/addEditProduct.html', context)

def editProduct(request,pk):
    product = Product.objects.get(id=pk)
    form = ProductForm(instance=product)
    # Pake instance biar nanti bkl akses id yang mau diedit
    # dan gak bakal buat room baru

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        # Sama kyk reasoning di atas, ditambah instance biar
        # nanti dia edit room sesuai sm id dan bukan nambah
        # room baru.

        if form.is_valid:
            form.save()
            return redirect('aperd', pk=product.aperd.id)

    context = {'form': form, 'product': product}
    return render(request, 'myapp/addEditAperd.html', context)

def deleteProduct(request, pk):
    product = Product.objects.get(id=pk)
    aperd_id = product.aperd.id

    if request.method == 'POST':
        product.delete()
        return redirect('aperd', pk=aperd_id)
    
    context = {'obj': product}
    return render(request, 'myapp/delete.html', context)  

def add_product_data(request, pk):
    product = get_object_or_404(Product, id=pk)
    
    if request.method == 'POST':
        form = ProductDataForm(request.POST)
        if form.is_valid():
            try:
                product_data = form.save(commit=False)
                product_data.product = product
                product_data.save()
                # messages.success(request, 'Data added successfully!')
                return redirect('product', pk=product.id)
            except IntegrityError:
                messages.error(request, 'Data for this date already exists. Please choose a different date or edit the existing data.')
                return render(request, 'myapp/addEditProduct.html', {
                    'form': form,
                    'product': product,
                    'title': 'Add Product Data'
                })
    else:
        form = ProductDataForm()
    
    context = {
        'form': form,
        'product': product,
        'title': 'Add Product Data'
    }
    return render(request, 'myapp/addEditProduct.html', context)

def edit_product_data(request, pk, data_pk):
    product_data = get_object_or_404(ProductData, id=data_pk, product_id=pk)
    
    if request.method == 'POST':
        form = ProductDataForm(request.POST, instance=product_data)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data updated successfully!')
            return redirect('product', pk=pk)
    else:
        form = ProductDataForm(instance=product_data)
    
    context = {
        'form': form,
        'product': product_data.product,
        'title': 'Edit Product Data'
    }
    return render(request, 'myapp/addEditProduct.html', context)

def delete_product_data(request, pk, data_pk):
    product_data = get_object_or_404(ProductData, id=data_pk, product_id=pk)
    
    if request.method == 'POST':
        product_data.delete()
        messages.success(request, 'Data deleted successfully!')
        return redirect('product', pk=pk)
    
    context = {
        'obj': product_data,
        'title': 'Delete Product Data'
    }
    return render(request, 'myapp/delete.html', context)  