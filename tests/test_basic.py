import datetime
import unittest

from bs4 import BeautifulSoup

import personalize
import run
import scraper as s


class T(unittest.TestCase):
    def test_email_proven_matches_owner(self):
        ok, _ = s.email_proven("jane@acme.com", "Jane Smith", [])
        self.assertTrue(ok)

    def test_general_inbox_not_owner_direct(self):
        ok, _ = s.email_proven("info@acme.com", "Jane Smith", [])
        self.assertFalse(ok)

    def test_shopify_only_gets_laya365(self):
        offer, _, _ = s.offer_for("Shopify", ["no mobile viewport tag"], set())
        self.assertEqual(offer, "LAYA 365")
        offer, _, _ = s.offer_for("Shopify", ["no mobile viewport tag"], {"instagram"})
        self.assertEqual(offer, "")

    def test_offer_combo(self):
        self.assertEqual(s.offer_for("", ["builder"], set())[0], "Website + LAYA 365")
        self.assertEqual(s.offer_for("", ["builder"], {"facebook"})[0], "Website")
        self.assertEqual(s.offer_for("", [], set())[0], "LAYA 365")

    def test_gaps(self):
        html = "<html><head></head><body>Copyright 2018 <a href='https://x.wixstatic.com/a.png'>x</a></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        g = s.visible_gaps({"https://a.com": html}, html, soup, "", year=2026)
        self.assertTrue(any("viewport" in x for x in g))
        self.assertTrue(any("Wix" in x for x in g))
        self.assertTrue(any("2018" in x for x in g))
        self.assertTrue(any("form" in x for x in g))

    def test_social_found(self):
        pages = {"u": '<a href="https://www.facebook.com/acmejobs">f</a> <a href="https://www.facebook.com/sharer.php?u=1">s</a>'}
        self.assertEqual(s.social_found(pages), {"facebook"})

    def test_parse_seed(self):
        d = s.parse_seed("www.Acme.com | Recruitment | 12 | United States | Miami, FL | Acme")
        self.assertEqual((d["domain"], d["industry"], d["headcount"], d["country"]), ("acme.com", "Recruitment", 12, "United States"))

    def test_duplicate_by_domain_email_phone(self):
        m = [{"Website": "https://acme.com", "Email": "a@acme.com", "Phone": "555-123-4567"}]
        self.assertTrue(run.is_duplicate({"Website": "acme.com", "Email": "", "Phone": ""}, m))
        self.assertTrue(run.is_duplicate({"Website": "b.com", "Email": "A@acme.com", "Phone": ""}, m))
        self.assertTrue(run.is_duplicate({"Website": "b.com", "Email": "", "Phone": "(555) 123-4567"}, m))
        self.assertFalse(run.is_duplicate({"Website": "b.com", "Email": "c@b.com", "Phone": "555-999-0000"}, m))

    def test_personalize_needs_evidence(self):
        line, why = personalize.personalize("Acme", "Jane", "Recruitment", "we recruit healthcare nurses and clinical staff")
        self.assertIn("healthcare", line)
        line, why = personalize.personalize("Acme", "Jane", "Recruitment", "we hire people")
        self.assertIn("general", why)

    def test_expand_queries_adds_state(self):
        q = run.expand_queries(["boutique recruitment agency USA | Recruitment"], datetime.date(2026, 11, 16))
        self.assertGreater(len(q), 1)
        self.assertTrue(all("|" in x for x in q))


    def test_clean_city_and_phone(self):
        self.assertEqual(s.clean_city("First Street North Glasgow"), "Glasgow")
        self.assertEqual(s.clean_city("New York"), "New York")
        self.assertEqual(s.fmt_phone("16467065330"), "646-706-5330")
        self.assertEqual(s.fmt_phone("+442034686977"), "+442034686977")

    def test_expand_queries_adds_city(self):
        q = run.expand_queries(["boutique recruitment agency contact Australia | Recruitment"], datetime.date(2026, 11, 16))
        self.assertGreater(len(q), 1)
        self.assertTrue(any(c in x for x in q for c in run.CITIES["Australia"]))


if __name__ == "__main__":
    unittest.main()
