import base64
import requests 
import os
from dotenv import load_dotenv
from commune.module.TheRoost.api import run
from typing import Optional

from commune import Module

c = Module()

load_dotenv()


class S2TAgent(Module):

    def __init__(self, config:Optional[dict]=None, **kwargs):
        self.init_s2t(config=config, **kwargs)


    def init_s2t(self, config=None, **kwargs):
        # initialize the validator
        config = self.set_config(config=config, kwargs=kwargs)
        # merge the config with the default config
        self.config = c.dict2munch({**S2TAgent.config, **config}) # merge the config with the default config
        # we want to make sure that the config is a munch
        self.sync()

        if self.config.workers > 0:


    with open("commune/module/agent_artificial/jfk.wav", "rb") as f:
        data = f.read()
        base64_data = base64.b64encode(data).decode("utf-8")

        print(base64_data)