from os import path

from iris_pusher.dfir_iris_client.session import ClientSession
from iris_pusher.dfir_iris_client.case import Case 
from iris_pusher.dfir_iris_client.helper.utils import (
    get_data_from_resp,
    assert_api_resp,
)
from .datastore_entities import *
from .datastore_extractor import DatastoreExtractor

class DatastoreCreator:
    def __init__(self, session: ClientSession, cid: int, ds_folder: str) -> None:
        self.session: ClientSession = session
        self.case: Case = Case(session=self.session)
        self.cid = cid
        self.ds_folder = ds_folder
        self.current_ds: DatastoreFolder = DatastoreExtractor(self.session, self.cid).extract()
        self.folders: dict = {} # (old_case_id, old_folder_id) -> new
        self.files: dict = {} # (old_case_id, old_file_id) -> new

    def create_entity(self, parent_id: int, entity: DatastoreEntity, save_entity_id=True) -> DatastoreEntity:
        if isinstance(entity, DatastoreFile):
            response = self.case.add_ds_file(
                parent_id=parent_id,
                file_stream=open(path.join(self.ds_folder, entity.path), 'rb'),
                filename=entity.filename,
                file_description=entity.file_description,
                file_is_ioc=entity.file_is_ioc,
                file_is_evidence=entity.file_is_evidence,
                file_password=entity.file_password,
                cid=self.cid
            )
            assert_api_resp(response, soft_fail=False)
            new_id = int(get_data_from_resp(response)['file_id'])
            if save_entity_id:
                self.files[(int(entity.case_id), int(entity.id))] = new_id
            
        elif isinstance(entity, DatastoreFolder):
            response = self.case.add_ds_folder(
                parent_id=parent_id,
                folder_name=entity.folder_name,
                cid=self.cid
            )
            assert_api_resp(response, soft_fail=False)
            new_id = int(get_data_from_resp(response)['path_id'])
            
            for child in entity.children:
                self.create_entity(new_id, child)
                
            if save_entity_id:
                self.folders[(int(entity.case_id), int(entity.id))] = new_id
        else:
            raise TypeError("Uncorrent type provided while creating datastore entity")
        
        return new_id

    def create_new_tree(self, ds: DatastoreFolder):
        self.remove_current_tree()
        
        response = self.case.rename_ds_folder(self.current_ds.id , ds.folder_name, self.cid)
        assert_api_resp(response, soft_fail=False)
        
        new_id = int(get_data_from_resp(response)['path_id'])
        self.folders[ds.id] = new_id
        
        for entity in ds.children:
            self.create_entity(self.current_ds.id , entity)
            
        return new_id
        
    def remove_current_tree(self):
        for entity in self.current_ds.children:
            if isinstance(entity, DatastoreFolder):
                self.case.delete_ds_folder(entity.id, self.cid)
            elif isinstance(entity, DatastoreFile):
                self.case.delete_ds_file(entity.id, self.cid)