"""Utility for building custom design generation prompts."""

from typing import List, Optional, Dict

from .prompt_builder import LEGAL_TEXT, format_hat_style, format_material

# Decoration method display names
DECORATION_METHODS = {
    "embroidery": "flat embroidery",
    "screen_print": "screen printing",
    "patch": "sewn patch",
    "3d_puff": "3D puff embroidery",
    "laser_cut": "laser-cut applique",
    "heat_transfer": "heat transfer vinyl",
    "sublimation": "sublimation printing",
}

# Size display names
SIZES = {
    "small": "small (approximately 2 inches)",
    "medium": "medium (approximately 3 inches)",
    "large": "large (approximately 4 inches)",
}

# Location display names
LOCATION_NAMES = {
    "front": "front center",
    "left": "left side",
    "right": "right side",
    "back": "back",
    "visor": "underneath the visor",
}


def format_decoration_method(method: str) -> str:
    """Convert decoration method code to display name."""
    return DECORATION_METHODS.get(method, method)


def format_size(size: str, size_details: Optional[str] = None) -> str:
    """Convert size code to display name with optional custom details."""
    if size == "custom" and size_details:
        return f"custom size ({size_details})"
    return SIZES.get(size, size)


def format_location(location: str) -> str:
    """Convert location code to display name."""
    return LOCATION_NAMES.get(location, location)


def build_custom_design_prompt(
    hat_style: str,
    material: str,
    brand_name: str,
    location_logos: List[Dict],
    reference_hat_path: Optional[str] = None,
) -> str:
    """
    Build the full prompt for custom design generation with per-location logos.

    Args:
        hat_style: The hat style code (e.g., '6-panel-hat')
        material: The material code (e.g., 'cotton-twill')
        brand_name: The brand/client name
        location_logos: List of location logo specifications with keys:
            - location: The location code (front, left, right, back, visor)
            - decoration_method: The decoration method code
            - size: The size code
            - size_details: Optional custom size details
        reference_hat_path: Optional path to reference hat image

    Returns:
        The complete prompt string for image generation
    """
    formatted_style = format_hat_style(hat_style)
    formatted_material = format_material(material)

    # Build decoration location descriptions
    decoration_descriptions = []
    for logo in location_logos:
        location_name = format_location(logo["location"])
        method_name = format_decoration_method(logo["decoration_method"])
        size_name = format_size(logo["size"], logo.get("size_details"))

        decoration_descriptions.append(
            f"- **{location_name.upper()}**: {method_name} using the provided {logo['location']} logo, sized {size_name}"
        )

    decorations_text = "\n".join(decoration_descriptions)

    if reference_hat_path:
        # Reference hat recreation mode
        prompt = f"""Recreate this reference hat design with the customer's branding.

REFERENCE HAT: An image of a reference hat has been provided. Match the following aspects:
- Overall hat shape and style
- Color scheme and color blocking
- Panel structure and construction details
- Any distinctive design elements (stitching patterns, contrast elements, etc.)

TARGET HAT SPECIFICATIONS:
- Hat type: **{formatted_style}** made of **{formatted_material}**
- Brand: **{brand_name}**

LOGO PLACEMENTS - Replace any existing logos/branding with the customer's provided logos at these specific locations:
{decorations_text}

CRITICAL INSTRUCTIONS:
1. Use ONLY the provided logo images for each location - do NOT search for or use any other logos
2. Match the reference hat's style and aesthetic as closely as possible
3. Maintain professional quality and clean execution
4. Each logo should be clearly visible and properly sized for its location

The hat is viewed from the front, left, right, back, underneath the visor with the front end of the visor pointing down, and worn on a white male model.

Professional studio lighting, white background, 4k resolution.

Add the following legal language to the bottom of the image: {LEGAL_TEXT}"""
    else:
        # Standard custom design mode
        prompt = f"""Create a photorealistic product shot of a **{formatted_style}** made of **{formatted_material}**.

BRAND: **{brand_name}**

DECORATION SPECIFICATIONS - Place the provided logos at exactly these locations using the specified methods:
{decorations_text}

CRITICAL INSTRUCTIONS:
1. Use ONLY the provided logo images for each location - do NOT search for or use any other logos from the internet
2. Place each logo exactly at its specified location
3. Use the specified decoration method for each location (embroidery has texture and depth, patches are raised, screen print is flat, etc.)
4. Size each decoration according to the specification
5. Do NOT add any decorations at locations not specified above
6. Keep the design clean and professional

The hat is viewed from the front, left, right, back, underneath the visor with the front end of the visor pointing down, and worn on a white male model.

Professional studio lighting, white background, 4k resolution.

Add the following legal language to the bottom of the image: {LEGAL_TEXT}"""

    return prompt


def build_custom_revision_prompt(
    original_prompt: str,
    revision_notes: str,
) -> str:
    """
    Build a prompt for custom design revision.

    Args:
        original_prompt: The original design prompt
        revision_notes: User's requested changes

    Returns:
        The complete prompt for revision
    """
    return f"""{original_prompt}

REVISION REQUESTED:
{revision_notes}

Please generate a revised version of the hat design incorporating the requested changes while maintaining the exact logo placements and decoration methods specified. Do not change the logos themselves - only modify the hat design, colors, or placement as requested."""
