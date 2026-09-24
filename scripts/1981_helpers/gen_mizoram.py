import yaml
import os

with open('Madhya_Pradesh_Formats/pdf_formats.yaml') as f:
    mp_data = yaml.safe_load(f)

civic_cols = next(c['columns'] for c in mp_data['categories'] if 'civic' in c['name'].lower())
mededu_cols = next(c['columns'] for c in mp_data['categories'] if 'medical' in c['name'].lower())
tehsil_cols = next(c['columns'] for c in mp_data['categories'] if 'tehsil' in c['name'].lower())

mizoram_data = {
    "state": "Mizoram",
    "categories": [
        {
            "name": "Civic Amenities",
            "columns": civic_cols,
            "pdfs": [
                {
                    "filenames": ["1981_Aizawl_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 19]]}
                },
                {
                    "filenames": ["1981_Chhimtuipui_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 19]]}
                }
            ]
        },
        {
            "name": "Medical and Educational Amenities",
            "columns": mededu_cols,
            "pdfs": [
                {
                    "filenames": ["1981_Aizawl_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 20]]}
                },
                {
                    "filenames": ["1981_Chhimtuipui_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 20]]}
                }
            ]
        },
        {
            "name": "Tehsil Appendix",
            "columns": tehsil_cols,
            "pdfs": [
                {
                    "filenames": ["1981_Aizawl_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 14], [30, 41]],
                        "page_2_columns": [[15, 29], [42, 56]]
                    }
                },
                {
                    "filenames": ["1981_Chhimtuipui_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 16], [30, 44]],
                        "page_2_columns": [[17, 29], [45, 56]]
                    }
                }
            ]
        }
    ]
}

os.makedirs('Mizoram_Formats', exist_ok=True)
with open('Mizoram_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(mizoram_data, f, sort_keys=False)
print("Mizoram generated!")
