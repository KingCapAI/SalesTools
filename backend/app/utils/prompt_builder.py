"""Utility for building design generation prompts."""

from typing import Optional, List, Dict, Any

# Legal text to include in generated images
LEGAL_TEXT = """All designs, artwork, and concepts presented herein are the sole property of King Cap and are provided for the exclusive consideration of the intended recipient. These materials are confidential and may not be copied, reproduced, shared, or used in whole or in part for any purpose other than reviewing potential production with King Cap. Any unauthorized use, reproduction, or distribution of these designs is strictly prohibited and may result in legal action."""

# Hat style display names
HAT_STYLES = {
    "6-panel-hat": "6-panel hat",
    "6-panel-trucker": "6-panel trucker hat",
    "5-panel-hat": "A-Frame 5-panel hat",
    "5-panel-trucker": "A-Frame 5-panel trucker hat",
    "perforated-6-panel": "perforated 6-panel hat",
    "perforated-5-panel": "perforated A-Frame 5-panel hat",
}

# Material display names
MATERIALS = {
    "cotton-twill": "cotton twill",
    "performance-polyester": "performance polyester",
    "nylon": "nylon",
    "canvas": "canvas",
    "let-ai-choose": "a high-quality fabric that best fits the design direction",
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
    # Sentinel: when present, build_design_prompt uses ONLY the custom description.
    "describe-below": "",
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


def is_trucker_style(hat_style: str) -> bool:
    """True if the style is a trucker (structured fabric front, mesh back)."""
    return "trucker" in (hat_style or "").lower()


def format_construction(hat_style: str, material: str) -> str:
    """Describe what each part of the hat is made of.

    Trucker styles need explicit mesh-back language: applying the single
    `material` field to the whole hat erases the mesh back panels that
    define a trucker, so the model renders a solid-fabric cap instead.
    """
    let_ai_choose = (material or "").lower() == "let-ai-choose"
    fmt_material = format_material(material)
    if is_trucker_style(hat_style):
        front_clause = (
            "are made of a high-quality fabric that best fits the design direction"
            if let_ai_choose
            else f"are made of {fmt_material}"
        )
        return (
            f"TRUCKER CONSTRUCTION (critical — this defines the hat): the FRONT panels "
            f"{front_clause}; the BACK panels are open-weave polyester MESH. "
            f"The mesh back is the single most defining feature of a trucker hat and MUST "
            f"be clearly visible in the side, back, and model views. Do NOT render a "
            f"solid-fabric back — the back panels must read unmistakably as mesh."
        )
    if let_ai_choose:
        return (
            "The hat is made of a high-quality fabric appropriate for the design "
            "(your choice — pick whichever fabric best fits the style direction)."
        )
    return f"The entire hat is made of {fmt_material}."


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


# Map internal location codes (used in form values) to the canonical
# wearer-perspective label used in prompts and the result template.
# IMPORTANT: "left" and "right" in the form mean "wearer's left/right" —
# the side facing the camera in the WEARERS LEFT / WEARERS RIGHT views
# of the result template.
LOCATION_PROMPT_LABELS: Dict[str, str] = {
    "front": "FRONT",
    "back": "BACK",
    "left": "WEARER'S LEFT side (the side facing the camera in the WEARERS LEFT view of the result template)",
    "right": "WEARER'S RIGHT side (the side facing the camera in the WEARERS RIGHT view of the result template)",
    "visor": "UNDERBILL (inside the visor/brim)",
    "underbill": "UNDERBILL (inside the visor/brim)",
}


def build_logo_placement_instructions(logos: List[Dict[str, Any]]) -> str:
    """Build prompt section describing how to place multiple named logos."""
    lines = []
    lines.append("LOGOS PROVIDED:")

    assigned_logos = []
    unassigned_logos = []

    for logo in logos:
        name = logo.get('name', 'Logo')
        location = (logo.get('location') or '').lower().strip()
        if location:
            label = LOCATION_PROMPT_LABELS.get(location, location.upper())
            assigned_logos.append((name, location))
            lines.append(f"- '{name}' → Place on the **{label}** of the hat")
        else:
            unassigned_logos.append(name)
            lines.append(f"- '{name}' → Place at the best location (AI's choice)")

    lines.append("")
    lines.append("IMPORTANT - LOGO USAGE: Use ONLY the provided logo images labeled above. Do NOT search for or use any other logos from the internet. Each logo image is labeled with its name.")
    lines.append(
        "IMPORTANT - SIDE PERSPECTIVE: All references to 'left' and 'right' are from the WEARER's perspective, "
        "not the viewer's. The wearer's left side is on the right side of the image when viewing the FRONT view. "
        "This must match the WEARERS LEFT / WEARERS RIGHT labels in the result template's 6-view layout."
    )

    if unassigned_logos:
        names = ", ".join(f"'{n}'" for n in unassigned_logos)
        lines.append(
            f"\nFor logos marked as AI's choice ({names}), place them at appropriate locations that complement "
            f"the overall design. Choose from: front, wearer's left side, wearer's right side, back, or underbrim."
        )

    lines.append("""
DECORATION RULES — MAXIMUM 3 LOCATIONS:
Use no more than 3 decoration locations total. Keep the design clean and professional.
Allowed methods per location:
- FRONT: flat embroidery, 3D embroidery, PVC patch, woven patch, faux leather patch, embroidered patch, sublimated patch, or 3D printing.
- WEARER'S LEFT SIDE: flat embroidery, 3D embroidery, woven patch, or sublimated patch ONLY.
- WEARER'S RIGHT SIDE: flat embroidery, 3D embroidery, woven patch, or sublimated patch ONLY.
- BACK: flat embroidery ONLY.
- UNDERBILL (inside visor): sublimated print ONLY.
Do NOT use decoration methods not listed for a given location.""")

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
    construction_sentence = format_construction(hat_style, material)
    formatted_structure = format_structure(structure)
    formatted_closure = format_closure(closure)

    # Style directions may arrive as a single value or as " and "-joined values
    # from the router. Strip the "describe-below" sentinel from the list — when
    # selected, the user is signaling: "ignore preset directions, use my text."
    raw_parts = [p.strip() for p in (style_direction or "").split(" and ") if p.strip()]
    filtered_parts = [p for p in raw_parts if p.lower() != "describe-below"]
    only_describe_below = bool(raw_parts) and not filtered_parts

    if filtered_parts:
        formatted_direction = format_style_direction(" and ".join(filtered_parts))
        style_desc = formatted_direction
        if custom_description:
            style_desc = f"{formatted_direction}. {custom_description}"
    elif only_describe_below and custom_description:
        # User chose "Describe below" → use ONLY their text, no preset framing.
        style_desc = custom_description
    elif custom_description:
        style_desc = custom_description
    else:
        # Final fallback if nothing was provided.
        style_desc = "Modern"

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

IMPORTANT - SIDE PERSPECTIVE: All references to 'left' and 'right' are from the WEARER's perspective, not the viewer's. This must match the WEARERS LEFT / WEARERS RIGHT labels in the result template's 6-view layout.

DECORATION LOCATIONS — MAXIMUM 3 locations. Choose up to 3 from the following:
1. FRONT: Always include a decoration on the front. Methods: flat embroidery, 3D embroidery, PVC patch, woven patch, faux leather patch, embroidered patch, sublimated patch, or 3D printing.
2. SIDE (choose ONE — wearer's left or wearer's right, not both): Methods: flat embroidery, 3D embroidery, woven patch, or sublimated patch ONLY.
3. BACK: Method: flat embroidery ONLY.
4. UNDERBILL (inside visor): Method: sublimated print ONLY.

STRICT: Do NOT use more than 3 decoration locations. Do NOT use decoration methods not listed for a given location. Keep the design clean and professional."""

    # Get variation hint
    variation_hint = VARIATION_HINTS[variation_index % len(VARIATION_HINTS)]

    prompt = f"""RENDERING STYLE — READ FIRST:
The output is a PHOTOREALISTIC studio product photograph composed in a 3x2 grid.
- All six cells must look like real photographs of a real physical hat (and a real human in cell 6).
- DO NOT produce cartoon, illustration, line-art, vector-flat, watercolor, painted, sketched, or otherwise stylized output.
- The layout template image provided alongside this prompt is itself a cartoon line-art illustration — that is for STRUCTURE ONLY. Its art style must NOT appear in your output.
- Lighting: soft professional studio lighting. Background: clean neutral white (#f5f5f7-ish). Materials: realistic fabric weave, stitching, and shadow detail.

A photorealistic product shot of a **{formatted_style}**.

CONSTRUCTION & MATERIALS: {construction_sentence}{construction_details}

The brand is **{client_name}**.

The overall design vibe is **{style_desc}**.

{logo_section}

DECORATION METHOD CALLOUTS:
Label each unique decoration ONCE across the entire image. Rules:
- Each decoration method should be labeled EXACTLY ONCE in the view where it is most clearly visible. Do NOT label the same decoration in multiple views.
- Format: thin line or arrow from label to the decoration it identifies.
- Label text = exact method name, e.g. "Flat Embroidery", "3D Embroidery", "PVC Patch", "Woven Patch", "Sublimated Patch", "Sublimated Print".
- Style: clean sans-serif font, black text on a small white pill/tag background.
- Do NOT add ANY labels to the MODEL VIEW (view #6). The model view should be clean with no callouts.
- Only label decorations in hat-only views (views 1-5). Pick the view where each decoration is most prominent.

IMAGE LAYOUT — Match the provided LAYOUT TEMPLATE image precisely. The template defines a 3x2 grid with EXACTLY 6 UNIQUE VIEWS. Use the template ONLY for grid composition and angle labels — do not copy its hat shape, colors, or design.

Each view shows the SAME hat from a DIFFERENT angle. Same design, same colors, same logos, same decorations in every view.

Top row:
1. **FRONT** (top-left) — hat facing camera straight-on, front panel visible
2. **WEARERS RIGHT** (top-center) — hat rotated so the WEARER'S RIGHT side faces the camera; the brim points to the LEFT side of the image
3. **WEARERS LEFT** (top-right) — hat rotated so the WEARER'S LEFT side faces the camera; the brim points to the RIGHT side of the image

Bottom row:
4. **BACK** (bottom-left) — hat rotated 180°, back panel and closure visible
5. **UNDERVISOR** (bottom-center) — hat flipped to show the underside of the visor/brim and the sweatband
6. **MODEL** (bottom-right) — PHOTOREALISTIC professional studio photograph of a real adult male model wearing the hat, head-and-shoulders portrait. This must look like an actual photo of a real person — NOT a cartoon, NOT an illustration, NOT a stylized drawing, NOT line-art. Skin, hair, fabric textures must all read as photographic. Ignore the cartoon person shown in the layout template — the template's art style is for layout reference only and must NOT be reproduced in this cell.

Place the angle labels (FRONT, WEARERS RIGHT, WEARERS LEFT, BACK, UNDERVISOR, MODEL) under each box exactly as shown in the LAYOUT TEMPLATE.

STRICT RULES:
- Exactly 6 views. Not 4, not 5, not 7, not 8. Exactly 6.
- Each view must show a DIFFERENT angle — no duplicate or near-duplicate views.
- WEARERS RIGHT and WEARERS LEFT are mirror images — they must NOT look the same. WEARERS RIGHT shows the right side panel from the wearer's perspective; WEARERS LEFT shows the left side panel from the wearer's perspective.
- The design must be IDENTICAL across all views — do not change decorations, colors, or logos between views.

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
