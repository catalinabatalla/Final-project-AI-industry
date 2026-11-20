import json
nb = json.load(open('notebooks/01_EDA_and_Preprocessing.ipynb', encoding='utf-8'))
print(f"Total cells: {len(nb['cells'])}")
for i, c in enumerate(nb['cells']):
    src = "".join(c['source'])
    print(f"Cell {i} [{c['cell_type']}]: {repr(src[:100])}")
