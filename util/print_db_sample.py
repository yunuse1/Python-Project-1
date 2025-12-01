import json
import sys
import datetime
sys.path.insert(0, r'.')
from util.connect import get_db

def main():
    db = get_db()
    cursor = db['university_prices'].find({'university_name':'Istanbul Nisantasi University'}).sort('department',1).limit(20)
    docs = []
    for d in cursor:
        d = dict(d)
        d['_id'] = str(d.get('_id'))
        for k, v in list(d.items()):
            if isinstance(v, datetime.datetime):
                d[k] = v.isoformat()
        docs.append(d)
    print(json.dumps(docs, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
