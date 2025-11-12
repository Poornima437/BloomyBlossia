from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Wallet

# Create your views here.
@login_required
def wallet_view(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by('-date')
    return render(request, 'user_profile/wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
    })