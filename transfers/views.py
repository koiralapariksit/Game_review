
# transfers/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Transfer


def transfer_list(request):
    """
    View to display all transfers with optional filtering by transfer_type.
    Supports pagination (10 items per page).
    """
    # Get all transfers with related user data for efficiency
    transfers = Transfer.objects.select_related('posted_by').all()
    
    # Filter by transfer_type if provided in GET parameters
    transfer_type = request.GET.get('type')
    if transfer_type and transfer_type in ['RUMOR', 'CONFIRMED', 'HISTORY']:
        transfers = transfers.filter(transfer_type=transfer_type)
    
    # Setup pagination (10 transfers per page)
    paginator = Paginator(transfers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transfers': page_obj,  # For template compatibility
        'current_filter': transfer_type,
        'total_count': paginator.count,
    }
    
    return render(request, 'transfers/transfer_list.html', context)


def transfer_detail(request, id):
    """
    View to display detailed information about a specific transfer.
    """
    transfer = get_object_or_404(
        Transfer.objects.select_related('posted_by'), 
        pk=id
    )
    
    context = {
        'transfer': transfer,
    }
    
    return render(request, 'transfers/transfer_detail.html', context)


def latest_transfers(request):
    """
    View to display only confirmed transfers, ordered by date descending.
    Supports pagination (10 items per page).
    """
    # Get only confirmed transfers
    transfers = Transfer.objects.select_related('posted_by').filter(
        transfer_type='CONFIRMED'
    ).order_by('-transfer_date', '-created_at')
    
    # Setup pagination
    paginator = Paginator(transfers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transfers': page_obj,
        'page_title': 'Latest Confirmed Transfers',
        'total_count': paginator.count,
    }
    
    return render(request, 'transfers/latest_transfers.html', context)


def transfer_rumors(request):
    """
    View to display only transfer rumors, ordered by date descending.
    Supports pagination (10 items per page).
    """
    # Get only rumor transfers
    transfers = Transfer.objects.select_related('posted_by').filter(
        transfer_type='RUMOR'
    ).order_by('-transfer_date', '-created_at')
    
    # Setup pagination
    paginator = Paginator(transfers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transfers': page_obj,
        'page_title': 'Transfer Rumors',
        'total_count': paginator.count,
    }
    
    return render(request, 'transfers/transfer_rumors.html', context)