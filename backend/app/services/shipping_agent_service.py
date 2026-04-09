"""Shipping logistics AI agent powered by Anthropic Claude.

Analyzes pending overseas orders, shipping rates, and delivery constraints
to recommend optimal shipment batches (ocean FCL/LCL vs air freight).
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import anthropic
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.shipping import ShipmentAnalysis, ShipmentBatch, ShippingRate
from . import bc_service

logger = logging.getLogger(__name__)
settings = get_settings()


SYSTEM_PROMPT = """You are a shipping logistics analyst for King Cap, a B2B wholesale hat company.

King Cap manufactures custom hats in Bangladesh (Chittagong port) and ships to Los Angeles, California.

Your job is to analyze pending overseas orders and recommend the most cost-effective shipping strategy by batching orders together optimally.

Key logistics facts:
- Ocean freight (Chittagong → LA): 28-31 days port-to-port, plus customs/port buffer
- Air freight (Chittagong → LA): 2-8 days, significantly more expensive
- FCL (Full Container Load) is cost-effective when volume exceeds ~13-15 CBM
- 20ft container: ~33 CBM capacity, ~28,000 kg max
- 40ft container: ~67 CBM capacity, ~28,000 kg max
- LCL (Less Than Container Load): charged per CBM, adds 2-5 days for consolidation
- Batching multiple orders into one shipment can save 20-40% per unit cost
- Always account for buffer days (customs clearance, port handling, local delivery)

When recommending batches:
1. Group orders that can ship together based on delivery deadlines
2. Prefer FCL when combined volume justifies it (>13 CBM)
3. Use air freight only for urgent orders that can't meet deadlines via ocean
4. Consider holding orders 3-7 days to consolidate for FCL savings
5. Calculate estimated costs using the provided rate data
6. Explain your reasoning for each batch

You MUST respond with valid JSON only, no markdown fences. Use this exact schema:
{
  "batches": [
    {
      "batch_label": "descriptive name",
      "recommended_method": "ocean_fcl" | "ocean_fcl_40" | "ocean_lcl" | "air_freight",
      "bc_order_numbers": ["SO-...", "SO-..."],
      "order_count": 2,
      "total_volume_cbm": 15.5,
      "total_weight_kg": 372.0,
      "estimated_shipping_cost_cents": 250000,
      "recommended_ship_date": "2026-03-15",
      "estimated_arrival_date": "2026-04-15",
      "latest_delivery_deadline": "2026-04-20",
      "reasoning": "explanation of why these orders are batched this way"
    }
  ],
  "summary": "Overall analysis summary with key recommendations and estimated total savings",
  "total_estimated_cost_cents": 350000,
  "alternative_cost_cents": 480000,
  "estimated_savings_cents": 130000
}"""


def _build_analysis_prompt(
    orders: List[Dict[str, Any]],
    rates: List[Dict[str, Any]],
    current_date: str,
) -> str:
    """Build the user message for Claude with order data and rate cards."""

    rates_text = "CURRENT SHIPPING RATES:\n"
    for r in rates:
        cost_dollars = r["cost_per_unit"] / 100
        rates_text += (
            f"- {r['label']}: ${cost_dollars:.2f} per {r['unit_type']} | "
            f"Transit: {r['transit_days_min']}-{r['transit_days_max']} days | "
            f"Buffer: {r['buffer_days']} days"
        )
        if r.get("min_volume_cbm") is not None:
            rates_text += f" | Volume: {r['min_volume_cbm']}-{r['max_volume_cbm']} CBM"
        rates_text += "\n"

    orders_text = f"\nPENDING OVERSEAS ORDERS (as of {current_date}):\n"
    total_qty = 0
    total_vol = 0.0
    total_wt = 0.0

    for o in orders:
        orders_text += (
            f"\n  Order: {o['bc_order_number']}\n"
            f"    Customer: {o['customer_name']}\n"
            f"    Order Date: {o.get('order_date', 'N/A')}\n"
            f"    Delivery Deadline: {o.get('requested_delivery_date', 'N/A')}\n"
            f"    Total Qty: {o['total_quantity']} hats\n"
            f"    Est. Volume: {o['estimated_volume_cbm']} CBM\n"
            f"    Est. Weight: {o['estimated_weight_kg']} kg\n"
            f"    Value: ${o.get('total_amount', 0):,.2f}\n"
        )
        if o.get("line_items"):
            orders_text += "    Items:\n"
            for li in o["line_items"]:
                orders_text += (
                    f"      - {li['description']}: {li['quantity']} units"
                    f" @ ${li.get('unit_price', 0):.2f}\n"
                )
        total_qty += o["total_quantity"]
        total_vol += o["estimated_volume_cbm"]
        total_wt += o["estimated_weight_kg"]

    summary = (
        f"\nTOTALS: {len(orders)} orders | {total_qty:,} hats | "
        f"{total_vol:.1f} CBM | {total_wt:.1f} kg\n"
    )

    return rates_text + orders_text + summary + (
        "\nAnalyze these orders and recommend optimal shipping batches. "
        "Consider delivery deadlines, cost optimization through batching, "
        "and the trade-off between ocean and air freight. "
        "Respond with JSON only."
    )


def _parse_ai_response(text: str) -> Dict[str, Any]:
    """Extract and validate JSON from Claude's response."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip().rstrip("`")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from AI response: {text[:200]}")


async def run_analysis(
    db: Session,
    triggered_by: str = "admin",
    analysis_type: str = "full",
    use_mock: bool = False,
) -> ShipmentAnalysis:
    """Run a full shipping logistics analysis.

    Args:
        db: Database session
        triggered_by: Who triggered the analysis
        analysis_type: "full" or "quick"
        use_mock: If True, use mock data instead of live BC orders
    """
    # Create analysis record
    analysis = ShipmentAnalysis(
        triggered_by=triggered_by,
        analysis_type=analysis_type,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        # Fetch orders
        if use_mock or not settings.bc_client_id:
            orders = bc_service.generate_mock_orders()
        else:
            orders = await bc_service.get_pending_overseas_orders()

        if not orders:
            analysis.status = "completed"
            analysis.completed_at = datetime.utcnow()
            analysis.recommendation_summary = "No pending overseas orders found."
            analysis.total_orders_analyzed = 0
            db.commit()
            return analysis

        # Fetch active shipping rates
        rate_records = db.query(ShippingRate).filter(
            ShippingRate.is_active == True  # noqa: E712
        ).all()

        rates = [
            {
                "method": r.method,
                "label": r.label,
                "cost_per_unit": r.cost_per_unit,
                "unit_type": r.unit_type,
                "min_volume_cbm": r.min_volume_cbm,
                "max_volume_cbm": r.max_volume_cbm,
                "transit_days_min": r.transit_days_min,
                "transit_days_max": r.transit_days_max,
                "buffer_days": r.buffer_days,
            }
            for r in rate_records
        ]

        # Store input summary
        analysis.input_summary = json.dumps({
            "order_count": len(orders),
            "total_quantity": sum(o["total_quantity"] for o in orders),
            "total_volume_cbm": round(sum(o["estimated_volume_cbm"] for o in orders), 2),
            "total_weight_kg": round(sum(o["estimated_weight_kg"] for o in orders), 2),
            "rate_count": len(rates),
        })
        analysis.total_orders_analyzed = len(orders)
        analysis.total_volume_cbm = sum(o["estimated_volume_cbm"] for o in orders)
        analysis.total_weight_kg = sum(o["estimated_weight_kg"] for o in orders)
        db.commit()

        # Build prompt and call Claude
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        user_prompt = _build_analysis_prompt(orders, rates, current_date)

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_response = message.content[0].text
        analysis.raw_ai_response = raw_response

        # Parse response
        result = _parse_ai_response(raw_response)

        analysis.recommendation_summary = result.get("summary", "")
        analysis.estimated_savings_cents = result.get("estimated_savings_cents")

        # Create batch records
        for i, batch_data in enumerate(result.get("batches", [])):
            ship_date = None
            arrival_date = None
            deadline_date = None

            if batch_data.get("recommended_ship_date"):
                try:
                    ship_date = datetime.fromisoformat(batch_data["recommended_ship_date"])
                except (ValueError, TypeError):
                    pass
            if batch_data.get("estimated_arrival_date"):
                try:
                    arrival_date = datetime.fromisoformat(batch_data["estimated_arrival_date"])
                except (ValueError, TypeError):
                    pass
            if batch_data.get("latest_delivery_deadline"):
                try:
                    deadline_date = datetime.fromisoformat(batch_data["latest_delivery_deadline"])
                except (ValueError, TypeError):
                    pass

            batch = ShipmentBatch(
                analysis_id=analysis.id,
                batch_number=i + 1,
                batch_label=batch_data.get("batch_label", f"Batch {i + 1}"),
                recommended_method=batch_data.get("recommended_method", "ocean_lcl"),
                total_volume_cbm=batch_data.get("total_volume_cbm", 0),
                total_weight_kg=batch_data.get("total_weight_kg", 0),
                estimated_shipping_cost=batch_data.get("estimated_shipping_cost_cents", 0),
                recommended_ship_date=ship_date,
                estimated_arrival_date=arrival_date,
                latest_delivery_deadline=deadline_date,
                bc_order_numbers=json.dumps(batch_data.get("bc_order_numbers", [])),
                order_count=batch_data.get("order_count", 0),
                reasoning=batch_data.get("reasoning", ""),
            )
            db.add(batch)

        analysis.status = "completed"
        analysis.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(analysis)
        return analysis

    except Exception as e:
        logger.exception("Shipping analysis failed")
        analysis.status = "failed"
        analysis.error_message = str(e)
        analysis.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(analysis)
        return analysis
