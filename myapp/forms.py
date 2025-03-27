from django.forms import ModelForm
from .models import Aperd, Product, ProductData
from django import forms

class AperdForm(ModelForm):
    class Meta:
        model = Aperd
        fields = ['name', 'pic', 'progress', 'desc']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'pic': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'progress': forms.Select(attrs={
                'class': 'form-input'
            }),
            'desc': forms.TextInput(attrs={  # Changed from Textarea to TextInput
                'class': 'form-input'
            })
        }

class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'status', 'aperd']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-input'
            }),
            'aperd': forms.Select(attrs={
                'class': 'form-input'
            })
        }

class ProductDataForm(forms.ModelForm):
    class Meta:
        model = ProductData
        fields = ['date', 'aum', 'noa']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input'
            }),
            'aum': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01'
            }),
            'noa': forms.NumberInput(attrs={
                'class': 'form-input'
            })
        }   
