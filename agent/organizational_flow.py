from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from agent.LLM import LLMClient
from agent.state import AgentState
from agent.helper import normalize_whitespace, yes_no, first_name
from helper.address_validation import validate_address_line
from helper.storage import save_latest_state

DATA_PATH = Path("data/appointments.json")

STEP_ORDER = ["patient", "insurance", "medical", "demographics", "appointment", "qa"]
REQUIRED = {
    "patient": ["patient.full_name", "patient.date_of_birth"],
    "insurance": ["insurance.payer_name"],
    "medical": ["medical.chief_complaint"],
    "demographics": ["demographics.raw_address_line"],
}


def load_appointments() -> Dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def get(state: AgentState, dotted: str) -> Any:
    root, field = dotted.split(".", 1)
    return getattr(getattr(state, root), field)


def set(state: AgentState, dotted: str, val: Any) -> None:
    root, field = dotted.split(".", 1)
    setattr(getattr(state, root), field, val)


def missing_fields(state: AgentState) -> List[str]:
    return [p for p in REQUIRED.get(state.current_step, []) if not get(state, p)]


def advance(state: AgentState) -> None:
    if state.current_step in REQUIRED and missing_fields(state):
        return
    if state.current_step == "demographics" and (state.demographics.awaiting_confirmation or not state.demographics.is_valid):
        return
    i = STEP_ORDER.index(state.current_step)
    state.current_step = STEP_ORDER[min(i + 1, len(STEP_ORDER) - 1)]


def apply_updates(state: AgentState, updates: Dict[str, Any]) -> None:
    mapping = {
        ("patient", "full_name"): "patient.full_name",
        ("patient", "date_of_birth"): "patient.date_of_birth",
        ("insurance", "payer_name"): "insurance.payer_name",
        ("medical", "chief_complaint"): "medical.chief_complaint",
        ("demographics", "raw_address_line"): "demographics.raw_address_line",
    }
    for (section, key), path in mapping.items():
        sec = updates.get(section)
        if isinstance(sec, dict) and sec.get(key):
            set(state, path, normalize_whitespace(str(sec[key])))


def validate_address_gate(state: AgentState) -> Optional[str]:
    demo = state.demographics
    if not demo.raw_address_line:
        return None

    res = validate_address_line(demo.raw_address_line)
    demo.formatted = res.get("formatted")
    demo.place_id = res.get("place_id")
    demo.missing_fields = res.get("missing_fields") or []

    if res.get("needs_confirmation") and demo.formatted:
        demo.awaiting_confirmation = True
        demo.pending_formatted = demo.formatted
        demo.pending_place_id = demo.place_id
        demo.is_valid = False
        return f"I found this address:\n  {demo.pending_formatted}\nIs this correct? (yes/no)"

    if not res.get("is_valid"):
        demo.raw_address_line = None
        demo.awaiting_confirmation = False
        demo.pending_formatted = None
        demo.pending_place_id = None
        demo.is_valid = False
        return f"{res.get('message')}\nPlease re-enter your address (street, city, state, ZIP)."

    demo.awaiting_confirmation = False
    demo.pending_formatted = None
    demo.pending_place_id = None
    demo.is_valid = True
    return None


def handle_address_confirmation(state: AgentState, user_input: str) -> str:
    demo = state.demographics
    if yes_no(user_input) is True:
        demo.formatted = demo.pending_formatted
        demo.place_id = demo.pending_place_id
        demo.pending_formatted = None
        demo.pending_place_id = None
        demo.awaiting_confirmation = False
        demo.is_valid = True
        return "Thanks — confirmed."

    demo.raw_address_line = None
    demo.formatted = None
    demo.place_id = None
    demo.pending_formatted = None
    demo.pending_place_id = None
    demo.awaiting_confirmation = False
    demo.is_valid = False
    return "Okay — please re-enter your address (street, city, state, ZIP)."


def choose_appointment(state: AgentState) -> None:
    providers = load_appointments().get("providers", [])
    flat = [(p["name"], slot) for p in providers for slot in p.get("available_time_slots", [])]

    print("\nAvailable appointments:")
    for i, (name, slot) in enumerate(flat, 1):
        print(f"  {i}. {slot} — {name}")

    while True:
        c = input("\nYou: ").strip()
        if c.isdigit() and 1 <= int(c) <= len(flat):
            name, dt = flat[int(c) - 1]
            state.appointment.provider = name
            state.appointment.datetime = dt
            return
        print("Agent: Please type a valid number.")


def print_confirmation(state: AgentState) -> None:
    address = state.demographics.formatted or state.demographics.raw_address_line or "(missing)"
    print("\n--- Confirmation ---")
    print(f"Name: {state.patient.full_name or '(missing)'}")
    print(f"DOB: {state.patient.date_of_birth or '(missing)'}")
    print(f"Address: {address}")
    print(f"Reason for visit: {state.medical.chief_complaint or '(missing)'}")
    print(f"Appointment: {state.appointment.datetime or '(missing)'}")
    print(f"Provider: {state.appointment.provider or '(missing)'}")
    print("--------------------\n")


def prompt_next(llm: LLMClient, state: AgentState) -> None:
    msg, _ = llm.chat_and_extract(
        step_name=state.current_step,
        missing_fields=missing_fields(state),
        user_message="Continue. Ask the next required question.",
        state_public=state.to_public_dict(),
    )
    print(f"\nAgent: {msg}")


def run_agent() -> None:
    state = AgentState()
    llm = LLMClient()
    save_latest_state(state.to_public_dict())

    prompt_next(llm, state)

    while True:
        if state.demographics.awaiting_confirmation:
            u = input("\nYou: ").strip()
            if u.lower() in {"quit", "exit"}:
                return
            print(f"\nAgent: {handle_address_confirmation(state, u)}")
            save_latest_state(state.to_public_dict())
            advance(state)
            if state.current_step == "appointment":
                print("\nAgent: Please choose an appointment number from the list.")
            else:
                prompt_next(llm, state)
            continue

        if state.current_step == "appointment":
            choose_appointment(state)
            save_latest_state(state.to_public_dict())
            state.current_step = "qa"
            prompt_next(llm, state)  
            continue

        if state.current_step == "qa":
            u = input("\nYou: ").strip()
            if u.lower() in {"quit", "exit"}:
                return

            yn = yes_no(u)
            if yn is False:
                name = first_name(state.patient.full_name)
                print(f"\nAgent: Thank you, {name}! Have a great day!")
                print_confirmation(state)
                return

            if yn is True:
                q = input("\nYou: ").strip()
                if not q:
                    continue
                print(f"\nAgent: {llm.answer_user_question(q, state.to_public_dict())}")
                prompt_next(llm, state)
                continue

            print("\nAgent: Please answer yes or no.")
            continue

        # intake steps
        u = input("\nYou: ").strip()
        if not u:
            continue
        if u.lower() in {"quit", "exit"}:
            return

        before = state.current_step

        assistant, updates = llm.chat_and_extract(
            step_name=state.current_step,
            missing_fields=missing_fields(state),
            user_message=u,
            state_public=state.to_public_dict(),
        )
        apply_updates(state, updates)

        if state.current_step == "demographics" and state.demographics.raw_address_line:
            gate = validate_address_gate(state)
            save_latest_state(state.to_public_dict())
            if gate:
                print(f"\nAgent: {gate}")
                continue

        advance(state)
        save_latest_state(state.to_public_dict())

        if state.current_step != before:
            if state.current_step == "appointment":
                print("\nAgent: Please choose an appointment number from the list.")
            else:
                prompt_next(llm, state)
            continue

        if missing_fields(state):
            prompt_next(llm, state)
            continue

        print(f"\nAgent: {assistant}")
