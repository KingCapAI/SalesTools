"""Gemini AI service for brand scraping and image generation."""

import base64
import json
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

import google.generativeai as genai
from PIL import Image
import io

from ..config import get_settings
from ..utils.prompt_builder import build_design_prompt, build_revision_prompt
from ..utils.custom_prompt_builder import build_custom_design_prompt, build_custom_revision_prompt
from .storage_service import read_file_bytes

# Supported image formats for Gemini API
SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}

settings = get_settings()

# Layout template — 6-view grid reference image bundled with the backend
_LAYOUT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "ai_design_template_v2.jpeg"
_layout_template_part_cache: Optional[Dict[str, Any]] = None


def _get_layout_template_part() -> Optional[Dict[str, Any]]:
    """Load the 6-view layout template once and return as an inlineData image part."""
    global _layout_template_part_cache
    if _layout_template_part_cache is not None:
        return _layout_template_part_cache
    try:
        if not _LAYOUT_TEMPLATE_PATH.exists():
            print(f"Warning: Layout template not found at {_LAYOUT_TEMPLATE_PATH}")
            return None
        with open(_LAYOUT_TEMPLATE_PATH, "rb") as f:
            raw = f.read()
        _layout_template_part_cache = {
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": base64.b64encode(raw).decode("utf-8"),
            }
        }
        return _layout_template_part_cache
    except Exception as e:
        print(f"Warning: Could not load layout template: {e}")
        return None


_LAYOUT_TEMPLATE_LABEL = (
    "LAYOUT TEMPLATE (structural reference only — DO NOT IMITATE ITS ART STYLE): "
    "This template is a flat cartoon line-art illustration drawn for clarity. "
    "It exists ONLY to show: (1) the 3x2 grid composition, (2) the six box positions, "
    "and (3) the six angle labels (FRONT, WEARERS RIGHT, WEARERS LEFT, BACK, UNDERVISOR, MODEL). "
    "The OUTPUT image must be a PHOTOREALISTIC studio product photograph — NOT cartoon, "
    "NOT illustration, NOT line-art, NOT stylized drawing. "
    "Do NOT copy the template's hat shape, colors, design details, line-art rendering, "
    "flat coloring, or the cartoon person in the MODEL cell. Replicate ONLY the grid "
    "layout and the angle labels."
)

# Retry configuration for 503 errors
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 5
IMAGE_GENERATION_TIMEOUT = 300.0  # 5 minutes for image generation

# --- Vertex AI auth helpers ---

_vertex_credentials = None
_vertex_token_expiry = 0


def _get_vertex_credentials():
    """Load service account credentials from the JSON env var."""
    global _vertex_credentials
    if _vertex_credentials is not None:
        return _vertex_credentials

    creds_json = settings.google_application_credentials_json
    if not creds_json:
        return None

    try:
        from google.oauth2 import service_account
        info = json.loads(creds_json)
        _vertex_credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return _vertex_credentials
    except Exception as e:
        print(f"Warning: Failed to load Vertex AI credentials: {e}")
        return None


def _get_vertex_access_token() -> Optional[str]:
    """Get a valid access token, refreshing if needed."""
    creds = _get_vertex_credentials()
    if creds is None:
        return None

    import google.auth.transport.requests
    if not creds.valid:
        creds.refresh(google.auth.transport.requests.Request())

    return creds.token


def _use_vertex_ai() -> bool:
    """Check if Vertex AI is configured and should be used."""
    return bool(settings.google_cloud_project and settings.google_application_credentials_json)


def _get_image_gen_url(api_key: Optional[str] = None) -> tuple[str, dict]:
    """
    Return (url, headers) for image generation.
    Prefers Vertex AI if configured, falls back to direct Gemini API.
    """
    if _use_vertex_ai():
        try:
            token = _get_vertex_access_token()
            if token:
                project = settings.google_cloud_project
                url = (
                    f"https://aiplatform.googleapis.com/v1/projects/{project}"
                    f"/locations/global/publishers/google/models/gemini-3.1-flash-image-preview:generateContent"
                )
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                }
                print(f"[ImageGen] Using Vertex AI (project: {project})")
                return url, headers
            else:
                print("[ImageGen] WARNING: Vertex AI configured but failed to get access token, falling back to direct API")
        except Exception as e:
            print(f"[ImageGen] WARNING: Vertex AI auth error: {e}, falling back to direct API")

    # Fallback to direct Gemini API
    key = api_key or settings.google_gemini_api_key
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    print(f"[ImageGen] Using direct Gemini API (key present: {bool(key)})")
    return url, headers


def init_gemini():
    """Initialize the Gemini client."""
    if settings.google_gemini_api_key:
        genai.configure(api_key=settings.google_gemini_api_key)


async def _call_gemini_text(prompt: str, image_parts: Optional[List[Dict]] = None) -> str:
    """
    Call Gemini text model via the direct AI Studio SDK.
    Image generation uses Vertex AI separately; text tasks use AI Studio because
    paid-tier AI Studio has higher RPM than a fresh Vertex project's default quotas.
    """
    init_gemini()
    model = genai.GenerativeModel("gemini-flash-latest")
    if image_parts:
        sdk_parts = []
        for p in image_parts:
            if "inlineData" in p:
                sdk_parts.append({
                    "inline_data": {
                        "mime_type": p["inlineData"]["mimeType"],
                        "data": p["inlineData"]["data"],
                    }
                })
        sdk_parts.append(prompt)
        response = model.generate_content(sdk_parts)
    else:
        response = model.generate_content(prompt)
    return response.text


async def extract_decorations_from_image(image_data: str) -> Optional[Dict[str, str]]:
    """
    Use Gemini Vision to read decoration method callouts from a generated hat design image.

    Args:
        image_data: Base64-encoded image data

    Returns:
        Dict mapping location to decoration method, e.g.
        {"front": "3D Embroidery", "left": "Woven Patch", "back": "Flat Embroidery"}
        Returns None if extraction fails.
    """
    try:
        prompt = """Analyze this hat design image. It shows multiple views of a hat with decoration method callout labels (white pills with black text connected by lines/arrows to the decorations).

For each labeled decoration, identify:
1. The hat LOCATION. Use these EXACT keys: "front", "left", "right", "back", "underbill". The angle labels in the image may say FRONT, WEARERS RIGHT, WEARERS LEFT, BACK, UNDERVISOR, MODEL — map them as: WEARERS RIGHT -> "right", WEARERS LEFT -> "left", UNDERVISOR -> "underbill". Skip the MODEL view.
2. The DECORATION METHOD text shown in the callout label

Return ONLY a JSON object mapping location to decoration method. Example:
{"front": "3D Embroidery", "left": "Woven Patch", "back": "Flat Embroidery"}

Rules:
- Only include locations that have a visible callout label
- Use the EXACT text from the callout label
- If the same decoration method appears labeled multiple times, count it only ONCE for its location
- Do NOT include the model/person view — only read labels from hat-only views
- If no callout labels are visible, return {}

Return ONLY the JSON object, no other text."""

        image_part = {
            "inlineData": {
                "mimeType": "image/png",
                "data": image_data,
            }
        }

        raw_text = await _call_gemini_text(prompt, image_parts=[image_part])
        response_text = raw_text.strip()

        # Clean markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        result = json.loads(response_text.strip())

        # Normalize location keys to lowercase
        normalized = {}
        for loc, method in result.items():
            key = loc.lower().strip().replace("'", "").replace("’", "")
            # Normalize common variations
            if key in ("underbill", "undervisor", "visor", "underbrim", "under brim", "under bill", "under visor"):
                key = "underbill"
            if key in ("left side", "left panel", "wearers left", "wearer left", "left view"):
                key = "left"
            if key in ("right side", "right panel", "wearers right", "wearer right", "right view"):
                key = "right"
            if key in ("front center", "front panel", "front view"):
                key = "front"
            if key in ("back panel", "rear", "back view"):
                key = "back"
            # Deduplicate — keep first occurrence
            if key not in normalized:
                normalized[key] = method

        print(f"[DecorationExtract] Detected: {normalized}")
        return normalized

    except Exception as e:
        print(f"[DecorationExtract] Failed to extract decorations: {e}")
        return None


_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_PAGE_FETCH_TIMEOUT = 10.0
_IMAGE_FETCH_TIMEOUT = 6.0
_HTML_MAX_BYTES = 2_000_000
_IMAGE_MAX_BYTES = 5_000_000


def _absolute_url(page_url: str, href: str) -> str:
    """Resolve a possibly-relative href against the page URL."""
    from urllib.parse import urljoin
    return urljoin(page_url, href)


def _normalize_url(url: str) -> str:
    """Add https:// if scheme is missing."""
    url = (url or "").strip()
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


async def _fetch_url_brand_assets(brand_url: str) -> Dict[str, Any]:
    """Best-effort fetch of homepage HTML + favicon + og:image.

    Returns a dict with whatever we could pull; missing fields are absent.
    Never raises — failures degrade silently to fewer signals.
    """
    import re

    result: Dict[str, Any] = {}
    normalized = _normalize_url(brand_url)
    if not normalized:
        return result

    headers = {"User-Agent": _BROWSER_UA, "Accept": "text/html,*/*"}

    try:
        async with httpx.AsyncClient(
            timeout=_PAGE_FETCH_TIMEOUT,
            follow_redirects=True,
            max_redirects=5,
            headers=headers,
        ) as client:
            html_response = await client.get(normalized)
            html_bytes = html_response.content[:_HTML_MAX_BYTES]
            final_url = str(html_response.url)
            html = html_bytes.decode("utf-8", errors="ignore")

            def first(pattern: str, flags: int = re.IGNORECASE) -> Optional[str]:
                m = re.search(pattern, html, flags)
                return m.group(1).strip() if m else None

            title = first(r"<title[^>]*>([^<]+)</title>")
            description = first(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']'
            ) or first(
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']'
            )
            theme_color = first(
                r'<meta[^>]+name=["\']theme-color["\'][^>]+content=["\']([^"\']+)["\']'
            )
            og_image_href = first(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']'
            )
            favicon_href = first(
                r'<link[^>]+rel=["\'](?:icon|shortcut icon|apple-touch-icon)["\'][^>]+href=["\']([^"\']+)["\']'
            )
            # Fallback: link rel comes after href
            if not favicon_href:
                favicon_href = first(
                    r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\'](?:icon|shortcut icon|apple-touch-icon)["\']'
                )

            if title:
                result["title"] = title[:300]
            if description:
                result["description"] = description[:500]
            if theme_color:
                result["theme_color"] = theme_color

            async def _fetch_image(href: Optional[str]) -> Optional[Dict[str, str]]:
                if not href:
                    return None
                try:
                    img_url = _absolute_url(final_url, href)
                    img_resp = await client.get(img_url)
                    img_bytes = img_resp.content[:_IMAGE_MAX_BYTES]
                    if len(img_bytes) < 100:
                        return None
                    mime = img_resp.headers.get("content-type", "").split(";")[0].strip()
                    if not mime.startswith("image/"):
                        # Guess from extension
                        lower = img_url.lower()
                        if lower.endswith(".png"):
                            mime = "image/png"
                        elif lower.endswith((".jpg", ".jpeg")):
                            mime = "image/jpeg"
                        elif lower.endswith(".webp"):
                            mime = "image/webp"
                        elif lower.endswith(".ico"):
                            mime = "image/x-icon"
                        else:
                            return None
                    # Gemini doesn't accept ICO — skip those
                    if mime in ("image/x-icon", "image/vnd.microsoft.icon"):
                        return None
                    return {
                        "mime": mime,
                        "data": base64.b64encode(img_bytes).decode("utf-8"),
                    }
                except Exception:
                    return None

            og_image = await _fetch_image(og_image_href)
            favicon = await _fetch_image(favicon_href)
            if og_image:
                result["og_image"] = og_image
            if favicon:
                result["favicon"] = favicon

    except Exception as e:
        print(f"[BrandScrape] URL fetch failed for {normalized}: {e}")

    return result


def _kmeans_colors_from_logo(logo_bytes: bytes) -> List[str]:
    """Run k-means on logo bytes and return the top dominant hex codes.

    Drops near-white and fully transparent pixels so backgrounds don't
    dilute the result. Returns at most 3 hex codes, ordered by pixel share.
    """
    try:
        import numpy as np
        from sklearn.cluster import KMeans

        img = Image.open(io.BytesIO(logo_bytes))
        if img.mode in ("P", "L"):
            img = img.convert("RGBA")
        elif img.mode == "CMYK":
            img = img.convert("RGB")
        img.thumbnail((200, 200), Image.LANCZOS)

        pixels = np.array(img).reshape(-1, len(img.getbands()))

        # Strip transparent pixels first if RGBA, then near-white background.
        if pixels.shape[1] == 4:
            opaque = pixels[pixels[:, 3] >= 30]
            pixels = opaque[:, :3]
        else:
            pixels = pixels[:, :3]
        if len(pixels) == 0:
            return []
        non_white = pixels[~np.all(pixels >= 240, axis=1)]
        if len(non_white) == 0:
            return []

        unique_count = len(np.unique(non_white.astype(np.int32), axis=0))
        k = min(5, max(1, unique_count))
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(non_white.astype(np.float64))
        centers = kmeans.cluster_centers_.astype(int)
        counts = np.bincount(labels, minlength=k)

        ordered = sorted(zip(counts, centers), key=lambda t: -t[0])
        hexes: List[str] = []
        for count, rgb in ordered:
            if count / counts.sum() < 0.03:  # drop noise clusters under 3%
                continue
            r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
            hexes.append(f"#{r:02X}{g:02X}{b:02X}")
            if len(hexes) >= 3:
                break
        return hexes
    except Exception as e:
        print(f"[BrandScrape] Logo k-means failed: {e}")
        return []


async def scrape_brand_info(
    brand_name: Optional[str] = None,
    brand_url: Optional[str] = None,
    logo_bytes: Optional[bytes] = None,
    logo_mime: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Vision-based brand analysis.

    Authority order for the primary color palette:
      1. The uploaded brand logo (k-means on pixels — ground truth).
      2. Visual signals from the homepage (og:image + favicon, sent as
         vision inputs to Gemini).
      3. Gemini's training-time knowledge of the brand (last resort).

    Returns dict shape unchanged for callers:
      {primary_colors, secondary_colors, brand_style, design_aesthetic,
       typography, target_audience, industry, brand_elements,
       recommendations, color_sources}
    """
    init_gemini()

    # 1. Logo k-means (authoritative primaries if logo provided)
    logo_hexes: List[str] = []
    if logo_bytes:
        logo_hexes = _kmeans_colors_from_logo(logo_bytes)

    # 2. URL fetch (vision inputs + page metadata)
    page_assets: Dict[str, Any] = {}
    if brand_url:
        page_assets = await _fetch_url_brand_assets(brand_url)

    # Build vision parts list
    image_parts: List[Dict[str, Any]] = []
    image_labels: List[str] = []

    if logo_bytes:
        mime = logo_mime or "image/png"
        image_parts.append({"inlineData": {
            "mimeType": mime,
            "data": base64.b64encode(logo_bytes).decode("utf-8"),
        }})
        image_labels.append("brand logo (authoritative source for primary colors)")

    if page_assets.get("og_image"):
        image_parts.append({"inlineData": {
            "mimeType": page_assets["og_image"]["mime"],
            "data": page_assets["og_image"]["data"],
        }})
        image_labels.append("website Open Graph share image (use for secondary/accent colors and brand vibe)")

    if page_assets.get("favicon"):
        image_parts.append({"inlineData": {
            "mimeType": page_assets["favicon"]["mime"],
            "data": page_assets["favicon"]["data"],
        }})
        image_labels.append("website favicon (small, lower confidence — use only if other signals are missing)")

    # Build the text prompt
    prompt_lines = [
        "You are extracting brand identity signals for hat design.",
        "",
        f"Brand name: {brand_name or 'Not provided'}",
        f"Brand website: {brand_url or 'Not provided'}",
    ]
    if page_assets.get("title"):
        prompt_lines.append(f"Page title: {page_assets['title']}")
    if page_assets.get("description"):
        prompt_lines.append(f"Page description: {page_assets['description']}")
    if page_assets.get("theme_color"):
        prompt_lines.append(f"Site theme-color meta: {page_assets['theme_color']}")

    if image_parts:
        prompt_lines.append("")
        prompt_lines.append("Images attached (in order):")
        for idx, label in enumerate(image_labels, start=1):
            prompt_lines.append(f"  {idx}. {label}")

    if logo_hexes:
        prompt_lines.extend([
            "",
            "CONFIRMED PRIMARY COLORS (sampled from the logo's pixels — these are anchors, not the full palette):",
            "  " + ", ".join(logo_hexes[:5]),
            "",
            "YOUR JOB — EXPAND BEYOND THESE:",
            "- Treat the logo colors above as ONE anchor in the palette, not the full story.",
            "- Identify ADDITIONAL brand colors that complement them: accent colors used in the brand's marketing, signature secondary colors, alternate logo variants, brand guideline palette colors you've seen for this brand.",
            "- Sources to consult: the attached website images, your training knowledge of this brand's identity, common variations of the brand mark.",
            "- Put these additional colors in secondary_colors. Aim for 2-4 entries when signals exist.",
            "- DO NOT duplicate the logo colors in secondary_colors.",
            "- DO NOT include generic UI neutrals (#FFFFFF, #000000, plain grays) unless they're explicitly part of the brand identity.",
            "- DO NOT include CTA button colors or generic website chrome unless they clearly are brand colors.",
        ])
    else:
        prompt_lines.extend([
            "",
            "PRIMARY COLOR RULES:",
            "- Pull primary colors from the most prominent visual mark (logo/wordmark) in the attached images.",
            "- DO NOT pull primary colors from CTAs, buttons, background neutrals (#FFFFFF, #000000, light grays), or generic UI accent colors unless they clearly are the brand color.",
            "- For secondary_colors, include accent colors used in marketing materials, alternate logo variants, or brand palette colors you know from training. 1-3 entries when signals exist.",
            "- If signals are weak, prefer fewer colors over guessing.",
        ])

    prompt_lines.extend([
        "",
        "Respond with ONLY a JSON object — no prose, no markdown fences:",
        "{",
        '  "primary_colors": ["#RRGGBB", ...],          // 1-3 entries',
        '  "secondary_colors": ["#RRGGBB", ...],        // up to 4 entries — the full brand palette beyond the primaries',
        '  "brand_style": "...",                         // short phrase, e.g. "modern athletic"',
        '  "typography": "...",                          // recommended font style',
        '  "design_aesthetic": "...",                    // minimalist / bold / etc.',
        '  "target_audience": "...",',
        '  "industry": "...",',
        '  "brand_elements": ["..."],',
        '  "recommendations": "..."                      // 1-2 sentences for hat design',
        "}",
    ])

    prompt = "\n".join(prompt_lines)

    try:
        raw_text = await _call_gemini_text(prompt, image_parts=image_parts or None)

        response_text = raw_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        try:
            parsed = json.loads(response_text.strip())
        except json.JSONDecodeError:
            parsed = {
                "raw_response": raw_text,
                "brand_style": "Unable to parse structured response",
                "recommendations": raw_text,
            }

        # Merge logo k-means with Gemini-found colors.
        # Logo colors anchor primaries; any additional brand colors Gemini
        # surfaced (whether in primary_colors or secondary_colors) flow into
        # secondaries, deduped against the logo anchors. The logo doesn't
        # override the palette — it just becomes its most authoritative tier.
        sources: Dict[str, str] = {}
        gemini_primaries = [
            (h or "").strip() for h in (parsed.get("primary_colors") or [])
            if h and isinstance(h, str)
        ]
        gemini_secondaries = [
            (h or "").strip() for h in (parsed.get("secondary_colors") or [])
            if h and isinstance(h, str)
        ]

        def _seen_upper(items: List[str]) -> set:
            return {x.upper() for x in items if x}

        if logo_hexes:
            anchors = logo_hexes[:3]
            seen = _seen_upper(anchors)
            extras: List[str] = []
            # Anything Gemini surfaced that isn't already in the logo palette
            # becomes part of the broader brand palette.
            for candidate in gemini_primaries + gemini_secondaries:
                up = candidate.upper()
                if up and up not in seen:
                    extras.append(candidate)
                    seen.add(up)
            parsed["primary_colors"] = anchors
            parsed["secondary_colors"] = extras[:4]
            for hx in anchors:
                sources[hx.upper()] = "logo"
            for hx in extras[:4]:
                sources.setdefault(hx.upper(), "website" if page_assets else "knowledge")
        else:
            for hx in gemini_primaries[:3]:
                sources[hx.upper()] = "website" if page_assets else "knowledge"
            for hx in gemini_secondaries[:4]:
                sources.setdefault(hx.upper(), "website" if page_assets else "knowledge")

        parsed["color_sources"] = sources
        return parsed

    except Exception as e:
        # If Gemini failed but we still have logo k-means, return those as a usable result.
        if logo_hexes:
            return {
                "primary_colors": logo_hexes[:3],
                "secondary_colors": [],
                "brand_style": "",
                "recommendations": "",
                "color_sources": {hx.upper(): "logo" for hx in logo_hexes[:3]},
            }
        return {
            "error": str(e),
            "brand_style": "Error fetching brand information",
            "recommendations": f"Please provide brand guidelines manually. Error: {str(e)}",
        }


async def generate_design_image(
    prompt: str,
    logo_path: Optional[str] = None,
    logos: Optional[List] = None,
    brand_assets: Optional[List[str]] = None,
    original_image_path: Optional[str] = None,
    reference_image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a hat design image using Gemini 3 Pro Image (Nano Banana Pro).

    Args:
        prompt: The design prompt
        logo_path: Optional path to the client logo (DEPRECATED: use logos)
        logos: Optional list of logo objects/dicts with name, logo_path, location
        brand_assets: Optional list of paths to brand asset files
        original_image_path: Optional path to original image (for revisions/edits)

    Returns:
        Dictionary with 'success', 'image_data' (base64), or 'error'
    """
    try:
        if not _use_vertex_ai() and not settings.google_gemini_api_key:
            return {
                "success": False,
                "error": "No image generation API configured. Set Vertex AI credentials or Gemini API key.",
            }

        url, auth_headers = _get_image_gen_url()

        # Build parts list - include logos and/or original image
        parts = []

        # Layout template (reference only) — placed first so the model uses it as composition guidance.
        # Skip when an original image is provided (revision/edit flow keeps existing layout).
        if not original_image_path:
            template_part = _get_layout_template_part()
            if template_part:
                parts.append({"text": _LAYOUT_TEMPLATE_LABEL})
                parts.append(template_part)

        # User-supplied reference image (existing hat/design to riff on).
        # Placed BEFORE logos so the model anchors silhouette/composition first,
        # then drops the brand's logos onto that base.
        if reference_image_path:
            try:
                ref_bytes = await read_file_bytes(reference_image_path)
                if ref_bytes:
                    ref_base64 = base64.b64encode(ref_bytes).decode("utf-8")
                    ref_mime = "image/png"
                    lower = reference_image_path.lower()
                    if lower.endswith((".jpg", ".jpeg")):
                        ref_mime = "image/jpeg"
                    elif lower.endswith(".webp"):
                        ref_mime = "image/webp"
                    parts.append({"text": "USER REFERENCE IMAGE (the existing design the user wants to reference — see the REFERENCE IMAGE section of the prompt for how strictly to follow it):"})
                    parts.append({
                        "inlineData": {
                            "mimeType": ref_mime,
                            "data": ref_base64,
                        }
                    })
            except Exception as e:
                print(f"Warning: Could not load reference image: {e}")

        # Multi-logo support: add each logo with a label
        if logos:
            for logo in logos:
                l_path = logo.logo_path if hasattr(logo, 'logo_path') else logo.get('logo_path')
                l_name = logo.name if hasattr(logo, 'name') else logo.get('name', 'Logo')
                l_location = logo.location if hasattr(logo, 'location') else logo.get('location')

                if not l_path:
                    continue

                try:
                    ext = Path(l_path).suffix.lower()
                    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                        print(f"Warning: Skipping unsupported image format for '{l_name}': {ext}")
                        continue

                    logo_bytes = await read_file_bytes(l_path)
                    if not logo_bytes:
                        print(f"Warning: Logo file not found: {l_path}")
                        continue
                    logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

                    mime_type = "image/png"
                    if ext in {'.jpg', '.jpeg'}:
                        mime_type = "image/jpeg"
                    elif ext == '.webp':
                        mime_type = "image/webp"

                    # Add label before the logo image
                    label = f"LOGO '{l_name}'"
                    if l_location:
                        label += f" (for {l_location.upper()} of hat)"
                    label += ":"

                    parts.append({"text": label})
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": logo_base64
                        }
                    })
                except Exception as e:
                    print(f"Warning: Could not load logo '{l_name}': {e}")

        # Backward compat: single logo_path
        elif logo_path:
            try:
                ext = Path(logo_path).suffix.lower()
                if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                    print(f"Warning: Skipping unsupported image format: {ext}. Only PNG, JPG, and WEBP are supported.")
                else:
                    logo_bytes = await read_file_bytes(logo_path)
                    if logo_bytes:
                        logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

                        mime_type = "image/png"
                        if ext in {'.jpg', '.jpeg'}:
                            mime_type = "image/jpeg"
                        elif ext == '.webp':
                            mime_type = "image/webp"

                        parts.append({
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": logo_base64
                            }
                        })
            except Exception as e:
                print(f"Warning: Could not load logo: {e}")

        # If we have an original image (revision mode), include it
        if original_image_path:
            try:
                image_bytes = await read_file_bytes(original_image_path)
                if image_bytes:
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
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
                "responseModalities": ["TEXT", "IMAGE"],
                # Low-but-not-too-low temp keeps view consistency without making the
                # model latch onto the cartoon template style.
                "temperature": 0.4,
                "topP": 0.85
            }
        }

        import time as _time
        async with httpx.AsyncClient(timeout=IMAGE_GENERATION_TIMEOUT) as client:
            # Retry logic for 503 errors (model overloaded)
            last_error = None
            _start = _time.time()
            for attempt in range(MAX_RETRIES):
                print(f"[ImageGen] Attempt {attempt + 1}/{MAX_RETRIES}...")
                response = await client.post(
                    url,
                    json=payload,
                    headers=auth_headers,
                )
                print(f"[ImageGen] Response: {response.status_code} ({_time.time() - _start:.1f}s elapsed)")

                if response.status_code == 503:
                    last_error = "The model is overloaded. Please try again."
                    if attempt < MAX_RETRIES - 1:
                        wait = RETRY_DELAY_SECONDS * (attempt + 1)
                        print(f"[ImageGen] 503 - retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                    return {
                        "success": False,
                        "error": "The AI image generator is currently busy. Please wait a moment and try again.",
                    }

                if response.status_code != 200:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
                    print(f"[ImageGen] Error: {response.status_code} - {str(error_data)[:200]}")
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}: {error_data}",
                    }

                break  # Success, exit retry loop

            print(f"[ImageGen] Success in {_time.time() - _start:.1f}s")
            result = response.json()

            # Extract image from response
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
    structure: Optional[str] = None,
    closure: Optional[str] = None,
    logo_path: Optional[str] = None,
    logos: Optional[List] = None,
    logos_data: Optional[List[Dict[str, Any]]] = None,
    brand_assets: Optional[List[str]] = None,
    variation_index: int = 0,
    reference_image_path: Optional[str] = None,
    reference_match_mode: Optional[str] = None,
    brand_colors: Optional[List[str]] = None,
    brand_guidelines_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a complete hat design.

    Args:
        customer_name: The client/brand name
        hat_style: The hat style code
        material: The material code
        style_direction: The style direction code
        custom_description: Optional additional style description
        structure: Optional hat structure (structured or unstructured)
        closure: Optional closure type (snapback, metal_slider_buckle, velcro_strap)
        logo_path: Optional path to client logo (DEPRECATED)
        logos: Optional list of DesignLogo model objects
        logos_data: Optional list of logo dicts for prompt building
        brand_assets: Optional list of brand asset paths
        variation_index: Index for design variation (0, 1, or 2)

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
        structure=structure,
        closure=closure,
        logos=logos_data,
        variation_index=variation_index,
        reference_match_mode=reference_match_mode if reference_image_path else None,
        brand_colors=brand_colors,
        brand_guidelines_text=brand_guidelines_text,
    )

    # Generate the image
    result = await generate_design_image(
        prompt=prompt,
        logo_path=logo_path,
        logos=logos,
        brand_assets=brand_assets,
        reference_image_path=reference_image_path,
    )

    return {
        "prompt": prompt,
        **result,
    }


async def generate_revision_v2(
    base_prompt: str,
    edit_notes: str,
    logos: Optional[List] = None,
    logo_path: Optional[str] = None,
    brand_assets: Optional[List[str]] = None,
    reference_image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a revision by regenerating the design from scratch with an edit block.

    Critically, this DOES NOT feed the prior generated image back to the model.
    Image-to-image revisions degrade quality over rounds and tend to drift on
    accuracy because the model fights between "preserve" and "change." This
    function instead takes the prior prompt, appends a focused EDIT INSTRUCTIONS
    block, and produces a fresh generation. Quality stays at first-gen level.

    Args:
        base_prompt: The prior version's prompt (whose spec we want to inherit).
        edit_notes: User-supplied free-text feedback.
        logos: DesignLogo objects to pass alongside the prompt.
        logo_path: Backward-compat single logo path.
        brand_assets: Brand asset paths.
        reference_image_path: Optional reference image (carry through from creation).

    Returns:
        Dict with prompt, success, image_data or error — identical shape to
        generate_design's return.
    """
    revised_prompt = f"""{base_prompt}


EDIT INSTRUCTIONS — APPLY THESE CHANGES TO THE DESIGN ABOVE:
{edit_notes.strip()}

CRITICAL: Apply ONLY the changes listed above. Every other aspect of the
design (colors not mentioned, decorations not mentioned, logos, hat style,
materials, layout, model, lighting) must stay EXACTLY as the original
description specifies. Do not introduce new design elements. Do not change
anything that was not requested. The result must still be a 6-view layout
matching the layout template.
"""

    result = await generate_design_image(
        prompt=revised_prompt,
        logo_path=logo_path,
        logos=logos,
        brand_assets=brand_assets,
        reference_image_path=reference_image_path,
    )

    return {
        "prompt": revised_prompt,
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
        if not _use_vertex_ai() and not settings.google_gemini_api_key:
            return {
                "success": False,
                "error": "No image generation API configured. Set Vertex AI credentials or Gemini API key.",
            }

        url, auth_headers = _get_image_gen_url()

        # Build parts - include the latest image first, then the edit instruction
        parts = []

        # Load and include the latest generated image
        if original_image_path:
            try:
                image_bytes = await read_file_bytes(original_image_path)
                if image_bytes:
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
                "responseModalities": ["TEXT", "IMAGE"],
                # Low-but-not-too-low temp keeps view consistency without making the
                # model latch onto the cartoon template style.
                "temperature": 0.4,
                "topP": 0.85
            }
        }

        async with httpx.AsyncClient(timeout=IMAGE_GENERATION_TIMEOUT) as client:
            # Retry logic for 503 errors (model overloaded)
            last_error = None
            for attempt in range(MAX_RETRIES):
                # Refresh token on retries in case it expired
                if attempt > 0 and _use_vertex_ai():
                    url, auth_headers = _get_image_gen_url()

                response = await client.post(
                    url,
                    json=payload,
                    headers=auth_headers,
                )

                if response.status_code == 503:
                    last_error = "The model is overloaded. Please try again."
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "prompt": revision_notes,
                        "error": "The AI image generator is currently busy. Please wait a moment and try again.",
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

            # Extract image from response
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


async def generate_custom_design(
    brand_name: str,
    hat_style: str,
    material: str,
    location_logos: List[Dict[str, Any]],
    structure: Optional[str] = None,
    closure: Optional[str] = None,
    crown_color: Optional[str] = None,
    visor_color: Optional[str] = None,
    reference_hat_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a custom hat design with per-location logo specifications.

    Args:
        brand_name: The client/brand name
        hat_style: The hat style code
        material: The material code
        location_logos: List of dicts with keys:
            - location: front, left, right, back, visor
            - logo_path: path to the logo file
            - decoration_method: embroidery, screen_print, patch, etc.
            - size: small, medium, large, custom
            - size_details: optional custom size string
        structure: Hat structure (structured or unstructured)
        closure: Closure type (snapback, metal_slider_buckle, velcro_strap)
        crown_color: Color of the hat crown
        visor_color: Color of the visor
        reference_hat_path: Optional path to reference hat image

    Returns:
        Dictionary with prompt, success status, and image data or error
    """
    try:
        if not _use_vertex_ai() and not (settings.google_gemini_api_key_mockup or settings.google_gemini_api_key):
            return {
                "success": False,
                "error": "No image generation API configured. Set Vertex AI credentials or Gemini API key.",
            }

        # Build the prompt
        prompt = build_custom_design_prompt(
            hat_style=hat_style,
            material=material,
            brand_name=brand_name,
            location_logos=location_logos,
            structure=structure,
            closure=closure,
            crown_color=crown_color,
            visor_color=visor_color,
            reference_hat_path=reference_hat_path,
        )

        # Use mockup-specific API key for fallback if Vertex AI not configured
        fallback_key = settings.google_gemini_api_key_mockup or settings.google_gemini_api_key
        url, auth_headers = _get_image_gen_url(api_key=fallback_key)

        # Build parts list - include all location logos and reference hat
        parts = []

        # Layout template (reference only) — first part so it frames the composition
        template_part = _get_layout_template_part()
        if template_part:
            parts.append({"text": _LAYOUT_TEMPLATE_LABEL})
            parts.append(template_part)

        # Add reference hat image if provided
        if reference_hat_path:
            try:
                image_bytes = await read_file_bytes(reference_hat_path)
                if image_bytes:
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    mime_type = "image/png"
                    if reference_hat_path.lower().endswith((".jpg", ".jpeg")):
                        mime_type = "image/jpeg"
                    parts.append({"text": "REFERENCE HAT IMAGE:"})
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_base64
                        }
                    })
            except Exception as e:
                print(f"Warning: Could not load reference hat: {e}")

        # Add each location logo
        for logo_info in location_logos:
            logo_path = logo_info.get("logo_path")
            location = logo_info.get("location", "unknown")

            if logo_path:
                try:
                    ext = Path(logo_path).suffix.lower()
                    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                        print(f"Warning: Skipping {location} logo - unsupported format: {ext}. Only PNG, JPG, and WEBP are supported.")
                        continue

                    logo_bytes = await read_file_bytes(logo_path)
                    if not logo_bytes:
                        print(f"Warning: {location} logo not found: {logo_path}")
                        continue
                    logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

                    mime_type = "image/png"
                    if ext in {'.jpg', '.jpeg'}:
                        mime_type = "image/jpeg"
                    elif ext == '.webp':
                        mime_type = "image/webp"

                    parts.append({"text": f"LOGO FOR {location.upper()} LOCATION:"})
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": logo_base64
                        }
                    })
                except Exception as e:
                    print(f"Warning: Could not load {location} logo: {e}")

        # Add the text prompt at the end
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                # Low-but-not-too-low temp keeps view consistency without making the
                # model latch onto the cartoon template style.
                "temperature": 0.4,
                "topP": 0.85
            }
        }

        print(f"[Mockup Builder] Making API request ({'Vertex AI' if _use_vertex_ai() else 'direct Gemini'})...")
        print(f"[Mockup Builder] Number of parts: {len(parts)}")

        async with httpx.AsyncClient(timeout=IMAGE_GENERATION_TIMEOUT) as client:
            # Retry logic for 503 errors (model overloaded)
            last_error = None
            for attempt in range(MAX_RETRIES):
                print(f"[Mockup Builder] Attempt {attempt + 1}/{MAX_RETRIES}")
                # Refresh token on retries in case it expired
                if attempt > 0 and _use_vertex_ai():
                    url, auth_headers = _get_image_gen_url(api_key=fallback_key)
                try:
                    response = await client.post(
                        url,
                        json=payload,
                        headers=auth_headers,
                    )
                    print(f"[Mockup Builder] Response status: {response.status_code}")
                except Exception as req_error:
                    print(f"[Mockup Builder] Request error: {req_error}")
                    raise

                if response.status_code == 503:
                    last_error = "The model is overloaded. Please try again."
                    print(f"[Mockup Builder] 503 error - model overloaded")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "prompt": prompt,
                        "error": "The AI image generator is currently busy. Please wait a moment and try again.",
                    }

                if response.status_code != 200:
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = {"error": response.text[:500]}
                    print(f"[Mockup Builder] API error {response.status_code}: {error_data}")
                    return {
                        "success": False,
                        "prompt": prompt,
                        "error": f"API error {response.status_code}: {error_data}",
                    }

                break  # Success, exit retry loop

            result = response.json()
            print(f"[Mockup Builder] Got response with keys: {list(result.keys())}")

            # Extract image from Gemini response
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "inlineData" in part:
                            return {
                                "success": True,
                                "prompt": prompt,
                                "image_data": part["inlineData"]["data"],
                                "mime_type": part["inlineData"].get("mimeType", "image/png"),
                            }

            return {
                "success": False,
                "prompt": prompt,
                "error": f"No image in response: {result}",
            }

    except httpx.TimeoutException as timeout_err:
        print(f"[Mockup Builder] TIMEOUT after {IMAGE_GENERATION_TIMEOUT}s: {timeout_err}")
        return {
            "success": False,
            "prompt": prompt if 'prompt' in dir() else "Error building prompt",
            "error": "Request timed out. Image generation may take longer than expected.",
        }
    except Exception as e:
        print(f"[Mockup Builder] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "prompt": prompt if 'prompt' in dir() else "Error building prompt",
            "error": str(e),
        }
