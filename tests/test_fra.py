import unittest
import fra


class FraTests(unittest.TestCase):
    def test_saudi_agency_with_contact(self):
        html = "<html><body><h1>Gulf Star Recruitment</h1><p>Licensed recruitment office in Riyadh, Saudi Arabia. We hire Filipino domestic workers and skilled workers such as electrician and welder. Urgent requirement: 20 housemaid. Call +966 55 123 4567. Email info@gulfstar-example.sa. Partner agencies in the Philippines welcome.</p></body></html>"
        res, why = fra.evaluate("gulfstar-example.sa", [("https://gulfstar-example.sa", html)])
        self.assertEqual(why, "ok")
        self.assertEqual(res["country"], "Saudi Arabia")
        self.assertEqual(res["hires"], "Both")
        self.assertEqual(res["phones"][0], "+966 55 123 4567")
        self.assertEqual(res["partner"], "Yes")

    def test_philippine_agency_rejected(self):
        html = "<html><body>POEA licensed agency in Manila. Jobs in Saudi Arabia and Riyadh. Email hr@example.ph</body></html>"
        res, why = fra.evaluate("agency.com.ph", [("https://agency.com.ph", html)])
        self.assertIsNone(res)

    def test_non_gulf_rejected(self):
        res, why = fra.evaluate("shop.com", [("https://shop.com", "<html><body>Filipino food shop in Texas</body></html>")])
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
