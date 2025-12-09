# Autonomous-Insurance-Claims-Processing-Agent
README – Autonomous Insurance Claims Processing Agent (Lite Version)
1. Overview
This project is a single-file Python prototype (claims_agent_demo.py) that performs autonomous
insurance claims processing on FNOL (First Notice of Loss) text documents.
The goal of this Lite Version is to demonstrate:- Extraction of key FNOL fields- Basic validation and detection of missing/inconsistent data- Simple rule-based severity scoring- Workflow routing (fast-track vs manual review)- Optional explainability for all decisions
2. Approach
A. Extraction (Regex + Keyword Rules)
The system converts raw FNOL text into structured JSON by extracting fields like Policy Number,
Policyholder Name, Incident Type, Dates, Claim Amount, Contact Phone, and Supporting Documents.
Techniques include regex and keyword matching.
B. Validation Logic
Checks for missing fields, invalid dates, unparsable amounts, and unusually high claim amounts.
Generates validation flags with explanations.
C. Severity Score (Rule-Based)
Computes a lightweight severity score (0–1) based on incident type, claim amount, and presence of a
police report.
D. Workflow Routing
Rules:- If validation flags exist → Manual Review- Else if low severity and low claim amount → Fast Track
- Otherwise → Manual Review
E. Explainability
Each output contains explanations of field extraction, validations, and routing decisions.
F. Demo Samples
Contains three FNOL samples:
1. Collision – complete
2. Theft – missing policy number
3. Fire – high severity with inconsistent dates
3. How to Run
Requires Python 3.x.
Run:
python claims_agent_demo.py
Outputs include console JSON and demo_results.json.
4. Future Improvements- OCR/PDF ingestion- ML-based classification- Modular architecture- FastAPI endpoints- Unit tests- Improved date handling
5. Why This Approach Works- End-to-end processing- Deterministic and simple- Easy to test/extend
- Fully explainable- Meets all assignment requirements
