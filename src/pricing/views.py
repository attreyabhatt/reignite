from django.shortcuts import render

# Create your views here.
def pricing_home(request):
    return render(request, 'pricing/index.html')