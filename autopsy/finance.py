"""Deterministic ordinary-equity math. Inputs are supplied, never inferred."""
from typing import Literal
from datetime import date
from pydantic import Field, model_validator
from autopsy.mandate import Validated


class Deal(Validated):
    company_id: str
    name: str
    currency: str = 'INR'
    sector: str = ''
    stage: str = ''
    geography: str = ''
    investment: float = Field(ge=0)
    valuation: float = Field(gt=0)
    valuation_basis: Literal['pre-money','post-money'] = 'pre-money'
    round_size: float | None = Field(default=None, gt=0)
    instrument: Literal['Ordinary equity','Preferred shares','SAFE','Convertible note'] = 'Ordinary equity'
    cash: float | None = Field(default=None, ge=0)
    monthly_burn: float | None = Field(default=None, gt=0)
    revenue: float | None = Field(default=None, ge=0)
    prior_revenue: float | None = Field(default=None, gt=0)
    gross_profit: float | None = None
    operating_profit: float | None = None
    financial_date: date | None = None
    documents: list[str] = Field(default_factory=list)
    rejection_reviewed: bool = False
    human_review_confirmed: bool = False
    downside_moic: float | None = Field(default=None, ge=0)
    base_moic: float | None = Field(default=None, ge=0)
    upside_moic: float | None = Field(default=None, ge=0)
    provenance: Literal['USER-PROVIDED DATA','SYNTHETIC DEMO DATA'] = 'USER-PROVIDED DATA'

    @model_validator(mode='after')
    def terms(self):
        if self.round_size is not None and self.round_size < self.investment:
            raise ValueError('Round size must include proposed investment')
        if self.valuation_basis=='post-money' and self.valuation <= (self.round_size or self.investment):
            raise ValueError('Post-money must exceed new financing')
        if self.financial_date and self.financial_date > date.today():
            raise ValueError('Financial as-of date cannot be in the future')
        if all(v is not None for v in (self.downside_moic,self.base_moic,self.upside_moic)) and not self.downside_moic<=self.base_moic<=self.upside_moic:
            raise ValueError('Scenario labels require downside MOIC <= base MOIC <= upside MOIC')
        return self


def deal_metrics(deal):
    supported = deal.instrument=='Ordinary equity'
    round_total = deal.round_size if deal.round_size is not None else deal.investment
    post = deal.valuation + round_total if deal.valuation_basis=='pre-money' else deal.valuation
    return {
        'post_money':post if supported else None,
        'ownership':deal.investment/post if supported else None,
        'valuation_revenue_multiple':post/deal.revenue if supported and deal.revenue else None,
        'runway_months':deal.cash/deal.monthly_burn if deal.cash is not None and deal.monthly_burn else None,
        'revenue_growth':deal.revenue/deal.prior_revenue-1 if deal.revenue and deal.prior_revenue else None,
        'gross_margin':deal.gross_profit/deal.revenue if deal.gross_profit is not None and deal.revenue else None,
        'operating_margin':deal.operating_profit/deal.revenue if deal.operating_profit is not None and deal.revenue else None,
        'assumptions':['USER-PROVIDED DATA; financials unverified.',
                       'Unknown round size assumes investor is the only new capital; confirm before approval.' if deal.round_size is None else 'Supplied round size includes investor cheque.',
                       'Ordinary equity only; no preferences, fees, taxes, option pool or convertibles in entry math.' if supported else 'Instrument requires legal conversion/payout terms; ordinary-equity calculations withheld.']}


def readiness(mandate, deal, dossier=None):
    outside, missing, warnings = [], [], []
    for label, allowed, actual in [('sector',mandate.sectors,deal.sector),('stage',mandate.stages,deal.stage),('geography',mandate.geographies,deal.geography)]:
        if not actual: missing.append(f'Confirm {label}')
        elif allowed and actual.casefold() not in [s.casefold() for s in allowed]: outside.append(f'{label} outside mandate')
    if deal.currency != mandate.currency: outside.append('Currency differs; no implicit FX conversion')
    if not mandate.min_cheque <= deal.investment <= mandate.max_cheque: outside.append('Cheque outside limits')
    existing = sum(h.amount for h in mandate.existing if h.company_id==deal.company_id)
    if existing+deal.investment > mandate.capital*mandate.company_limit: outside.append('Company concentration limit')
    for category, limit in [('sector',mandate.sector_limit),('stage',mandate.stage_limit)]:
        exposure=sum(h.amount for h in mandate.existing if getattr(h,category)==getattr(deal,category))
        if exposure+deal.investment > mandate.capital*limit: outside.append(category+' concentration limit')
    if deal.investment > mandate.deployable: outside.append('Insufficient deployable capital after reserve')
    if not deal.investment: missing.append('Positive proposed investment')
    if not deal.round_size: missing.append('Confirmed total round size')
    if deal.instrument!='Ordinary equity': missing.append('Legal instrument conversion and payout model')
    if any(v is None for v in (deal.cash,deal.monthly_burn,deal.revenue,deal.financial_date)):
        missing.append('Dated cash, burn and annual revenue')
    elif (date.today()-deal.financial_date).days>120: missing.append('Refresh financial statements older than 120 days')
    for doc in ('Financial statements','Cap table','Term sheet'):
        if doc not in deal.documents: missing.append(doc)
    if mandate.rejection_criteria and not deal.rejection_reviewed: missing.append('Review custom hard rejection criteria')
    ownership=deal_metrics(deal)['ownership']
    if ownership is not None:
        if mandate.target_ownership_min is not None and ownership < mandate.target_ownership_min: missing.append('Ownership below target; review terms')
        if mandate.target_ownership_max is not None and ownership > mandate.target_ownership_max: missing.append('Ownership above target; review terms')
    if not dossier or not dossier.evidence: missing.append('External company evidence')
    elif dossier.company_id != deal.company_id: raise ValueError('Dossier identity does not match deal')
    else:
        if any(e.conflicts for e in dossier.evidence): missing.append('Reconcile contradictory evidence')
        if dossier.status!='complete': missing.append('Resolve incomplete investigation')
        if dossier.assessment.missing: warnings.extend(dossier.assessment.missing)
    status = 'OUTSIDE MANDATE' if outside else 'MORE DILIGENCE REQUIRED' if missing else 'READY FOR COMMITTEE REVIEW' if deal.human_review_confirmed else 'CONDITIONALLY REVIEWABLE'
    return {'status':status,'violations':outside,'missing':missing,'coverage_warnings':warnings,
            'approval_condition':'Human verification of supplied documents and approval-critical facts is required. Document labels are attestations, not document verification.'}


class Scenario(Validated):
    cash: float = Field(ge=0)
    monthly_burn: float = Field(ge=0)
    years: Literal[1,3,5,7,10] = 5
    burn_reduction: float = Field(default=0, ge=0, le=1)
    implementation_cost: float = Field(default=0, ge=0)
    monthly_revenue: float = Field(default=0, ge=0)
    monthly_revenue_growth: float = Field(default=0, ge=-1, le=1)
    financing: float = Field(default=0, ge=0)
    financing_month: int = Field(default=1, ge=1, le=120)
    ownership: float = Field(default=0, ge=0, le=1)
    dilution: float = Field(default=0, ge=0, le=1)
    exit_value: float = Field(default=0, ge=0)
    invested: float = Field(default=0, ge=0)


def simulate(scenario):
    """Burn is current NET burn. Revenue changes adjust that baseline, not double count it.
    Cost change is a user-assumed reduction of net burn from month one.
    Financing arrives at START of month, only if company survived earlier months.
    Exhaustion at month end is absorbing; external rescue is not assumed.
    """
    s=scenario
    cash=s.cash-s.implementation_cost
    exhaustion=0 if cash<=0 else None
    funded=False
    trajectory=[{'month':0,'cash':round(cash,2)}]
    for month in range(1,12*s.years+1):
        if exhaustion is not None: break
        if month==s.financing_month and s.financing>0:
            cash+=s.financing; funded=True
        revenue_delta=s.monthly_revenue*((1+s.monthly_revenue_growth)**(month-1)-1)
        cash-=s.monthly_burn*(1-s.burn_reduction)-revenue_delta
        trajectory.append({'month':month,'cash':round(cash,2)})
        if cash<=0: exhaustion=month
    ownership=s.ownership*(1-s.dilution) if funded else s.ownership
    proceeds=0 if exhaustion is not None else ownership*s.exit_value
    moic=proceeds/s.invested if s.invested else None
    return {'baseline_runway_months':s.cash/s.monthly_burn if s.monthly_burn else None,
            'cash_exhaustion_month':exhaustion,'financing_received':funded,'ending_ownership':ownership,
            'exit_proceeds':proceeds,'moic':moic,'annualized_return':moic**(1/s.years)-1 if moic is not None else None,
            'trajectory':trajectory,'assumptions':s.model_dump(),
            'limitations':'MODELED ASSUMPTIONS, not a forecast. Revenue change passes fully to net cash flow; fixed baseline net burn. Exhaustion implies zero recovery. Ordinary equity, no preferences, fees or taxes.'}


def financing_round(ownership, pre_money, financing, follow_on=0., option_pool_fraction=0.):
    if not all(__import__('math').isfinite(v) for v in (ownership,pre_money,financing,follow_on,option_pool_fraction)):
        raise ValueError('Inputs must be finite')
    if not 0<=ownership<=1 or pre_money<=0 or financing<0 or not 0<=follow_on<=financing or not 0<=option_pool_fraction<1:
        raise ValueError('Invalid ordinary-equity financing inputs')
    # Pool is new post-financing ownership, diluting all equity holders.
    after=(ownership*pre_money+follow_on)/(pre_money+financing)*(1-option_pool_fraction)
    pro_rata=ownership*financing
    required=ownership*((pre_money+financing)/(1-option_pool_fraction)-pre_money)
    return {'ownership_before':ownership,'ownership_after':after,'dilution_points':ownership-after,
            'pro_rata_capital_before_pool':pro_rata,'capital_to_maintain_after_pool':required,
            'maintain_feasible':required<=financing,
            'limitations':'Ordinary equity only. New pool issued after financing. No SAFEs, notes, liquidation preferences, participation rights, fees or taxes.'}
