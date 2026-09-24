import yaml
import os
import json

with open('Madhya_Pradesh_Formats/pdf_formats.yaml') as f:
    mp_data = yaml.safe_load(f)

civic_cols = next(c['columns'] for c in mp_data['categories'] if 'civic' in c['name'].lower())
mededu_cols = next(c['columns'] for c in mp_data['categories'] if 'medical' in c['name'].lower())
tehsil_cols = next(c['columns'] for c in mp_data['categories'] if 'tehsil' in c['name'].lower())

nagaland_data = {
    "state": "Nagaland",
    "categories": [
        {
            "name": "Civic Amenities",
            "columns": civic_cols,
            "pdfs": [
                {
                    "filenames": ["1981_Kohima_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 19]]}
                },
                {
                    "filenames": ["1981_Mokokchung_civic_amenities.pdf", "1981_Zunhebota_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 10]], "page_2_columns": [[11, 19]]}
                },
                {
                    "filenames": ["1981_Tuensang_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[11, 19]]}
                }
            ]
        },
        {
            "name": "Medical and Educational Amenities",
            "columns": mededu_cols,
            "pdfs": [
                {
                    "filenames": ["1981_Kohima_medical_educational_amenities.pdf", "1981_Mokokchung_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 9]], "page_2_columns": [[10, 20]]}
                },
                {
                    "filenames": ["1981_Tuensang_medical_educational_amenities.pdf", "1981_Zunhebota_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 10]], "page_2_columns": [[11, 20]]}
                }
            ]
        },
        {
            "name": "Tehsil Appendix",
            "columns": tehsil_cols,
            "pdfs": [
                {
                    "filenames": ["1981_Kohima_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 14]],
                        "page_2_columns": [[15, 31]],
                        "page_3_columns": [[1, 2], [32, 42]],
                        "page_4_columns": [[43, 56]]
                    }
                },
                {
                    "filenames": ["1981_Mokokchung_tehsil_appendix.pdf", "1981_Phek_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 16]],
                        "page_2_columns": [[17, 34]],
                        "page_3_columns": [[1, 2], [35, 44]],
                        "page_4_columns": [[45, 56]]
                    }
                },
                {
                    "filenames": ["1981_Tuensang_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 2], [35, 44]],
                        "page_2_columns": [[45, 56]]
                    }
                },
                {
                    "filenames": ["1981_Zunhebota_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 14], [28, 42]],
                        "page_2_columns": [[15, 27], [43, 56]]
                    }
                }
            ]
        }
    ]
}

os.makedirs('Nagaland_Formats', exist_ok=True)
with open('Nagaland_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(nagaland_data, f, sort_keys=False)
print("Nagaland generated!")
