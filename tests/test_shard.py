import datetime
import unittest

import fresh
import shard_queries


class ShardTests(unittest.TestCase):
    def test_fresh_drops_known_sites(self):
        f = fresh.Fresh(lambda: ["a.com", "B.com"])
        out = f.filter([("a.com", "x"), ("www.b.com", "y"), ("c.com", "z")])
        self.assertEqual(out, [("c.com", "z")])

    def test_city_queries_cover_many_cities(self):
        cities = {"Canada": ["Toronto", "Calgary"]}
        ex = shard_queries.make_expander(cities)
        out = ex(["roofing contractor USA | Home services", "dental clinic Canada | Dental"], datetime.date(2026, 11, 17))
        self.assertGreater(len(out), 300)
        self.assertTrue(all("|" in q for q in out))
        self.assertTrue(any(" TX" in q or " CA" in q for q in out))
        self.assertTrue(any("Toronto" in q or "Calgary" in q for q in out))
        self.assertFalse(any(q.startswith("roofing contractor USA") for q in out))


if __name__ == "__main__":
    unittest.main()
