"""Static constants shared across FRAMEFORGE AI."""

APP_NAME = "FRAMEFORGE AI"
SUBTITLE = "INTELLIGENT FILM PRODUCTION MANAGEMENT"
TAGLINE = "From Script to Production. One Intelligent Black Book."

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt")
INT_EXT = ["INT", "EXT", "INT/EXT", "UNKNOWN"]
TIMES_OF_DAY = ["DAY", "NIGHT", "DAWN", "DUSK", "MORNING", "AFTERNOON",
                "EVENING", "CONTINUOUS", "UNKNOWN"]
COMPLEXITY = ["Low", "Medium", "High"]
SCENE_STATUSES = ["Not Started", "Planned", "In Progress", "Completed", "On Hold"]
SOURCE_TYPES = ["EXPLICIT", "INFERRED", "RECOMMENDED"]
SOURCE_RANK = {"EXPLICIT": 0, "INFERRED": 1, "RECOMMENDED": 2}
RESOURCE_CATEGORIES = ["Prop", "Costume", "Equipment", "Vehicle", "Special Effect", "Other"]
REVIEW_STATUSES = ["DRAFT", "UNDER REVIEW", "APPROVED"]

# Generic gear that adds no information to a breakdown; filtered from AI equipment suggestions.
GENERIC_EQUIPMENT = {
    "camera", "cameras", "lights", "lighting", "tripod", "microphone", "microphones",
    "sound equipment", "audio equipment", "lighting equipment", "camera equipment",
    "basic lighting", "standard lighting", "boom mic", "boom microphone", "lens", "lenses",
    "camera and lighting", "camera and sound", "standard camera setup", "monitor",
}

NAV_PAGES = [
    "Dashboard", "New Production", "My Projects", "Script Analysis", "Scene Breakdown",
    "Character Register", "Locations", "Production Resources", "Shooting Schedule",
    "Call Sheets", "Production Progress", "Black Book", "AI Production Assistant", "Settings",
]

STAGES = ["chunking", "scene_extraction", "registers", "story_analysis"]
DISCLAIMER = ("This document was prepared with AI assistance from the supplied screenplay. "
              "AI-generated and inferred information must be reviewed by the production team "
              "before it is relied upon. Schedules are proposals, not confirmed bookings.")
