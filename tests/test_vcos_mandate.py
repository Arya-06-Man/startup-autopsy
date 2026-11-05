import json
from datetime import datetime, timezone, timedelta
import pytest
from autopsy.mandate import Mandate, Workspace, thesis_draft
from autopsy.storage import Store


def test_thesis_reviewed_constraints():
    draft=thesis_draft('I have ₹10 crore, want Indian B2B SaaS startups, moderate risk, a 5-year horizon, maximum 25% in any company, and 30% reserved for follow-on funding.')
    m=Mandate(**draft)
    assert m.capital==100000000 and m.company_limit==.25 and m.reserve_fraction==.3
    assert m.geographies==['India'] and m.sectors==['B2B SaaS']
    assert m.deployable==70000000


@pytest.mark.parametrize('changes',[{'capital':float('nan')},{'company_limit':1.1},{'min_cheque':20,'max_cheque':10},
    {'reserve_fraction':.9,'liquidity_buffer':20},{'target_ownership_min':.5,'target_ownership_max':.1},
    {'currency':'<script>'},{'unexpected':True}])
def test_mandate_rejects_invalid(changes):
    with pytest.raises(ValueError): Mandate(**({'capital':100}|changes))


def test_local_persistence_and_duplicate_holdings(tmp_path):
    m=Mandate(capital=1000,existing=[{'company_id':'synth','sector':'A','stage':'seed','amount':20}]*2)
    assert m.deployable==660
    workspace=Workspace(tmp_path)
    workspace.save('mandates',m.model_dump(mode='json'))
    assert workspace.mandates()[0]==m
    with pytest.raises(ValueError): workspace.save('snapshots',{'id':'../../secret'})
    with pytest.raises(ValueError): workspace.list('../private')


@pytest.mark.parametrize('stamp',[None,'invalid',datetime.now().isoformat(),(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()])
def test_invalid_and_future_cache_is_miss(tmp_path,stamp):
    store=Store(tmp_path)
    store.put_cache('/test',{}, {'data':{},'retrieved_at':stamp})
    assert store.cached('/test',{},24) is None


def test_stale_and_original_cache_timestamp(tmp_path):
    store=Store(tmp_path)
    timestamp=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
    store.put_cache('/test',{}, {'data':{},'retrieved_at':timestamp})
    assert store.cached('/test',{},24)['retrieved_at']==timestamp
    assert store.cached('/test',{},1) is None
