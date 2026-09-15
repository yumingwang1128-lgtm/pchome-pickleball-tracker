import html as html_module
import re
from collections.abc import Iterable


def parse_product_links(html: str, target_terms: str | Iterable[str]) -> list[tuple[str, str]]:
    """Return distinct PChome product links whose visible title contains a configured product term."""
    terms = (target_terms,) if isinstance(target_terms, str) else tuple(target_terms)
    matches = re.finditer(
        r'<a\s+href=["\'](?P<href>/prod/(?P<id>[A-Z0-9-]+))["\'][^>]*>(?P<title>.*?)</a>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    accessory_markers = ("保護", "拍套", "收納", "清潔", "橡皮擦", "配重")

    def add_link(product_id: str, title: str) -> None:
        if (
            any(term in title for term in terms)
            and not any(marker in title for marker in accessory_markers)
            and product_id not in seen
        ):
            seen.add(product_id)
            links.append((product_id, f"https://24h.pchome.com.tw/prod/{product_id}"))

    for match in matches:
        title = re.sub(r"<[^>]+>", "", html_module.unescape(match.group("title")))
        product_id = match.group("id").upper()
        add_link(product_id, title)

    payload = html.replace(r'\"', '"')
    for link_match in re.finditer(r'"link":"/prod/(?P<id>[A-Z0-9-]+)"', payload, flags=re.IGNORECASE):
        preceding_payload = payload[max(0, link_match.start() - 5000):link_match.start()]
        names = re.findall(r'"originProductName":"(?P<title>(?:\\.|[^"\\])*)"', preceding_payload)
        if names:
            add_link(link_match.group("id").upper(), html_module.unescape(names[-1]))
    return links
