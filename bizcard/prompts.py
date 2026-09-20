"""Prompt sent to the vision-language model together with each card image."""

EXTRACTION_PROMPT = (
    "You are reading a business card. Extract the contact details and return ONLY a valid "
    "JSON object with exactly these keys: first_name, last_name, position, company, "
    "location, phone, email.\n"
    "Rules:\n"
    "- location is the city / state / country taken from the address on the card.\n"
    "- If there are several phone numbers, join them with ', '.\n"
    "- Copy text exactly as printed. Do not guess or invent anything.\n"
    "- Use null for any field that is not visible on the card.\n"
    "- No explanation and no markdown, JSON only."
)
