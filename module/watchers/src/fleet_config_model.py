from typing import Annotated
from pydantic import BaseModel, StringConstraints

# https://www.ietf.org/rfc/rfc1035.txt
ProjectIdString = Annotated[str, StringConstraints(min_length=6, max_length=30, pattern="^[a-z]([-a-z0-9]*[a-z0-9])?")]

class FleetConfigModel(BaseModel):
    fleet_project_id: ProjectIdString
    cluster_version: str
