"""Models for the Retrieval Layer (component 4).

The retrieval service is treated as a black box / authoritative source
(Principle 2). ``usecase`` selects which analysis_template_svc usecase
(brand guidance vs category) the question is routed to -- this is decided
by the Planner, not the Planner Consultant.
"""

from typing import Literal

from pydantic import BaseModel

Usecase = Literal["brand_guidance", "category"]


class RetrievalQuery(BaseModel):
    question: str
    usecase: Usecase = "brand_guidance"


class RetrievalResult(BaseModel):
    question: str
    answer: str
