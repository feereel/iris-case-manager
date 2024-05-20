from iris_pusher.dfir_iris_client.session import ClientSession
from iris_pusher.dfir_iris_client.case import Case 
from iris_pusher.dfir_iris_client.helper.utils import (
    get_data_from_resp,
    assert_api_resp,
)

from copy import deepcopy

from .case_enitity import CaseData
from .datastore_creator import DatastoreCreator
from .datastore_extractor import DatastoreExtractor
from .datastore_entities import *

import re
import logging as logger

log = logger.getLogger(__name__)


class CaseCreator():
    
    def __init__(self, session: str, case_data: CaseData, publisher_name: str = None, ds_folder: str = '') -> None:
        self.session: ClientSession = session
        self.case: Case = Case(session=self.session)
        self.cid: int = None
        self.data: CaseData = deepcopy(case_data)
        self.ds_folder: str = ds_folder
        self.ds_creator: DatastoreCreator = None
        
        self.publisher_name: str = publisher_name
        
        self.groups: dict[int, int] = {} # old_id -> new_id
        self.iocs: dict[int, int] = {} # old_id -> new_id
        self.assets: dict[int, int] = {} # old_id -> new_id
        self.timelines: dict[int, int] = {} # old_id -> new_id
        self.tasks: dict[int, int] = {} # old_id -> new_id
        self.evidences: dict[int, int] = {} # old_id -> new_id
  
    def _replace_links(self, text: str | dict[int, str]):
        if not text:
            return text
        
        old_link = rf'/datastore/file/view/(\d+)\?cid=(\d+)'
        new_text = text
        for occur in set(re.finditer(old_link, text)):
            file_id = int(occur.group(1))
            case_id = int(occur.group(2))
            if (case_id, file_id) not in self.ds_creator.files:
                log.error(f"File with id {file_id} is not found in datastore with case id {case_id}")
                continue
            
            new_link = rf'/datastore/file/view/{self.ds_creator.files[(case_id, file_id)]}?cid={self.cid}'
            new_text = new_text.replace(occur.group(0), new_link)
        return new_text

    # push case to server 
    def push(self):
        self.create_case()        
        self.ds_creator = DatastoreCreator(self.session, self.cid, self.ds_folder)
        self._ds_root_id = self.ds_creator.create_new_tree(self.data.datastore)
        
        new_description =  self._replace_links(self.data.case_info.case_description)
        self.case.update_case(case_id=self.cid, case_description=new_description)
        
        self.create_notes()
        self.create_iocs()
        self.create_assets()
        self.create_timelines()
        self.create_tasks()
        self.create_evidences()

    # Bad implementation need to fix            
    def create_case(self) -> int:
        if self.publisher_name:
            self.data.case_info.case_customer = self.publisher_name
        if not self.data.case_info.case_classification:
            self.data.case_info.case_classification = 1
            
        response = self.case.add_case(
            case_name = self.data.case_info.case_name,
            case_description = self.data.case_info.case_description,
            case_customer = self.data.case_info.case_customer,
            case_classification = self.data.case_info.case_classification,
            soc_id = self.data.case_info.soc_id,
            custom_attributes = self.data.case_info.custom_attributes,
            create_customer = self.data.case_info.create_customer)
            
        assert_api_resp(response, soft_fail=False)
        
        data = get_data_from_resp(response)
        self.cid = data['case_id']
        
    def create_notes(self):
        for id, group_notes in self.data.notes_directory.items():
            response = self.case.add_notes_group(group_notes.dir_title, self.cid)
            assert_api_resp(response, soft_fail=False)
            
            group_id = get_data_from_resp(response)['group_id']
            self.groups[id] = group_id
            
            for note in group_notes.notes:
                note.note_content = self._replace_links(note.note_content)
                
                response = self.case.add_note(
                    note_title=note.note_title,
                    note_content=note.note_content,
                    custom_attributes=note.custom_attributes,
                    group_id=group_id,
                    cid=self.cid
                )
                
                assert_api_resp(response)
                
                data = get_data_from_resp(response)
                note_id = data['note_id']
                
                for comment in note.comments:
                    response = self.case.add_note_comment(note_id, self._replace_links(comment), self.cid)
                    assert_api_resp(response, soft_fail=False)
                
    def create_iocs(self):
        for id, ioc in self.data.iocs.items():
            ioc.description =  self._replace_links(ioc.description)
            
            response = self.case.add_ioc(
                value = ioc.value,
                ioc_type = ioc.ioc_type,
                description = ioc.description,
                ioc_tlp = ioc.ioc_tlp,
                ioc_tags = ioc.ioc_tags,
                custom_attributes = ioc.custom_attributes,
                cid=self.cid
            )
            assert_api_resp(response, soft_fail=False)
            
            data = get_data_from_resp(response)
            ioc_id = data['ioc_id']
            self.iocs[id] = ioc_id
            
            for comment in ioc.comments:
                response = self.case.add_ioc_comment(ioc_id, self._replace_links(comment), self.cid)
                assert_api_resp(response, soft_fail=False)
        
    def create_assets(self):
        for id, asset in self.data.assets.items():
            asset.ioc_links = [t for f, t in self.iocs.items() if f in asset.ioc_links]
            
            asset.description = self._replace_links(asset.description)
            
            response = self.case.add_asset(
                name = asset.name,
                asset_type = asset.asset_type,
                analysis_status = asset.analysis_status,
                compromise_status = asset.compromise_status,
                tags = asset.tags,
                description = asset.description,
                domain = asset.domain,
                ip = asset.ip,
                additional_info = asset.additional_info,
                ioc_links = asset.ioc_links,
                custom_attributes = asset.custom_attributes,
                cid=self.cid
            )
            
            assert_api_resp(response, soft_fail=False)
            
            data = get_data_from_resp(response)
            asset_id = data['asset_id']
            self.assets[id] = asset_id
            
            for comment in asset.comments:
                response = self.case.add_asset_comment(asset_id, self._replace_links(comment), self.cid)
                assert_api_resp(response, soft_fail=False)
            
    def create_timelines(self):
        for id, timeline in self.data.timelines.items():
            timeline.linked_iocs  = [t for f, t in self.iocs.items() if f in timeline.linked_iocs]            
            timeline.linked_assets = [t for f, t in self.assets.items() if f in timeline.linked_assets]    
            
            timeline.content = self._replace_links(timeline.content)        
            
            response = self.case.add_event(
                title = timeline.title,
                date_time = timeline.date_time,
                content = timeline.content,
                raw_content = timeline.raw_content,
                source = timeline.source,
                linked_assets = timeline.linked_assets,
                linked_iocs = timeline.linked_iocs,
                category = timeline.category,
                tags = timeline.tags,
                color = timeline.color,
                display_in_graph = timeline.display_in_graph,
                display_in_summary = timeline.display_in_summary,
                custom_attributes = timeline.custom_attributes,
                timezone_string = timeline.timezone_string,
                sync_ioc_with_assets = timeline.sync_ioc_with_assets,
                cid=self.cid
            )
            
            assert_api_resp(response, soft_fail=False)
            
            data = get_data_from_resp(response)
            timeline_id = data['event_id']
            self.timelines[id] = timeline_id
            
            for comment in timeline.comments:
                response = self.case.add_event_comment(timeline_id, self._replace_links(comment), self.cid)
                assert_api_resp(response, soft_fail=False)
    
    def create_tasks(self):
        for id, task in self.data.tasks.items():
            
            task.description = self._replace_links(task.description)
            
            response = self.case.add_task(
                title = task.title,
                status = task.status,
                assignees = task.assignees,
                description = task.description,
                tags = task.tags,
                custom_attributes = task.custom_attributes,
                cid = self.cid,
            )
            
            
            assert_api_resp(response, soft_fail=False)
            
            data = get_data_from_resp(response)
            task_id = data['id']
            self.tasks[id] = task_id
            
            for comment in task.comments:
                response = self.case.add_task_comment(task_id, self._replace_links(comment), self.cid)
                assert_api_resp(response, soft_fail=False)
            
    def create_evidences(self):
        for id, evidence in self.data.evidences.items():
            
            evidence.description = self._replace_links(evidence.description)
            
            response = self.case.add_evidence(
                filename = evidence.filename,
                file_size = evidence.file_size,
                description = evidence.description,
                file_hash = evidence.file_hash,
                custom_attributes = evidence.custom_attributes,
                cid = self.cid,
            )
            
            assert_api_resp(response, soft_fail=False)
            
            data = get_data_from_resp(response)
            evidence_id = data['id']
            self.evidences[id] = evidence_id
            
            for comment in evidence.comments:
                response = self.case.add_evidence_comment(evidence_id, self._replace_links(comment), self.cid)
                assert_api_resp(response, soft_fail=False)