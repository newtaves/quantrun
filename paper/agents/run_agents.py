import asyncio
import logging

from paper.agents.runner import run_all_agents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_all_agents())
