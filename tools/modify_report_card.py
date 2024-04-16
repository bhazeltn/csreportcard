import pandas as pd
import pdfrw

def load_mappings(csv_path):
    """ Load the field mappings from a CSV file. """
    return pd.read_csv(csv_path)

def update_pdf_field_names(pdf_template_path, mapping_df, output_pdf_path):

    # Load the PDF
    template_pdf = pdfrw.PdfReader(pdf_template_path)

    # Iterate through the pages and annotations (form fields)
    for page in template_pdf.pages:
        annotations = page['/Annots']
        if annotations:
            for annotation in annotations:
                if annotation['/Subtype'] == '/Widget' and annotation['/T']:
                    field_name = annotation['/T'][1:-1]  # Remove parentheses around the field name
                    # Find the new name in the dataframe
                    new_name = mapping_df.loc[mapping_df['Report Card Name'] == field_name, 'Our Name']
                    if not new_name.empty:
                        # Remove spaces or replace with underscores
                        new_name_cleaned = new_name.iloc[0].replace(' ', '_')
                        # Update the field name
                        annotation.update(pdfrw.PdfDict(T=pdfrw.objects.pdfstring.PdfString(f'({new_name_cleaned})')))

    # Save the updated PDF
    pdfrw.PdfWriter(output_pdf_path, trailer=template_pdf).write()

mapping_df = load_mappings('/home/bradley/development/csreportcard/data/report_card_mapping.csv')
print (mapping_df.head())

update_pdf_field_names('/home/bradley/development/csreportcard/app/templates/Report_Card_ENG_original.pdf', mapping_df,
                       '/home/bradley/development/csreportcard/app/templates/Report_Card_ENG.pdf')
