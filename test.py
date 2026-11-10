from core.llm import call_llm, parse_json
from tools.registry import TOOL_REGISTRY, run_tool, CURRENT_JOB
from core.state import StateMachine, PHASE_TOOLS


sm = StateMachine()
history = []          # the conversation so far

# ---- identity check status (pickup mode) ----
MAX_VERIFY_ATTEMPTS = 3
verified = False      # becomes True only after verify_patient returns "match"
failed_attempts = 0   # how many wrong dates of birth so far


def job_text():
    """Job info for the prompt. Date of birth is NOT included."""
    if len(CURRENT_JOB) == 0:
        return "none"
    return (f"name={CURRENT_JOB['name']}, procedure={CURRENT_JOB['procedure']}, "
            f"waiting_area={CURRENT_JOB['waiting_area']}, destination={CURRENT_JOB['destination']}")


def build_prompt():
    # --- tools allowed in this phase ---
    tool_lines = ""
    for name in PHASE_TOOLS[sm.phase]:
        tool = TOOL_REGISTRY[name]
        tool_lines += f'- "{name}": {tool["description"]} Required fields: {tool["required_fields"]}\n'

    # set_phase is always available (handled by this script, not the registry)
    tool_lines += f'- "set_phase": Move to the next phase. Required fields: ["phase"]. Allowed: {sm.get_allowed_phases()}\n'

    return f"""
You are a hospital guide robot. Calm, short, simple sentences. Never give medical diagnoses.

CURRENT MODE: {sm.mode}
CURRENT PHASE: {sm.phase}
YOUR JOB NOW: {sm.get_instruction()}
PATIENT JOB: {job_text()}

AVAILABLE ACTIONS:
{tool_lines}
Reply ONLY with one JSON object, e.g. {{"action": "speak", "text": "..."}}
When the job of this phase is done, use set_phase to move on.
"""


def escalate_to_staff(reason):
    """No LLM involved: stop the task and call a human."""
    print(f"🚨 STAFF ALERT: {reason}")
    sm.phase = "DONE"     # end the task directly (forced stop, outside normal transitions)
    return f"task stopped, staff notified: {reason}"


def handle_action(action):
    global verified, failed_attempts

    name = action.get("action")

    # 1. phase change → handled by the state machine
    if name == "set_phase":
        new_phase = action.get("phase")

        # RULE 2: can't leave VERIFY towards EXPLAIN without a confirmed match
        if sm.phase == "VERIFY" and new_phase == "EXPLAIN" and not verified:
            return "ERROR: identity not confirmed yet. Use verify_patient first."

        return sm.change_phase(new_phase)

    # 2. tool not allowed in this phase → block it
    if not sm.is_tool_allowed(name):
        return f"ERROR: '{name}' not allowed in phase {sm.phase}"

    # 3. allowed → registry runs it
    result = run_tool(action)

    # 4. after verify_patient: code decides what happens, not the LLM
    if name == "verify_patient":

        if result.startswith("match"):
            verified = True
            return result + " | You may now set_phase to EXPLAIN."

        if result.startswith("no match"):
            failed_attempts += 1

            # RULE 3: too many wrong attempts → get a human
            if failed_attempts >= MAX_VERIFY_ATTEMPTS:
                return escalate_to_staff(f"identity could not be verified after {failed_attempts} attempts")

            # RULE 1: wrong person → back to calling the patient
            sm.change_phase("CALL_PATIENT")
            return (result + f" | Attempt {failed_attempts}/{MAX_VERIFY_ATTEMPTS}. "
                    "Phase is now CALL_PATIENT. Politely tell this person you are looking "
                    "for someone else, then call the patient again.")

    return result


# ===================== ONE ROBOT TURN =====================

def run_turn(message):
    """Add a message to history, then let the robot act until it speaks."""
    history.append({"role": "user", "content": message})

    # up to 5 actions per turn (e.g. navigate, then call_patient)
    for step in range(5):
        if sm.phase == "DONE":
            return

        messages = [{"role": "system", "content": build_prompt()}]
        for msg in history:
            messages.append(msg)

        raw = call_llm(messages)
        action = parse_json(raw)

        if action is None:
            print("ERROR: invalid JSON:", raw)
            return

        result = handle_action(action)
        print(f"   ACTION: {action}")
        print(f"   RESULT: {result}")

        # remember what happened, so the LLM sees it next step
        history.append({"role": "assistant", "content": raw})
        history.append({"role": "user", "content": f"RESULT: {result}"})

        # robot spoke or called someone → wait for the patient
        if action.get("action") in ["speak", "call_patient"]:
            return


# ===================== START =====================

mode = input("Mode (walk_in / pickup): ")

if mode == "pickup":
    CURRENT_JOB["name"]         = input("Patient name: ")
    CURRENT_JOB["dob"]          = input("Date of birth (DD.MM.YYYY): ")
    CURRENT_JOB["procedure"]    = input("Procedure: ")
    CURRENT_JOB["waiting_area"] = input("Waiting area: ")
    CURRENT_JOB["destination"]  = input("Destination: ")

print(sm.start(mode))


# ===================== FIRST TURN (robot starts by itself) =====================

if mode == "pickup":
    run_turn("EVENT: pickup job started. Go to the waiting area and call the patient.")


# ===================== TEXT LOOP =====================

while sm.phase != "DONE":
    user_text = input(f"\n[{sm.phase}] Patient: ")
    if user_text == "exit":
        break

    run_turn(user_text)

print("\n✅ Task finished.")