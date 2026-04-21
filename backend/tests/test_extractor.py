from processing.extractor import _parse_arxiv_sections, _strip_html

ARXIV_HTML_FIXTURE = """
<html><body>
<section id="S1">
  <h2>1 Introduction</h2>
  <p>This paper presents a novel approach to agent planning.</p>
  <p>We demonstrate improvements on standard benchmarks.</p>
</section>
<section id="S2">
  <h2>2 Related Work</h2>
  <p>Prior work includes many things.</p>
</section>
<section id="S5">
  <h2>5 Conclusion</h2>
  <p>We showed that adaptive planning reduces failures by 40%.</p>
</section>
</body></html>
"""


def test_parse_arxiv_sections_extracts_intro_and_conclusion():
    result = _parse_arxiv_sections(ARXIV_HTML_FIXTURE)
    assert "novel approach" in result
    assert "adaptive planning" in result
    assert "Related Work" not in result


def test_strip_html_removes_tags():
    result = _strip_html("<p>Hello <b>world</b></p>")
    assert "Hello" in result
    assert "world" in result
    assert "<" not in result
