from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Beneficiary
from .forms import BeneficiaryForm
from accounts.services import log_audit_event, send_notification

@login_required
def beneficiary_list_view(request):
    """
    List all active beneficiaries for the current logged-in user.
    """
    query = request.GET.get('q', '').strip()
    beneficiaries = Beneficiary.objects.filter(user=request.user, is_active=True)

    if query:
        beneficiaries = beneficiaries.filter(
            models_Q_search(query)
        )

    return render(request, 'beneficiaries/list.html', {
        'beneficiaries': beneficiaries,
        'query': query
    })

def models_Q_search(query):
    from django.db.models import Q
    return Q(beneficiary_name__icontains=query) | Q(account_number__icontains=query) | Q(bank_name__icontains=query) | Q(nickname__icontains=query)


@login_required
def beneficiary_add_view(request):
    """
    Add a new beneficiary with validation and duplicate prevention.
    """
    if request.method == 'POST':
        form = BeneficiaryForm(request.POST, user=request.user)
        if form.is_valid():
            bene = form.save(commit=False)
            bene.user = request.user
            bene.save()

            log_audit_event("BENEFICIARY_ADD", f"Added beneficiary: {bene.beneficiary_name} ({bene.account_number})", user=request.user, request=request)
            send_notification(request.user, "New Beneficiary Added", f"{bene.beneficiary_name} has been added to your beneficiary list.", "SUCCESS")
            messages.success(request, f"Beneficiary '{bene.beneficiary_name}' added successfully!")
            return redirect('beneficiaries:list')
    else:
        form = BeneficiaryForm(user=request.user)

    return render(request, 'beneficiaries/add.html', {'form': form})


@login_required
def beneficiary_edit_view(request, beneficiary_id):
    """
    Edit beneficiary details (nickname, contact details).
    """
    bene = get_object_or_404(Beneficiary, id=beneficiary_id, user=request.user)

    if request.method == 'POST':
        form = BeneficiaryForm(request.POST, instance=bene, user=request.user)
        if form.is_valid():
            form.save()
            log_audit_event("BENEFICIARY_EDIT", f"Updated beneficiary {bene.beneficiary_name}", user=request.user, request=request)
            messages.success(request, f"Beneficiary '{bene.beneficiary_name}' updated successfully.")
            return redirect('beneficiaries:list')
    else:
        form = BeneficiaryForm(instance=bene, user=request.user)

    return render(request, 'beneficiaries/edit.html', {'form': form, 'beneficiary': bene})


@login_required
def beneficiary_delete_view(request, beneficiary_id):
    """
    Soft-delete / remove beneficiary from user's list.
    """
    bene = get_object_or_404(Beneficiary, id=beneficiary_id, user=request.user)
    if request.method == 'POST':
        name = bene.beneficiary_name
        bene.delete()
        log_audit_event("BENEFICIARY_DELETE", f"Deleted beneficiary {name}", user=request.user, request=request)
        messages.info(request, f"Beneficiary '{name}' was removed from your list.")
        return redirect('beneficiaries:list')

    return render(request, 'beneficiaries/delete_confirm.html', {'beneficiary': bene})
