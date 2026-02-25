# Health AI Chat Agent

A terminal-based medical intake chatbot that guides patients through appointment scheduling by collecting required information step-by-step. The agent uses an LLM for natural conversation and validates addresses via the Google Address Validation API.

## Features

- **Guided intake flow**: Collects patient info, insurance, medical reason, demographics, and appointment selection
- **Conversational AI**: Uses OpenAI's API to ask one question at a time and respond naturally
- **Address validation**: Validates and formats addresses using Google's Address Validation API
- **State persistence**: Saves session state to `data/latest_session.json`
- **Q&A step**: Allows patients to ask questions before completing intake

## Intake Steps

1. **Patient** — Full name, date of birth  
2. **Insurance** — Payer name (no member ID required)  
3. **Medical** — Chief complaint / reason for visit  
4. **Demographics** — Address (validated and confirmed)  
5. **Appointment** — Choose from available providers and time slots  
6. **Q&A** — Optional questions before finishing  

## Requirements

- Python 3.12+
- [Poetry](https://python-poetry.org/) for dependency management

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Health-AI-Chatbot
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Configure environment variables**

   Create a `.env` file in the project root:

   ```env
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o-mini   # optional, defaults to gpt-4o-mini
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key   # for address validation
   ```

   - **OPENAI_API_KEY** — Required for the chat agent
   - **GOOGLE_MAPS_API_KEY** — Required for address validation. Without it, address validation will fail with a clear message.

## Usage

Run the agent:

```bash
poetry run python main.py
```

The agent will prompt you through each step. Type `quit` or `exit` at any time to end the session.

## Project Structure

```
├── main.py                 # Entry point
├── agent/
│   ├── LLM.py              # OpenAI client and chat/extract logic
│   ├── state.py            # AgentState and data models
│   ├── organizational_flow.py  # Main intake flow and step logic
│   └── helper.py           # Utilities (normalize, yes/no, first_name)
├── helper/
│   ├── address_validation.py   # Google Address Validation API integration
│   └── storage.py          # Session state persistence
├── data/
│   ├── appointments.json   # Available providers and time slots
│   └── latest_session.json # Saved session (created at runtime)
└── pyproject.toml
```

## Customizing Appointments

Edit `data/appointments.json` to change available providers and time slots:

```json
{
  "providers": [
    {
      "name": "Dr. Jordan Patel",
      "available_time_slots": ["2026-01-27T09:30:00-05:00", "..."]
    }
  ]
}
```

## License

See repository for license information.
