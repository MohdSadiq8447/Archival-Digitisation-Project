import json
with open('Karnataka/1981_Karnataka_manifest.json') as f:
    manifest = json.load(f)
for item in manifest:
    if item['table'] == 'tehsil_appendix' and item['verification']:
        print(f"{item['district']}: {item['verification']['output_pages']} pages")
