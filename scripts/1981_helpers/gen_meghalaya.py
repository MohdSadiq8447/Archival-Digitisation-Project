import yaml
import json

# MP columns
mp_columns = [
    {"number": 1, "name": "Sl. No.", "variable_name": "sl_no"},
    {"number": 2, "name": "Name of Taluk", "variable_name": "taluk_name"},
    {"number": 3, "name": "EDUCATIONAL - Primary school - Villages", "variable_name": "educational_primary_school_villages"},
    {"number": 4, "name": "EDUCATIONAL - Primary school - Institutions", "variable_name": "educational_primary_school_institutions"},
    {"number": 5, "name": "EDUCATIONAL - Middle school - Villages", "variable_name": "educational_middle_school_villages"},
    {"number": 6, "name": "EDUCATIONAL - Middle school - Institutions", "variable_name": "educational_middle_school_institutions"},
    {"number": 7, "name": "EDUCATIONAL - Matriculation/ secondary school - Villages", "variable_name": "educational_matriculation_secondary_school_villages"},
    {"number": 8, "name": "EDUCATIONAL - Matriculation/ secondary school - Institutions", "variable_name": "educational_matriculation_secondary_school_institutions"},
    {"number": 9, "name": "EDUCATIONAL - Higher Secondary/PUC/ Intermediate/ Junior College - Villages", "variable_name": "educational_higher_secondary_puc_intermediate_junior_college_villages"},
    {"number": 10, "name": "EDUCATIONAL - Higher Secondary/PUC/ Intermediate/ Junior College - Institutions", "variable_name": "educational_higher_secondary_puc_intermediate_junior_college_institutions"},
    {"number": 11, "name": "EDUCATIONAL - College (graduate and above) - Villages", "variable_name": "educational_college_graduate_and_above_villages"},
    {"number": 12, "name": "EDUCATIONAL - College (graduate and above) - Institutions", "variable_name": "educational_college_graduate_and_above_institutions"},
    {"number": 13, "name": "EDUCATIONAL - Adult literacy classes/centres - Villages", "variable_name": "educational_adult_literacy_classes_centres_villages"},
    {"number": 14, "name": "EDUCATIONAL - Adult literacy classes/centres - Institutions", "variable_name": "educational_adult_literacy_classes_centres_institutions"},
    {"number": 15, "name": "EDUCATIONAL - Others - Villages", "variable_name": "educational_others_villages"},
    {"number": 16, "name": "EDUCATIONAL - Others - Institutions", "variable_name": "educational_others_institutions"},
    {"number": 17, "name": "EDUCATIONAL - Villages with no educational facilities", "variable_name": "educational_villages_with_no_educational_facilities"},
    {"number": 18, "name": "MEDICAL - Dispensary - Villages", "variable_name": "medical_dispensary_villages"},
    {"number": 19, "name": "MEDICAL - Dispensary - Institutions", "variable_name": "medical_dispensary_institutions"},
    {"number": 20, "name": "MEDICAL - Hospital - Villages", "variable_name": "medical_hospital_villages"},
    {"number": 21, "name": "MEDICAL - Hospital - Institutions", "variable_name": "medical_hospital_institutions"},
    {"number": 22, "name": "MEDICAL - Maternity and Child Welfare centre/Maternity home/Child Welfare Centre - Villages", "variable_name": "medical_maternity_and_child_welfare_centre_maternity_home_child_welfare_centre_villages"},
    {"number": 23, "name": "MEDICAL - Maternity and Child Welfare centre/Maternity home/Child Welfare Centre - Institutions", "variable_name": "medical_maternity_and_child_welfare_centre_maternity_home_child_welfare_centre_institutions"},
    {"number": 24, "name": "MEDICAL - Primary Health Centre/Health Centre - Villages", "variable_name": "medical_primary_health_centre_health_centre_villages"},
    {"number": 25, "name": "MEDICAL - Primary Health Centre/Health Centre - Institutions", "variable_name": "medical_primary_health_centre_health_centre_institutions"},
    {"number": 26, "name": "MEDICAL - Family Planning Centre - Villages", "variable_name": "medical_family_planning_centre_villages"},
    {"number": 27, "name": "MEDICAL - Family Planning Centre - Institutions", "variable_name": "medical_family_planning_centre_institutions"},
    {"number": 28, "name": "MEDICAL - Primary Health Sub-centre - Villages", "variable_name": "medical_primary_health_sub_centre_villages"},
    {"number": 29, "name": "MEDICAL - Primary Health Sub-centre - Institutions", "variable_name": "medical_primary_health_sub_centre_institutions"},
    {"number": 30, "name": "MEDICAL - Community Health Worker - Villages", "variable_name": "medical_community_health_worker_villages"},
    {"number": 31, "name": "MEDICAL - Community Health Worker - Numbers", "variable_name": "medical_community_health_worker_numbers"},
    {"number": 32, "name": "MEDICAL - Others - Villages", "variable_name": "medical_others_villages"},
    {"number": 33, "name": "MEDICAL - Others - Institutions", "variable_name": "medical_others_institutions"},
    {"number": 34, "name": "MEDICAL - Villages with no medical facility", "variable_name": "medical_villages_with_no_medical_facility"},
    {"number": 35, "name": "DRINKING WATER - Tap", "variable_name": "drinking_water_tap"},
    {"number": 36, "name": "DRINKING WATER - Well", "variable_name": "drinking_water_well"},
    {"number": 37, "name": "DRINKING WATER - Tank", "variable_name": "drinking_water_tank"},
    {"number": 38, "name": "DRINKING WATER - Tube-well", "variable_name": "drinking_water_tube_well"},
    {"number": 39, "name": "DRINKING WATER - River", "variable_name": "drinking_water_river"},
    {"number": 40, "name": "DRINKING WATER - Fountain", "variable_name": "drinking_water_fountain"},
    {"number": 41, "name": "DRINKING WATER - Canal", "variable_name": "drinking_water_canal"},
    {"number": 42, "name": "DRINKING WATER - Others", "variable_name": "drinking_water_others"},
    {"number": 43, "name": "DRINKING WATER - More than one source", "variable_name": "drinking_water_more_than_one_source"},
    {"number": 44, "name": "DRINKING WATER - Villages with no drinking water facility of any type", "variable_name": "drinking_water_villages_with_no_drinking_water_facility_of_any_type"},
    {"number": 45, "name": "POST AND TELEGRAPH - P.O.", "variable_name": "post_and_telegraph_po"},
    {"number": 46, "name": "POST AND TELEGRAPH - T.O.", "variable_name": "post_and_telegraph_to"},
    {"number": 47, "name": "POST AND TELEGRAPH - P.T.O.", "variable_name": "post_and_telegraph_pto"},
    {"number": 48, "name": "POST AND TELEGRAPH - P.O. & Phone", "variable_name": "post_and_telegraph_po_phone"},
    {"number": 49, "name": "POST AND TELEGRAPH - T.O. & Phone", "variable_name": "post_and_telegraph_to_phone"},
    {"number": 50, "name": "POST AND TELEGRAPH - P.T.O. & Phone", "variable_name": "post_and_telegraph_pto_phone"},
    {"number": 51, "name": "POST AND TELEGRAPH - Phone", "variable_name": "post_and_telegraph_phone"},
    {"number": 52, "name": "COMMUNICATIONS - Bus Stop", "variable_name": "communications_bus_stop"},
    {"number": 53, "name": "COMMUNICATIONS - Railway Station", "variable_name": "communications_railway_station"},
    {"number": 54, "name": "COMMUNICATIONS - Navigable waterway", "variable_name": "communications_navigable_waterway"},
    {"number": 55, "name": "POWER SUPPLY - Available", "variable_name": "power_supply_available"},
    {"number": 56, "name": "POWER SUPPLY - Not available", "variable_name": "power_supply_not_available"}
]

civic_cols = [
    {"number": 1, "name": "Sl. No.", "variable_name": "sl_no"},
    {"number": 2, "name": "Class and Name of Town", "variable_name": "class_and_name_of_town"},
    {"number": 3, "name": "Civic Administration Status", "variable_name": "civic_administration_status"},
    {"number": 4, "name": "Population", "variable_name": "population"},
    {"number": 5, "name": "Scheduled Castes Population", "variable_name": "scheduled_castes_population"},
    {"number": 6, "name": "Scheduled Tribes Population", "variable_name": "scheduled_tribes_population"},
    {"number": 7, "name": "Receipts - Taxes", "variable_name": "receipts_taxes"},
    {"number": 8, "name": "Receipts - All other sources", "variable_name": "receipts_all_other_sources"},
    {"number": 9, "name": "Receipts - Total", "variable_name": "receipts_total"},
    {"number": 10, "name": "Expenditure - General Administration", "variable_name": "expenditure_general_administration"},
    {"number": 11, "name": "Expenditure - Public Safety", "variable_name": "expenditure_public_safety"},
    {"number": 12, "name": "Expenditure - Public Health and Conveniences", "variable_name": "expenditure_public_health_and_conveniences"},
    {"number": 13, "name": "Expenditure - Public Works", "variable_name": "expenditure_public_works"},
    {"number": 14, "name": "Expenditure - Public Institutions", "variable_name": "expenditure_public_institutions"},
    {"number": 15, "name": "Expenditure - Others", "variable_name": "expenditure_others"},
    {"number": 16, "name": "Expenditure - Total", "variable_name": "expenditure_total"}
]

mededu_cols = [
    {"number": 1, "name": "Sl. No.", "variable_name": "sl_no"},
    {"number": 2, "name": "Class and Name of Town", "variable_name": "class_and_name_of_town"},
    {"number": 3, "name": "Population", "variable_name": "population"},
    {"number": 4, "name": "Hospitals/Dispensaries/T.B. Clinics etc.", "variable_name": "hospitals_dispensaries_tb_clinics_etc"},
    {"number": 5, "name": "Beds in Medical institutions", "variable_name": "beds_in_medical_institutions"},
    {"number": 6, "name": "Arts/Science/Commerce Colleges", "variable_name": "arts_science_commerce_colleges"},
    {"number": 7, "name": "Medical Colleges", "variable_name": "medical_colleges"},
    {"number": 8, "name": "Engineering Colleges", "variable_name": "engineering_colleges"},
    {"number": 9, "name": "Polytechnics", "variable_name": "polytechnics"},
    {"number": 10, "name": "Recognised Shorthand, Type-Writing and Vocational Training Institutions", "variable_name": "recognised_shorthand_type_writing_and_vocational_training_institutions"},
    {"number": 11, "name": "Higher Secondary/Intermediate/PUC/Junior College", "variable_name": "higher_secondary_intermediate_puc_junior_college"},
    {"number": 12, "name": "Matriculation/Secondary", "variable_name": "matriculation_secondary"},
    {"number": 13, "name": "Junior Secondary and Middle Schools", "variable_name": "junior_secondary_and_middle_schools"},
    {"number": 14, "name": "Primary Schools", "variable_name": "primary_schools"},
    {"number": 15, "name": "Adult Literacy Classes/Centres, Others", "variable_name": "adult_literacy_classes_centres_others"},
    {"number": 16, "name": "Working Women's Hostels with No. of Seats", "variable_name": "working_womens_hostels_with_no_of_seats"},
    {"number": 17, "name": "Stadia", "variable_name": "stadia"},
    {"number": 18, "name": "Cinema", "variable_name": "cinema"},
    {"number": 19, "name": "Auditoria/Drama/Community Halls", "variable_name": "auditoria_drama_community_halls"},
    {"number": 20, "name": "Public Libraries including Reading Rooms", "variable_name": "public_libraries_including_reading_rooms"}
]

data = {
    "state": "Meghalaya",
    "categories": [
        {
            "name": "Civic Amenities",
            "columns": civic_cols,
            "pdfs": [
                {
                    "filenames": ["1981_East Garo Hills_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 10], [11, 19]]}
                },
                {
                    "filenames": ["1981_Jaintia Khasi Hills_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 10], [11, 19]]}
                },
                {
                    "filenames": ["1981_West Garo Hills_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 19]]}
                },
                {
                    "filenames": ["1981_West Khasi Hills_civic_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 10], [11, 19]]}
                }
            ]
        },
        {
            "name": "Medical and Educational Amenities",
            "columns": mededu_cols,
            "pdfs": [
                {
                    "filenames": ["1981_East Garo Hills_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 10], [11, 20]]}
                },
                {
                    "filenames": ["1981_Jaintia Khasi Hills_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 8], [9, 15], [16, 20]]}
                },
                {
                    "filenames": ["1981_West Garo Hills_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 20]]}
                },
                {
                    "filenames": ["1981_West Khasi Hills_medical_educational_amenities.pdf"],
                    "pagination": {"page_1_columns": [[1, 5], [6, 15], [16, 20]]}
                }
            ]
        },
        {
            "name": "Tehsil Appendix",
            "columns": mp_columns,
            "pdfs": [
                {
                    "filenames": ["1981_East Garo Hills_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 12], [13, 23]],
                        "page_2_columns": [[24, 36], [37, 46], [47, 56]]
                    }
                },
                {
                    "filenames": ["1981_Jaintia Khasi Hills_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 17], [18, 34]],
                        "page_2_columns": [[35, 51], [52, 56]]
                    }
                },
                {
                    "filenames": ["1981_West Garo Hills_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 12]],
                        "page_2_columns": [[13, 23]],
                        "page_3_columns": [[24, 36]],
                        "page_4_columns": [[35, 44]],
                        "page_5_columns": [[42, 56]]
                    }
                },
                {
                    "filenames": ["1981_West Khasi Hills_tehsil_appendix.pdf"],
                    "pagination": {
                        "page_1_columns": [[1, 17], [18, 34]],
                        "page_2_columns": [[35, 44], [45, 56]]
                    }
                }
            ]
        }
    ]
}

import os
os.makedirs('Meghalaya_Formats', exist_ok=True)
with open('Meghalaya_Formats/pdf_formats.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)
print('Done!')
