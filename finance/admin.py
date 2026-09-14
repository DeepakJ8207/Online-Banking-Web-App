from django.contrib import admin
from .models import LoanProduct, Loan, LoanRepayment, FixedDeposit, RecurringDeposit

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'loan_type', 'interest_rate', 'min_amount', 'max_amount', 'min_tenure_months', 'max_tenure_months', 'is_active')
    list_filter = ('loan_type', 'is_active')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_account_number', 'user', 'loan_product', 'principal_amount', 'outstanding_balance', 'monthly_emi', 'status', 'start_date')
    search_fields = ('loan_account_number', 'user__username', 'loan_product__name')
    list_filter = ('status', 'loan_product__loan_type')
    readonly_fields = ('loan_account_number', 'created_at')

@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'installment_number', 'due_date', 'emi_amount', 'paid_amount', 'paid_date', 'status')
    list_filter = ('status', 'due_date')

@admin.register(FixedDeposit)
class FixedDepositAdmin(admin.ModelAdmin):
    list_display = ('fd_number', 'user', 'principal_amount', 'interest_rate', 'tenure_months', 'maturity_amount', 'maturity_date', 'status')
    search_fields = ('fd_number', 'user__username')
    list_filter = ('status', 'tenure_months')
    readonly_fields = ('fd_number', 'created_at')

@admin.register(RecurringDeposit)
class RecurringDepositAdmin(admin.ModelAdmin):
    list_display = ('rd_number', 'user', 'monthly_deposit', 'interest_rate', 'tenure_months', 'maturity_amount', 'maturity_date', 'status')
    search_fields = ('rd_number', 'user__username')
    list_filter = ('status', 'tenure_months')
    readonly_fields = ('rd_number', 'created_at')
