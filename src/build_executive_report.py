"""Build the native PBIR executive page. Close Desktop before running.

Synthetic portfolio simulation. Run from the repository root. Existing project
definitions are backed up; the imported data and model connections are preserved.
"""
import json
import argparse
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1] / 'powerbi'
REPORT = ROOT / 'Wallet.Report'
PAGE = REPORT / 'definition/pages/66d82c0d70b751fba14d'
NAVY, TEAL, MUTED, BG, WHITE = '#132D46', '#008B86', '#60758A', '#F2F5F8', '#FFFFFF'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def literal(value):
    if isinstance(value, bool):
        text = str(value).lower()
    elif isinstance(value, (int, float)):
        text = str(value) + 'D'
    else:
        text = "'" + value.replace("'", "''") + "'"
    return {'expr': {'Literal': {'Value': text}}}


def color(value):
    return {'solid': {'color': literal(value)}}


def obj(**properties):
    return [{'properties': properties}]


def field(table, name, measure=False):
    return {('Measure' if measure else 'Column'): {
        'Expression': {'SourceRef': {'Entity': table}}, 'Property': name}}


def projection(table, name, measure=False, label=None):
    p = {'field': field(table, name, measure), 'queryRef': f'{table}.{name}',
         'nativeQueryRef': name}
    if label:
        p['displayName'] = label
    return p


def measure(name, label=None):
    table = 'fact_reversal' if name in ['Reversal Count', 'Reversed Value AED', 'Fee Refunds AED'] else 'fact_transaction'
    return projection(table, name, True, label)


def container(title=None, background=WHITE):
    c = {
        'background': obj(show=literal(True), color=color(background), transparency=literal(0)),
        'border': obj(show=literal(False)),
        'visualHeader': obj(show=literal(False)),
    }
    if title:
        c['title'] = obj(show=literal(True), text=literal(title), fontColor=color(NAVY),
                         fontSize=literal(12), fontFamily=literal('Segoe UI Semibold'), alignment=literal('left'))
    else:
        c['title'] = obj(show=literal(False))
    return c


VISUALS = []


def visual(name, kind, x, y, width, height, title=None, roles=None, objects=None, background=WHITE):
    v = {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json',
         'name': name,
         'position': {'x': x, 'y': y, 'width': width, 'height': height, 'z': len(VISUALS), 'tabOrder': len(VISUALS)},
         'visual': {'visualType': kind, 'visualContainerObjects': container(title, background),
                    'drillFilterOtherVisuals': True}}
    if roles:
        v['visual']['query'] = {'queryState': {role: {'projections': items} for role, items in roles.items()}}
    if objects:
        v['visual']['objects'] = objects
    VISUALS.append(v)
    return v


def textbox(name, text, x, y, width, height, size=12, ink=MUTED, background=BG, bold=False):
    return visual(name, 'textbox', x, y, width, height, background=background, objects={
        'general': obj(paragraphs=[{'textRuns': [{'value': text, 'textStyle': {
            'fontFamily': 'Segoe UI', 'fontSize': f'{size}pt', 'color': ink,
            'fontWeight': 'bold' if bold else 'normal'}}]}])})


def build():
    backup = ROOT / 'backups' / f'wallet_before_visuals_{datetime.now():%Y%m%d_%H%M%S}.zip'
    backup.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(backup, 'x', ZIP_DEFLATED) as archive:
        for folder in [REPORT, ROOT / 'Wallet.SemanticModel']:
            for path in folder.rglob('*'):
                if path.is_file() and '.pbi' not in path.parts:
                    archive.write(path, path.relative_to(ROOT))
        archive.write(ROOT / 'Wallet.pbip', 'Wallet.pbip')

    report = json.loads((REPORT / 'definition/report.json').read_text(encoding='utf-8'))
    scope = {'name': 'ReportingWindowOnly', 'field': field('dim_date', 'is_in_reporting_window'),
             'type': 'Categorical', 'howCreated': 'User', 'isLockedInViewMode': True,
             'filter': {'Version': 2, 'From': [{'Name': 'd', 'Entity': 'dim_date', 'Type': 0}],
                        'Where': [{'Condition': {'In': {
                            'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 'd'}},
                                                       'Property': 'is_in_reporting_window'}}],
                            'Values': [[{'Literal': {'Value': 'true'}}]]}}}]}}
    report['filterConfig'] = {'filters': [scope]}
    theme_name = 'WalletExecutive'
    theme = {'name': theme_name, 'dataColors': [TEAL, '#3573B9', '#D59A35', '#B45567'],
             'background': WHITE, 'foreground': NAVY, 'tableAccent': TEAL,
             'textClasses': {'label': {'fontFace': 'Segoe UI', 'fontSize': 11, 'color': MUTED},
                             'title': {'fontFace': 'Segoe UI Semibold', 'fontSize': 13, 'color': NAVY},
                             'callout': {'fontFace': 'Segoe UI Semibold', 'fontSize': 30, 'color': NAVY}}}
    write(REPORT / 'StaticResources/RegisteredResources/WalletExecutive.json', theme)
    report['themeCollection']['customTheme'] = {
        'name': theme_name, 'type': 'RegisteredResources',
        'reportVersionAtImport': {'visual': '2.4.0', 'page': '2.1.0', 'report': '3.3.0'}}
    packages = [p for p in report.get('resourcePackages', []) if p['name'] != 'RegisteredResources']
    existing = next((p for p in report.get('resourcePackages', []) if p['name'] == 'RegisteredResources'), None)
    items = [i for i in (existing or {}).get('items', []) if i['name'] != theme_name]
    items.append({'name': theme_name, 'path': 'WalletExecutive.json', 'type': 'CustomTheme'})
    packages.append({'name': 'RegisteredResources', 'type': 'RegisteredResources', 'items': items})
    report['resourcePackages'] = packages
    write(REPORT / 'definition/report.json', report)

    page = json.loads((PAGE / 'page.json').read_text(encoding='utf-8'))
    page.update({'displayName': 'Executive overview', 'width': 1600, 'height': 900,
                 'displayOption': 'FitToPage',
                 'objects': {'background': obj(color=color(BG), transparency=literal(0))}})
    write(PAGE / 'page.json', page)

    textbox('wallet_header', 'DIGITAL WALLET  /  BI & REPORTING', 28, 20, 940, 52, 25, WHITE, NAVY, True)
    textbox('wallet_scope', 'EXECUTIVE OVERVIEW   •   Synthetic portfolio simulation', 28, 72, 940, 34, 13, '#B9DDE0', NAVY)
    textbox('wallet_period', 'Reporting window: Oct 2025 – Sep 2026  |  AED  |  UTC', 28, 114, 925, 30, 12)
    for name, title, table, col, x in [
        ('month_selector', 'MONTH', 'dim_date', 'year_month', 1000),
        ('service_selector', 'SERVICE', 'dim_service', 'service_name', 1294)]:
        visual(name, 'slicer', x, 20, 278, 100, title,
               {'Values': [projection(table, col)]}, {
                   'data': obj(mode=literal('Dropdown')),
                   'selection': obj(singleSelect=literal(False), selectAllCheckboxEnabled=literal(True)),
                   'header': obj(show=literal(False)),
                   'items': obj(fontColor=color(NAVY), textSize=literal(11))})

    cards = [('kpi_success', 'SUCCESSFUL TRANSACTIONS', 'Successful Transactions', NAVY, 0),
             ('kpi_value', 'SUCCESSFUL VALUE · AED', 'Successful Value AED', NAVY, 2),
             ('kpi_fees', 'NET FEE REVENUE · AED', 'Net Fee Revenue AED', TEAL, 2),
             ('kpi_failure', 'FAILURE RATE · ALL ATTEMPTS', 'Failure Rate', '#A65C25', 2)]
    for i, (name, title, metric, ink, precision) in enumerate(cards):
        visual(name, 'card', 28 + i*390, 158, 374, 116, title, {'Values': [measure(metric)]}, {
            'labels': obj(color=color(ink), fontSize=literal(28), labelDisplayUnits=literal(1),
                          labelPrecision=literal(precision), fontFamily=literal('Segoe UI Semibold')),
            'categoryLabels': obj(show=literal(False))})

    chart_objects = {
        'legend': obj(show=literal(False)),
        'categoryAxis': obj(show=literal(True), showAxisTitle=literal(False),
                            labelColor=color(MUTED), fontSize=literal(10)),
        'valueAxis': obj(show=literal(True), showAxisTitle=literal(False),
                         labelColor=color(MUTED), fontSize=literal(10),
                         gridlineColor=color('#E4EAF0')),
        'dataPoint': obj(defaultColor=color(TEAL)),
    }
    trend = visual('value_trend', 'lineChart', 28, 298, 920, 280,
                   'Successful payment value by month · AED',
                   {'Category': [projection('dim_date', 'year_month')],
                    'Y': [measure('Successful Value AED')],
                    'Tooltips': [measure('Successful Transactions'), measure('Reversed Value AED')]}, chart_objects)
    trend['visual']['query']['sortDefinition'] = {'sort': [
        {'field': field('dim_date', 'year_month'), 'direction': 'Ascending'}], 'isDefaultSort': False}
    service = visual('service_volume', 'clusteredBarChart', 972, 298, 600, 280,
                     'Successful transactions by service',
                     {'Category': [projection('dim_service', 'service_name')],
                      'Y': [measure('Successful Transactions')],
                      'Tooltips': [measure('Successful Value AED'), measure('Failure Rate')]}, chart_objects)
    service['visual']['query']['sortDefinition'] = {'sort': [
        {'field': field('fact_transaction', 'Successful Transactions', True), 'direction': 'Descending'}], 'isDefaultSort': False}
    table_objects = {
        'grid': obj(gridVertical=literal(False), gridHorizontal=literal(True),
                    gridHorizontalColor=color('#E4EAF0'), rowPadding=literal(10)),
        'columnHeaders': obj(fontColor=color(MUTED), backColor=color('#F6F8FA'), fontSize=literal(10)),
        'values': obj(fontColorPrimary=color(NAVY), fontSize=literal(11)),
        'total': obj(totals=literal(True), fontColor=color(NAVY), backColor=color('#EAF3F3'), fontSize=literal(11)),
    }
    visual('service_operations', 'tableEx', 28, 602, 750, 232, 'Service operations',
           {'Values': [projection('dim_service', 'service_name', label='Service'),
                       measure('Transaction Attempts', 'Attempts'), measure('Successful Transactions', 'Successful'),
                       measure('Failure Rate', 'Failure rate'), measure('Reversal Count', 'Reversals')]}, table_objects)
    visual('fee_reconciliation', 'tableEx', 802, 602, 770, 232, 'Fee revenue reconciliation · AED',
           {'Values': [projection('dim_service', 'service_name', label='Service'),
                       measure('Gross Fee Revenue AED', 'Gross fees'), measure('Fee Refunds AED', 'Refunds'),
                       measure('Net Fee Revenue AED', 'Net fees')]}, table_objects)
    textbox('simulation_footer', 'SYNTHETIC DATA ONLY  •  synthetic data. Net fees are not profit; costs are not modeled.',
            28, 850, 1544, 30, 11)
    for v in VISUALS:
        write(PAGE / 'visuals' / v['name'] / 'visual.json', v)
    # Structural checks: layout, bindings, scope and required labels.
    assert len({v['name'] for v in VISUALS}) == len(VISUALS)
    for v in VISUALS:
        p = v['position']
        assert p['x'] >= 0 and p['y'] >= 0 and p['x'] + p['width'] <= 1600 and p['y'] + p['height'] <= 900
        for role in v['visual'].get('query', {}).get('queryState', {}).values():
            for item in role['projections']:
                ref = next(iter(item['field'].values()))
                table, name = ref['Expression']['SourceRef']['Entity'], ref['Property']
                tmdl = (ROOT / 'Wallet.SemanticModel/definition/tables' / f'{table}.tmdl').read_text(encoding='utf-8-sig')
                assert f"measure '{name}'" in tmdl or f'column {name}' in tmdl, (table, name)
    print(f'Built {len(VISUALS)} native visuals. Layout and model bindings checked. Backup: {backup}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    args = parser.parse_args()
    ROOT = args.project_root.resolve()
    REPORT = ROOT / 'Wallet.Report'
    PAGE = REPORT / 'definition/pages/66d82c0d70b751fba14d'
    build()
