
from retry import retry
from typing import *
import json
import os
import commune as c
import requests 

from substrateinterface import SubstrateInterface

U32_MAX = 2**32 - 1
U16_MAX = 2**16 - 1

class Subspace(c.Module):
    """
    Handles interactions with the subspace chain.
    """
    whitelist = ['query', 
                 'query_map', 
                 'get_module', 
                 'get_balance', 
                 'get_stake_to', 
                 'get_stake_from']
    
    cost = 1

    block_time = 8 # (seconds)
    fmt = 'j'
    git_url = 'https://github.com/commune-ai/subspace.git'
    default_config = c.get_config('subspace', to_munch=False)
    token_decimals = default_config['token_decimals']
    network = default_config['network']
    chain = network
    libpath = chain_path = c.libpath + '/subspace'
    spec_path = f"{chain_path}/specs"
    netuid = default_config['netuid']
    local = default_config['local']
    
    features = ['Keys', 
                'StakeTo',
                'Name', 
                'Address',
                'Weights',
                'Emission', 
                'Incentive', 
                'Dividends', 
                'LastUpdate',
                'ProfitShares',
                'Proposals', 
                'Voter2Info',
                ]

    def __init__( 
        self, 
        **kwargs,
    ):
        self.set_config(kwargs=kwargs)

    connection_mode = 'ws'

    def resolve_url(self, url:str = None, network:str = network, mode=None , **kwargs):
        """
        Resolves the URL for the given network and mode.

        Args:
            url (str, optional): The URL to resolve. Defaults to None.
            network (str, optional): The network to resolve the URL for. Defaults to the network specified in the config.
            mode (str, optional): The mode to use for resolving the URL. Defaults to the mode specified in the config.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The resolved URL.

        Raises:
            None

        Examples:
            >>> resolve_url(url='http://example.com', network='mainnet', mode='rpc')
            'http://0.0.0.0'

        Note:
            - If the `url` parameter is not provided, the function searches for matching providers in the config and resolves the URL accordingly.
            - The resolved URL is modified to replace the IP address with '0.0.0.0'.

        """
        mode = mode or self.config.connection_mode
        network = 'network' or self.config.network
        if url == None:
            
            url_search_terms = [x.strip() for x in self.config.url_search.split(',')]
            is_match = lambda x: any([url in x for url in url_search_terms])
            urls = []
            for provider, mode2url in self.config.urls.items():
                if is_match(provider):
                    chain = c.module('subspace.chain')
                    if provider == 'commune':
                        url = chain.resolve_node_url(url=url, chain=network, mode=mode) 
                    elif provider == 'local':
                        url = chain.resolve_node_url(url=url, chain='local', mode=mode)
                    else:
                        url = mode2url[mode]

                    if isinstance(url, list):
                        urls += url
                    else:
                        urls += [url] 

            url = c.choice(urls)
        
        url = url.replace(c.ip(), '0.0.0.0')
        

        return url
    
    url2substrate = {}
    def get_substrate(self, 
                network:str = 'main',
                url : str = None,
                websocket:str=None, 
                ss58_format:int=42, 
                type_registry:dict=None, 
                type_registry_preset='substrate-node-template',
                cache_region=None, 
                runtime_config=None, 
                ws_options=None, 
                auto_discover=True, 
                auto_reconnect=True, 
                trials:int = 10,
                cache:bool = True,
                mode = 'http',):
        
        network = network or self.config.network


        
        '''
        A specialized class in interfacing with a Substrate node.

        Parameters
       A specialized class in interfacing with a Substrate node.

        Parameters
        url : the URL to the substrate node, either in format <https://127.0.0.1:9933> or wss://127.0.0.1:9944
        
        ss58_format : The address type which account IDs will be SS58-encoded to Substrate addresses. Defaults to 42, for Kusama the address type is 2
        
        type_registry : A dict containing the custom type registry in format: {'types': {'customType': 'u32'},..}
        
        type_registry_preset : The name of the predefined type registry shipped with the SCALE-codec, e.g. kusama
        
        cache_region : a Dogpile cache region as a central store for the metadata cache
        
        use_remote_preset : When True preset is downloaded from Github master, otherwise use files from local installed scalecodec package
        
        ws_options : dict of options to pass to the websocket-client create_connection function
        : dict of options to pass to the websocket-client create_connection function
                
        '''
        if cache:
            if url in self.url2substrate:
                return self.url2substrate[url]


        while trials > 0:
            try:
                url = self.resolve_url(url, mode=mode, network=network)

                substrate= SubstrateInterface(url=url, 
                            websocket=websocket, 
                            ss58_format=ss58_format, 
                            type_registry=type_registry, 
                            type_registry_preset=type_registry_preset, 
                            cache_region=cache_region, 
                            runtime_config=runtime_config, 
                            ws_options=ws_options, 
                            auto_discover=auto_discover, 
                            auto_reconnect=auto_reconnect)
                break
            except Exception as e:
                trials = trials - 1
                if trials > 0:
                    raise e
        
        if cache:
            self.url2substrate[url] = substrate

        self.network = network
        self.url = url
        
        return substrate


    def set_network(self, 
                network:str = 'main',
                mode = 'http',
                trials = 10,
                url : str = None, **kwargs):
        """
        Set the network configuration and retrieve the corresponding substrate. 

        Args:
            network (str): The network to connect to (default is 'main').
            mode: The mode of connection (default is 'http').
            trials: The number of connection trials (default is 10).
            url (str): The URL for the network connection.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the network and URL information.
        """
               
        self.substrate = self.get_substrate(network=network, url=url, mode=mode, trials=trials , **kwargs)
        response =  {'network': self.network, 'url': self.url}
        c.print(response)
        
        return response

    def __repr__(self) -> str:
        return f'<Subspace: network={self.network}>'
    def __str__(self) -> str:

        return f'<Subspace: network={self.network}>'


    def rank_modules(self,search=None, k='stake', n=10, modules=None, reverse=True, names=False, **kwargs):
        """
        Generate function comment for the given function body.
        
        :param search: Optional, a search term.
        :param k: Optional, the key to rank the modules by.
        :param n: Optional, number of modules to return.
        :param modules: Optional, a list of modules to rank.
        :param reverse: Optional, whether to reverse the ranking.
        :param names: Optional, if True, return only module names.
        :param **kwargs: Additional keyword arguments.
        
        :return: A list of modules ranked according to the specified key.
        """
        modules = self.modules(search=search, **kwargs) if modules == None else modules
        modules = sorted(modules, key=lambda x: x[k], reverse=reverse)
        if names:
            return [m['name'] for m in modules]
        if n != None:
            modules = modules[:n]
        return modules[:n]
    
    def top_modules(self,search=None, k='stake', n=10, modules=None, **kwargs):
        top_modules = self.rank_modules(search=search, k=k, n=n, modules=modules, reverse=True, **kwargs)
        return top_modules[:n]
    
    def top_module_keys(self,search=None, k='dividends ', n=10, modules=None, **kwargs):
        top_modules = self.rank_modules(search=search, k=k, n=n, modules=modules, reverse=True, **kwargs)
        return [m['key'] for m in top_modules[:n]]
    
    best = best_modules = top_modules
    
    def bottom_modules(self,search=None, k='stake', n=None, modules=None, **kwargs):
        bottom_modules = self.rank_modules(search=search, k=k, n=n, modules=modules, reverse=False, **kwargs)
        return bottom_modules[:n]
    
    worst = worst_modules = bottom_modules
  
    def names2uids(self, names: List[str] = None, **kwargs ) -> Union['torch.tensor', list]:
        # queries updated network state
        names = names or []
        name2uid = self.name2uid(**kwargs)
        uids = []
        for name in names:
            if name in name2uid:
                uids += [name2uid[name]]
        return uids
    
    def get_netuid_for_subnet(self, network: str = None) -> int:
        """
        Get the netuid for a given subnet.

        Args:
            network (str, optional): The name of the network. Defaults to None.

        Returns:
            int: The netuid for the subnet. If the network is not found, returns 0.
        """
        return {'commune': 0}.get(network, 0)


    def get_existential_deposit(
        self,
        block: Optional[int] = None,
        fmt = 'nano'
    ) -> Optional['Balance']:
        """ Returns the existential deposit for the chain. """
        result = self.query_constant(
            module_name='Balances',
            constant_name='ExistentialDeposit',
            block = block,
        )
        
        if result is None:
            return None
        
        return self.format_amount( result, fmt = fmt )
        

    def wasm_file_path(self):
        """
        Returns the file path of the WASM file for the current library.

        :return: A string representing the file path of the WASM file.
        """
        wasm_file_path = self.libpath + '/target/release/wbuild/node-subspace-runtime/node_subspace_runtime.compact.compressed.wasm'
        return wasm_file_path

    def my_stake_from(self, netuid = 0, block=None, update=False, network=network, fmt='j', max_age=1000 , **kwargs):
        """
        Calculates the total stake from a specific network or subnet.

        Args:
            netuid (int, optional): The network ID. Defaults to 0.
            block (int, optional): The block number. Defaults to None.
            update (bool, optional): Whether to update the stake information. Defaults to False.
            network (str, optional): The network name. Defaults to network.
            fmt (str, optional): The format for the stake amount. Defaults to 'j'.
            max_age (int, optional): The maximum age of the stake information. Defaults to 1000.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the total stake from the specified network or subnet. The keys are the staker addresses and the values are the stake amounts formatted according to the specified format.
        """
        stake_from_tuples = self.stake_from(netuid=netuid,
                                             block=block,
                                               update=update, 
                                            network=network, 
                                               tuples = True,
                                               fmt=fmt, max_age=max_age, **kwargs)

        address2key = c.address2key()
        stake_from_total = {}
        if netuid == 'all':
            for netuid, stake_from_tuples_subnet in stake_from_tuples.items():
                for module_key,staker_tuples in stake_from_tuples_subnet.items():
                    for staker_key, stake in staker_tuples:
                        if module_key in address2key:
                            stake_from_total[staker_key] = stake_from_total.get(staker_key, 0) + stake

        else:
            for module_key,staker_tuples in stake_from_tuples.items():
                for staker_key, stake in staker_tuples:
                    if module_key in address2key:
                        stake_from_total[staker_key] = stake_from_total.get(staker_key, 0) + stake

        
        for staker_address in address2key.keys():
            if staker_address in stake_from_total:
                stake_from_total[staker_address] = self.format_amount(stake_from_total[staker_address], fmt=fmt)
        return stake_from_total   

    
    def delegation_fee(self, netuid = 0, block=None, network=None, update=False, fmt='j'):
        """
        Retrieve the delegation fee for a specific network user.

        Args:
            netuid (int, optional): The network user ID. Defaults to 0.
            block (str, optional): The block to query. Defaults to None.
            network (str, optional): The network to query. Defaults to None.
            update (bool, optional): Whether to update the query. Defaults to False.
            fmt (str, optional): The format of the query result. Defaults to 'j'.

        Returns:
            dict: The delegation fee information.
        """
        delegation_fee = self.query_map('DelegationFee', netuid=netuid, block=block ,update=update, network=network)
        return delegation_fee

    def stake_to(self, netuid=0, network=network, block=None, update=False, fmt='nano', **kwargs):
        """
        Query the 'StakeTo' data and format the results.

        Parameters:
        - netuid (int): The unique identifier for the network.
        - network (str): The network to query.
        - block (str): The block to query.
        - update (bool): Whether to update the query.
        - fmt (str): The format for the amount (e.g., 'nano').
        - **kwargs: Additional keyword arguments for the query.

        Returns:
        - dict: The structured stake information.
        """
        stake_to = self.query_map('StakeTo', netuid=netuid, block=block, update=update, network=network, **kwargs)
        format_tuples = lambda x: [[_k, self.format_amount(_v, fmt=fmt)] for _k,_v in x]
        if netuid == 'all':
            stake_to = {netuid: {k: format_tuples(v) for k,v in stake_to[netuid].items()} for netuid in stake_to}
        else:
            stake_to = {k: format_tuples(v) for k,v in stake_to.items()}
    
        return stake_to
    
    def my_stake_to(self, netuid = 0, block=None, update=False, network='main', fmt='j'):
        """
        Calculate the total stake for each staker address and return the aggregated stake totals.
        
        Parameters:
            netuid (int): The netuid to calculate the stake for. Default is 0.
            block (NoneType): The block to calculate the stake for. Default is None.
            update (bool): Flag to indicate whether to update the stake information. Default is False.
            network (str): The network to perform the stake calculation on. Default is 'main'.
            fmt (str): The format of the stake information. Default is 'j'.
        
        Returns:
            dict: A dictionary containing the staker addresses as keys and their total stakes as values.
        """
        stake_to = self.stake_to(netuid=netuid, block=block, update=update, network=network, fmt=fmt)
        address2key = c.address2key()
        stake_to_total = {}
        if netuid == 'all':
            stake_to_dict = stake_to
            for netuid, stake_to in stake_to_dict.items():
                for staker_address in address2key.keys():
                    if staker_address in stake_to:
                        stake_to_total[staker_address] = stake_to_total.get(staker_address, 0) + sum([v[1] for v in stake_to[staker_address]])
        else:
            for staker_address in address2key.keys():
                if staker_address in stake_to:
                    stake_to_total[staker_address] = stake_to_total.get(staker_address, 0) + sum([v[1] for v in stake_to[staker_address]])
        return stake_to_total
    
    def min_burn(self,  network='main', block=None, update=False, fmt='j'):
        """
        Retrieves the minimum burn amount for a given network and block.

        Args:
            network (str, optional): The name of the network. Defaults to 'main'.
            block (int, optional): The block number. Defaults to None.
            update (bool, optional): Whether to update the data. Defaults to False.
            fmt (str, optional): The format of the amount. Defaults to 'j'.

        Returns:
            str: The formatted minimum burn amount.

        """
        min_burn = self.query('MinBurn', block=block, update=update, network=network)
        return self.format_amount(min_burn, fmt=fmt)
    
    def query(self, name:str,  
              params = None, 
              module:str='SubspaceModule',
              block=None,  
              netuid = None,
              network: str = network, 
              save= True,
              mode = 'http',
            update=False):
        """
        A method to query a network with specific parameters and return the response value.

        Parameters:
            name (str): The name of the query.
            params (Optional): Additional parameters for the query (default None).
            module (str): The module to query from (default 'SubspaceModule').
            block: The block to specify for the query (default None).
            netuid: The unique identifier for the network (default None).
            network (str): The network to query from (default the value of 'network' variable).
            save (bool): Flag to indicate whether to save the query value (default True).
            mode (str): The mode of querying (default 'http').
            update (bool): Flag to indicate if the query result should be updated (default False).

        Returns:
            The response value of the query.
        """
        network = self.resolve_network(network)
        path = f'query/{network}/{module}.{name}'
    
        params = params or []
        if not isinstance(params, list):
            params = [params]
        if netuid != None and netuid != 'all':
            params = [netuid] + params
            
        # we want to cache based on the params if there are any
        if len(params) > 0 :
            path = path + f'::params::' + '-'.join([str(p) for p in params])

        if not update:
            value = self.get(path, None)
            if value != None:
                return value
        substrate = self.get_substrate(network=network, mode=mode)
        response =  substrate.query(
            module=module,
            storage_function = name,
            block_hash = None if block == None else substrate.get_block_hash(block), 
            params = params
        )
        value =  response.value

        # if the value is a tuple then we want to convert it to a list
        if save:
            self.put(path, value)

        return value

    def query_constant( self, 
                        constant_name: str, 
                       module_name: str = 'SubspaceModule', 
                       block: Optional[int] = None ,
                       network: str = None) -> Optional[object]:
        """
        Query a constant value from the blockchain substrate network.

        Parameters:
            constant_name (str): The name of the constant value to query.
            module_name (str): The name of the module where the constant is defined. Default is 'SubspaceModule'.
            block (Optional[int]): The block number to query the constant value at. Default is None.
            network (str): The network to query the constant value from.

        Returns:
            Optional[object]: The value of the queried constant.
        """

        network = self.resolve_network(network)
        substrate = self.get_substrate(network=network)

        value =  substrate.query(
            module=module_name,
            storage_function=constant_name,
            block_hash = None if block == None else substrate.get_block_hash(block)
        )
            
        return value
    
    

    @retry(tries=10, delay=1, backoff=2, max_delay=10)
    def query_map(self, name: str = 'StakeFrom', 
                  params: list = None,
                  block: Optional[int] = None, 
                  network:str = 'main',
                  netuid = None,
                  page_size=1000,
                  max_results=100000,
                  module='SubspaceModule',
                  update: bool = True,
                  max_age = None, # max age in seconds
                  mode = 'ws',
                  **kwargs
                  ) -> Optional[object]:
        """
        A function that queries a map based on specified parameters and returns the resulting map.
        
        Parameters:
            name (str): The name of the map to query.
            params (list): The parameters for the query.
            block (Optional[int]): The block number for the query.
            network (str): The network to query on.
            netuid : The unique identifier for the network.
            page_size (int): The size of the page for the query.
            max_results (int): The maximum number of results to retrieve.
            module (str): The module to query.
            update (bool): Whether to update the query results.
            max_age : The maximum age in seconds for the query.
            mode (str): The mode of querying.
            **kwargs: Additional keyword arguments for the query.
        
        Returns:
            Optional[object]: The queried map object.
        """


        # if all lowercase then we want to capitalize the first letter
        if name[0].islower():
            _splits = name.split('_')
            name = _splits[0].capitalize() + ''.join([s[0].capitalize() + s[1:] for s in _splits[1:]])
            
        if name  == 'Account':
            module = 'System'

        network = self.resolve_network(network, new_connection=False, mode=mode)
        path = f'query/{network}/{module}.{name}'
        # resolving the params
        params = params or []

        is_single_subnet = bool(netuid != 'all' and netuid != None)
        if is_single_subnet:
            params = [netuid] + params

        if not isinstance(params, list):
            params = [params]
        if len(params) > 0 :
            path = path + f'::params::' + '-'.join([str(p) for p in params])

        value = None if update else self.get(path, None, max_age=max_age)
        
        if value == None:
            network = self.resolve_network(network)
            # if the value is a tuple then we want to convert it to a list
            block = block or self.block
            substrate = self.get_substrate(network=network, mode=mode)
            qmap =  substrate.query_map(
                module=module,
                storage_function = name,
                params = params,
                page_size = page_size,
                max_results = max_results,
                block_hash =substrate.get_block_hash(block)
            )

            new_qmap = {} 
            progress_bar = c.progress(qmap, desc=f'Querying {name} map')
            for (k,v) in qmap:
                progress_bar.update(1)
                if not isinstance(k, tuple):
                    k = [k]
                if type(k) in [tuple,list]:
                    # this is a double map
                    k = [_k.value for _k in k]
                if hasattr(v, 'value'):
                    v = v.value
                    c.dict_put(new_qmap, k, v)
        else:
            new_qmap = value

        # this is a double
        if isinstance(new_qmap, dict) and len(new_qmap) > 0:

            k = list(new_qmap.keys())[0]    
            v = list(new_qmap.values())[0]

            if c.is_digit(k):
                new_qmap = {int(k): v for k,v in new_qmap.items()}
            new_qmap = dict(sorted(new_qmap.items(), key=lambda x: x[0]))
            if isinstance(v, dict):
                for k,v in new_qmap.items():
                    _k = list(v.keys())[0]
                    if c.is_digit(_k):
                        new_qmap[k] = dict(sorted(new_qmap[k].items(), key=lambda x: x[0]))
                        new_qmap[k] = {int(_k): _v for _k, _v in v.items()}

        self.put(path, new_qmap)

        return new_qmap
    
    def runtime_spec_version(self, network:str = 'main'):
        """
        Get the runtime version.

        Parameters:
            network (str): The network to retrieve the runtime version from. Defaults to 'main'.

        Returns:
            str: The runtime version.
        """
        # Get the runtime version
        self.resolve_network(network=network)
        c.print(self.substrate.runtime_config.__dict__)
        runtime_version = self.query_constant(module_name='System', constant_name='SpVersionRuntimeVersion')
        return runtime_version
        
        
    #####################################
    #### Hyper parameter calls. ####
    #####################################

    """ Returns network SubnetN hyper parameter """
    def n(self,  netuid: int = 0, network = 'main' ,block: Optional[int] = None, update=True, **kwargs ) -> int:
        """
        A description of the entire function, its parameters, and its return types.
        
            netuid: int = 0
            network: str = 'main'
            block: Optional[int] = None
            update: bool = True
            **kwargs

        Returns:
            int
        """
        if netuid == 'all':
            return sum(self.query_map('N', block=block , update=update, network=network, **kwargs))
        else:
            return self.query( 'N', params=[netuid], block=block , update=update, network=network, **kwargs)

    ##########################
    #### Account functions ###
    ##########################
    
    """ Returns network Tempo hyper parameter """
    def stakes(self, netuid: int = 0, block: Optional[int] = None, fmt:str='nano', max_staleness = 100,network=None, update=False, **kwargs) -> int:
        """
        A function that retrieves stakes for a given netuid and formats the amount based on the specified format.
        
        Parameters:
            netuid (int): The unique identifier for the stakes.
            block (Optional[int]): The block number associated with the stakes. Default is None.
            fmt (str): The format in which the amount should be displayed. Default is 'nano'.
            max_staleness (int): The maximum staleness allowed in retrieving the stakes. Default is 100.
            network: Additional network information.
            update (bool): A flag indicating whether to update the stakes. Default is False.
            **kwargs: Additional keyword arguments.
        
        Returns:
            int: A dictionary containing the formatted stakes.
        """
        stakes =  self.query_map('Stake', update=update, **kwargs)[netuid]
        return {k: self.format_amount(v, fmt=fmt) for k,v in stakes.items()}

    """ Returns the stake under a coldkey - hotkey pairing """
    
    def resolve_key_ss58(self, key:str, network='main', netuid:int=0, resolve_name=True, **kwargs):
        """
        Resolves a given key to its corresponding ss58 address.

        Args:
            key (str): The key to be resolved.
            network (str, optional): The network to use for resolution. Defaults to 'main'.
            netuid (int, optional): The network UID to use for resolution. Defaults to 0.
            resolve_name (bool, optional): Whether to resolve the key name. Defaults to True.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The ss58 address of the resolved key.
        """
        if key == None:
            key = c.get_key(key)

        if isinstance(key, str):
            if c.valid_ss58_address(key):
                return key
            else:

                if c.key_exists( key ):
                    key = c.get_key( key )
                    key_address = key.ss58_address
                else:
                    assert resolve_name, f"Invalid Key {key} as it should have ss58_address attribute."
                    name2key = self.name2key(network=network, netuid=netuid)

                    if key in name2key:
                        key_address = name2key[key]
                    else:
                        key_address = key 
        # if the key has an attribute then its a key
        elif hasattr(key, 'ss58_address'):
            key_address = key.ss58_address
        
        return key_address

    def subnet2modules(self, network:str='main', **kwargs):
        """
        Retrieves the modules for each subnet in the specified network.

        Args:
            network (str, optional): The network for which to retrieve the modules. Defaults to 'main'.
            **kwargs: Additional keyword arguments to be passed to the `my_modules` method.

        Returns:
            dict: A dictionary mapping each subnet UID to a list of modules.

        Raises:
            None

        Examples:
            >>> subnet2modules()
            {'subnet1': [module1, module2], 'subnet2': [module3]}

        Note:
            This method resolves the network before retrieving the modules for each subnet.

        """
        subnet2modules = {}
        self.resolve_network(network)

        for netuid in self.netuids():
            c.print(f'Getting modules for SubNetwork {netuid}')
            subnet2modules[netuid] = self.my_modules(netuid=netuid, **kwargs)

        return subnet2modules
    
    def module2netuids(self, network:str='main', **kwargs):
        """
        Generate a dictionary mapping module names to lists of network UIDs. 

        :param network: the network for which to generate the module to network UID mapping
        :param kwargs: additional keyword arguments
        :type network: str
        :return: a dictionary mapping module names to lists of network UIDs
        :rtype: dict
        """
        subnet2modules = self.subnet2modules(network=network, **kwargs)
        module2netuids = {}
        for netuid, modules in subnet2modules.items():
            for module in modules:
                if module['name'] not in module2netuids:
                    module2netuids[module['name']] = []
                module2netuids[module['name']] += [netuid]
        return module2netuids
    
    
    @classmethod
    def from_nano(cls,x):
        """
        Calculates the value of a given number in base units of the token.

        Args:
            x (float): The number to be converted.

        Returns:
            float: The value of the number in base units of the token.
        """
        return x / (10**cls.token_decimals)
    to_token = from_nano
    @classmethod
    def to_nanos(cls,x):
        """
        Converts a token amount to nanos
        """
        return x * (10**cls.token_decimals)
    from_token = to_nanos

    @classmethod
    def format_amount(cls, x, fmt='nano', decimals = None, format=None, features=None, **kwargs):
        fmt = format or fmt # format is an alias for fmt

        if fmt in ['token', 'unit', 'j', 'J']:
            x = x / 10**9
        
        if decimals != None:
            x = c.round_decimals(x, decimals=decimals)
  

        return x
    
    def get_stake( self, key_ss58: str, block: Optional[int] = None, netuid:int = None , fmt='j', update=True ) -> Optional['Balance']:
        """
        Retrieves the stake for a given key on a specified network.

        Args:
            key_ss58 (str): The SS58-encoded key for which to retrieve the stake.
            block (Optional[int], optional): The block number to query the stake at. Defaults to None, which retrieves the current stake.
            netuid (int, optional): The network identifier. Defaults to None, which retrieves the stake for the default network.
            fmt (str, optional): The format in which to return the stake amount. Defaults to 'j'.
            update (bool, optional): Whether to update the stake before retrieving it. Defaults to True.

        Returns:
            Optional['Balance']: The stake amount for the given key on the specified network, formatted according to the specified format.
        """
        
        key_ss58 = self.resolve_key_ss58( key_ss58)
        netuid = self.resolve_netuid( netuid )
        stake = self.query( 'Stake',params=[netuid, key_ss58], block=block , update=update)
        return self.format_amount(stake, fmt=fmt)

    

    def all_key_info(self, netuid='all', timeout=10, update=False, **kwargs):
        """
        Retrieves all key information for a given netuid.

        :param netuid: A string representing the netuid for which to retrieve key information. Defaults to 'all'.
        :param timeout: An integer representing the timeout value in seconds. Defaults to 10.
        :param update: A boolean indicating whether to update the key information. Defaults to False.
        :param **kwargs: Additional keyword arguments.

        :return: A list of key information dictionaries.
        """
        my_keys = c.my_keys()


    def key_info(self, key:str = None, netuid='all', timeout=10, update=False, **kwargs):
        """
        Get information about the key, including balance and stake information.

        Parameters:
            key (str): The key to retrieve information for.
            netuid (str): The network UID to retrieve information for. Defaults to 'all'.
            timeout (int): The timeout for the request. Defaults to 10.
            update (bool): Whether to update the information. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the balance and stake information for the key.
        """
        key = self.resolve_key_ss58(key)
        stake_to = self.stake_to(update=update, netuid=netuid, **kwargs)
        key2address = c.key2address()
        my_stake_to = {}
        if netuid == 'all':
            for i,stake_to_dict in enumerate(stake_to):
                if key in stake_to_dict:
                    my_stake_to[i] = stake_to_dict[key]
        key_info = {
            'balance': c.get_balance(key=key, **kwargs),
            'stake_to': my_stake_to,
        }
        return key_info

        

    def get_stake_to( self, 
                     key: str = None, 
                     module_key=None,
                     netuid:int = 0 ,
                       block: Optional[int] = None, 
                       timeout=20,
                       names = False,
                        fmt='j' , network=None, update=True,
                         **kwargs) -> Optional['Balance']:
        """
        Retrieves the stake to amount for a given key and network.

        Args:
            key (str, optional): The key to retrieve the stake to amount for. Defaults to None.
            module_key (Any, optional): The module key to retrieve the stake to amount for. Defaults to None.
            netuid (int, optional): The netuid to retrieve the stake to amount for. Defaults to 0.
            block (Optional[int], optional): The block number to retrieve the stake to amount for. Defaults to None.
            timeout (int, optional): The timeout value for the request. Defaults to 20.
            names (bool, optional): Whether to retrieve the names of the keys. Defaults to False.
            fmt (str, optional): The format of the amount. Defaults to 'j'.
            network (Any, optional): The network to retrieve the stake to amount for. Defaults to None.
            update (bool, optional): Whether to update the stake to amount. Defaults to True.
            **kwargs: Additional keyword arguments.

        Returns:
            Optional['Balance']: The stake to amount for the given key and network.
        """

        if netuid == 'all':
            netuids = self.netuids()
            stake_to = [[] for _ in netuids]
            c.print(f'Getting stake to for all netuids {netuids}')

            while len(netuids) > 0:
                future2netuid = {}
                for netuid in netuids:
                    f = c.submit(self.get_stake_to, kwargs=dict(key=key, 
                                                                        module_key=module_key, 
                                                                        block=block, 
                                                                        netuid=netuid, fmt=fmt, update=update, **kwargs), timeout=timeout)
                    future2netuid[f] = netuid

                futures = list(future2netuid.keys())

                for ready in c.as_completed(futures, timeout=timeout):
                    netuid = future2netuid[ready]
                    result = ready.result()
                    if not c.is_error(result):
                        stake_to[netuid] = result
                        netuids.remove(netuid)
                        c.print(netuids)
    
                c.print(netuids)
                    
            
            return stake_to
        
        key_address = self.resolve_key_ss58( key )
        netuid = self.resolve_netuid( netuid )
        stake_to = self.query( 'StakeTo', params=[netuid, key_address], block=block, update=update, network=network)
        stake_to =  {k: self.format_amount(v, fmt=fmt) for k, v in stake_to}
        if module_key != None:
            module_key = self.resolve_key_ss58( module_key )
            stake_to ={ k:v for k, v in stake_to.items()}.get(module_key, 0)
        if names:
            keys = list(stake_to.keys())
            modules = self.get_modules(keys, netuid=netuid, **kwargs)
            key2name = {m['key']: m['name'] for m in modules}

            stake_to = {key2name[k]: v for k,v in stake_to.items()}
        return stake_to
    
    
    def get_stake_total( self, 
                     key: str = None, 
                     module_key=None,
                     netuid:int = 'all' ,
                       block: Optional[int] = None, 
                       timeout=20,
                       names = False,
                        fmt='j' , network=None, update=True,
                         **kwargs) -> Optional['Balance']:
        """
        Calculates the total stake for a given key, module key, netuid, block, timeout, names, fmt, network, and update.
        
        Args:
            key (str, optional): The key to calculate the stake for. Defaults to None.
            module_key (str, optional): The module key to calculate the stake for. Defaults to None.
            netuid (int, optional): The netuid to calculate the stake for. Defaults to 'all'.
            block (Optional[int], optional): The block to calculate the stake for. Defaults to None.
            timeout (int, optional): The timeout for the calculation. Defaults to 20.
            names (bool, optional): Whether to include names in the calculation. Defaults to False.
            fmt (str, optional): The format of the calculation. Defaults to 'j'.
            network (str, optional): The network to calculate the stake for. Defaults to None.
            update (bool, optional): Whether to update the calculation. Defaults to True.
        
        Returns:
            Optional['Balance']: The total stake calculated.
        """
        stake_to = self.get_stake_to(key=key, module_key=module_key, netuid=netuid, block=block, timeout=timeout, names=names, fmt=fmt, network=network, update=update, **kwargs)
        if netuid == 'all':
            return sum([sum(list(x.values())) for x in stake_to])
        else:
            return sum(stake_to.values())
    
        return stake_to
    
    get_staketo = get_stake_to
    
    def get_value(self, key=None):
        """
        Retrieves the value associated with a given key.

        Parameters:
            key (optional): The key to retrieve the value for. If not provided, the default key will be used.

        Returns:
            int: The value associated with the key.

        Raises:
            None

        Example:
            >>> obj = MyClass()
            >>> obj.get_value()
            42
        """
        key = self.resolve_key_ss58(key)
        value = self.get_balance(key)
        netuids = self.netuids()
        for netuid in netuids:
            stake_to = self.get_stake_to(key, netuid=netuid)
            value += sum(stake_to.values())
        return value    

    

    def get_stakers( self, key: str, block: Optional[int] = None, netuid:int = None , fmt='j' ) -> Optional['Balance']:
        """
        Retrieves the stakers for a given key.

        Parameters:
            key (str): The key to retrieve the stakers for.
            block (Optional[int]): The block number to retrieve the stakers from. Defaults to None.
            netuid (int): The netuid to retrieve the stakers from. Defaults to None.
            fmt (str): The format of the returned stakers. Defaults to 'j'.

        Returns:
            Optional['Balance']: A dictionary containing the stakers for the given key.
        """
        stake_from = self.get_stake_from(key=key, block=block, netuid=netuid, fmt=fmt)
        key2module = self.key2module(netuid=netuid)
        return {key2module[k]['name'] : v for k,v in stake_from}
    

    def get_stake_from( self, key: str, from_key=None, block: Optional[int] = None, netuid:int = None, fmt='j', update=True  ) -> Optional['Balance']:
        """
        Retrieves the stake from a specific key in the network.

        Args:
            key (str): The key to retrieve the stake from.
            from_key (str, optional): The key to retrieve the stake from specifically. Defaults to None.
            block (int, optional): The block number to retrieve the stake from. Defaults to None.
            netuid (int, optional): The network identifier. Defaults to None.
            fmt (str, optional): The format of the returned balance. Defaults to 'j'.
            update (bool, optional): Whether to update the state. Defaults to True.

        Returns:
            Optional['Balance']: The stake amount from the specified key. If `from_key` is provided, the stake amount from the specific key is returned. If no stake is found, None is returned.
        """
        key = self.resolve_key_ss58( key )
        netuid = self.resolve_netuid( netuid )
        state_from =  [(k, self.format_amount(v, fmt=fmt)) for k, v in self.query( 'StakeFrom', block=block, params=[netuid, key], update=update )]
 
        if from_key is not None:
            from_key = self.resolve_key_ss58( from_key )
            state_from ={ k:v for k, v in state_from}.get(from_key, 0)

        return state_from
    
    
    def get_total_stake_from( self, key: str, from_key=None, block: Optional[int] = None, netuid:int = None, fmt='j', update=True  ) -> Optional['Balance']:
        """
        Calculate the total stake from a given key.

        Parameters:
            key (str): The key to calculate the total stake from.
            from_key (Optional[str]): The key to calculate the total stake from, if different from the main key.
            block (Optional[int]): The block number to calculate the total stake from, if different from the current block.
            netuid (int): The network unique identifier.
            fmt (str): The format of the result.
            update (bool): Whether to update the stake information.

        Returns:
            Optional['Balance']: The total stake calculated from the given key.
        """
        stake_from = self.get_stake_from(key=key, from_key=from_key, block=block, netuid=netuid, fmt=fmt, update=update)
        return sum([v for k,v in stake_from])
    
    get_stakefrom = get_stake_from 


    ###########################
    #### Global Parameters ####
    ###########################

    @property
    def block(self, network:str=None, trials=100) -> int:
        """
        A property function that returns the block for a given network.

        Args:
            network (str, optional): The network for which to get the block. Defaults to None.
            trials (int): The number of trials to attempt.

        Returns:
            int: The block for the specified network.
        """
        return self.get_block(network=network)


    
   
    @classmethod
    def archived_blocks(cls, network:str=network, reverse:bool = True) -> List[int]:
        """
        Returns a list of archived blocks.

        Args:
            network (str): The network for which the blocks are being retrieved.
            reverse (bool): Flag to indicate whether the blocks should be returned in reverse order.

        Returns:
            List[int]: A list of integers representing the archived blocks.
        """
        # returns a list of archived blocks 
        
        blocks =  [f.split('.B')[-1].split('.json')[0] for f in cls.glob(f'archive/{network}/state.B*')]
        blocks = [int(b) for b in blocks]
        sorted_blocks = sorted(blocks, reverse=reverse)
        return sorted_blocks

    @classmethod
    def oldest_archive_path(cls, network:str=network) -> str:
        """
        A class method that returns the path to the oldest archive for a given network.

        Args:
            cls: The class itself.
            network (str): The network for which the oldest archive path is needed.

        Returns:
            str: The path to the oldest archive for the specified network.
        """
        oldest_archive_block = cls.oldest_archive_block(network=network)
        assert oldest_archive_block != None, f"No archives found for network {network}"
        return cls.resolve_path(f'state_dict/{network}/state.B{oldest_archive_block}.json')
    @classmethod
    def newest_archive_block(cls, network:str=network) -> str:
        """
        A method to retrieve the newest archive block for a given network.

        Parameters:
            network (str): The network for which the newest archive block is retrieved.

        Returns:
            str: The newest archive block.
        """
        blocks = cls.archived_blocks(network=network, reverse=True)
        return blocks[0]
    @classmethod
    def newest_archive_path(cls, network:str=network) -> str:
        """
        Returns the path of the newest archive file for the given network.

        :param network: The name of the network (default: network).
        :type network: str
        :return: The path of the newest archive file.
        :rtype: str
        """
        oldest_archive_block = cls.newest_archive_block(network=network)
        return cls.resolve_path(f'archive/{network}/state.B{oldest_archive_block}.json')
    @classmethod
    def oldest_archive_block(cls, network:str=network) -> str:
        """
        Return the oldest archive block for the given network.

        Args:
            network (str): The network for which the archived blocks are retrieved.

        Returns:
            str: The oldest archive block, or None if no blocks are found.
        """
        blocks = cls.archived_blocks(network=network, reverse=True)
        if len(blocks) == 0:
            return None
        return blocks[-1]

    @classmethod
    def ls_archives(cls, network=network):
        """
        Retrieves a list of archives for the specified network.

        Args:
            network (str, optional): The name of the network to retrieve archives for. Defaults to the network specified in the class.

        Returns:
            List[str]: A list of archive file paths that match the specified network.

        Raises:
            None

        Examples:
            >>> Subspace.ls_archives()
            ['state_dict/network1.zip', 'state_dict/network2.zip']
            >>> Subspace.ls_archives(network='network1')
            ['state_dict/network1.zip']
        """
        if network == None:
            network = cls.network 
        return [f for f in cls.ls(f'state_dict') if os.path.basename(f).startswith(network)]

    
    @classmethod
    def block2archive(cls, network=network):
        """
        Generate a dictionary mapping block numbers to archive paths for a given network.

        :param network: The network for which to generate the dictionary. Defaults to the value of the 'network' parameter.
        :type network: str
        :return: A dictionary mapping block numbers to archive paths.
        :rtype: dict
        """
        paths = cls.ls_archives(network=network)

        block2archive = {int(p.split('-')[-1].split('-time')[0]):p for p in paths if p.endswith('.json') and f'{network}.block-' in p}
        return block2archive

    def latest_archive_block(self, network=network) -> int:
        """
        Returns the latest block number of the archive for a given network.

        Parameters:
            network (str): The network to get the latest archive block for. Defaults to the network specified in the class.

        Returns:
            int: The latest block number of the archive.
        """
        latest_archive_path = self.latest_archive_path(network=network)
        block = int(latest_archive_path.split(f'.block-')[-1].split('-time')[0])
        return block


        

    @classmethod
    def time2archive(cls, network=network):
        """
        A class method to generate a dictionary mapping block timestamps to archive file paths.
        
        Args:
            cls: The class itself.
            network: The network to retrieve the archives from.
        
        Returns:
            Dictionary: A dictionary mapping block timestamps to archive file paths.
        """
        paths = cls.ls_archives(network=network)

        block2archive = {int(p.split('time-')[-1].split('.json')[0]):p for p in paths if p.endswith('.json') and f'time-' in p}
        return block2archive

    @classmethod
    def datetime2archive(cls,search=None, network=network):
        """
        Converts a datetime object to an archive format based on the specified search criteria.

        Parameters:
            search (str, optional): The search criteria to filter the datetime objects. Defaults to None.
            network (str): The network to use for the conversion. Defaults to the value of the 'network' class variable.

        Returns:
            dict: A dictionary mapping datetime objects to their corresponding archive values. The dictionary is sorted by datetime in ascending order.
                  If a search criteria is provided, only the datetime objects that match the search criteria will be included in the result.
        """
        time2archive = cls.time2archive(network=network)
        datetime2archive = {c.time2datetime(time):archive for time,archive in time2archive.items()}
        # sort by datetime
        # 
        datetime2archive = {k:v for k,v in sorted(datetime2archive.items(), key=lambda x: x[0])}
        if search != None:
            datetime2archive = {k:v for k,v in datetime2archive.items() if search in k}
        return datetime2archive



    @classmethod
    def latest_archive_path(cls, network=network):
        """
        Returns the path of the latest archive available for the given network.

        Parameters:
            network (str): The network for which to retrieve the latest archive path. Defaults to the value of the 'network' variable.

        Returns:
            str or None: The path of the latest archive if it exists, None otherwise.
        """
        latest_archive_time = cls.latest_archive_time(network=network)
    
        if latest_archive_time == None:
            return None
        time2archive = cls.time2archive(network=network)
        return time2archive[latest_archive_time]

    @classmethod
    def latest_archive_time(cls, network=network):
        """
        Returns the latest archive time for the given network.

        Parameters:
            network (str): The network for which to retrieve the latest archive time. Defaults to the value of the `network` parameter in the class.

        Returns:
            datetime or None: The latest archive time if there are archive times available, None otherwise.
        """
        time2archive = cls.time2archive(network=network)
        if len(time2archive) == 0:
            return None
        latest_time = max(time2archive.keys())
        return latest_time

    @classmethod
    def lag(cls, network:str = network):
        """
        Calculate the time lag between the current timestamp and the latest archive time of a network.

        Args:
            network (str, optional): The network for which to calculate the time lag. Defaults to the value of the `network` parameter.

        Returns:
            int: The time lag in seconds.

        """
        return c.timestamp() - cls.latest_archive_time(network=network) 
    @classmethod
    def latest_archive_datetime(cls, network=network):
        """
        Retrieves the latest archive datetime for a given network.

        :param network: The network for which to retrieve the latest archive datetime. Defaults to the class variable 'network'.
        :type network: str
        :return: The latest archive datetime for the given network.
        :rtype: datetime.datetime
        :raises AssertionError: If no archives are found for the given network.
        """
        latest_archive_time = cls.latest_archive_time(network=network)
        assert latest_archive_time != None, f"No archives found for network {network}"
        return c.time2datetime(latest_archive_time)

    @classmethod
    def latest_archive(cls, network=network):
        """
        Returns the latest archive of the class.

        :param network: The network to retrieve the archive from. Defaults to the value of the `network` parameter.
        :type network: Any
        :return: The latest archive of the class.
        :rtype: dict
        """
        path = cls.latest_archive_path(network=network)
        if path == None:
            return {}
        return cls.get(path, {})
    
 


    def light_sync(self, network=None, remote:bool=True, netuids=None, local:bool=True, save:bool=True, timeout=20, **kwargs):
        """
        Synchronizes the local network with a remote network by fetching the latest data from the remote network and updating the local network accordingly.

        Args:
            network (str, optional): The name of the network to sync with. Defaults to None.
            remote (bool, optional): Whether to fetch data from the remote network. Defaults to True.
            netuids (list, optional): A list of network UIDs to sync. Defaults to None.
            local (bool, optional): Whether to update the local network. Defaults to True.
            save (bool, optional): Whether to save the updated data. Defaults to True.
            timeout (int, optional): The maximum time in seconds to wait for the synchronization to complete. Defaults to 20.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the synchronization result.
                - 'success' (bool): True if the synchronization was successful, False otherwise.
                - 'block' (int): The block number at which the synchronization was performed.
        """
        netuids = self.netuids(network=network, update=True) if netuids == None else netuids
        assert len(netuids) > 0, f"No netuids found for network {network}"
        stake_from_futures = []
        namespace_futures = []
        weight_futures = []
        for netuid in netuids:
            stake_from_futures += [c.asubmit(self.stake_from, netuid=netuid, network=network, update=True)]
            namespace_futures += [c.asubmit(self.namespace, netuid=netuid, network=network, update=True)]
            weight_futures += [c.asubmit(self.weights, netuid=netuid, network=network, update=True)]

        c.gather(stake_from_futures + namespace_futures + weight_futures, timeout=timeout)

        # c.print(namespace_list)
        return {'success': True, 'block': self.block}


    def loop(self, intervals = {'light': 5, 'full': 600}, network=None, remote:bool=True):
        """
        A function that loops indefinitely, checking for staleness and syncing data if necessary.

        Parameters:
            intervals (dict): A dictionary containing the intervals for light and full updates.
            network (optional): The network to sync data with.
            remote (bool): Flag indicating whether to execute the function remotely.

        Returns:
            None
        """
        if remote:
            return self.remote_fn('loop', kwargs=dict(intervals=intervals, network=network, remote=False))
        last_update = {k:0 for k in intervals.keys()}
        staleness = {k:0 for k in intervals.keys()}
        c.get_event_loop()

        while True:
            block = self.block
            timestamp = c.timestamp()
            staleness = {k:timestamp - last_update[k] for k in intervals.keys()}
            if staleness["full"] > intervals["full"]:
                request = {
                            'network': network, 
                           'block': block
                           }
                try:
                    self.sync(**request)
                except Exception as e:
                    c.print(e)
                    continue
                last_update['full'] = timestamp
            

    def subnet_exists(self, subnet:str, network=None) -> bool:
        """
        Check if a subnet exists in the given network.

        Args:
            subnet (str): The subnet to check.
            network (Optional[str]): The network to check in. If not provided, the default network will be used.

        Returns:
            bool: True if the subnet exists in the network, False otherwise.
        """
        subnets = self.subnets(network=network)
        return bool(subnet in subnets)

    def subnet_emission(self, netuid:str = 0, network=None, block=None, update=False, **kwargs):
        """
        Calculate the emission of a subnet.

        Args:
            netuid (str, optional): The unique identifier of the subnet. Defaults to 0.
            network (Network, optional): The network object. Defaults to None.
            block (Block, optional): The block object. Defaults to None.
            update (bool, optional): Whether to update the emission. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            float: The total emission of the subnet.
        """
        emissions = self.emission(block=block, update=update, network=network, netuid=netuid, **kwargs)
        if isinstance(emissions[0], list):
            emissions = [sum(e) for e in emissions]
        return sum(emissions)
    
    
    def unit_emission(self, network=None, block=None, update=False, **kwargs):
        """
        Retrieves the unit emission value for a given network and block.

        Args:
            network (str, optional): The name of the network to query. Defaults to None.
            block (int, optional): The block number to query. Defaults to None.
            update (bool, optional): Whether to update the query result. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            The unit emission value.

        Raises:
            None.
        """
        return self.query_constant( "UnitEmission", block=block,network=network)

    def subnet_state(self,  netuid='all',  network='main', block=None, update=False, fmt='j', **kwargs):
        """
        Get the state of a subnet with the given parameters.

        Args:
            netuid (str): The unique identifier of the subnet. Defaults to 'all'.
            network (str): The network to which the subnet belongs. Defaults to 'main'.
            block (NoneType): The block to be considered. Defaults to None.
            update (bool): Whether to update the state. Defaults to False.
            fmt (str): The format of the state. Defaults to 'j'.
            **kwargs: Additional keyword arguments for flexibility.

        Returns:
            dict: A dictionary containing the state of the subnet, including its parameters and modules.
        """

        subnet_state = {
            'params': self.subnet_params(netuid=netuid, network=network, block=block, update=update, fmt=fmt, **kwargs),
            'modules': self.modules(netuid=netuid, network=network, block=block, update=update, fmt=fmt, **kwargs),
        }
        return subnet_state

        

    def subnet_states(self, *args, **kwargs):
        """
        Generate the subnet states for each network UID.

        :param args: Additional arguments to pass to the subnet function.
        :param kwargs: Additional keyword arguments to pass to the subnet function.
        :return: List of subnet states for each network UID.
        """
        subnet_states = []

        for netuid in c.tqdm(self.netuids()):
            subnet_state = self.subnet(*args,  netuid=netuid, **kwargs)
            subnet_states.append(subnet_state)
        return subnet_states

    def total_stake(self, network=network, block: Optional[int] = None, netuid:int='all', fmt='j', update=False) -> 'Balance':
        """
        Calculate the total stake for a given network.

        Args:
            network: The network for which the total stake is being calculated.
            block: The block number to consider (default is None).
            netuid: The unique identifier for the network stake (default is 'all').
            fmt: The format of the calculation (default is 'j').
            update: A flag to indicate if the stake data should be updated.

        Returns:
            Balance: The total stake amount.
        """
        return sum([sum([sum(list(map(lambda x:x[1], v))) for v in vv.values()]) for vv in self.stake_to(network=network, block=block,update=update, netuid='all')])

    def total_balance(self, network=network, block: Optional[int] = None, fmt='j', update=False) -> 'Balance':
        """
        Calculate the total balance for the given network and block, with the option to update the balances. 

        Args:
            network: The network for which the balance is being calculated.
            block: The block number for which the balance is being calculated.
            fmt: The format of the balance calculation.
            update: A boolean indicating whether to update the balances.

        Returns:
            Balance: The total balance calculated.
        """
        return sum(list(self.balances(network=network, block=block, fmt=fmt).values()), update=update)

    def mcap(self, network=network, block: Optional[int] = None, fmt='j', update=False) -> 'Balance':
        """
        Calculates the MCap (Market Capitalization) of the entity represented by the current instance.

        Args:
            network (str, optional): The network on which the calculation is performed. Defaults to the default network.
            block (int, optional): The block number at which the calculation is performed. If None, the latest block is used. Defaults to None.
            fmt (str, optional): The format in which the amount is returned. Defaults to 'j' (JSON).
            update (bool, optional): Whether to update the data before calculating the MCap. Defaults to False.

        Returns:
            Balance: The MCap of the entity represented by the current instance, formatted according to the specified format.
        """
        total_balance = self.total_balance(network=network, block=block, update=update)
        total_stake = self.total_stake(network=network, block=block, update=update)
        return self.format_amount(total_stake + total_balance, fmt=fmt)
    
    market_cap = total_supply = mcap  
            
        
    @classmethod
    def feature2storage(cls, feature:str):
        """
        Convert a feature string to a storage string.

        Args:
            feature (str): The feature string to be converted.

        Returns:
            str: The storage string generated from the feature string.

        Example:
            >>> feature2storage('my_feature')
            'MyFeature'

        Note:
            This function iterates over each character in the feature string and converts it to uppercase if it is the first character of a word. It also inserts a capital letter after each underscore in the feature string.

        """
        storage = ''
        capitalize = True
        for i, x in enumerate(feature):
            if capitalize:
                x =  x.upper()
                capitalize = False

            if '_' in x:
                capitalize = True

            storage += x
        return storage

    
    def subnet_params(self, 
                    netuid=0,
                    network = network,
                    block : Optional[int] = None,
                    update = False,
                    timeout = 30,
                    fmt:str='j', 
                    rows:bool = True
                    ) -> list:
        """
        Retrieves the parameters of a subnet.

        Args:
            netuid (int, optional): The unique identifier of the subnet. Defaults to 0.
            network (str, optional): The name of the network. Defaults to 'network'.
            block (Optional[int], optional): The block number. Defaults to None.
            update (bool, optional): Whether to update the cache. Defaults to False.
            timeout (int, optional): The timeout value for the query. Defaults to 30.
            fmt (str, optional): The format of the amount. Defaults to 'j'.
            rows (bool, optional): Whether to return the parameters in row format. Defaults to True.

        Returns:
            list: The parameters of the subnet.

        Raises:
            None

        Example:
            >>> subnet_params(netuid=0, network='network', block=None, update=False, timeout=30, fmt='j', rows=True)
            [{'tempo': 10, 'immunity_period': 5, 'min_allowed_weights': 0.1, 'max_allowed_weights': 1.0, 'max_allowed_uids': 100, 'min_stake': 1000, 'founder': 'John', 'founder_share': 0.1, 'incentive_ratio': 0.5, 'trust_ratio': 0.3, 'vote_threshold': 0.5, 'vote_mode': 'majority', 'max_weight_age': 100, 'name': 'Subnet1', 'max_stake': 10000}]
        """

        name2feature  = {
                'tempo': "Tempo",
                'immunity_period': 'ImmunityPeriod',
                'min_allowed_weights': 'MinAllowedWeights',
                'max_allowed_weights': 'MaxAllowedWeights',
                'max_allowed_uids': 'MaxAllowedUids',
                'min_stake': 'MinStake',
                'founder': 'Founder', 
                'founder_share': 'FounderShare',
                'incentive_ratio': 'IncentiveRatio',
                'trust_ratio': 'TrustRatio',
                'vote_threshold': 'VoteThresholdSubnet',
                'vote_mode': 'VoteModeSubnet',
                'max_weight_age': 'MaxWeightAge',
                'name': 'SubnetNames',
                'max_stake': 'MaxStake',
            }
        

        network = self.resolve_network(network)
        path = f'cache/{network}.subnet_params.json'
        subnet_params = None if update else self.get(path, None) 
    
        
        features = list(name2feature.keys())
        block = block or self.block

        if subnet_params == None:
            def query(**kwargs ):
                return self.query_map(**kwargs)
            
            subnet_params = {}
            n = len(features)
            progress = c.tqdm(total=n, desc=f'Querying {n} features')
            while True:
                
                features_left = [f for f in features if f not in subnet_params]
                if len(features_left) == 0:
                    c.print(f'All features queried, {c.emoji("checkmark")}')
                    break

                name2job = {k:c.submit(query, dict(name=v, update=update, block=block)) for k, v in name2feature.items()}
                jobs = list(name2job.values())
                results = c.wait(jobs, timeout=timeout)
                for i, feature in enumerate(features_left):
                    if c.is_error(results[i]):
                        c.print(f'Error querying {results[i]}')
                    else:
                        subnet_params[feature] = results[i]
                        progress.update(1)

                        
            
            self.put(path, subnet_params)


        subnet_params = {f: {int(k):v for k,v in subnet_params[f].items()} for f in subnet_params}


        if netuid != None and netuid != 'all':
            netuid = self.resolve_netuid(netuid)
            new_subnet_params = {}
            for k,v in subnet_params.items():
                new_subnet_params[k] = v[netuid]
            subnet_params = new_subnet_params
            for k in ['min_stake', 'max_stake']:
                subnet_params[k] = self.format_amount(subnet_params[k], fmt=fmt)

        else:
            if rows:
                num_subnets = len(subnet_params['tempo'])
                subnets_param_rows = []
                for netuid in range(num_subnets):
                    subnets_param_row = {}
                    for k in subnet_params.keys():
                        c.print(k, subnet_params[k], netuid)
                        subnets_param_row[k] = subnet_params[k][netuid]
                    subnets_param_rows.append(subnets_param_row)
                subnet_params = subnets_param_rows    

                            
        return subnet_params
    
    subnet = subnet_params


    def subnet2params( self, network: int = None, block: Optional[int] = None ) -> Optional[float]:
        """
        Generate subnet parameters for a given network and block, returning a dictionary mapping subnets to their parameters.
        
        Args:
            network (int): The network identifier.
            block (Optional[int]): The block identifier.

        Returns:
            Optional[float]: A dictionary mapping subnets to their parameters, or None if no parameters are found.
        """
        netuids = self.netuids(network=network)
        subnet2params = {}
        netuid2subnet = self.netuid2subnet()
        for netuid in netuids:
            subnet = netuid2subnet[netuid]
            subnet2params[subnet] = self.subnet_params(netuid=netuid, block=block)
        return subnet2params
    
    def subnet2emission( self, network: int = None, block: Optional[int] = None ) -> Optional[float]:
        """
        A function that converts a subnet to an emission, utilizing parameters from subnet2params.
        
        :param network: An integer representing the network.
        :param block: An optional integer representing the block.
        :return: An optional float value.
        """

        subnet2emission = self.subnet2params(network=network, block=block)
        return subnet2emission

    

    def subnet2state( self, network: int = None, block: Optional[int] = None ) -> Optional[float]:
        """
        Retrieves the state of a subnet.

        Args:
            network (int, optional): The network ID. Defaults to None.
            block (Optional[int], optional): The block number. Defaults to None.

        Returns:
            Optional[float]: The state of the subnet, or None if the state cannot be determined.
        """
        subnet2state = self.subnet2params(network=network, block=block)

        return subnet2state
            

    def is_registered( self, key: str, netuid: int = None, block: Optional[int] = None) -> bool:
        """
        Checks if a given key is registered in the network.

        Args:
            key (str): The key to check for registration.
            netuid (int, optional): The network ID to use for the check. Defaults to None.
            block (Optional[int], optional): The block number to query at. Defaults to None.

        Returns:
            bool: True if the key is registered, False otherwise.
        """
        netuid = self.resolve_netuid( netuid )
        if not c.valid_ss58_address(key):
            name2key = self.name2key(netuid=netuid)
            if key in name2key:
                key = name2key[key]
        assert c.valid_ss58_address(key), f"Invalid key {key}"
        is_reged =  bool(self.query('Uids', block=block, params=[ netuid, key ]))
        return is_reged

    def get_uid( self, key: str, netuid: int = 0, block: Optional[int] = None, update=False, **kwargs) -> int:
        """
        Retrieves the unique identifier (UID) associated with a given key.

        Args:
            key (str): The key for which to retrieve the UID.
            netuid (int, optional): The network unique identifier. Defaults to 0.
            block (Optional[int], optional): The block number to query. Defaults to None.
            update (bool, optional): Whether to update the UID. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            int: The unique identifier associated with the given key.

        """
        return self.query( 'Uids', block=block, params=[ netuid, key ] , update=update, **kwargs)  



    def register_subnets( self, *subnets, module='vali', **kwargs ) -> Optional['Balance']:
        """
        Registers one or more subnets with the specified module and returns a list of responses.
        
        Args:
            *subnets (str or List[str]): The subnets to register. Can be a single subnet or a list of subnets.
            module (str, optional): The module to register the subnets with. Defaults to 'vali'.
            **kwargs: Additional keyword arguments to pass to the register function.
        
        Returns:
            Optional[List[str]]: A list of responses, where each response corresponds to the registration of a subnet. 
                                Returns None if no subnets were registered.
        """
        if len(subnets) == 1:
            subnets = subnets[0]
        subnets = list(subnets)
        assert isinstance(subnets, list), f"Subnets must be a list. Got {subnets}"
        
        responses = []
        for subnet in subnets:
            tag = subnet
            response = c.register(module=module, tag=tag, subnet=subnet , **kwargs)
            c.print(response)
            responses.append(response)

        return responses
        

    def total_emission( self, netuid: int = 0, block: Optional[int] = None, fmt:str = 'j', **kwargs ) -> Optional[float]:
        """
        Calculate the total emission for a given netuid and block, and return the formatted amount.
        
        Args:
            netuid (int): The netuid for which the emission is calculated (default is 0).
            block (Optional[int]): The block number for which the emission is calculated (default is None).
            fmt (str): The format in which the total emission should be returned (default is 'j').
            **kwargs: Additional keyword arguments.
            
        Returns:
            Optional[float]: The formatted total emission amount.
        """
        total_emission =  sum(self.emission(netuid=netuid, block=block, **kwargs))
        return self.format_amount(total_emission, fmt=fmt)


    def regblock(self, netuid: int = 0, block: Optional[int] = None, network=network, update=False ) -> Optional[float]:
        """
        Retrieves the registration block for a given network UID and block number.

        Args:
            netuid (int, optional): The network UID. Defaults to 0.
            block (Optional[int], optional): The block number. Defaults to None.
            network (Network, optional): The network object. Defaults to network.
            update (bool, optional): Whether to update the registration block. Defaults to False.

        Returns:
            Optional[float]: The registration block for the given network UID and block number, or None if not found.
        """
        regblock =  self.query_map('RegistrationBlock',block=block, update=update )
        if isinstance(netuid, int):
            regblock = regblock[netuid]
        return regblock

    def age(self, netuid: int = None) -> Optional[float]:
        netuid = self.resolve_netuid( netuid )
        regblock = self.regblock(netuid=netuid)
        block = self.block
        age = {}
        for k,v in regblock.items():
            age[k] = block - v
        return age
    
    
     
    def global_params(self, 
                      network: str = 'main',
                         timeout = 2,
                         update = False,
                         block : Optional[int] = None,
                         fmt = 'nanos'
                          ) -> Optional[float]:
        """
        Retrieves the global parameters for a given network.

        Args:
            network (str, optional): The name of the network. Defaults to 'main'.
            timeout (int, optional): The timeout value for the query. Defaults to 2.
            update (bool, optional): Whether to update the cache. Defaults to False.
            block (int, optional): The block number. Defaults to None.
            fmt (str, optional): The format for amount values. Defaults to 'nanos'.

        Returns:
            Optional[dict]: A dictionary containing the global parameters, or None if the parameters could not be retrieved.
                The dictionary includes the following keys:
                - 'burn_rate': The burn rate.
                - 'max_name_length': The maximum allowed name length.
                - 'max_allowed_modules': The maximum allowed modules.
                - 'max_allowed_subnets': The maximum allowed subnets.
                - 'max_proposals': The maximum allowed proposals.
                - 'max_registrations_per_block': The maximum allowed registrations per block.
                - 'min_burn': The minimum burn amount.
                - 'min_stake': The minimum stake amount.
                - 'min_weight_stake': The minimum weight stake.
                - 'unit_emission': The unit emission.
                - 'tx_rate_limit': The transaction rate limit.
                - 'vote_threshold': The global vote threshold.
                - 'vote_mode': The global vote mode.

        Note:
            - If the 'update' parameter is set to True, the cache will be updated.
            - The 'block' parameter specifies the block number to query. If not provided, the latest block will be used.
            - The 'fmt' parameter specifies the format for the amount values.

        Example:
            global_params(network='main', timeout=2, update=False, block=None, fmt='nanos')
        """
        
        path = f'cache/{network}.global_params.json'
        global_params = None if update else self.get(path, None)

        if global_params == None:
            self.resolve_network(network)
            global_params = {}

            global_params['burn_rate'] =  'BurnRate' 
            global_params['max_name_length'] =  'MaxNameLength'
            global_params['max_allowed_modules'] =  'MaxAllowedModules' 
            global_params['max_allowed_subnets'] =  'MaxAllowedSubnets'
            global_params['max_proposals'] =  'MaxProposals'
            global_params['max_registrations_per_block'] =  'MaxRegistrationsPerBlock' 
            global_params['min_burn'] =  'MinBurn' 
            global_params['min_stake'] =  'MinStakeGlobal' 
            global_params['min_weight_stake'] =  'MinWeightStake'       
            global_params['unit_emission'] =  'UnitEmission' 
            global_params['tx_rate_limit'] =  'TxRateLimit' 
            global_params['vote_threshold'] =  'GlobalVoteThreshold' 
            global_params['vote_mode'] =  'VoteModeGlobal' 

            async def aquery_constant(f, **kwargs):
                return self.query_constant(f, **kwargs)
            
            for k,v in global_params.items():
                global_params[k] = aquery_constant(v, block=block )
            
            futures = list(global_params.values())
            results = c.wait(futures, timeout=timeout)
            global_params = dict(zip(global_params.keys(), results))

            for i,(k,v) in enumerate(global_params.items()):
                global_params[k] = v.value
            
            self.put(path, global_params)
        for k in ['min_stake', 'min_burn', 'unit_emission']:
            global_params[k] = self.format_amount(global_params[k], fmt=fmt)
        return global_params



    def balance(self,
                 key: str = None ,
                 block: int = None,
                 fmt='j',
                 network=None,
                 update=True) -> Optional['Balance']:
        r""" Returns the token balance for the passed ss58_address address
        Args:
            address (Substrate address format, default = 42):
                ss58 chain address.
        Return:
            balance (bittensor.utils.balance.Balance):
                account balance
        """
        key_ss58 = self.resolve_key_ss58( key )
        self.resolve_network(network)

        result = self.query(
                module='System',
                name='Account',
                params=[key_ss58],
                block = block,
                network=network,
                update=update
            )

        return  self.format_amount(result['data']['free'] , fmt=fmt)
        
    get_balance = balance 

    def get_account(self, key = None, network=None, update=True):
        """
        Retrieves the account information for a given key and network.

        Args:
            key (str, optional): The key for which to retrieve the account information. Defaults to None.
            network (str, optional): The network for which to retrieve the account information. Defaults to None.
            update (bool, optional): Whether to update the account information. Defaults to True.

        Returns:
            The account information for the given key and network.
        """
        self.resolve_network(network)
        key = self.resolve_key_ss58(key)
        account = self.substrate.query(
            module='System',
            storage_function='Account',
            params=[key],
        )
        return account
    
    def accounts(self, key = None, network=None, update=True, block=None):
        """
        Retrieves the account information for a given key and network.

        Args:
            key (str, optional): The key for which to retrieve the account information. Defaults to None.
            network (str, optional): The network for which to retrieve the account information. Defaults to None.
            update (bool, optional): Whether to update the account information. Defaults to True.

        Returns:
            The account information for the given key and network.
        """
        self.resolve_network(network)
        key = self.resolve_key_ss58(key)
        accounts = self.query_map(
            module='System',
            name='Account',
            update=update,
            block = block,
        )
        return accounts
    
    def balances(self,fmt:str = 'n', network:str = network, block: int = None, n = None, update=False , **kwargs) -> Dict[str, 'Balance']:
        """
        Retrieves the balances of all accounts on a specified network.

        Args:
            fmt (str, optional): The format in which the balances should be returned. Defaults to 'n'.
            network (str, optional): The network on which the accounts are located. Defaults to the value of the 'network' parameter.
            block (int, optional): The block number to retrieve the balances at. If not specified, the latest block will be used. Defaults to None.
            n (int, optional): The number of accounts to retrieve. If not specified, all accounts will be retrieved. Defaults to None.
            update (bool, optional): Whether to update the account information. Defaults to False.
            **kwargs: Additional keyword arguments that may be required by other methods.

        Returns:
            Dict[str, 'Balance']: A dictionary mapping account names to their corresponding balances.

        """
        accounts = self.accounts(network=network, update=update, block=block)
        balances =  {k:v['data']['free'] for k,v in accounts.items()}
        balances = {k: self.format_amount(v, fmt=fmt) for k,v in balances.items()}
        return balances
    
    
    def resolve_network(self, network: Optional[int] = None, new_connection =False, mode='ws', **kwargs) -> int:
        """
        A function to resolve the network connection based on inputs and return the network value.
        
        Parameters:
            network (Optional[int]): An optional integer representing the network.
            new_connection (bool): A boolean flag indicating if a new connection should be made.
            mode (str): A string representing the mode of connection.
            **kwargs: Additional keyword arguments.
        
        Returns:
            int: The resolved network value.
        """
        if  not hasattr(self, 'substrate') or new_connection:
            self.set_network(network, **kwargs)

        if network == None:
            network = self.network
        
        return network
    
    def resolve_subnet(self, subnet: Optional[int] = None) -> int:
        """
        Resolve the subnet based on the provided subnet ID.
        
        Parameters:
            subnet (Optional[int]): The ID of the subnet to resolve.
        
        Returns:
            int: The resolved subnet ID.
        """
        
        if isinstance(subnet, int):
            assert subnet in self.netuids()
            subnet = self.netuid2subnet(netuid=subnet)
        subnets = self.subnets()
        assert subnet in subnets, f"Subnet {subnet} not found in {subnets}"
        return subnet


    def subnets(self, **kwargs) -> Dict[int, str]:
        """
        Return a dictionary of subnet names based on the provided keyword arguments.
        """
        return self.subnet_names(**kwargs)
    
    def num_subnets(self, **kwargs) -> int:
        """
        Return the number of subnets based on the given keyword arguments.
        """
        return len(self.subnets(**kwargs))
    
    def netuids(self, network=network, update=False, block=None) -> Dict[int, str]:
        """
        Retrieves a list of network uids based on the given network, with options to update and specify a block. Returns a dictionary with integer keys and string values.
        """
        return list(self.netuid2subnet(network=network, update=update, block=block).keys())

    def subnet_names(self, network=network , update=False, block=None, **kwargs) -> Dict[str, str]:
        """
        Retrieve subnet names from the given network.

        Args:
            network: The network from which to retrieve subnet names.
            update: A boolean indicating whether to update the records.
            block: The block from which to retrieve subnet names.
            **kwargs: Additional keyword arguments.

        Returns:
            A dictionary mapping subnet names to their corresponding values.
        """

        records = self.query_map('SubnetNames', update=update, network=network, block=block, **kwargs)
        return list(records.values())
    
    netuid2subnet = subnet_names

    def subnet2netuid(self, subnet=None, network=network, update=False,  **kwargs ) -> Dict[str, str]:
        """
        A function that converts subnet information to network unique identifiers.

        Parameters:
            subnet (optional): A specific subnet to convert (default is None).
            network: The network information.
            update: A boolean flag indicating whether to update the network information.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict[str, str]: A dictionary mapping subnet information to network unique identifiers.
        """
        subnet2netuid =  {v:k for k,v in self.netuid2subnet(network=network, update=update, **kwargs).items()}
        
        if subnet != None:
            return subnet2netuid[subnet] if subnet in subnet2netuid else len(subnet2netuid)

        return subnet2netuid
    
    def netuid2subnet(self, netuid=None, network=network, update=False, block=None, **kwargs ) -> Dict[str, str]:
        netuid2subnet = self.query_map('SubnetNames', update=update, network=network, block=block, **kwargs)
        if netuid != None:
            return netuid2subnet[netuid]
        return netuid2subnet


    subnet_namespace = subnet2netuid

    def resolve_netuid(self, netuid: int = None, network=network, update=False) -> int:
        """
        A function to resolve the netuid based on the input netuid, network, and update flag.
        
        Parameters:
            netuid (int, optional): The netuid to resolve. Defaults to None.
            network: The network to use for resolving the netuid.
            update (bool, optional): Flag to indicate whether to update the netuid. Defaults to False.
            
        Returns:
            int: The resolved netuid.
        """
        if netuid == None or  netuid == 'all':
            # If the netuid is not specified, use the default.
            return 0

        if isinstance(netuid, str):
            # If the netuid is a subnet name, resolve it to a netuid.
            subnet_namespace = self.subnet_namespace(network=network, update=update)
            assert netuid in subnet_namespace, f"Subnet {netuid} not found in {subnet_namespace}"
            netuid = int(self.subnet_namespace(network=network).get(netuid, 0))
        elif isinstance(netuid, int):
            if netuid == 0: 
                return netuid
            # If the netuid is an integer, ensure it is valid.
            
        assert isinstance(netuid, int), "netuid must be an integer"
        return netuid
    
    resolve_net = resolve_subnet = resolve_netuid


    def key2name(self, key: str = None, netuid: int = None) -> str:
        """
        A function that maps keys to names. 

        Args:
            key (str): The key to look up the corresponding name for.
            netuid (int): The netuid value.

        Returns:
            str: The name corresponding to the input key.
        """
        modules = self.keys()
        key2name =  { m['key']: m['name']for m in modules}
        if key != None:
            return key2name[key]
        
    def name2uid(self,name = None, search:str=None, netuid: int = None, network: str = None) -> int:
        """
        Retrieves the unique identifier (UID) associated with a given name.

        Args:
            name (str, optional): The name to retrieve the UID for. Defaults to None.
            search (str, optional): A substring to search for in the names. Defaults to None.
            netuid (int, optional): The network UID to use for name retrieval. Defaults to None.
            network (str, optional): The network to use for name retrieval. Defaults to None.

        Returns:
            int: The UID associated with the given name.

        Raises:
            KeyError: If the name is not found in the name-to-UID mapping.

        """
        uid2name = self.uid2name(netuid=netuid, network=network)
        name2uid =  {v:k for k,v in uid2name.items()}
        if name != None:
            return name2uid[name]
        if search != None:
            name2uid = {k:v for k,v in name2uid.items() if search in k}
            if len(name2uid) == 1:
                return list(name2uid.values())[0]
        return name2uid

    
        
    def name2key(self, search:str=None, network=network, netuid: int = 0, update=False ) -> Dict[str, str]:
        """
        Returns a dictionary mapping names to keys for a given network and netuid.
        
        :param search: (str, optional) A string to search for in the names. Defaults to None.
        :param network: (str, optional) The network to search in. Defaults to the current network.
        :param netuid: (int, optional) The netuid to search in. Defaults to 0.
        :param update: (bool, optional) Whether to update the cache. Defaults to False.
        
        :return: (Dict[str, str]) A dictionary mapping names to keys. If search is not None, returns a single key if only one match is found.
        """
        # netuid = self.resolve_netuid(netuid)
        self.resolve_network(network)
        names = self.names(netuid=netuid, update=update)
        keys = self.keys(netuid=netuid, update=update)
        name2key = dict(zip(names, keys))
        if search != None:
            name2key = {k:v for k,v in name2key.items() if search in k}
            if len(name2key) == 1:
                return list(name2key.values())[0]
        return name2key





    def key2name(self,search=None, netuid: int = None, network=network, update=False) -> Dict[str, str]:
        """
        A function that maps values to keys using the name2key function and returns the result as a dictionary.
        
        Parameters:
            search (optional): The search term to filter the mapping.
            netuid (optional, int): The unique identifier for the network.
            network: The network to perform the mapping on.
            update (optional, bool): A flag indicating whether to update the mapping.
        
        Returns:
            Dict[str, str]: A dictionary with values as keys and keys as values.
        """
        return {v:k for k,v in self.name2key(search=search, netuid=netuid, network=network, update=update).items()}
        
    def is_unique_name(self, name: str, netuid=None):
        """
        Check if the given name is unique within the current namespace.

        Args:
            name (str): The name to check for uniqueness.
            netuid (Optional[str]): The netuid to use for the namespace. Defaults to None.

        Returns:
            bool: True if the name is unique, False otherwise.
        """
        return bool(name not in self.get_namespace(netuid=netuid))



    def name2inc(self, name: str = None, netuid: int = netuid, nonzero_only:bool=True) -> int:
        """
        This function takes in a name, netuid, and nonzero_only flag and returns the incentive associated with the given name. If name is not provided, it returns a sorted dictionary of names and their associated incentives. The parameters are:
        - name: a string representing the name (default is None)
        - netuid: an integer representing the netuid (default is the class variable netuid)
        - nonzero_only: a boolean flag indicating whether to include only nonzero incentives (default is True)
        The function returns an integer representing the incentive.
        """
        name2uid = self.name2uid(name=name, netuid=netuid)
        incentives = self.incentive(netuid=netuid)
        name2inc = { k: incentives[uid] for k,uid in name2uid.items() }

        if name != None:
            return name2inc[name]


        else:
            name2inc = dict(sorted(name2inc.items(), key=lambda x: x[1], reverse=True))
    
    
            return name2inc



    def top_valis(self, netuid: int = netuid, n:int = 10, **kwargs) -> Dict[str, str]:
        """
        A function that returns the top 'n' values from a dictionary after sorting by values.

        Parameters:
            netuid (int): The unique identifier for the network.
            n (int): The number of top values to return.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict[str, str]: A dictionary containing the top 'n' keys based on their values.
        """
        name2div = self.name2div(name=None, netuid=netuid, **kwargs)
        name2div = dict(sorted(name2div.items(), key=lambda x: x[1], reverse=True))
        return list(name2div.keys())[:n]

    def name2div(self, name: str = None, netuid: int = netuid, nonzero_only: bool = True) -> int:
        """
        Generates a dictionary mapping names to their corresponding dividends.

        Args:
            name (str, optional): The name of the dividend to retrieve. Defaults to None.
            netuid (int, optional): The unique identifier for the net. Defaults to netuid.
            nonzero_only (bool, optional): Whether to include only non-zero dividends. Defaults to True.

        Returns:
            int or dict: If `name` is provided, returns the dividend value for the given name. If `name` is not provided, returns a dictionary mapping names to their dividends.
        """
        name2uid = self.name2uid(name=name, netuid=netuid)
        dividends = self.dividends(netuid=netuid)
        name2div = { k: dividends[uid] for k,uid in name2uid.items() }
    
        if nonzero_only:
            name2div = {k:v for k,v in name2div.items() if v != 0}

        name2div = dict(sorted(name2div.items(), key=lambda x: x[1], reverse=True))
        if name != None:
            return name2div[name]
        return name2div
    
    def epoch_time(self, netuid=0, network='main', update=False, **kwargs):
        """
        Calculates the epoch time based on the subnet parameters of a specific network.

        Args:
            netuid (int, optional): The unique identifier of the subnet. Defaults to 0.
            network (str, optional): The name of the network. Defaults to 'main'.
            update (bool, optional): Whether to update the subnet parameters. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            int: The calculated epoch time based on the subnet parameters and the block time.
        """
        return self.subnet_params(netuid=netuid, network=network)['tempo']*self.block_time

    def blocks_per_day(self, netuid=None, network=None):
        """
        Calculates the number of blocks per day based on the block time.

        :param netuid: Optional parameter representing the network UID.
        :param network: Optional parameter representing the network.
        :return: Returns the number of blocks per day.
        """
        return 24*60*60/self.block_time
    

    def epochs_per_day(self, netuid=None, network=None):
        """
        Calculates the number of epochs per day based on the epoch time of the network.

        Args:
            netuid (str, optional): The unique identifier of the network. Defaults to None.
            network (str, optional): The name of the network. Defaults to None.

        Returns:
            int: The number of epochs per day.
        """
        return 24*60*60/self.epoch_time(netuid=netuid, network=network)
    
    def emission_per_epoch(self, netuid=None, network=None):
        """
        Calculate the emission per epoch for a given network and network UID.

        Args:
            netuid (str, optional): The network UID. Defaults to None.
            network (str, optional): The network name. Defaults to None.

        Returns:
            float: The emission per epoch.
        """
        return self.subnet(netuid=netuid, network=network)['emission']*self.epoch_time(netuid=netuid, network=network)


    def get_block(self, network=None, block_hash=None): 
        """
        Retrieves a block from the specified network using the given block hash.

        Args:
            network (str, optional): The network to retrieve the block from. If not specified, the default network will be used.
            block_hash (str, optional): The hash of the block to retrieve. If not specified, the latest block will be retrieved.

        Returns:
            int: The block number of the retrieved block.

        Raises:
            ValueError: If the network is not specified and no default network is set.
            ValueError: If the block hash is not specified and no latest block is available.
        """
        self.resolve_network(network)
        return self.substrate.get_block( block_hash=block_hash)['header']['number']

    def block_hash(self, block = None, network='main'): 
        """
        Retrieves the hash of a block from the specified network.

        Args:
            block (int, optional): The block number. If not provided, the default block number is used.
            network (str, optional): The network to retrieve the block hash from. Defaults to 'main'.

        Returns:
            str: The hash of the specified block.
        """
        if block == None:
            block = self.block

        substrate = self.get_substrate(network=network)
        
        return substrate.get_block_hash(block)


    def hash2block(self, network=None, block_hash=None):
        """
        A function that takes in a network and block hash, retrieves the block hash using the get_block_hash method, 
        and then returns the block using the get_block method.
        """
        block_hash = self.get_block_hash(network=network, block_hash=block_hash)
        return self.get_block(network=network, block_hash=block_hash)

    

    def seconds_per_epoch(self, netuid=None, network=None):
        """
        Calculates the number of seconds per epoch for a given network.

        :param netuid: The unique identifier of the network (default: None)
        :type netuid: int or None
        :param network: The network object (default: None)
        :type network: Network or None
        :return: The number of seconds per epoch
        :rtype: int
        """
        self.resolve_network(network)
        netuid =self.resolve_netuid(netuid)
        return self.block_time * self.subnet(netuid=netuid)['tempo']



    
    def get_module(self, module='vali',
                    netuid=0,
                    network='main',
                    fmt='j',
                    method='subspace_getModuleInfo',
                    lite = True, **kwargs ) -> 'ModuleInfo':
        """
        A method to retrieve module information from a specified network.
        
        Parameters:
            module (str): The module name or key. Defaults to 'vali'.
            netuid (int): The network UID. Defaults to 0.
            network (str): The network name. Defaults to 'main'.
            fmt (str): The format of the data. Defaults to 'j'.
            method (str): The method to retrieve module information. Defaults to 'subspace_getModuleInfo'.
            lite (bool): Flag to determine if lite features are used. Defaults to True.
            **kwargs: Additional keyword arguments.
        
        Returns:
            ModuleInfo: An object containing detailed information about the module.
        """
        url = self.resolve_url(network=network, mode='http')

        if isinstance(module, int):
            module = self.uid2key(uid=module)
        if isinstance(module, str):
            module_key = self.resolve_key_ss58(module)
        json={'id':1, 'jsonrpc':'2.0',  'method': method, 'params': [module_key, netuid]}
        module = requests.post(url,  json=json).json()
        module = {**module['result']['stats'], **module['result']['params']}
        # convert list of u8 into a string Vector<u8> to a string
        module['name'] = self.vec82str(module['name'])
        module['address'] = self.vec82str(module['address'])
        module['dividends'] = module['dividends'] / (U16_MAX)
        module['incentive'] = module['incentive'] / (U16_MAX)
        module['stake_from'] = [[k,self.format_amount(v, fmt=fmt)] for k,v in module['stake_from']]
        module['stake'] = sum([v for k,v in module['stake_from'] ])
        module['emission'] = self.format_amount(module['emission'], fmt=fmt)
        module['key'] = module.pop('controller', None)
        if lite :
            features = self.lite_module_features + ['stake']
            module = {f: module[f] for f in features}


        

        return module
    

    @staticmethod
    def vec82str(l:list):
        """
        Convert a list of integers to a string by joining the characters corresponding to the ASCII values in the list and then stripping any leading or trailing whitespace.
        """
        return ''.join([chr(x) for x in l]).strip()

    def get_modules(self, keys:list = None,
                     network='main',
                          timeout=20,
                         netuid=0, fmt='j',
                         include_uids = True,
                           **kwargs) -> List['ModuleInfo']:
        """
        A function to retrieve modules based on the provided keys, network, timeout, netuid, format, and additional keyword arguments, returning a list of ModuleInfo objects.
        """

        if keys == None:
            keys = self.my_keys()
        key2module = {}
        futures = []
        key2future = {}
        progress_bar = c.tqdm(total=len(keys), desc=f'Querying {len(keys)} keys for modules')
        c.print(len(key2module))
        future_keys = [k for k in keys if k not in key2module and k not in key2future]
        for key in future_keys:
            key2future[key] = c.submit(self.get_module, dict(module=key, netuid=netuid, network=network, fmt=fmt, **kwargs))
        future2key = {v:k for k,v in key2future.items()}
        futures = list(key2future.values())
        results = []


        if include_uids:
            name2uid = self.key2uid(netuid=netuid)

        for future in  c.as_completed(futures, timeout=timeout):
            progress_bar.update(1)
            module = future.result()
            key = future2key[future]
            if isinstance(module, dict) and 'name' in module:
                results.append(module)
            else:
                c.print(f'Error querying module for key {key}')

        if include_uids:
            for module in results:
                module['uid'] = name2uid[module['key']]

        return results
    
    def my_modules(self, **kwargs):
        """
        This function takes keyword arguments and calls the get_modules method with the result of my_keys as the keys argument.
        """
        return self.get_modules(keys=self.my_keys(), **kwargs)
        
    @property
    def null_module(self):
        """
        Returns a dictionary representing a null module.

        :return: A dictionary with keys 'name', 'key', 'uid', 'address', 'stake', 'balance', 'emission', 'incentive', 'dividends', 'stake_to', 'stake_from', and 'weight'. The values are set to None, 0, and empty dictionaries and lists respectively.
        :rtype: dict
        """
        return {'name': None, 'key': None, 'uid': None, 'address': None, 'stake': 0, 'balance': 0, 'emission': 0, 'incentive': 0, 'dividends': 0, 'stake_to': {}, 'stake_from': {}, 'weight': []}
        
        
    def name2module(self, name:str = None, netuid: int = None, **kwargs) -> 'ModuleInfo':
        """
        Return the module information for the given name or the entire mapping of module names to ModuleInfo objects.
        
        Args:
            name (str): The name of the module. Defaults to None.
            netuid (int): The network ID. Defaults to None.
            **kwargs: Additional keyword arguments for filtering the modules.
        
        Returns:
            ModuleInfo or dict: If name is provided, returns the ModuleInfo object for the given name. 
            If name is not provided, returns a mapping of module names to ModuleInfo objects.
        """
        modules = self.modules(netuid=netuid, **kwargs)
        name2module = { m['name']: m for m in modules }
        default = {}
        if name != None:
            return name2module.get(name, self.null_module)
        return name2module
        
        
        
        
        
    def key2module(self, key: str = None, netuid: int = None, default: dict =None, **kwargs) -> Dict[str, str]:
        """
        Retrieves the module information associated with a given key or netuid.

        Args:
            key (str, optional): The key to retrieve the module information for. Defaults to None.
            netuid (int, optional): The netuid to retrieve the module information for. Defaults to None.
            default (dict, optional): The default value to return if no module information is found. Defaults to None.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the module information associated with the given key or netuid.
        """
        modules = self.modules(netuid=netuid, **kwargs)
        key2module =  { m['key']: m for m in modules }
        
        if key != None:
            key_ss58 = self.resolve_key_ss58(key)
            return  key2module.get(key_ss58, default if default != None else {})
        return key2module
        
    def module2key(self, module: str = None, **kwargs) -> Dict[str, str]:
        """
        Returns a dictionary mapping module names to their corresponding keys.

        Parameters:
            module (str, optional): The name of a specific module. If provided, only the key for that module will be returned. Defaults to None.
            **kwargs: Additional keyword arguments to filter the modules.

        Returns:
            dict: A dictionary mapping module names to their corresponding keys. If `module` is not None, only the key for that module will be returned.
        """
        modules = self.modules(**kwargs)
        module2key =  { m['name']: m['key'] for m in modules }
        
        if module != None:
            return module2key[module]
        return module2key
    

    
    

    def module2stake(self,*args, **kwargs) -> Dict[str, str]:
        """
        Returns a dictionary mapping module names to their corresponding stake values.

        Parameters:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            A dictionary with module names as keys and their corresponding stake values as values.
        """
        
        module2stake =  { m['name']: m['stake'] for m in self.modules(*args, **kwargs) }
        
        return module2stake

    @classmethod
    def get_feature(cls, feature, **kwargs):
        """
        Retrieves a specific feature using the given feature name and optional keyword arguments.

        :param feature: The name of the feature to retrieve.
        :param kwargs: Optional keyword arguments to be passed to the feature method.
        :return: The result of the feature method execution.
        """
        self = cls()
        return getattr(self, feature)(**kwargs)


    def format_module(self, module: 'ModuleInfo', fmt:str='j', features=None) -> 'ModuleInfo':
        """
        Formats the given module information according to the specified format and features.

        Args:
            module (ModuleInfo): The module information to be formatted.
            fmt (str, optional): The format in which the amounts should be formatted. Defaults to 'j'.
            features (list, optional): The list of features to include in the formatted module. Defaults to None.

        Returns:
            ModuleInfo: The formatted module information.

        Raises:
            None

        Examples:
            >>> module = {'emission': 100, 'stake': 50, 'incentive': 0.5, 'dividends': 0.25, 'stake_from': {'a': 20, 'b': 30}}
            >>> format_module(module, fmt='p')
            {'emission': '100.00', 'stake': '50.00', 'incentive': '0.50', 'dividends': '0.25', 'stake_from': [['a', '20.00'], ['b', '30.00']]}

        Note:
            - If the 'stake_from' feature is included in the features list but the 'stake' feature is not, the 'stake' feature is added to the features list.
            - The 'emission', 'stake', 'incentive', and 'dividends' values in the module dictionary are formatted according to the specified format.
            - The 'stake_from' value in the module dictionary is converted to a list of lists, where each inner list contains the key-value pair of the stake amount formatted according to the specified format.
            - If the 'stake_from' value in the module dictionary is a dictionary, it is converted to a list of lists before formatting.
            - If the features list is not None, only the specified features are included in the formatted module dictionary.

        """
        if 'stake_from' in features and 'stake' not in features:
            features += ['stake']
        for k in ['emission', 'stake']:
            module[k] = self.format_amount(module[k], fmt=fmt)
        for k in ['incentive', 'dividends']:
            module[k] = module[k] / (U16_MAX)
        if isinstance(module['stake_from'], dict):
            module['stake_from'] = [[k, self.format_amount(v, fmt=fmt)]  for k, v in module['stake_from'].items()]
        module['stake_from']= [[k, self.format_amount(v, fmt=fmt)]  for k, v in module['stake_from']]
        if features != None:
            module = {f:module[f] for f in features}
        return module
    
    module_features = ['key', 
                       'address', 
                       'name', 
                       'emission', 
                       'incentive', 
                       'dividends', 
                       'last_update', 
                       'stake_from', 
                       'weights',
                       'delegation_fee',
                       'trust', 
                       'regblock']
    lite_module_features = [
                            'key', 
                            'name',
                            'address',
                            'emission',
                            'incentive', 
                            'dividends', 
                            'last_update', 
                            'stake_from', 'delegation_fee']
    feature2key = {
        'key': 'keys',
        'address': 'addresses',
        'name': 'names',
        }
    def modules(self,
                search:str= None,
                network = 'main',
                netuid: int = 0,
                block: Optional[int] = None,
                fmt='nano', 
                features : List[str] = module_features,
                timeout = 100,
                update: bool = False,
                sortby = 'emission',
                page_size = 100,
                lite: bool = True,
                page = None,
                **kwargs
                ) -> Dict[str, 'ModuleInfo']:
        """
        A function to fetch modules with various search parameters and options.
        
        Parameters:
            search (str): The search term to filter modules. Defaults to None.
            network (str): The network to fetch modules from. Defaults to 'main'.
            netuid (int): The unique identifier for the network. Defaults to 0.
            block (Optional[int]): The block number. Defaults to None.
            fmt (str): The format of the fetched modules. Defaults to 'nano'.
            features (List[str]): The list of features to fetch. Defaults to module_features.
            timeout: The timeout for fetching modules. Defaults to 100.
            update (bool): Flag to indicate if modules should be updated. Defaults to False.
            sortby (str): The parameter to sort the fetched modules by. Defaults to 'emission'.
            page_size: The number of modules per page. Defaults to 100.
            lite (bool): Flag to indicate lite version. Defaults to True.
            page: The page number for pagination. Defaults to None.
            **kwargs: Additional keyword arguments.
        
        Returns:
            Dict[str, 'ModuleInfo']: A dictionary containing information about the fetched modules.
        """
        if search == 'all':
            netuid = search
            search = None
        if isinstance(netuid, str) and netuid != 'all':
            netuid = self.subnet2netuid(netuid)
        features = self.lite_module_features if lite else features

        t1 = c.time()
        state = {}
        if update:
            block = block or self.block
            state = {}
            key2future = {}
            while len(state) < len(features):
                features_left = [f for f in features if f not in state and f not in key2future]                
                c.print( f'Fetching {features_left} ')
                for f in features_left:
                    kw = dict(feature=self.feature2key.get(f,f), 
                              network=network, 
                              netuid=netuid, 
                              block=block, 
                              update=True)
                    key2future[f] = c.submit(self.get_feature,kwargs=kw)
                future2key = {v:k for k,v in key2future.items()}
                futures = list(key2future.values())

                progress = c.tqdm(total=len(futures), desc=f'Fetching {len(futures)} features')
            
                for future in  c.as_completed(futures, timeout=timeout):
                    key = future2key[future]
                    result = future.result()
                    futures.remove(future)  
                    if not c.is_error(result):
                        progress.update(1)
                        state[key] = result
                    else:
                        c.print('Error fetching feature', key, result)
                        break

                
        if isinstance(search, int):
            netuid = search
            search = None

        if netuid == 'all':
            netuids = self.netuids(network=network)

        else:
            netuids = [netuid]
            state = {k:{netuid: v} for k,v in state.items()}
            
        all_modules = []
        return_netuid = isinstance(netuid, int)
        for netuid in netuids:
            c.print(netuid)
            path = f'modules/{network}.{netuid}'

            modules = [] if update else self.get(path, [])
            
            if len(modules) == 0:
                c.print(state.keys())
                c.print(state)
                for uid, key in enumerate(state['key'][netuid]):
                    module = { 'uid': uid, 'key': key}
                    for  f in features:
                        if f in ['name', 'address', 'emission', 'incentive', 
                                 'dividends', 'last_update', 'regblock']:
                            module[f] = state[f][netuid][uid]
                        elif f in ['trust']:
                            module[f] = state[f][netuid][uid] if len(state[f][netuid]) > uid else 0
                        elif f in ['delegation_fee']:
                            module[f] = state[f][netuid].get(key, 20)
                        elif f in ['stake_from']:
                            module[f] = state[f].get(netuid, {}).get(key, [])
                            module['stake'] =  sum([v for k,v in module['stake_from']])
                        elif f in ['weights']:
                            module[f] = state[f].get(netuid, {}).get(uid, [])
                    modules.append(module)
                self.put(path, modules)

            for i, module in enumerate(modules):
                modules[i] = self.format_module(modules[i], fmt=fmt, features=features)
            if search != None and search != 'all':
                modules = [m for m in modules if search in m['name']]
        
            all_modules.append(modules)
            

        
        # sort by emission
        if sortby != None and sortby in features:
            all_modules = [sorted(modules, key=lambda x: x[sortby] if 'sortby' != 'weights' else len(x[sortby]), reverse=True) for modules in all_modules]
    
        if return_netuid:
            modules =  all_modules[0]
            n = len(modules)
        else:
            modules = all_modules
            n = sum([len(m) for m in modules])

        c.print(f'Fetched {len(modules)} modules in {c.time() - t1} seconds')
        if page != None:
            if isinstance(modules[0], list): 
                # flatten list
                new_modules = []
                for m in modules:
                    new_modules += m
                modules = new_modules
            num_pages = n//page_size
            start_idx = page*page_size
            end_idx = start_idx + page_size
            modules = modules[start_idx:end_idx]

            c.print(f'Page {page} of {n//page_size} pages')
    
            


        return modules
    


    def min_stake(self, netuid: int = 0, network: str = 'main', fmt:str='j', **kwargs) -> int:
        """
        Calculate the minimum stake for a given `netuid` and `network`.

        :param netuid: An integer representing the netuid. Default is 0.
        :param network: A string representing the network. Default is 'main'.
        :param fmt: A string representing the format. Default is 'j'.
        :param **kwargs: Additional keyword arguments.
        :return: An integer representing the minimum stake.
        """
        min_stake = self.query('MinStake', netuid=netuid, network=network, **kwargs)
        return self.format_amount(min_stake, fmt=fmt)

    def registrations_per_block(self, network: str = network, fmt:str='j', **kwargs) -> int:
        """
        Get the number of registrations per block for the specified network.

        Args:
            network (str): The name of the network to query. Defaults to the value of the `network` parameter.
            fmt (str): The format of the response. Defaults to 'j'.
            **kwargs: Additional keyword arguments to pass to the query function.

        Returns:
            int: The number of registrations per block.
        """
        return self.query('RegistrationsPerBlock', params=[], network=network, **kwargs)
    regsperblock = registrations_per_block
    
    def max_registrations_per_block(self, network: str = network, fmt:str='j', **kwargs) -> int:
        """
        A function that calculates the maximum number of registrations per block. 

        Parameters:
            network (str): The network to query for.
            fmt (str): The format of the query (default is 'j').
            **kwargs: Additional keyword arguments to pass to the query function.

        Returns:
            int: The maximum number of registrations per block.
        """
        return self.query('MaxRegistrationsPerBlock', params=[], network=network, **kwargs)
 
    def uids(self, netuid = 0, **kwargs):
        """
        Return a list of unique identifiers for the given network UID and additional keyword arguments.
        """
        return list(self.uid2key(netuid=netuid, **kwargs).keys())
   
    def keys(self,
             netuid = 0,
              update=False, 
             network : str = 'main', 
             **kwargs) -> List[str]:
        """
        A description of the entire function, its parameters, and its return types.
        
            Parameters:
                netuid (int): The netuid parameter for the function.
                update (bool): The update parameter for the function.
                network (str): The network parameter for the function.
                **kwargs: Additional keyword arguments.
            
            Returns:
                List[str]: A list of keys.
        """
        keys =  list(self.query_map('Keys', netuid=netuid, update=update, network=network, **kwargs).values())
        return keys

    def uid2key(self, uid=None, 
             netuid = 0,
              update=False, 
             network=network, 
             return_dict = True,
             **kwargs):
        """
        Retrieves the key associated with a given unique identifier (UID).
        
        Args:
            uid (int, optional): The unique identifier of the key to retrieve. Defaults to None.
            netuid (int, optional): The network unique identifier. Defaults to 0.
            update (bool, optional): Whether to update the key mapping. Defaults to False.
            network (str, optional): The network to query. Defaults to 'network'.
            return_dict (bool, optional): Whether to return the key mapping as a dictionary. Defaults to True.
            **kwargs: Additional keyword arguments.
        
        Returns:
            dict or str: The key associated with the given UID, or the entire key mapping if UID is None.
        """
        netuid = self.resolve_netuid(netuid)
        uid2key =  self.query_map('Keys',  netuid=netuid, update=update, network=network, **kwargs)
        # sort by uid
        if uid != None:
            return uid2key[uid]
        return uid2key
    

    def key2uid(self, key = None, network:str=  'main' ,netuid: int = 0, update=False, **kwargs):
        """
        Generates a mapping from values to keys based on the given network and netuid.
        
        Parameters:
            key (optional): The key to be used for mapping. Default is None.
            network (str): The network to be used. Default is 'main'.
            netuid (int): The netuid to be used. Default is 0.
            update (bool): A flag indicating whether to update the mapping. Default is False.
            **kwargs: Additional keyword arguments.
        
        Returns:
            Either the value corresponding to the provided key, or the entire mapping if key is not provided.
        """
        key2uid =  {v:k for k,v in self.uid2key(network=network, netuid=netuid, update=update, **kwargs).items()}
        if key != None:
            key_ss58 = self.resolve_key_ss58(key)
            return key2uid[key_ss58]
        return key2uid
        

    def uid2name(self, netuid: int = 0, update=False,  **kwargs) -> List[str]:
        """
        Converts a network UID to a list of names.

        Args:
            netuid (int, optional): The network UID to be converted. Defaults to 0.
            update (bool, optional): Whether to update the query map. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            List[str]: A list of names corresponding to the network UID.
        """
        netuid = self.resolve_netuid(netuid)
        names = {k: v for k,v in enumerate(self.query_map('Name', update=update,**kwargs)[netuid])}
        names = {k: names[k] for k in sorted(names)}
        return names
    
    def names(self, 
              netuid: int = 0, 
              update=False,
                **kwargs) -> List[str]:
        """
        Function to retrieve names based on netuid, with an option to update and additional keyword arguments.

        Args:
            netuid (int): The netuid parameter (default is 0).
            update (bool): A flag to indicate whether to update the names.
            **kwargs: Additional keyword arguments.

        Returns:
            List[str]: A list of names retrieved based on the netuid.
        """
        names = self.query_map('Name', update=update, netuid=netuid,**kwargs)
        if isinstance(netuid, int):
            names = list(names.values())
        else:
            for k,v in names.items():
                names[k] = list(v.values())
        return names

    def addresses(self, netuid: int = 0, update=False, **kwargs) -> List[str]:
        """
        Retrieves a list of addresses based on the given parameters.

        Args:
            netuid (int, optional): The netuid to filter the addresses by. Defaults to 0.
            update (bool, optional): Whether to update the addresses. Defaults to False.
            **kwargs: Additional keyword arguments to pass to the query_map method.

        Returns:
            List[str]: A list of addresses.

        Note:
            - If the `netuid` parameter is an integer, the function returns a list of addresses as values of the `addresses` dictionary.
            - If the `netuid` parameter is not an integer, the function returns a dictionary where each key is a key from the `addresses` dictionary and each value is a list of values from the corresponding value in the `addresses` dictionary.
        """
        addresses = self.query_map('Address',netuid=netuid, update=update, **kwargs)
        
        if isinstance(netuid, int):
            addresses = list(addresses.values())
        else:
            for k,v in addresses.items():
                addresses[k] = list(v.values())
        return addresses

    def namespace(self, search=None, netuid: int = 0, update:bool = False, timeout=30, local=False, max_age=1000, **kwargs) -> Dict[str, str]:
        """
        A function that retrieves namespace information based on the provided parameters.

        Args:
            search (str): The search string used to filter the namespace dictionary.
            netuid (int): The netuid to be used for the namespace retrieval.
            update (bool): A flag indicating whether to update the namespace information.
            timeout (int): The timeout value for the namespace retrieval operation.
            local (bool): A flag indicating whether to filter the namespace based on local IP.
            max_age (int): The maximum age of the namespace information.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict[str, str]: A dictionary containing the namespace information.
        """
        namespace = {}  

        futures = [c.submit(self.names, kwargs=dict(netuid=netuid, update=update, max_age=max_age,**kwargs), timeout=timeout), 
            c.submit(self.addresses, kwargs=dict(netuid=netuid, update=update, max_age=max_age, **kwargs))]
        names, addresses = c.wait(futures, timeout=timeout)
        namespace = {k:v for k,v in zip(names, addresses)}

        if search != None:
            namespace = {k:v for k,v in namespace.items() if search in k}

        if local:
            ip = c.ip()
            namespace = {k:v for k,v in namespace.items() if ip in str(v)}

        return namespace

    
    def weights(self,  netuid = 0,  network = 'main', update=False, **kwargs) -> list:
        """
        Retrieve weights for a given network by querying the 'Weights' table.

        Args:
            netuid (int): The unique identifier for the network.
            network (str): The name of the network.
            update (bool): Whether to update the weights.
            **kwargs: Additional keyword arguments for the query.

        Returns:
            list: The weights retrieved from the query.
        """
        weights =  self.query_map('Weights',netuid=netuid, network = network, update=update, **kwargs)

        return weights

    def proposals(self, netuid = netuid, block=None,   network="main", nonzero:bool=False, update:bool = False,  **kwargs):
        """
        A description of the entire function, its parameters, and its return types.
        
            :param netuid: 
            :param block: 
            :param network: 
            :param nonzero: 
            :param update: 
            :param kwargs: 
            :return: 
        """
        proposals = [v for v in self.query_map('Proposals', network = 'main', block=block, update=update, **kwargs)]
        return proposals

    def save_weights(self, nonzero:bool = False, network = "main",**kwargs) -> list:
        """
        Save the weights of the model.

        Args:
            nonzero (bool, optional): Whether to save only the nonzero weights. Defaults to False.
            network (str, optional): The name of the network. Defaults to "main".
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary indicating the success of the operation and a message.
                - success (bool): True if the weights were saved successfully, False otherwise.
                - msg (str): A message indicating the status of the operation.

        """
        self.query_map('Weights',network = 'main', update=True, **kwargs)
        return {'success': True, 'msg': 'Saved weights'}

    def pending_deregistrations(self, netuid = 0, update=False, **kwargs):
        """
        Retrieves the list of pending deregistrations for a specific netuid.

        Args:
            netuid (int, optional): The netuid for which to retrieve the pending deregistrations. Defaults to 0.
            update (bool, optional): Whether to update the query map before retrieving the pending deregistrations. Defaults to False.
            **kwargs: Additional keyword arguments to be passed to the query_map function.

        Returns:
            list: The list of pending deregistrations for the specified netuid.
        """
        pending_deregistrations = self.query_map('PendingDeregisterUids',update=update,**kwargs)[netuid]
        return pending_deregistrations
    
    def num_pending_deregistrations(self, netuid = 0, **kwargs):
        """
        A function to calculate the number of pending deregistrations based on the given netuid and optional keyword arguments.
        """
        pending_deregistrations = self.pending_deregistrations(netuid=netuid, **kwargs)
        return len(pending_deregistrations)
        
    def emissions(self, netuid = 0, network = "main", block=None, update=False, **kwargs):
        """
        This function retrieves emissions data based on the specified parameters.

        :param netuid: (int) The unique identifier of the network.
        :param network: (str) The name of the network.
        :param block: (str) The block to retrieve emissions data for.
        :param update: (bool) Flag to indicate whether to update the emissions data.
        :param kwargs: Additional keyword arguments for query_vector function.
        :return: The result of the query_vector function with the specified parameters.
        """

        return self.query_vector('Emission', network=network, netuid=netuid, block=block, update=update, **kwargs)
    
    emission = emissions
    
    def incentives(self, 
                  netuid = 0, 
                  block=None,  
                  network = "main", 
                  update:bool = False, 
                  **kwargs):
        """
        Retrieves the incentives for a given netuid, block, network, and update status.

        Args:
            netuid (int, optional): The netuid to retrieve incentives for. Defaults to 0.
            block (Any, optional): The block to retrieve incentives for. Defaults to None.
            network (str, optional): The network to retrieve incentives for. Defaults to "main".
            update (bool, optional): Whether to update the incentives. Defaults to False.
            **kwargs: Additional keyword arguments to pass to the query_vector method.

        Returns:
            Any: The result of the query_vector method.
        """
        return self.query_vector('Incentive', netuid=netuid, network=network, block=block, update=update, **kwargs)
    incentive = incentives

    def trust(self, 
                  netuid = 0, 
                  block=None,  
                  network = "main", 
                  update:bool = False, 
                  **kwargs):
        """
        Executes a trust query on the specified network for the given netuid.

        Args:
            netuid (int, optional): The unique identifier for the netuid. Defaults to 0.
            block (Any, optional): The block to be used in the query. Defaults to None.
            network (str, optional): The network to be used in the query. Defaults to "main".
            update (bool, optional): Indicates whether to update the query. Defaults to False.
            **kwargs: Additional keyword arguments to be passed to the query.

        Returns:
            Any: The result of the trust query.

        """
        return self.query_vector('Trust', netuid=netuid, network=network, block=block, update=update, **kwargs)
    
    incentive = incentives
    
    def query_vector(self, name='Trust', netuid = 0, network="main", update=False, **kwargs):
        """
        A function to generate a query vector based on the provided parameters.
        
        Parameters:
            name (str): The name parameter for the query vector.
            netuid (int): The netuid parameter for the query vector.
            network (str): The network parameter for the query vector.
            update (bool): A flag indicating whether to update the query vector.
            **kwargs: Additional keyword arguments for customization.
        
        Returns:
            dict: The generated query vector based on the provided parameters.
        """
        if isinstance(netuid, int):
            query_vector = self.query(name,  netuid=netuid, network=network, update=update, **kwargs)
        else:
            query_vector = self.query_map(name, netuid=netuid, network=network, update=update, **kwargs)
            if len(query_vector) == 0:
                query_vector = {_: [] for _ in range(len(self.netuids()))}
        return query_vector
    
    def last_update(self, netuid = 0, network='main', update=False, **kwargs):
        """
        Method to retrieve the last update with optional parameters netuid, network, update, and additional keyword arguments.
        Returns the result of the query_vector method with the 'LastUpdate' command and the specified parameters.
        """
        return self.query_vector('LastUpdate', netuid=netuid,  network=network, update=update, **kwargs)

    def dividends(self, netuid = 0, network = 'main',  update=False, **kwargs):
        """
        Retrieves the dividends for a specific entity.

        Args:
            netuid (int, optional): The unique identifier of the entity. Defaults to 0.
            network (str, optional): The network on which the entity operates. Defaults to 'main'.
            update (bool, optional): Whether to update the dividends data. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            The dividends data for the specified entity.

        """
        return  self.query_vector('Dividends', netuid=netuid, network=network,  update=update,  **kwargs)
            

    dividend = dividends

    def registration_block(self, netuid: int = 0, update=False, **kwargs):
        """
        A method that retrieves registration blocks based on specified parameters.

        :param netuid: An integer representing the netuid (default 0).
        :param update: A boolean indicating whether to update the registration blocks.
        :param kwargs: Additional keyword arguments for query customization.
        :return: A list of registration blocks.
        """
        registration_blocks = self.query_map('RegistrationBlock', netuid=netuid, update=update, **kwargs)
        return registration_blocks

    regblocks = registration_blocks = registration_block

    def stake_from(self, netuid = 0,
                    block=None, 
                    update=False,
                    network=network,
                    fmt='nano', **kwargs) -> List[Dict[str, Union[str, int]]]:
        """
        Retrieve stake information for a specific network or all networks, formatted in the specified format.

        Args:
            netuid: The network ID to retrieve stake information for. Defaults to 0.
            block: The block to retrieve stake information for. Defaults to None.
            update: A boolean indicating whether to update the stake information. Defaults to False.
            network: The network to retrieve stake information for. Defaults to the network attribute of the class.
            fmt: The format in which to return the stake information. Defaults to 'nano'.
            **kwargs: Additional keyword arguments.

        Returns:
            List of dictionaries containing the formatted stake information.
        """
        
        stake_from = self.query_map('StakeFrom', netuid=netuid, block=block, update=update, network=network, **kwargs)
        format_tuples = lambda x: [[_k, self.format_amount(_v, fmt=fmt)] for _k,_v in x]
        if netuid == 'all':
            stake_from = {netuid: {k: format_tuples(v) for k,v in stake_from[netuid].items()} for netuid in stake_from}
        else:
            stake_from = {k: format_tuples(v) for k,v in stake_from.items()}
    
        return stake_from
        return stake_from
    

    def get_archive_blockchain_archives(self, netuid=netuid, network:str=network, **kwargs) -> List[str]:
        """
        A function to retrieve blockchain archives based on network and datetime,
        and break them into blocks. Returns a list of dictionaries containing 
        blockchain id, archive path, and block number.
        Parameters:
            netuid: The unique identifier of the network (default: netuid)
            network: The network to retrieve archives from
            **kwargs: Additional keyword arguments
        Returns:
            List[str]: A list of dictionaries containing blockchain id, archive path, and block number
        """

        datetime2archive =  self.datetime2archive(network=network, **kwargs) 
        break_points = []
        last_block = 10e9
        blockchain_id = 0
        get_archive_blockchain_ids = []
        for dt, archive_path in enumerate(datetime2archive):
            
            archive_block = int(archive_path.split('block-')[-1].split('-')[0])
            if archive_block < last_block :
                break_points += [archive_block]
                blockchain_id += 1
            last_block = archive_block
            get_archive_blockchain_ids += [{'blockchain_id': blockchain_id, 'archive_path': archive_path, 'block': archive_block}]

            c.print(archive_block, archive_path)

        return get_archive_blockchain_ids


    def get_archive_blockchain_info(self, netuid=netuid, network:str=network, **kwargs) -> List[str]:
        """
        Retrieves the blockchain information for the given network and netuid.

        Args:
            netuid (str): The netuid associated with the network.
            network (str): The name of the network.
            **kwargs: Additional keyword arguments.

        Returns:
            List[str]: A list of blockchain information.
        """

        datetime2archive =  self.datetime2archive(network=network, **kwargs) 
        break_points = []
        last_block = 10e9
        blockchain_id = 0
        get_archive_blockchain_info = []
        for i, (dt, archive_path) in enumerate(datetime2archive.items()):
            c.print(archive_path)
            archive_block = int(archive_path.split('block-')[-1].split('-time')[0])
            
            c.print(archive_block < last_block, archive_block, last_block)
            if archive_block < last_block :
                break_points += [archive_block]
                blockchain_id += 1
                blockchain_info = {'blockchain_id': blockchain_id, 'archive_path': archive_path, 'block': archive_block, 'earliest_block': archive_block}
                get_archive_blockchain_info.append(blockchain_info)
                c.print(archive_block, archive_path)
            last_block = archive_block
            if len(break_points) == 0:
                continue


        return get_archive_blockchain_info


    @classmethod
    def most_recent_archives(cls,):
        """
        Returns the most recent archives.

        This class method searches for archives using the `search_archives` method and returns the result.

        Returns:
            list: A list of the most recent archives.
        """
        archives = cls.search_archives()
        return archives
    
    @classmethod
    def num_archives(cls, *args, **kwargs):
        return len(cls.datetime2archive(*args, **kwargs))

        """
        Return the number of archives created using the given arguments.
        """
    def keep_archives(self, loockback_hours=24, end_time='now'):
        all_archive_paths = self.ls_archives()
        kept_archives = self.search_archives(lookback_hours=loockback_hours, end_time=end_time)
        kept_archive_paths = [a['path'] for a in kept_archives]
        rm_archive_paths = [a for a in all_archive_paths if a not in kept_archive_paths]
        for archive_path in rm_archive_paths:
            c.print('Removing', archive_path)
            c.rm(archive_path)
        return kept_archive_paths

    @classmethod
    def search_archives(cls, 
                    lookback_hours : int = 24,
                    end_time :str = 'now', 
                    start_time: Optional[Union[int, str]] = None, 
                    netuid=0, 
                    n = 1000,
                    **kwargs):
        """
        Search archives within a given time frame and return the relevant data.
        
        Args:
            lookback_hours (int): Number of hours to look back for archives (default is 24).
            end_time (str): End time for the search (default is 'now').
            start_time (Union[int, str], optional): Start time for the search. If not provided, it is calculated based on the lookback hours and end time.
            netuid: Network UID for the search.
            n: Number of archives to return.
            **kwargs: Additional keyword arguments.
        
        Returns:
            list: List of dictionaries containing archive data.
        """


        if end_time == 'now':
            end_time = c.time()
        elif isinstance(end_time, str):
            c.print(end_time)
            
            end_time = c.datetime2time(end_time)
        elif isinstance(end_time, int):
            pass
        else:
            raise Exception(f'Invalid end_time {end_time}')
            end_time = c.time2datetime(end_time)



        if start_time == None:
            start_time = end_time - lookback_hours*3600
            start_time = c.time2datetime(start_time)

        if isinstance(start_time, int) or isinstance(start_time, float):
            start_time = c.time2datetime(start_time)
        
        if isinstance(end_time, int) or isinstance(end_time, float):
            end_time = c.time2datetime(end_time)
        

        assert end_time > start_time, f'end_time {end_time} must be greater than start_time {start_time}'
        datetime2archive = cls.datetime2archive()
        datetime2archive= {k: v for k,v in datetime2archive.items() if k >= start_time and k <= end_time}
        c.print(len(datetime2archive))
        factor = len(datetime2archive)//n
        if factor == 0:
            factor = 1
        archives = []

        c.print('Searching archives from', start_time, 'to', end_time)

        cnt = 0
        for i, (archive_dt, archive_path) in enumerate(datetime2archive.items()):
            if i % factor != 0:
                continue
            archive_block = int(archive_path.split('block-')[-1].split('-time')[0])
            archive = c.get(archive_path)
            total_balances = sum([b for b in archive['balances'].values()])

            total_stake = sum([sum([_[1]for _ in m['stake_from']]) for m in archive['modules'][netuid]])
            subnet = archive['subnets'][netuid]
            row = {
                    'block': archive_block,  
                    'total_stake': total_stake*1e-9,
                    'total_balance': total_balances*1e-9, 
                    'market_cap': (total_stake+total_balances)*1e-9 , 
                    'dt': archive_dt, 
                    'block': archive['block'], 
                    'path': archive_path, 
                    'mcap_per_block': 0,
                }
            
            if len(archives) > 0:
                denominator = ((row['block']//subnet['tempo']) - (archives[-1]['block']//subnet['tempo']))*subnet['tempo']
                if denominator > 0:
                    row['mcap_per_block'] = (row['market_cap'] - archives[-1]['market_cap'])/denominator

            archives += [row]
            
        return archives

    @classmethod
    def archive_history(cls, 
                     *args, 
                     network=network, 
                     netuid= 0 , 
                     update=True,  
                     **kwargs):
        """
        A class method to archive history.

        Args:
            *args: Variable length argument list.
            network: The network to archive history for.
            netuid: The network unique identifier.
            update: Whether to update the archive.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            The archived history.
        """
        
        path = f'history/{network}.{netuid}.json'

        archive_history = []
        if not update:
            archive_history = cls.get(path, [])
        if len(archive_history) == 0:
            archive_history =  cls.search_archives(*args,network=network, netuid=netuid, **kwargs)
            cls.put(path, archive_history)
            
        return archive_history
        
    def key_usage_path(self, key:str):
        """
        Generate a path based on the provided key by resolving its ss58 and appending it to 'key_usage/'.
        
        Parameters:
        key (str): The key to generate the path for.
        
        Returns:
        str: The generated path based on the key.
        """
        key_ss58 = self.resolve_key_ss58(key)
        return f'key_usage/{key_ss58}'

    def key_used(self, key:str):
        """ 
        shows the current keys being used
        """
        return self.exists(self.key_usage_path(key))

    def use_key(self, key:str):
        """
        Uses the specified key by putting the current time to the key usage path.

        Parameters:
            key (str): The key to be used.

        Returns:
            None
        """
        return self.put(self.key_usage_path(key), c.time())
    
    def unuse_key(self, key:str):
        """
        Remove the specified key from key usage and return the result.
        
        Parameters:
            key (str): The key to be removed from key usage.
            
        Returns:
            The result of removing the specified key from key usage.
        """
        return self.rm(self.key_usage_path(key))
    
    def test_key_usage(self):
        """
        Test the key usage functionality.

        This function performs a series of tests to ensure that the key usage functionality is working correctly. It does the following steps:
        1. Adds a test key to the key path 'test_key_usage'.
        2. Uses the test key.
        3. Asserts that the test key is marked as used.
        4. Unuses the test key.
        5. Asserts that the test key is marked as not used.
        6. Removes the test key from the key path.
        7. Asserts that the test key does not exist.
        
        Returns:
            dict: A dictionary containing the test result. The dictionary has two keys:
                - 'success' (bool): True if all the tests pass, False otherwise.
                - 'msg' (str): A message indicating the test result for the specific key path.
        """
        key_path = 'test_key_usage'
        c.add_key(key_path)
        self.use_key(key_path)
        assert self.key_used(key_path)
        self.unuse_key(key_path)
        assert not self.key_used(key_path)
        c.rm_key('test_key_usage')
        assert not c.key_exists(key_path)
        return {'success': True, 'msg': f'Tested key usage for {key_path}'}
        

    def get_nonce(self, key:str=None, network=None, **kwargs):
        """
        Get the nonce for a given key and network.

        Args:
            key (str, optional): The key to use for getting the nonce. Defaults to None.
            network (str, optional): The network to use for getting the nonce. Defaults to None.
            **kwargs: Additional keyword arguments.

        Returns:
            The nonce for the given key and network.
        """
        key_ss58 = self.resolve_key_ss58(key)
        self.resolve_network(network)   
        return self.substrate.get_account_nonce(key_ss58)

    history_path = f'history'

    chain_path = c.libpath + '/subspace'
    spec_path = f"{chain_path}/specs"
    snapshot_path = f"{chain_path}/snapshots"
    @classmethod
    def convert_snapshot(cls, from_version=3, to_version=2, network=network):
        
        
        if from_version == 1 and to_version == 2:
            factor = 1_000 / 42 # convert to new supply
            path = f'{cls.snapshot_path}/{network}.json'
            snapshot = c.get_json(path)
            snapshot['balances'] = {k: int(v*factor) for k,v in snapshot['balances'].items()}
            for netuid in range(len(snapshot['subnets'])):
                for j, (key, stake_to_list) in enumerate(snapshot['stake_to'][netuid]):
                    c.print(stake_to_list)
                    for k in range(len(stake_to_list)):
                        snapshot['stake_to'][netuid][j][1][k][1] = int(stake_to_list[k][1]*factor)
            snapshot['version'] = to_version
            c.put_json(path, snapshot)
            return {'success': True, 'msg': f'Converted snapshot from {from_version} to {to_version}'}

        elif from_version == 3 and to_version == 2:
            path = cls.latest_archive_path()
            state = c.get(path)
            subnet_params : List[str] =  ['name', 'tempo', 'immunity_period', 'min_allowed_weights', 'max_allowed_weights', 'max_allowed_uids', 'trust_ratio', 'min_stake', 'founder']
            module_params : List[str] = ['Keys', 'Name', 'Address']

            modules = []
            subnets = []
            for netuid in range(len(state['subnets'])):
                keys = state['Keys'][netuid]
                for i in range(len(keys)):
                    module = [state[p][netuid][i] for p in module_params]
                    modules += [module]
                c.print(state['subnets'][netuid])
                subnet = [state['subnets'][netuid][p] for p in subnet_params]
                subnets += [subnet]


            snapshot = {
                'balances': state['balances'],
                'modules': modules,
                'version': 2,
                'subnets' : subnets,
                'stake_to': state['StakeTo'],
            }

            path = f'{cls.snapshot_path}/{network}-new.json'
            c.put_json(path, snapshot)
            total_balance = sum(snapshot['balances'].values())
            c.print(f'Total balance: {total_balance}')


            total_stake_to = sum([sum([sum([_v[1] for _v in v]) for k,v in l.items()]) for l in snapshot['stake_to']])
            c.print(f'Total stake_to: {total_stake_to}')
            total_tokens = total_balance + total_stake_to
            c.print(f'Total tokens: {total_tokens}')
            return {'success': True, 'msg': f'Converted snapshot from {from_version} to {to_version}', 'path': path}

        else:
            raise Exception(f'Invalid conversion from {from_version} to {to_version}')

    @classmethod
    def check(cls, netuid=0):
        """
        Check function for validating various aspects of the input data.
        """
        self = cls()

        # c.print(len(self.modules()))
        c.print(len(self.query_map('Keys', netuid)), 'keys')
        c.print(len(self.query_map('Name', netuid)), 'names')
        c.print(len(self.query_map('Address', netuid)), 'address')
        c.print(len(self.incentive()), 'incentive')
        c.print(len(self.uids()), 'uids')
        c.print(len(self.stakes()), 'stake')
        c.print(len(self.query_map('Emission')[0][1]), 'emission')
        c.print(len(self.query_map('Weights', netuid)), 'weights')



    def stats(self, 
              search = None,
              netuid=0,  
              network = network,
              df:bool=True, 
              update:bool = False , 
              local: bool = True,
              cols : list = ['name', 'emission','incentive', 'dividends', 'stake', 'last_update', 'serving'],
              sort_cols = ['name', 'serving',  'emission', 'stake'],
              fmt : str = 'j',
              include_total : bool = True,
              **kwargs
              ):
        """
        A method to calculate statistics based on the given parameters and return the result as a dataframe.
        
        Args:
            search (str): A string to search within the dataframe.
            netuid (int): The unique identifier for the network.
            network: The network to be used for calculations.
            df (bool): A flag to indicate whether to return the result as a dataframe or not.
            update (bool): A flag to indicate whether to update the statistics or not.
            local (bool): A flag to indicate whether to use local statistics or not.
            cols (list): A list of columns to include in the result dataframe.
            sort_cols: A list of columns to use for sorting the dataframe.
            fmt (str): The format of the result.
            include_total (bool): A flag to indicate whether to include the total in the result or not.
            **kwargs: Additional keyword arguments.
            
        Returns:
            DataFrame or list: The calculated statistics as a dataframe or a list of records.
        """

        modules = self.my_modules(netuid=netuid, update=update, network=network, fmt=fmt, **kwargs)
        stats = []

        local_key_addresses = list(c.key2address().values())
        servers = c.servers(network='local')
        for i, m in enumerate(modules):
            if m['key'] not in local_key_addresses :
                continue
            # sum the stake_from
            # we want to round these values to make them look nice
            for k in ['emission', 'dividends', 'incentive']:
                m[k] = c.round(m[k], sig=4)

            m['serving'] = bool(m['name'] in servers)
            stats.append(m)
        df_stats =  c.df(stats)
        if len(stats) > 0:
            df_stats = df_stats[cols]
            if 'last_update' in cols:
                df_stats['last_update'] = df_stats['last_update'].apply(lambda x: x)
            if 'emission' in cols:
                epochs_per_day = self.epochs_per_day(netuid=netuid, network=network)
                df_stats['emission'] = df_stats['emission'] * epochs_per_day
            sort_cols = [c for c in sort_cols if c in df_stats.columns]  
            df_stats.sort_values(by=sort_cols, ascending=False, inplace=True)
            if search is not None:
                df_stats = df_stats[df_stats['name'].str.contains(search, case=True)]

        if not df:
            return df_stats.to_dict('records')
        else:
            return df_stats


    @classmethod
    def status(cls):
        """
        Returns the status of the current working directory.

        :return: The status of the current working directory.
        :rtype: str
        """
        return c.status(cwd=cls.libpath)


    def storage_functions(self, network=network, block_hash = None):
        """
        This function takes in a network and optional block_hash parameter and resolves the network. 
        It then returns the metadata storage functions using the provided block_hash.
        """
        self.resolve_network(network)
        return self.substrate.get_metadata_storage_functions( block_hash=block_hash)
    storage_fns = storage_functions
        

    def storage_names(self,  search=None, network=network, block_hash = None):
        """
        Returns a list of storage names for a given substrate network. 

        :param search: (Optional) A string to search for in the storage names. Default is None.
        :type search: str
        :param network: (Optional) The substrate network to use. Default is the network specified in the class.
        :type network: str
        :param block_hash: (Optional) The block hash to use. Default is None.
        :type block_hash: str
        :return: A list of storage names.
        :rtype: list
        """
        self.resolve_network(network)
        storage_names =  [f['storage_name'] for f in self.substrate.get_metadata_storage_functions( block_hash=block_hash)]
        if search != None:
            storage_names = [s for s in storage_names if search in s.lower()]
        return storage_names

    def state_dict(self , 
                   timeout=1000, 
                   network='main', 
                   netuid = 'all',
                   update=False, 
                   mode='http', 
                   save = False,
                   block=None):
        """
        A function to get the state dictionary with various features and parameters, and optionally save it to a specified path.
        
        :param timeout: int, the timeout for network requests
        :param network: str, the network to use
        :param netuid: str, the unique identifier for the network
        :param update: bool, whether to update the state dictionary
        :param mode: str, the mode of the network requests
        :param save: bool, whether to save the state dictionary
        :param block: int, the block number
        
        :return: dict, the response object containing the success status, message, latency, and block information
        """
        
        
        start_time = c.time()
        self.resolve_network(network)

        if save:
            update = True
        if not update:
            state_path = self.latest_archive_path() # get the latest archive path
            state_dict = c.get(state_path, None)
            if state_path != None:
                return state_dict

        block = block or self.block

        path = f'state_dict/{network}.block-{block}-time-{int(c.time())}'

        
        def get_feature(feature, **kwargs):
            self = Subspace(mode=mode)
            return getattr(self, feature)(**kwargs)

        feature2params = {}

        feature2params['balances'] = [get_feature, dict(feature='balances', update=update, block=block, timeout=timeout)]
        feature2params['subnets'] = [get_feature, dict(feature='subnet_params', update=update, block=block, netuid=netuid, timeout=timeout)]
        feature2params['global'] = [get_feature, dict(feature='global_params', update=update, block=block, timeout=timeout)]
        feature2params['modules'] = [get_feature, dict(feature='modules', update=update, block=block, timeout=timeout)]
    
        feature2result = {}
        state_dict = {'block': block,'block_hash': self.block_hash(block)}
        while len(feature2params) > 0:
            
            for feature, (fn, kwargs) in feature2params.items():
                if feature in feature2result:
                    continue
                feature2result[feature] = c.submit(fn, kwargs) 
            result2feature = {v:k for k,v in feature2result.items()}
            futures = list(feature2result.values())
            for future in c.as_completed(futures, timeout=timeout):
                feature = result2feature[future]
                result = future.result()
                if c.is_error(result):
                    c.print('ERROR IN FEATURE', feature, result)
                    continue
                state_dict[feature] = result

                feature2params.pop(feature, None)
                result2feature.pop(future, None)

                # verbose 
                msg = {
                    'features_left': list(feature2params.keys()),

                }
                c.print(msg)
            
            feature2result = {}

        if save:
            self.put(path, state_dict)
            end_time = c.time()
            latency = end_time - start_time
            response = {"success": True,
                        "msg": f'Saving state_dict to {path}', 
                        'latency': latency, 
                        'block': state_dict['block']}

        
        return response  # put it in storage
    

    def sync(self,*args, **kwargs):
        """
        Perform a synchronous operation with the given arguments and keyword arguments. 
        Returns the state dictionary with the specified arguments saved and updated.
        """
        return  self.state_dict(*args, save=True, update=True, **kwargs)

    @classmethod
    def test(cls):
        """
        This is a class method that tests the functionality of the Subspace class.
        It creates an instance of the Subspace class and performs the following tests:
        
        - Tests if the number of subspaces is greater than 0.
        - Tests if the market capitalization is a float.
        - Tests if the name-to-key dictionary has the same length as the number of subspaces.
        - Prints the statistics of the subspaces.
        
        This method does not take any parameters and does not return any values.
        """
        s = c.module('subspace')()
        n = s.n()
        assert isinstance(n, int)
        assert n > 0

        market_cap = s.mcap()
        assert isinstance(market_cap, float), market_cap

        name2key = s.name2key()
        assert isinstance(name2key, dict)
        assert len(name2key) == n

        stats = s.stats(df=False)
        c.print(stats)
        assert isinstance(stats, list) 

    def check_storage(self, block_hash = None, network=network):
        """
        Retrieves the metadata storage functions for a given block hash.

        Args:
            block_hash (str, optional): The hash of the block to retrieve metadata for. If not provided, the latest block will be used. Defaults to None.
            network (str, optional): The network to use for retrieving the metadata. Defaults to the default network set in the class.

        Returns:
            dict: A dictionary containing the metadata storage functions for the specified block hash.

        Raises:
            None

        Examples:
            >>> my_object = MyClass()
            >>> metadata = my_object.check_storage(block_hash='0x1234567890abcdef', network='mainnet')

        """
        self.resolve_network(network)
        return self.substrate.get_metadata_storage_functions( block_hash=block_hash)

    @classmethod
    def sand(cls): 
        """
        A class method that performs the sand operation.

        Returns:
            None
        """
        node_keys =  cls.node_keys()
        spec = cls.spec()
        addy = c.root_key().ss58_address

        for i, (k, v) in enumerate(cls.datetime2archive('2023-10-17').items()):
            if i % 10 != 0:
                c.print(i, '/', len(v))
                continue
            state = c.get(v)
            c.print(state.keys())
            c.print(k, state['balances'].get(addy, 0))
        



    def test_balance(self, network:str = network, n:int = 10, timeout:int = 10, verbose:bool = False, min_amount = 10, key=None):
        """
        Test the balance of a given network by performing a series of transfers.

        Args:
            network (str, optional): The network to test the balance on. Defaults to the value of the 'network' variable.
            n (int, optional): The number of transfers to perform. Defaults to 10.
            timeout (int, optional): The timeout for each transfer in seconds. Defaults to 10.
            verbose (bool, optional): Whether to print verbose output. Defaults to False.
            min_amount (int, optional): The minimum amount for each transfer. Defaults to 10.
            key (Any, optional): The key to use for authentication. Defaults to None.

        Raises:
            AssertionError: If the balance is less than or equal to 0.

        Returns:
            None
        """
        key = c.get_key(key)

        balance = self.get_balance(network=network)
        assert balance > 0, f'balance must be greater than 0, not {balance}'
        balance = int(balance * 0.5)
        c.print(f'testing network {network} with {n} transfers of {balance} each')


    def test_commands(self, network:str = network, n:int = 10, timeout:int = 10, verbose:bool = False, min_amount = 10, key=None):
        """
        This function tests commands with the given network, number of transfers, timeout, verbosity, minimum amount, and key.
        :param network: a string representing the network
        :param n: an integer representing the number of transfers
        :param timeout: an integer representing the timeout value
        :param verbose: a boolean representing the verbosity
        :param min_amount: the minimum amount
        :param key: the key for the transaction
        """
        key = c.get_key(key)

        key2 = c.get_key('test2')
        
        balance = self.get_balance(network=network)
        assert balance > 0, f'balance must be greater than 0, not {balance}'
        c.transfer(dest=key, amount=balance, timeout=timeout, verbose=verbose)
        balance = int(balance * 0.5)
        c.print(f'testing network {network} with {n} transfers of {balance} each')


    @classmethod
    def fix(cls):
        """
        Fixes the issue by finding three free ports and adding them to the list of ports to avoid.

        Returns:
            None
        """
        avoid_ports = []
        free_ports = c.free_ports(n=3, avoid_ports=avoid_ports)
        avoid_ports += free_ports

    def num_holders(self, **kwargs):
        """
        This function calculates the number of holders and returns the count.
        """
        balances = self.balances(**kwargs)
        return len(balances)

    def total_balance(self, **kwargs):
        """
        Calculates the total balance of the object based on the balances returned by the `balances` method.

        Args:
            **kwargs: Keyword arguments that will be passed to the `balances` method.

        Returns:
            float: The total balance of the object.

        """
        balances = self.balances(**kwargs)
        return sum(balances.values())
    

    def sand(self, **kwargs):
        """
        Calculate the total sum of balances from the `my_balances` method.
        """
        balances = self.my_balances(**kwargs)
        return sum(balances.values())
    
    """
    
    WALLET VIBES
    
    """
    
    
    """
    #########################################
                    CHAIN LAND
    #########################################
    
    """

    def chain(self, *args, **kwargs):
        """
        A function that chains together the specified functions from the subspace.chain module.
        
        Parameters:
            *args: Variable length arguments to pass to the chained functions.
            **kwargs: Keyword arguments to pass to the chained functions.
        
        Returns:
            The result of chaining the specified functions.
        """
        return c.module('subspace.chain')(*args, **kwargs)
    
    def chain_config(self, *args, **kwargs):
        """
        This function chains the configuration and returns the configuration object.
        """
        return self.chain(*args, **kwargs).config
    
    def chains(self, *args, **kwargs):
        """
        A function that takes in any number of positional and keyword arguments and returns the result of calling the `chain` method with those arguments on the current instance of the class, followed by calling the `chains` method on the result.

        Parameters:
            *args: Any number of positional arguments.
            **kwargs: Any number of keyword arguments.

        Returns:
            The result of calling the `chains` method on the result of calling the `chain` method with the given arguments.
        """
        return self.chain(*args, **kwargs).chains()

    """
    #########################################
                    CHAIN LAND
    #########################################
    
    """
    ##################
    #### Register ####
    ##################
    def min_register_stake(self, netuid: int = 0, network: str = network, fmt='j', **kwargs) -> float:
        """
        Calculate the minimum stake required for registration.

        :param netuid: An integer representing the network UID (default is 0).
        :param network: A string representing the network (default is the value of network).
        :param fmt: A string specifying the format (default is 'j').
        :param **kwargs: Additional keyword arguments.
        :return: A float representing the total minimum stake required for registration.
        """
        min_burn = self.min_burn( network=network, fmt=fmt)
        min_stake = self.min_stake(netuid=netuid, network=network, fmt=fmt)
        return min_stake + min_burn
    def register(
        self,
        name: str , # defaults to module.tage
        address : str = 'NA',
        stake : float = 0,
        subnet: str = 'commune',
        key : str  = None,
        module_key : str = None,
        network: str = network,
        wait_for_inclusion: bool = True,
        wait_for_finalization: bool = True,
        nonce=None,
        fmt = 'nano',
    **kwargs
    ) -> bool:
        """
        A method to register a user with the given name, address, stake amount, subnet, key, module key, network, and other optional parameters. 
        It resolves the network and key, validates the address, calculates the stake if not provided, converts the stake to nanos, creates parameters dictionary, prints the parameters, composes a call to register, and returns the response.
        Parameters:
            name: str - the name of the user (defaults to module.tage)
            address: str - the address of the user (default is 'NA')
            stake: float - the stake amount (default is 0)
            subnet: str - the subnet for the user (default is 'commune')
            key: str - the key for the user
            module_key: str - the module key for the user
            network: str - the network for the user
            wait_for_inclusion: bool - flag to wait for inclusion (default is True)
            wait_for_finalization: bool - flag to wait for finalization (default is True)
            nonce: None - the nonce value
            fmt: str - the format (default is 'nano')
            kwargs: dict - additional keyword arguments
        Returns:
            bool - True if registration is successful, False otherwise
        """
        network =self.resolve_network(network)
        key = self.resolve_key(key)
        address = address or c.namespace(network='local').get(name, '0.0.0.0:8888')
        module_key = module_key or c.get_key(name).ss58_address

        # Validate address.
        if stake == None :
            netuid = self.subnet2netuid(subnet)
            min_stake = self.min_register_stake(netuid=netuid, network=network)
            stake = min_stake + 1
            

        stake = self.to_nanos(stake)

        params = { 
                    'network': subnet.encode('utf-8'),
                    'address': address.encode('utf-8'),
                    'name': name.encode('utf-8'),
                    'stake': stake,
                    'module_key': module_key,
                }
        
        c.print(params)
        # create extrinsic call
        response = self.compose_call('register', params=params, key=key, wait_for_inclusion=wait_for_inclusion, wait_for_finalization=wait_for_finalization, nonce=nonce)
        return response

    reg = register

    ##################
    #### Transfer ####
    ##################
    def transfer(
        self,
        dest: str, 
        amount: float , 
        key: str = None,
        network : str = None,
        nonce= None,
        **kwargs
        
    ) -> bool:
        """
        Transfers a specified amount of tokens to a given destination address.

        Args:
            dest (str): The destination address to transfer the tokens to.
            amount (float): The amount of tokens to transfer.
            key (str, optional): The private key to use for the transaction. Defaults to None.
            network (str, optional): The network to use for the transaction. Defaults to None.
            nonce (int, optional): The nonce value for the transaction. Defaults to None.
            **kwargs: Additional keyword arguments to be passed to the `compose_call` method.

        Returns:
            bool: True if the transfer is successful, False otherwise.

        Note:
            - If the `dest` argument is a float, it is assumed to be the amount and the `amount` argument is converted to a string.
            - The `key` argument is resolved using the `resolve_key` method.
            - The `network` argument is resolved using the `resolve_network` method.
            - The `dest` argument is resolved using the `resolve_key_ss58` method.
            - The `amount` argument is converted to nano units using the `to_nanos` method.
            - The transaction is composed using the `compose_call` method.
        """
        # this is a bit of a hack to allow for the amount to be a string for c send 500 0x1234 instead of c send 0x1234 500
        if type(dest) in [int, float]:
            assert isinstance(amount, str), f"Amount must be a string"
            new_amount = int(dest)
            dest = amount
            amount = new_amount
        key = self.resolve_key(key)
        network = self.resolve_network(network)
        dest = self.resolve_key_ss58(dest)
        amount = self.to_nanos(amount) # convert to nano (10^9 nanos = 1 token)

        response = self.compose_call(
            module='Balances',
            fn='transfer',
            params={
                'dest': dest, 
                'value': amount
            },
            key=key,
            nonce = nonce,
            **kwargs
        )
        
        return response


    send = transfer

    ##################
    #### Transfer ####
    ##################
    def add_profit_shares(
        self,
        keys: List[str], 
        shares: List[float] = None , 
        key: str = None,
        network : str = None,
    ) -> bool:
        """
        Adds profit shares for the provided keys and their corresponding shares. 
        Resolves the key and network if provided, and performs input validations. 
        Composes a call to the 'SubspaceModule' with the provided keys and shares, and returns the response. 

        Parameters:
            keys (List[str]): The list of keys for which profit shares are being added.
            shares (List[float], optional): The list of shares corresponding to the keys. Defaults to None.
            key (str, optional): The key to be resolved. Defaults to None.
            network (str, optional): The network to be resolved. Defaults to None.

        Returns:
            bool: True if the profit shares are added successfully.
        """
        
        key = self.resolve_key(key)
        network = self.resolve_network(network)
        assert len(keys) > 0, f"Must provide at least one key"
        assert all([c.valid_ss58_address(k) for k in keys]), f"All keys must be valid ss58 addresses"
        shares = shares or [1 for _ in keys]

        assert len(keys) == len(shares), f"Length of keys {len(keys)} must be equal to length of shares {len(shares)}"

        response = self.compose_call(
            module='SubspaceModule',
            fn='add_profit_shares',
            params={
                'keys': keys, 
                'shares': shares
            },
            key=key
        )

        return response


    def switch_module(self, module:str, new_module:str, n=10, timeout=20):
        """
        Switches the module of the specified number of servers to a new module.

        Args:
            module (str): The name of the module to switch.
            new_module (str): The name of the new module to switch to.
            n (int, optional): The number of servers to switch. Defaults to 10.
            timeout (int, optional): The timeout value in seconds. Defaults to 20.

        Returns:
            list: A list of results from the module update operation.
        """
        stats = c.stats(module, df=False)
        namespace = c.namespace(new_module, public=True)
        servers = list(namespace.keys())[:n]
        stats = stats[:len(servers)]

        kwargs_list = []

        for m in stats:
            if module in m['name']:
                if len(servers)> 0: 
                    server = servers.pop()
                    server_address = namespace.get(server)
                    kwargs_list += [{'module': m['name'], 'name': server, 'address': server_address}]

        results = c.wait([c.submit(c.update_module, kwargs=kwargs, timeout=timeout, return_future=True) for kwargs in kwargs_list])
        
        return results
                



    def update_module(
        self,
        module: str, # the module you want to change
        # params from here
        name: str = None,
        address: str = None,
        delegation_fee: float = None,
        netuid: int = None,
        network : str = network,
        nonce = None,
        tip: int = 0,


    ) -> bool:
        """
        A description of the entire function, its parameters, and its return types.
        
        :param module: the module you want to change
        :param name: 
        :param address: 
        :param delegation_fee: 
        :param netuid: 
        :param network: 
        :param nonce: 
        :param tip: 
        
        :return: bool
        """
        self.resolve_network(network)
        key = self.resolve_key(module)
        netuid = self.resolve_netuid(netuid)  
        module_info = self.get_module(module)

        if module_info['key'] == None:
            return {'success': False, 'msg': 'not registered'}
        
        if name == None:
            name = module_info['name']
        if address == None:
            address = module_info['address'][:32]
        # Validate that the module is already registered with the same address
        # ENSURE DELEGATE FEE IS BETWEEN 0 AND 100
        if delegation_fee == None:
            delegation_fee = module_info['delegation_fee']
        assert delegation_fee >= 0 and delegation_fee <= 100, f"Delegate fee must be between 0 and 100"


        params = {
            'netuid': netuid, # defaults to module.netuid
             # PARAMS #
            'name': name, # defaults to module.tage
            'address': address, # defaults to module.tage
            'delegation_fee': delegation_fee, # defaults to module.delegate_fee
        }

        reponse  = self.compose_call('update_module',params=params, key=key, nonce=nonce, tip=tip)

        return reponse



    #################
    #### UPDATE SUBNET ####
    #################
    def update_subnet(
        self,
        netuid: int = None,
        key: str = None,
        network = network,
        nonce = None,
        update= True,
        **params,
    ) -> bool:
        """
        Update a subnet with the given parameters and return a boolean indicating success.
        
        Args:
            netuid (int): The unique identifier of the subnet.
            key (str): The key for the subnet.
            network: The network for the subnet.
            nonce: The nonce for the subnet.
            update (bool): Boolean indicating whether to update the subnet.
            **params: Additional parameters for the subnet.
        
        Returns:
            bool: A boolean value indicating the success of the update.
        """
            
        self.resolve_network(network)
        netuid = self.resolve_netuid(netuid)
        subnet_params = self.subnet_params( netuid=netuid , update=update, network=network, fmt='nanos')
        # infer the key if you have it
        if key == None:
            key2address = self.address2key()
            if subnet_params['founder'] not in key2address:
                return {'success': False, 'message': f"Subnet {netuid} not found in local namespace, please deploy it "}
            key = c.get_key(key2address.get(subnet_params['founder']))
            c.print(f'Using key: {key}')

        # remove the params that are the same as the module info
        params = {**subnet_params, **params}
        for k in ['name', 'vote_mode']:
            params[k] = params[k].encode('utf-8')


        params['netuid'] = netuid


        return self.compose_call(fn='update_subnet',
                                     params=params, 
                                     key=key, 
                                     nonce=nonce)


    #################
    #### Serving ####
    #################
    def propose_subnet_update(
        self,
        netuid: int = None,
        key: str = None,
        network = 'main',
        nonce = None,
        **params,
    ) -> bool:
        """
        A function to propose an update for a subnet.

        Parameters:
            netuid: int, optional - The unique identifier of the subnet.
            key: str, optional - A key parameter.
            network: str - The network to operate on.
            nonce: None - A nonce parameter.
            **params - Additional keyword arguments.

        Returns:
            bool - The response of the function call.
        """

        self.resolve_network(network)
        netuid = self.resolve_netuid(netuid)
        c.print(f'Adding proposal to subnet {netuid}')
        subnet_params = self.subnet_params( netuid=netuid , update=True)
        # remove the params that are the same as the module info
        params = {**subnet_params, **params}
        for k in ['name', 'vote_mode']:
            params[k] = params[k].encode('utf-8')
        params['netuid'] = netuid

        response = self.compose_call(fn='add_subnet_proposal',
                                     params=params, 
                                     key=key, 
                                     nonce=nonce)


        return response



    #################
    #### Serving ####
    #################
    def vote_proposal(
        self,
        proposal_id: int = None,
        key: str = None,
        network = 'main',
        nonce = None,
        **params,

    ) -> bool:
        """
        Vote on a proposal.

        Args:
            proposal_id (int, optional): The ID of the proposal to vote on. Defaults to None.
            key (str, optional): The key used for voting. Defaults to None.
            network (str, optional): The network to use for voting. Defaults to 'main'.
            nonce (Any, optional): The nonce for the voting transaction. Defaults to None.
            **params: Additional parameters for voting.

        Returns:
            bool: True if the vote was successful, False otherwise.

        Raises:
            None

        Examples:
            >>> vote_proposal(proposal_id=1, key="my_key", network="testnet")
            True
        """

        self.resolve_network(network)
        # remove the params that are the same as the module info
        params = {
            'proposal_id': proposal_id,
            'netuid': netuid,
        }

        response = self.compose_call(fn='add_subnet_proposal',
                                     params=params, 
                                     key=key, 
                                     nonce=nonce)


        return response



    #################
    #### Serving ####
    #################
    def update_global(
        self,
        key: str = None,
        network = 'main',
        **params,
    ) -> bool:
        """
        A function to update a global setting with the given key and parameters.
        
        Parameters:
            key (str): The key to be updated.
            network (str): The network to perform the update on. Default is 'main'.
            **params: Additional keyword arguments for the update.
        
        Returns:
            bool: True if the update was successful, False otherwise.
        """

        key = self.resolve_key(key)
        network = self.resolve_network(network)
        global_params = self.global_params( )
        global_params.update(params)
        params = global_params
        for k,v in params.items():
            if isinstance(v, str):
                params[k] = v.encode('utf-8')

        # this is a sudo call
        response = self.compose_call(fn='update_global',
                                     params=params, 
                                     key=key, 
                                     sudo=True)

        return response





    #################
    #### set_code ####
    #################
    def set_code(
        self,
        wasm_file_path = None,
        key: str = None,
        network = network,
    ) -> bool:
        """
        A function to set the code for a smart contract on the blockchain.

        Args:
            wasm_file_path (str, optional): The file path to the WebAssembly (WASM) file. Defaults to None.
            key (str, optional): The key to sign the transaction. Defaults to None.
            network (str): The network to connect to.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """

        if wasm_file_path == None:
            wasm_file_path = self.wasm_file_path()

        assert os.path.exists(wasm_file_path), f'Wasm file not found at {wasm_file_path}'

        self.resolve_network(network)
        key = self.resolve_key(key)

        # Replace with the path to your compiled WASM file       
        with open(wasm_file_path, 'rb') as file:
            wasm_binary = file.read()
            wasm_hex = wasm_binary.hex()

        code = '0x' + wasm_hex

        # Construct the extrinsic
        response = self.compose_call(
            module='System',
            fn='set_code',
            params={
                'code': code.encode('utf-8')
            },
            unchecked_weight=True,
            sudo = True,
            key=key
        )

        return response

    
    def transfer_stake(
            self,
            new_module_key: str ,
            module_key: str ,
            amount: Union['Balance', float] = None, 
            key: str = None,
            netuid:int = None,
            wait_for_inclusion: bool = False,
            wait_for_finalization: bool = True,
            network:str = None,
            existential_deposit: float = 0.1,
            sync: bool = False
        ) -> bool:
        """
        Transfer stake from one module to another, with various optional parameters and network settings. Returns a boolean indicating success or failure.
        """
        # STILL UNDER DEVELOPMENT, DO NOT USE
        network = self.resolve_network(network)
        netuid = self.resolve_netuid(netuid)
        key = c.get_key(key)

        c.print(f':satellite: Staking to: [bold white]SubNetwork {netuid}[/bold white] {amount} ...')
        # Flag to indicate if we are using the wallet's own hotkey.

        name2key = self.name2key(netuid=netuid)
        module_key = self.resolve_module_key(module_key=module_key, netuid=netuid, name2key=name2key)
        new_module_key = self.resolve_module_key(module_key=new_module_key, netuid=netuid, name2key=name2key)

        assert module_key != new_module_key, f"Module key {module_key} is the same as new_module_key {new_module_key}"
        assert module_key in name2key.values(), f"Module key {module_key} not found in SubNetwork {netuid}"
        assert new_module_key in name2key.values(), f"Module key {new_module_key} not found in SubNetwork {netuid}"

        stake = self.get_stakefrom( module_key, from_key=key.ss58_address , fmt='j', netuid=netuid)

        if amount == None:
            amount = stake
        
        amount = self.to_nanos(amount - existential_deposit)
        
        # Get current stake
        params={
                    'netuid': netuid,
                    'amount': int(amount),
                    'module_key': module_key

                    }

        balance = self.get_balance( key.ss58_address , fmt='j')

        response  = self.compose_call('transfer_stake',params=params, key=key)

        if response['success']:
            new_balance = self.get_balance(key.ss58_address , fmt='j')
            new_stake = self.get_stakefrom( module_key, from_key=key.ss58_address , fmt='j', netuid=netuid)
            msg = f"Staked {amount} from {key.ss58_address} to {module_key}"
            return {'success': True, 'msg':msg, 'balance': {'old': balance, 'new': new_balance}, 'stake': {'old': stake, 'new': new_stake}}
        else:
            return  {'success': False, 'msg':response.error_message}



    def stake(
            self,
            module: Optional[str] = None, # defaults to key if not provided
            amount: Union['Balance', float] = None, 
            key: str = None,  # defaults to first key
            netuid:int = None,
            network:str = None,
            existential_deposit: float = 0,
            **kwargs
        ) -> bool:
        """
        description: 
            Unstakes the specified amount from the module. 
            If no amount is specified, it unstakes all of the amount.
            If no module is specified, it unstakes from the most staked module.
        params:
            amount: float = None, # defaults to all
            module : str = None, # defaults to most staked module
            key : 'c.Key' = None,  # defaults to first key 
            netuid : Union[str, int] = 0, # defaults to module.netuid
            network: str= main, # defaults to main
        return: 
            response: dict
        
        """
        network = self.resolve_network(network)
        netuid = self.resolve_netuid(netuid)
        key = c.get_key(key)
        
        
        if module == None:
            module_key = list(name2key.values())[0]

        else:
            key2name = self.key2name(netuid=netuid, update=False)

            if module in key2name:
                module_key = module
            else:
                name2key = self.name2key(netuid=netuid, update=False)
                if module in name2key:
                    module_key = name2key[module]
                else:
                    module_key = module

        # Flag to indicate if we are using the wallet's own hotkey.
        
        if amount == None:
            amount = self.get_balance( key.ss58_address , fmt='nano') - existential_deposit*10**9
        else:
            c.print(amount)
            amount = int(self.to_nanos(amount - existential_deposit))
        assert amount > 0, f"Amount must be greater than 0 and greater than existential deposit {existential_deposit}"
        
        # Get current stake
        params={
                    'netuid': netuid,
                    'amount': amount,
                    'module_key': module_key
                    }

        response = self.compose_call('add_stake',params=params, key=key)
        return response



    def unstake(
            self,
            module : str = None, # defaults to most staked module
            amount: float =None, # defaults to all of the amount
            key : 'c.Key' = None,  # defaults to first key
            netuid : Union[str, int] = 0, # defaults to module.netuid
            network: str= None,
            **kwargs
        ) -> dict:
        """
        description: 
            Unstakes the specified amount from the module. 
            If no amount is specified, it unstakes all of the amount.
            If no module is specified, it unstakes from the most staked module.
        params:
            amount: float = None, # defaults to all
            module : str = None, # defaults to most staked module
            key : 'c.Key' = None,  # defaults to first key 
            netuid : Union[str, int] = 0, # defaults to module.netuid
            network: str= main, # defaults to main
        return: 
            response: dict
        
        """
        if isinstance(module, int):
            amount = module
            module = None
        network = self.resolve_network(network)
        key = c.get_key(key)
        netuid = self.resolve_netuid(netuid)
        # get most stake from the module
        stake_to = self.get_stake_to(netuid=netuid, names = False, fmt='nano', key=key)

        module_key = None
        if module == None:
            # find the largest staked module
            max_stake = 0
            for k,v in stake_to.items():
                if v > max_stake:
                    max_stake = v
                    module_key = k            
        else:
            key2name = self.key2name(netuid=netuid)
            name2key = {key2name[k]:k for k,v in key2name.items()}
            if module in name2key:
                module_key = name2key[module]
            else:
                module_key = module
        
        # we expected to switch the module to the module key
        assert c.valid_ss58_address(module_key), f"Module key {module_key} is not a valid ss58 address"
        assert module_key in stake_to, f"Module {module_key} not found in SubNetwork {netuid}"
        if amount == None:
            amount = stake_to[module_key]
        else:
            amount = int(self.to_nanos(amount))
        # convert to nanos
        params={
            'amount': amount ,
            'netuid': netuid,
            'module_key': module_key
            }
        response = self.compose_call(fn='remove_stake',params=params, key=key, **kwargs)

        return response
            
    
    
    

    def stake_many( self, 
                        modules:List[str] = None,
                        amounts:Union[List[str], float, int] = None,
                        key: str = None, 
                        netuid:int = 0,
                        min_balance = 100_000_000_000,
                        n:str = 100,
                        network: str = None) -> Optional['Balance']:
        """
        A function that stakes multiple modules with specified amounts. 

        Args:
            modules (List[str], optional): A list of module names to stake to. Defaults to None.
            amounts (Union[List[str], float, int], optional): Amounts to stake for each module. Defaults to None.
            key (str, optional): The key for staking. Defaults to None.
            netuid (int, optional): The user ID for staking. Defaults to 0.
            min_balance (int): The minimum balance required for staking. Defaults to 100_000_000_000.
            n (str): The number of modules to stake to. Defaults to 100.
            network (str, optional): The network to stake on. Defaults to None.

        Returns:
            Optional['Balance']: The response from staking the modules.
        """
        network = self.resolve_network( network )
        netuid = self.resolve_netuid( netuid )
        key = self.resolve_key( key )

        if modules == None:
            my_modules = self.my_modules(netuid=netuid, network=network, update=False)
            modules = [m['key'] for m in my_modules if 'vali' in m['name']]

        modules = modules[:n] # only stake to the first n modules

        assert len(modules) > 0, f"No modules found with name {modules}"
        module_keys = modules
        if amounts == None:
            balance = self.get_balance(key=key, fmt='nanos') - min_balance
            amounts = [(balance // len(modules))] * len(modules) 
            assert sum(amounts) < balance, f'The total amount is {sum(amounts)} > {balance}'
        else:
            if isinstance(amounts, (float, int)): 
                amounts = [amounts] * len(modules)

            for i, amount in enumerate(amounts):
                amounts[i] = self.to_nanos(amount)

        assert len(modules) == len(amounts), f"Length of modules and amounts must be the same. Got {len(modules)} and {len(amounts)}."

        params = {
            "netuid": netuid,
            "module_keys": module_keys,
            "amounts": amounts
        }

        response = self.compose_call('add_stake_multiple', params=params, key=key)

        return response
                    


    def transfer_multiple( self, 
                        destinations:List[str],
                        amounts:Union[List[str], float, int],
                        key: str = None, 
                        netuid:int = 0,
                        n:str = 10,
                        local:bool = False,
                        network: str = None) -> Optional['Balance']:
        """
        Transfers multiple amounts to multiple destinations.

        Args:
            destinations (List[str]): A list of destination addresses.
            amounts (Union[List[str], float, int]): The amounts to transfer. If a single value is provided, it will be used for all destinations.
            key (str, optional): The private key to sign the transaction. Defaults to None.
            netuid (int, optional): The netuid of the network. Defaults to 0.
            n (str, optional): The number of destinations to transfer to. Defaults to 10.
            local (bool, optional): Whether to use local addresses. Defaults to False.
            network (str, optional): The network to use. Defaults to None.

        Returns:
            Optional['Balance']: The balance after the transfer.

        Raises:
            AssertionError: If the total amount exceeds the balance, or if the length of destinations and amounts is not the same.

        """
        network = self.resolve_network( network )
        key = self.resolve_key( key )
        balance = self.get_balance(key=key, fmt='j')

        # name2key = self.name2key(netuid=netuid)


        
        key2address = c.key2address()
        name2key = self.name2key(netuid=netuid)

        if isinstance(destinations, str):
            local_destinations = [k for k,v in key2address.items() if destinations in k]
            if len(destinations) > 0:
                destinations = local_destinations
            else:
                destinations = [_k for _n, _k in name2key.items() if destinations in _n]

        assert len(destinations) > 0, f"No modules found with name {destinations}"
        destinations = destinations[:n] # only stake to the first n modules
        # resolve module keys
        for i, destination in enumerate(destinations):
            if destination in name2key:
                destinations[i] = name2key[destination]
            if destination in key2address:
                destinations[i] = key2address[destination]

        if isinstance(amounts, (float, int)): 
            amounts = [amounts] * len(destinations)

        assert len(destinations) == len(amounts), f"Length of modules and amounts must be the same. Got {len(modules)} and {len(amounts)}."
        assert all([c.valid_ss58_address(d) for d in destinations]), f"Invalid destination address {destinations}"



        total_amount = sum(amounts)
        assert total_amount < balance, f'The total amount is {total_amount} > {balance}'


        # convert the amounts to their interger amount (1e9)
        for i, amount in enumerate(amounts):
            amounts[i] = self.to_nanos(amount)

        assert len(destinations) == len(amounts), f"Length of modules and amounts must be the same. Got {len(modules)} and {len(amounts)}."

        params = {
            "netuid": netuid,
            "destinations": destinations,
            "amounts": amounts
        }

        response = self.compose_call('transfer_multiple', params=params, key=key)

        return response

    transfer_many = transfer_multiple


    def unstake_many( self, 
                        modules:Union[List[str], str] = None,
                        amounts:Union[List[str], float, int] = None,
                        key: str = None, 
                        netuid:int = 0,
                        network: str = None) -> Optional['Balance']:
        """
        This function unstakes multiple modules from the blockchain, with the option to specify the modules and corresponding amounts. It resolves the network and key, and then performs the unstaking operation. The parameters include modules (either a list of strings or a string), amounts (either a list of strings, a float, or an integer), key, netuid, and network. It returns an optional Balance object.
        """
        
        network = self.resolve_network( network )
        key = self.resolve_key( key )

        if modules == None or modules == 'all':
            stake_to = self.get_stake_to(key=key, netuid=netuid, names=False, update=True, fmt='nanos') # name to amount
            module_keys = [k for k in stake_to.keys()]
            # RESOLVE AMOUNTS
            if amounts == None:
                amounts = [stake_to[m] for m in module_keys]

        else:
            name2key = {}

            module_keys = []
            for i, module in enumerate(modules):
                if c.valid_ss58_address(module):
                    module_keys += [module]
                else:
                    if name2key == {}:
                        name2key = self.name2key(netuid=netuid, update=True)
                    assert module in name2key, f"Invalid module {module} not found in SubNetwork {netuid}"
                    module_keys += [name2key[module]]
                
            # RESOLVE AMOUNTS
            if amounts == None:
                stake_to = self.get_staketo(key=key, netuid=netuid, names=False, update=True, fmt='nanos') # name to amounts
                amounts = [stake_to[m] for m in module_keys]
                

            if isinstance(amounts, (float, int)): 
                amounts = [amounts] * len(module_keys)

            for i, amount in enumerate(amounts):
                amounts[i] = self.to_nanos(amount) 

        assert len(module_keys) == len(amounts), f"Length of modules and amounts must be the same. Got {len(module_keys)} and {len(amounts)}."

        params = {
            "netuid": netuid,
            "module_keys": module_keys,
            "amounts": amounts
        }
        c.print(params)
        response = self.compose_call('remove_stake_multiple', params=params, key=key)

        return response
                    

    def unstake2key( self,
                    modules = 'all',
                    netuid = 0,
                    network = network,
                    to = None):
        """
        unstake2key function to unstake modules. 

        Args:
            modules (str or list): Module name or list of module names to unstake. Defaults to 'all'.
            netuid (int): Unique identifier for the network. Defaults to 0.
            network: The network to unstake modules from.
            to: Not used in this function.

        Returns:
            None
        """
        if modules == 'all':
            modules = self.my_modules()
        else:
            assert isinstance(modules, list), f"Modules must be a list of module names"
            for m in modules:
                assert m in self.my_modules_names(), f"Module {m} not found in your modules"
            modules = [m for m in self.my_modules() if m['name'] in modules or m['key'] in modules]

        c.print(f'Unstaking {len(modules)} modules')

        



    def unstake_all( self, 
                        key: str = 'model.openai', 
                        netuid = 0,
                        network = network,
                        to = None,
                        existential_deposit = 1) -> Optional['Balance']:
        """
        Unstakes all the modules from the specified key, with the option to specify the network, recipient, and existential deposit amount. Returns the response of the unstaking and transfer operations.
        
        Args:
            key (str): The key to unstake the modules from. Defaults to 'model.openai'.
            netuid: The netuid value for the modules.
            network: The network to use for the operation.
            to: The recipient of the unstaked amount.
            existential_deposit (int): The amount of existential deposit.
            
        Returns:
            Optional['Balance']: The response of the unstaking and transfer operations.
        """
        
        network = self.resolve_network( network )
        key = self.resolve_key( key )
    
        key_stake_to = self.get_stake_to(key=key, netuid=netuid, names=False, update=True, fmt='nanos') # name to amount
        


        params = {
            "netuid": netuid,
            "module_keys": list(key_stake_to.keys()),
            "amounts": list(key_stake_to.values())
        }

        response = {}

        if len(key_stake_to) > 0:
            c.print(f'Unstaking all of {len(key_stake_to)} modules')
            response['stake'] = self.compose_call('remove_stake_multiple', params=params, key=key)
            total_stake = (sum(key_stake_to.values())) / 1e9
        else: 
            c.print(f'No modules found to unstake')
            total_stake = self.get_balance(key)

        total_stake = total_stake - existential_deposit
        to = c.get_key(to)
        c.print(f'Transfering {total_stake} to ')
        response['transfer'] = self.transfer(dest=to, amount=total_stake, key=key)
        
        return response
                    

    

    def my_servers(self, search=None,  **kwargs):
        """
        Retrieves a list of servers associated with the user's modules.

        Args:
            search (str, optional): A string to search for within the server names. Defaults to None.
            **kwargs: Additional keyword arguments to be passed to the `my_modules` method.

        Returns:
            list: A list of server names that match the search criteria. If no search criteria is provided, all server names are returned.
        """
        servers = [m['name'] for m in self.my_modules(**kwargs)]
        if search != None:
            servers = [s for s in servers if search in s]
        return servers
    
    def my_modules_names(self, *args, **kwargs):
        """
        Generate the names of all modules owned by the user.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List[str]: A list of strings representing the names of the modules owned by the user.
        """
        my_modules = self.my_modules(*args, **kwargs)
        return [m['name'] for m in my_modules]

    def my_module_keys(self, *args,  **kwargs):
        """
        A description of the entire function, its parameters, and its return types.
        """
        modules = self.my_modules(*args, **kwargs)
        return [m['key'] for m in modules]

    def my_key2uid(self, *args, network=None, netuid=0, update=False, **kwargs):
        """
        This function takes in variable arguments, a network, netuid, and update flag. It calls the key2uid method to get a dictionary, then calls the key2address method to get a dictionary, and filters the key2uid dictionary based on the keys present in the values of the key2address dictionary. It returns the filtered dictionary.
        """
        key2uid = self.key2uid(*args, network=network, netuid=netuid, **kwargs)
        key2address = c.key2address(update=update )
        key_addresses = list(key2address.values())
        my_key2uid = { k: v for k,v in key2uid.items() if k in key_addresses}
        return my_key2uid
    
    def staked_modules(self, key = None, netuid = 0, network = 'main', **kwargs):
        """
        Retrieves staked modules for a given key and network.

        Args:
            key (optional): The key to retrieve staked modules for.
            netuid (optional): The network UID to retrieve staked modules for.
            network (optional): The network to retrieve staked modules for.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary of staked modules.
        """
        key = self.resolve_key(key)
        netuid = self.resolve_netuid(netuid)
        staked_modules = self.get_stake_to(key=key, netuid=netuid, names=False, update=True, network=network, **kwargs)
        keys = list(staked_modules.keys())
        modules = self.get_modules(keys)
        return modules

    
    
    
    def my_keys(self, *args, **kwargs):
        """
        Returns a list of keys from the result of calling `my_key2uid` method with the given arguments.
        """
        return list(self.my_key2uid(*args, **kwargs).keys())

    def vote(
        self,
        uids: Union['torch.LongTensor', list] = None,
        weights: Union['torch.FloatTensor', list] = None,
        netuid: int = 0,
        key: 'c.key' = None,
        network = None,
        update=False,
    ) -> bool:
        """
        Vote function for setting weights for uids in a network.
        
        Parameters:
            uids: Union['torch.LongTensor', list] = None - UIDs to vote for.
            weights: Union['torch.FloatTensor', list] = None - Associated weights for the uids.
            netuid: int = 0 - Network ID.
            key: 'c.key' = None - Key for the vote.
            network - Network information.
            update: bool = False - Flag for updating.

        Returns:
            bool: Success status of the voting process.
        """
        import torch
        network = self.resolve_network(network)
        netuid = self.resolve_netuid(netuid)
        key = self.resolve_key(key)
        module_info = self.get_module(key.ss58_address, netuid=netuid)
        
        subnet = self.subnet( netuid = netuid )
        min_allowed_weights = subnet['min_allowed_weights']
        global_params = self.global_params( network=network, update=update, fmt='j')
        max_allowed_weights = subnet['max_allowed_weights']
        
        stake = module_info['stake']
        min_weight_stake = global_params['min_weight_stake']/1e9
        min_stake = min_weight_stake * min_allowed_weights
        assert stake > min_stake, f"Stake {stake} < min_stake {min_stake} for subnet {netuid}"
        max_num_votes = stake // min_weight_stake
        n = int(min(max_num_votes, max_allowed_weights))
        # checking if the "uids" are passed as names -> strings
        if uids != None and all(isinstance(item, str) for item in uids):
            names2uid = self.names2uids(names=uids, netuid=netuid)
            for i, name in enumerate(uids):
                if name in names2uid:
                    uids[i] = names2uid[name]
                else:
                    c.print(f'Could not find {name} in network {netuid}')
                    return False

        if uids == None:
            # we want to vote for the nonzero dividedn
            uids = self.uids(netuid=netuid, network=network, update=update)
            assert len(uids) > 0, f"No nonzero dividends found in network {netuid}"
            # shuffle the uids
            uids = c.shuffle(uids)
            
        if weights is None:
            weights = [1 for _ in uids]


        

  
        if len(uids) < min_allowed_weights:
            n = self.n(netuid=netuid)
            while len(uids) < min_allowed_weights:
                
                uid = c.choice(list(range(n)))
                if uid not in uids:
                    uids.append(uid)
                    weights.append(1)

        uid2weight = {uid: weight for uid, weight in zip(uids, weights)}
        # sort the uids and weights
        uid2weight = {k: v for k, v in dict(sorted(uid2weight.items(), key=lambda item: item[1], reverse=True)).items()}
        
        c.print(n)
        uids = list(uid2weight.keys())[:n]
        weights = list(uid2weight.values())[:n]

        c.print(f'Voting for {len(uids)} uids in network {netuid} with {len(weights)} weights')

        
        if len(uids) == 0:
            return {'success': False, 'message': f'No uids found in network {netuid}'}
        
        assert len(uids) == len(weights), f"Length of uids {len(uids)} must be equal to length of weights {len(weights)}"


        uids = uids[:max_allowed_weights]
        weights = weights[:max_allowed_weights]

        # uids = [int(uid) for uid in uids]
        uid2weight = {uid: weight for uid, weight in zip(uids, weights)}
        uids = list(uid2weight.keys())
        weights = list(uid2weight.values())

        # sort the uids and weights
        uids = torch.tensor(uids)
        weights = torch.tensor(weights)
        indices = torch.argsort(weights, descending=True)
        uids = uids[indices]
        weights = weights[indices]
        c.print(weights)
        weight_sum = weights.sum()
        assert weight_sum > 0, f"Weight sum must be greater than 0. Got {weight_sum}"
        weights = weights / (weight_sum)
        U16_MAX = 2**16 - 1
        weights = weights * (U16_MAX)
        weights = list(map(lambda x : int(min(x, U16_MAX)), weights.tolist()))

        uids = list(map(int, uids.tolist()))

        params = {'uids': uids,
                  'weights': weights, 
                  'netuid': netuid}
        
        response = self.compose_call('set_weights',params = params , key=key)
            
        if response['success']:
            return {'success': True,  'num_weigts': len(uids), 'message': 'Set weights', 'key': key.ss58_address, 'netuid': netuid, 'network': network}
        
        return response

    set_weights = vote



    def register_servers(self, search=None, **kwargs):
        """
        Registers servers based on the provided search criteria and keyword arguments.

        :param search: Optional search criteria
        :param kwargs: Additional keyword arguments
        :return: None
        """
        stakes = self.stakes()
        for m in c.servers(network='local'):
            try:
                key = c.get_key(m)
                if key.ss58_address in stakes:
                    self.update_module(module=m)
                else:
                    self.register(name=m)
            except Exception as e:
                c.print(e, color='red')
    reg_servers = register_servers
    def reged_servers(self, **kwargs):
        """
        Retrieves the registered servers from the local network.

        :param kwargs: Additional keyword arguments.
        :return: The list of registered servers.
        """
        servers =  c.servers(network='local')



    def my_uids(self, *args, **kwargs):
        """
        Returns a list of unique identifiers (UIDs) associated with the current instance of the class.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            list: A list of UIDs associated with the current instance.
        """
        return list(self.my_key2uid(*args, **kwargs).values())
    
    def my_names(self, *args, **kwargs):
        my_modules = self.my_modules(*args, **kwargs)
        return [m['name'] for m in my_modules]
 


    def registered_servers(self, netuid = 0, network = network,  **kwargs):
        """
        A function that retrieves registered servers based on the provided netuid, network, and additional keyword arguments.
        Parameters:
            netuid : int, optional (default = 0)
                The unique identifier for the network.
            network : str
                The network to retrieve servers from.
            **kwargs : dict
                Additional keyword arguments to be passed.
        Returns:
            list
                A list of registered server keys.
        """
        netuid = self.resolve_netuid(netuid)
        network = self.resolve_network(network)
        servers = c.servers(network='local')
        registered_keys = []
        for s in servers:
            if self.is_registered(s, netuid=netuid):
                registered_keys += [s]
        return registered_keys
    reged = reged_servers = registered_servers

    def unregistered_servers(self, netuid = 0, network = network,  **kwargs):
        """
        Retrieves a list of unregistered servers.

        This function takes in an optional parameter `netuid` which represents the unique identifier for the network.
        If `netuid` is not provided, it defaults to 0.

        The `network` parameter represents the network for which the unregistered servers are to be retrieved.
        If `network` is not provided, it defaults to the value of the `network` variable.

        Additional keyword arguments can be provided, but they are not used in this function.

        Returns:
            list: A list of unregistered server keys.

        """
        netuid = self.resolve_netuid(netuid)
        network = self.resolve_network(network)
        network = self.resolve_network(network)
        servers = c.servers(network='local')
        unregistered_keys = []
        for s in servers:
            if not self.is_registered(s, netuid=netuid):
                unregistered_keys += [s]
        return unregistered_keys

    
    def check_reged(self, netuid = 0, network = network,  **kwargs):
        """
        Checks if a given `netuid` is registered in the specified `network`.
        
        :param netuid: An integer representing the `netuid` to be checked. Defaults to 0.
        :param network: A string representing the `network` to be checked. Defaults to 'network'.
        :param **kwargs: Additional keyword arguments.
        
        :return: A dictionary containing the results of the check.
        """
        reged = self.reged(netuid=netuid, network=network, **kwargs)
        jobs = []
        for module in reged:
            job = c.call(module=module, fn='info',  network='subspace', netuid=netuid, return_future=True)
            jobs += [job]

        results = dict(zip(reged, c.gather(jobs)))

        return results 

    unreged = unreged_servers = unregistered_servers
               
    def my_balances(self, search=None, update=False, fmt='j', min_value=10, **kwargs):
        """
        Retrieves the balances of the addresses associated with the given search criteria.

        Args:
            search (str, optional): The search criteria to filter the addresses. Defaults to None.
            update (bool, optional): Whether to update the balances. Defaults to False.
            fmt (str, optional): The format of the balances. Defaults to 'j'.
            min_value (int, optional): The minimum value of balances to include. Defaults to 10.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: A dictionary containing the balances of the addresses associated with the search criteria, filtered by the minimum value.
        """
        key2address = c.key2address(search)
        balances = self.balances(update=update, fmt=fmt, **kwargs)
        my_balances = {k:balances[v] for k,v in key2address.items() if v in balances}
        if min_value > 0:
            my_balances = {k:v for k,v in my_balances.items() if v > min_value}
        return my_balances
    


    def stake_spread(self,  modules:list=None, key:str = None,ratio = 1.0, n:int=50):
        """
        Stakes a specified amount of tokens for a given list of modules.

        Args:
            modules (list, optional): A list of modules to stake tokens for. Defaults to None.
            key (str, optional): The key to use for staking. Defaults to None.
            ratio (float, optional): The ratio of the total balance to stake. Defaults to 1.0.
            n (int, optional): The number of top modules to consider. Defaults to 50.

        Raises:
            AssertionError: If the balance is less than or equal to 0, or if the ratio is greater than 1.0 or less than 0.0.

        Returns:
            None
        """
        key = self.resolve_key(key)
        name2key = self.name2key()
        if modules == None:
            modules = self.top_valis(n=n)
        if isinstance(modules, str):
            modules = [k for k,v in name2key.items() if modules in k]

        modules = modules[:n]
        modules = c.shuffle(modules)

        name2key = {k:name2key[k] for k in modules if k in name2key}


        module_names = list(name2key.keys())
        module_keys = list(name2key.values())
        n = len(name2key)

        # get the balance, of the key
        balance = self.get_balance(key)
        assert balance > 0, f'balance must be greater than 0, not {balance}'
        assert ratio <= 1.0, f'ratio must be less than or equal to 1.0, not {ratio}'
        assert ratio > 0.0, f'ratio must be greater than or equal to 0.0, not {ratio}'

        balance = int(balance * ratio)
        assert balance > 0, f'balance must be greater than 0, not {balance}'
        stake_per_module = int(balance/n)


        c.print(f'staking {stake_per_module} per module for ({module_names}) modules')

        s = c.module('subspace')()

        s.stake_many(key=key, modules=module_keys, amounts=stake_per_module)

       
    def key2value(self, search=None, fmt='j', netuid=0, **kwargs):
        """
        This function takes in several parameters and returns a dictionary with updated values based on the input parameters.
        """
        key2value = self.my_balance(search=search, fmt=fmt, **kwargs)
        for k,v in self.my_stake(search=search, fmt=fmt, netuid=netuid, **kwargs).items():
            key2value[k] += v
        return key2value

    def total_value(self, search=None, fmt='j', **kwargs):
        """
        Calculate the total value based on the provided search criteria and format, and return the sum of the values.
        
        :param search: (optional) The search criteria to filter the values.
        :param fmt: (optional) The format of the values. Default is 'j'.
        :param kwargs: Additional keyword arguments.
        :return: The total sum of the values.
        """
        return sum(self.key2value(search=search, fmt=fmt, **kwargs).values())


    def my_stake(self, search=None, netuid = 0, network = None, fmt=fmt,  block=None, update=False):
        """
        Calculates the stake for each key in `mystaketo` dictionary based on the provided `netuid`, `network`, `fmt`, `block`, and `update` parameters. 
        
        Args:
            search (str, optional): A string to search for in the keys of `mystaketo` dictionary. Defaults to None.
            netuid (int, optional): The netuid parameter. Defaults to 0.
            network (str, optional): The network parameter. Defaults to None.
            fmt (str, optional): The fmt parameter. Defaults to fmt.
            block (str, optional): The block parameter. Defaults to None.
            update (bool, optional): The update parameter. Defaults to False.
            
        Returns:
            dict: A dictionary containing the keys from `mystaketo` dictionary and their corresponding stake values.
        """
        mystaketo = self.my_stake_to(netuid=netuid, network=network, fmt=fmt,block=block, update=update)
        key2stake = {}
        for key, staketo_tuples in mystaketo.items():
            stake = sum([s for a, s in staketo_tuples])
        if search != None:
            key2stake = {k:v for k,v in key2stake.items() if search in k}
        return key2stake
    


    def stake_top_modules(self,netuid=netuid, feature='dividends', **kwargs):
        """
        A function to stake top modules based on a specified feature with optional keyword arguments.
        
        Parameters:
            netuid: str, optional, the unique identifier for the network
            feature: str, the feature to base the stake on, default is 'dividends'
            **kwargs: additional keyword arguments to pass to other functions
        
        Returns:
            None
        """
        top_module_keys = self.top_module_keys(k='dividends')
        self.stake_many(modules=top_module_keys, netuid=netuid, **kwargs)
    
    def rank_my_modules(self,search=None, k='stake', n=10, **kwargs):
        """
        Ranks the modules based on the given search criteria and returns the top 'n' ranked modules.

        Parameters:
            search (str, optional): The search criteria to filter the modules. Defaults to None.
            k (str, optional): The ranking criterion. Defaults to 'stake'.
            n (int, optional): The number of top ranked modules to return. Defaults to 10.
            **kwargs: Additional keyword arguments.

        Returns:
            list: A list of the top 'n' ranked modules.
        """
        modules = self.my_modules(search=search, **kwargs)
        ranked_modules = self.rank_modules(modules=modules, search=search, k=k, n=n, **kwargs)
        return modules[:n]


    mys =  mystake = key2stake =  my_stake


    def my_balance(self, search:str=None, update=False, network:str = 'main', fmt=fmt,  block=None, min_value:int = 0):
        """
        Calculate the balance of the user for a specific network.

        Parameters:
            search (str, optional): A string to search for in the balance dictionary. Defaults to None.
            update (bool, optional): Whether to update the balance or not. Defaults to False.
            network (str, optional): The network to calculate the balance for. Defaults to 'main'.
            fmt (str, optional): The format of the balance. Defaults to fmt.
            block (int, optional): The block number to calculate the balance at. Defaults to None.
            min_value (int, optional): The minimum value of the balance to include. Defaults to 0.

        Returns:
            dict: A dictionary containing the user's balance for each key.
        """

        balances = self.balances(network=network, fmt=fmt, block=block, update=update)
        my_balance = {}
        key2address = c.key2address()
        for key, address in key2address.items():
            if address in balances:
                my_balance[key] = balances[address]

        if search != None:
            my_balance = {k:v for k,v in my_balance.items() if search in k}
            
        my_balance = dict(sorted(my_balance.items(), key=lambda x: x[1], reverse=True))

        if min_value > 0:
            my_balance = {k:v for k,v in my_balance.items() if v > min_value}

        return my_balance
        
    key2balance = myb = mybal = my_balance

    def my_value(
                 self, 
                 network = 'main',
                 update=False,
                 fmt='j'
                 ):
        """
        Calculate the sum of the total stake and total balance for a given network.
        
        :param network: The network to calculate the sum for. Default is 'main'.
        :type network: str
        :param update: Whether to update the values before calculating the sum. Default is False.
        :type update: bool
        :param fmt: The format of the returned value. Default is 'j'.
        :type fmt: str
        
        :return: The sum of the total stake and total balance.
        :rtype: int or float
        """
        return self.my_total_stake(network=network, update=update, fmt=fmt,) + \
                    self.my_total_balance(network=network, update=update, fmt=fmt)
    
    my_supply   = my_value

    def subnet2stake(self, network=None, update=False) -> dict:
        subnet2stake = {}
        for subnet_name in self.subnet_names(network=network):
            c.print(f'Getting stake for subnet {subnet_name}')
            subnet2stake[subnet_name] = self.my_total_stake(network=network, netuid=subnet_name , update=update)
        return subnet2stake

    def my_total_stake(self, netuid='all', network = 'main', fmt=fmt, update=False):
        """
        Calculate the total stake for the specified netuid on the specified network.
        
        Parameters:
            netuid (str): The identifier for the stakeholder. Default is 'all'.
            network (str): The network to calculate the stake on. Default is 'main'.
            fmt (fmt): The format of the stake information.
            update (bool): Whether to update the stake information. Default is False.
        
        Returns:
            float: The total stake value.
        """
        my_stake_to = self.my_stake_to(netuid=netuid, network=network, fmt=fmt, update=update)
        return sum(list(my_stake_to.values()))


    def staker2stake(self,  update=False, network='main', fmt='j', local=False):
        """
        Calculates the total stake for each staker in the given network.

        Args:
            update (bool, optional): Whether to update the stake information. Defaults to False.
            network (str, optional): The network to calculate the stake for. Defaults to 'main'.
            fmt (str, optional): The format of the returned stake information. Defaults to 'j'.
            local (bool, optional): Whether to use local stake information. Defaults to False.

        Returns:
            dict: A dictionary mapping each staker to their total stake.

        Raises:
            None

        Examples:
            >>> staker2stake()
            {'staker1': 100, 'staker2': 50}
        """
        staker2netuid2stake = self.staker2netuid2stake(update=update, network=network, fmt=fmt, local=local)
        staker2stake = {}
        for staker, netuid2stake in staker2netuid2stake.items():
            if staker not in staker2stake:
                staker2stake[staker] = 0
            
        return staker2stake
    

    def staker2netuid2stake(self,  update=False, network='main', fmt='j', local=False, **kwargs):
        """
        A function to update staker to netuid to stake mapping and return the updated dictionary.
        
        Parameters:
            update (bool): If True, update the mapping, default is False.
            network (str): The network for which the mapping is to be updated, default is 'main'.
            fmt (str): The format of the stake, default is 'j'.
            local (bool): If True, use a local mapping, default is False.
            **kwargs: Additional keyword arguments for querying the mapping.

        Returns:
            dict: The updated staker to netuid to stake mapping.
        """
        stake_to = self.query_map("StakeTo", update=update, network=network, **kwargs)
        staker2netuid2stake = {}
        for netuid , stake_to_subnet in stake_to.items():
            for staker, stake_tuples in stake_to_subnet.items():
                staker2netuid2stake[staker] = staker2netuid2stake.get(staker, {})
                staker2netuid2stake[staker][netuid] = staker2netuid2stake[staker].get(netuid, [])
                staker2netuid2stake[staker][netuid] = sum(list(map(lambda x: x[-1], stake_tuples )))
                staker2netuid2stake[staker][netuid] +=  self.format_amount(staker2netuid2stake[staker][netuid],fmt=fmt)
        
        if local:
            address2key = c.address2key()
            staker2netuid2stake = {address:staker2netuid2stake.get(address,{}) for address in address2key.keys()}

        return staker2netuid2stake
    

 
    def my_total_balance(self, network = None, fmt=fmt, update=False):
        """
        Calculate the total balance for a user on a given network.

        :param network: (optional) The network on which to calculate the balance.
        :type network: str
        :param fmt: (optional) The format in which to display the balance.
        :type fmt: str
        :param update: (optional) Whether to update the balance before calculating the total.
        :type update: bool
        :return: The total balance for the user on the specified network.
        :rtype: float
        """
        return sum(self.my_balance(network=network, fmt=fmt, update=update ).values())


    def check_valis(self, **kwargs):
        """
        Check the validity of the servers based on the given parameters.

        :param kwargs: Additional parameters to be passed to the `check_servers` method.
        :return: The result of the `check_servers` method.
        """
        return self.check_servers(search='vali', **kwargs)
    
    
    def check_servers(self, search='vali',update:bool=False,  min_lag=100, remote=False, **kwargs):
        """
        Generate a batch response after checking the status of servers for the given search criteria.
        
        Parameters:
            search (str): The criteria to search for in the servers.
            update (bool): Flag indicating whether to update the server information.
            min_lag (int): The minimum acceptable lag for a server.
            remote (bool): Flag indicating whether to execute the function remotely.
            **kwargs: Additional keyword arguments.
        
        Returns:
            dict: A dictionary containing the response for each server checked.
        """
        if remote:
            kwargs = c.locals2kwargs(locals())
            return self.remote_fn('check_servers', kwargs=kwargs)
        cols = ['name', 'serving', 'address', 'last_update', 'stake', 'dividends']
        module_stats = self.stats(search=search, netuid=0, cols=cols, df=False, update=update)
        module2stats = {m['name']:m for m in module_stats}
        block = self.block
        response_batch = {}
        c.print(f"Checking {len(module2stats)} {search} servers")
        for module, stats in module2stats.items():
            # check if the module is serving
            lag = block - stats['last_update']
            if not c.server_exists(module) or lag > min_lag:
                response  = c.serve(module)
            else:
                response = f"{module} is already serving or has a lag of {lag} blocks but less than {min_lag} blocks"
            response_batch[module] = response

        return response_batch




    def compose_call(self,
                     fn:str, 
                    params:dict = None, 
                    key:str = None,
                    tip: int = 0, # tip can
                    module:str = 'SubspaceModule', 
                    wait_for_inclusion: bool = True,
                    wait_for_finalization: bool = True,
                    process_events : bool = True,
                    color: str = 'yellow',
                    verbose: bool = True,
                    save_history : bool = True,
                    sudo:bool  = False,
                    nonce: int = None,
                    remote_module: str = None,
                    unchecked_weight: bool = False,
                    network = network,
                    mode='ws',
                     **kwargs):
        """
        A method to compose and execute a call using a given function name and parameters.
        :param fn: The name of the function to call.
        :param params: A dictionary of parameters to pass to the function.
        :param key: The key used for the call.
        :param tip: The tip value for the call.
        :param module: The module to call the function from.
        :param wait_for_inclusion: A boolean indicating whether to wait for inclusion.
        :param wait_for_finalization: A boolean indicating whether to wait for finalization.
        :param process_events: A boolean indicating whether to process events.
        :param color: The color to display the transaction information.
        :param verbose: A boolean indicating whether to display verbose information.
        :param save_history: A boolean indicating whether to save the transaction history.
        :param sudo: A boolean indicating whether to use sudo for the call.
        :param nonce: The nonce value for the call.
        :param remote_module: The remote module to connect to.
        :param unchecked_weight: A boolean indicating whether to use unchecked weight.
        :param network: The network to connect to.
        :param mode: The mode of connection.
        :param **kwargs: Additional keyword arguments.
        :return: The response of the call.
        """
        key = self.resolve_key(key)
        network = self.resolve_network(network, mode=mode)

        if remote_module != None:
            kwargs = c.locals2kwargs(locals())
            return c.connect(remote_module).compose_call(**kwargs)

        params = {} if params == None else params
        if verbose:
            kwargs = c.locals2kwargs(locals())
            kwargs['verbose'] = False
            c.status(f":satellite: Calling [bold]{fn}[/bold]")
            return self.compose_call(**kwargs)

        start_time = c.datetime()
        ss58_address = key.ss58_address
        paths = {m: f'history/{self.network}/{ss58_address}/{m}/{start_time}.json' for m in ['complete', 'pending']}
        params = {k: int(v) if type(v) in [float]  else v for k,v in params.items()}
        compose_kwargs = dict(
                call_module=module,
                call_function=fn,
                call_params=params,
        )

        c.print(f'Sending Transaction: 📡', compose_kwargs, color=color)
        tx_state = dict(status = 'pending',start_time=start_time, end_time=None)

        self.put_json(paths['pending'], tx_state)

        substrate = self.get_substrate(network=network, mode='ws')
        call = substrate.compose_call(**compose_kwargs)

        if sudo:
            call = substrate.compose_call(
                call_module='Sudo',
                call_function='sudo',
                call_params={
                    'call': call,
                }
            )
        if unchecked_weight:
            # uncheck the weights for set_code
            call = substrate.compose_call(
                call_module="Sudo",
                call_function="sudo_unchecked_weight",
                call_params={
                    "call": call,
                    'weight': (0,0)
                },
            )
        # get nonce 
        extrinsic = substrate.create_signed_extrinsic(call=call,keypair=key,nonce=nonce, tip=tip)

        response = substrate.submit_extrinsic(extrinsic=extrinsic,
                                                wait_for_inclusion=wait_for_inclusion, 
                                                wait_for_finalization=wait_for_finalization)

        if wait_for_finalization:
            if process_events:
                response.process_events()

            if response.is_success:
                response =  {'success': True, 'tx_hash': response.extrinsic_hash, 'msg': f'Called {module}.{fn} on {self.network} with key {key.ss58_address}'}
            else:
                response =  {'success': False, 'error': response.error_message, 'msg': f'Failed to call {module}.{fn} on {self.network} with key {key.ss58_address}'}
        else:
            response =  {'success': True, 'tx_hash': response.extrinsic_hash, 'msg': f'Called {module}.{fn} on {self.network} with key {key.ss58_address}'}
        

        tx_state['end_time'] = c.datetime()
        tx_state['status'] = 'completed'
        tx_state['response'] = response

        # remo 
        self.rm(paths['pending'])
        self.put_json(paths['complete'], tx_state)

        return response
            

    def tx_history(self, key:str=None, mode='complete',network=network, **kwargs):
        """
        Retrieves the transaction history for a given key.

        Args:
            key (str, optional): The key to retrieve the transaction history for. Defaults to None.
            mode (str, optional): The mode of retrieval. Can be either 'pending' or 'complete'. Defaults to 'complete'.
            network (str, optional): The network to retrieve the transaction history from. Defaults to the value of the 'network' parameter.
            **kwargs: Additional keyword arguments.

        Returns:
            list: A list of transaction history objects.

        Raises:
            AssertionError: If the mode is not 'pending' or 'complete'.
        """
        key_ss58 = self.resolve_key_ss58(key)
        assert mode in ['pending', 'complete']
        pending_path = f'history/{network}/{key_ss58}/{mode}'
        return self.glob(pending_path)
    
    def pending_txs(self, key:str=None, **kwargs):
        """
        Retrieve pending transactions using the specified key and additional keyword arguments.
        """
        return self.tx_history(key=key, mode='pending', **kwargs)

    def complete_txs(self, key:str=None, **kwargs):
        """
        This function completes transactions using the provided key and optional keyword arguments.
        """
        return self.tx_history(key=key, mode='complete', **kwargs)

    def clean_tx_history(self):
        """
        Clean transaction history and return the result.
        """
        return self.ls(f'tx_history')

        
    def resolve_tx_dirpath(self, key:str=None, mode:'str([pending,complete])'='pending', network=network, **kwargs):
        """
        Resolves the directory path for a given key in the transaction history.

        Args:
            key (str, optional): The key to resolve the directory path for. Defaults to None.
            mode (str, optional): The mode of the transaction history. Must be either 'pending' or 'complete'. Defaults to 'pending'.
            network (str): The network on which the transaction history is stored.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The resolved directory path for the given key and mode.

        Raises:
            AssertionError: If the mode is not either 'pending' or 'complete'.
        """
        key_ss58 = self.resolve_key_ss58(key)
        assert mode in ['pending', 'complete']
        pending_path = f'history/{network}/{key_ss58}/{mode}'
        return pending_path
    

    def resolve_key(self, key = None):
        """
        Resolve the key to be used, taking into account default values and configurations.

        Parameters:
            key (str): The key to be resolved. If None, it defaults to self.config.key or 'module'.

        Returns:
            str: The resolved key with an ss58_address attribute.
        """
        if key == None:
            key = self.config.key
        if key == None:
            key = 'module'
        if isinstance(key, str):
            if c.key_exists( key ):
                key = c.get_key( key )
            else:
                raise ValueError(f"Key {key} not found in your keys, please make sure you have it")
        assert hasattr(key, 'ss58_address'), f"Invalid Key {key} as it should have ss58_address attribute."
        return key
        
    @classmethod
    def test_endpoint(cls, url=None):
        """
        Test the endpoint by setting the network with the given URL and checking if the network is successfully set.
        
        :param url: (optional) The URL to test the endpoint with. If not provided, a random URL from the list of URLs will be used.
        :type url: str
        
        :return: True if the network is successfully set, False otherwise.
        :rtype: bool
        """
        if url == None:
            url = c.choice(cls.urls())
        self = cls()
        c.print('testing url -> ', url, color='yellow' )

        try:
            self.set_network(url=url, trials=1)
            success = isinstance(self.block, int)
        except Exception as e:
            c.print(c.detailed_error(e))
            success = False

        c.print(f'success {url}-> ', success, color='yellow' )
        
        return success


    def stake_spread_top_valis(self):
        """
        This function calculates the stake spread for the top valis and assigns a key to each vali.
        """
        top_valis = self.top_valis()
        name2key = self.name2key()
        for vali in top_valis:
            key = name2key[vali]

    @classmethod
    def pull(cls, rpull:bool = False):
        """
        Pulls the latest changes from the remote repository and removes the library path if it contains less than 5 files.

        :param rpull: (bool) If True, recursively pulls the changes from all submodules. Default is False.
        :return: None
        """
        if len(cls.ls(cls.libpath)) < 5:
            c.rm(cls.libpath)
        c.pull(cwd=cls.libpath)
        if rpull:
            cls.rpull()

    def dashboard(self, **kwargs):
        """
        This function is a dashboard method that takes in keyword arguments and uses the streamlit library to write the output of the get_module method.
        """
        import streamlit as st
        return st.write(self.get_module())
    

    



Subspace.run(__name__)