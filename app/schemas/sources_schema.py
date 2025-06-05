from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class SourceStatus(str, Enum):
    READY_TO_USE = "ready to use"
    IN_DEVELOPMENT = "in development"
    DEPRECATED = "deprecated"


class Source(BaseModel):
    sourceId: str
    sourceName: str
    sourceUrl: str
    sourceStatus: SourceStatus
    sourceIcon: Optional[str] = None