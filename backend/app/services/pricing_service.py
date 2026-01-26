"""
Pricing service for calculating domestic and overseas quotes.
"""

from typing import Optional
from ..data.pricing import (
    DOMESTIC_QUANTITY_BREAKS,
    OVERSEAS_QUANTITY_BREAKS,
    DOMESTIC_BLANK_PRICES,
    DOMESTIC_STYLES,
    DOMESTIC_FRONT_DECORATION_PRICES,
    DOMESTIC_ADDITIONAL_DECORATION_PRICES,
    DOMESTIC_RUSH_FEES,
    DOMESTIC_ADDONS,
    DOMESTIC_ADDITIONAL_CHARGES,
    OVERSEAS_HAT_TYPES,
    OVERSEAS_FRONT_DECORATION_PRICES,
    OVERSEAS_SIDE_DECORATION_PRICES,
    OVERSEAS_BACK_DECORATION_PRICES,
    OVERSEAS_VISOR_DECORATION_PRICES,
    OVERSEAS_DESIGN_ADDONS,
    OVERSEAS_ACCESSORIES,
    OVERSEAS_SHIPPING,
)


def get_quantity_break(quantity: int, breaks: list[int]) -> int:
    """Find the applicable quantity break for a given quantity."""
    applicable_break = breaks[0]
    for brk in breaks:
        if quantity >= brk:
            applicable_break = brk
        else:
            break
    return applicable_break


def get_price_at_quantity(prices: dict, quantity: int, breaks: list[int]) -> float:
    """Get the price for a specific quantity from a price table."""
    qty_break = get_quantity_break(quantity, breaks)
    return prices.get(qty_break, 0)


def calculate_domestic_quote(
    style_number: str,
    quantity: int,
    front_decoration: Optional[str] = None,
    left_decoration: Optional[str] = None,
    right_decoration: Optional[str] = None,
    back_decoration: Optional[str] = None,
    shipping_speed: str = "Standard (5-7 Production Days)",
    include_rope: bool = False,
    num_dst_files: int = 1,
) -> dict:
    """
    Calculate a domestic quote.

    Returns a dict with price breakdowns at each quantity break.
    """
    if style_number not in DOMESTIC_BLANK_PRICES:
        raise ValueError(f"Unknown style number: {style_number}")

    style_info = DOMESTIC_STYLES.get(style_number, {})
    results = []

    for qty_break in DOMESTIC_QUANTITY_BREAKS:
        if quantity < qty_break and qty_break != DOMESTIC_QUANTITY_BREAKS[0]:
            continue

        # Base hat price
        blank_price = DOMESTIC_BLANK_PRICES[style_number].get(qty_break, 0)

        # Front decoration
        front_deco_price = 0
        if front_decoration and front_decoration in DOMESTIC_FRONT_DECORATION_PRICES:
            front_deco_price = DOMESTIC_FRONT_DECORATION_PRICES[front_decoration].get(qty_break, 0)

        # Additional locations
        left_deco_price = 0
        if left_decoration and left_decoration in DOMESTIC_ADDITIONAL_DECORATION_PRICES:
            left_deco_price = DOMESTIC_ADDITIONAL_DECORATION_PRICES[left_decoration].get(qty_break, 0)

        right_deco_price = 0
        if right_decoration and right_decoration in DOMESTIC_ADDITIONAL_DECORATION_PRICES:
            right_deco_price = DOMESTIC_ADDITIONAL_DECORATION_PRICES[right_decoration].get(qty_break, 0)

        back_deco_price = 0
        if back_decoration and back_decoration in DOMESTIC_ADDITIONAL_DECORATION_PRICES:
            back_deco_price = DOMESTIC_ADDITIONAL_DECORATION_PRICES[back_decoration].get(qty_break, 0)

        # Rush fee
        rush_fee = DOMESTIC_RUSH_FEES.get(shipping_speed, 0)

        # Rope add-on
        rope_price = DOMESTIC_ADDONS["Rope"] if include_rope else 0

        # Per-piece total
        per_piece = blank_price + front_deco_price + left_deco_price + right_deco_price + back_deco_price + rush_fee + rope_price

        # One-time charges
        digitizing_fee = DOMESTIC_ADDITIONAL_CHARGES["Embroidery Digitizing Fee"].get(qty_break, 0) * num_dst_files

        # Total
        total = (per_piece * quantity) + digitizing_fee

        results.append({
            "quantity_break": qty_break,
            "blank_price": blank_price,
            "front_decoration_price": front_deco_price,
            "left_decoration_price": left_deco_price,
            "right_decoration_price": right_deco_price,
            "back_decoration_price": back_deco_price,
            "rush_fee": rush_fee,
            "rope_price": rope_price,
            "per_piece_price": round(per_piece, 2),
            "digitizing_fee": digitizing_fee,
            "subtotal": round(per_piece * quantity, 2),
            "total": round(total, 2),
        })

    return {
        "quote_type": "domestic",
        "style_number": style_number,
        "style_name": style_info.get("name", ""),
        "collection": style_info.get("collection", ""),
        "quantity": quantity,
        "front_decoration": front_decoration,
        "left_decoration": left_decoration,
        "right_decoration": right_decoration,
        "back_decoration": back_decoration,
        "shipping_speed": shipping_speed,
        "include_rope": include_rope,
        "price_breaks": results,
    }


def calculate_overseas_quote(
    hat_type: str,
    quantity: int,
    front_decoration: Optional[str] = None,
    left_decoration: Optional[str] = None,
    right_decoration: Optional[str] = None,
    back_decoration: Optional[str] = None,
    visor_decoration: Optional[str] = None,
    design_addons: Optional[list[str]] = None,
    accessories: Optional[list[str]] = None,
    shipping_method: str = "FOB CA",
) -> dict:
    """
    Calculate an overseas quote.

    Returns a dict with price breakdowns at each quantity break.
    When an option doesn't meet MOQ at a quantity break, that break's
    per_piece_price will be None (indicating "Does not meet MOQ").
    """
    if hat_type not in OVERSEAS_HAT_TYPES:
        raise ValueError(f"Unknown hat type: {hat_type}")

    design_addons = design_addons or []
    accessories = accessories or []

    results = []

    # Always return all quantity breaks for overseas quotes
    for qty_break in OVERSEAS_QUANTITY_BREAKS:
        # Track if any selected option doesn't meet MOQ at this quantity
        meets_moq = True

        # Base hat price
        hat_prices = OVERSEAS_HAT_TYPES[hat_type]["prices"]
        blank_price = hat_prices.get(qty_break, 0)

        # Front decoration
        front_deco_price = 0
        if front_decoration and front_decoration in OVERSEAS_FRONT_DECORATION_PRICES:
            price_dict = OVERSEAS_FRONT_DECORATION_PRICES[front_decoration]
            if qty_break in price_dict:
                front_deco_price = price_dict[qty_break]
            else:
                meets_moq = False

        # Side decorations
        left_deco_price = 0
        if left_decoration and left_decoration in OVERSEAS_SIDE_DECORATION_PRICES:
            price_dict = OVERSEAS_SIDE_DECORATION_PRICES[left_decoration]
            if qty_break in price_dict:
                left_deco_price = price_dict[qty_break]
            else:
                meets_moq = False

        right_deco_price = 0
        if right_decoration and right_decoration in OVERSEAS_SIDE_DECORATION_PRICES:
            price_dict = OVERSEAS_SIDE_DECORATION_PRICES[right_decoration]
            if qty_break in price_dict:
                right_deco_price = price_dict[qty_break]
            else:
                meets_moq = False

        # Back decoration
        back_deco_price = 0
        if back_decoration and back_decoration in OVERSEAS_BACK_DECORATION_PRICES:
            price_dict = OVERSEAS_BACK_DECORATION_PRICES[back_decoration]
            if qty_break in price_dict:
                back_deco_price = price_dict[qty_break]
            else:
                meets_moq = False

        # Visor decoration
        visor_deco_price = 0
        if visor_decoration and visor_decoration in OVERSEAS_VISOR_DECORATION_PRICES:
            price_dict = OVERSEAS_VISOR_DECORATION_PRICES[visor_decoration]
            if qty_break in price_dict:
                visor_deco_price = price_dict[qty_break]
            else:
                meets_moq = False

        # Design add-ons
        addons_price = 0
        for addon in design_addons:
            if addon in OVERSEAS_DESIGN_ADDONS:
                price_dict = OVERSEAS_DESIGN_ADDONS[addon]
                if qty_break in price_dict:
                    addons_price += price_dict[qty_break]
                else:
                    meets_moq = False

        # Accessories
        accessories_price = 0
        for accessory in accessories:
            if accessory in OVERSEAS_ACCESSORIES:
                price_dict = OVERSEAS_ACCESSORIES[accessory]
                if qty_break in price_dict:
                    accessories_price += price_dict[qty_break]
                else:
                    meets_moq = False

        # Shipping
        shipping_price = 0
        if shipping_method in OVERSEAS_SHIPPING:
            shipping_price = OVERSEAS_SHIPPING[shipping_method].get(qty_break, 0)

        # If any option doesn't meet MOQ, mark this quantity break as invalid
        if meets_moq:
            hat_subtotal = blank_price + front_deco_price + left_deco_price + right_deco_price + back_deco_price + visor_deco_price + addons_price + accessories_price
            per_piece_with_shipping = hat_subtotal + shipping_price
            total = per_piece_with_shipping * quantity

            results.append({
                "quantity_break": qty_break,
                "blank_price": round(blank_price, 2),
                "front_decoration_price": round(front_deco_price, 2),
                "left_decoration_price": round(left_deco_price, 2),
                "right_decoration_price": round(right_deco_price, 2),
                "back_decoration_price": round(back_deco_price, 2),
                "visor_decoration_price": round(visor_deco_price, 2),
                "addons_price": round(addons_price, 2),
                "accessories_price": round(accessories_price, 2),
                "hat_subtotal": round(hat_subtotal, 2),
                "shipping_price": round(shipping_price, 2),
                "per_piece_price": round(per_piece_with_shipping, 2),
                "total": round(total, 2),
            })
        else:
            # Option doesn't meet MOQ at this quantity break
            results.append({
                "quantity_break": qty_break,
                "blank_price": None,
                "front_decoration_price": None,
                "left_decoration_price": None,
                "right_decoration_price": None,
                "back_decoration_price": None,
                "visor_decoration_price": None,
                "addons_price": None,
                "accessories_price": None,
                "hat_subtotal": None,
                "shipping_price": None,
                "per_piece_price": None,
                "total": None,
            })

    return {
        "quote_type": "overseas",
        "hat_type": hat_type,
        "quantity": quantity,
        "front_decoration": front_decoration,
        "left_decoration": left_decoration,
        "right_decoration": right_decoration,
        "back_decoration": back_decoration,
        "visor_decoration": visor_decoration,
        "design_addons": design_addons,
        "accessories": accessories,
        "shipping_method": shipping_method,
        "price_breaks": results,
    }
