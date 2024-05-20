from dataclasses import dataclass
from pydantic import BaseModel
from datetime import datetime
from typing import Union

from .datastore_entities import DatastoreFolder

class CaseInfo(BaseModel):
    case_name: str
    case_description: str
    case_customer: Union[str, int]
    case_classification: Union[str, int, None]
    soc_id: str
    custom_attributes: Union[dict, None] = None
    create_customer: bool = False

class Note(BaseModel):
    note_title: str
    note_content: str
    custom_attributes: Union[dict, None] = None
    comments: Union[list[str], None] = None

class NotesDirectory(BaseModel):
    dir_title: str
    notes: Union[list[Note], None] = None
    directories: Union[list, None] = None
    
class Asset(BaseModel):
    name: str
    asset_type: Union[str, int]
    analysis_status: Union[str, int]
    compromise_status: Union[str, int, None] = None
    tags: Union[list[str], int, None] = None
    description: Union[str, None] = None
    domain: Union[str, None] = None
    ip: Union[str, None] = None
    additional_info: Union[str, None] = None
    ioc_links: Union[list[int], None] = None
    custom_attributes: Union[dict, None]  = None
    comments: Union[list[str], None]  = None

class IoC(BaseModel):
    value: str
    ioc_type: Union[str, int]
    description: Union[str, None] = None
    ioc_tlp: Union[str, int, None] = None
    ioc_tags: Union[list[str], None] = None
    custom_attributes: Union[dict, None]  = None
    comments: Union[list[str], None] = None

class Timeline(BaseModel):
    title: str
    date_time: datetime
    content: Union[str, None] = None
    raw_content: Union[str, None] = None
    source: Union[str, None] = None
    linked_assets: Union[list, None] = None
    linked_iocs: Union[list[int], None] = None
    category: Union[str, int, None] = None
    tags: Union[list[str], None] = None
    color: Union[str, None] = None
    display_in_graph: Union[bool, None] = None
    display_in_summary: Union[bool, None] = None
    custom_attributes: Union[dict, None] = None
    timezone_string: Union[str, None] = None
    sync_ioc_with_assets: Union[bool, None] = False
    parent_event_id: Union[int, None] = None
    comments: Union[list[str], None] = None

class Task(BaseModel):
    title: str
    status: Union[str, int]
    assignees: list[Union[str,int]]
    description: Union[str, None] = None
    tags: Union[list[str], None] = None
    custom_attributes: Union[dict, None] = None
    comments: Union[list[str],None] = None

class Evidence(BaseModel):
    filename: str
    file_size: int
    description: Union[str, None] = None
    file_hash: Union[str, None] = None
    custom_attributes: Union[dict, None] = None
    comments: Union[list[str], None] = None

class CaseData(BaseModel):
    case_info: CaseInfo
    notes_directory: dict[int, NotesDirectory]
    assets: dict[int, Asset]
    iocs: dict[int, IoC]
    timelines: dict[int, Timeline]
    tasks: dict[int, Task]
    evidences: dict[int, Evidence]
    datastore: DatastoreFolder
    