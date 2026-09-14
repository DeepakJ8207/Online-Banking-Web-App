import io
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from django.utils import timezone
from decimal import Decimal

def generate_account_statement_pdf(account, transactions, from_date, to_date):
    """
    Generates a professional PDF account statement using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0d2346")
    secondary_color = colors.HexColor("#1a56db")
    accent_color = colors.HexColor("#059669")
    gray_bg = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#e2e8f0")

    title_style = ParagraphStyle(
        'BankTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=primary_color,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'BankSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=12
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=primary_color,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=cell_style,
        fontName='Helvetica-Bold'
    )
    cell_credit = ParagraphStyle(
        'TableCellCredit',
        parent=cell_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#059669")
    )
    cell_debit = ParagraphStyle(
        'TableCellDebit',
        parent=cell_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#dc2626")
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7,
        textColor=colors.HexColor("#64748b"),
        alignment=1, # Center
        spaceBefore=12
    )

    # 1. Header Banner
    story.append(Paragraph("PRIME RESERVE BANK", title_style))
    story.append(Paragraph("Banking Made Simple, Secure & Smarter. | Registered Educational Banking Portal", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=0, spaceAfter=12))

    # 2. Account & Customer Meta Information Table
    cust = account.user.profile if hasattr(account.user, 'profile') else None
    cust_name = account.user.get_full_name() or account.user.username
    cif_no = cust.cif_number if cust else "N/A"
    phone_no = cust.phone_number if cust else "N/A"

    info_data = [
        [
            Paragraph(f"<b>Account Holder:</b> {cust_name}", cell_style),
            Paragraph(f"<b>Account Number:</b> {account.account_number}", cell_style)
        ],
        [
            Paragraph(f"<b>Customer ID / CIF:</b> {cif_no}", cell_style),
            Paragraph(f"<b>Account Type:</b> {account.get_account_type_display()}", cell_style)
        ],
        [
            Paragraph(f"<b>Branch:</b> {account.branch.branch_name} ({account.branch.ifsc_code})", cell_style),
            Paragraph(f"<b>Current Balance:</b> ₹{account.balance:,.2f}", cell_bold)
        ],
        [
            Paragraph(f"<b>Statement Period:</b> {from_date.strftime('%d %b %Y')} to {to_date.strftime('%d %b %Y')}", cell_style),
            Paragraph(f"<b>Generated On:</b> {timezone.now().strftime('%d %b %Y, %I:%M %p')}", cell_style)
        ]
    ]

    info_table = Table(info_data, colWidths=[260, 260])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), gray_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # 3. Transaction Summary Calculation
    total_credit = Decimal('0.00')
    total_debit = Decimal('0.00')

    txn_rows = [
        [
            Paragraph("<b>Date & Time</b>", cell_bold),
            Paragraph("<b>Txn ID / Ref</b>", cell_bold),
            Paragraph("<b>Description / Remarks</b>", cell_bold),
            Paragraph("<b>Debit (₹)</b>", cell_bold),
            Paragraph("<b>Credit (₹)</b>", cell_bold),
            Paragraph("<b>Balance (₹)</b>", cell_bold)
        ]
    ]

    for txn in transactions:
        is_sender = (txn.sender_account_id == account.id)
        is_receiver = (txn.receiver_account_id == account.id)

        debit_str = "-"
        credit_str = "-"
        balance_str = "-"

        if is_sender:
            total_debit += txn.amount
            debit_str = f"₹{txn.amount:,.2f}"
            desc = f"To {txn.receiver_name} | {txn.remarks}"
            if txn.sender_balance_after is not None:
                balance_str = f"₹{txn.sender_balance_after:,.2f}"
            debit_p = Paragraph(debit_str, cell_debit)
            credit_p = Paragraph(credit_str, cell_style)
        else:
            total_credit += txn.amount
            credit_str = f"₹{txn.amount:,.2f}"
            desc = f"From {txn.sender_name} | {txn.remarks}"
            if txn.receiver_balance_after is not None:
                balance_str = f"₹{txn.receiver_balance_after:,.2f}"
            debit_p = Paragraph(debit_str, cell_style)
            credit_p = Paragraph(credit_str, cell_credit)

        txn_rows.append([
            Paragraph(txn.timestamp.strftime('%d-%m-%Y<br/>%H:%M'), cell_style),
            Paragraph(f"<b>{txn.transaction_id}</b><br/>{txn.reference_number}", cell_style),
            Paragraph(desc, cell_style),
            debit_p,
            credit_p,
            Paragraph(balance_str, cell_bold)
        ])

    if len(txn_rows) == 1:
        txn_rows.append([
            Paragraph("No transactions recorded during this statement period.", cell_style),
            "", "", "", "", ""
        ])

    # 4. Summary Cards Bar
    summary_data = [
        [
            Paragraph(f"<b>Total Credits:</b> <font color='#059669'>+₹{total_credit:,.2f}</font>", cell_style),
            Paragraph(f"<b>Total Debits:</b> <font color='#dc2626'>-₹{total_debit:,.2f}</font>", cell_style),
            Paragraph(f"<b>Net Movement:</b> ₹{(total_credit - total_debit):,.2f}", cell_style),
            Paragraph(f"<b>Total Transactions:</b> {len(transactions)}", cell_style),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[130, 130, 130, 130])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # 5. Transactions Table
    story.append(Paragraph("Account Transaction Details", section_heading))
    txn_table = Table(txn_rows, colWidths=[70, 95, 175, 60, 60, 60], repeatRows=1)
    txn_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d2346")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('BOX', (0, 0), (-1, -1), 0.5, primary_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(txn_table)

    # 6. Disclaimer Footer
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "*** IMPORTANT: This statement is generated solely for college educational demonstration purposes. "
        "PRIME RESERVE BANK is a fictional simulated digital banking system. No actual financial or banking services are provided. ***",
        disclaimer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
