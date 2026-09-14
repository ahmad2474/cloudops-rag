from cloudops_rag.ingestion.parsers import parse_aws_html, parse_markdown


def test_markdown_strips_frontmatter_and_hugo_shortcodes() -> None:
    raw = (
        "---\ntitle: Pods\n---\n<!-- overview -->\n{{< note >}}\nKeep me.\n{{< /note >}}\n\n"
        "## Section\n\ntext\n"
    )
    out = parse_markdown(raw)
    assert "title: Pods" not in out
    assert "{{<" not in out
    assert "Keep me." in out
    assert "<!-- overview -->" in out  # comments are content, not markup
    assert "## Section" in out


def test_markdown_strips_mdx_imports_and_jsx_but_keeps_inner_text() -> None:
    raw = (
        'import X from "y"\n\n<Tabs>\n<Tab heading="CLI">\n\n'
        "-> **Tip:** run `terraform import`.\n\n</Tab>\n</Tabs>\n"
    )
    out = parse_markdown(raw)
    assert "import X" not in out
    assert "<Tab" not in out
    assert "**Tip:** run `terraform import`." in out
    assert not out.startswith("->")


def test_markdown_never_touches_code_fences() -> None:
    raw = "para {{< bad >}}\n\n```hcl\nimport {\n  to = aws_s3_bucket.b\n}\n{{< untouched >}}\n```"
    out = parse_markdown(raw)
    assert "{{< bad >}}" not in out
    assert "{{< untouched >}}" in out
    assert "import {" in out


def test_markdown_collapses_blank_lines_and_normalises_newlines() -> None:
    out = parse_markdown("a\r\n\r\n\r\n\r\nb  \n")
    assert out == "a\n\nb\n"


AWS_HTML = """<html><body>
<nav>skip</nav>
<div id="main-col-body">
  <awsui-alert class="awsdocs-page-banner"><p><strong>Help improve this page</strong>
  </p></awsui-alert>
  <h1 class="topictitle">Troubleshoot EKS</h1>
  <p>Intro with <code class="code">aws-node</code>.</p>
  <h2 id="pending">Pods stuck in <code>Pending</code></h2>
  <div class="code-btn-container"><button class="btn-copy-code">Copy</button></div>
  <pre class="programlisting">kubectl describe pod &lt;pod&gt;
kubectl get events</pre>
  <div class="table-container"><table><tr><th>Error</th><th>Fix</th></tr>
  <tr><td>Insufficient cpu</td><td>Add nodes</td></tr></table></div>
  <img src="x.png" alt="diagram"/>
</div>
<footer>footer</footer>
</body></html>"""


def test_aws_html_extracts_article_and_drops_chrome() -> None:
    out = parse_aws_html(AWS_HTML)
    assert out.startswith("# Troubleshoot EKS")
    assert "skip" not in out and "footer" not in out
    assert "Help improve this page" not in out
    assert "Copy" not in out


def test_aws_html_preserves_code_blocks_tables_and_inline_code() -> None:
    out = parse_aws_html(AWS_HTML)
    assert "```\nkubectl describe pod <pod>\nkubectl get events\n```" in out
    assert "`aws-node`" in out
    assert "## Pods stuck in `Pending`" in out
    assert "| Insufficient cpu | Add nodes |" in out
    assert "[image: diagram]" in out
