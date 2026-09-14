"""Markdown / MDX / Hugo normaliser.

Handles the three Markdown dialects in the corpus:
- Acme synthetic docs (plain Markdown + YAML frontmatter)
- kubernetes/website (Hugo: frontmatter, ``{{< shortcode >}}`` / ``{{% shortcode %}}``,
  ``<!-- overview -->`` markers)
- hashicorp/web-unified-docs (MDX: frontmatter, ``import`` lines, JSX components such as
  ``<Tabs>``/``<Tab>``/``<Note>``, ``-> **Tip:**`` callouts)

Deliberately conservative: it strips *markup*, never *content*. HTML comments are kept — the
adversarial documents rely on them and a downstream system must cope with them as data.
"""

import re

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_MDX_IMPORT = re.compile(r"^(import|export)\s.*$", re.M)
# {{< note >}} ... {{< /note >}}  and  {{% ... %}} — keep inner content, drop the tags.
_HUGO_SHORTCODE = re.compile(r"\{\{[<%]\s*/?\s*[\w-]+[^}]*?[>%]\}\}")
# JSX components used by HashiCorp docs; keep inner content.
_JSX_TAG = re.compile(r"</?(Tabs|Tab|Note|Warning|Tip|Highlight|CodeBlockConfig|CodeTabs)\b[^>]*>")
_HASHICORP_CALLOUT = re.compile(r"^(->|~>|!>)\s*", re.M)
_TRAILING_WS = re.compile(r"[ \t]+$", re.M)
_MULTI_BLANK = re.compile(r"\n{3,}")


def _outside_code_fences(text: str, fn: "type[_Transform]") -> str:
    """Apply a transform only to segments outside ``` fences so code stays byte-exact."""
    parts = re.split(r"(```.*?```)", text, flags=re.S)
    return "".join(p if p.startswith("```") else fn.apply(p) for p in parts)


class _Transform:
    @staticmethod
    def apply(segment: str) -> str:
        segment = _MDX_IMPORT.sub("", segment)
        segment = _HUGO_SHORTCODE.sub("", segment)
        segment = _JSX_TAG.sub("", segment)
        segment = _HASHICORP_CALLOUT.sub("", segment)
        return segment


def parse_markdown(raw: str) -> str:
    text = raw.replace("\r\n", "\n")
    text = _FRONTMATTER.sub("", text, count=1)
    text = _outside_code_fences(text, _Transform)
    text = _TRAILING_WS.sub("", text)
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip() + "\n"
