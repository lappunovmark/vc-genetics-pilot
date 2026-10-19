"""NIH SBIR/STTR awards from the NIH RePORTER API v2 (public, no key).

Usage: python fetch_reporter_sbir.py OUT_CSV [FIRST_FY] [LAST_FY]
Activity codes: R41/R42 (STTR phase I/II), R43/R44 (SBIR phase I/II), U43/U44 (cooperative-agreement SBIR),
SB1 (commercialisation readiness). One query per fiscal year x code keeps every query under the API's 15,000-record
offset limit; the API asks for no more than one request per second.
"""
import csv, sys, time
import requests

URL = 'https://api.reporter.nih.gov/v2/projects/search'
CODES = ['R41', 'R42', 'R43', 'R44', 'U43', 'U44', 'SB1']
FIELDS = ['ApplId', 'ProjectNum', 'CoreProjectNum', 'FiscalYear', 'ActivityCode', 'Organization', 'AwardAmount',
          'ProjectStartDate', 'ProjectTitle', 'AgencyIcAdmin']
COLS = ['appl_id', 'project_num', 'core_project_num', 'fiscal_year', 'activity_code', 'org_name', 'org_city', 'org_state',
        'org_country', 'org_uei', 'org_duns', 'award_amount', 'project_start_date', 'project_title', 'ic']


def row(p):
    o = p.get('organization') or {}
    duns = o.get('org_duns') or []
    return [p.get('appl_id'), p.get('project_num'), p.get('core_project_num'), p.get('fiscal_year'), p.get('activity_code'),
            o.get('org_name'), o.get('org_city'), o.get('org_state'), o.get('org_country'), o.get('org_ueis') and ';'.join(o['org_ueis']),
            ';'.join(duns) if isinstance(duns, list) else duns, p.get('award_amount'), p.get('project_start_date'),
            p.get('project_title'), (p.get('agency_ic_admin') or {}).get('abbreviation')]


def main(out, fy0=2000, fy1=2025):
    s = requests.Session()
    s.headers['User-Agent'] = 'vc-genetics-thesis (UCL MSc dissertation; contact via repository)'
    n = 0
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(COLS)
        for fy in range(int(fy0), int(fy1) + 1):
            for code in CODES:
                off = 0
                while True:
                    body = {'criteria': {'fiscal_years': [fy], 'activity_codes': [code]}, 'include_fields': FIELDS,
                            'offset': off, 'limit': 500, 'sort_field': 'appl_id', 'sort_order': 'asc'}
                    for k in range(5):
                        try:
                            r = s.post(URL, json=body, timeout=120)
                            if r.status_code == 200:
                                break
                        except requests.RequestException:
                            pass
                        time.sleep(5 * (k + 1))
                    j = r.json()
                    res = j.get('results') or []
                    for p in res:
                        w.writerow(row(p))
                    n += len(res)
                    total = (j.get('meta') or {}).get('total', 0)
                    off += 500
                    time.sleep(1.1)
                    if off >= total or not res:
                        break
                print(fy, code, total, 'cum', n, flush=True)
    print('done', n)


if __name__ == '__main__':
    main(*sys.argv[1:4])
