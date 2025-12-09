"""
claims_agent_demo.py
Single-file prototype for Autonomous Insurance Claims Processing Agent (Lite Version).
Run: python claims_agent_demo.py

What it does:
- Defines simple OCR-free pipeline (text input) to extract key FNOL fields
- Validates fields and flags missing/inconsistent info
- Computes rule-based severity score
- Routes to 'fast_track' or 'manual_review'
- Prints JSON outputs for 3 sample FNOL texts

Note: This is a demo. For production, separate modules, add OCR (pytesseract/pdfplumber), unit tests, and optional ML model.
"""

import re
import json
from datetime import datetime, date
from typing import Dict, Any, Tuple, List

# ------------------------- Utilities -------------------------

def clean_text(text: str) -> str:
    t = text.replace('\r', '\n')
    t = re.sub(r"\s+", ' ', t)
    return t.strip()


def parse_date_first_match(text: str):
    """Try common date formats and return a date object or None."""
    if not text:
        return None
    # search for common patterns
    patterns = [r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            s = m.group(0)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    pass
    # fallback: try to find month names (e.g., 9 December 2025)
    try:
        # crude fuzzy parse: look for a 4-digit year and nearby tokens
        m = re.search(r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", text)
        if m:
            return datetime.strptime(m.group(1), "%d %B %Y").date()
    except Exception:
        pass
    return None

# ------------------------- Extraction -------------------------

def extract_fields(text: str) -> Dict[str, Any]:
    t = text
    out: Dict[str, Any] = {}

    # Policy number (common patterns)
    m = re.search(r'policy(?:\s*(?:no|number|#)[:\s-]*)?([A-Z0-9\-\/]*)', t, re.I)
    out['policy_number'] = m.group(1).strip() if m and m.group(1) else None

    # Policyholder name: look for lines starting with Name, Policyholder, Insured
    m = re.search(r'(?:name|policyholder|insured)[:\s-]{1,30}([A-Z][a-zA-Z .,-]{2,60})', t)
    out['policyholder_name'] = m.group(1).strip() if m else None

    # Incident date (first date-like token)
    out['incident_date'] = parse_date_first_match(t)

    # Submission date if present
    sub = None
    m = re.search(r'(?:submission|reported|received)[:\s-]*([\d/\-]{6,12})', t, re.I)
    if m:
        sub = parse_date_first_match(m.group(1))
    out['submission_date'] = sub

    # Contact phone
    m = re.search(r'(\+?\d{10,13})', t)
    out['contact_phone'] = m.group(1) if m else None

    # Claimed amount
    m = re.search(r'(?:claimed amount|amount|total loss)[:\s-]*([₹$EUR£]?\s?[\d,\.]+)', t, re.I)
    out['claimed_amount_text'] = m.group(1).strip() if m else None
    if out['claimed_amount_text']:
        digits = re.sub(r'[^\d.]', '', out['claimed_amount_text'])
        try:
            out['claimed_amount_value'] = float(digits)
        except Exception:
            out['claimed_amount_value'] = None
    else:
        out['claimed_amount_value'] = None

    # Incident type via keywords
    low = t.lower()
    if re.search(r'\b(theft|stolen)\b', low):
        out['incident_type'] = 'theft'
    elif re.search(r'\b(collision|accident|crash)\b', low):
        out['incident_type'] = 'collision'
    elif re.search(r'\b(fire|burn)\b', low):
        out['incident_type'] = 'fire'
    elif re.search(r'\b(flood|water damage)\b', low):
        out['incident_type'] = 'water'
    else:
        out['incident_type'] = 'other'

    # Supporting docs
    out['has_police_report'] = bool(re.search(r'police report|fir|police', low))
    out['has_photos'] = bool(re.search(r'photo|image|picture|attached', low))

    return out

# ------------------------- Validation & Flags -------------------------

def validate_fields(fields: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    flags: List[str] = []
    reasons: List[str] = []
    if not fields.get('policy_number'):
        flags.append('missing_policy_number')
        reasons.append('Policy number not found.')
    if not fields.get('policyholder_name'):
        flags.append('missing_policyholder_name')
        reasons.append('Policyholder name not found.')
    if not fields.get('incident_date'):
        flags.append('missing_incident_date')
        reasons.append('Incident date not found.')
    # date consistency
    if fields.get('incident_date') and fields.get('submission_date'):
        if fields['incident_date'] > fields['submission_date']:
            flags.append('incident_after_submission')
            reasons.append('Incident date is after submission date.')
    # claimed amount sanity
    val = fields.get('claimed_amount_value')
    if val is None and fields.get('claimed_amount_text'):
        flags.append('unparseable_claim_amount')
        reasons.append('Claimed amount could not be parsed to a number.')
    if isinstance(val, (int, float)) and val > 1_000_000:
        flags.append('very_high_claim_amount')
        reasons.append('Very high claimed amount (> 1,000,000).')
    return flags, reasons

# ------------------------- Severity & Routing -------------------------

def compute_severity(fields: Dict[str, Any]) -> float:
    score = 0.0
    it = fields.get('incident_type')
    if it == 'fire':
        score += 0.5
    if it == 'collision':
        score += 0.2
    if it == 'theft':
        score += 0.3
    if fields.get('has_police_report'):
        score -= 0.15
    amt = fields.get('claimed_amount_value') or 0
    if amt > 200_000:
        score += 0.35
    if amt > 500_000:
        score += 0.2
    return max(0.0, min(1.0, score))


def decide_route(fields: Dict[str, Any], flags: List[str]) -> Tuple[str, str, float]:
    severity = compute_severity(fields)
    if flags:
        return 'manual_review', 'Missing or inconsistent information: ' + '; '.join(flags), severity
    if severity < 0.25 and (fields.get('claimed_amount_value') or 0) < 150_000:
        return 'fast_track', 'Low severity and complete fields', severity
    return 'manual_review', 'Severity or amount requires review', severity

# ------------------------- Pipeline -------------------------

def process_claim_text(text: str, submission_date: date = None) -> Dict[str, Any]:
    text = clean_text(text)
    fields = extract_fields(text)
    if submission_date:
        fields['submission_date'] = submission_date
    flags, reasons = validate_fields(fields)
    route, route_reason, severity = decide_route(fields, flags)
    out = {
        'extracted_fields': fields,
        'validation_flags': flags,
        'validation_reasons': reasons,
        'severity_score': round(severity, 2),
        'workflow': route,
        'workflow_reason': route_reason,
        'explanation': [
            'Extraction: deterministic regex + keyword matching.',
            'Validation: flags for missing/unparseable/inconsistent fields.',
            'Routing: rule-based severity + presence of flags.'
        ]
    }
    return out

# ------------------------- Demo samples & run -------------------------

SAMPLES = [
    {
        'name': 'Collision - complete',
        'text': '''
Policy Number: ABC-12345
Name: Nagalakshmi Devarapu
Incident Date: 09/12/2025
Incident: Collision with another car, photos attached.
Claimed Amount: ₹1,50,000
Police report: FIR filed.
Contact: +919876543210
'''
    },
    {
        'name': 'Theft - missing policy',
        'text': '''
Name: Ramesh Kumar
Incident Date: 01/11/2025
Incident: Vehicle stolen from parking. No photos available.
Claimed Amount: ₹3,50,000
Contact: +919812345678
'''
    },
    {
        'name': 'Fire - high amount, inconsistent date',
        'text': '''
Policy Number: FIRE-9988
Policyholder: S. Roy
Reported: 05/12/2025
Incident Date: 10/12/2025
Incident: Kitchen fire causing major damage. Photos attached.
Claimed Amount: ₹12,00,000
Police report: Police notified.
Contact: +919900112233
'''
    }
]


def main():
    today = date(2025, 12, 9)  # demo submission date
    results = []
    for s in SAMPLES:
        print(f"--- Processing sample: {s['name']} ---")
        res = process_claim_text(s['text'], submission_date=today)
        print(json.dumps(res, default=str, indent=2))
        results.append({'name': s['name'], 'result': res})

    # Optionally: write results to file
    with open('demo_results.json', 'w') as f:
        json.dump(results, f, default=str, indent=2)
    print('\nResults also saved to demo_results.json')

if __name__ == '__main__':
    main()
