"""Build all four native Power BI report pages from the saved semantic model.

Run with Power BI Desktop closed. Synthetic data only.
"""
from pathlib import Path
import json
import build_executive_report as ui

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'powerbi'
PAGES = PROJECT / 'Wallet.Report/definition/pages'
CHART = {
    'legend': ui.obj(show=ui.literal(False)),
    'categoryAxis': ui.obj(show=ui.literal(True), showAxisTitle=ui.literal(False), labelColor=ui.color(ui.MUTED), fontSize=ui.literal(10)),
    'valueAxis': ui.obj(show=ui.literal(True), showAxisTitle=ui.literal(False), labelColor=ui.color(ui.MUTED), fontSize=ui.literal(10)),
    'dataPoint': ui.obj(defaultColor=ui.color(ui.TEAL)),
}
TABLE = {
    'grid': ui.obj(gridVertical=ui.literal(False), gridHorizontal=ui.literal(True), gridHorizontalColor=ui.color('#E4EAF0'), rowPadding=ui.literal(7)),
    'columnHeaders': ui.obj(fontColor=ui.color(ui.MUTED), backColor=ui.color('#F6F8FA'), fontSize=ui.literal(10)),
    'values': ui.obj(fontColorPrimary=ui.color(ui.NAVY), fontSize=ui.literal(11)),
    'total': ui.obj(totals=ui.literal(True), fontColor=ui.color(ui.NAVY), backColor=ui.color('#EAF3F3')),
}


def start(page_id, title, subtitle, services=True):
    ui.VISUALS.clear()
    ui.textbox('heading', title, 28, 20, 940, 52, 25, ui.WHITE, ui.NAVY, True)
    ui.textbox('subtitle', subtitle, 28, 72, 940, 34, 12, '#B9DDE0', ui.NAVY)
    ui.textbox('scope', 'SYNTHETIC DATA  |  Oct 2025 – Sep 2026  |  AED  |  UTC', 28, 114, 940, 30, 12)
    selections = [('month', 'MONTH', 'dim_date', 'year_month', 1000)]
    if services:
        selections.append(('service', 'SERVICE', 'dim_service', 'service_name', 1294))
    for name, label, table, col, x in selections:
        ui.visual(name, 'slicer', x, 20, 278, 100, label, {'Values': [ui.projection(table, col)]}, {
            'data': ui.obj(mode=ui.literal('Dropdown')), 'header': ui.obj(show=ui.literal(False)),
            'selection': ui.obj(singleSelect=ui.literal(False), selectAllCheckboxEnabled=ui.literal(True))})
    return page_id


def cards(items):
    for i, (title, name, precision) in enumerate(items):
        ui.visual(f'card_{i}', 'card', 28+390*i, 158, 374, 116, title,
                  {'Values': [ui.measure(name)]}, {
                      'labels': ui.obj(color=ui.color(ui.TEAL if i == 2 else ui.NAVY), fontSize=ui.literal(28),
                                       labelDisplayUnits=ui.literal(1), labelPrecision=ui.literal(precision)),
                      'categoryLabels': ui.obj(show=ui.literal(False))})


def chart(name, kind, title, x, y, w, h, table, column, metric):
    v = ui.visual(name, kind, x, y, w, h, title,
                  {'Category': [ui.projection(table, column)], 'Y': [ui.measure(metric)]}, CHART)
    v['visual']['query']['sortDefinition'] = {'sort': [
        {'field': ui.field(table, column), 'direction': 'Ascending'}], 'isDefaultSort': False}
    return v


def table(name, title, x, y, w, h, columns, metrics):
    return ui.visual(name, 'tableEx', x, y, w, h, title,
                     {'Values': [ui.projection(t,c,label=label) for t,c,label in columns]
                      + [ui.measure(m,label) for m,label in metrics]}, TABLE)


def service_filter(v, values):
    v['filterConfig'] = {'filters': [{
        'name': 'ServiceScope', 'field': ui.field('dim_service', 'service_type'), 'type': 'Categorical',
        'filter': {'Version': 2, 'From': [{'Name':'s','Entity':'dim_service','Type':0}],
                   'Where': [{'Condition': {'In': {
                       'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source':'s'}}, 'Property':'service_type'}}],
                       'Values': [[{'Literal': {'Value': "'"+value+"'"}}] for value in values]}}}]}}]}


def finish(page_id, title, note):
    ui.textbox('footer', 'SYNTHETIC DATA  •  ' + note, 28, 850, 1544, 32, 11)
    page = {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json',
            'name':page_id,'displayName':title,'displayOption':'FitToPage','width':1600,'height':900,
            'objects': {'background':ui.obj(color=ui.color(ui.BG),transparency=ui.literal(0))}}
    ui.write(PAGES/page_id/'page.json',page)
    for v in ui.VISUALS:
        ui.write(PAGES/page_id/'visuals'/v['name']/'visual.json',v)


def build():
    ui.ROOT, ui.REPORT = PROJECT, PROJECT/'Wallet.Report'
    ui.PAGE = PAGES/'66d82c0d70b751fba14d'
    ui.VISUALS.clear()
    ui.build()

    page=start('operations','TRANSACTION OPERATIONS','Monitor attempts, failures, pending states and completed reversals')
    cards([('ALL ATTEMPTS','Transaction Attempts',0),('FAILED ATTEMPTS','Failed Transactions',0),
           ('PENDING AT CUTOFF','Pending Transactions',0),('COMPLETED REVERSALS','Reversal Count',0)])
    chart('failure_trend','lineChart','Failure rate by month',28,298,750,280,'dim_date','year_month','Failure Rate')
    chart('reversal_trend','clusteredColumnChart','Reversals by reversal month',802,298,770,280,'dim_date','year_month','Reversal Count')
    table('monthly_operations','Monthly operational reconciliation',28,602,1544,232,
          [('dim_date','year_month','Month')], [('Transaction Attempts','Attempts'),('Successful Transactions','Successful'),
          ('Failed Transactions','Failed'),('Pending Transactions','Pending'),('Failure Rate','Failure rate'),
          ('Reversal Count','Reversals'),('Reversed Value AED','Reversed AED')])
    finish(page,'Transaction operations','Failure rate uses all attempts. Pending is a cutoff snapshot; reversals use their own event date.')

    page=start('customers','CUSTOMER ACTIVITY & RETENTION','Both transfer senders and recipients count as active customers',False)
    cards([('ACTIVE · SELECTED PERIOD','Active Customers',0),('AVERAGE MONTHLY ACTIVE','Average Monthly Active Customers',0),
           ('LATEST SELECTED MONTH · ACTIVE','Latest Month Active Customers',0),('LATEST OBSERVABLE RETENTION','Latest Observable Retention',2)])
    chart('activity_trend','lineChart','Unique active customers by month',28,298,750,280,'dim_date','year_month','Active Customers')
    chart('retention_trend','lineChart','Next-month retention · starting month',802,298,770,280,'dim_date','year_month','Next Month Retention')
    table('retention_details','Activity retention · month M → month M+1',28,602,1544,232,
          [('dim_date','year_month','Starting month')], [('Active Customers','Active'),('Retained Next Month','Retained next month'),
          ('Not Active Next Month','Not active next month'),('Next Month Retention','Retention')])
    finish(page,'Customers','Final-month retention is blank, not zero. Latest observable retention defaults to Aug → Sep. Inactivity is not permanent churn.')

    page=start('partners','MERCHANT & AGENT PERFORMANCE','Activity volumes and wallet fees · all partners remain available for inspection',False)
    cards([('ACTIVE MERCHANTS','Active Merchants',0),('ACTIVE AGENTS','Active Agents',0),
           ('MERCHANT NET VALUE · AED','Merchant Net Value AED',2),('AGENT NET ACTIVITY · AED','Agent Net Value AED',2)])
    merchant=table('merchants','Merchant payments · scroll to inspect all merchants',28,298,750,536,
          [('dim_merchant','merchant_id','Merchant')], [('Successful Transactions','Successful'),('Failure Rate','Failure rate'),
          ('Net Value AED','Net value AED'),('Net Fee Revenue AED','Net fees AED')])
    service_filter(merchant,['merchant_payment'])
    agent=table('agents','Agent activity · cash-in and cash-out separately',802,298,770,536,
          [('dim_agent','agent_id','Agent'),('dim_service','service_type','Service')],
          [('Successful Transactions','Successful'),('Failure Rate','Failure rate'),('Net Value AED','Net value AED')])
    service_filter(agent,['cash_in','cash_out'])
    finish(page,'Merchants & agents','Net agent activity is not a cash balance. Fees are wallet revenue, not agent earnings. Costs are not modeled.')
    metadata=json.loads((PAGES/'pages.json').read_text(encoding='utf-8'))
    metadata['pageOrder']=['66d82c0d70b751fba14d','operations','customers','partners']
    metadata['activePageName']='66d82c0d70b751fba14d'
    ui.write(PAGES/'pages.json',metadata)
    print('Built four report pages. Run tests/test_report.py before opening powerbi/Wallet.pbip.')


if __name__=='__main__':
    build()
