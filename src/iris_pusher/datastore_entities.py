from abc import ABC
from dataclasses import dataclass
from pydantic import BaseModel
from typing import Union

class DatastoreEntity(BaseModel):
    id: int
    case_id: int
    path: Union[str | None]
    
class DatastoreFile(DatastoreEntity):
    filename: str
    file_description: str
    file_is_ioc: bool = False
    file_is_evidence: bool = False,
    file_password: Union[str, None] = None,
    file_tags: Union[list[str], None] = None,
    
class DatastoreFolder(DatastoreEntity):
    folder_name: str
    children: list[Union[DatastoreFile, 'DatastoreFolder']]