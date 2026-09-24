import yaml

for state in ['Dadra_&_Nagar_Haveli', 'Daman_&_Diu', 'Gujarat']:
    path = f"{state}_Formats/pdf_formats.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    for cat in data['categories']:
        if cat['name'] == 'Medical and Educational Amenities':
            for pdf in cat['pdfs']:
                pag = pdf['pagination']
                if 'page_1_columns' in pag and pag['page_1_columns'] == [1, 10]:
                    pag['page_1_columns'] = [1, 9]
                if 'page_2_columns' in pag and pag['page_2_columns'] == [11, 20]:
                    pag['page_2_columns'] = [10, 20]
    with open(path, 'w') as outf:
        yaml.dump(data, outf, sort_keys=False)
