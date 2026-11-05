import pytest
from autopsy.ingestion import ingest
from autopsy.models import Run
from autopsy.storage import Store

def test_ingestion():
    assert ingest('https://www.retool.com/path\nretool.com\nRetool') == ['retool.com','Retool']
    assert ingest(csv_bytes=b'domain\nretool.com\n') == ['retool.com']

@pytest.mark.parametrize('text', ['', '\n', '\n'.join('Company'+str(i) for i in range(6))])
def test_bad_input(text):
    with pytest.raises(ValueError): ingest(text)

def test_bad_csv():
    with pytest.raises(ValueError): ingest(csv_bytes=b'wrong\na\n')

def test_persistence(tmp_path):
    store=Store(tmp_path); run=Run(); store.save(run)
    assert store.runs()[0].id == run.id
