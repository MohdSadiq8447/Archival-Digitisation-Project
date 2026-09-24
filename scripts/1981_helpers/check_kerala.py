import json
with open('Kerala/1981_Kerala_manifest.json') as f:
    manifest = json.load(f)
for item in manifest:
    if item['verification']:
        print(f"{item['table']} - {item['district']}: {item['verification']['output_pages']} pages")
