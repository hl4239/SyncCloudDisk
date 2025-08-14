from enum import Enum

from pydantic import BaseModel, Field

class En(str,Enum):
    A='a'

class t1(BaseModel):
    t:str=Field(default=None)
    en:En=Field(default=None)

if __name__ == '__main__':
    tt1=t1(t='asd',en=En.A)
    dict_tt1=tt1.model_dump()
    print(dict_tt1)
    tt2=t1(**dict_tt1)
    print(tt2)
