TOOL_REGISTRY = {}
CURRENT_JOB = {}

def register_tool(name, required_fields, description):
    """Decorator: attaches a function to the registry under `name`."""
    def wrapper(func):
        TOOL_REGISTRY[name] = {
            "function": func,
            "required_fields": required_fields,
            "description": description,
        }
        return func
    return wrapper


def run_tool(action):
    # `action` is the dict from the LLM, e.g. {"action": "speak", "text": "Hello"}

    name = action.get("action")               # get the tool name → "speak"

    if name not in TOOL_REGISTRY:             # is this tool in the phone book?
        return f"ERROR: unknown tool '{name}'"

    tool = TOOL_REGISTRY[name]                # get the tool's entry

    # --- check for missing fields ---
    missing = []                              # start with an empty list
    for field in tool["required_fields"]:     # go through each required field
        if field not in action:               # not in the action?
            missing.append(field)             # → remember it

    if len(missing) > 0:                      # something is missing → error
        return f"ERROR: '{name}' missing fields {missing}"

    # --- collect only the values the tool needs ---
    args = {}                                 # start with an empty dict
    for field in tool["required_fields"]:     # for each required field
        args[field] = action[field]           # copy its value from the action

    # --- run the tool ---
    return tool["function"](**args)           # e.g. speak(text="Hello")
# ===================== TOOLS =====================

@register_tool("speak", ["text"], "Say something to the patient.")
def speak(text):
    print(f"🤖 Baymax: {text}")
    return "spoken"


@register_tool("navigate", ["location"], "Start guiding the patient to a location.")
def navigate(location):
    # GHOST: real implementation later in ROS 2
    print(f"🧭 NAVIGATION REQUESTED → {location}")
    return f"navigation_requested: {location}"

@register_tool("call_patient", ["name"], "Call out a patient's name in the waiting area.")
def call_patient(name):
    print(f"📢 ANNOUNCEMENT: {name}, please come to the robot.")
    return f"called: {name}"

@register_tool("verify_patient", ["dob"],
               "Check the date of birth the patient told you. Pass it exactly as DD.MM.YYYY.")
def verify_patient(dob):
    expected = CURRENT_JOB.get("dob")
    if expected is None:
        return "ERROR: no patient job loaded"

    # keep only the digits, so "12.03.1985" and "12/03/1985" both match
    given_digits = ""
    for char in dob:
        if char.isdigit():
            given_digits += char

    expected_digits = ""
    for char in expected:
        if char.isdigit():
            expected_digits += char

    if given_digits == expected_digits:
        return "match: identity confirmed"
    return "no match: this is not the right patient"
# ===================== TEST =====================
if __name__ == "__main__":
    print("Registered tools:", list(TOOL_REGISTRY.keys()))
    print()

    tests = [
        {"action": "speak", "text": "Hello, please follow me."},
        {"action": "navigate", "location": "xray_room"},
        {"action": "speak"},                        # missing field
        {"action": "fly", "destination": "moon"},   # unknown tool
    ]

    for t in tests:
        print("INPUT :", t)
        print("RESULT:", run_tool(t))
        print()