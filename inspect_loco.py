import altrios as alt
import json

# Ensure lib loaded
try:
    loco = alt.Locomotive.default()
    print("Locomotive Default Structure:")
    # Use to_json then parse to avoid complex object printing
    print(loco.to_json())
except Exception as e:
    print(f"Error: {e}")
