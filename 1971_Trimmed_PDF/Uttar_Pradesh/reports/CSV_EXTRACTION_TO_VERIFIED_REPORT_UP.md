# Uttar Pradesh 1971 CSV Extraction to Resolved and Verified Stage

Date prepared: 3 September 2026

## In simple terms

The project started with trimmed PDF pages from the 1971 Uttar Pradesh district handbooks. The relevant Civic, Medical/Educational, and Tehsil tables were separated into individual PDF files, read into structured CSV files, checked for OCR mistakes, compared back to the scanned pages, and then combined into three final files.

The final merge used the five-district pilot outputs where they were available and the later `source-checked-v1` outputs for the remaining districts. Temporary regex-cleaned and provisional outputs were not used in the final merge.

## 1. Preparing the source PDFs

The PDF folder contains 157 available table PDFs covering 53 districts. The filenames identify both the district and table type, for example:

- `agra_civic_1971.pdf`
- `agra_mededu_1971.pdf`
- `agra_tehsil_1971.pdf`

Each logical table was kept traceable to its source PDF and source pages. Civic and MedEdu tables generally use an anchor page and a continuation page. Tehsil tables use the two-page appendix layout, with different groups of columns appearing in different parts of the spread.

There are no Tehsil PDFs for Mirzapur or Varanasi, so the available total is 51 Tehsil files rather than 53.

## 2. Extracting the tables into CSV

The table pages were read into three consistent table formats:

- Civic and Other Amenities (`format_001`)
- Medical, Educational, Recreational and Cultural facilities (`format_002`)
- Tahsil-wise Abstract of Educational, Medical and Other Amenities (`format_003`)

The extracted CSVs contain not only the visible values, but also the information needed to trace each value back to its source. This includes the source PDF name, PDF identifier, district, table identifier, source page range, row position, and source hashes.

The extraction also preserved special historical details such as blank values, ellipses, dashes, abbreviations, cross-reference rows, aggregate rows, and child/component rows. This was important because these are meaningful features of the original tables, not simply OCR noise.

## 3. Cleaning and structuring the extracted data

After extraction, the CSVs were post-processed to correct structural problems that OCR can create. This included:

- separating row identities from continuation-page values;
- preserving cross-reference, aggregate, and component rows;
- recalculating the relevant flags and row types;
- recomputing Civic road-length derivatives;
- applying MedEdu parent values only to the correct child rows; and
- keeping the original row order and provenance fields.

This stage produced separate per-PDF CSVs and correction logs. Automatic regex-cleaned folders were kept separate from the source-checked outputs.

## 4. Checking the values against the scans

The five-district pilot covered Aligarh, Allahabad, Almora, Azamgarh, and Bahraich. Its 15 CSVs were source-verified against 300-DPI page renders. The pilot report records 2,700 unique source cells checked, 896 correction-ledger entries, and no unresolved cells.

The remaining 142 available table PDFs were processed district by district and table by table. Their final inputs for this merge are the folders labelled `source-checked-v1`. These checks compared the extracted values with the printed source pages, including punctuation, historical codes, blanks, ellipses, page continuation alignment, table hierarchy, and cross-references.

The unresolved-cell files accompanying the source-checked inputs were also checked during consolidation. They contained no populated unresolved records; blank placeholder lines were not treated as unresolved data.

In practical terms, “resolved and verified” here means that the CSV values used in the merge came from the pilot’s source-verified outputs or from the remaining source-checked outputs, with corrections retained in the CSVs and the source/provenance fields left intact.

## 5. Creating the three final merged CSVs

The five pilot districts were taken from:

`E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed\pilot-5districts-hierarchy-v2-postprocessed-v1\csv`

All other districts were taken only from the `source-checked-v1\csv` folders under:

`E:\Archival-Digitisation-Project\1971_Trimmed_PDF\Uttar_Pradesh\outputs\postprocessed`

The PDF filenames were sorted in ascending order. Within each category, the corresponding CSV rows were appended in that same district sequence. Existing row numbers were not renumbered, and the source PDF and provenance columns were not changed. Each merged file has one header row and uses consistent CSV quoting and UTF-8 encoding.

## 6. Final results

| Final file | Input table files | Data rows | First source PDF | Last source PDF |
|---|---:|---:|---|---|
| `merged_civic_agra_to_varanasi.csv` | 53 Civic | 416 | `agra_civic_1971.pdf` | `varanasi_civic_1971.pdf` |
| `merged_mededu_agra_to_varanasi.csv` | 53 MedEdu | 1,036 | `agra_mededu_1971.pdf` | `varanasi_mededu_1971.pdf` |
| `merged_tehsils_agra_to_varanasi.csv` | 51 Tehsil | 270 | `agra_tehsil_1971.pdf` | `uttar_kashi_tehsil_1971.pdf` |

The Tehsil file correctly stops at Uttar Kashi because the source PDF set has no Varanasi Tehsil appendix.

## 7. Final checks performed

The completed merge was checked to confirm that:

- all 157 available PDFs had exactly one matching CSV input;
- the source split was correct: five pilot districts and the remaining source-checked districts;
- each category had the expected number of columns: 53 Civic, 56 MedEdu, and 119 Tehsil;
- the final row totals matched the source totals;
- each output followed the PDF filename order;
- each data row retained the correct `source_pdf` and `pdf_id`;
- no repeated header rows were inserted; and
- the source CSVs were not modified.

## Final file location

All three merged CSVs and this report are in:

`E:\Archival-Digitisation-Project\1971_Trimmed_PDF\`

The three merged files are:

- `merged_civic_agra_to_varanasi.csv`
- `merged_mededu_agra_to_varanasi.csv`
- `merged_tehsils_agra_to_varanasi.csv`

