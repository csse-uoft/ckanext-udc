import json
with open('examples/maturity_model_v0.3.json') as f:
    data = json.load(f)
import pandas as pd
res = []
for mm in data:
    title = mm['title']
    name = mm['name']
    for field in mm['fields']:
        category = field.get('category')
        if 'ckanField' in field.keys():
            fname = field['ckanField']
            flabel = fname
        else:
            fname = field['name']
            flabel = field['label']
        sdesc = field.get('short_description')
        ldesc = field.get('long_description')

        res.append([title, name, category, flabel, sdesc, ldesc])
df = pd.DataFrame(res, columns=['mm_title', 'mm_name', 'category', 'flabel', 'sdesc', 'ldesc'])
df.to_csv('examples/maturity_model_v0.3.csv', index=False)
