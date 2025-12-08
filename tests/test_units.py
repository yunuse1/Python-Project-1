import io
import sys
import types
import datetime
from unittest.mock import Mock, MagicMock
import pytest
import requests 

import models.university_models as models_mod
import util.connect as connect_mod
import util.web_scraping as web_mod
import util.notifications as notif_mod
import util.create_prices_migration as mig_mod
import repository.repository as repo_mod
import main as main_mod

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

def test_slugify_university_name():
    result = web_mod.slugify_university_name('İstanbul Üniversitesi ücretleri')
    assert result
    assert 'istanbul' in result.lower()
    assert 'ü' not in result
    assert 'İ' not in result


def test_scrape_universities_from_list_returns_tuple(monkeypatch):
    monkeypatch.setitem(sys.modules, 'util.school_list', types.SimpleNamespace(universities=[]))
    
    result = web_mod.scrape_universities_from_list(save=True, delay=0, start_index=0, stop_index=0)
    assert isinstance(result, tuple)
    assert len(result) == 4


def test_send_scrape_notification(monkeypatch):
    called = {}
    
    def mock_send(topic, message, title=None, priority=3):
        called['topic'] = topic
        called['message'] = message
        return True
    
    monkeypatch.setattr(notif_mod, 'send_notification', mock_send)
    
    web_mod.send_scrape_notification('test-topic', 'test message', title='Test')
    assert called.get('topic') == 'test-topic'
    assert called.get('message') == 'test message'


def test_send_scrape_notification_empty_topic():
    web_mod.send_scrape_notification('', 'message')
    web_mod.send_scrape_notification(None, 'message')

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

    mock_post_resp = Mock()
    mock_post_resp.raise_for_status.return_value = None
    mock_post_resp.status_code = 200
    mock_requests.post.return_value = mock_post_resp
    
    assert notif_mod.send_notification('t','m') is True

    mock_requests.post.side_effect = requests.exceptions.RequestException('fail')
    assert notif_mod.send_notification('t','m') is False

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

def test_normalize_turkish_text():
    assert main_mod.normalize_turkish_text('İSTANBUL') == 'istanbul'
    assert main_mod.normalize_turkish_text('') == ''

def test_export_prices_writes_excel_and_pdf(monkeypatch, tmp_path):
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

    monkeypatch.setattr(connect_mod, 'get_client', MagicMock())
    monkeypatch.setattr(main_mod, 'UniversityPriceRepository', lambda *args, **kwargs: fake_repo)
    monkeypatch.setitem(
        sys.modules,
        'util.school_list',
        types.SimpleNamespace(scholarship_rates=[('İstinye Üniversitesi', 20)])
    )

    excel_created = {'called': False}
    pdf_created = {'called': False}

    def mock_excel(df, path):
        excel_created['called'] = True
        excel_created['path'] = path
        excel_created['df'] = df

    def mock_pdf(df, path):
        pdf_created['called'] = True
        pdf_created['path'] = path

    monkeypatch.setattr(main_mod, 'convert_to_excel', mock_excel)
    monkeypatch.setattr(main_mod, 'convert_to_pdf', mock_pdf)

    out = tmp_path / 'out'
    main_mod.export_prices('İstinye Üniversitesi', 'all', 'full', True, str(out))

    assert excel_created['called']
    assert pdf_created['called']
    assert 'İstinye Üniversitesi' in excel_created['df']['University'].values

def test_list_universities_logs(monkeypatch, caplog):
    import logging
    
    price = models_mod.UniversityDepartmentPrice(
        university_name='U1',
        department_name='Dept1',
        price_amount=100.0,
        currency_code='TRY',
        last_scraped_at=datetime.datetime.now(datetime.timezone.utc)
    )
    
    mock_repo_instance = Mock()
    mock_repo_instance.get_all_prices.return_value = [price]
    
    monkeypatch.setattr(main_mod, 'UniversityPriceRepository', lambda *args, **kwargs: mock_repo_instance)
    
    monkeypatch.setattr(connect_mod, 'get_client', MagicMock())

    with caplog.at_level(logging.INFO):
        main_mod.list_universities()
    
    log_output = caplog.text
    assert 'U1' in log_output or 'Total' in log_output or 'universities' in log_output.lower()

def test_school_list_structure():
    import util.school_list as sl
    assert isinstance(sl.scholarship_rates, list)
    assert isinstance(sl.universities, list)

def test_imports():
    import importlib
    importlib.reload(models_mod)
    importlib.reload(connect_mod)
    importlib.reload(web_mod)
    importlib.reload(notif_mod)
    importlib.reload(mig_mod)
    importlib.reload(repo_mod)
    importlib.reload(main_mod)