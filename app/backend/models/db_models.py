from sqlalchemy import Column, Integer, String, DateTime, func
from app.backend.db.database import Base


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(String, nullable=False)
    jd_text = Column(String, nullable=False)
    parsed_data = Column(String, nullable=False)  # JSON string
    analysis_result = Column(String, nullable=False)  # JSON string
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
