from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName

def set_checkbox_true(template_pdf, field_name):
    for page in template_pdf.pages:
        annotations = page['/Annots']
        if annotations:from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName

def set_checkbox_true(template_pdf, field_name):
    for page in template_pdf.pages:
        annotations = page['/Annots']
        if annotations:
            for annotation in annotations:
                if annotation['/Subtype'] == '/Widget' and annotation['/T'] and annotation['/T'].to_unicode() == field_name:
                    annotation.update({
                        PdfName('V'): PdfName('Yes'),
                        PdfName('AS'): PdfName('Yes')
                    })
                    return True
    return False

def set_date_field(template_pdf, field_name, date_value):
    for page in template_pdf.pages:
        annotations = page['/Annots']
        if annotations:
            for annotation in annotations:
                if annotation['/Subtype'] == '/Widget' and annotation['/T'] and annotation['/T'].to_unicode() == field_name:
                    annotation.update({
                        PdfName('V'): PdfName(date_value.strftime('%Y-%m-%d'))
                    })
                    return True
    return False

def create_and_save_pdf(evaluation_data, achievements_data, field_names, pdf_path, output_pdf_path):
    template_pdf = PdfReader(pdf_path)
    modified = False

    # Update checkboxes based on evaluation data
    for field in field_names['checkboxes']:
        if set_checkbox_true(template_pdf, field):
            modified = True
    
    # Update date fields based on achievements data
    for field, date in achievements_data.items():
        if set_date_field(template_pdf, field, date):
            modified = True

    if modified:
        PdfWriter().write(output_pdf_path, template_pdf)
        for annotation in annotations:
            if annotation['/Subtype'] == '/Widget' and annotation['/T'] and annotation['/T'].to_unicode() == field_name:
                annotation.update({
                    PdfName('V'): PdfName('Yes'),
                    PdfName('AS'): PdfName('Yes')
                })
                return True
    return False

def set_date_field(template_pdf, field_name, date_value):
    for page in template_pdf.pages:
        annotations = page['/Annots']
        if annotations:
            for annotation in annotations:
                if annotation['/Subtype'] == '/Widget' and annotation['/T'] and annotation['/T'].to_unicode() == field_name:
                    annotation.update({
                        PdfName('V'): PdfName(date_value.strftime('%Y-%m-%d'))
                    })
                    return True
    return False

def create_and_save_pdf(evaluation_data, achievements_data, field_names, pdf_path, output_pdf_path):
    template_pdf = PdfReader(pdf_path)
    modified = False

    # Update checkboxes based on evaluation data
    for field in field_names['checkboxes']:
        if set_checkbox_true(template_pdf, field):
            modified = True
    
    # Update date fields based on achievements data
    for field, date in achievements_data.items():
        if set_date_field(template_pdf, field, date):
            modified = True

    if modified:
        PdfWriter().write(output_pdf_path, template_pdf)
