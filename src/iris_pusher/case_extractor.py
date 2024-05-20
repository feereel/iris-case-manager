from datetime import datetime

from iris_pusher.dfir_iris_client.session import ClientSession
from iris_pusher.dfir_iris_client.case import Case 
from iris_pusher.dfir_iris_client.users import User 
from iris_pusher.dfir_iris_client.helper.utils import (
    get_data_from_resp,
    assert_api_resp,
)
from iris_pusher.dfir_iris_client.helper.errors import IrisClientException

from .case_enitity import *
from .helper.utils import extract_object, pretty

from .datastore_extractor import DatastoreExtractor
from .datastore_entities import DatastoreFile, DatastoreFolder

import re, os
import logging as logger

log = logger.getLogger(__name__)

class CaseExtractor:
    def __init__(self, cid: int, session: ClientSession, collect_usernames: bool = False, ds_os_folder: str = '/tmp', ds_case_folder: str = '', donwload_another_case_files: str = False) -> None:
        self.session = session
        self.cid = cid
        self.case = Case(session=self.session)
        self.collect_usernames = collect_usernames
        self.ds_os_folder = ds_os_folder
        self.ds_case_folder = ds_case_folder
        self.donwload_another_case_files = donwload_another_case_files
        self.folder_for_another_case = f'Files_from_another_case_{self.cid}'
 
    def extract(self):
        case_data = CaseData(case_info=self.get_case_info(),
                        notes_directory=self.list_notes_groups(),
                        assets=self.list_assets(),
                        iocs=self.list_iocs(),
                        timelines=self.list_timelines(),
                        tasks=self.list_tasks(),
                        evidences=self.list_evidences(),
                        datastore=DatastoreExtractor(self.session, self.cid).extract(self.ds_os_folder, self.ds_case_folder))
        
        if self.donwload_another_case_files:
            self.include_another_case_files(case_data)
            
        return case_data
    
    def extract_another_case_files(self, text: str, store_os_folder: str, store_case_folder: str) -> list[DatastoreFile]:
        if not text:
            return []
        
        link = rf'/datastore/file/view/(\d+)\?cid=(\d+)'
        ds_files = []
        occurs = re.finditer(link, text)
        
        for occur in set(occurs):
            file_id = int(occur.group(1))
            case_id = int(occur.group(2))
            if case_id == self.cid:
                continue
            
            response = self.case.get_ds_file_info(file_id=file_id, cid=case_id)
            if response.is_error():
                log.error(f"Can't extract file with id {file_id} from case {case_id}")
                continue
            
            data = get_data_from_resp(response)
            
            os_path = os.path.join(store_os_folder, data['file_original_name'])
            case_path = os.path.join(store_case_folder, data['file_original_name'])
            
            ds_file = DatastoreFile(id = file_id,
                        case_id = case_id,
                        filename = data['file_original_name'],
                        path = case_path,
                        file_description = data['file_description'],
                        file_is_ioc = False,
                        file_is_evidence = False,
                        file_password = data['file_password'],
                        file_tags = data['file_tags'].split(',') if data['file_tags'] else None)
            ds_files.append(ds_file)
            
            with open(os_path, 'wb') as file:
                response = self.case.download_ds_file(file_id, case_id)
                file.write(response.content)
            
        return ds_files

    def include_another_case_files(self, case_data: CaseData):
        store_os_folder = os.path.join(self.ds_os_folder, case_data.datastore.folder_name, self.folder_for_another_case)
        store_case_folder = os.path.join(self.ds_os_folder, case_data.datastore.folder_name, self.folder_for_another_case)
        
        os.makedirs(store_os_folder, exist_ok=True)
        folder = DatastoreFolder(
            id=0,
            case_id=self.cid,
            folder_name=self.folder_for_another_case,
            children=list(),
            path=store_case_folder
        )
        case_data.datastore.children.append(folder)

        files = self.extract_another_case_files(case_data.case_info.case_description, store_os_folder, store_case_folder)
        folder.children.extend(files)
        
        for id, notes_group in case_data.notes_directory.items():
            for note in notes_group.notes:
                files = self.extract_another_case_files(note.note_content, store_os_folder, store_case_folder)
                for comment in note.comments:
                    files += self.extract_another_case_files(comment, store_os_folder, store_case_folder)
                
                folder.children.extend(files)
                
        for id, asset in case_data.assets.items():
            files = self.extract_another_case_files(asset.description, store_os_folder, store_case_folder)
            for comment in asset.comments:
                files += self.extract_another_case_files(comment, store_os_folder, store_case_folder)
            
            folder.children.extend(files)
        
        for id, ioc in case_data.iocs.items():
            files = self.extract_another_case_files(ioc.description, store_os_folder, store_case_folder)
            for comment in ioc.comments:
                files += self.extract_another_case_files(comment, store_os_folder, store_case_folder)
            
            folder.children.extend(files)
        
        for id, timeline in case_data.timelines.items():
            files = self.extract_another_case_files(timeline.content, store_os_folder, store_case_folder)
            for comment in timeline.comments:
                files += self.extract_another_case_files(comment, store_os_folder, store_case_folder)
            
            folder.children.extend(files)
        
        for id, task in case_data.tasks.items():
            files = self.extract_another_case_files(task.description, store_os_folder, store_case_folder)
            for comment in task.comments:
                files += self.extract_another_case_files(comment, store_os_folder, store_case_folder)
            
            folder.children.extend(files)
            
        for id, evidence in case_data.evidences.items():
            files = self.extract_another_case_files(evidence.description, store_os_folder, store_case_folder)
            for comment in evidence.comments:
                files += self.extract_another_case_files(comment, store_os_folder, store_case_folder)
            
            folder.children.extend(files)
   
    def get_case_info(self) -> CaseInfo:
        response = self.case.get_case(cid=self.cid)
        assert_api_resp(response, soft_fail=False)
        
        data = get_data_from_resp(response)
        ret = CaseInfo(
            case_name = re.sub(r'^#\d+? - ', '', data['case_name']),
            case_description = data['case_description'],
            case_classification = data['classification_id'],
            case_customer = data['customer_name'],
            soc_id = data['case_soc_id'],
            custom_attributes = data['custom_attributes'],
        )
        
        return ret

    def extract_asset_data(self, data: dict, comments: list[str]) -> Asset:     
        ret = Asset(
            name = data['asset_name'],
            asset_type = data['asset_type']['asset_id'],
            analysis_status = data['analysis_status_id'],
            compromise_status = data['asset_compromise_status_id'],
            tags = data['asset_tags'].split(',') if data['asset_tags'] else None,
            description = data['asset_description'],
            domain = data['asset_domain'],
            ip = data['asset_ip'],
            additional_info = data['asset_info'],
            ioc_links = extract_object(data['linked_ioc'], 'ioc_id'),
            custom_attributes = data['custom_attributes'],
            comments=comments
        )
        return ret
    
    def get_asset(self, id: int) -> Asset:
        response = self.case.get_asset(id, self.cid)
        assert_api_resp(response, soft_fail=False)
        
        data = get_data_from_resp(response)
        
        c_response = self.case.list_asset_comments(id, self.cid)
        assert_api_resp(c_response, soft_fail=False)
        
        comments = extract_object(get_data_from_resp(c_response), 'comment_text')
        
        return self.extract_asset_data(data, comments)
    
    def list_assets(self) -> dict[int, Asset]:
        response = self.case.list_assets(self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)['assets']
        
        ids = extract_object(data, 'asset_id')
        return_data = {}
        for id in ids:
            return_data[id] = self.get_asset(id)
        
        return return_data
    
    def extract_ioc_data(self, data: dict, comments: list[str]) -> IoC:
        ret = IoC(
            value = data['ioc_value'],
            ioc_type = data['ioc_type_id'],
            ioc_tlp = data['ioc_tlp_id'],
            description = data['ioc_description'],
            ioc_tags = data['ioc_tags'].split(',') if data['ioc_tags'] else None,
            custom_attributes = data['custom_attributes'],
            comments=comments
        )
        return ret
    
    def get_ioc(self, id: int) -> IoC:
        response = self.case.get_ioc(id, self.cid)
        assert_api_resp(response, soft_fail=False)
        
        c_response = self.case.list_ioc_comments(id, self.cid)
        assert_api_resp(c_response, soft_fail=False)
        
        comments = extract_object(get_data_from_resp(c_response), 'comment_text')
        
        data = get_data_from_resp(response)
        return self.extract_ioc_data(data, comments)
    
    def list_iocs(self) -> dict[int, IoC]:
        response = self.case.list_iocs(cid=self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)['ioc']
        
        ids = extract_object(data, 'ioc_id')
        
        return_data = {}
        for id in ids:
            return_data[id] = self.get_ioc(id)
        
        return return_data
    
    def extract_timeline_data(self, data: dict, comments: list[str]) -> Timeline:
        ret = Timeline(
            title = data['event_title'],
            date_time = datetime.strptime(data['event_date'], r'%Y-%m-%dT%H:%M:%S.%f'),
            content = data['event_content'],
            raw_content = data['event_raw'],
            source = data['event_source'],
            linked_assets = data['event_assets'],
            linked_iocs = data['event_iocs'],
            category = data['event_category_id'],
            tags = data['event_tags'].split(',') if data['event_tags'] else None,
            color = data['event_color'],
            display_in_graph = data['event_in_graph'],
            display_in_summary = data['event_in_summary'],
            custom_attributes = data['custom_attributes'],
            timezone_string = data['event_tz'],
            sync_ioc_with_assets = data['event_is_flagged'],
            comments=comments
        )
        return ret
    
    def get_timeline(self, id: int) -> Timeline:
        response = self.case.get_event(id, self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)
        
        c_response = self.case.list_event_comments(id, self.cid)
        assert_api_resp(c_response, soft_fail=False)
        
        comments = extract_object(get_data_from_resp(c_response), 'comment_text')
        
        return self.extract_timeline_data(data, comments)
    
    def list_timelines(self) -> dict[int, Timeline]:
        response = self.case.list_events(cid=self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)['timeline']
        
        
        return_data = {}
        for tl in data:
            id = tl['event_id']
            try:
                return_data[id] = self.get_timeline(id)
            except IrisClientException:
                title = tl['event_title'] if 'event_title' in tl else ''
                log.error(f"Can't extract event_{id} ({title})")
        
        return return_data
    
    def extract_task_data(self, data: dict, comments: list[str]) -> Task:
        ret = Task(
            title = data['task_title'],
            status = data['task_status_id'],
            assignees = extract_object(data['task_assignees'], 'user') if self.collect_usernames else [],
            description = data['task_description'],
            tags = data['task_tags'].split(',') if data['task_tags'] else None,
            custom_attributes = data['custom_attributes'],
            comments=comments
        )
        return ret
    
    def get_task(self, id: int) -> Task:
        response = self.case.get_task(id, self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)
        
        c_response = self.case.list_task_comments(id, self.cid)
        assert_api_resp(c_response, soft_fail=False)
        comments = extract_object(get_data_from_resp(c_response), 'comment_text')
        
        data = self.extract_task_data(data, comments)
    
        for name in data.assignees:
            user = User(session=self.session)
            assert_api_resp(user.lookup_username(name), soft_fail=False)
        
        return data
    
    def list_tasks(self) -> dict[int, Task]:
        response = self.case.list_tasks(cid=self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)['tasks']
        
        ids = extract_object(data, 'task_id')
        
        return_data = {}
        for id in ids:
            return_data[id] = self.get_task(id)
        
        return return_data
  
    def extract_evidence_data(self, data: dict, comments: list[str]) -> Evidence:
        ret = Evidence(
            filename = data['filename'],
            file_size = data['file_size'],
            description = data['file_description'],
            file_hash = data['file_hash'],
            custom_attributes = data['custom_attributes'],
            comments=comments
        )
        return ret
    
    def get_evidence(self, id: int) -> Evidence:
        response = self.case.get_evidence(id, self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)
        
        c_response = self.case.list_evidence_comments(id, self.cid)
        assert_api_resp(c_response, soft_fail=False)
        comments = extract_object(get_data_from_resp(c_response), 'comment_text')
        
        return self.extract_evidence_data(data, comments)
    
    def list_evidences(self) -> dict[int, Evidence]:
        response = self.case.list_evidences(cid=self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)['evidences']
        
        ids = extract_object(data, 'id')
        
        return_data = {}
        for id in ids:
            return_data[id] = self.get_evidence(id)
        
        return return_data

    def extract_note_data(self, data: dict, comments: list[str]) -> Note:
        ret = Note(
            note_title = data['note_title'],
            note_content = data['note_content'],
            custom_attributes = data['custom_attributes'],
            comments=comments
        )
        return ret
    
    def get_note(self, id: int) -> Note:
        response = self.case.get_note(id, self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)
        
        c_response = self.case.list_note_comments(id, self.cid)
        assert_api_resp(c_response, soft_fail=False)
        
        comments = extract_object(get_data_from_resp(c_response), 'note')
        
        return self.extract_note_data(data, comments)

    def extract_notes_group_data(self, data: dict) -> NotesDirectory:
        ret = NotesDirectory(dir_title = data['group_title'])
        ret.notes = []
        
        ids = extract_object(data['notes'], 'note_id')
        for id in ids:
            ret.notes.append(self.get_note(id))
        
        return ret
    
    def get_notes_group(self, id: int) -> NotesDirectory:
        response = self.case.get_notes_group(id, self.cid)
        assert_api_resp(response, soft_fail=False)
        
        data = self.extract_notes_group_data(get_data_from_resp(response))
    
        return data
    
    def list_notes_groups(self) -> dict[int, NotesDirectory]:
        response = self.case.list_notes_groups(cid=self.cid)
        assert_api_resp(response, soft_fail=False)
        data = get_data_from_resp(response)['groups']
        
        ids = extract_object(data, 'group_id')
        
        return_data = {}
        for id in ids:
            return_data[id] = self.get_notes_group(id)
        
        return return_data
