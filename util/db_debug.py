import sys
sys.path.insert(0, '.')
from util.connect import get_db

db = get_db()
coll = db['university_prices']
uni = 'Istanbul Nisantasi University'
base = 'Ameliyathane Hizmetleri'
base_doc = coll.find_one({'university_name': uni, 'department': base})
print('base_doc exists:', bool(base_doc))
if base_doc:
    print('base price_text:', repr(base_doc.get('price_text')))

variant = 'Ameliyathane Hizmetleri (Burslu)'
var_doc = coll.find_one({'university_name': uni, 'department': variant})
print('variant_doc exists:', bool(var_doc))
if var_doc:
    print('variant price_text:', repr(var_doc.get('price_text')))

cnt = coll.count_documents({'university_name': uni, 'department': {'$regex': '\\('}, 'price_text': ''})
print('variants without price_text count:', cnt)

s = coll.find_one({'university_name': uni, 'department': {'$regex': '\\('}, 'price_text': ''})
print('sample variant without price:', s and s.get('department'))
