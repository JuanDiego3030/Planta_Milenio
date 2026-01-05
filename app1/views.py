from urllib import request
from django.shortcuts import render
from .models import Prueba
from django.db import connections

def index(request):

    return render(request, 'index.html')
