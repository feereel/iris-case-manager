from iris_pusher.dfir_iris_client.session import ClientSession
from iris_pusher.dfir_iris_client.case import Case 
from iris_pusher.dfir_iris_client.helper.utils import (
    get_data_from_resp,
    assert_api_resp,
)
from .datastore_entities import *

import os

class DatastoreExtractor:
    def __init__(self, session: ClientSession, cid: int) -> None:
        self.session: ClientSession = session
        self.case: Case = Case(session=self.session)
        self.cid = cid
    
    def extract(self, os_folder: str | None = None, case_folder: str | None = None) -> DatastoreFolder:
        data = self.list_ds()
        return self.extract_ds_tree(data, os_folder,case_folder)
        
    def extract_ds_tree(self, root: dict, os_folder: str | None = False, case_folder: str | None = False) -> DatastoreEntity:
        key, data = list(root.items())[0]
        entity_type, entity_id = key.split('-')
        
        if entity_type == 'd':
            new_os_path = os.path.join(os_folder, data['name']) if os_folder else None
            new_case_path = os.path.join(case_folder, data['name']) if os_folder else None
            if new_os_path:
                os.makedirs(new_os_path, exist_ok=True)
                        
            children=[self.extract_ds_tree({c_key: c_data}, os_folder=new_os_path, case_folder=new_case_path) for c_key, c_data in data['children'].items()]
            return DatastoreFolder(
                id=entity_id,
                case_id=self.cid,
                folder_name=data['name'],
                children=children,
                path=new_case_path
            )
            
        if entity_type == 'f':
            file_os_path = os.path.join(os_folder, data['file_original_name']) if os_folder else None
            file_case_path = os.path.join(case_folder, data['file_original_name']) if case_folder else None
            if file_os_path:
                with open(file_os_path, 'wb') as file:
                    response = self.case.download_ds_file(int(entity_id), self.cid)
                    file.write(response.content)
            
            return DatastoreFile(id=entity_id,
                                case_id=self.cid,
                                filename=data['file_original_name'],
                                file_description=data['file_description'],
                                file_is_ioc=data['file_is_ioc'] if data['file_is_ioc'] else False,
                                file_is_evidence=data['file_is_evidence'] if data['file_is_evidence'] else False,
                                file_password=data['file_password'],
                                file_tags=data['file_tags'].split(',') if data['file_tags'] else [],
                                path=file_case_path)
            
        raise KeyError("Datastore key is not valid")
        
    def list_ds(self):
        response = self.case.list_ds_tree(cid=self.cid)
        assert_api_resp(response, soft_fail=False)
        
        data = get_data_from_resp(response)
        return data