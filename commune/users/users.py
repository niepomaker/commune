
import commune as c
from typing import Dict , Any, List
import streamlit as st
import json

class Users(c.Module):
    
    def add_user(self, name , auth:dict):
        key=self.get_key(key)
        
        
    def authenticate(self, data, staleness: int = 60, ) -> bool:
        
        '''
        Args:
            auth {
                'signature': str,
                'data': str (json) with ['timestamp'],
                'public_key': str
            }
            
            statleness: int (seconds) - how old the request can be
        return bool
        '''
        if not isinstance(data, dict):
            return False
        
        fn = data.get('fn', None)
        assert fn != None, 'Must provide a function name'
        
        assert fn in self.whitelist_functions(), f'AuthFail: Function {fn} not in whitelist'
        assert fn not in self.blacklist_functions(), f'AuthFail: Function {fn} in blacklist'
        
        # # check if user is in the list of users
        # is_user = self.is_user(auth)
        
        # # check the data
        # data = auth['data']
        
        # expiration  = self.time() - staleness
        # is_user = bool(data['timestamp'] > expiration)
            
        return True
        
        
        
    def is_user(self, auth: dict = None) -> bool:
        assert isinstance(auth, dict), 'Auth must be provided'
        for k in ['signature', 'data', 'public_key']:
            assert k in auth, f'Auth must have key {k}'
            
        user_address = self.verify(user, auth)
        if not hasattr(self, 'users'):
            self.users = {}
        return bool(user_address in self.users)
        
        
    @classmethod
    def add_user(cls, 
                 name: str = None,
                 signature: str = None,
                 role='sudo', **info):
        if not hasattr(self, 'users'):
            self.users = {}
        info.update(dict(timestamp=self.time(), 
                         role=role, 
                         user=user,
                         address=address))
        self.put(f'users/{user}/{role}', info)
    
    @classmethod
    def get_user(cls, user: str = None) -> dict:
        return cls.ls(f'users/{user}')
    
    @classmethod
    def rm_user(cls, user: str = None):
        self.users.pop(user, None)  
        
    @classmethod
    def users(self):
        return self._users

if __name__ == "__main__":
    Users.test()
    
    