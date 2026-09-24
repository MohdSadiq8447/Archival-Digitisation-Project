import yaml, json, os

with open('Bihar_Formats/pdf_formats.yaml', 'r') as f:
    data = yaml.safe_load(f)

for category in data['categories']:
    cat_name = category['name']
    
    # clear pdfs
    category['pdfs'] = []
    if 'default_pagination' in category:
        del category['default_pagination']
        
    fn = ''
    if cat_name == 'Civic Amenities':
        fn = '1981_Dadra_&_Nagar_Haveli_civic_amenities.pdf'
        pag = {'page_1_columns': [1, 10], 'page_2_columns': [11, 19]}
    elif cat_name == 'Medical and Educational Amenities':
        fn = '1981_Dadra_&_Nagar_Haveli_medical_educational_amenities.pdf'
        pag = {'page_1_columns': [1, 10], 'page_2_columns': [11, 20]}
    elif cat_name == 'Tehsil Appendix':
        fn = '1981_Dadra_&_Nagar_Haveli_tehsil_appendix.pdf'
        pag = {'page_1_columns': [1, 27], 'page_2_columns': [28, 56]}
        
    # check if file exists
    folder = ''
    if cat_name == 'Civic Amenities': folder = 'civic amenities'
    elif cat_name == 'Medical and Educational Amenities': folder = 'mededu'
    elif cat_name == 'Tehsil Appendix': folder = 'tehsil appendix'
    
    # Actually the filenames might be different. Let's list the folder
    actual_fn = os.listdir(os.path.join('Dadra & Nagar Haveli', folder))[0]
    
    category['pdfs'].append({
        'filename': actual_fn,
        'pagination': pag
    })

with open('Dadra_&_Nagar_Haveli_Formats/pdf_formats.yaml', 'w') as outf:
    yaml.dump(data, outf, sort_keys=False)
