import json
from pathlib import Path
import pandas as pd
w=pd.ExcelFile('data/korail_voc_routing_master.xlsx')
for name in w.sheet_names:
 d=pd.read_excel(w,sheet_name=name); print(name,len(d))
print(pd.read_excel(w,sheet_name='channel_master').to_dict('records'))
