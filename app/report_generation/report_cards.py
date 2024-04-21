from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName
import os
import pandas as pd

def update_evaluations(annotations, evaluation_data):
    """Update checkboxes in the PDF based on evaluation data."""
    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            field_name_pdf = annotation['/T'].to_unicode()
            mapped_field_name = map_field_name(field_name_pdf)  # Ensure proper name mapping
            if mapped_field_name in evaluation_data:
                checkbox_value = 'Yes' if evaluation_data[mapped_field_name] else 'Off'
                annotation.update({
                    PdfName('V'): PdfName(checkbox_value),
                    PdfName('AS'): PdfName(checkbox_value)
                })

def update_achievements(annotations, achievements_data, skater_name):
    """Insert achievement dates into the PDF based on achievements data."""
    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            pdf_field_name = annotation['/T'].to_unicode().strip('()')
            mapped_field_name = map_field_name(pdf_field_name)
            if mapped_field_name in achievements_data.columns:
                skater_achievement = achievements_data.loc[achievements_data['Skater Name'] == skater_name, mapped_field_name]
                if not skater_achievement.empty and not pd.isna(skater_achievement.iloc[0]):
                    # Check if the data is a datetime object and format it, otherwise use it as is
                    if isinstance(skater_achievement.iloc[0], pd.Timestamp):
                        date_str = skater_achievement.iloc[0].strftime('%Y-%m-%d')
                    else:
                        date_str = skater_achievement.iloc[0]
                    annotation.update(PdfDict(V=date_str))


def generate_individual_report_card(evaluation_data, achievements_df, template_path, output_path):
    """Generate an individual report card for a skater."""
    template_pdf = PdfReader(template_path)
    for page in template_pdf.pages:
        annotations = page['/Annots']
        if annotations:
            update_evaluations(annotations, evaluation_data)
            update_achievements(annotations, achievements_df, evaluation_data['Skater Name'])
    PdfWriter(output_path, trailer=template_pdf).write()  # Save the filled PDF

def merge_report_cards(directory_path, output_path):
    """
    Merge all PDF files in a specified directory into a single PDF file.
    
    Args:
        directory_path (str): Path to the directory containing the PDF files.
        output_path (str): Path to save the merged PDF file.
    """
    writer = PdfWriter()
    files = [f for f in os.listdir(directory_path) if f.endswith('.pdf')]
    files.sort()  # Optional: sort files if needed

    for filename in files:
        path = os.path.join(directory_path, filename)
        reader = PdfReader(path)
        writer.addpages(reader.pages)
        print(f"Added {filename}")

    writer.write(output_path)
    print(f"Merged PDF saved as {output_path}")



def map_field_name(field_name):
    """Map the field name from the PDF to the column names used in the dataframes."""
    return field_name.replace('_', ' ')

def create_report_cards(evaluations_df, achievements_df, template_path, output_directory):
    """Generate report cards for all skaters and save them as individual PDFs."""
    print ("hello")
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)  # Ensure the output directory exists

    individual_directory = os.path.join(output_directory, 'individual')
    if not os.path.exists(individual_directory):
        os.makedirs(individual_directory)  # Ensure the output directory exists

    for index, evaluation_data in evaluations_df.iterrows():
        skater_name = evaluation_data['Skater Name']
        output_path = os.path.join(individual_directory, f"{skater_name.replace(' ', '_')}_Report_Card.pdf")
        generate_individual_report_card(evaluation_data, achievements_df, template_path, output_path)
        print(f"Report card generated for {skater_name} at {output_path}")
    
    merged_path = os.path.join(output_directory, 'report_cards.pdf')
    
    merge_report_cards(individual_directory, merged_path)
