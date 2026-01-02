# -*- coding: utf-8 -*-
"""Image generation service using Google Gemini API (Nano Banana 2).

This module provides AI image generation for Agent avatars using
the Gemini 2.5 Flash Image model.
"""

import base64
import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_gemini_client():
    """Get Gemini client for image generation.

    Returns:
        tuple: (client, api_key) or (None, None) if not configured
    """
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        logger.warning("No GEMINI_API_KEY or GOOGLE_API_KEY found")
        return None, None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return client, api_key
    except ImportError:
        logger.error("google-genai package not installed")
        return None, None
    except Exception as e:
        logger.error("Failed to initialize Gemini client: %s", e)
        return None, None


def generate_agent_avatar(
    agent_name: str,
    agent_description: str,
    agent_id: str,
    style: str = "professional",
) -> dict:
    """Generate an avatar image for an Agent using Nano Banana 2.

    Args:
        agent_name: The name/role of the agent (e.g., "Frontend Developer")
        agent_description: Description of the agent's capabilities
        agent_id: Unique identifier for the agent
        style: Avatar style - "professional", "cartoon", "pixel", "3d"

    Returns:
        dict with:
            - success: bool
            - image_data: base64 encoded image (if success)
            - image_url: URL to saved image (if success)
            - error: error message (if failed)
    """
    client, api_key = _get_gemini_client()

    if client is None:
        return {
            "success": False,
            "error": "Gemini API not configured. Set GEMINI_API_KEY environment variable.",
        }

    # Build prompt for avatar generation
    style_prompts = {
        "professional": "modern professional avatar, clean design, subtle gradient background",
        "cartoon": "cute cartoon character avatar, vibrant colors, friendly expression",
        "pixel": "pixel art avatar, retro gaming style, 8-bit aesthetic",
        "3d": "3D rendered character avatar, soft lighting, modern CGI style",
    }

    style_desc = style_prompts.get(style, style_prompts["professional"])

    # Create a prompt that generates consistent, professional avatars
    prompt = f"""Create a single avatar icon for an AI Agent with the following characteristics:

Role: {agent_name}
Description: {agent_description}

Style requirements:
- {style_desc}
- Single centered character or icon
- Circular or rounded square composition suitable for avatar use
- High contrast, easily recognizable at small sizes
- No text or labels in the image
- Professional tech industry aesthetic
- Symbolic representation of the role (e.g., code symbols for developers, database icons for data experts)

Generate a unique, visually appealing avatar that represents this AI agent's role and expertise."""

    try:
        logger.info("Generating avatar for agent: %s", agent_id)

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
        )

        # Extract image from response
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/png"

                # Save image to static directory
                image_url = _save_avatar_image(agent_id, image_data, mime_type)

                logger.info("Avatar generated successfully for: %s", agent_id)
                return {
                    "success": True,
                    "image_data": image_data,
                    "mime_type": mime_type,
                    "image_url": image_url,
                }

        logger.warning("No image data in Gemini response for: %s", agent_id)
        return {
            "success": False,
            "error": "No image generated in response",
        }

    except Exception as e:
        logger.error("Avatar generation failed for %s: %s", agent_id, e)
        return {
            "success": False,
            "error": str(e),
        }


def _save_avatar_image(agent_id: str, image_data: str, mime_type: str) -> str:
    """Save avatar image to static directory.

    Args:
        agent_id: Agent identifier
        image_data: Base64 encoded image data
        mime_type: MIME type of the image

    Returns:
        URL path to the saved image
    """
    # Determine file extension
    ext_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }
    ext = ext_map.get(mime_type, ".png")

    # Create filename from agent_id hash
    filename = f"agent_{hashlib.md5(agent_id.encode()).hexdigest()[:12]}{ext}"

    # Get static directory path
    static_dir = Path(__file__).parent.parent / "static" / "avatars"
    static_dir.mkdir(parents=True, exist_ok=True)

    # Save image
    image_path = static_dir / filename
    with open(image_path, "wb") as f:
        f.write(base64.b64decode(image_data))

    logger.info("Avatar saved to: %s", image_path)

    # Return URL path (relative to static root)
    return f"/static/avatars/{filename}"


def generate_avatars_batch(
    agents: list[dict],
    style: str = "professional",
) -> list[dict]:
    """Generate avatars for multiple agents.

    Args:
        agents: List of dicts with 'agent_id', 'name', 'description'
        style: Avatar style

    Returns:
        List of dicts with 'agent_id' and 'avatar_url' or 'error'
    """
    results = []

    for agent in agents:
        result = generate_agent_avatar(
            agent_name=agent.get("name", "AI Agent"),
            agent_description=agent.get("description", ""),
            agent_id=agent.get("agent_id", "unknown"),
            style=style,
        )

        results.append({
            "agent_id": agent.get("agent_id"),
            "avatar_url": result.get("image_url") if result["success"] else None,
            "error": result.get("error") if not result["success"] else None,
        })

    return results
