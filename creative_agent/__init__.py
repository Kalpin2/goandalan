"""Modular 4-Role Instagram Creative Agent + 4-Layer Typography & Niche Resolver for @goandalan."""

from creative_agent.style_registry import (
    STYLE_LIBRARY_12,
    STORYTELLING_METHODS,
    COMPOSITION_METHODS,
    DEMO_STYLE_TO_CAROUSEL_STYLE,
    extract_palette_from_image,
    resolve_style_key,
)
from creative_agent.typography_engine import (
    ART_DIRECTIONS_30,
    TYPEFACE_CLASSIFICATIONS,
    assert_core_library_integrity,
    plan_typography_direction,
    audit_typography_anti_patterns,
    record_carousel_to_learning_log,
    add_candidate_to_library,
    record_learning_cycle,
)
from creative_agent.niche_resolver import (
    NICHE_BLUEPRINTS,
    resolve_niche_blueprint,
    check_registry_skill_coverage,
    audit_repo_with_skillspector,
)
from creative_agent.creative_director import CreativeDirector
from creative_agent.carousel_planner import CarouselPlanner
from creative_agent.visual_designer import VisualDesigner
from creative_agent.design_reviewer import DesignReviewer
from creative_agent.copy_engine import (
    assert_copy_library_integrity,
    route_voice_for_lead,
    draft_cold_dm,
    draft_followup,
    draft_cold_call,
    draft_recycled_caption,
    validate_copy,
    log_copy_event,
    update_copy_outcome,
    summarize_human_edit,
)
from creative_agent.lead_enricher import (
    resolve_agent_reach_bin,
    validate_public_http_url,
    extract_instagram_handle,
    analyze_website_ux_flaw,
    fetch_ig_observation,
    enrich_new_lead,
    enrich_new_leads,
)

from creative_agent.token_optimizer import (
    compact_scrape_text,
    compute_edit_delta,
    build_learning_digest,
    evaluate_learning_signals,
    get_relevant_pattern_slice,
)

__all__ = [
    "STYLE_LIBRARY_12",
    "STORYTELLING_METHODS",
    "COMPOSITION_METHODS",
    "DEMO_STYLE_TO_CAROUSEL_STYLE",
    "ART_DIRECTIONS_30",
    "TYPEFACE_CLASSIFICATIONS",
    "NICHE_BLUEPRINTS",
    "extract_palette_from_image",
    "resolve_style_key",
    "plan_typography_direction",
    "audit_typography_anti_patterns",
    "record_carousel_to_learning_log",
    "add_candidate_to_library",
    "record_learning_cycle",
    "resolve_niche_blueprint",
    "check_registry_skill_coverage",
    "audit_repo_with_skillspector",
    "CreativeDirector",
    "CarouselPlanner",
    "VisualDesigner",
    "DesignReviewer",
    "assert_copy_library_integrity",
    "route_voice_for_lead",
    "draft_cold_dm",
    "draft_followup",
    "draft_cold_call",
    "draft_recycled_caption",
    "validate_copy",
    "log_copy_event",
    "update_copy_outcome",
    "summarize_human_edit",
    "resolve_agent_reach_bin",
    "validate_public_http_url",
    "extract_instagram_handle",
    "analyze_website_ux_flaw",
    "fetch_ig_observation",
    "enrich_new_lead",
    "enrich_new_leads",
    "compact_scrape_text",
    "compute_edit_delta",
    "build_learning_digest",
    "evaluate_learning_signals",
    "get_relevant_pattern_slice",
]
