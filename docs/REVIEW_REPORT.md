# Review Report: 5-District Pilot Extraction (1971 UP Census)

> Run ID `pilot-5districts` · model `deepseek/deepseek-ocr-2` · 15 PDFs ·
> Districts: Aligarh, Allahabad, Almora, Azamgarh, Bahraich × {civic, mededu, tehsil}.

## 1. Headline result

**All 15 tables were QUARANTINED — 0 reached `clean`.** The deterministic geometry and
grounded row OCR largely worked (269/270 row crops produced `<|ref|>/<|det|>` boxes), but the
**transcribed cell content** was unreliable and, in the Tahsil/MedEdu formats, the model
frequently hallucinated or leaked the prompt instead of reading the faint scan. The fail-closed
design did its job: nothing wrong was emitted as clean data.

| Metric | Value |
|---|---|
| Tables processed | 15 |
| Status SUCCESS / QUARANTINED / ERROR | 0 / 15 / 0 |
| Total OCR requests (all cache-miss) | 891 |
| Requests that failed (transient retries exhausted) | 145 (16%) |
| Row crops with empty OCR text | 33 |
| Cell OCR responses rejected as prompt leakage | 213 |
| Total validation findings | 274 |
| Total flagged cells | 234 |
| Rows requiring review | 64 |

## 2. Findings by error code

| Code | Count | Meaning |
|---|---|---|
| type_parse | 175 | a transcribed value could not be parsed to its declared type |
| ambiguous_ocr | 59 | value parsed but carries a review flag (spaced digits, historic-code mismatch, etc.) |
| column_ocr_completeness | 25 | an entire column has no transcribed values |
| identity_missing | 9 | a row has blank town/tahsil identity |
| tahsil_total_sum | 4 | District Total row does not equal component sum |
| tahsil_total_presence | 2 | no District Total row was found |

## 3. Flag inventory (every flagged value)

Flag totals: `AMBIGUOUS_HISTORIC_CODE` = 3, `AMBIGUOUS_OCR` = 175, `SPACED_DIGITS` = 55, `TRAILING_MARK_REMOVED` = 1.

| Variable | Flag(s) |
|---|---|
| `auditoria` | AMBIGUOUS_OCR ×3 |
| `canal_villages` | AMBIGUOUS_OCR ×4 |
| `cinemas` | AMBIGUOUS_OCR ×11, SPACED_DIGITS ×1 |
| `college_villages` | AMBIGUOUS_OCR ×1 |
| `colleges` | AMBIGUOUS_OCR ×2 |
| `dispensaries` | SPACED_DIGITS ×1 |
| `dispensary_villages` | AMBIGUOUS_OCR ×1 |
| `engg_colleges` | AMBIGUOUS_OCR ×6 |
| `family_planning_centres` | AMBIGUOUS_OCR ×2, SPACED_DIGITS ×3 |
| `family_planning_villages` | AMBIGUOUS_OCR ×4, SPACED_DIGITS ×1 |
| `fountain_villages` | AMBIGUOUS_OCR ×5 |
| `hand_pipe_villages` | AMBIGUOUS_OCR ×3 |
| `health_centre_villages` | AMBIGUOUS_OCR ×3, SPACED_DIGITS ×1 |
| `health_centres` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×2 |
| `higher_secondary_schools` | AMBIGUOUS_OCR ×13, SPACED_DIGITS ×2 |
| `higher_secondary_villages` | AMBIGUOUS_OCR ×1 |
| `hospital_villages` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×2 |
| `junior_basic_schools` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×1 |
| `junior_basic_villages` | AMBIGUOUS_OCR ×4, SPACED_DIGITS ×1 |
| `kachcha_road_villages` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×1 |
| `lake_villages` | AMBIGUOUS_OCR ×3 |
| `mcw_centres` | SPACED_DIGITS ×1 |
| `mcw_villages` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×3 |
| `med_beds` | AMBIGUOUS_OCR ×8, SPACED_DIGITS ×5 |
| `medical_colleges` | AMBIGUOUS_OCR ×3 |
| `middle_schools` | AMBIGUOUS_OCR ×4, SPACED_DIGITS ×2 |
| `night_soil_disposal_method` | AMBIGUOUS_HISTORIC_CODE ×3 |
| `no_water_villages` | AMBIGUOUS_OCR ×4 |
| `other_edu_institutions` | AMBIGUOUS_OCR ×7 |
| `other_edu_villages` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×1 |
| `other_latrines` | SPACED_DIGITS ×1 |
| `other_med_institutions` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×2 |
| `other_med_villages` | AMBIGUOUS_OCR ×4, SPACED_DIGITS ×3 |
| `other_road_villages` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×1 |
| `other_water_villages` | AMBIGUOUS_OCR ×3, TRAILING_MARK_REMOVED ×1 |
| `polytechnics` | AMBIGUOUS_OCR ×4 |
| `post_office_villages` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×1 |
| `post_offices` | AMBIGUOUS_OCR ×2, SPACED_DIGITS ×1 |
| `post_telegraph_offices` | AMBIGUOUS_OCR ×3, SPACED_DIGITS ×1 |
| `post_telegraph_villages` | AMBIGUOUS_OCR ×2, SPACED_DIGITS ×2 |
| `power_available_villages` | AMBIGUOUS_OCR ×2 |
| `power_not_available_villages` | AMBIGUOUS_OCR ×2 |
| `primary_schools` | AMBIGUOUS_OCR ×10, SPACED_DIGITS ×2 |
| `pucca_kachcha_road_villages` | AMBIGUOUS_OCR ×2, SPACED_DIGITS ×1 |
| `pucca_road_villages` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×1 |
| `river_villages` | AMBIGUOUS_OCR ×2 |
| `senior_basic_schools` | AMBIGUOUS_OCR ×1 |
| `senior_basic_villages` | AMBIGUOUS_OCR ×1 |
| `service_latrines` | SPACED_DIGITS ×2 |
| `stadia` | AMBIGUOUS_OCR ×6 |
| `tank_villages` | AMBIGUOUS_OCR ×2, SPACED_DIGITS ×2 |
| `tap_water_villages` | AMBIGUOUS_OCR ×2 |
| `telegraph_office_villages` | AMBIGUOUS_OCR ×3, SPACED_DIGITS ×1 |
| `telegraph_offices` | AMBIGUOUS_OCR ×4, SPACED_DIGITS ×1 |
| `telephone_villages` | AMBIGUOUS_OCR ×2, SPACED_DIGITS ×1 |
| `telephones` | AMBIGUOUS_OCR ×3, SPACED_DIGITS ×1 |
| `tube_well_villages` | AMBIGUOUS_OCR ×3, SPACED_DIGITS ×1 |
| `water_borne_latrines` | AMBIGUOUS_OCR ×1, SPACED_DIGITS ×1 |
| `water_fall_villages` | AMBIGUOUS_OCR ×4 |
| `well_villages` | AMBIGUOUS_OCR ×5, SPACED_DIGITS ×1 |

## 4. Per-table results

### aligarh_civic_1971

- status **QUARANTINED** · rows 6 · valid 6 · quality 0.952 (geom 0.951, ocr 1.000, parse 1.000, semantic 0.833)
- flagged cells 0 · rows needing review 0 · audit records {'row_ocr': 12, 'raw_rows': 1}

Findings:
- `column_ocr_completeness`: Column 'water_capacity' has no transcribed values

### aligarh_mededu_1971

- status **QUARANTINED** · rows 7 · valid 3 · quality 0.940 (geom 0.969, ocr 1.000, parse 0.855, semantic 0.857)
- flagged cells 6 · rows needing review 4 · audit records {'row_ocr': 14, 'validation_cell_retry': 13, 'raw_rows': 1}

Findings:
- `type_parse`: med_beds: expected integer for '337 ... 25 ...'
- `ambiguous_ocr`: med_beds: SPACED_DIGITS for '4 6 6'
- `type_parse`: medical_colleges: expected integer for '... ... ...'
- `type_parse`: engg_colleges: expected integer for '... ... ... ... ... ...'
- `type_parse`: polytechnics: expected integer for '... ... ...'
- `type_parse` ×2: cinemas: expected integer for '... ...'
- `type_parse`: med_beds: expected integer for 'A 4 0 0'
- `type_parse`: medical_colleges: expected integer for 'Medical Colleges Field | Expected Value 1 | 0 2 | 0 3 | 0 4 | 0'
- `type_parse`: engg_colleges: expected integer for '... ... ... ...'
- `type_parse`: polytechnics: expected integer for '... ...'
- `type_parse`: med_beds: expected integer for '16 ...'

### aligarh_tehsil_1971

- status **QUARANTINED** · rows 7 · valid 0 · quality 0.680 (geom 0.967, ocr 0.714, parse 0.934, semantic 0.000)
- flagged cells 16 · rows needing review 7 · audit records {'row_ocr': 28, 'cell_fallback': 116, 'validation_cell_retry': 17, 'raw_rows': 1}

Findings:
- `type_parse`: lake_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, formulas, or tables. It is a title slide with the title "tahsil_abstract_1971" and a subtitle "panel: tahsil_power_water."'
- `type_parse` ×3: no_water_villages: expected integer for '0 | 2'
- `type_parse`: tap_water_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, formulas, or tables. It is a title slide with the title "tahsil_abstract_1971" and a subtitle "panel: tahsil_power_water."'
- `type_parse`: tank_villages: expected integer for 'I'
- `type_parse`: no_water_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, formulas, or tables. It is a table with a single row and two columns.'
- `ambiguous_ocr` ×2: other_med_villages: SPACED_DIGITS for '4 4'
- `type_parse`: tank_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, formulas, or tables. It is a table with a single row and two columns.'
- `type_parse` ×2: river_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, formulas, or tables. It is a table with a single row and two columns.'
- `type_parse`: post_telegraph_offices: expected integer for '1 ...'
- `type_parse`: family_planning_villages: expected integer for '... ...'
- `type_parse`: well_villages: expected integer for '36.4'
- `type_parse`: canal_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, formulas, or tables. It is a title slide with the title "tahsil_abstract_1971" and a description that reads "tahsil_abstract_1971".'
- `ambiguous_ocr`: health_centres: SPACED_DIGITS for '4 4'
- `type_parse`: water_fall_villages: expected integer for '0 | 1'
- `type_parse`: other_water_villages: expected integer for 'This image does not contain any data, axes, or labels that can be extracted into a table. It is a title slide with the title "Uttar Pradesh District Census Handbook" and a description of the purpose of the table.'
- `ambiguous_ocr`: junior_basic_schools: SPACED_DIGITS for '1 0 4'
- `ambiguous_ocr`: mcw_villages: SPACED_DIGITS for '5 4'
- `ambiguous_ocr`: junior_basic_villages: SPACED_DIGITS for '1 812'
- `column_ocr_completeness`: Column 'other_edu_institutions' has no transcribed values
- `column_ocr_completeness`: Column 'fountain_villages' has no transcribed values
- `column_ocr_completeness`: Column 'telegraph_offices' has no transcribed values
- `tahsil_total_presence`: Expected one district total row; found 0

### allahabad_civic_1971

- status **QUARANTINED** · rows 9 · valid 7 · quality 0.926 (geom 0.984, ocr 1.000, parse 0.987, semantic 0.667)
- flagged cells 3 · rows needing review 2 · audit records {'row_ocr': 18, 'edge_cell_refinement': 2, 'edge_value_selection': 2, 'validation_cell_retry': 1, 'raw_rows': 1}

Findings:
- `ambiguous_ocr`: night_soil_disposal_method: AMBIGUOUS_HISTORIC_CODE for 'HC | MT | B'
- `type_parse`: water_borne_latrines: expected integer for '105 ...'
- `ambiguous_ocr`: service_latrines: SPACED_DIGITS for '237 389'
- `ambiguous_ocr`: night_soil_disposal_method: AMBIGUOUS_HISTORIC_CODE for 'B B'

### allahabad_mededu_1971

- status **QUARANTINED** · rows 15 · valid 1 · quality 0.761 (geom 0.985, ocr 0.933, parse 0.661, semantic 0.200)
- flagged cells 15 · rows needing review 12 · audit records {'row_ocr': 30, 'cell_fallback': 18, 'validation_cell_retry': 52, 'raw_rows': 1}

Findings:
- `type_parse`: medical_colleges: expected integer for 'ity ity AERATION'
- `type_parse`: engg_colleges: expected integer for 'Urban Urban'
- `type_parse`: polytechnics: expected integer for 'Agglomé. Agglomé.'
- `type_parse`: primary_schools: expected integer for 'aiaadad C ahabad Ci 307'
- `type_parse`: other_edu_institutions: expected integer for 'ity Urb ity Urb 52'
- `type_parse`: cinemas: expected integer for 'Agglomeration 11'
- `identity_missing` ×5: Row identity is blank
- `ambiguous_ocr`: higher_secondary_schools: SPACED_DIGITS for '1 3 3 3'
- `ambiguous_ocr`: middle_schools: SPACED_DIGITS for '2 1 1 1'
- `ambiguous_ocr`: primary_schools: SPACED_DIGITS for '1 3 3 3'
- `ambiguous_ocr`: med_beds: SPACED_DIGITS for '100 24'
- `type_parse`: higher_secondary_schools: expected integer for 'VI See'
- `type_parse`: primary_schools: expected integer for 'habad Ci i'
- `type_parse`: other_edu_institutions: expected integer for 'Urban'
- `type_parse`: cinemas: expected integer for 'Agglomeration'
- `type_parse`: med_beds: expected integer for '... ...'
- `type_parse`: engg_colleges: expected integer for '... ...'
- `type_parse`: higher_secondary_schools: expected integer for 'BANKING'
- `type_parse`: primary_schools: expected integer for 'important commodity infra.'
- `ambiguous_ocr`: med_beds: SPACED_DIGITS for '4 4'
- `type_parse`: higher_secondary_schools: expected integer for '1st'
- `type_parse`: primary_schools: expected integer for '2nd'
- `type_parse`: other_edu_institutions: expected integer for 'No. c 3rd'
- `type_parse`: stadia: expected integer for 'of Banks Ag Cre'
- `type_parse`: cinemas: expected integer for 'No. of *ricultural* *dit Societies*'
- `type_parse`: auditoria: expected integer for 'No. of Non-Agricultur Credit Societie'
- `ambiguous_ocr`: higher_secondary_schools: SPACED_DIGITS for '15 0'
- `ambiguous_ocr`: middle_schools: SPACED_DIGITS for '2 1'
- `type_parse`: primary_schools: expected integer for 'znd 1,1'
- `type_parse`: other_edu_institutions: expected integer for '3rd ..'
- `type_parse`: stadia: expected integer for '33: 49: 65: 81: 97: 17: 5:0 34: 50: 66: 82: 98:'
- `type_parse`: cinemas: expected integer for '18: 35: 51: 67: 83: 99: 19: 6:0 36: 52: 68: 84: 100:'
- `type_parse`: auditoria: expected integer for 'Urcail Societie'
- `type_parse` ×2: higher_secondary_schools: expected integer for 'See'
- `type_parse`: middle_schools: expected integer for 'Allah: Allah is the name of the God of Islam, and the name is used to refer to the God of the Quran.'
- `type_parse`: primary_schools: expected integer for 'abad City'
- `type_parse`: other_edu_institutions: expected integer for ', y y & 0.0 Urban'
- `type_parse`: cinemas: expected integer for 'Aglomeration'
- `type_parse`: primary_schools: expected integer for 'hes Steel B₁'
- `type_parse`: engg_colleges: expected integer for 'DE, COMME'
- `type_parse` ×2: higher_secondary_schools: expected integer for 'Bidi'
- `type_parse`: middle_schools: expected integer for 'Quilt'
- `type_parse`: med_beds: expected integer for '| of three most in | im .r1'
- `type_parse`: polytechnics: expected integer for 'lost important exported'
- `type_parse`: primary_schools: expected integer for 'a Uil om Cloth Alabast'
- `type_parse`: middle_schools: expected integer for 'Allaha'
- `type_parse`: primary_schools: expected integer for 'ibad City'
- `type_parse`: other_edu_institutions: expected integer for "'"
- `type_parse`: cinemas: expected integer for "1 'gglomeratlan"

### allahabad_tehsil_1971

- status **QUARANTINED** · rows 14 · valid 0 · quality 0.685 (geom 0.953, ocr 0.821, parse 0.741, semantic 0.000)
- flagged cells 51 · rows needing review 14 · audit records {'row_ocr': 56, 'cell_fallback': 156, 'validation_cell_retry': 74, 'raw_rows': 1}

Findings:
- `type_parse`: hand_pipe_villages: expected integer for '0.00'
- `ambiguous_ocr`: dispensaries: SPACED_DIGITS for '2 2'
- `ambiguous_ocr`: family_planning_villages: SPACED_DIGITS for '1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1'
- `ambiguous_ocr`: family_planning_centres: SPACED_DIGITS for '1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1'
- `ambiguous_ocr`: other_med_villages: SPACED_DIGITS for '1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1'
- `ambiguous_ocr`: other_med_institutions: SPACED_DIGITS for '1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1'
- `type_parse`: hand_pipe_villages: expected integer for '1: Tahsil_abstract_1971. Appendix: Tahsil-wise Abstract of Educational, Medical and Other Amenities (1971). Aggregates amenity counts (Junior/Senior Basic schools, Higher Secondary, Colleges, Medical institutions & beds, Power supply, Drinking water sources like Tap/Well/Tube-well/Tank/River, Pucca/Kheragarh | Kiraoli | DISTRICT TOTAL 2: Name of Tahsil or District Total; type=integer; count of Tahsil names with power supply; possible printed forms: 1 | 2 | 3 | 4 | 5 3: No. of Villages with Power Supply; field=tahsil_power_villages; type=integer; count of villages with power supply; possible printed forms: 95 | 60 | 40 | 0 4: No. of Villages with Power Supply Not Available; field=power_not_available_villages; type=integer; count of villages with power supply; possible printed forms: 120 | 80 | 50 | 0 5: No. of Villages having Tap Water; field=tap_water_villages; type=integer; count of villages with tap water; possible printed forms: 85 | 40 | 0 6: No. of Villages having Hand Pipe; field=hand_pipe_villages; type=integer; count of villages having hand pipes / spring water; possible printed forms: 2 | 0 7: No. of Villages having Water Fall; field=water_fall_villages; type=integer; count of villages having waterfall source; possible printed forms: 0 | 1 8: No. of Villages having Tube-Well; field=tube_well_villages; type=integer; count of villages having tube-wells; possible printed forms: 65 | 30 | 0 9: No. of Villages having Other Water Source; field=other_water_villages; type=integer; count of villages having other water source; possible printed forms: 5 | 0 10: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 11: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 12: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 13: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 14: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 15: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 16: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 17: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 18: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 19: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 20: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 21: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 22: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 23: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 24: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 25: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 26: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 27: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 28: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 29: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 30: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 31: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 32: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2 33: No. of Villages with No Water Source; field=no_water_villages; type=integer; count of villages with no drinking water source; possible printed forms: 0 | 2'
- `ambiguous_ocr`: hospital_villages: SPACED_DIGITS for '7 7'
- `type_parse`: health_centre_villages: expected integer for '一'
- `type_parse`: health_centres: expected integer for '一 一'
- `type_parse`: family_planning_villages: expected integer for '一'
- `type_parse`: family_planning_centres: expected integer for '一 一'
- `type_parse`: other_med_villages: expected integer for '一'
- `type_parse`: other_med_institutions: expected integer for '一 一'
- `type_parse`: power_available_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, tables, or other visual elements. It is a title page or cover page for a census report.'
- `type_parse`: tap_water_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, axes, or labels that can be extracted into a table.'
- `ambiguous_ocr`: mcw_villages: SPACED_DIGITS for '0 0'
- `ambiguous_ocr`: health_centres: SPACED_DIGITS for '3 3'
- `ambiguous_ocr`: family_planning_centres: SPACED_DIGITS for '3 3'
- `ambiguous_ocr`: other_med_institutions: SPACED_DIGITS for '3 3'
- `type_parse` ×2: well_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, axes, or labels that can be extracted into a table.'
- `type_parse`: fountain_villages: expected integer for 'This image does not contain any data, axes, or labels that can be extracted into a table. It is a title slide with the text "Title of the presentation" and a background image. Therefore, it is not possible to create a table from this image.'
- `type_parse`: well_villages: expected integer for '3U0'
- `type_parse`: pucca_kachcha_road_villages: expected integer for 'H'
- `type_parse`: post_office_villages: expected integer for '\\[z^{-1}\\]'
- `type_parse`: post_offices: expected integer for '、 、 、 、 、 、 47 、 、'
- `type_parse` ×2: telegraph_office_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_communications. This image does not contain any data, tables, or other visual elements. It is a title page or cover page for a census report.'
- `type_parse`: telegraph_offices: expected integer for '、 、 、 、 、 、 、 、 、 、 、 、'
- `type_parse`: post_telegraph_villages: expected integer for '、 、 、 、 、 、 、 、 、 、 、 、'
- `type_parse`: post_telegraph_offices: expected integer for '、 、 、 、 、 、 、 、 、 、'
- `type_parse`: telephone_villages: expected integer for '、 、 、 、 、 、 、 、 、 、 、 、 、 、'
- `type_parse`: telephones: expected integer for '、 、 、 、 、 、 、 、 、'
- `type_parse`: health_centre_villages: expected integer for '+'
- `type_parse`: well_villages: expected integer for 'आमा'
- `type_parse` ×2: water_fall_villages: expected integer for '0 | 1'
- `type_parse`: power_available_villages: expected integer for 'U'
- `type_parse`: power_not_available_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, tables, or other visual elements. It is a title page or cover page for a census report.'
- `type_parse`: fountain_villages: expected integer for 'This image does not contain any data, axes, or labels that can be extracted into a table. It is a title slide with the text "Title Goes Here" and a background image. Therefore, it is not possible to create a table from this image.'
- `type_parse`: canal_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, formulas, or tables. It is a title slide with the title "tahsil_abstract_1971" and a subtitle "panel: tahsil_power_water."'
- `type_parse`: lake_villages: expected integer for 'This image does not contain any data, axes, or labels that can be extracted into a table. It is a title slide with the text "Title Goes Here" and a background image. Therefore, it is not possible to create a data table from this image.'
- `type_parse`: tube_well_villages: expected integer for '``` F ```'
- `ambiguous_ocr`: tank_villages: SPACED_DIGITS for '22 29'
- `type_parse`: telegraph_offices: expected integer for '一'
- `type_parse`: post_telegraph_villages: expected integer for '一'
- `type_parse`: post_telegraph_offices: expected integer for '一'
- `type_parse`: telephone_villages: expected integer for '一'
- `type_parse`: telephones: expected integer for '一'
- `type_parse`: power_not_available_villages: expected integer for '0.0 0.0'
- `type_parse`: tube_well_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data, axes, or labels that can be extracted into a table.'
- `type_parse`: other_water_villages: expected integer for '0.0 0.0 0.0 0.0'
- `type_parse`: junior_basic_villages: expected integer for 'Power { }'
- `type_parse`: higher_secondary_schools: expected integer for 'Drinking Water'
- `type_parse`: other_edu_villages: expected integer for 'ATURI'
- `type_parse`: fountain_villages: expected integer for '一'
- `type_parse`: canal_villages: expected integer for '一 一'
- `type_parse`: lake_villages: expected integer for '一'
- `identity_missing` ×3: Row identity is blank
- `type_parse`: junior_basic_villages: expected integer for 'Number of vi'
- `type_parse`: higher_secondary_schools: expected integer for 'r of villages h'
- `ambiguous_ocr`: tank_villages: SPACED_DIGITS for '09 102'
- `type_parse`: junior_basic_villages: expected integer for 'power supply is'
- `type_parse`: post_offices: expected integer for 'This image does not contain any data, axes, or labels that can be extracted into a table. It is a title slide with the text "Title" and a blank space for the title.'
- `type_parse`: hospital_villages: expected integer for 'Ful'
- `type_parse`: junior_basic_villages: expected integer for 'Available Available'
- `type_parse`: junior_basic_schools: expected integer for 'Not Availiable.'
- `type_parse`: senior_basic_villages: expected integer for 'Tap Hand Didi'
- `type_parse`: senior_basic_schools: expected integer for 'Id Well Tank Id'
- `type_parse`: higher_secondary_villages: expected integer for '| River | Foul | | --- | --- | | taij | t'
- `type_parse`: higher_secondary_schools: expected integer for 'n- Canal Wa n F'
- `type_parse`: college_villages: expected integer for '| tahsil_abstract_1971 | tahsil_education | |---|---| | atter | Lake | | all | |'
- `type_parse`: colleges: expected integer for 'Tub~ well'
- `type_parse`: other_edu_institutions: expected integer for 'Not available.'
- `type_parse`: dispensary_villages: expected integer for 'Kachna Road'
- `type_parse`: mcw_villages: expected integer for 'DAYILG Post NAR: ...'
- `type_parse`: health_centre_villages: expected integer for '| Tally | | | |---|---|---| | Telegraph | | | | | | | | | | | | | | | | | | |'
- `type_parse`: family_planning_villages: expected integer for 'Post &'
- `type_parse`: family_planning_centres: expected integer for 'Office'
- `type_parse`: other_med_villages: expected integer for '--0-- Télé- phones'
- `ambiguous_ocr`: well_villages: SPACED_DIGITS for '1,722 6'
- `ambiguous_ocr`: tube_well_villages: SPACED_DIGITS for '209 1'
- `type_parse`: kachcha_road_villages: expected integer for '0.0 47.2'
- `column_ocr_completeness`: Column 'no_water_villages' has no transcribed values

### almora_civic_1971

- status **QUARANTINED** · rows 6 · valid 5 · quality 0.856 (geom 0.963, ocr 1.000, parse 1.000, semantic 0.333)
- flagged cells 4 · rows needing review 1 · audit records {'row_ocr': 12, 'edge_cell_refinement': 2, 'edge_value_selection': 4, 'raw_rows': 1}

Findings:
- `ambiguous_ocr`: water_borne_latrines: SPACED_DIGITS for '140 10'
- `ambiguous_ocr`: service_latrines: SPACED_DIGITS for '218 58'
- `ambiguous_ocr`: other_latrines: SPACED_DIGITS for '520 6'
- `ambiguous_ocr`: night_soil_disposal_method: AMBIGUOUS_HISTORIC_CODE for 'B/HC IIL'

### almora_mededu_1971

- status **QUARANTINED** · rows 5 · valid 2 · quality 0.630 (geom 0.969, ocr 0.600, parse 0.862, semantic 0.000)
- flagged cells 7 · rows needing review 3 · audit records {'row_ocr': 10, 'cell_fallback': 24, 'validation_cell_retry': 4, 'raw_rows': 1}

Findings:
- `type_parse`: med_beds: expected integer for '0 235 ...'
- `type_parse`: middle_schools: expected integer for 'I I'
- `ambiguous_ocr`: primary_schools: SPACED_DIGITS for '15 15'
- `type_parse`: stadia: expected integer for 'Stadia: 14 | 0 | Nil | -'
- `ambiguous_ocr`: cinemas: SPACED_DIGITS for '2 2'
- `type_parse`: higher_secondary_schools: expected integer for '+ + +'
- `ambiguous_ocr`: med_beds: SPACED_DIGITS for '12 45 6'
- `column_ocr_completeness`: Column 'medical_colleges' has no transcribed values
- `column_ocr_completeness`: Column 'other_edu_institutions' has no transcribed values
- `column_ocr_completeness`: Column 'auditoria' has no transcribed values

### almora_tehsil_1971

- status **QUARANTINED** · rows 5 · valid 0 · quality 0.678 (geom 0.976, ocr 0.700, parse 0.934, semantic 0.000)
- flagged cells 13 · rows needing review 5 · audit records {'row_ocr': 20, 'cell_fallback': 72, 'validation_cell_retry': 9, 'raw_rows': 1}

Findings:
- `ambiguous_ocr`: mcw_centres: SPACED_DIGITS for '16 16'
- `type_parse`: colleges: expected integer for '... ...'
- `ambiguous_ocr`: other_water_villages: TRAILING_MARK_REMOVED for '72)'
- `type_parse`: telegraph_office_villages: expected integer for 'I'
- `type_parse` ×2: telegraph_offices: expected integer for 'I'
- `ambiguous_ocr`: health_centre_villages: SPACED_DIGITS for '10 2'
- `ambiguous_ocr`: hospital_villages: SPACED_DIGITS for '2 4'
- `type_parse`: family_planning_villages: expected integer for 'J 5'
- `ambiguous_ocr`: family_planning_centres: SPACED_DIGITS for '1 5'
- `type_parse`: pucca_road_villages: expected integer for '7.21'
- `type_parse`: telephones: expected integer for 'I'
- `type_parse`: other_med_villages: expected integer for 'tahsil_abstract_1971; panel: tahsil_medical. This image does not contain any data, charts, or graphs. It is a table with a single row and two columns.'
- `type_parse`: pucca_kachcha_road_villages: expected integer for 'PSUP (R) 32 Janganna/181—1974.—745 Books.'
- `column_ocr_completeness`: Column 'other_edu_institutions' has no transcribed values
- `column_ocr_completeness`: Column 'hand_pipe_villages' has no transcribed values
- `column_ocr_completeness`: Column 'tank_villages' has no transcribed values
- `column_ocr_completeness`: Column 'lake_villages' has no transcribed values
- `column_ocr_completeness`: Column 'tube_well_villages' has no transcribed values
- `column_ocr_completeness`: Column 'no_water_villages' has no transcribed values
- `column_ocr_completeness`: Column 'telephone_villages' has no transcribed values

### azamgarh_civic_1971

- status **QUARANTINED** · rows 1 · valid 1 · quality 0.795 (geom 0.984, ocr 1.000, parse 1.000, semantic 0.000)
- flagged cells 0 · rows needing review 0 · audit records {'row_ocr': 2, 'raw_rows': 1}

Findings:
- `column_ocr_completeness`: Column 'other_latrines' has no transcribed values
- `column_ocr_completeness`: Column 'water_capacity' has no transcribed values
- `column_ocr_completeness`: Column 'fire_service' has no transcribed values
- `column_ocr_completeness`: Column 'elec_other' has no transcribed values

### azamgarh_mededu_1971

- status **QUARANTINED** · rows 5 · valid 0 · quality 0.931 (geom 0.969, ocr 1.000, parse 0.871, semantic 0.800)
- flagged cells 6 · rows needing review 5 · audit records {'row_ocr': 10, 'validation_cell_retry': 9, 'raw_rows': 1}

Findings:
- `type_parse`: primary_schools: expected integer for '; 21'
- `type_parse` ×2: stadia: expected integer for '***'
- `type_parse`: cinemas: expected integer for '***'
- `type_parse`: auditoria: expected integer for '***'
- `ambiguous_ocr`: med_beds: SPACED_DIGITS for '12 16'
- `type_parse`: med_beds: expected integer for '10 ...'
- `type_parse`: cinemas: expected integer for '*** ***'
- `type_parse`: stadia: expected integer for '... ...'

### azamgarh_tehsil_1971

- status **QUARANTINED** · rows 7 · valid 3 · quality 0.758 (geom 0.989, ocr 0.893, parse 0.992, semantic 0.000)
- flagged cells 4 · rows needing review 3 · audit records {'row_ocr': 28, 'cell_fallback': 36, 'validation_cell_retry': 3, 'raw_rows': 1}

Findings:
- `ambiguous_ocr`: mcw_villages: SPACED_DIGITS for '3 2'
- `type_parse`: fountain_villages: expected integer for '... ...'
- `type_parse`: other_road_villages: expected integer for '3+'
- `ambiguous_ocr`: other_edu_villages: SPACED_DIGITS for '7 7'
- `column_ocr_completeness`: Column 'tap_water_villages' has no transcribed values
- `column_ocr_completeness`: Column 'no_water_villages' has no transcribed values
- `tahsil_total_sum`: District total 73 != component sum 60
- `tahsil_total_sum`: District total 25 != component sum 95
- `tahsil_total_sum`: District total 72805176 != component sum 7023274
- `tahsil_total_sum`: District total 207 != component sum 267

### bahraich_civic_1971

- status **QUARANTINED** · rows 3 · valid 3 · quality 0.862 (geom 0.984, ocr 1.000, parse 1.000, semantic 0.333)
- flagged cells 0 · rows needing review 0 · audit records {'row_ocr': 6, 'raw_rows': 1}

Findings:
- `column_ocr_completeness`: Column 'other_latrines' has no transcribed values
- `column_ocr_completeness`: Column 'elec_other' has no transcribed values

### bahraich_mededu_1971

- status **QUARANTINED** · rows 4 · valid 0 · quality 0.918 (geom 0.967, ocr 1.000, parse 0.853, semantic 0.750)
- flagged cells 4 · rows needing review 4 · audit records {'row_ocr': 8, 'validation_cell_retry': 6, 'raw_rows': 1}

Findings:
- `type_parse`: cinemas: expected integer for '... ...'
- `type_parse`: med_beds: expected integer for '18 4 ...'
- `type_parse`: engg_colleges: expected integer for '... ...'
- `type_parse`: higher_secondary_schools: expected integer for 'VI'
- `type_parse`: higher_secondary_schools: expected integer for 'AND BANKIN'
- `identity_missing`: Row identity is blank

### bahraich_tehsil_1971

- status **QUARANTINED** · rows 4 · valid 0 · quality 0.786 (geom 0.978, ocr 1.000, parse 0.951, semantic 0.000)
- flagged cells 19 · rows needing review 4 · audit records {'row_ocr': 16, 'validation_cell_retry': 7, 'raw_rows': 1}

Findings:
- `ambiguous_ocr`: post_telegraph_villages: SPACED_DIGITS for '1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1'
- `type_parse`: fountain_villages: expected integer for '... ...'
- `type_parse`: water_fall_villages: expected integer for '0 | 1'
- `type_parse`: other_water_villages: expected integer for '... ...'
- `ambiguous_ocr`: kachcha_road_villages: SPACED_DIGITS for '9 9 9 9 9 9 352'
- `ambiguous_ocr`: pucca_kachcha_road_villages: SPACED_DIGITS for '9 9 9 9 9 9 9 9 9 9 9 9 9'
- `ambiguous_ocr`: other_road_villages: SPACED_DIGITS for '9 9 9 9 9 9 9 9 9 9 9 9 9 9'
- `ambiguous_ocr`: post_office_villages: SPACED_DIGITS for '9 9 9 9 9 9'
- `ambiguous_ocr`: post_offices: SPACED_DIGITS for '9 9 9 9 9 9 9 9 9 9 9 9'
- `ambiguous_ocr`: telegraph_office_villages: SPACED_DIGITS for '9 9 9 9 9 9'
- `ambiguous_ocr`: telegraph_offices: SPACED_DIGITS for '9 9 9 9 9 9 9 9 9 9 9 9'
- `ambiguous_ocr`: post_telegraph_villages: SPACED_DIGITS for '9 9 9 9 9 9 9 9 9 9 9 9'
- `ambiguous_ocr`: post_telegraph_offices: SPACED_DIGITS for '9 9 9 9 9 9 9 9 9 9 9 9'
- `ambiguous_ocr`: telephone_villages: SPACED_DIGITS for '9 9 9 9 9 9'
- `ambiguous_ocr`: telephones: SPACED_DIGITS for '9 9 9 9 9 9 9 9 9 9 9 9'
- `type_parse`: canal_villages: expected integer for '... ...'
- `type_parse`: tube_well_villages: expected integer for '... ...'
- `type_parse`: other_med_villages: expected integer for '#'
- `type_parse`: hand_pipe_villages: expected integer for '531.1.'
- `ambiguous_ocr`: pucca_road_villages: SPACED_DIGITS for '0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0'
- `column_ocr_completeness`: Column 'other_edu_villages' has no transcribed values
- `column_ocr_completeness`: Column 'other_edu_institutions' has no transcribed values
- `tahsil_total_presence`: Expected one district total row; found 0

## 5. Issue classification

Each repeating failure is classified as **OCR-side** (model/API; fixable only by prompt/model
change or re-OCR) or **post-processing** (fixable in pipeline code without re-OCR).

### 5.1 OCR-side (model / API)

1. **Prompt / schema leakage.** The model echoes its own prompt instead of transcribing:
   - *"Medical Colleges Field | Expected Value 1 | 0 2 | 0 3 | 0 4 | 0"* — copies schema `value_examples`.
   - *"tahsil_abstract_1971; panel: tahsil_power_water. This image does not contain any data..."* —
     describes the crop as a title slide/empty image.
   - 213 cell-OCR responses were rejected by the existing leakage guard; the same behaviour leaks
     into row OCR where it is not fully filtered.
2. **Off-topic / foreign-script hallucination.** For unreadable cells the model emits unrelated
   content: *"Allah is the name of the God of Islam..."*, CJK `一` / `、`, Devanagari `आमा`,
   `\[z^{-1}\]`, ```` ```F``` ````, `***`, `+`, `#`.
3. **"Empty image" fabrication.** Many real table crops were described as *"does not contain any
   data / title slide / cover page"* — the model failed to read faint 300-dpi crops.
4. **Transient API failures.** 145 requests exhausted retries (timeout / 429 / 5xx); 33 row crops
   returned empty text. Operational, but amplified by the retry-heavy fallback path.

### 5.2 Post-processing correctable (pipeline code)

1. **Spaced digits.** Multi-digit numbers are returned as separate grounded tokens joined with
   spaces: `4 6 6`→466, `1 0 4`→104, `1 812`→1812, `1 1 1 1 …` and `9 9 9 9 …` (whole-column
   spill). **Fix:** strip spaces (or join digit tokens without separators) before integer parse.
2. **Spaced ellipsis not null.** `... ...` / `... ... ...` pass the null matcher (which only matches
   `...`). **Fix:** treat `(\.\s*){2,}` as null.
3. **Historic-code normalization.** `night_soil_disposal_method` values like `HC | MT | B`, `B B`,
   `B/HC IIL` (IIL≈HL) fail the `HC/HL/MT/WB/B/C/T` matcher. **Fix:** map `|`→`/`, collapse spaces,
   tolerate `I`↔`L`.
4. **Example-value leakage is only partly caught.** Values like `0 | 1`, `0 | 2`, `Stadia: 14 | 0 |
   Nil | -` are literal schema `value_examples` pasted back. **Fix:** reject any cell whose value
   equals the joined `possible printed forms` of its column.
5. **Missing columns from panel detection.** Civic column 10 (`water_capacity`) is not matched in
   the continuation panel (`matched_numbers = 9,11,12,…`), and edge columns `elec_other`,
   `fire_service`, `other_latrines` come back empty → `column_ocr_completeness`. **Fix:** strengthen
   printed-number detection / interpolate the missing `10` centre.
6. **Anchor row under-segmentation.** `azamgarh_civic` segmented 1 row (anchor body only ~133 px tall
   vs 662 px on the continuation) and `bahraich_civic` 3 rows. **Fix:** review body-boundary + ink-band
   row detection on faint anchors.
7. **Wrong-region reads on MedEdu page 2.** `allahabad_mededu` data columns filled with a *different*
   table's text (`BANKING`, `No. of Agricultural Credit Societies`, `Steel/Cloth/Alabast`, `1st/2nd/3rd`).
   Row crops are landing on adjacent directory text. **Fix:** tighten continuation-panel alignment.
8. **Tahsil District-Total row.** 2 tables found no `DISTRICT TOTAL` row; 4 found one whose sums are
   wildly wrong (e.g. `72805176 != 7023274`) — the total row caught non-table text. **Fix:** total-row
   detection + numeric sanity bound.
9. **Blank identities.** 9 rows (mostly `allahabad_mededu` urban-agglomeration components) have empty
   `town_name`. **Fix:** anchor-identity recovery for component/`See` rows.

### 5.3 Tooling bugs (pipeline CLI)

1. **UnicodeEncodeError crash.** `cli._print_summary` crashed with `charmap/cp1252` on CJK output
   (`\u4e00`), aborting the post-run summary print (data was already written). **Fix:** set
   `PYTHONIOENCODING=utf-8` / reconfigure stdout.
2. **Cumulative `cache_metrics`.** Per-PDF `hits/misses` are cumulative on the shared client, so they
   over-report (misleading). **Fix:** snapshot deltas per PDF.

## 6. Repeating patterns (ranked)

| # | Pattern | Scope | Class |
|---|---|---|---|
| 1 | Spaced digits from split grounded tokens | all formats, 55+ cells | post-processing |
| 2 | Prompt/schema leakage & "empty image" hallucination | mededu + tehsil (dense pages) | OCR |
| 3 | Spaced ellipsis leaking into integer parse | mededu + tehsil | post-processing |
| 4 | Missing civic col 10 / edge columns | civic | post-processing (geometry) |
| 5 | Foreign-script / symbol hallucination on faint cells | tehsil mainly | OCR |
| 6 | Tahsil District-Total row wrong/missing | tehsil | post-processing |
| 7 | Anchor row under-segmentation | azamgarh/bahraich civic | post-processing (geometry) |
| 8 | Transient API failures (16% of requests) | all | OCR/operational |

## 7. Recommendation

Fix the cheap post-processing items first (spaced-digit join, ellipsis, historic-code, example-value
rejection, missing-column interpolation, total-row sanity) — these account for most `type_parse` and
`ambiguous_ocr` findings. Then address the OCR-side hallucination by re-prompting the dense mededu/tehsil
crops (smaller per-column crops up front rather than whole-row grounding) and adding a "transcribe or say
empty" constraint plus a stricter leakage guard. Re-run before scaling to the full 157-PDF batch.
