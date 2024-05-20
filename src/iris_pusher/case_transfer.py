
from iris_pusher.dfir_iris_client.session import ClientSession
from iris_pusher.dfir_iris_client.case import Case 
from iris_pusher.dfir_iris_client.helper.utils import (
    get_data_from_resp,
    assert_api_resp,
)

import logging as logger

from .helper.utils import extract_object
from .case_extractor import CaseExtractor
from .case_creator import CaseCreator

log = logger.getLogger(__name__)

def get_cases_ids(session: ClientSession) -> list[int]:
    case = Case(session=session)
    response = case.list_cases()
    assert_api_resp(response, soft_fail=False)
    
    data = get_data_from_resp(response)
    ids = extract_object(data, 'case_id')
    return ids

def transfer_all_cases(destination: ClientSession, source: ClientSession, publisher_name: str = None, collect_usernames: bool = False):
    ids = get_cases_ids(source)
    for id in ids:
        try:
            extractor = CaseExtractor(cid=id, session=source)
            data = extractor.extract()
            log.info(f"Case {id} extracted!")
            
            creator = CaseCreator(session=destination, case_data=data, publisher_name = publisher_name)
            creator.push()
            log.info(f"Case {id} transfered!")
        except:
            log.error(f"Can't transfer case {id}. skipping...")