import sys, asyncio, json, tempfile, argparse, hashlib
import pipecat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "voice/server"))
import httpx
from dotenv import dotenv_values
from loguru import logger

logger.remove()
from luna_tutor.api import runtime
from luna_tutor.llm.openrouter import OpenRouterClient, _redact_contact


class CapturingClient(OpenRouterClient):
    """Synthetic-run diagnostics only: no headers, keys or HTTP bodies recorded."""

    parsed_outputs = []

    async def structured_chat(self, *args, **kwargs):
        result = await super().structured_chat(*args, **kwargs)
        self.parsed_outputs.append(_redact_contact(result))
        return result


runtime.OpenRouterClient = CapturingClient
build_runtime_app = runtime.build_runtime_app
from text_pipeline import PipecatTurnService

ANSWERS = {
    "warm-up.hello": "Hello Luna.",
    "warm-up.feelings": "I'm fine, thank you.",
    "warm-up.start": "Let's start.",
    "lesson-01.place-meaning": "A city has tall buildings. The countryside has many trees.",
    "lesson-01.class": "I'm in Class 5B.",
    "lesson-01.home": "I live countryside.",
    "lesson-01.ask-luna": "Where do you live?",
    "lesson-02.favourite-animal": "It's a dolphin.",
    "lesson-02.favourite-colour": "It's pink.",
    "lesson-02.favourite-food": "It's a sandwich.",
    "lesson-02.favourite-sport": "It's table tennis.",
    "lesson-02.ask-luna": "What's your favourite animal?",
    "lesson-03.introductions": "I'm in Class 5B and I live in the countryside.",
    "lesson-03.favourites": "My favourite animal is a dolphin. I like pink and sandwiches and table tennis.",
    "lesson-03.ask-luna": "What's your favourite food?",
    "level-02.birthday": "It's in May.",
    "level-02.hobby": "My hobby is playing table tennis.",
    "level-02.subject": "My favourite subject is English.",
    "level-02.ask-luna": "What's your hobby?",
    "level-03.home-description": "I live in the countryside. It's calm and the air is fresh.",
    "level-03.contrast": "My village is calm; however, there aren't many shops.",
    "level-03.addition": "My town has good schools; moreover, there is an amusement park.",
    "level-03.use-cottage": "There is a small cottage near my house.",
    "level-03.use-vehicles": "There are many vehicles on the road.",
    "level-03.use-traffic-jam": "There is a traffic jam near my school in the morning.",
    "level-03.use-pavement": "I walk on the pavement to stay safe.",
    "level-03.use-drawback": "One drawback is that there aren't many shops.",
    "level-03.use-amusement-park": "I go to an amusement park with my family.",
    "level-03.ask-luna": "What is your town like?",
    "free-talk.conversation": "Hello Emma! I'm Quang. I live in the countryside and I like table tennis. What do you like?",
}


async def main(args):
    out = args.output
    if out.exists():
        raise RuntimeError("Will not overwrite")
    sources = (
        list((ROOT / "backend/src/luna_tutor").rglob("*.py"))
        + list((ROOT / "backend/src/luna_tutor/prompts").glob("*.yaml"))
        + list((ROOT / "voice/server").glob("*.py"))
        + list((ROOT / "curriculum/grade-05/unit-01").rglob("*.yaml"))
    )
    payload = {
        "pipecat_version": pipecat.__version__,
        "hashes": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sources
        },
        "scope": "scripted student full Unit1 API Pipecat journey; semantic review pending",
        "complete": False,
        "records": [],
    }
    values = dotenv_values(args.env_file)
    with tempfile.TemporaryDirectory() as folder:
        app = build_runtime_app(
            {
                "OPENROUTER_API_KEY": values["OPENROUTER_API_KEY"],
                "TUTOR_DATABASE_PATH": str(Path(folder) / "session.sqlite3"),
            },
            turn_service_adapter=PipecatTurnService,
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as api:
                current = (await api.post("/api/sessions")).json()
                visits = {}
                for i in range(100):
                    aid = current["activity_id"]
                    visits[aid] = visits.get(aid, 0) + 1
                    if visits[aid] > 3:
                        payload["stopped"] = "activity_stalled:" + aid
                        break
                    if ".introduce-" in aid:
                        text = aid.split(".introduce-")[1].replace("-", " ")
                    else:
                        text = ANSWERS[aid]
                    CapturingClient.parsed_outputs.clear()
                    try:
                        response = await api.post(
                            f"/api/sessions/{current['session_id']}/turns",
                            json={
                                "turn_id": f"journey-{i}",
                                "expected_state_version": current["state_version"],
                                "learner_text": text,
                            },
                        )
                    except Exception as error:
                        payload["stopped"] = "execution_error"
                        payload["error"] = {
                            "type": type(error).__name__,
                            "activity_id": aid,
                        }
                        break
                    record = {
                        "activity_before": aid,
                        "teacher_before": current["messages"][-1]["text"],
                        "input": text,
                        "status": response.status_code,
                        "parsed_model_response_count": len(CapturingClient.parsed_outputs),
                    }
                    if response.status_code != 200:
                        record["error"] = response.json()
                        record["parsed_model_outputs"] = list(
                            CapturingClient.parsed_outputs
                        )
                        payload["records"].append(record)
                        payload["stopped"] = "request_error"
                        break
                    current = response.json()["session"]
                    record["result"] = {
                        k: v for k, v in current.items() if k != "messages"
                    }
                    record["teacher"] = current["messages"][-1]
                    payload["records"].append(record)
                    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
                    print(i, aid, "->", current["activity_id"], flush=True)
                    if aid == "free-talk.conversation":
                        payload["reached_free_talk"] = True
                        finished = await api.post(
                            f"/api/sessions/{current['session_id']}/finish",
                            json={"expected_state_version": current["state_version"]},
                        )
                        payload["finish"] = {
                            "status": finished.status_code,
                            "result": finished.json(),
                        }
                        break
                payload["complete"] = True
                out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Diagnostic full Unit 1 scripted-student text journey. No automatic semantic acceptance."
    )
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
