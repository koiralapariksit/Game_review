# transfers/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Transfer


def transfer_list(request):
    """
    View to display all transfers with optional filtering by transfer_type.
    Optimized with select_related('posted_by') and 12-item pagination.
    """
    transfers = Transfer.objects.select_related('posted_by').all().order_by('-transfer_date', '-created_at')
    
    # Filter by transfer_type if provided in GET parameters
    transfer_type = request.GET.get('type')
    if transfer_type and transfer_type in ['RUMOR', 'CONFIRMED', 'HISTORY']:
        transfers = transfers.filter(transfer_type=transfer_type)
    
    # Setup pagination (12 transfers per page)
    paginator = Paginator(transfers, 12)
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
    Optimized with pagination (12 items per page).
    """
    transfers = Transfer.objects.select_related('posted_by').filter(
        transfer_type='CONFIRMED'
    ).order_by('-transfer_date', '-created_at')
    
    paginator = Paginator(transfers, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transfers': page_obj,
        'page_title': 'Confirmed Transfers',
        'total_count': paginator.count,
    }
    
    return render(request, 'transfers/latest_transfers.html', context)


def transfer_rumors(request):
    """
    View to display only transfer rumors, ordered by date descending.
    Optimized with pagination (12 items per page).
    """
    transfers = Transfer.objects.select_related('posted_by').filter(
        transfer_type='RUMOR'
    ).order_by('-reliability_tier', '-transfer_date', '-created_at')
    
    paginator = Paginator(transfers, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transfers': page_obj,
        'page_title': 'Transfer Rumors & Intelligence',
        'total_count': paginator.count,
    }
    
    return render(request, 'transfers/transfer_rumors.html', context)
