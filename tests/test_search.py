import unittest

import search


class SearchTests(unittest.TestCase):
    def test_wrapped_links_are_unwrapped(self):
        html = ('<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Facme-recruit.com%2F&rut=x">a</a>'
                '<a href="https://www.bing.com/ck/a?u=a1aHR0cHM6Ly9leGFtcGxlLWFnZW5jeS5jb20v&x=1">b</a>'
                '<a href="https://r.search.yahoo.com/RU=https%3a%2f%2ftest-staff.com%2f/RK=2">c</a>'
                '<a href="https://www.mojeek.com/about">d</a><a href="https://plain-site.org/p">e</a>')
        self.assertEqual(search.result_hosts(html, 15),
                         ["acme-recruit.com", "example-agency.com", "test-staff.com", "plain-site.org"])

    def test_blocked_engine_is_paused(self):
        before = search._state["ddg"]["until"]
        search.cool("ddg", True)
        self.assertGreater(search._state["ddg"]["until"], before)
        search._state["ddg"].update({"until": 0.0, "strikes": 0})


if __name__ == "__main__":
    unittest.main()
