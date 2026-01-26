"""AI-related routes for brand scraping and design generation."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.gemini_service import scrape_brand_info
from ..utils.dependencies import require_auth

router = APIRouter(prefix="/ai", tags=["AI"])


class BrandScrapeRequest(BaseModel):
    brand_name: Optional[str] = None
    brand_url: Optional[str] = None


class BrandScrapeResponse(BaseModel):
    success: bool
    data: dict
    message: Optional[str] = None


@router.post("/brand-scrape", response_model=BrandScrapeResponse)
async def scrape_brand(
    request: BrandScrapeRequest,
    user=Depends(require_auth),
):
    """
    Scrape brand information using AI.

    Uses Gemini to analyze brand name and/or website to extract
    brand colors, style, and design recommendations.
    """
    if not request.brand_name and not request.brand_url:
        raise HTTPException(
            status_code=400,
            detail="Either brand_name or brand_url must be provided",
        )

    try:
        # Scrape brand info
        scraped_data = await scrape_brand_info(
            brand_name=request.brand_name,
            brand_url=request.brand_url,
        )

        # Check for errors
        if "error" in scraped_data:
            return BrandScrapeResponse(
                success=False,
                data=scraped_data,
                message=scraped_data.get("error"),
            )

        return BrandScrapeResponse(
            success=True,
            data=scraped_data,
            message="Brand information scraped successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape brand information: {str(e)}",
        )
