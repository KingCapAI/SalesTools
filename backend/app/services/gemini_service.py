"""Gemini AI service for brand scraping and image generation."""

import base64
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

import google.generativeai as genai
from PIL import Image
import io

from ..config import get_settings
from ..utils.prompt_builder import build_design_prompt, build_revision_prompt

settings = get_settings()

# Retry configuration for 503 errors
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def init_gemini():
    """Initialize the Gemini client."""
    if settings.google_gemini_api_key:
        genai.configure(api_key=settings.google_gemini_api_key)


async def scrape_brand_info(
    brand_name: Optional[str] = None,
    brand_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use Gemini to scrape and analyze brand information.

    Args:
        brand_name: The name of the brand
        brand_url: The brand's website URL

    Returns:
        Dictionary containing brand colors, style, and guidelines
    """
    init_gemini()

    prompt = f"""Analyze the brand and provide comprehensive brand guidelines information.

Brand Name: {brand_name or 'Not provided'}
Brand Website: {brand_url or 'Not provided'}

Please provide the following information in a structured format:
1. Primary brand colors (provide hex codes if possible)
2. Secondary/accent colors
3. Brand style/personality (e.g., modern, traditional, playful, professional)
4. Typography style recommendations
5. Design aesthetic (minimalist, bold, elegant, etc.)
6. Target audience characteristics
7. Industry/sector
8. Any notable brand elements or motifs

If you cannot find specific information, provide reasonable suggestions based on the brand name and any available context.

Respond in JSON format with the following structure:
{{
    "primary_colors": ["#hex1", "#hex2"],
    "secondary_colors": ["#hex1", "#hex2"],
    "brand_style": "description of brand style",
    "typography": "recommended font styles",
    "design_aesthetic": "description of design aesthetic",
    "target_audience": "description of target audience",
    "industry": "industry/sector",
    "brand_elements": ["element1", "element2"],
    "recommendations": "additional recommendations for hat design"
}}"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        # Try to parse as JSON
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        import json

        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            # Return raw text if JSON parsing fails
            return {
                "raw_response": response.text,
                "brand_style": "Unable to parse structured response",
                "recommendations": response.text,
            }

    except Exception as e:
        return {
            "error": str(e),
            "brand_style": "Error fetching brand information",
            "recommendations": f"Please provide brand guidelines manually. Error: {str(e)}",
        }


async def generate_design_image(
    prompt: str,
    logo_path: Optional[str] = None,
    brand_assets: Optional[List[str]] = None,
    original_image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a hat design image using Gemini 3 Pro Image (Nano Banana Pro).

    Args:
        prompt: The design prompt
        logo_path: Optional path to the client logo
        brand_assets: Optional list of paths to brand asset files
        original_image_path: Optional path to original image (for revisions/edits)

    Returns:
        Dictionary with 'success', 'image_data' (base64), or 'error'
    """
    try:
        api_key = settings.google_gemini_api_key
        if not api_key:
            return {
                "success": False,
                "error": "Gemini API key not configured",
            }

        # Use Gemini 3 Pro Image (Nano Banana Pro) for professional asset production
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent?key={api_key}"

        # Build parts list - include original image if this is a revision
        parts = []

        # If we have an original image (revision mode), include it first
        if original_image_path:
            try:
                # Load the original image and convert to base64
                from ..config import get_settings
                settings_local = get_settings()
                full_path = Path(settings_local.upload_dir) / original_image_path

                if full_path.exists():
                    with open(full_path, "rb") as f:
                        image_bytes = f.read()
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                    # Determine mime type
                    mime_type = "image/png"
                    if original_image_path.endswith(".jpg") or original_image_path.endswith(".jpeg"):
                        mime_type = "image/jpeg"

                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_base64
                        }
                    })
            except Exception as e:
                # Log error but continue without the image
                print(f"Warning: Could not load original image: {e}")

        # Add the text prompt
        parts.append({"text": prompt})

        payload = {
            "contents": [
                {
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE"]
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Retry logic for 503 errors (model overloaded)
            last_error = None
            for attempt in range(MAX_RETRIES):
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 503:
                    last_error = "The model is overloaded. Please try again."
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "error": f"API error 503: {last_error} (tried {MAX_RETRIES} times)",
                    }

                if response.status_code != 200:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}: {error_data}",
                    }

                break  # Success, exit retry loop

            result = response.json()

            # Extract image from Gemini response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "inlineData" in part:
                            return {
                                "success": True,
                                "image_data": part["inlineData"]["data"],
                                "mime_type": part["inlineData"].get("mimeType", "image/png"),
                            }

            return {
                "success": False,
                "error": f"No image in response: {result}",
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Request timed out. Image generation may take longer than expected.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def generate_design(
    customer_name: str,
    hat_style: str,
    material: str,
    style_direction: str,
    custom_description: Optional[str] = None,
    logo_path: Optional[str] = None,
    brand_assets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a complete hat design.

    Args:
        customer_name: The client/brand name
        hat_style: The hat style code
        material: The material code
        style_direction: The style direction code
        custom_description: Optional additional style description
        logo_path: Optional path to client logo
        brand_assets: Optional list of brand asset paths

    Returns:
        Dictionary with prompt, success status, and image data or error
    """
    # Build the prompt
    prompt = build_design_prompt(
        hat_style=hat_style,
        material=material,
        client_name=customer_name,
        style_direction=style_direction,
        custom_description=custom_description,
    )

    # Generate the image
    result = await generate_design_image(
        prompt=prompt,
        logo_path=logo_path,
        brand_assets=brand_assets,
    )

    return {
        "prompt": prompt,
        **result,
    }


async def generate_revision(
    original_prompt: str,
    revision_notes: str,
    original_image_path: Optional[str] = None,
    logo_path: Optional[str] = None,
    brand_assets: Optional[List[str]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate a revised hat design.

    Sends the latest image with a focused edit instruction to make
    precise, minimal changes.

    Args:
        original_prompt: The original design prompt
        revision_notes: User's requested changes
        original_image_path: Path to the latest generated image
        logo_path: Optional path to client logo
        brand_assets: Optional list of brand asset paths
        conversation_history: Not used (kept for API compatibility)

    Returns:
        Dictionary with prompt, success status, and image data or error
    """
    try:
        api_key = settings.google_gemini_api_key
        if not api_key:
            return {
                "success": False,
                "error": "Gemini API key not configured",
            }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent?key={api_key}"

        # Build parts - include the latest image first, then the edit instruction
        parts = []

        # Load and include the latest generated image
        if original_image_path:
            try:
                full_path = Path(settings.upload_dir) / original_image_path
                if full_path.exists():
                    with open(full_path, "rb") as f:
                        image_bytes = f.read()
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                    mime_type = "image/png"
                    if original_image_path.endswith((".jpg", ".jpeg")):
                        mime_type = "image/jpeg"

                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_base64
                        }
                    })
            except Exception as e:
                print(f"Warning: Could not load image: {e}")

        # Create a focused edit prompt that emphasizes minimal changes
        edit_prompt = f"""Edit this hat design image. Make ONLY the following change:

{revision_notes}

IMPORTANT: Keep everything else exactly the same. Only modify what is specifically requested above. Maintain all other design elements, colors, decorations, and styling unchanged."""

        parts.append({"text": edit_prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"]
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Retry logic for 503 errors (model overloaded)
            last_error = None
            for attempt in range(MAX_RETRIES):
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 503:
                    last_error = "The model is overloaded. Please try again."
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "prompt": revision_notes,
                        "error": f"API error 503: {last_error} (tried {MAX_RETRIES} times)",
                    }

                if response.status_code != 200:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
                    return {
                        "success": False,
                        "prompt": revision_notes,
                        "error": f"API error {response.status_code}: {error_data}",
                    }

                break  # Success, exit retry loop

            result = response.json()

            # Extract image from Gemini response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "inlineData" in part:
                            return {
                                "success": True,
                                "prompt": revision_notes,
                                "image_data": part["inlineData"]["data"],
                                "mime_type": part["inlineData"].get("mimeType", "image/png"),
                            }

            return {
                "success": False,
                "prompt": revision_notes,
                "error": f"No image in response: {result}",
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "prompt": revision_notes,
            "error": "Request timed out. Image generation may take longer than expected.",
        }
    except Exception as e:
        return {
            "success": False,
            "prompt": revision_notes,
            "error": str(e),
        }
