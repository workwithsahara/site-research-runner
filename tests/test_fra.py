import unittest
import fra


class FraTests(unittest.TestCase):
    def test_saudi_agency_with_contact(self):
        html = "<html><body><h1>Gulf Star Recruitment</h1><p>Licensed recruitment office in Riyadh, Saudi Arabia. We hire Filipino domestic workers and skilled workers such as electrician and welder. Urgent requirement: 20 housemaid. Call +966 55 123 4567. Email info@gulfstar.sa. Partner agencies in the Philippines welcome.</p></body></html>"
        res, why = fra.evaluate("gulfstar.sa", [("https://gulfstar.sa", html)])
        self.assertEqual(why, "ok")
        self.assertEqual(res["country"], "Saudi Arabia")
        self.assertEqual(res["hires"], "Both")
        self.assertEqual(res["emails"][0], "info@gulfstar.sa")
        self.assertEqual(res["partner"], "Yes")

    def test_placeholder_email_dropped(self):
        html = "<html><head><title>Realoffice Recruitment</title></head><body>Recruitment office, manpower and staffing. Saudi Arabia Riyadh Filipino workers. Call +966 55 123 4567. Mail info@realoffice.sa or building@yoursite.com</body></html>"
        res, why = fra.evaluate("realoffice.sa", [("https://realoffice.sa", html)])
        self.assertEqual(res["emails"], ["info@realoffice.sa"])

    def test_philippine_agency_rejected(self):
        html = "<html><body>POEA licensed agency in Manila. Jobs in Saudi Arabia and Riyadh. Email hr@example.ph</body></html>"
        res, why = fra.evaluate("agency.com.ph", [("https://agency.com.ph", html)])
        self.assertIsNone(res)

    def test_non_gulf_rejected(self):
        res, why = fra.evaluate("shop.com", [("https://shop.com", "<html><body>Filipino food shop in Texas</body></html>")])
        self.assertIsNone(res)

    def test_open_market_agency_without_filipino_mention(self):
        html = "<html><body><h1>Najd Manpower</h1><p>Licensed recruitment office in Riyadh, Saudi Arabia. We bring domestic workers from abroad, Kenya and Uganda. Visa processing. Call +966 55 123 4567. Email info@najdmp.sa</p></body></html>"
        res, why = fra.evaluate("najdmp.sa", [("https://najdmp.sa", html)])
        self.assertEqual(why, "ok")
        self.assertIn("open market", res["partner"])

    def test_news_site_rejected(self):
        html = "<html><head><title>Saudi Gazette news</title></head><body>Recruitment manpower staffing news. Riyadh Saudi Filipino. +966 55 123 4567 info@sg.com.sa</body></html>"
        res, why = fra.evaluate("saudigazette.com.sa", [("https://saudigazette.com.sa", html)])
        self.assertIsNone(res)

    def test_non_recruiter_rejected(self):
        res, why = fra.evaluate("food.sa", [("https://food.sa", "<html><body>Riyadh Saudi restaurant menu. Call +966 55 123 4567 info@food.sa</body></html>")])
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
