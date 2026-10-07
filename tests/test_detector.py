import json

import pytest

from appointment_monitor.detector import (
    Availability,
    detect_product_availability,
)


def test_structured_product_stock_status_matches_the_named_product():
    page = f"""
    <script type="application/ld+json">{json.dumps([
        {
            "@type": "Product",
            "name": "Chocolate Iced Doughnut",
            "offers": {"availability": "https://schema.org/OutOfStock"},
        },
        {
            "@type": "Product",
            "name": "Original Glazed Doughnut",
            "offers": {"availability": "https://schema.org/InStock"},
        },
    ])}</script>
    """

    result = detect_product_availability(page, "Original Glazed")

    assert result.availability == Availability.AVAILABLE
    assert result.evidence == "structured stock status"


def test_structured_product_reports_out_of_stock():
    page = """
    <script type="application/ld+json">
    {"@type":"Product","name":"Original Glazed Dozen",
     "offers":{"availability":"https://schema.org/OutOfStock"}}
    </script>
    """

    result = detect_product_availability(page, "Original Glazed Dozen")

    assert result.availability == Availability.UNAVAILABLE


def test_product_card_checks_only_the_matching_item():
    page = """
    <article class="product-card">
      <h2>Chocolate Iced Doughnut</h2>
      <p>Sold out</p>
      <button disabled>Add to order</button>
    </article>
    <article class="product-card">
      <h2>Original Glazed Doughnut</h2>
      <button>Add to order</button>
    </article>
    """

    result = detect_product_availability(page, "Original Glazed Doughnut")

    assert result.availability == Availability.AVAILABLE
    assert result.evidence == "active product action"


def test_krispy_kreme_customize_action_marks_the_item_available():
    page = """
    <article class="menu-item-card">
      <img alt="Pumpkin Spice Latte">
      <h2>PUMPKIN SPICE LATTE</h2>
      <span>$4.55 | 370 cal</span>
      <button>CUSTOMIZE</button>
    </article>
    """

    result = detect_product_availability(page, "Pumpkin Spice Latte")

    assert result.availability == Availability.AVAILABLE
    assert result.evidence == "active product action"


@pytest.mark.parametrize(
    "control",
    (
        '<a href="/customize">CUSTOMIZE</a>',
        '<div role="button" tabindex="0">CUSTOMIZE</div>',
        '<div class="btn">CUSTOMIZE</div>',
        '<span>CUSTOMIZE</span>',
        '<kk-button>CUSTOMIZE</kk-button>',
    ),
)
def test_customize_action_is_detected_when_rendered_as_link_or_aria_button(control):
    page = f"""
    <article class="menu-item-card">
      <h2>PUMPKIN SPICE LATTE</h2>
      {control}
    </article>
    """

    result = detect_product_availability(page, "Pumpkin Spice Latte")

    assert result.availability == Availability.AVAILABLE
    assert result.evidence == "active product action"


def test_krispy_kreme_out_of_stock_badge_takes_precedence_over_disabled_order_button():
    page = """
    <div class="product-card">
      <div class="product-details">
        <img alt="Autumn Seasonal Dozen">
        <h2>AUTUMN SEASONAL DOZEN</h2>
        <span>$25.99</span>
        <button disabled>ADD TO ORDER</button>
      </div>
      <span class="stock-badge">OUT OF STOCK</span>
    </div>
    """

    result = detect_product_availability(page, "AUTUMN SEASONAL DOZEN")

    assert result.availability == Availability.UNAVAILABLE
    assert result.evidence == "item marked unavailable"


def test_sold_out_wins_over_active_purchase_control_inside_nested_product_card():
    page = """
    <div class="product-card">
      <div class="product-content">
        <h2>NVIDIA GeForce RTX 5090 Founders Edition</h2>
        <button>Add to cart</button>
      </div>
      <div class="fulfillment">
        <button>Sold Out</button>
      </div>
    </div>
    <div class="product-card">
      <h2>Another Graphics Card</h2>
      <button>Add to cart</button>
    </div>
    """

    result = detect_product_availability(
        page,
        "NVIDIA GeForce RTX 5090 Founders Edition",
    )

    assert result.availability == Availability.UNAVAILABLE
    assert result.evidence == "item marked unavailable"


def test_disabled_customize_link_does_not_mark_product_available():
    page = """
    <article class="menu-item-card">
      <h2>PUMPKIN SPICE LATTE</h2>
      <a class="button disabled" aria-disabled="true">CUSTOMIZE</a>
    </article>
    """

    result = detect_product_availability(page, "Pumpkin Spice Latte")

    assert result.availability == Availability.UNKNOWN


def test_disabled_styled_parent_does_not_mark_customize_as_available():
    page = """
    <article class="menu-item-card">
      <h2>PUMPKIN SPICE LATTE</h2>
      <div class="product-button disabled"><span>CUSTOMIZE</span></div>
    </article>
    """

    result = detect_product_availability(page, "Pumpkin Spice Latte")

    assert result.availability == Availability.UNKNOWN


def test_product_card_reports_sold_out_even_if_unrelated_page_has_order_button():
    page = """
    <button>Order now</button>
    <article class="product-card">
      <h2>Original Glazed Doughnut</h2>
      <p>Sold out</p>
      <button disabled>Add to order</button>
    </article>
    """

    result = detect_product_availability(page, "Original Glazed Doughnut")

    assert result.availability == Availability.UNAVAILABLE


def test_unrelated_available_text_does_not_mark_product_available():
    page = """
    <p>Many products are available today.</p>
    <article class="product-card">
      <h2>Original Glazed Doughnut</h2>
      <button disabled>Add to order</button>
    </article>
    """

    result = detect_product_availability(page, "Original Glazed Doughnut")

    assert result.availability == Availability.UNKNOWN
    assert "clear stock status" in result.error_message


def test_page_without_the_named_product_is_unknown():
    result = detect_product_availability(
        "<p>Original Glazed is available</p>",
        "Chocolate Iced Doughnut",
    )

    assert result.availability == Availability.UNKNOWN
    assert "Could not identify" in result.error_message


def test_nested_product_markup_does_not_raise_recursion_error():
    page = """
    <div class="page">
      <div class="search-results">
        <div class="product-card">
          <div class="product-title">
            <span>MSI - Aegis ZS2 Gaming Desktop</span>
          </div>
        </div>
      </div>
    </div>
    """

    result = detect_product_availability(
        page,
        "MSI - Aegis ZS2 Gaming Desktop",
    )

    assert result.availability == Availability.UNKNOWN
    assert "clear stock status" in result.error_message


def test_visible_text_without_item_stock_data_is_unknown():
    page = """
    <script>Original Glazed Doughnut is available</script>
    <article class="product-card"><h2>Original Glazed Doughnut</h2></article>
    """

    result = detect_product_availability(page, "Original Glazed Doughnut")

    assert result.availability == Availability.UNKNOWN


def test_location_prompt_reports_that_store_selection_is_required():
    page = """
    <div role="dialog">
      <button>
        <p>PICKUP LOCATION</p>
        <p>Please Select An Address</p>
      </button>
      <button disabled>Start pickup order</button>
    </div>
    <article class="product-card">
      <h2>PUMPKIN SPICE LATTE</h2>
      <button>CUSTOMIZE</button>
    </article>
    """

    result = detect_product_availability(page, "Pumpkin Spice Latte")

    assert result.availability == Availability.UNKNOWN
    assert "requires a pickup location" in result.error_message


def test_empty_product_name_returns_clear_error():
    result = detect_product_availability("<p>Product</p>", " ")

    assert result.availability == Availability.UNKNOWN
    assert result.error_message == "Enter a product name to monitor."


NEWEGG_STYLE_PAGE = """
<html><body>
<ol class="breadcrumb"><li><a>Home</a></li><li><a>GPUs</a></li></ol>
<h1 class="product-title">MSI Ventus GeForce RTX 5070 Ti 16G VENTUS 3X OC</h1>
<div id="ProductBuy" class="product-buy">
  <input class="qty-box-input" aria-label="Qty" value="1"/>
  <button class="btn btn-primary btn-wide"
    title="Add MSI Ventus GeForce RTX 5070 Ti to cart">Add to cart</button>
</div>
<ul><li class="item-cell"><a>Other Card</a>
  <button class="btn">Add to cart</button></li></ul>
</body></html>
"""


def test_single_product_page_with_buy_box_outside_a_card_is_available():
    result = detect_product_availability(NEWEGG_STYLE_PAGE, "MSI RTX 5070 Ti")

    assert result.availability == Availability.AVAILABLE


def test_single_product_page_without_active_buy_button_is_unavailable():
    page = NEWEGG_STYLE_PAGE.replace(
        '<button class="btn btn-primary btn-wide"\n    title="Add MSI Ventus GeForce RTX 5070 Ti to cart">Add to cart</button>',
        '<button class="btn">Auto Notify</button>',
    )

    result = detect_product_availability(page, "MSI RTX 5070 Ti")

    assert result.availability == Availability.UNAVAILABLE


def test_single_product_page_ignores_related_item_buttons():
    page = NEWEGG_STYLE_PAGE.replace("Add to cart</button>\n</div>", "Sold out</button>\n</div>", 1)
    page = page.replace('title="Add MSI Ventus GeForce RTX 5070 Ti to cart"', "")

    result = detect_product_availability(page, "MSI RTX 5070 Ti")

    assert result.availability == Availability.UNAVAILABLE


def test_page_mode_requires_matching_heading():
    result = detect_product_availability(NEWEGG_STYLE_PAGE, "Radeon RX 9070")

    assert result.availability == Availability.UNKNOWN
