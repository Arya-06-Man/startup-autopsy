"""Investor-owned constraints. No model may silently change a saved mandate."""
import json
import re
from pathlib import Path
from uuid import uuid4
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from autopsy.models import now


class Validated(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Holding(Validated):
    company_id: str
    sector: str
    stage: str
    amount: float = Field(ge=0)


class Mandate(Validated):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = 'Investment mandate'
    capital: float = Field(gt=0)
    currency: str = Field(default='INR', pattern=r'^[A-Z]{3}$')
    risk: Literal['Conservative', 'Moderate', 'Aggressive'] = 'Moderate'
    horizon_years: int = Field(default=5, ge=1, le=30)
    stages: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    geographies: list[str] = Field(default_factory=list)
    min_cheque: float = Field(default=0, ge=0)
    max_cheque: float = Field(default=1e8, gt=0)
    company_limit: float = Field(default=.25, gt=0, le=1)
    sector_limit: float = Field(default=.5, gt=0, le=1)
    stage_limit: float = Field(default=.75, gt=0, le=1)
    reserve_fraction: float = Field(default=.3, ge=0, le=1)
    liquidity_buffer: float = Field(default=0, ge=0)
    existing: list[Holding] = Field(default_factory=list)
    target_ownership_min: float | None = Field(default=None, ge=0, le=1)
    target_ownership_max: float | None = Field(default=None, ge=0, le=1)
    rejection_criteria: list[str] = Field(default_factory=list)
    thesis: str = ''
    provenance: str = 'USER-PROVIDED DATA'

    @model_validator(mode='after')
    def consistent(self):
        if self.min_cheque > self.max_cheque:
            raise ValueError('Minimum cheque exceeds maximum cheque')
        if self.target_ownership_min is not None and self.target_ownership_max is not None and self.target_ownership_min > self.target_ownership_max:
            raise ValueError('Ownership minimum exceeds maximum')
        if self.reserve + self.liquidity_buffer + sum(h.amount for h in self.existing) > self.capital:
            raise ValueError('Existing holdings, reserve and liquidity exceed total portfolio capital')
        return self

    @property
    def reserve(self):
        return self.capital * self.reserve_fraction

    @property
    def deployable(self):
        return max(0., self.capital - self.reserve - self.liquidity_buffer - sum(h.amount for h in self.existing))


def thesis_draft(text):
    """Conservative deterministic extraction; omissions require explicit review."""
    result = {'thesis': text}
    money = re.search(r'(?:₹|INR\s*|Rs\.?\s*)([\d,.]+)\s*(crore|lakh|million)?', text, re.I)
    if money:
        result['capital'] = float(money[1].replace(',', '')) * {'crore':1e7,'lakh':1e5,'million':1e6,None:1}[money[2].lower() if money[2] else None]
        result['currency'] = 'INR'
    horizon = re.search(r'(\d+)\s*[- ]year', text, re.I)
    if horizon: result['horizon_years'] = int(horizon[1])
    for risk in ('Conservative','Moderate','Aggressive'):
        if risk.lower() in text.lower(): result['risk'] = risk
    company = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:in\s+)?(?:any|each|per)\s+company', text, re.I)
    if company: result['company_limit'] = float(company[1])/100
    reserve = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:reserved|reserve)', text, re.I)
    if reserve: result['reserve_fraction'] = float(reserve[1])/100
    if re.search(r'\bIndian?\b', text, re.I): result['geographies'] = ['India']
    if 'b2b saas' in text.lower(): result['sectors'] = ['B2B SaaS']
    return result


class Workspace:
    def __init__(self, root='data/vcos'):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, kind, value):
        if kind not in ('mandates','snapshots','watchlists'): raise ValueError('Invalid record kind')
        record = dict(value)
        record.setdefault('id', uuid4().hex)
        record.setdefault('created_at', now())
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', record['id']): raise ValueError('Invalid record ID')
        directory = self.root / kind
        directory.mkdir(exist_ok=True)
        path = directory / (record['id']+'.json')
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(record, indent=2, allow_nan=False))
        tmp.replace(path)
        return record

    def list(self, kind):
        if kind not in ('mandates','snapshots','watchlists'): raise ValueError('Invalid record kind')
        result = []
        for path in (self.root / kind).glob('*.json'):
            try: result.append(json.loads(path.read_text()))
            except (ValueError, OSError): continue
        return sorted(result, key=lambda r:r.get('created_at',''), reverse=True)

    def mandates(self):
        result = []
        for record in self.list('mandates'):
            try: result.append(Mandate.model_validate({k:v for k,v in record.items() if k!='created_at'}))
            except ValueError: continue
        return result
