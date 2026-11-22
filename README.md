# Kabadi AI — beginner setup

## 1. Files
- `app.py`: Streamlit application
- `requirements.txt`: Python packages

## 2. Create your private `.env` file
In the same folder as `app.py`, create a file named `.env` with:
```
GEMINI_API_KEY=PASTE_YOUR_REAL_KEY_HERE
GEMINI_MODEL=gemini-3.5-flash-lite
```
Get a key through Google AI Studio. Do not share the key or upload `.env` to GitHub.

The app loads `.env` from the folder containing `app.py`, even when Streamlit is launched from another working directory. If this model is unavailable to your account, set `GEMINI_MODEL` to a model currently enabled for your key.

## 3. Install and run (Windows / VS Code terminal)
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
If `python` is not recognized, install Python and make sure “Add Python to PATH” is selected, then reopen VS Code.

## Important limits
- AI classification requires internet access and a valid Gemini API key.
- External API outages, quotas, invalid keys, and model access can still prevent a request from succeeding; the app displays an actionable error and retries some temporary failures.
- AI result text can be requested in English, Hindi, Bengali, Tamil, Telugu, Marathi, Kannada, Malayalam, Gujarati, Punjabi, or Urdu.
- The photo identifies likely category/material only. It cannot reliably determine actual physical weight. Weigh the waste using a scale.
- Enter your measured weight in grams or kilograms. The estimated value uses the configured local rate for the identified material.
- Prices start at ₹0 intentionally. Enter rates verified with a local scrap dealer; these are manual rates, not live market prices. The Kabadi-wala count is also manually entered and is not a live directory. A live local count or current-rate feed requires a location and a suitable data provider/API.
- AI classification can be wrong; check safety instructions and local waste rules.
