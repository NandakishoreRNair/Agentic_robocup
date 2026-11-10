# ===================== PHASES =====================
# Every step the conversation can be in.

GREET        = "GREET"         # Mode 1: patient walked up
IDENTIFY     = "IDENTIFY"      # Mode 1: find out where patient needs to go
CALL_PATIENT = "CALL_PATIENT"  # Mode 2: robot calls patient in waiting area
VERIFY       = "VERIFY"        # Mode 2: confirm it's the right patient
EXPLAIN      = "EXPLAIN"       # both: explain the procedure
GUIDE        = "GUIDE"         # both: take patient to the location
HANDOVER     = "HANDOVER"      # both: arrived, hand over to staff
DONE         = "DONE"          # finished


# ===================== START PHASE FOR EACH MODE =====================

START_PHASE = {
    "walk_in": GREET,          # Mode 1
    "pickup":  CALL_PATIENT,   # Mode 2
}


# ===================== ALLOWED TRANSITIONS =====================
# From each phase, which phases may come next.

TRANSITIONS = {
    GREET:        [IDENTIFY],
    IDENTIFY:     [EXPLAIN, GUIDE],
    CALL_PATIENT: [VERIFY],
    VERIFY:       [EXPLAIN, CALL_PATIENT],   # wrong person → call again
    EXPLAIN:      [GUIDE, IDENTIFY],
    GUIDE:        [HANDOVER, EXPLAIN],       # patient may ask a question while walking
    HANDOVER:     [DONE],
    DONE:         [],
}


# ===================== INSTRUCTIONS FOR THE LLM =====================
# One job per phase. This goes into the prompt later.

PHASE_INSTRUCTIONS = {
    GREET:        "Greet the patient warmly and ask how you can help.",
    IDENTIFY:     "Find out which appointment or place the patient needs.",
    CALL_PATIENT: "Call out the patient's name in the waiting area.",
    VERIFY:       "Confirm the patient's identity (full name and date of birth) before continuing.",
    EXPLAIN:      "Explain the procedure in simple, calm words. Ask if they have questions.",
    GUIDE:        "Ask the patient to follow you and start navigation to the destination.",
    HANDOVER:     "Tell the patient they have arrived and what happens next.",
    DONE:         "The task is finished.",
}


# ===================== ALLOWED TOOLS PER PHASE =====================
# Tools not listed here are blocked in that phase.

PHASE_TOOLS = {
    GREET:        ["speak"],
    IDENTIFY:     ["speak"],
    CALL_PATIENT: ["speak", "navigate"],   # navigate to the waiting area
    VERIFY:       ["speak"],
    EXPLAIN:      ["speak"],
    GUIDE:        ["speak", "navigate"],
    HANDOVER:     ["speak"],
    DONE:         ["speak"], 
    CALL_PATIENT: ["speak", "navigate", "call_patient"],
    VERIFY:       ["speak", "verify_patient","call_patient"],
}


# ===================== THE STATE MACHINE =====================

class StateMachine:

    def __init__(self):
        self.mode = None       # "walk_in" or "pickup"
        self.phase = None      # current phase

    def start(self, mode):
        """Begin a new conversation in the given mode."""
        if mode not in START_PHASE:
            return f"ERROR: unknown mode '{mode}'"
        self.mode = mode
        self.phase = START_PHASE[mode]
        return f"started in mode '{mode}', phase {self.phase}"

    def change_phase(self, new_phase):
        """Move to a new phase, only if the move is allowed."""
        allowed = TRANSITIONS[self.phase]
        if new_phase not in allowed:
            return f"ERROR: cannot go from {self.phase} to {new_phase}. Allowed: {allowed}"
        old_phase = self.phase
        self.phase = new_phase
        return f"phase changed: {old_phase} → {new_phase}"

    def is_tool_allowed(self, tool_name):
        """Is this tool allowed in the current phase?"""
        return tool_name in PHASE_TOOLS[self.phase]

    def get_instruction(self):
        """The LLM's job for the current phase."""
        return PHASE_INSTRUCTIONS[self.phase]

    def get_allowed_phases(self):
        """Which phases can come next."""
        return TRANSITIONS[self.phase]


# ===================== TEST =====================

if __name__ == "__main__":
    sm = StateMachine()

    print("--- MODE 1: walk-in ---")
    print(sm.start("walk_in"))
    print("Instruction:", sm.get_instruction())
    print("navigate allowed?", sm.is_tool_allowed("navigate"))   # False
    print(sm.change_phase(HANDOVER))                             # should fail
    print(sm.change_phase(IDENTIFY))                             # ok
    print(sm.change_phase(GUIDE))                                # ok
    print("navigate allowed?", sm.is_tool_allowed("navigate"))   # True

    print()
    print("--- MODE 2: pickup ---")
    print(sm.start("pickup"))
    print("Instruction:", sm.get_instruction())
    print(sm.change_phase(VERIFY))                               # ok
    print(sm.change_phase(CALL_PATIENT))                         # wrong person → ok
    print(sm.change_phase(EXPLAIN))                              # should fail (must verify first)