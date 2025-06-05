from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class SourceStatus(str, Enum):
    ACTIVE = "active"
    IN_DEVELOPMENT = "in_development"
    DEPRECATED = "deprecated"


class Source(BaseModel):
    sourceId: str
    sourceName: str
    sourceUrl: str
    sourceStatus: SourceStatus
    sourceIcon: Optional[str] = None