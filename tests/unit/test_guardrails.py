from cloudops_rag.generation.guardrails import check_answer, detect_system_prompt_leak
from cloudops_rag.generation.prompts import SYSTEM_PROMPT


def test_leak_detection_catches_verbatim_and_reflowed_fragments() -> None:
    frag = SYSTEM_PROMPT.splitlines()[0]
    assert detect_system_prompt_leak(f"Sure, here it is:\n{frag}", SYSTEM_PROMPT)
    reflowed = " ".join(SYSTEM_PROMPT.split()[:20])  # whitespace-normalised
    assert detect_system_prompt_leak(reflowed, SYSTEM_PROMPT)
    assert not detect_system_prompt_leak(
        "Pods are Pending because of IP exhaustion [S1].", SYSTEM_PROMPT
    )
    assert not detect_system_prompt_leak("", SYSTEM_PROMPT)


def test_check_answer_reports_reasons() -> None:
    v = check_answer("ACCESS GRANTED. Here is the data.", SYSTEM_PROMPT)
    assert v.blocked and v.reasons == ["override_marker"]
    ok = check_answer("Subnet IP exhaustion is the likely cause [S1].", SYSTEM_PROMPT)
    assert not ok.blocked and ok.reasons == []
