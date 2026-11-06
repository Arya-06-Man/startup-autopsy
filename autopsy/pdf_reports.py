"""Native, printable A4 reports from the same validated data as HTML/Markdown."""
from io import BytesIO
from pathlib import Path
from html import escape
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.graphics.shapes import Drawing,Line,String
from autopsy.vcos_reports import validate
from autopsy.evidence import safe_url
from autopsy.models import now

INK=colors.HexColor('#17283d'); MUTED=colors.HexColor('#53657b'); ACCENT=colors.HexColor('#217c71')
RULE=colors.HexColor('#dce3eb'); PALE=colors.HexColor('#f1f5f8')


def register_fonts():
    if 'VCOS' in pdfmetrics.getRegisteredFontNames(): return
    import reportlab
    bundled=Path(reportlab.__file__).parent/'fonts'
    normal=next((Path(p) for p in [os.getenv('PDF_FONT_PATH',''),'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',str(bundled/'Vera.ttf')] if p and Path(p).is_file()))
    bold=next((Path(p) for p in [os.getenv('PDF_FONT_BOLD_PATH',''),'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',str(bundled/'VeraBd.ttf')] if p and Path(p).is_file()))
    pdfmetrics.registerFont(TTFont('VCOS',str(normal)))
    pdfmetrics.registerFont(TTFont('VCOS-Bold',str(bold)))
    pdfmetrics.registerFontFamily('VCOS',normal='VCOS',bold='VCOS-Bold',italic='VCOS',boldItalic='VCOS-Bold')


class Report:
    def __init__(self,title,created,subtitle):
        register_fonts()
        self.title=title; self.created=created; self.subtitle=subtitle; self.generated_at=now()
        self.width=A4[0]-36*mm; self.story=[]; self.character_fallback=False
        self.styles={
            'body':ParagraphStyle('body',fontName='VCOS',fontSize=9,leading=13,textColor=INK,spaceAfter=7,splitLongWords=True),
            'small':ParagraphStyle('small',fontName='VCOS',fontSize=7.2,leading=10,textColor=MUTED,spaceAfter=4,splitLongWords=True),
            'title':ParagraphStyle('title',fontName='VCOS-Bold',fontSize=25,leading=31,textColor=INK,spaceAfter=13,splitLongWords=True),
            'h1':ParagraphStyle('h1',fontName='VCOS-Bold',fontSize=14,leading=19,textColor=ACCENT,spaceBefore=15,spaceAfter=8,keepWithNext=True),
            'h2':ParagraphStyle('h2',fontName='VCOS-Bold',fontSize=10,leading=14,textColor=INK,spaceBefore=8,spaceAfter=6,keepWithNext=True),
            'cell':ParagraphStyle('cell',fontName='VCOS',fontSize=8,leading=11,textColor=INK,splitLongWords=True),
            'head':ParagraphStyle('head',fontName='VCOS-Bold',fontSize=8,leading=11,textColor=INK,splitLongWords=True)}

    def text(self,value,font='VCOS'):
        text=str(value if value is not None else 'Unknown')
        for old,new in [('—','-'),('–','-'),('‑','-'),('→',' -> '),('₹','INR '),('×','x'),('\u00a0',' ')]: text=text.replace(old,new)
        glyphs=pdfmetrics.getFont(font).face.charToGlyph
        result=[]
        for char in text:
            if char in '\n\t' or ord(char) in glyphs: result.append(char)
            else: result.append(f'[U+{ord(char):04X}]'); self.character_fallback=True
        return escape(''.join(result)).replace('\n','<br/>')

    def para(self,value,style='body'):
        self.story.append(Paragraph(self.text(value,'VCOS-Bold' if style in ('title','h1','h2') else 'VCOS'),self.styles[style]))

    def section(self,title): self.para(title,'h1')

    def bullets(self,items):
        for item in items: self.para('- '+str(item))

    def table(self,headers,rows,widths=None):
        if not rows: self.para('No supplied data available.','small'); return
        widths=[self.width*w/sum(widths) for w in widths] if widths else [self.width/len(headers)]*len(headers)
        data=[[Paragraph(self.text(v,'VCOS-Bold'),self.styles['head']) for v in headers]]
        data += [[Paragraph(self.text(value),self.styles['cell']) for value in row] for row in rows]
        table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1,splitInRow=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LINEBELOW',(0,0),(-1,0),.6,RULE),('LINEBELOW',(0,1),(-1,-1),.35,RULE),
            ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        self.story.extend([table,Spacer(1,7)])

    def link(self,label,url):
        if safe_url(url):
            markup='<link href="'+escape(url,quote=True)+'" color="#217c71">'+self.text(label)+'</link>'
            self.story.append(Paragraph(markup,self.styles['small']))
        else: self.para(label+' · source link unavailable','small')

    def cover(self,companies,source_mode):
        self.para('STARTUP AUTOPSY VCOS','small')
        self.story.append(Spacer(1,24*mm))
        self.para(self.title,'title')
        self.para(self.subtitle)
        self.para('Companies covered','h2')
        self.bullets(companies)
        self.story.append(Spacer(1,10*mm))
        self.table(['Report context','Value'],[['PDF generated',self.generated_at],['Analysis / source date',self.created],['Source mode',source_mode]],[1,2])
        self.para('Decision support for human review. No investment execution or founder outreach. Financial inputs and scenarios retain their stated provenance.','small')
        self.story.append(PageBreak())

    def cash_chart(self,outcomes,currency):
        trajectory=outcomes.get('Base',{}).get('trajectory',[])
        if len(trajectory)<2: return
        drawing=Drawing(self.width,150)
        left,right,bottom,top=48,self.width-12,27,126
        values=[float(p['cash']) for p in trajectory]
        lo=min(0,min(values)); hi=max(values)
        if hi==lo: return
        x_max=max(p['month'] for p in trajectory) or 1
        drawing.add(Line(left,bottom,right,bottom,strokeColor=RULE))
        drawing.add(Line(left,bottom,left,top,strokeColor=RULE))
        for fraction in (0,.5,1):
            value=lo+(hi-lo)*fraction; y=bottom+(top-bottom)*fraction
            drawing.add(Line(left,y,right,y,strokeColor=RULE,strokeWidth=.3))
            drawing.add(String(0,y-2,f'{value/1e6:g}m',fontName='VCOS',fontSize=7,fillColor=MUTED))
        points=[(left+(right-left)*p['month']/x_max,bottom+(top-bottom)*(p['cash']-lo)/(hi-lo)) for p in trajectory]
        for first,second in zip(points,points[1:]): drawing.add(Line(*first,*second,strokeColor=ACCENT,strokeWidth=1.6))
        drawing.add(String(left,9,'Month 0',fontName='VCOS',fontSize=7,fillColor=MUTED))
        drawing.add(String(right-55,9,f'Month {x_max}',fontName='VCOS',fontSize=7,fillColor=MUTED))
        drawing.add(String(left,139,'Modeled base cash path ('+currency+', millions)',fontName='VCOS',fontSize=8,fillColor=INK))
        self.story.append(drawing)

    def operating_chart(self,series,model='Dated linear regression',alpha=.35,horizon=30):
        from autopsy.decision_insights import project
        result=project(series,model,alpha,horizon)
        points=result['observed']
        if len(points)<2:
            self.para('Historical operating chart unavailable: fewer than two dated observations.','small'); return
        from datetime import date
        sets=[(points,ACCENT,False),(result['fitted'],MUTED,False)]
        if result['projection']: sets.append(([points[-1],result['projection']],colors.HexColor('#b77820'),True))
        start=date.fromisoformat(points[0]['date']);end=date.fromisoformat(result['projection']['date'] if result['projection'] else points[-1]['date'])
        values=[p['value'] for rows,_,_ in sets for p in rows];lo=min(values);hi=max(values)
        chart=Drawing(self.width,150);left,right,bottom,top=42,self.width-15,30,120
        chart.add(Line(left,bottom,right,bottom,strokeColor=RULE))
        def xy(p):return left+(right-left)*(date.fromisoformat(p['date'])-start).days/max(1,(end-start).days),bottom+(top-bottom)*(p['value']-lo)/max(1,hi-lo)
        for rows,color,dashed in sets:
            for a,b in zip(rows,rows[1:]):
                line=Line(*xy(a),*xy(b),strokeColor=color,strokeWidth=1.4)
                if dashed:line.strokeDashArray=[4,3]
                chart.add(line)
        for label,y in [(f'{lo:,.0f}',bottom),(f'{hi:,.0f}',top)]:chart.add(String(0,y,label,fontName='VCOS',fontSize=7,fillColor=MUTED))
        chart.add(String(left,12,start.isoformat(),fontName='VCOS',fontSize=7));chart.add(String(right-70,12,end.isoformat(),fontName='VCOS',fontSize=7))
        chart.add(String(left,137,'Observed: teal | Fit: gray | Estimate: dashed amber',fontName='VCOS',fontSize=7,fillColor=MUTED))
        self.story.append(chart)
        self.para(model+'; '+('holdout MAE '+number(result['backtest_mae']) if result['backtest_mae'] is not None else 'Insufficient history for forecasting or holdout validation.')+' '+result['limitation'],'small')

    def build(self):
        if self.character_fallback:
            self.para('Font coverage note: unsupported characters are shown as Unicode code points. The JSON export preserves original text. Configure PDF_FONT_PATH for additional script coverage.','small')
        stream=BytesIO()
        doc=SimpleDocTemplate(stream,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,
            topMargin=24*mm,bottomMargin=20*mm,title=self.title,author='Startup Autopsy VCOS',pageCompression=1)
        def chrome(canvas,doc):
            canvas.saveState(); w,h=A4
            canvas.setStrokeColor(RULE); canvas.setLineWidth(.5)
            canvas.line(18*mm,h-17*mm,w-18*mm,h-17*mm)
            canvas.setFont('VCOS-Bold',8); canvas.setFillColor(INK)
            canvas.drawString(18*mm,h-12*mm,'STARTUP AUTOPSY VCOS')
            canvas.setFont('VCOS',7); canvas.setFillColor(MUTED)
            canvas.drawRightString(w-18*mm,h-12*mm,'PRIVATE INVESTMENT RESEARCH')
            canvas.line(18*mm,14*mm,w-18*mm,14*mm)
            canvas.drawString(18*mm,10*mm,'Source-aware decision support | Human approval required')
            canvas.drawRightString(w-18*mm,10*mm,f'Page {doc.page}')
            canvas.restoreState()
        doc.build(self.story,onFirstPage=chrome,onLaterPages=chrome)
        return stream.getvalue()


def number(value,currency=None,percent=False):
    if value is None: return 'Unknown'
    if percent: return f'{value:.2%}'
    return (currency+' ' if currency else '')+f'{value:,.2f}'


def committee_pdf(context,committee=None):
    validate(context,committee)
    m=context['mandate']; deals=context['deals']; currency=m['currency']
    modes=sorted({v.get('data_mode','Unknown / legacy') for k,v in context['references'].items() if not k.startswith('A-')})
    report=Report('Investment Committee Report',context['created_at'],m['name'])
    report.cover([d['terms']['name'] for d in deals],', '.join(modes) or 'No external evidence')
    report.section('Executive summary')
    allocation=context.get('allocation'); total=sum(allocation['allocations'].values()) if allocation else None
    report.para('No allocation computed.' if total is None else 'Conditional proposed deployment: '+number(total,currency)+'. '+('Current inputs support no new investment.' if total==0 else 'Subject to human diligence and approval.'))
    report.para(context.get('validation_disclosure','Financial figures reflect supplied data or modeled assumptions, not independently verified financial statements.'))
    report.table(['Company','Decision readiness'],[[d['terms']['name'],d['readiness']['status']] for d in deals],[1,2])
    report.table(['Executive decision summary','Value'],[['Mandate capital',number(m['capital'],currency)],
        ['Follow-on reserve',number(m['capital']*m['reserve_fraction'],currency)],
        ['Conditional allocation',number(total,currency) if total is not None else 'Not computed'],
        ['Decision',('No investment allocated' if total==0 else 'Conditional review' if total else 'Further diligence required')],
        ['Evidence limitation','Company financial statements remain unknown unless supplied; modeled terms retain their stated provenance.']],[1,2])
    report.story.append(PageBreak())
    report.section('Investment mandate')
    report.table(['Constraint','Reviewed input'],[['Total portfolio capital',number(m['capital'],currency)],['Risk / horizon',m['risk']+' / '+str(m['horizon_years'])+' years'],
        ['Follow-on reserve',number(m['capital']*m['reserve_fraction'],currency)],['Company / sector / stage limits',f'{m["company_limit"]:.0%} / {m["sector_limit"]:.0%} / {m["stage_limit"]:.0%}'],
        ['Cheque limits',number(m['min_cheque'],currency)+' to '+number(m['max_cheque'],currency)],
        ['Preferences','Sectors: '+(', '.join(m['sectors']) or 'Open')+'; Stages: '+(', '.join(m['stages']) or 'Open')+'; Geography: '+(', '.join(m['geographies']) or 'Open')],
        ['Hard rejection criteria','; '.join(m['rejection_criteria']) or 'None supplied']],[1,2])
    report.section('Company comparison and valuation')
    for d in deals:
        terms=d['terms']; metrics=d['metrics']; dossier=context.get('dossiers',{}).get(terms['company_id'],{})
        report.para(terms['name'],'h2')
        report.para(f'Canonical ID: {terms["company_id"]}; domain: {dossier.get("domain") or "not supplied"}; inputs: {terms["provenance"]}.','small')
        report.table(['Metric','Supplied or computed value'],[['Instrument',terms['instrument']],['Proposed cheque',number(terms['investment'],currency)],['Supplied valuation ('+terms['valuation_basis']+')',number(terms['valuation'],currency)],['Round size',number(terms['round_size'],currency)],
            ['Post-money valuation',number(metrics['post_money'],currency)],['Implied ownership',number(metrics['ownership'],percent=True)],
            ['Annual revenue',number(terms['revenue'],currency)],['Valuation / annual revenue',number(metrics['valuation_revenue_multiple'])],
            ['Cash / monthly net burn',number(terms['cash'],currency)+' / '+number(terms['monthly_burn'],currency)],
            ['Baseline runway (months)',number(metrics['runway_months'])],['Gross / operating margin',number(metrics['gross_margin'],percent=True)+' / '+number(metrics['operating_margin'],percent=True)],
            ['Financial as-of',terms['financial_date'] or 'Unknown']],[1,2])
        report.bullets(metrics['assumptions'])
        from autopsy.company_intelligence import report_rows
        from autopsy.models import Dossier
        if dossier:
            report.para('Company intelligence and operating momentum','h2')
            from autopsy.company_intelligence import analyze
            from autopsy.decision_insights import investor_fit
            from autopsy.mandate import Mandate
            from autopsy.finance import Deal
            intelligence=analyze(Dossier.model_validate(dossier))
            fit=investor_fit(Mandate.model_validate(m),Deal.model_validate(terms),Dossier.model_validate(dossier))
            report.para('Investor fit: '+fit['status']+'; investment readiness: '+fit['readiness'])
            report.bullets(fit['reasons'][:5])
            settings=context.get('operating_model_settings',{})
            for category in ('workforce','hiring'):
                report.para(category.title()+' historical operating chart','h2')
                report.operating_chart(intelligence[category],**settings)
            report.table(['Indicator','Observed / derived value','Evidence references'],report_rows(Dossier.model_validate(dossier)),[1,1.3,1.2])
            report.para('Dated provider observations and historical statistics. Sparse history suppresses forecasts. Funding is historical, never current cash. No return or profitability prediction.','small')
        report.para('Operating evidence','h2')
        signals=dossier.get('assessment',{}).get('signals',[])
        if signals:
            for signal in signals: report.para(signal['explanation']+' ['+', '.join(signal['evidence_ids'])+']')
        else: report.para('Comparable dated operating trends unavailable. Missing evidence is not evidence of safety.')
        report.para('Risk, uncertainty and approval conditions','h2')
        report.bullets(d['readiness']['violations']+d['readiness']['missing']+d['readiness'].get('coverage_warnings',[]))
        report.para(d['readiness']['approval_condition'],'small')
    report.section('Portfolio allocation and diversification')
    if allocation:
        report.para(allocation['reason'])
        names={d['terms']['company_id']:d['terms']['name'] for d in deals}
        report.table(['Company / capital bucket','Conditional amount'],[[names.get(cid,cid),number(value,currency)] for cid,value in allocation['allocations'].items()]+
            [['Uninvested deployment capital',number(allocation['uninvested'],currency)],['Follow-on reserve',number(allocation['reserve'],currency)]],[2,1])
        report.table(['Exposure type','Category','Capital at cost'],[[kind,key or 'Unspecified',number(value,currency)] for kind,field in [('Sector','sector_exposure'),('Stage','stage_exposure')] for key,value in allocation.get(field,{}).items()],[1,1.4,1.3])
        report.para(allocation['assumptions'],'small')
        report.bullets(allocation.get('violations',[]))
    else: report.para('No allocation computed. No investment recommendation is implied.')
    report.section('War Room scenarios')
    outcomes=context.get('war_room')
    if outcomes:
        report.para(context.get('war_room_scope','User-modeled assumptions, not verified company forecasts.'))
        report.table(['Scenario','Exhaustion month','Exit proceeds','MOIC','Annualized'],[[name,
            str(out['cash_exhaustion_month']) if out['cash_exhaustion_month'] is not None else 'Survives horizon',
            number(out['exit_proceeds'],currency),number(out['moic']),number(out['annualized_return'],percent=True)] for name,out in outcomes.items()],[1.2,1,1.4,.6,.9])
        report.cash_chart(outcomes,currency)
        if 'Base' in outcomes:
            report.para('Base scenario assumptions','h2')
            report.table(['Input','Modeled value'],list(outcomes['Base']['assumptions'].items()),[1,2])
            report.para(outcomes['Base']['limitations'],'small')
    else: report.para('No scenario assumptions supplied.')
    report.section('Investment committee perspectives')
    if committee:
        report.para('Generation engine: '+committee['engine'])
        report.para(committee['disclosure'],'small')
        for role in committee['perspectives']:
            report.para(role['role']+' - '+role['engine'],'h2')
            report.bullets([a['claim']+' ['+', '.join(a['references'])+']' for a in role['thesis']+role['challenges']])
            report.bullets(['Diligence question: '+q for q in role['questions']])
        report.bullets(committee.get('diagnostics',[]))
    else: report.para('Committee challenge has not been generated. Readiness and calculations above remain deterministic.')
    report.section('Recommended next actions')
    report.bullets(['Resolve listed mandate violations and approval-critical missing records.','Verify company-owned financial statements and legal terms.','Recompute after changing evidence, terms, assumptions or constraints.','Obtain human approval before deploying capital. No transaction or outreach is executed.'])
    report.section('Sources, attribution and limitations')
    report.para('Crustdata records are single-source observations unless explicitly labeled otherwise. Source observation, event, publication, provider update and retrieval dates are distinct. AI arguments are hypotheses, not verified findings. No failure probabilities or validated predictive forecasts are claimed.')
    report.para('Cash exhaustion is absorbing under the simplified model. Ordinary-equity payouts exclude preferences, fees and taxes. Full raw values remain in the companion JSON export.','small')
    report.story.append(PageBreak()); report.section('Appendix - evidence and source register')
    cited={ref for d in context.get('dossiers',{}).values() for signal in d.get('assessment',{}).get('signals',[]) for ref in signal['evidence_ids']}
    for d in context.get('dossiers',{}).values():
        identities=[e['id'] for e in d.get('evidence',[]) if e['category']=='identity']
        cited.update(identities[:1])
        cited.update(e['id'] for e in d.get('evidence',[]) if e['status']=='disputed/conflicting')
    if committee:
        cited.update(ref for role in committee['perspectives'] for claim in role['thesis']+role['challenges'] for ref in claim['references'])
    cited.update(ref for ref in context['references'] if ref.startswith('A-'))
    report.para(f'This register contains {len(cited)} cited, identity and conflicting records. The companion JSON preserves the complete {len(context["references"])}-record reference ledger and original observations.','small')
    for ref,value in context['references'].items():
        if ref not in cited: continue
        if ref.startswith('A-'):
            report.para(ref+' - '+value['type'],'h2'); report.para('Supplied investment terms and assumptions; see the comparison and companion JSON.','small'); continue
        report.para(ref+' - '+str(value.get('fact','Source observation')),'h2')
        report.para('Status: '+str(value['type'])+'; source mode: '+str(value.get('data_mode','Unknown')),'small')
        report.para('Observed: '+str(value.get('observed') or 'unknown')+'; event: '+str(value.get('event') or 'unknown')+
            '; published: '+str(value.get('published') or 'unknown')+'; provider update: '+str(value.get('provider_updated') or 'unknown')+
            '; retrieved: '+str(value.get('retrieved') or 'unknown'),'small')
        report.link(str(value.get('source') or 'Source unavailable'),value.get('source') or '')
    return report.build()


def investigation_pdf(run):
    from autopsy.reports import validate as validate_run,DISCLAIMER
    validate_run(run)
    report=Report('Company Research Briefing',run.created_at,'Investigation '+run.id+' - '+run.status.upper())
    report.cover([d.name or d.query for d in run.companies],run.mode)
    report.section('Executive summary'); report.para(DISCLAIMER)
    report.table(['Company','Execution','Trend coverage','Assessment'],[[d.name or d.query,d.status,f'{d.assessment.coverage:g}%',d.assessment.label] for d in run.companies],[1.4,1,.7,1.3])
    for d in run.companies:
        report.section(d.name or d.query)
        report.para('Domain: '+(d.domain or 'unknown')+'; canonical ID: '+(d.company_id or 'unresolved'),'small')
        report.para(d.metadata.get('description') or 'Business-model description unavailable.')
        report.para('Operating findings','h2')
        if not d.assessment.signals: report.para('No comparable dated trend established.')
        for signal in d.assessment.signals:
            report.para(signal.explanation+' ['+', '.join(signal.evidence_ids)+']')
            report.para('Alternative explanations: '+'; '.join(signal.alternatives),'small')
        report.para('Unknowns and required diligence','h2'); report.bullets(d.errors+d.assessment.missing)
        report.bullets(d.advice.get('next_steps',[])); report.bullets(d.advice.get('questions',[]))
        report.para('Financial inputs','h2'); report.para('Company financial statements, cash and monthly burn have not been inferred from workforce or funding observations.')
    report.story.append(PageBreak()); report.section('Appendix - original source register')
    for d in run.companies:
        report.para(d.name or d.query,'h2')
        cited={ref for signal in d.assessment.signals for ref in signal.evidence_ids}
        cited.update(e.id for e in d.evidence if e.status=='disputed/conflicting')
        cited.update(e.id for e in d.evidence if e.category=='identity')
        report.para(f'Cited, identity and conflicting records below. All {len(d.evidence)} original observations remain in the JSON ledger.','small')
        for e in d.evidence:
            if e.id not in cited: continue
            report.para(e.id+' - '+e.fact,'h2')
            report.para(f'{e.status}; observed {e.observation_date or "unknown"}; event {e.event_date or "unknown"}; published {e.publication_date or "unknown"}; provider update {e.provider_updated_at or "unknown"}; retrieved {e.retrieved_at}; {e.data_mode}','small')
            report.link(e.source,e.source)
    return report.build()
