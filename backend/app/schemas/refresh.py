from pydantic import BaseModel


class RefreshPilotResponse(BaseModel):
    pilot_id: int
    pilot_name: str
    rows_processed: int
    message: str


class RefreshAllError(BaseModel):
    pilot_id: int
    pilot_name: str
    error: str


class RefreshAllResponse(BaseModel):
    success_count: int
    failed_count: int
    errors: list[RefreshAllError]
