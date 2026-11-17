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
        before = search._state["bing"]["until"]
        search.cool("bing", True)
        self.assertGreater(search._state["bing"]["until"], before)
        search._state["bing"].update({"until": 0.0, "strikes": 0})

    def test_search_merges_sources(self):
        class R:
            status_code = 200
            def __init__(self, t): self.text = t
        class S:
            n = 0
            def get(self, url, **k):
                S.n += 1
                return R('<a href="https://site%d.com/">x</a><a href="https://shared.com/">y</a>' % S.n)
        for st in search._state.values():
            st.update({"until": 0.0, "strikes": 0})
        out = search.search_hosts("roofing Tulsa", S(), 30)
        self.assertIn("shared.com", out)
        self.assertEqual(len(out), 6)

    def test_only_real_results_when_page_has_result_blocks(self):
        html = ('<ul><li class="b_algo"><h2><a href="https://real-agency.com/">r</a></h2></li></ul>'
                '<div class="b_ans"><a href="https://emojipedia.org/">junk</a></div>'
                '<div class="b_rs"><a href="https://soundboard.com/">related</a></div>')
        self.assertEqual(search.result_hosts(html, 30), ["real-agency.com"])


if __name__ == "__main__":
    unittest.main()
