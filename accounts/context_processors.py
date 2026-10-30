from django.conf import settings
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Notification
from banking.models import BankAccount
from upi.models import UPIAccount

def bank_context(request):
    context = {
        'BANK_NAME': getattr(settings, 'BANK_NAME', 'PRIME RESERVE BANK'),
        'BANK_TAGLINE': getattr(settings, 'BANK_TAGLINE', 'Banking Made Simple, Secure & Smarter.'),
        'BANK_IFSC_PREFIX': getattr(settings, 'BANK_IFSC_PREFIX', 'PRMB'),
        'IS_EDUCATIONAL_DEMO': getattr(settings, 'IS_EDUCATIONAL_DEMO', True),
        'DEMO_OTP_DISPLAY': getattr(settings, 'DEMO_OTP_DISPLAY', True),
        'user_accounts': [],
        'user_primary_account': None,
        'unread_notifications_count': 0,
        'recent_notifications': [],
        'user_upi_accounts': [],
        'linked_accounts': [],
        'linked_accounts_count': 0,
        'can_add_more_accounts': True,
    }

    if request.user.is_authenticated:
        accounts = BankAccount.objects.filter(user=request.user, status='ACTIVE').order_by('id')
        context['user_accounts'] = accounts
        context['user_primary_account'] = accounts.first() if accounts.exists() else None
        
        notifications = Notification.objects.filter(user=request.user)
        context['unread_notifications_count'] = notifications.filter(is_read=False).count()
        context['recent_notifications'] = notifications[:5]

        context['user_upi_accounts'] = UPIAccount.objects.filter(user=request.user, is_active=True)

        # Multi-Account Linked Sessions (Up to 4 accounts)
        linked_ids = request.session.get('linked_user_ids', [])
        if request.user.id not in linked_ids:
            linked_ids = [request.user.id] + [uid for uid in linked_ids if uid != request.user.id]
            request.session['linked_user_ids'] = linked_ids[:4]

        linked_list = []
        for uid in request.session.get('linked_user_ids', []):
            try:
                u = User.objects.select_related('profile').prefetch_related('bank_accounts').get(id=uid)
                if not u.is_active:
                    continue
                primary = u.bank_accounts.filter(status='ACTIVE').first()
                raw_bal = sum((acc.balance for acc in u.bank_accounts.filter(status='ACTIVE')), Decimal('0.00')) if hasattr(u, 'bank_accounts') else Decimal('0.00')
                bal = Decimal(f"{float(raw_bal):.2f}")
                linked_list.append({
                    'user': u,
                    'user_id': u.id,
                    'username': u.username,
                    'full_name': u.get_full_name() or u.username,
                    'cif_number': u.profile.cif_number if hasattr(u, 'profile') else 'N/A',
                    'masked_phone': u.profile.masked_phone() if hasattr(u, 'profile') else '',
                    'primary_account': primary,
                    'total_balance': bal,
                    'is_current': (u.id == request.user.id),
                })
            except User.DoesNotExist:
                continue

        context['linked_accounts'] = linked_list
        context['linked_accounts_count'] = len(linked_list)
        context['can_add_more_accounts'] = (len(linked_list) < 4)

    return context
