from pydantic import BaseModel, Field


# Schema for choosing a plan (incoming request data)
class PlanSelectSchema(BaseModel):
    plan_id: int = Field(gt = 0)
