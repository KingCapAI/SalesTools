"""Utility for building design generation prompts."""

from typing import Optional, List, Dict, Any

# Legal text to include in generated images
LEGAL_TEXT = """All designs, artwork, and concepts presented herein are the sole property of King Cap and are provided for the exclusive consideration of the intended recipient. These materials are confidential and may not be copied, reproduced, shared, or used in whole or in part for any purpose other than reviewing potential production with King Cap. Any unauthorized use, reproduction, or distribution of these designs is strictly prohibited and may result in legal action."""

# Hat style display names
HAT_STYLES = {
    "6-panel-hat": "6-panel hat",
    "6-panel-trucker": "6-panel trucker hat",
    "5-panel-hat": "5-panel hat",
    "5-panel-trucker": "5-panel trucker hat",
    "perforated-6-panel": "perforated 6-panel hat",
    "perforated-5-panel": "perforated 5-panel hat",
}

# Material display names
MATERIALS = {
    "cotton-twill": "cotton twill",
    "performance-polyester": "performance polyester",
    "nylon": "nylon",
    "canvas": "canvas",
}

# Style direction display names
STYLE_DIRECTIONS = {
    "simple": "Simple",
    "modern": "Modern",
    "luxurious": "Luxurious",
    "sporty": "Sporty",
    "rugged": "Rugged",
    "retro": "Retro",
    "collegiate": "Collegiate",
}

# Structure display names
STRUCTURES = {
    "structured": "structured (with front panel buckram stiffener)",
    "unstructured": "unstructured (soft, relaxed crown)",
}

# Closure display names
CLOSURES = {
    "snapback": "plastic snapback closure",
    "metal_slider_buckle": "metal slider buckle closure",
    "velcro_strap": "velcro strap closure",
}

# Variation hints for generating 3 distinct versions
VARIATION_HINTS = [
    "Create a unique interpretation focusing on classic, clean aesthetics with traditional placement and timeless appeal.",
    "Create a unique interpretation focusing on bold, eye-catching elements with striking color contrast and prominent branding.",
    "Create a unique interpretation focusing on creative, unexpected details with modern flair and distinctive character.",
]


def format_hat_style(style: str) -> str:
    """Convert hat style code to display name."""
    return HAT_STYLES.get(style, style)


def format_material(material: str) -> str:
    """Convert material code to display name."""
    return MATERIALS.get(material, material)


def format_style_direction(direction: str) -> str:
    """Convert style direction code to display name."""
    return STYLE_DIRECTIONS.get(direction, direction)


def format_structure(structure: Optional[str]) -> Optional[str]:
    """Convert structure code to display name."""
    if not structure:
        return None
    return STRUCTURES.get(structure, structure)


def format_closure(closure: Optional[str]) -> Optional[str]:
    """Convert closure code to display name."""
    if not closure:
        return None
    return CLOSURES.get(closure, closure)


def build_logo_placement_instructions(logos: List[Dict[str, Any]]) -> str:
    """Build prompt section describing how to place multiple named logos."""
    lines = []
    lines.append("LOGOS PROVIDED:")

    assigned_logos = []
    unassigned_logos = []

    for logo in logos:
        name = logo.get('name', 'Logo')
        location = logo.get('location')
        if location:
            assigned_logos.append((name, location))
            lines.append(f"- '{name}' → Place at the **{location.upper()}** of the hat")
        else:
            unassigned_logos.append(name)
            lines.append(f"- '{name}' → Place at the best location (AI's choice)")

    lines.append("")
    lines.append("IMPORTANT - LOGO USAGE: Use ONLY the provided logo images labeled above. Do NOT search for or use any other logos from the internet. Each logo image is labeled with its name.")

    if unassigned_logos:
        names = ", ".join(f"'{n}'" for n in unassigned_logos)
        lines.append(f"\nFor logos marked as AI's choice ({names}), place them at appropriate locations that complement the overall design. Choose from: front, left side, right side, back, or underbrim.")

    lines.append("\nUse exactly 3 decoration locations total. Methods: flat embroidery, 3D embroidery, PVC patch, woven patch, faux leather patch, embroidered patch, sublimated patch, or 3D printing.")
    lines.append("Do NOT add more than 3 decoration locations. Keep the design clean and professional.")

    return "\n".join(lines)


def build_design_prompt(
    hat_style: str,
    material: str,
    client_name: str,
    style_direction: str,
    custom_description: Optional[str] = None,
    structure: Optional[str] = None,
    closure: Optional[str] = None,
    logos: Optional[List[Dict[str, Any]]] = None,
    variation_index: int = 0,
) -> str:
    """
    Build the full prompt for Gemini image generation.

    Args:
        hat_style: The hat style code (e.g., '6-panel-hat')
        material: The material code (e.g., 'cotton-twill')
        client_name: The brand/client name
        style_direction: The style direction code (e.g., 'modern')
        custom_description: Optional additional style description
        structure: Optional hat structure (structured or unstructured)
        closure: Optional closure type (snapback, metal_slider_buckle, velcro_strap)
        logos: Optional list of logo dicts with 'name' and optional 'location'
        variation_index: Index for generating distinct variations (0, 1, or 2)

    Returns:
        The complete prompt string for image generation
    """
    formatted_style = format_hat_style(hat_style)
    formatted_material = format_material(material)
    formatted_direction = format_style_direction(style_direction)
    formatted_structure = format_structure(structure)
    formatted_closure = format_closure(closure)

    # Combine style direction with custom description if provided
    style_desc = formatted_direction
    if custom_description:
        style_desc = f"{formatted_direction}. {custom_description}"

    # Build construction details if provided
    construction_details = ""
    if formatted_structure or formatted_closure:
        construction_parts = []
        if formatted_structure:
            construction_parts.append(f"Structure: **{formatted_structure}**")
        if formatted_closure:
            construction_parts.append(f"Closure: **{formatted_closure}**")
        construction_details = f"""

HAT CONSTRUCTION:
{chr(10).join('- ' + part for part in construction_parts)}
"""

    # Build logo instructions based on whether multi-logo is provided
    if logos and len(logos) > 0:
        logo_section = build_logo_placement_instructions(logos)
    else:
        logo_section = """IMPORTANT - LOGO USAGE: If a logo image has been provided with this prompt, you MUST use that exact logo in your design. Do NOT search for or use any other logos from the internet. Use ONLY the submitted logo artwork. If no logo is provided, create a simple text-based design using the brand name.

DECORATION LOCATIONS - Use exactly 3 decoration locations:
1. FRONT (required): Always include a decoration on the front of the hat. Methods: flat embroidery, 3D embroidery, PVC patch, woven patch, faux leather patch, embroidered patch, sublimated patch, or 3D printing.
2. SIDE (choose ONE): Decorate EITHER the left side OR right side (not both). Methods: flat embroidery or woven patch.
3. BACK OR UNDERBRIM (choose ONE): Decorate EITHER the back of the hat OR underneath the visor bill (not both). Back methods: flat embroidery or woven patch. Underbrim: sublimated design.

Do NOT add more than 3 decoration locations. Keep the design clean and professional."""

    # Get variation hint
    variation_hint = VARIATION_HINTS[variation_index % len(VARIATION_HINTS)]

    prompt = f"""A photorealistic product shot of a **{formatted_style}** made of **{formatted_material}**.{construction_details}
The hat is viewed from the front, left, right, back, underneath the visor with the front end of the visor pointing down, and worn on a white male model.

The brand is **{client_name}**.

The overall design vibe is **{style_desc}**.

{logo_section}

Professional studio lighting, white background, 4k resolution.

DESIGN VARIATION: {variation_hint}

Add the following legal language to the bottom of the image: {LEGAL_TEXT}"""

    return prompt


def build_revision_prompt(
    original_prompt: str,
    revision_notes: str,
) -> str:
    """
    Build a prompt for design revision.

    Args:
        original_prompt: The original design prompt
        revision_notes: User's requested changes

    Returns:
        The complete prompt for revision
    """
    return f"""{original_prompt}

REVISION REQUESTED:
{revision_notes}

Please generate a revised version of the hat design incorporating the requested changes while maintaining the overall brand aesthetic and quality standards."""
