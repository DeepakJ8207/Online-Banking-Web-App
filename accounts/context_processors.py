from django.conf import settings
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
    }

    if request.user.is_authenticated:
        accounts = BankAccount.objects.filter(user=request.user, status='ACTIVE').order_by('id')
        context['user_accounts'] = accounts
        context['user_primary_account'] = accounts.first() if accounts.exists() else None
        
        notifications = Notification.objects.filter(user=request.user)
        context['unread_notifications_count'] = notifications.filter(is_read=False).count()
        context['recent_notifications'] = notifications[:5]

        context['user_upi_accounts'] = UPIAccount.objects.filter(user=request.user, is_active=True)

    return context
