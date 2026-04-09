"""Social Media Manager API — proxies Vertex AI for image + caption generation."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..services.gemini_service import generate_design_image, init_gemini

router = APIRouter(prefix="/social", tags=["social-media"])


class ImageGenRequest(BaseModel):
    prompt: str


class CaptionGenRequest(BaseModel):
    context: str
    funnel: str = "upper"
    audience: str = "dtc"
    platform: str = "instagram"
    tone: str = "bold & confident"


@router.post("/generate-image")
async def generate_image(req: ImageGenRequest):
    """Generate an image via Vertex AI (Nano Banana Pro)."""
    result = await generate_design_image(prompt=req.prompt)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Image generation failed"))
    return {
        "image_data": result["image_data"],
        "mime_type": result.get("mime_type", "image/png"),
    }


@router.post("/generate-caption")
async def generate_caption(req: CaptionGenRequest):
    """Generate social media captions via Gemini."""
    import google.generativeai as genai
    from ..config import get_settings

    settings = get_settings()
    if not settings.google_gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    init_gemini()

    funnel_desc = {
        "upper": "Upper Funnel (Awareness): Brand storytelling, aspirational, no hard sells. Focus on reach.",
        "mid": "Mid Funnel (Consideration): Product features, social proof, behind-the-scenes. Build trust.",
        "lower": "Lower Funnel (Conversion): Offers, CTAs, urgency, limited drops. Drive action.",
    }.get(req.funnel, req.funnel)

    audience_desc = {
        "dtc": "Direct to Consumer: Lifestyle-focused, trend-driven, personal expression.",
        "promo": "Promotional Distributors: B2B tone, volume pricing, customization, turnaround times.",
        "golf": "Golf Market: Performance features, course-ready style, tournament/event context.",
    }.get(req.audience, req.audience)

    platform_desc = {
        "instagram": "Instagram: Emoji-friendly, include hashtags, visual-first, max 2200 chars.",
        "facebook": "Facebook: Slightly longer form, community-focused, shareable.",
        "youtube": "YouTube: Description-style, keyword-rich, structured with bullet points.",
        "linkedin": "LinkedIn: Professional tone, industry insights, thought leadership.",
    }.get(req.platform, req.platform)

    system_prompt = f"""You are a social media copywriter for King Cap, a premium headwear company founded in 1991. Based in the USA with domestic and overseas production.

Brand: Premium caps, trucker hats, snapbacks, golf caps. Known for quality, custom decoration (3D embroidery, patches, screen print, sublimation, laser cut). Brand colors: Gold (#C8994A), Black. Tagline essence: "The Crown You Deserve."

PARAMETERS:
- {funnel_desc}
- {audience_desc}
- {platform_desc}
- Tone: {req.tone}

Generate exactly 2 distinct caption variations for the topic provided. Separate them with: |||
Output ONLY the raw captions. No labels, no explanations."""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_prompt)
        response = model.generate_content(f"Write captions about: {req.context}")
        text = response.text.strip()
        captions = [s.strip() for s in text.split("|||") if s.strip()]
        return {"captions": captions}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
