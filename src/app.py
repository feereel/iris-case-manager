import os, shutil

from urllib.parse import urlparse
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile
from io import BytesIO
from pydantic import ValidationError

from iris_pusher.case_enitity import CaseData
from iris_pusher.case_extractor import CaseExtractor
from iris_pusher.case_creator import CaseCreator
from iris_pusher.dfir_iris_client.session import ClientSession
from iris_pusher.case_transfer import get_cases_ids

STORAGE_DIR = 'Cases'
CASE_DUMP_NAME = 'case.json'

from walkoff_app_sdk.app_base import AppBase

class IrisCaseHarvester(AppBase):
    __version__ = "1.0.0"
    app_name = "IrisCaseHarvester"
    
    def __init__(self, redis, logger, console_logger=None):
        """
        Each app should have this __init__ to set up Redis and logging.
        :param redis:
        :param logger:
        :param console_logger:
        """
        super().__init__(redis, logger, console_logger)

    def establish_session(self, apikey, host, agent=None, ssl_verify=None):
        url = urlparse(host)
        
        ssl_verify = True if ssl_verify.lower() == "true" else False
        agent = agent if agent else 'iris-client'
        
        try:
            return ClientSession(apikey=apikey, host=f"{url.scheme}://{url.netloc}", agent=agent, ssl_verify=ssl_verify)
        except ValueError as e:
            raise ValueError("Error while creating sesion... Check passed values")

    def list_all_cases(self, apikey, host, agent=None, ssl_verify=None):
        session = self.establish_session(apikey, host, agent, ssl_verify)
        cases_ids: list[int] = get_cases_ids(session=session)
        return {"success": True, "cases_ids": cases_ids}

    def export_case(self, apikey, cid, host, agent=None, ssl_verify=None):
        cid = int(cid)
        session = self.establish_session(apikey, host, agent, ssl_verify)
        
        with TemporaryDirectory() as temp_folder:
            uuid = str(uuid4())
            storage_folder = os.path.join(temp_folder, STORAGE_DIR)
            case_storage_folder = os.path.join(storage_folder, uuid)
            
            try:
                extractor = CaseExtractor(cid, session, ds_os_folder=case_storage_folder, donwload_another_case_files=True)
                model: CaseData = extractor.extract()
                case_path = os.path.join(case_storage_folder, model.datastore.folder_name)
                
                with open(os.path.join(case_path, CASE_DUMP_NAME), 'w') as f:
                    f.write(model.model_dump_json())
            except Exception as e:
                return e
            
            zip_path = shutil.make_archive(os.path.join(temp_folder, model.datastore.folder_name), 'zip', temp_folder, STORAGE_DIR)
        
            data = open(zip_path, 'rb').read()
            
            
            filedata = {
                "filename": os.path.basename(zip_path),
                "data": data,
            }

            fileret = self.set_files([filedata])
            value = {"success": True, "file_ids": fileret}
            
        return value

    def export_all_cases(self, apikey, host, agent=None, ssl_verify=None, in_one_file=None):
        in_one_file = True if in_one_file.lower() == "true" else False
        
        session = self.establish_session(apikey, host, agent, ssl_verify)
        cases_ids: list[int] = get_cases_ids(session=session)
        
        case_uuids: list[str] = []
        
        with TemporaryDirectory() as temp_folder:
            storage_folder = os.path.join(temp_folder, STORAGE_DIR)
            
            for case_id in cases_ids:
                uuid = str(uuid4())
                case_storage_folder = os.path.join(storage_folder, uuid)
                try:
                    extractor = CaseExtractor(case_id, session, ds_os_folder=case_storage_folder, donwload_another_case_files=True)
                    model: CaseData = extractor.extract()
                    case_path = os.path.join(case_storage_folder, model.datastore.folder_name)
                    case_uuids.append(uuid)
                    
                    with open(os.path.join(case_path, CASE_DUMP_NAME), 'w') as f:
                        f.write(model.model_dump_json())
                except Exception as e:
                    return e

            if in_one_file:
                zip_path = shutil.make_archive(os.path.join(temp_folder, 'Cases'), 'zip', temp_folder, STORAGE_DIR)
            
                data = open(zip_path, 'rb').read()
                
                filedata = {
                    "filename": os.path.basename(zip_path),
                    "data": data,
                }
                files = [filedata]
            else:
                files = []
                for uuid in case_uuids:
                    case_path = os.path.join(STORAGE_DIR, uuid)
                    zip_path = shutil.make_archive(os.path.join(temp_folder, uuid), 'zip', temp_folder, case_path)
                
                    data = open(zip_path, 'rb').read()
                    
                    filedata = {
                        "filename": os.path.basename(zip_path),
                        "data": data,
                    }
                    files.append(filedata)
            fileret = self.set_files(files)
            value = {"success": True, "file_ids": fileret}
                
        return value
    
    def import_case(self, apikey, host, file_id, publisher_name = 'IrisInitialClient',  agent=None, ssl_verify=None):
        session = self.establish_session(apikey, host, agent, ssl_verify)
        fileret = self.get_file(file_id)
        data = fileret['data']
        
        pushed = []
        skipped_by_dump = []
        skipped_by_validation = []
        skipped_by_push = []
        
        with TemporaryDirectory() as temp_folder:
            with ZipFile(BytesIO(data), 'r') as archive:
                archive.extractall(temp_folder)
            
            cases_path = os.path.join(temp_folder, STORAGE_DIR) 
            _, uuids, _ = next(os.walk(cases_path))
            
            for uuid in uuids:
                uuid_path = os.path.join(cases_path, uuid)
                _, dirs, _ = next(os.walk(uuid_path))
                if len(dirs) != 1:
                    raise ValueError("Cases count in folder with uuid is not equal to 1!")
                
                case_name = dirs[0]
                case_dump_path = os.path.join(uuid_path, case_name, CASE_DUMP_NAME)
            
                if not os.path.isfile(case_dump_path):
                    skipped_by_dump.append(uuid)
                    continue
                
                try:
                    case_data = CaseData.model_validate_json(open(case_dump_path, 'r').read())
                except ValidationError as e:
                    skipped_by_validation.append(uuid)
                    continue
                
                try:
                    creator = CaseCreator(session, case_data, publisher_name=publisher_name, ds_folder=uuid_path)
                    creator.push()
                    pushed.append(uuid)
                except Exception as e:
                    skipped_by_push.append(str(e))
                    continue
                
        return {"success": True, "pushed": pushed, "skipped_by_dump": skipped_by_dump, "skipped_by_validation": skipped_by_validation, "skipped_by_push": skipped_by_push}
            
if __name__ == "__main__":
    IrisCaseHarvester.run()