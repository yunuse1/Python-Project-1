import io
import sys
import types
import datetime
from unittest.mock import Mock, MagicMock
import pytest
import requests 

# Modülleri doğru takma adlarla (alias) import ediyoruz
import models.university_models as models_mod
import util.connect as connect_mod
import util.web_scraping as web_mod
import util.notifications as notif_mod
import util.create_prices_migration as mig_mod
import repository.repository as repo_mod
import main as main_mod

# ---------------------------
# Helpers
# ---------------------------
class DummyResponse:
    def __init__(self, content: bytes, status: int = 200):
        self._content = content
        self.status = status
        self.text = content.decode('utf-8', errors='ignore')

    def read(self):
        return self._content

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

# ---------------------------
# models/university_models.py
# ---------------------------

def test_universitydepartmentprice_composite_and_formatting():
    now = datetime.datetime.now(datetime.timezone.utc)
    u = models_mod.UniversityDepartmentPrice(
        university_name='Test Uni',
        department_name='Computer Science',
        price_amount=12345.678,
        currency_code='TRY',
        last_scraped_at=now,
    )
    assert u.get_composite_id() == 'Test Uni::Computer Science'
    formatted = u.get_formatted_price()
    assert '₺' in formatted or formatted.startswith('TRY') 
    assert '78' in formatted or '68' in formatted or '12.345' in formatted

def test_apply_discount_and_errors():
    u = models_mod.UniversityDepartmentPrice(university_name='U')
    with pytest.raises(ValueError):
        u.apply_discount(10)

    u.price_amount = 200.0
    with pytest.raises(ValueError):
        u.apply_discount(-1)
    with pytest.raises(ValueError):
        u.apply_discount(101)
    assert u.apply_discount(25) == 150.0

# ---------------------------
# util.connect.py
# ---------------------------

def test_get_client_success(monkeypatch):
    fake_client = Mock()
    fake_client.admin = Mock()
    fake_client.admin.command.return_value = {'ok': 1}

    class FakePymongo:
        def MongoClient(self, uri, serverSelectionTimeoutMS=None):
            return fake_client

    monkeypatch.setattr(connect_mod, 'pymongo', FakePymongo())

    client = connect_mod.get_client('mongodb://example:27017')
    assert client is fake_client
    fake_client.admin.command.assert_called_with('ping')

def test_get_client_failure(monkeypatch):
    fake_client = Mock()
    fake_client.admin = Mock()
    from pymongo.errors import ServerSelectionTimeoutError
    fake_client.admin.command.side_effect = ServerSelectionTimeoutError('timeout')

    class FakePymongo:
        def MongoClient(self, uri, serverSelectionTimeoutMS=None):
            return fake_client

    monkeypatch.setattr(connect_mod, 'pymongo', FakePymongo())
    with pytest.raises(ConnectionError):
        connect_mod.get_client('mongodb://bad:27017')

def test_get_db_and_collection(monkeypatch):
    monkeypatch.setattr(connect_mod, 'get_client', lambda uri=None, timeout_ms=None: {'mydatabase': 'fake-db'})
    client_obj = MagicMock()
    client_obj.__getitem__.return_value = 123
    
    res = connect_mod.get_db('customdb', client=client_obj)
    assert res == 123

# ---------------------------
# repository.repository (CRUD)
# ---------------------------

def test_repository_upsert_insert_and_update(monkeypatch):
    fake_result_insert = Mock()
    fake_result_insert.upserted_id = 'someid'
    fake_result_update = Mock()
    fake_result_update.upserted_id = None

    fake_collection = Mock()
    fake_collection.update_one.side_effect = [fake_result_insert, fake_result_update]

    fake_db = MagicMock()
    fake_db.__getitem__.return_value = fake_collection

    monkeypatch.setattr(repo_mod, 'get_db', lambda name=None: fake_db)

    repo = repo_mod.UniversityPriceRepository(database_name=None)

    ent = models_mod.UniversityDepartmentPrice(university_name='A', department_name='D')
    was_inserted, was_updated = repo.upsert(ent)
    assert was_inserted and not was_updated

    was_inserted2, was_updated2 = repo.upsert(ent)
    assert not was_inserted2 and was_updated2
    assert fake_collection.update_one.call_count == 2

def test_repository_find_get_all_delete(monkeypatch):
    doc = {
        'university_name': 'U',
        'faculty_name': 'F',
        'department_name': 'D',
        'price_description': 'p',
        'price_amount': 100.0,
        'currency_code': 'TRY',
        'last_scraped_at': datetime.datetime.now(datetime.timezone.utc)
    }
    fake_collection = Mock()
    fake_collection.find.return_value = [doc]
    fake_collection.find_one.return_value = doc
    fake_collection.delete_one.return_value = Mock(deleted_count=1)

    fake_db = MagicMock()
    fake_db.__getitem__.return_value = fake_collection
    
    monkeypatch.setattr(repo_mod, 'get_db', lambda name=None: fake_db)

    repo = repo_mod.UniversityPriceRepository()
    all_prices = repo.get_all_prices()
    assert len(all_prices) == 1
    assert isinstance(all_prices[0], models_mod.UniversityDepartmentPrice)

    found = repo.find_price_by_department('U', 'D')
    assert isinstance(found, models_mod.UniversityDepartmentPrice)

    assert repo.delete('U::D') is True
    assert repo.delete('badformat') is False

# ---------------------------
# util.web_scraping.py
# ---------------------------

def test_parse_price_from_text_varieties():
    assert web_mod.parse_price_from_text('') == (None, None)
    amt, cur = web_mod.parse_price_from_text('₺235.000,00')
    assert amt == 235000.0 and cur == 'TRY'
    
    amt2, cur2 = web_mod.parse_price_from_text('$1234.56') 
    assert round(amt2 - 1234.56, 6) == 0 and cur2 == 'USD'
    
    assert web_mod.slugify_university_name('İstanbul ÜNİVERSİTESİ ücretleri')

def make_table_html(headers, rows):
    header_html = ''.join(f'<th>{h}</th>' for h in headers)
    rows_html = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f"<html><body><table id=\"ozeluni\"><tr>{header_html}</tr>{rows_html}</table></body></html>".encode('utf-8')


def test_scrape_university_prices_calls_repo(monkeypatch):
    html = make_table_html(['Bölüm', 'Ücret'], [['Bilgisayar', '₺4.500'], ['İşletme', '₺28.000']])
    monkeypatch.setattr(web_mod.urllib.request, 'urlopen', lambda request, context=None, timeout=None: DummyResponse(html))

    fake_repo = Mock()
    fake_repo.upsert.return_value = (True, False)
    monkeypatch.setattr(web_mod, 'UniversityPriceRepository', lambda *args, **kwargs: fake_repo)

    inserted, updated = web_mod.scrape_university_prices('http://example.com/test', 'Test Uni')
    assert inserted == 2 and updated == 0
    assert fake_repo.upsert.call_count == 2

def test_scrape_university_prices_404_fallback(monkeypatch):
    html = make_table_html(['Program', 'Ücret'], [['X', '₺1.000']])

    def first_raise(request, context=None, timeout=None):
        raise web_mod.urllib.error.HTTPError(getattr(request, 'full_url', 'u'), 404, 'Not Found', hdrs=None, fp=None)

    calls = [first_raise, lambda request, context=None, timeout=None: DummyResponse(html)]
    def seq(request, context=None, timeout=None):
        return calls.pop(0)(request, context, timeout)

    monkeypatch.setattr(web_mod.urllib.request, 'urlopen', seq)
    fake_repo = Mock()
    fake_repo.upsert.return_value = (True, False)
    monkeypatch.setattr(web_mod, 'UniversityPriceRepository', lambda *args, **kwargs: fake_repo)

    inserted, updated = web_mod.scrape_university_prices('http://example.com/some-universitesi-ucretleri/')
    assert inserted == 1

# ---------------------------
# scrape_universities_from_list and send notification
# ---------------------------

def test_scrape_universities_from_list_and_notification(monkeypatch):
    monkeypatch.setitem(sys.modules, 'util.school_list', types.SimpleNamespace(universities=['A Uni','B Uni']))
    monkeypatch.setattr(web_mod, 'slugify_university_name', lambda s: s.lower().replace(' ', '-'))
    monkeypatch.setattr(web_mod, 'scrape_university_prices', lambda url, name=None: (1,0))

    called = {}
    def fake_send(topic, message, title=None, priority=3):
        called['topic'] = topic
        called['message'] = message
    monkeypatch.setattr(web_mod, 'send_scrape_notification', fake_send)

    monkeypatch.setenv('NOTIFY_TOPIC', 'testtopic')
    total, ins, upd, failed = web_mod.scrape_universities_from_list(save=True, delay=0, start_index=0, stop_index=2)
    assert total == 2
    assert called.get('topic') == 'testtopic'

# ---------------------------
# util.notifications
# ---------------------------

def test_fetch_notifications_and_send(monkeypatch):
    mock_resp = Mock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = [{'id':'1','message':'hi'}]
    
    mock_requests = MagicMock()
    mock_requests.get.return_value = mock_resp
    mock_requests.post.return_value = mock_resp
    mock_requests.exceptions.RequestException = requests.exceptions.RequestException
    
    monkeypatch.setattr(notif_mod, 'requests', mock_requests)

    out = notif_mod.fetch_notifications('topic')
    assert isinstance(out, list) and out[0]['id'] == '1'

    # send success
    mock_post_resp = Mock()
    mock_post_resp.raise_for_status.return_value = None
    mock_post_resp.status_code = 200
    mock_requests.post.return_value = mock_post_resp
    
    assert notif_mod.send_notification('t','m') is True

    # send failure
    mock_requests.post.side_effect = requests.exceptions.RequestException('fail')
    assert notif_mod.send_notification('t','m') is False

# ---------------------------
# migrations
# ---------------------------

def test_get_validator_shape():
    v = mig_mod.get_validator()
    assert '$jsonSchema' in v

def test_create_or_update_collection(monkeypatch):
    fake_db = MagicMock()
    fake_db.create_collection.side_effect = None
    fake_coll = Mock()
    fake_db.__getitem__.return_value = fake_coll
    fake_coll.create_index.return_value = None

    mig_mod.create_or_update_collection(fake_db)
    fake_db.create_collection.assert_called()
    fake_coll.create_index.assert_called()

def test_seed_example(monkeypatch):
    fake_db = MagicMock()
    fake_coll = Mock()
    fake_db.__getitem__.return_value = fake_coll
    fake_coll.insert_many.return_value = Mock(inserted_ids=[1,2])
    docs = mig_mod.seed_example(fake_db)
    assert isinstance(docs, list) and len(docs) == 2

# ---------------------------
# main.py tests
# ---------------------------

def test_normalize_turkish_text():
    assert main_mod.normalize_turkish_text('İSTANBUL') == 'istanbul'
    assert main_mod.normalize_turkish_text('') == ''

def test_export_prices_writes_csv_and_generates(monkeypatch, tmp_path):
    price = models_mod.UniversityDepartmentPrice(
        university_name='İstinye Üniversitesi',
        faculty_name='Fakulte',
        department_name='Bilgisayar',
        price_amount=10000,
        currency_code='TRY',
        last_scraped_at=datetime.datetime.now(datetime.timezone.utc)
    )
    fake_repo = Mock()
    fake_repo.get_all_prices.return_value = [price]
    
    # 1. DÜZELTME: MagicMock kullandık, böylece client['db'] hatası vermez.
    monkeypatch.setattr(connect_mod, 'get_client', MagicMock())

    # Mocklama main.py'deki kullanım için yapılıyor
    # main.py içindeki UniversityPriceRepository sınıfını, bizim sahte nesnemizi döndüren bir lambda ile değiştiriyoruz.
    monkeypatch.setattr(main_mod, 'UniversityPriceRepository', lambda *args, **kwargs: fake_repo)

    monkeypatch.setitem(sys.modules, 'util.school_list', types.SimpleNamespace(scholarship_rates=[('İstinye Üniversitesi', 20)]))

    out = tmp_path / 'out.csv'
    monkeypatch.setattr(main_mod, 'convert_to_excel', lambda a, b: None)
    monkeypatch.setattr(main_mod, 'convert_to_pdf', lambda a, b: None)

    main_mod.export_prices('İstinye Üniversitesi', 'all', 'full', True, str(out))
    assert out.exists()
    content = out.read_text(encoding='utf-8-sig')
    assert 'İstinye Üniversitesi' in content

def test_list_universities_logs(monkeypatch, capsys):
    # 1. Hazırlık: Sahte veri
    price = models_mod.UniversityDepartmentPrice(
        university_name='U1',
        department_name='Dept1',
        price_amount=100.0,
        currency_code='TRY',
        last_scraped_at=datetime.datetime.now(datetime.timezone.utc)
    )
    
    # Bu obje repo.get_all_prices() çağrıldığında dönecek liste
    mock_repo_instance = Mock()
    mock_repo_instance.get_all_prices.return_value = [price]
    
    # 2. KRİTİK ADIM: main.py içinde "UniversityPriceRepository()" çağrıldığında
    # bizim hazırladığımız "mock_repo_instance" dönsün.
    # Bu yöntem, import karmaşasını tamamen çözer.
    monkeypatch.setattr(main_mod, 'UniversityPriceRepository', lambda *args, **kwargs: mock_repo_instance)
    
    # 3. SİGORTA: Eğer bir şekilde gerçek sınıfa giderse DB hatası vermesin diye MagicMock
    monkeypatch.setattr(connect_mod, 'get_client', MagicMock())

    # 4. Çalıştır
    main_mod.list_universities()
    
    # 5. Çıktıları kontrol et
    captured = capsys.readouterr()
    output = captured.out + captured.err
    
    assert 'Universities' in output or 'Total' in output or 'U1' in output

# ---------------------------
# school_list sanity
# ---------------------------

def test_school_list_structure():
    import util.school_list as sl
    assert isinstance(sl.scholarship_rates, list)
    assert isinstance(sl.universities, list)

# ---------------------------
# Imports
# ---------------------------

def test_imports():
    import importlib
    importlib.reload(models_mod)
    importlib.reload(connect_mod)
    importlib.reload(web_mod)
    importlib.reload(notif_mod)
    importlib.reload(mig_mod)
    importlib.reload(repo_mod)
    importlib.reload(main_mod)