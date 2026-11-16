"""Personalized first line and role suggestion. Uses only what was found on the company's own pages."""
import re

SPECS = [
    ("technology and IT", r"\b(?:technology|software|developer|devops|cyber ?security|data engineer|tech recruitment)\b"),
    ("finance and accounting", r"\b(?:finance|financial services|accounting|banking|investment banking|audit)\b"),
    ("healthcare", r"\b(?:healthcare|nursing|nurses|clinical|medical staffing|allied health)\b"),
    ("engineering", r"\b(?:engineering|engineers|manufacturing|mechanical)\b"),
    ("legal", r"\b(?:legal recruitment|solicitors|law firms|paralegal)\b"),
    ("executive search", r"\b(?:executive search|c-suite|board level|retained search)\b"),
    ("construction and trades", r"\b(?:construction|trades|skilled trades|civil)\b"),
    ("hospitality", r"\b(?:hospitality|restaurants|hotels|food service)\b"),
    ("sales and marketing", r"\b(?:sales recruitment|marketing recruitment|digital marketing|business development)\b"),
    ("education", r"\b(?:education|teachers|teaching|edtech|schools)\b"),
    ("supply chain and logistics", r"\b(?:supply chain|logistics|procurement|warehouse)\b"),
    ("energy", r"\b(?:energy|renewables|oil and gas|commodities)\b"),
    ("remote hiring", r"\b(?:remote hiring|remote jobs|remote talent|offshore)\b"),
]


def _is_recruit(industry):
    return bool(re.search(r"recruit|staffing|executive search", industry or "", re.I))


def personalize(company, first, industry, text):
    best, n = "", 0
    if _is_recruit(industry):
        for name, rx in SPECS:
            c = len(re.findall(rx, text, re.I))
            if c > n:
                best, n = name, c
    hi = f"{first}, " if first else ""
    if best and n >= 2:
        return (f"{hi}I came across {company} and noticed the focus on {best} hiring.",
                f"{best} wording appears {n} times on the pages checked")
    return (f"{hi}I came across {company} and wanted to reach out directly.",
            "no specialism proven on the pages, so the line stays general")


def ask_on_call(industry):
    if _is_recruit(industry):
        return "How do you get new clients and candidates in front of you right now, and who looks after your website and social posting?"
    return "How do new customers find you right now, and who looks after your website and social posting?"


def role_for(industry, offer, gaps, no_social, text):
    """Suggestion for a role Sahara or Khalil could apply for. A guess from the industry and the gaps, not a confirmed opening."""
    roles = []
    if _is_recruit(industry):
        roles += ["BDR or SDR (agency new business)", "Lead Admin or Recruitment Coordinator"]
    elif re.search(r"med ?spa|aesthetic|clinic|cosmetic|beauty", industry or "", re.I):
        roles += ["Appointment Setter or Patient Coordinator", "Lead Admin"]
    else:
        roles += ["Lead Admin or Virtual Assistant", "Appointment Setter"]
    if no_social:
        roles.insert(1, "Social Media Manager")
    if gaps:
        roles.append("Automation or Website Specialist")
    out, seen = [], set()
    for r in roles:
        if r not in seen:
            seen.add(r)
            out.append(r)
    out = out[:3]
    hint = " (hiring wording on their site)" if re.search(r"join (?:our|the) team|we'?re hiring|careers", text or "", re.I) else " (guess, check if they are hiring)"
    return "; ".join(out) + hint
