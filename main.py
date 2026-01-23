from dotenv import load_dotenv
from agent.organizational_flow import run_agent

if __name__ == "__main__":
    load_dotenv()
    run_agent()