import commune as c
from munch import Munch
from typing import Union, Optional
from commune import Module

class CLI(Module):
    """
    Create and init the CLI class, which handles the coldkey, hotkey and tao transfer 
    """
    # 

    def __init__(self, 
                 args = None,
                module = None, 
                new_event_loop: bool = True,
                save: bool = True):


        self.get_cli(args=args, 
                     module=module, 
                     new_event_loop=new_event_loop, 
                     save=save)



    def get_cli(
            self,
            args = None,
            module : Optional[Module] = None, # TODO revisit if this should be optional
            new_event_loop: bool = True,
            save: bool = True
        ) :
        self.base_module = c.Module() # This was declared as the base module yet not used anywhere else. having a non instantiated class as the module causes issues when using c.modulename as a function
        input = args or self.argv()
        args, kwargs = self.parse_args(input)
        
        if new_event_loop:
            self.base_module.new_event_loop(True) #using base module

        if len(args) == 0:
            return self.base_module.schema() #using base module
        

        base_module_attributes = list(set(self.base_module.functions()  + self.base_module.get_attributes()))
        # is it a fucntion, assume it is for the module
        # handle module/function
        is_fn = args[0] in base_module_attributes

        if '/' in args[0]:
            args = args[0].split('/') + args[1:]
            is_fn = False

        if is_fn: #I do not understand what is going on here. You are declaring it the base module which is the module, but you are giving it a default value of the uninstantiated module class. 
            # is a function
            module = self.base_module or Module 
            fn = args.pop(0)
        else:
            module = args.pop(0)
            if isinstance(module, str):
                module = self.base_module or Module # TODO revisit.
            fn = args.pop(0)
            
        fn_obj = getattr(module, fn)
        
        if callable(fn_obj) :
            if self.base_module.classify_fn(fn_obj) == 'self': #using base module
                fn_obj = getattr(Module(), fn)
            output = fn_obj(*args, **kwargs)
        elif self.base_module.is_property(fn_obj):
            output =  getattr(Module(), fn)
        else: 
            output = fn_obj  
        if callable(fn):
            output = fn(*args, **kwargs)
        self.process_output(output, save=save)

    def process_output(self, output, save=True, verbose=True):
        if save:
            self.save_history(input, output)
        if self.base_module.is_generator(output):
            for output_item in output:
                if isinstance(c, Munch):
                    output_item = output_item.toDict()
                self.base_module.print(output_item,  verbose=verbose)#using base module
        else:
            if isinstance(output, Munch):
                output = output.toDict()
            self.base_module.print(output, verbose=verbose) #using base module

    def save_history(self, input, output):
        try:
            self.put(f'cli_history/{int(self.base_module.time())}', {'input': input, 'output': output})
        except Exception as e:
            pass
        return {'input': input, 'output': output}
    @classmethod
    def history_paths(cls, n=10):
        return cls.ls('cli_history')[:n]
    
    @classmethod
    def history(cls, n=10):
        history_paths = cls.history_paths(n=n)
        historys = [Module.get_json(s) for s in history_paths] #need to make this Module if we are adjusting the class method
        return historys
    
    @classmethod
    def num_points(cls):
        return len(cls.history_paths())
    
    @classmethod
    def n_history(cls):
        return len(cls.history_paths())

    
    @classmethod
    def clear(cls):
        return cls.rm('cli_history')


        
    @classmethod
    def parse_args(cls, argv = None):
        if argv is None:
            argv = cls.argv()

        args = []
        kwargs = {}
        parsing_kwargs = False
        for arg in argv:
            # TODO fix exception with  "="
            # if any([arg.startswith(_) for _ in ['"', "'"]]):
            #     assert parsing_kwargs is False, 'Cannot mix positional and keyword arguments'
            #     args.append(cls.determine_type(arg))
            if '=' in arg:
                parsing_kwargs = True
                key, value = arg.split('=', 1)
                # use determine_type to convert the value to its actual type
                
                kwargs[key] = cls.determine_type(value)
            else:
                assert parsing_kwargs is False, 'Cannot mix positional and keyword arguments'
                args.append(cls.determine_type(arg))

        return args, kwargs

    @classmethod
    def determine_type(cls, x):
        if x.lower() == 'null' or x == 'None':
            return None
        elif x.lower() in ['true', 'false']:
            return bool(x.lower() == 'true')
        elif x.startswith('[') and x.endswith(']'):
            # this is a list
            try:
                
                list_items = x[1:-1].split(',')
                # try to convert each item to its actual type
                x =  [cls.determine_type(item.strip()) for item in list_items]
                if len(x) == 1 and x[0] == '':
                    x = []
                return x
       
            except:
                # if conversion fails, return as string
                return x
        elif x.startswith('{') and x.endswith('}'):
            # this is a dictionary
            if len(x) == 2:
                return {}
            try:
                dict_items = x[1:-1].split(',')
                # try to convert each item to a key-value pair
                return {key.strip(): cls.determine_type(value.strip()) for key, value in [item.split(':', 1) for item in dict_items]}
            except:
                # if conversion fails, return as string
                return x
        else:
            # try to convert to int or float, otherwise return as string
            try:
                return int(x)
            except ValueError:
                try:
                    return float(x)
                except ValueError:
                    return x
