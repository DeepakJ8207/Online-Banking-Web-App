from django.db import transaction
from decimal import Decimal
from banking.models import BankAccount
from transactions.models import Transaction
from accounts.services import log_audit_event, send_notification
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class TransferService:
    @classmethod
    def execute_transfer(
        cls,
        sender_account_id,
        amount,
        transfer_type='BANK_TRANSFER',
        receiver_account_number=None,
        receiver_ifsc=None,
        receiver_name='',
        remarks='Fund Transfer',
        category='TRANSFER',
        user=None,
        request=None
    ):
        """
        Executes a secure atomic double-sided financial transfer.
        Uses select_for_update() to prevent race conditions and double spending.
        """
        amount = Decimal(str(amount))
        if amount <= Decimal('0.00'):
            return False, "Transfer amount must be greater than ₹0.00", None

        try:
            with transaction.atomic():
                # 1. Lock and load sender account
                sender = BankAccount.objects.select_for_update().get(id=sender_account_id)

                if sender.status != 'ACTIVE':
                    return False, f"Sender account {sender.masked_account_number()} is not active ({sender.get_status_display()}).", None

                if sender.balance < amount:
                    return False, f"Insufficient balance. Available balance: ₹{sender.balance:,.2f}, required: ₹{amount:,.2f}", None

                # 2. Check internal receiver if account number is provided
                receiver = None
                if receiver_account_number:
                    receiver_qs = BankAccount.objects.select_for_update().filter(
                        account_number=str(receiver_account_number).strip(),
                        status='ACTIVE'
                    )
                    if receiver_qs.exists():
                        receiver = receiver_qs.first()

                # Self-transfer check
                if receiver and receiver.id == sender.id:
                    return False, "Cannot transfer funds to the exact same account.", None

                # 3. Debit sender account
                sender.balance -= amount
                sender.save(update_fields=['balance', 'updated_at'])

                # 4. Credit receiver account if internal
                receiver_balance_after = None
                if receiver:
                    receiver.balance += amount
                    receiver.save(update_fields=['balance', 'updated_at'])
                    receiver_balance_after = receiver.balance
                    if not receiver_name:
                        receiver_name = receiver.user.get_full_name() or receiver.user.username

                sender_name = sender.user.get_full_name() or sender.user.username
                if not receiver_name:
                    receiver_name = f"Account {receiver_account_number} ({receiver_ifsc or 'Other Bank'})"

                # 5. Create immutable Transaction record
                txn = Transaction.objects.create(
                    sender_account=sender,
                    receiver_account=receiver,
                    sender_name=sender_name,
                    receiver_name=receiver_name,
                    amount=amount,
                    transaction_type=transfer_type,
                    status='SUCCESS',
                    category=category,
                    remarks=remarks or "Fund Transfer",
                    sender_balance_after=sender.balance,
                    receiver_balance_after=receiver_balance_after
                )

                # 6. Notifications & Audit Logs
                send_notification(
                    user=sender.user,
                    title="Funds Debited",
                    message=f"₹{amount:,.2f} debited from A/c {sender.masked_account_number()} to {receiver_name}. Ref: {txn.reference_number}. Balance: ₹{sender.balance:,.2f}",
                    notification_type="INFO"
                )

                if receiver and receiver.user != sender.user:
                    send_notification(
                        user=receiver.user,
                        title="Funds Credited",
                        message=f"₹{amount:,.2f} credited to A/c {receiver.masked_account_number()} from {sender_name}. Ref: {txn.reference_number}. Balance: ₹{receiver.balance:,.2f}",
                        notification_type="SUCCESS"
                    )

                log_audit_event(
                    action="TRANSFER",
                    description=f"{transfer_type}: Transferred ₹{amount} from {sender.account_number} to {receiver_name} (Txn: {txn.transaction_id})",
                    user=user or sender.user,
                    request=request
                )

                return True, "Transfer completed successfully.", txn

        except BankAccount.DoesNotExist:
            return False, "Sender account does not exist.", None
        except Exception as e:
            logger.exception("Transfer processing failed with error")
            return False, f"Transaction failed: {str(e)}", None
