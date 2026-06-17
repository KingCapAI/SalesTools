"""AI-related routes for brand scraping and design generation."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.gemini_service import scrape_brand_info
from ..services.storage_service import read_file_bytes
from ..utils.dependencies import require_auth

router = APIRouter(prefix="/ai", tags=["AI"])


class BrandScrapeRequest(BaseModel):
    brand_name: Optional[str] = None
    brand_url: Optional[str] = None
    logo_path: Optional[str] = None  # If set, used as the authoritative source for primary colors


class BrandScrapeResponse(BaseModel):
    success: bool
    data: dict
    message: Optional[str] = None


def _mime_from_path(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/png"


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

    # If a logo was provided, load its bytes so the scraper can run k-means.
    logo_bytes: Optional[bytes] = None
    logo_mime: Optional[str] = None
    if request.logo_path:
        try:
            logo_bytes = await read_file_bytes(request.logo_path)
            if logo_bytes:
                logo_mime = _mime_from_path(request.logo_path)
        except Exception as e:
            print(f"[BrandScrape] Could not read logo {request.logo_path}: {e}")

    try:
        # Scrape brand info
        scraped_data = await scrape_brand_info(
            brand_name=request.brand_name,
            brand_url=request.brand_url,
            logo_bytes=logo_bytes,
            logo_mime=logo_mime,
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
