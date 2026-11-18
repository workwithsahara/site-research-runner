"""Decides whether a scraped 'owner' really starts with a person's first name. Anything doubtful returns False,
and the greeting then falls back to 'Hi there'."""
import re
import gender_guesser.detector as _g
try:
    from english_words import get_english_words_set
    _EN = {w.lower() for w in get_english_words_set(["web2"], lower=True)}
except Exception:
    _EN = set()
_d = _g.Detector(case_sensitive=False)
TITLES = {"dr", "mr", "mrs", "ms", "miss", "prof", "sir", "rev", "fr", "hon", "mx"}
# words that are never part of a person's name (surname-like words such as Hill, Glass, Wood, King are NOT here)
BAD = set("""team staff station division industry industries warehouse loans loan treasury board nurses nurse dentist dental dentistry planner council surgeon arborist trust city hours practice practioner practitioner studio region artist brow wedding veterinary veterinarian veterinarians certified sourcing past service services solutions group company companies office offices clinic centre center care health medical law legal firm partners associates agency recruitment consulting consultant consultants consultancy management manager managers director directors executive executives president presidents owner founder founders founding chief senior junior principal specialist specialists expert experts professional professionals supply store shop shops market markets retail trading trade tools equipment products product design designs designer designers builder builders building construction contractors contractor plumbing electrical roofing heating cooling air repair repairs cleaning landscaping garden pest control auto automotive body motors motor garage fitness gym yoga spa salon beauty hair nails barber massage therapy therapist therapists physio physiotherapy physiotherapist chiropractic hospital pharmacy school academy college university institute training education tutor tutors tutoring childcare kids children family home homes house housing real estate property properties realty mortgage finance financial accounting accountant accountants tax bookkeeping insurance bank banking investment investments equity capital fund funds wealth advisors advisor advisory planning marketing media digital web website online social photography photo video film events event catering restaurant cafe coffee bar pub hotel motel travel tours tour transport transportation logistics freight shipping delivery moving storage security safety fire emergency rescue animal animals pet pets dog dogs cat cats vet vets farm farms feed food foods fresh organic natural energy solar power water gas oil mining steel metal metals timber paint painting printing print packaging paper plastic rubber chemical chemicals lab laboratory research science technology tech software systems system network networks data cyber computer computers mobile phone phones telecom radio television news press magazine publishing publications books book library gallery museum arts art music dance theatre theater sports sport club clubs league association society foundation charity church ministry ministries community county state national international global world worldwide regional local united american australian canadian british european asian pacific northern southern eastern western north south east west central coastal island harbour harbor road street avenue lane place court square plaza tower towers lodge inn resort villa apartments suites rooms who friendly what where when why how best top leading premier quality licensed registered approved accredited trusted reliable affordable cheap free new old modern classic custom bespoke luxury premium elite prime smart bright rapid quick fast express direct instant total complete every any each other more most our your their this that these those the and for with from into over under about contact contacts info information get started apply now today welcome meet read learn view see find call email text click here page pages site sites menu search login log sign join member members membership female male officer officers enforcement guardian concierge instagram twitter facebook linkedin experience report reviews reader directory locations overview appointments quote guarantee championship pioneering stability pro lines asset account potential policy esthetician groomer technician nutrition spirits bakery extensions timeshare transfer ownership completed minded rules lead led time carrier delivery carrier abrasives contractor affair district weather lorem name last recall date given required casual casualty implant sale exist existing greenhouse learning commercial holiday strategic leadership operating operations sourcing""".split())
BAD |= {"who", "us", "we", "i", "dr"}


def _known(w):
    return _d.get_gender(w) != "unknown"


def real_first_name(owner):
    toks = (owner or "").split()
    if not toks:
        return False
    if len(toks) == 1:   # a lone word is only trusted when it is clearly a given name
        w = toks[0]
        return (re.fullmatch(r"[A-Z][a-z]{2,15}", w) is not None and w.lower() not in BAD and w.lower() not in TITLES
                and _d.get_gender(w) in ("male", "female", "mostly_male", "mostly_female"))
    f = toks[0]
    if not re.fullmatch(r"[A-Z][a-zA-Z'\-]{1,19}", f):
        return False
    fl = f.lower().strip("-'")
    if fl in TITLES or fl in BAD:
        return False
    if any(t.lower().strip("-'.") in BAD for t in toks[1:]):
        return False
    if _known(f):
        return True
    if fl in _EN:
        return False
    return True


def first_name(owner):
    """First name for the greeting, or "" when the scraped text does not clearly start with a person's first name."""
    return owner.split()[0] if real_first_name(owner) else ""
