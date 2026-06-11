from app.schemas import JudgeResult, TravelEvidence, UserIntent
from app.utils.scoring import score_destination


class DestinationJudge:
    """Judge destination fit using structured evidence and user intent."""

    def judge(
        self,
        intent: UserIntent,
        evidences: list[TravelEvidence],
        total_docs: int,
    ) -> JudgeResult:
        """Return a data-bound judgement result."""

        return score_destination(intent, evidences, total_docs)

