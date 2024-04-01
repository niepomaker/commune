from commune import Module 
import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Union
from abc import ABC, abstractmethod 
from dotenv import load_dotenv

load_dotenv()

c = Module()

# Keys dict
keys = {}
key2ss58address = {}
key2mnemonic = {}




def status():
    for key, value in keys.items():
        print(key, c.stats(value))


def vali_info():
    for key, vlue in keys.items():
        print(key, c.stats(vlue))

def register_vali(vali_name):
    confirm = input("Please confirm register. This will consume Com. y/n: ")
    if confirm.lower() == 'y' or confirm.lower() == 'yes' or confirm.lower() == '1':
        c.register(
            module_key="5F4c6WjExFshz3QQ4U6xtEXqUyPFV2P66Z5ZBQpvSyCFnuHE", 
            key="5F4c6WjExFshz3QQ4U6xtEXqUyPFV2P66Z5ZBQpvSyCFnuHE",
            address=""
            )
    else:
        print("Aborting.")
        return



# Unstake from all subnets and keys
def unstake_all():
    post_balance = []
    for key, value in keys.items():
        c.unstake_all()
        c.unstake_many()
        post_balance.append([key, c.balance(value)])


bals=[]
def balances():
    for key, _ in keys.items():
        bals.append(f'{balance(key)}\n')

    return "\n".join(bals)





if __name__ == "__main__":
    #status()
    parse_keys()
    #balances()
    