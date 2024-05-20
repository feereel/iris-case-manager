import json

def pretty(data: dict) -> None:
    return json.dumps(data, indent=2)

def extract_object(data: list, key: str) -> list:
    return [item[key] for item in data if key in item]

# Сhecks that the attribute is set 
def check_attributes(attribute_names: list[str]):
    def check(func):
        def wrapper(self, *args, **kwargs):
            for name in attribute_names:
                if not self.__getattribute__(name):
                    raise ValueError(f"{name} is not set")
                    
            return func(self, *args, **kwargs)
        
        return wrapper
    
    return check