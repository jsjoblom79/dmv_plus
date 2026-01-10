"""
Service for generating PDF reports of student driving hours
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from django.utils import timezone


def generate_driving_hours_pdf(student, trips, parent_profile):
    """
    Generate a PDF report of driving hours for DMV submission

    Args:
        student: StudentProfile object
        trips: QuerySet of approved Trip objects
        parent_profile: ParentProfile of the parent generating the report

    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()

    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    # Header info style
    header_style = ParagraphStyle(
        'HeaderInfo',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT
    )

    # Footer style
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        alignment=TA_LEFT
    )

    # Add title
    title = Paragraph(
        "HOURS OBTAINED WHILE IN THE PRESENCE<br/>OF A LICENSED DRIVER",
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    # Add student information - horizontal layout using Paragraphs
    student_info_data = [[
        Paragraph(f"<b>Student Name:</b> {student.first_name} {student.last_name}", header_style),
        Paragraph(f"<b>Permit Number:</b> {student.permit_number or 'Not Provided'}", header_style),
        Paragraph(f"<b>Report Date:</b> {timezone.now().strftime('%m/%d/%Y')}", header_style)
    ]]

    student_info_table = Table(student_info_data, colWidths=[2.5 * inch, 2.0 * inch, 1.5 * inch])
    student_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(student_info_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Calculate totals
    total_minutes = sum(trip.duration for trip in trips if trip.duration)
    total_hours = total_minutes / 60
    night_trips = [trip for trip in trips if trip.is_night]
    night_minutes = sum(trip.duration for trip in night_trips if trip.duration)
    night_hours = night_minutes / 60
    day_hours = total_hours - night_hours

    # Add summary - 4 column layout using Paragraphs for bold text
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )

    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )

    summary_data = [
        [Paragraph('<b>Summary of Hours</b>', summary_style), '', '', ''],
        [Paragraph('Day Driving Hours:', label_style),
         Paragraph(f'{day_hours:.2f}', value_style),
         Paragraph('Total Driving Hours:', label_style),
         Paragraph(f'{total_hours:.2f}', value_style)],
        [Paragraph('Night Driving Hours:', label_style),
         Paragraph(f'{night_hours:.2f}', value_style),
         Paragraph('Total Sessions:', label_style),
         Paragraph(str(len(trips)), value_style)],
    ]

    summary_table = Table(summary_data, colWidths=[1.8 * inch, 1.0 * inch, 1.8 * inch, 1.4 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('SPAN', (0, 0), (-1, 0)),  # Merge header across all columns
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Add detailed trip listing
    elements.append(Paragraph("<b>Detailed Session Log</b>", summary_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Create table data
    table_data = [
        ['Date', 'Start Time', 'End Time', 'Duration\n(minutes)', 'Type', 'Approved By']
    ]

    # Sort trips by date
    sorted_trips = sorted(trips, key=lambda x: x.start_time)

    for trip in sorted_trips:
        row = [
            trip.start_time.strftime('%m/%d/%Y'),
            trip.start_time.strftime('%I:%M %p'),
            trip.end_time.strftime('%I:%M %p') if trip.end_time else 'N/A',
            str(trip.duration),
            'Night' if trip.is_night else 'Day',
            trip.parent.user.get_full_name() or trip.parent.user.email
        ]
        table_data.append(row)

    # Create the table
    trip_table = Table(
        table_data,
        colWidths=[1.0 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch, 0.7 * inch, 1.4 * inch]
    )

    # Style the table
    trip_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),

        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

        # Alternate row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))

    elements.append(trip_table)
    elements.append(Spacer(1, 0.5 * inch))

    # Add certification section
    cert_text = """
    <b>Certification</b><br/>
    I hereby certify that the information contained in this report is true and accurate to the best 
    of my knowledge. All driving sessions listed were conducted under my supervision or the supervision 
    of another licensed driver, and comply with the requirements set forth by the Department of Motor Vehicles.
    """

    elements.append(Paragraph(cert_text, footer_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Signature lines
    sig_data = [
        ['Parent/Guardian Signature: _________________________________',
         'Date: __________________'],
    ]

    sig_table = Table(sig_data, colWidths=[4 * inch, 2 * inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(sig_table)
    elements.append(Spacer(1, 0.1 * inch))

    # Printed name
    printed_name = Paragraph(
        f"<b>Printed Name:</b> {parent_profile.user.get_full_name()}",
        footer_style
    )
    elements.append(printed_name)

    # Add footer with generation info and branding
    elements.append(Spacer(1, 0.3 * inch))
    footer_text = f"Document generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}"
    elements.append(Paragraph(footer_text,
                              ParagraphStyle('FooterSmall',
                                             parent=styles['Normal'],
                                             fontSize=8,
                                             textColor=colors.grey,
                                             alignment=TA_CENTER)))

    elements.append(Spacer(1, 0.1 * inch))

    # Add DMV+ branding
    branding_style = ParagraphStyle(
        'Branding',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#4CAF50')
    )

    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey
    )

    elements.append(Paragraph("DMV+", branding_style))
    elements.append(Spacer(1, 0.05 * inch))
    elements.append(Paragraph("<b>D</b>rive, <b>M</b>anage, <b>V</b>erify", tagline_style))

    # Build PDF
    doc.build(elements)

    # Get the value of the BytesIO buffer and return it
    pdf = buffer.getvalue()
    buffer.close()

    return pdf