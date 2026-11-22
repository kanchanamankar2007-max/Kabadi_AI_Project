import os
import json
import hashlib
from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# 1. CONFIGURATION
# ==========================================

load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

st.set_page_config(
    page_title="Kabadi AI",
    page_icon="♻️",
    layout="wide"
)

CATEGORIES = [
    "Wet Waste",
    "Dry Waste",
    "E-Waste",
    "Plastic Waste",
    "Uncertain"
]

LANGUAGES = {
    "English": "English",
    "हिन्दी (Hindi)": "Hindi",
    "বাংলা (Bengali)": "Bengali",
    "தமிழ் (Tamil)": "Tamil",
    "తెలుగు (Telugu)": "Telugu",
    "मराठी (Marathi)": "Marathi",
    "ಕನ್ನಡ (Kannada)": "Kannada",
    "മലയാളം (Malayalam)": "Malayalam",
    "ગુજરાતી (Gujarati)": "Gujarati",
    "ਪੰਜਾਬੀ (Punjabi)": "Punjabi",
    "اردو (Urdu)": "Urdu",
}

ICONS = {
    "Wet Waste": "💧",
    "Dry Waste": "♻️",
    "E-Waste": "🔌",
    "Plastic Waste": "🧴",
    "Uncertain": "❓"
}

# These are example starting values, NOT verified
# current market prices. Replace them with local rates.
DEFAULT_RATES = {
    "PET Plastic": 0.0,
    "Mixed Plastic": 0.0,
    "Cardboard": 0.0,
    "Newspaper": 0.0,
    "Aluminium": 0.0,
    "Iron": 0.0,
    "Glass": 0.0,
    "Electronic Waste": 0.0,
    "Organic Waste": 0.0,
    "Other": 0.0
}

MATERIAL_TO_RATE = {
    "pet plastic": "PET Plastic",
    "plastic": "Mixed Plastic",
    "mixed plastic": "Mixed Plastic",
    "cardboard": "Cardboard",
    "paper": "Newspaper",
    "newspaper": "Newspaper",
    "aluminium": "Aluminium",
    "aluminum": "Aluminium",
    "iron": "Iron",
    "steel": "Iron",
    "glass": "Glass",
    "electronic": "Electronic Waste",
    "e-waste": "Electronic Waste",
    "organic": "Organic Waste",
    "food": "Organic Waste"
}


# ==========================================
# 2. AI WASTE CLASSIFICATION
# ==========================================

def identify_waste(image, output_language):

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash-lite"
    )

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. "
            "Please configure your .env file."
        )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=45_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    image = image.copy()
    image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)

    prompt = """
You are Kabadi AI, a waste classification assistant
designed for Indian households.

Analyse the actual image supplied by the user.
Write item_name, material, reason, recommended_bin,
disposal_instructions, and safety_note in [OUTPUT_LANGUAGE].
Keep category exactly one of the canonical English category
names below, and confidence exactly High, Medium, or Low.

Classify the visible waste into exactly one category:

1. Wet Waste
   Food leftovers, vegetable peels, fruit scraps,
   and other biodegradable organic waste.

2. Dry Waste
   Paper, cardboard, newspapers, glass, and metal.

3. E-Waste
   Old phones, computers, chargers, keyboards,
   circuit boards, and discarded electronic devices.

4. Plastic Waste
   Plastic bottles, containers, bags, and packaging.

5. Uncertain
   Use when the image is unclear or the material
   cannot be identified reliably.

Rules:
- Identify the main visible item.
- Do not guess when the image is unclear.
- If several items are visible, mention that.
- Do not confuse dirty plastic with wet organic waste.
- An electronic device remains E-Waste even if its
  casing is plastic.
- Distinguish a material from its waste category.
- Give practical disposal recommendations.
- Do not invent the item's weight or scrap price.
- Do not claim that all plastic or glass is recyclable.
- Warn users to take batteries and electronics to
  appropriate authorised collection services.
- Explain uncertainty honestly.

Return ONLY valid JSON in this structure:

{
  "item_name": "Name of visible item",
  "category": "Wet Waste, Dry Waste, E-Waste, Plastic Waste, or Uncertain",
  "material": "Likely material",
  "confidence": "High, Medium, or Low",
  "reason": "Explanation of classification",
  "recommended_bin": "Suggested segregation category",
  "disposal_instructions": "Practical disposal guidance",
  "safety_note": "Relevant safety advice"
}
"""
    prompt = prompt.replace("[OUTPUT_LANGUAGE]", output_language)

    try:
        response = client.models.generate_content(
            model=model,
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=500,
            )
        )

        if not response.text:
            raise ValueError("The AI returned an empty response.")

        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.removeprefix("```json")
            response_text = response_text.removeprefix("```")
            response_text = response_text.rsplit("```", 1)[0].strip()

        result = json.loads(response_text)

        category = result.get("category")

        if category not in CATEGORIES:
            raise ValueError("The AI returned an unsupported category.")

        required_fields = [
            "item_name",
            "material",
            "confidence",
            "reason",
            "recommended_bin",
            "disposal_instructions",
            "safety_note"
        ]

        for field in required_fields:
            if not isinstance(result.get(field), str):
                raise ValueError(f"Missing or invalid field: {field}")

        return result

    except Exception as error:
        raise RuntimeError(
            f"Waste identification failed: {error}"
        ) from error


# ==========================================
# 3. SCRAP VALUE CALCULATION
# ==========================================

def calculate_scrap_value(weight_kg, price_per_kg):

    if weight_kg < 0 or price_per_kg < 0:
        raise ValueError(
            "Weight and price cannot be negative."
        )

    return weight_kg * price_per_kg


def get_rate_name(material):

    material_lower = material.lower()

    for keyword, rate_name in MATERIAL_TO_RATE.items():

        if keyword in material_lower:
            return rate_name

    return "Other"


def explain_api_error(error):

    error_text = str(error).lower()

    if "api key" in error_text and any(
        phrase in error_text
        for phrase in ["invalid", "not valid", "unauthenticated"]
    ):
        return (
            "Gemini rejected the API key. Check that GEMINI_API_KEY "
            "is valid, active, and has no extra quotes or spaces."
        )

    if any(code in error_text for code in ["403", "permission denied", "forbidden"]):
        return (
            "Gemini denied access. Check that the key has access to the "
            "Generative Language API and that billing or usage restrictions "
            "are not blocking the request."
        )

    if any(code in error_text for code in ["404", "not found"]):
        return (
            "The configured Gemini model was not found or is unavailable "
            "for this key. Set GEMINI_MODEL to a model enabled for your account."
        )

    if any(code in error_text for code in ["429", "resource_exhausted", "quota"]):
        return (
            "The Gemini API quota or rate limit was reached. Check the key's "
            "quota and try again later."
        )

    if any(code in error_text for code in ["503", "500", "504", "unavailable", "deadline_exceeded"]):
        if "504" in error_text or "deadline_exceeded" in error_text:
            return (
                "Gemini did not finish the request before its deadline. "
                "Try again, or use a smaller/clearer image."
            )
        return "Gemini is temporarily unavailable. Please try again shortly."

    if any(code in error_text for code in ["timeout", "connection", "network"]):
        return (
            "The app could not reach Gemini. Check the internet connection "
            "and any firewall or proxy settings."
        )

    return f"Gemini analysis failed: {error}"


# ==========================================
# 4. USER INTERFACE
# ==========================================

st.title("♻️ Kabadi AI")
st.subheader(
    "Smart Waste Management & Recycling Platform"
)

st.write(
    "Upload a waste image, identify its category, "
    "learn responsible disposal, and estimate its value."
)

st.info(
    "AI classifications are predictions. "
    "Confirm uncertain results before disposing of waste."
)

analysis_language = LANGUAGES[
    st.selectbox("Analysis language", list(LANGUAGES))
]


# ==========================================
# 5. LOCAL KABADI-WALA INFORMATION
# ==========================================

with st.expander("📍 Local Kabadi-wala information"):

    st.caption(
        "Enter verified local information. This is not a live directory; "
        "a count of 0 means no count has been entered, not that none exist."
    )

    st.text_input(
        "Location (city / PIN code)",
        key="kabadi_location"
    )

    st.number_input(
        "Number of nearby Kabadi walas (verified count)",
        min_value=0,
        max_value=1000000,
        step=1,
        key="kabadi_count"
    )

    st.text_input(
        "Count source / date checked",
        key="kabadi_count_source"
    )

# ==========================================
# 6. SCRAP PRICE SETTINGS
# ==========================================

with st.expander("⚙️ Configure local scrap prices"):

    st.write(
        "Enter prices verified with a local Kabadi buyer. "
        "All prices are in INR per kilogram."
    )
    st.caption(
        "These are manually entered local rates, not live market prices."
    )

    if "rates" not in st.session_state:
        st.session_state.rates = DEFAULT_RATES.copy()

    st.text_input(
        "Rate source / date checked",
        key="rate_source"
    )

    for material_name in DEFAULT_RATES:

        current_rate = st.session_state.rates[material_name]

        new_rate = st.number_input(
            f"{material_name} (₹/kg)",
            min_value=0.0,
            max_value=100000.0,
            value=float(current_rate),
            step=1.0,
            key=f"rate_{material_name}"
        )

        st.session_state.rates[material_name] = new_rate

    st.caption(
        "These settings are for the current application session. "
        "Connect a database for persistent price management."
    )


# ==========================================
# 7. IMAGE UPLOAD
# ==========================================

uploaded_file = st.file_uploader(
    "Upload a photograph of your waste",
    type=["jpg", "jpeg", "png", "webp"],
    help="Use a clear photo with good lighting."
)

if uploaded_file is not None:

    if uploaded_file.size > 10 * 1024 * 1024:

        st.error(
            "Image is too large. Please upload an image "
            "smaller than 10 MB."
        )

    else:

        try:

            image = Image.open(uploaded_file).convert("RGB")

            upload_signature = (
                hashlib.sha256(uploaded_file.getvalue()).hexdigest(),
                analysis_language,
            )

            if st.session_state.get("upload_signature") != upload_signature:
                st.session_state["upload_signature"] = upload_signature
                st.session_state.pop("waste_result", None)

            st.image(
                image,
                caption="Uploaded waste image",
                width=400
            )

            if st.button(
                "🔍 Identify Waste with AI",
                type="primary"
            ):

                with st.spinner(
                    "Kabadi AI is analysing your image (image is resized before upload; request timeout is 45 seconds)..."
                ):

                    try:

                        result = identify_waste(image, analysis_language)

                        st.session_state["waste_result"] = result

                    except Exception as error:

                        st.error(
                            explain_api_error(error)
                        )

                        with st.expander("Technical details"):
                            st.code(str(error))

            # Show the latest successful result.
            result = st.session_state.get("waste_result")

            if result:

                st.divider()

                category = result["category"]

                st.header("Waste Identification Result")

                st.subheader(
                    f"{ICONS[category]} {category}"
                )

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        "**Identified item:**",
                        result["item_name"]
                    )

                    st.write(
                        "**Material:**",
                        result["material"]
                    )

                    st.write(
                        "**Confidence:**",
                        result["confidence"]
                    )

                with col2:

                    st.write(
                        "**Suggested bin:**",
                        result["recommended_bin"]
                    )

                    st.write(
                        "**Reason:**",
                        result["reason"]
                    )

                st.success(
                    "**Disposal guidance:** "
                    + result["disposal_instructions"]
                )

                st.warning(
                    "**Safety advice:** "
                    + result["safety_note"]
                )

                # ==================================
                # 7. WEIGHT AND SCRAP VALUE
                # ==================================

                st.divider()

                st.header("⚖️ Weight & Scrap Value")

                st.write(
                    "Enter the actual measured weight. "
                    "A photograph alone cannot reliably "
                    "determine weight in kilograms."
                )

                material = result["material"]
                rate_name = get_rate_name(material)

                default_rate = st.session_state.rates.get(
                    rate_name, 0.0
                )

                weight_unit = st.radio(
                    "Measured weight unit",
                    ["kg", "g"],
                    horizontal=True,
                )

                weight_value = st.number_input(
                    f"Measured waste weight ({weight_unit})",
                    min_value=0.0,
                    max_value=10000.0 if weight_unit == "kg" else 10000000.0,
                    value=1.0,
                    step=0.1 if weight_unit == "kg" else 1.0,
                    key=f"waste_weight_{weight_unit}"
                )
                weight_kg = (
                    weight_value if weight_unit == "kg"
                    else weight_value / 1000
                )

                st.write(
                    f"Material rate category: **{rate_name}**"
                )

                price_per_kg = float(default_rate)
                st.metric(
                    "Configured local rate",
                    f"₹{price_per_kg:,.2f}/kg"
                )

                if category in [
                    "Wet Waste",
                    "Uncertain"
                ]:

                    st.info(
                        "A reliable scrap price is not "
                        "automatically assigned to this category. "
                        "Enter a verified rate in the price settings "
                        "only if applicable."
                    )

                if st.button("Calculate Estimated Value"):

                    if weight_kg <= 0:

                        st.warning(
                            "Enter a measured weight greater than zero."
                        )

                    elif price_per_kg <= 0:

                        st.warning(
                            "No local rate is configured for this material. "
                            "Add a verified rate in the price settings first."
                        )

                    else:

                        total_value = calculate_scrap_value(
                            weight_kg,
                            price_per_kg
                        )

                        st.metric(
                            "Estimated Scrap Value",
                            f"₹{total_value:,.2f}"
                        )

                        st.caption(
                            f"{weight_value:.2f} {weight_unit} "
                            f"({weight_kg:.3f} kg) × "
                            f"₹{price_per_kg:.2f}/kg = "
                            f"₹{total_value:.2f}"
                        )

                        st.caption(
                            "This is an estimate, not a guaranteed "
                            "offer from a recycling buyer."
                        )

        except (UnidentifiedImageError, OSError, ValueError) as error:

            st.error(
                "The image could not be processed. "
                "Please upload a valid JPG, PNG, or WebP image."
            )

            with st.expander("Technical details"):
                st.code(str(error))


# ==========================================
# 8. FOOTER
# ==========================================

st.divider()

st.caption(
    "Kabadi AI | Household Scrap Intelligence | "
    "AI-assisted waste classification and recycling."
)