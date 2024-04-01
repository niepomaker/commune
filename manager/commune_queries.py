from commune.module import Module

c = Module()

#Key the balance of keys in the keys dict
def get_free_balance(keyname, keys):
    return keyname, c.balance(keys[keyname])



if __name__ == "__main__":
    keys = {"test": '5F4c6WjExFshz3QQ4U6xtEXqUyPFV2P66Z5ZBQpvSyCFnuHE'}
    keyname = "test"
    print(get_free_balance(keyname, keys))