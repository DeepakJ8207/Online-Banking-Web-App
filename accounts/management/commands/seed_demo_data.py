import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random

from accounts.models import Branch, CustomerProfile, AuditLog, Notification
from banking.models import BankAccount
from beneficiaries.models import Beneficiary
from transactions.models import Transaction
from upi.models import UPIAccount, UPITransaction
from bills.models import BillerCategory, Biller, BillPayment
from finance.models import LoanProduct, Loan, LoanRepayment, FixedDeposit, RecurringDeposit
from finance.views import calculate_emi

class Command(BaseCommand):
    help = 'Seeds complete realistic demo banking data for Prime Reserve Bank demonstration.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding PRIME RESERVE BANK database with rich demo data..."))

        # 1. Create Branches
        branches_data = [
            {'name': 'Mumbai Fort Main Branch', 'code': 'PRM001', 'ifsc': 'PRMB0001001', 'address': '12, Reserve Bank Marg, Fort', 'city': 'Mumbai', 'state': 'Maharashtra', 'pin': '400001', 'phone': '022-22661001'},
            {'name': 'Delhi Connaught Place Branch', 'code': 'PRM002', 'ifsc': 'PRMB0002001', 'address': 'B-Block, Connaught Place', 'city': 'New Delhi', 'state': 'Delhi', 'pin': '110001', 'phone': '011-23341002'},
            {'name': 'Bengaluru MG Road Branch', 'code': 'PRM003', 'ifsc': 'PRMB0003001', 'address': '45, Mahatma Gandhi Road', 'city': 'Bengaluru', 'state': 'Karnataka', 'pin': '560001', 'phone': '080-25581003'},
            {'name': 'Hyderabad HITEC City Branch', 'code': 'PRM004', 'ifsc': 'PRMB0004001', 'address': 'Cyber Gateway, Madhapur', 'city': 'Hyderabad', 'state': 'Telangana', 'pin': '500081', 'phone': '040-23111004'},
            {'name': 'Pune Shivaji Nagar Branch', 'code': 'PRM005', 'ifsc': 'PRMB0005001', 'address': 'FC Road, Shivaji Nagar', 'city': 'Pune', 'state': 'Maharashtra', 'pin': '411005', 'phone': '020-25671005'},
        ]

        branches = []
        for b in branches_data:
            br, _ = Branch.objects.get_or_create(
                branch_code=b['code'],
                defaults={
                    'branch_name': b['name'],
                    'ifsc_code': b['ifsc'],
                    'address': b['address'],
                    'city': b['city'],
                    'state': b['state'],
                    'pincode': b['pin'],
                    'contact_number': b['phone']
                }
            )
            branches.append(br)

        mumbai_branch = branches[0]
        delhi_branch = branches[1]

        # 2. Create Admin Superuser
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser('admin', 'admin@primereservebank.demo', 'Admin@12345')
            admin_user.first_name = "Chief Administrator"
            admin_user.last_name = "PRMB"
            admin_user.save()
            CustomerProfile.objects.create(
                user=admin_user,
                cif_number="98765432100",
                phone_number="9876500000",
                kyc_status="VERIFIED",
                is_internet_banking_active=True,
                address="PRMB Headquarters, Nariman Point",
                city="Mumbai",
                state="Maharashtra",
                pincode="400021"
            )
            self.stdout.write(self.style.SUCCESS("Created Superuser: admin / Admin@12345"))

        # 3. Create Demo Users
        # Demo User 1: Aarav Sharma (demo_user)
        user1, _ = User.objects.get_or_create(username='demo_user', defaults={'email': 'aarav.sharma@primereserve.demo', 'first_name': 'Aarav', 'last_name': 'Sharma'})
        user1.set_password('Demo@12345')
        user1.save()

        CustomerProfile.objects.get_or_create(
            user=user1,
            defaults={
                'cif_number': '98765432101',
                'phone_number': '9876543210',
                'date_of_birth': date(1995, 5, 14),
                'gender': 'MALE',
                'address': 'Flat 402, Sea Breeze Heights, Bandra West',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'pincode': '400050',
                'kyc_status': 'VERIFIED',
                'is_internet_banking_active': True
            }
        )

        acc1, _ = BankAccount.objects.get_or_create(
            account_number='10010020030045',
            defaults={
                'user': user1,
                'account_type': 'SAVINGS',
                'branch': mumbai_branch,
                'balance': Decimal('125450.00'),
                'status': 'ACTIVE',
                'nominee_name': 'Sunita Sharma',
                'nominee_relation': 'Mother',
                'nominee_age': 54,
                'daily_transfer_limit': Decimal('200000.00'),
                'opening_date': date(2022, 1, 15)
            }
        )
        acc1.set_transaction_pin('1234')
        acc1.save()

        acc1_curr, _ = BankAccount.objects.get_or_create(
            account_number='10010020030046',
            defaults={
                'user': user1,
                'account_type': 'CURRENT',
                'branch': mumbai_branch,
                'balance': Decimal('45000.00'),
                'status': 'ACTIVE',
                'nominee_name': 'Sunita Sharma',
                'nominee_relation': 'Mother',
                'nominee_age': 54,
                'daily_transfer_limit': Decimal('500000.00'),
                'opening_date': date(2023, 6, 10)
            }
        )
        acc1_curr.set_transaction_pin('1234')
        acc1_curr.save()

        upi1, _ = UPIAccount.objects.get_or_create(
            upi_id='demo_user@primereserve',
            defaults={
                'user': user1,
                'bank_account': acc1,
                'is_primary': True,
                'is_active': True
            }
        )
        upi1.set_pin('1234')
        upi1.save()

        # Demo User 2: Priya Patel (priya_sharma)
        user2, _ = User.objects.get_or_create(username='priya_sharma', defaults={'email': 'priya.patel@primereserve.demo', 'first_name': 'Priya', 'last_name': 'Patel'})
        user2.set_password('Demo@12345')
        user2.save()

        CustomerProfile.objects.get_or_create(
            user=user2,
            defaults={
                'cif_number': '98765432102',
                'phone_number': '9876543211',
                'date_of_birth': date(1997, 8, 22),
                'gender': 'FEMALE',
                'address': 'Tower 3, Palm Meadows, Whitefield',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'pincode': '560066',
                'kyc_status': 'VERIFIED',
                'is_internet_banking_active': True
            }
        )

        acc2, _ = BankAccount.objects.get_or_create(
            account_number='10010020030099',
            defaults={
                'user': user2,
                'account_type': 'SAVINGS',
                'branch': mumbai_branch,
                'balance': Decimal('85200.00'),
                'status': 'ACTIVE',
                'nominee_name': 'Kirit Patel',
                'nominee_relation': 'Father',
                'nominee_age': 58,
                'opening_date': date(2022, 9, 1)
            }
        )
        acc2.set_transaction_pin('1234')
        acc2.save()

        upi2, _ = UPIAccount.objects.get_or_create(
            upi_id='priya@primereserve',
            defaults={
                'user': user2,
                'bank_account': acc2,
                'is_primary': True,
                'is_active': True
            }
        )
        upi2.set_pin('1234')
        upi2.save()

        # Demo User 3: Rahul Verma (rahul_verma)
        user3, _ = User.objects.get_or_create(username='rahul_verma', defaults={'email': 'rahul.verma@primereserve.demo', 'first_name': 'Rahul', 'last_name': 'Verma'})
        user3.set_password('Demo@12345')
        user3.save()

        CustomerProfile.objects.get_or_create(
            user=user3,
            defaults={
                'cif_number': '98765432103',
                'phone_number': '9876543212',
                'date_of_birth': date(1994, 3, 10),
                'gender': 'MALE',
                'address': 'House 14, Defence Colony',
                'city': 'New Delhi',
                'state': 'Delhi',
                'pincode': '110024',
                'kyc_status': 'VERIFIED',
                'is_internet_banking_active': True
            }
        )

        acc3, _ = BankAccount.objects.get_or_create(
            account_number='10010020030088',
            defaults={
                'user': user3,
                'account_type': 'SALARY',
                'branch': delhi_branch,
                'balance': Decimal('62750.00'),
                'status': 'ACTIVE',
                'opening_date': date(2023, 2, 18)
            }
        )
        acc3.set_transaction_pin('1234')
        acc3.save()

        upi3, _ = UPIAccount.objects.get_or_create(
            upi_id='rahul@primereserve',
            defaults={
                'user': user3,
                'bank_account': acc3,
                'is_primary': True,
                'is_active': True
            }
        )
        upi3.set_pin('1234')
        upi3.save()

        # 4. Beneficiaries for user1 (demo_user)
        beneficiaries_data = [
            {'name': 'Priya Patel', 'acc': '10010020030099', 'ifsc': 'PRMB0001001', 'bank': 'PRIME RESERVE BANK', 'nick': 'Priya Colleague', 'phone': '9876543211'},
            {'name': 'Rahul Verma', 'acc': '10010020030088', 'ifsc': 'PRMB0002001', 'bank': 'PRIME RESERVE BANK', 'nick': 'Rahul Roommate', 'phone': '9876543212'},
            {'name': 'Rohan Gupta', 'acc': '918273645012', 'ifsc': 'SBIN0001234', 'bank': 'State Bank of India', 'nick': 'Rohan Landlord', 'phone': '9811223344'},
            {'name': 'Ananya Sen', 'acc': '654321098711', 'ifsc': 'HDFC0000456', 'bank': 'HDFC Bank', 'nick': 'Ananya Sister', 'phone': '9822334455'},
        ]

        for b in beneficiaries_data:
            Beneficiary.objects.get_or_create(
                user=user1,
                account_number=b['acc'],
                defaults={
                    'beneficiary_name': b['name'],
                    'ifsc_code': b['ifsc'],
                    'bank_name': b['bank'],
                    'nickname': b['nick'],
                    'mobile_number': b['phone'],
                    'is_active': True
                }
            )

        # 5. Bill Categories & Billers
        cat_data = [
            {'code': 'ELECTRICITY', 'name': 'Electricity', 'icon': 'bi-lightning-charge-fill', 'desc': 'Pay state & private electricity bills'},
            {'code': 'MOBILE_RECHARGE', 'name': 'Mobile Recharge', 'icon': 'bi-phone-fill', 'desc': 'Prepaid & Postpaid mobile recharge'},
            {'code': 'WATER', 'name': 'Water Supply', 'icon': 'bi-droplet-fill', 'desc': 'Municipal water board payments'},
            {'code': 'GAS', 'name': 'Piped Gas & LPG', 'icon': 'bi-fire', 'desc': 'Domestic piped gas & cylinder bookings'},
            {'code': 'BROADBAND', 'name': 'Broadband & DTH', 'icon': 'bi-wifi', 'desc': 'High-speed internet & TV subscriptions'},
        ]

        cat_objs = {}
        for c in cat_data:
            obj, _ = BillerCategory.objects.get_or_create(code=c['code'], defaults={'name': c['name'], 'icon': c['icon'], 'description': c['desc']})
            cat_objs[c['code']] = obj

        billers_data = [
            {'cat': 'ELECTRICITY', 'name': 'Tata Power - Mumbai', 'area': 'Mumbai Metro', 'label': 'Consumer ID (12 Digits)'},
            {'cat': 'ELECTRICITY', 'name': 'Adani Electricity Mumbai Ltd', 'area': 'Mumbai Suburbs', 'label': 'CA Number (9 Digits)'},
            {'cat': 'ELECTRICITY', 'name': 'BSES Rajdhani Power Ltd', 'area': 'Delhi NCR', 'label': 'Consumer Account No.'},
            {'cat': 'ELECTRICITY', 'name': 'BESCOM - Bengaluru', 'area': 'Bengaluru Metro', 'label': 'Account ID'},
            {'cat': 'MOBILE_RECHARGE', 'name': 'Jio Prepaid / Postpaid', 'area': 'Pan India', 'label': '10-Digit Mobile Number'},
            {'cat': 'MOBILE_RECHARGE', 'name': 'Airtel India', 'area': 'Pan India', 'label': '10-Digit Mobile Number'},
            {'cat': 'MOBILE_RECHARGE', 'name': 'Vodafone Idea (Vi)', 'area': 'Pan India', 'label': '10-Digit Mobile Number'},
            {'cat': 'WATER', 'name': 'Brihanmumbai Municipal Corp (BMC Water)', 'area': 'Mumbai', 'label': 'CCN Number'},
            {'cat': 'WATER', 'name': 'Delhi Jal Board', 'area': 'Delhi', 'label': 'K No. (Consumer ID)'},
            {'cat': 'GAS', 'name': 'Mahanagar Gas Limited (MGL)', 'area': 'Mumbai Region', 'label': 'Consumer No. (8 Digits)'},
            {'cat': 'GAS', 'name': 'Indraprastha Gas Limited (IGL)', 'area': 'Delhi NCR', 'label': 'BP Number'},
            {'cat': 'BROADBAND', 'name': 'Airtel Xstream Fiber', 'area': 'Pan India', 'label': 'Landline No. with STD Code'},
            {'cat': 'BROADBAND', 'name': 'JioFiber Broadband', 'area': 'Pan India', 'label': 'Service ID / Mobile No.'},
        ]

        for b in billers_data:
            Biller.objects.get_or_create(
                category=cat_objs[b['cat']],
                name=b['name'],
                defaults={'service_area': b['area'], 'consumer_label': b['label'], 'is_active': True}
            )

        # 6. Loan Products
        products_data = [
            {'name': 'Prime Personal Loan', 'type': 'PERSONAL', 'rate': Decimal('10.50'), 'min_a': Decimal('25000'), 'max_a': Decimal('1500000'), 'min_t': 12, 'max_t': 60, 'feat': 'Instant digital disbursal\nZero prepayment charges after 6 months\nMinimal documentation'},
            {'name': 'Prime Home Loan', 'type': 'HOME', 'rate': Decimal('8.40'), 'min_a': Decimal('500000'), 'max_a': Decimal('10000000'), 'min_t': 36, 'max_t': 240, 'feat': 'Lowest interest rates\nUp to 90% property value financing\nTax benefits under Section 80C & 24b'},
            {'name': 'Prime Auto / Car Loan', 'type': 'CAR', 'rate': Decimal('8.75'), 'min_a': Decimal('100000'), 'max_a': Decimal('3000000'), 'min_t': 12, 'max_t': 84, 'feat': 'Up to 100% on-road funding\nQuick approval within 30 minutes\nAttractive interest rates for EVs'},
            {'name': 'Prime Education Loan', 'type': 'EDUCATION', 'rate': Decimal('9.15'), 'min_a': Decimal('50000'), 'max_a': Decimal('5000000'), 'min_t': 12, 'max_t': 120, 'feat': 'Covers tuition fees & living expenses\nMoratorium period up to course completion + 1 year\nNo collateral up to ₹7.5 Lakhs'},
            {'name': 'Prime Instant Gold Loan', 'type': 'GOLD', 'rate': Decimal('7.90'), 'min_a': Decimal('20000'), 'max_a': Decimal('2500000'), 'min_t': 6, 'max_t': 36, 'feat': 'Instant cash against gold jewellery\nHighest value per gram\nFlexible interest-only repayment option'},
        ]

        loan_prods = {}
        for p in products_data:
            obj, _ = LoanProduct.objects.get_or_create(
                name=p['name'],
                defaults={
                    'loan_type': p['type'],
                    'interest_rate': p['rate'],
                    'min_amount': p['min_a'],
                    'max_amount': p['max_a'],
                    'min_tenure_months': p['min_t'],
                    'max_tenure_months': p['max_t'],
                    'features': p['feat'],
                    'is_active': True
                }
            )
            loan_prods[p['type']] = obj

        # 7. Sample Transactions for user1 (Aarav Sharma)
        if Transaction.objects.filter(sender_account=acc1).count() == 0:
            sample_txns = [
                {'days_ago': 25, 'type': 'CREDIT', 'cat': 'SALARY', 'amount': Decimal('75000.00'), 'sender': 'Tech Mahindra Corporate Payroll', 'receiver': 'Aarav Sharma', 'remarks': 'Monthly Salary Credit - Aug 2026', 'is_credit': True},
                {'days_ago': 22, 'type': 'BANK_TRANSFER', 'cat': 'TRANSFER', 'amount': Decimal('18000.00'), 'sender': 'Aarav Sharma', 'receiver': 'Rohan Gupta (Landlord)', 'remarks': 'Apartment Rent - Aug 2026', 'is_credit': False},
                {'days_ago': 18, 'type': 'BILL_PAYMENT', 'cat': 'BILLS', 'amount': Decimal('2450.00'), 'sender': 'Aarav Sharma', 'receiver': 'Tata Power Mumbai', 'remarks': 'Electricity Bill Ref #4001928374', 'is_credit': False},
                {'days_ago': 14, 'type': 'RECHARGE', 'cat': 'BILLS', 'amount': Decimal('749.00'), 'sender': 'Aarav Sharma', 'receiver': 'Jio Prepaid', 'remarks': '3-Month Unlimited Plan Recharge', 'is_credit': False},
                {'days_ago': 10, 'type': 'UPI_TRANSFER', 'cat': 'FOOD', 'amount': Decimal('1500.00'), 'sender': 'Aarav Sharma', 'receiver': 'Priya Patel (priya@primereserve)', 'remarks': 'Weekend Dinner Bill Split', 'is_credit': False},
                {'days_ago': 8, 'type': 'DEBIT', 'cat': 'SHOPPING', 'amount': Decimal('4200.00'), 'sender': 'Aarav Sharma', 'receiver': 'Amazon India Retail', 'remarks': 'Electronics & Books purchase', 'is_credit': False},
                {'days_ago': 5, 'type': 'INTEREST_CREDIT', 'cat': 'SALARY', 'amount': Decimal('1250.00'), 'sender': 'PRIME RESERVE BANK', 'receiver': 'Aarav Sharma', 'remarks': 'Q2 Savings Interest Credit', 'is_credit': True},
                {'days_ago': 2, 'type': 'UPI_TRANSFER', 'cat': 'TRANSFER', 'amount': Decimal('3000.00'), 'sender': 'Rahul Verma', 'receiver': 'Aarav Sharma', 'remarks': 'Concert Tickets Reimbursement', 'is_credit': True},
            ]

            for s in sample_txns:
                txn_time = timezone.now() - timedelta(days=s['days_ago'], hours=random.randint(1, 10))
                
                if s['is_credit']:
                    txn = Transaction.objects.create(
                        sender_name=s['sender'],
                        receiver_name=s['receiver'],
                        receiver_account=acc1,
                        amount=s['amount'],
                        transaction_type=s['type'],
                        category=s['cat'],
                        remarks=s['remarks'],
                        status='SUCCESS',
                        receiver_balance_after=acc1.balance
                    )
                else:
                    txn = Transaction.objects.create(
                        sender_name=s['sender'],
                        receiver_name=s['receiver'],
                        sender_account=acc1,
                        amount=s['amount'],
                        transaction_type=s['type'],
                        category=s['cat'],
                        remarks=s['remarks'],
                        status='SUCCESS',
                        sender_balance_after=acc1.balance
                    )
                # Override timestamp
                Transaction.objects.filter(id=txn.id).update(timestamp=txn_time)

        # 8. Sample Fixed Deposit & Recurring Deposit for user1
        if not FixedDeposit.objects.filter(user=user1).exists():
            FixedDeposit.objects.create(
                user=user1,
                linked_account=acc1,
                principal_amount=Decimal('50000.00'),
                interest_rate=Decimal('7.25'),
                tenure_months=12,
                maturity_amount=Decimal('53724.00'),
                interest_earned=Decimal('3724.00'),
                start_date=timezone.now().date() - timedelta(days=60),
                maturity_date=timezone.now().date() + timedelta(days=305),
                auto_renew=True,
                status='ACTIVE'
            )

        if not RecurringDeposit.objects.filter(user=user1).exists():
            RecurringDeposit.objects.create(
                user=user1,
                linked_account=acc1,
                monthly_deposit=Decimal('5000.00'),
                interest_rate=Decimal('7.00'),
                tenure_months=12,
                total_deposit=Decimal('60000.00'),
                maturity_amount=Decimal('62275.00'),
                interest_earned=Decimal('2275.00'),
                start_date=timezone.now().date() - timedelta(days=90),
                maturity_date=timezone.now().date() + timedelta(days=275),
                status='ACTIVE'
            )

        # 9. Sample Loan for user1
        if not Loan.objects.filter(user=user1).exists():
            p_loan_prod = loan_prods['PERSONAL']
            emi_val = calculate_emi(Decimal('150000.00'), p_loan_prod.interest_rate, 24)
            tot_p = emi_val * 24
            sample_loan = Loan.objects.create(
                user=user1,
                disbursal_account=acc1,
                loan_product=p_loan_prod,
                principal_amount=Decimal('150000.00'),
                interest_rate=p_loan_prod.interest_rate,
                tenure_months=24,
                monthly_emi=emi_val,
                outstanding_balance=tot_p - (emi_val * 3),
                total_amount_payable=tot_p,
                total_paid=emi_val * 3,
                status='ACTIVE',
                start_date=timezone.now().date() - timedelta(days=90),
                end_date=timezone.now().date() + timedelta(days=630)
            )
            # Create 3 paid installments and 21 due installments
            for i in range(1, 25):
                due_d = sample_loan.start_date + timedelta(days=i * 30)
                is_paid = (i <= 3)
                LoanRepayment.objects.create(
                    loan=sample_loan,
                    installment_number=i,
                    due_date=due_d,
                    emi_amount=emi_val,
                    paid_amount=emi_val if is_paid else Decimal('0.00'),
                    paid_date=due_d if is_paid else None,
                    status='PAID' if is_paid else 'DUE'
                )

        # 10. Sample Notifications & Audit Logs for user1
        if Notification.objects.filter(user=user1).count() == 0:
            Notification.objects.create(user=user1, title="Salary Credited", message="₹75,000.00 credited to your account 10010020030045 from Tech Mahindra Corp.", notification_type="SUCCESS")
            Notification.objects.create(user=user1, title="Electricity Bill Paid", message="₹2,450.00 paid successfully to Tata Power Mumbai. Ref: BILL-202609-001", notification_type="INFO")
            Notification.objects.create(user=user1, title="Security Alert", message="New login detected from IP 127.0.0.1 (Chrome on macOS)", notification_type="SECURITY")
            Notification.objects.create(user=user1, title="Quarterly Interest Credited", message="₹1,250.00 savings account interest credited to your account.", notification_type="SUCCESS")

        if AuditLog.objects.filter(user=user1).count() == 0:
            AuditLog.objects.create(user=user1, action="LOGIN", description="User logged in from IP 127.0.0.1", ip_address="127.0.0.1")
            AuditLog.objects.create(user=user1, action="TRANSFER", description="Transferred ₹18,000 to Rohan Gupta (Landlord)", ip_address="127.0.0.1")
            AuditLog.objects.create(user=user1, action="BILL_PAYMENT", description="Paid electricity bill ₹2,450 to Tata Power", ip_address="127.0.0.1")

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("Demo Login: demo_user / Demo@12345"))
        self.stdout.write(self.style.SUCCESS("Admin Login: admin / Admin@12345"))
