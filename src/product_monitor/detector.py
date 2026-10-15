"""Detect a named product's availability on a store page."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
import re
from typing import Any


class Availability:
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DetectorResult:
    availability: str
    evidence: str | None = None
    error_message: str | None = None
    product_found: bool = False


@dataclass(eq=False)
class _Element:
    tag: str
    attributes: dict[str, str]
    parent: _Element | None = None
    children: list[_Element] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    _text_cache: str | None = field(default=None, init=False, repr=False)

    def text(self) -> str:
        # The tree is fully built before any caller reads text, so caching is safe.
        if self._text_cache is not None:
            return self._text_cache
        parts = list(self.text_parts)
        parts.extend(
            self.attributes.get(attribute, "")
            for attribute in ("alt", "aria-label", "title", "value")
        )
        for child in self.children:
            parts.append(child.text())
        self._text_cache = " ".join(" ".join(parts).split())
        return self._text_cache


class _ProductPageParser(HTMLParser):
    _VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
    _IGNORED_TAGS = {"head", "noscript", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("document", {})
        self.stack = [self.root]
        self.elements: list[_Element] = []
        self.json_ld_blocks: list[str] = []
        self._ignored_depth = 0
        self._script_depth = 0
        self._capturing_json_ld = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if tag == "script":
            self._script_depth += 1
            if self._script_depth == 1:
                self._capturing_json_ld = (
                    attributes.get("type", "").split(";", 1)[0].strip().lower()
                    == "application/ld+json"
                )
                self._script_parts = []
            return
        if self._ignored_depth or self._script_depth:
            return

        element = _Element(tag, attributes, self.stack[-1])
        self.stack[-1].children.append(element)
        self.elements.append(element)
        if tag not in self._VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if tag == "script" and self._script_depth:
            self._script_depth -= 1
            if not self._script_depth and self._capturing_json_ld:
                self.json_ld_blocks.append("".join(self._script_parts))
                self._capturing_json_ld = False
            return
        if self._ignored_depth or self._script_depth:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self._capturing_json_ld:
            self._script_parts.append(data)
        elif not self._ignored_depth and not self._script_depth:
            self.stack[-1].text_parts.append(data)


_UNAVAILABLE_TERMS = (
    "sold out",
    "out of stock",
    "unavailable",
    "not available",
    "not in stock",
)
_PURCHASE_ACTIONS = (
    "add to cart",
    "add to order",
    "add to bag",
    "customize",
    "order now",
    "buy now",
    "select options",
    "choose options",
)
_PRODUCT_MARKERS = re.compile(
    r"(?:product|sku|menu)[-_ ]?(?:card|tile|item)|item[-_ ]?card",
    re.IGNORECASE,
)
_AVAILABILITY_ATTRIBUTES = {
    "availability",
    "data-availability",
    "data-stock-status",
    "data-inventory-status",
}
_AVAILABLE_SCHEMA_VALUES = {
    "instock",
    "limitedavailability",
    "onlineonly",
    "preorder",
    "backorder",
}
_UNAVAILABLE_SCHEMA_VALUES = {
    "outofstock",
    "soldout",
    "discontinued",
}
_PURCHASE_CONTROL_TAGS = {"a", "button", "input"}


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _matches_product(name: object, product_name: str) -> bool:
    if not isinstance(name, str):
        return False
    normalized_name = _normalize(name)
    normalized_query = _normalize(product_name)
    return bool(normalized_query) and (
        normalized_query in normalized_name or normalized_name in normalized_query
    )


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _schema_product_results(
    blocks: list[str],
    product_name: str,
) -> list[DetectorResult]:
    results = []
    for block in blocks:
        try:
            document = json.loads(block)
        except (json.JSONDecodeError, TypeError):
            continue
        for item in _walk_json(document):
            item_types = item.get("@type", ())
            if isinstance(item_types, str):
                item_types = (item_types,)
            if not any(str(value).casefold().endswith("product") for value in item_types):
                continue
            if not _matches_product(item.get("name"), product_name):
                continue

            offers = item.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            if not isinstance(offers, list):
                continue
            statuses = {
                str(offer.get("availability", "")).rsplit("/", 1)[-1].casefold()
                for offer in offers
                if isinstance(offer, dict)
            }
            if statuses & _AVAILABLE_SCHEMA_VALUES:
                results.append(
                    DetectorResult(Availability.AVAILABLE, "structured stock status")
                )
            elif statuses and statuses <= _UNAVAILABLE_SCHEMA_VALUES:
                results.append(
                    DetectorResult(Availability.UNAVAILABLE, "structured stock status")
                )
    return results


def _descendants(element: _Element):
    yield element
    for child in element.children:
        yield from _descendants(child)


def _product_cards(
    elements: list[_Element],
    product_name: str,
) -> list[_Element]:
    # Each element's match result and title set is computed once; recomputing them
    # per ancestor made large store pages take minutes to analyze.
    match_cache: dict[int, bool] = {}

    def matches(element: _Element) -> bool:
        key = id(element)
        if key not in match_cache:
            match_cache[key] = _matches_product(element.text(), product_name)
        return match_cache[key]

    title_cache: dict[int, frozenset[str]] = {}

    def titles_in(element: _Element) -> frozenset[str]:
        key = id(element)
        cached = title_cache.get(key)
        if cached is not None:
            return cached
        titles: set[str] = set()
        for child in element.children:
            titles |= titles_in(child)
        if matches(element) and not any(matches(child) for child in element.children):
            titles.add(_normalize(element.text()))
        result = frozenset(titles)
        title_cache[key] = result
        return result

    descendant_match_cache: dict[int, bool] = {}

    def has_matching_descendant(element: _Element) -> bool:
        key = id(element)
        if key not in descendant_match_cache:
            descendant_match_cache[key] = any(
                matches(child) or has_matching_descendant(child)
                for child in element.children
            )
        return descendant_match_cache[key]

    title_elements = [
        element
        for element in elements
        if matches(element) and not has_matching_descendant(element)
    ]
    cards = []
    for title in title_elements:
        ancestor = title.parent
        candidate = None
        for _ in range(10):
            if ancestor is None:
                break
            marker_text = " ".join(
                ancestor.attributes.get(key, "")
                for key in ("class", "id", "data-testid", "data-qa")
            )
            title_count = len(titles_in(ancestor))
            is_marked_card = bool(_PRODUCT_MARKERS.search(marker_text))
            is_structural_card = ancestor.tag in {"article", "li"}
            if (
                (is_marked_card or is_structural_card)
                and title_count <= 3
            ):
                candidate = ancestor
            elif title_count > 3:
                break
            ancestor = ancestor.parent
        if candidate is not None and not any(candidate is card for card in cards):
            cards.append(candidate)
    return cards


def _is_purchase_control(element: _Element) -> bool:
    label = " ".join(
        (
            element.text(),
            element.attributes.get("aria-label", ""),
            element.attributes.get("value", ""),
            element.attributes.get("title", ""),
        )
    ).casefold()
    return any(action in label for action in _PURCHASE_ACTIONS)


def _is_purchase_control_element(element: _Element) -> bool:
    if element.tag in _PURCHASE_CONTROL_TAGS:
        return True
    role = element.attributes.get("role", "").casefold()
    if role in {"button", "link"}:
        return True
    classes = element.attributes.get("class", "").casefold().split()
    has_action_class = any(
        class_name == "btn"
        or "button" in class_name
        or "action" in class_name
        for class_name in classes
    )
    has_action_label = any(
        action in _normalize(" ".join(element.text_parts))
        for action in _PURCHASE_ACTIONS
    )
    return (
        "tabindex" in element.attributes
        or has_action_class
        or bool(element.attributes.get("aria-label"))
        or "-" in element.tag
        or has_action_label
    )


def _is_disabled(element: _Element) -> bool:
    classes = element.attributes.get("class", "").casefold().split()
    return (
        "disabled" in element.attributes
        or element.attributes.get("aria-disabled", "").casefold() == "true"
        or element.attributes.get("data-disabled", "").casefold() == "true"
        or any("disabled" in class_name for class_name in classes)
    )


def _has_disabled_ancestor(element: _Element, boundary: _Element) -> bool:
    current: _Element | None = element
    while current is not None:
        if _is_disabled(current):
            return True
        if current is boundary:
            break
        current = current.parent
    return False


def _card_result(card: _Element) -> DetectorResult:
    descendants = list(_descendants(card))
    attributes = {
        key: value.casefold()
        for element in descendants
        for key, value in element.attributes.items()
        if key in _AVAILABILITY_ATTRIBUTES
    }
    for value in attributes.values():
        normalized_value = value.rsplit("/", 1)[-1].replace("_", "").replace("-", "")
        if normalized_value in _AVAILABLE_SCHEMA_VALUES:
            return DetectorResult(Availability.AVAILABLE, "item stock status")
        if normalized_value in _UNAVAILABLE_SCHEMA_VALUES:
            return DetectorResult(Availability.UNAVAILABLE, "item stock status")

    card_text = _normalize(card.text())
    if any(term in card_text for term in _UNAVAILABLE_TERMS):
        return DetectorResult(Availability.UNAVAILABLE, "item marked unavailable")

    for element in descendants:
        if (
            not _is_purchase_control_element(element)
            or not _is_purchase_control(element)
        ):
            continue
        if not _has_disabled_ancestor(element, card):
            return DetectorResult(Availability.AVAILABLE, "active product action")
    return DetectorResult(Availability.UNKNOWN)


def _page_matches_heading(heading: _Element, product_name: str) -> bool:
    heading_text = _normalize(heading.text())
    tokens = _normalize(product_name).split()
    return bool(tokens) and all(token in heading_text for token in tokens)


def _inside_card(element: _Element) -> bool:
    ancestor = element.parent
    while ancestor is not None:
        if ancestor.tag in {"article", "li"}:
            return True
        ancestor = ancestor.parent
    return False


def _product_page_result(
    parser: _ProductPageParser,
    product_name: str,
) -> DetectorResult | None:
    """Classify a single-product page where the buy box is outside any card."""
    headings = [element for element in parser.elements if element.tag == "h1"]
    if len(headings) != 1 or not _page_matches_heading(headings[0], product_name):
        return None

    purchase_controls = []
    unavailable_controls = []
    for element in parser.elements:
        is_button = element.tag in {"button", "input"} or (
            element.attributes.get("role", "").casefold() == "button"
        )
        if not is_button or _inside_card(element):
            continue
        if _is_purchase_control(element):
            purchase_controls.append(element)
        elif any(
            term in _normalize(element.text())
            for term in (*_UNAVAILABLE_TERMS, "auto notify", "notify me")
        ):
            unavailable_controls.append(element)

    if any(
        not _has_disabled_ancestor(element, parser.root)
        for element in purchase_controls
    ):
        return DetectorResult(Availability.AVAILABLE, "active product action")
    if purchase_controls or unavailable_controls:
        return DetectorResult(Availability.UNAVAILABLE, "product action unavailable")
    return None


def detect_product_availability(
    page_html: str,
    product_name: str,
) -> DetectorResult:
    """Classify stock only when evidence is associated with the named product."""
    if not product_name.strip():
        return DetectorResult(
            Availability.UNKNOWN,
            error_message="Enter a product name to monitor.",
        )

    parser = _ProductPageParser()
    parser.feed(page_html)
    page_text = _normalize(parser.root.text())
    if (
        "pickup location" in page_text
        and "please select an address" in page_text
    ):
        return DetectorResult(
            Availability.UNKNOWN,
            error_message=(
                "The store page requires a pickup location. Use an ordering URL "
                "that opens the selected store before monitoring its products."
            ),
        )

    structured_results = _schema_product_results(parser.json_ld_blocks, product_name)
    if structured_results:
        if any(result.availability == Availability.AVAILABLE for result in structured_results):
            return next(
                result
                for result in structured_results
                if result.availability == Availability.AVAILABLE
            )
        return structured_results[0]

    cards = _product_cards(parser.elements, product_name)
    results = [_card_result(card) for card in cards]
    if not any(result.availability != Availability.UNKNOWN for result in results):
        page_result = _product_page_result(parser, product_name)
        if page_result is not None:
            return page_result
    if not cards:
        return DetectorResult(
            Availability.UNKNOWN,
            error_message=f"Could not identify {product_name!r} on this store page.",
        )

    if any(result.availability == Availability.UNAVAILABLE for result in results):
        return next(
            result
            for result in results
            if result.availability == Availability.UNAVAILABLE
        )
    if any(result.availability == Availability.AVAILABLE for result in results):
        return next(
            result
            for result in results
            if result.availability == Availability.AVAILABLE
        )
    return DetectorResult(
        Availability.UNKNOWN,
        error_message=(
            f"Found {product_name!r}, but the page did not expose clear stock status."
        ),
        product_found=True,
    )
