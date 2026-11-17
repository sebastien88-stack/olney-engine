from olney_engine import OlneyEngine

engine = OlneyEngine()

# This is what your Olney backend can expose as a tool.
result = engine.tool_get_state(
    birth_date="1965-05-18",
    target_date="2025-02-20",
    target_time="12:00",
    target_place="Longjumeau, FR",
)

# Send `result` to the LLM as structured tool output.
# The LLM should interpret it, never recalculate it.
print(result["birth"])
print(result["time"])
print(result["year"])
print(result["week"])
print(result["day"])
print(result["hour_card"])
