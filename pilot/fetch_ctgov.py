"""ClinicalTrials.gov API v2 helpers. Usage:
  python fetch_ctgov.py all OUT.csv            all interventional studies (used by the pilot)
  python fetch_ctgov.py stopped OUT.csv        stopped industry interventional studies only
  python fetch_ctgov.py ids OUT.csv IDS.csv    records for the nct_id column of IDS.csv
"""
import sys, time, json, requests, pandas as pd
API = 'https://clinicaltrials.gov/api/v2/studies'
FIELDS = ','.join(['NCTId','LeadSponsorName','LeadSponsorClass','CollaboratorName','CollaboratorClass',
                   'Phase','StartDate','OverallStatus','WhyStopped','CompletionDate','PrimaryCompletionDate',
                   'StudyType','InterventionType','LastUpdatePostDate'])
S = requests.Session()

def get(params):
    for i in range(6):
        try:
            r = S.get(API, params=params, timeout=120)
            if r.status_code == 429: time.sleep(10 * (i + 1)); continue
            r.raise_for_status(); return r.json()
        except Exception as e:
            print('retry', e, flush=True); time.sleep(5 * (i + 1))
    raise RuntimeError(params)

def flat(st):
    p = st.get('protocolSection', {})
    idm, sm = p.get('identificationModule', {}), p.get('statusModule', {})
    sc, dm = p.get('sponsorCollaboratorsModule', {}), p.get('designModule', {})
    ai = p.get('armsInterventionsModule', {})
    lead = sc.get('leadSponsor', {}) or {}
    col = sc.get('collaborators', []) or []
    return {
        'nct_id': idm.get('nctId'),
        'lead_sponsor': lead.get('name'), 'lead_class': lead.get('class'),
        'collaborators': '|'.join(c.get('name', '') for c in col),
        'collab_classes': '|'.join(c.get('class', '') for c in col),
        'phases': '|'.join(dm.get('phases', []) or []),
        'study_type': dm.get('studyType'),
        'start_date': (sm.get('startDateStruct') or {}).get('date'),
        'status': sm.get('overallStatus'), 'why_stopped': sm.get('whyStopped'),
        'completion_date': (sm.get('completionDateStruct') or {}).get('date'),
        'primary_completion_date': (sm.get('primaryCompletionDateStruct') or {}).get('date'),
        'last_update': (sm.get('lastUpdatePostDateStruct') or {}).get('date'),
        'intervention_types': '|'.join(sorted({i.get('type', '') for i in (ai.get('interventions') or [])})),
    }

def paged(params):
    rows, token, n = [], None, 0
    while True:
        q = dict(params, pageSize=1000, format='json', fields=FIELDS)
        if token: q['pageToken'] = token
        js = get(q); rows += [flat(s) for s in js.get('studies', [])]
        n += 1; token = js.get('nextPageToken')
        if n % 10 == 0: print(n, 'pages', len(rows), 'rows', flush=True)
        if not token: return rows

def by_ids(ncts, chunk=200):
    ncts = sorted(set(ncts)); rows = []
    for i in range(0, len(ncts), chunk):
        rows += paged({'filter.ids': ','.join(ncts[i:i + chunk])})
        if (i // chunk) % 20 == 0: print('ids', i, '/', len(ncts), flush=True)
    return pd.DataFrame(rows)

def stopped_industry():
    return pd.DataFrame(paged({'filter.overallStatus': 'TERMINATED,WITHDRAWN,SUSPENDED',
                               'filter.advanced': 'AREA[LeadSponsorClass]INDUSTRY AND AREA[StudyType]INTERVENTIONAL'}))

if __name__ == '__main__':
    mode, out = sys.argv[1], sys.argv[2]
    if mode == 'stopped':
        df = stopped_industry()
    elif mode == 'all':
        df = pd.DataFrame(paged({'filter.advanced': 'AREA[StudyType]INTERVENTIONAL'}))
    else:
        ids = pd.read_csv(sys.argv[3]).nct_id
        df = by_ids(ids)
    df.to_csv(out, index=False); print(mode, len(df), 'rows ->', out)
