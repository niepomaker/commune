from commune import Module 


c = Module()


# Keys dict
keys = {
    "vali": "5FcKL8ZKHW9h1cNTw1DyZ9PC9u5WFYLKqCwhHYsDvtmvF4xJ",
    "vali::agentartificial": "5G4VmeAD23Kj2K9eTcvd5eBHx1Cwssj7rnhoY8KaBBKspjTT",
    "none1": "5CPoqeTvAdiyoEUYWrs3qBGdCVgnxEnoFtYxMg8KFqnTyVZf",
    "razor": "5F6fGvNACrwmEkkygAcyCqeou126TeYdd9Z5NNJpKcwRhiqe",
    "razor-dev-key": "5GFAqW58Tp1anmQZofSiXcjPkaMBcSyYxs3LHcqaPFxCbF2Y",
    "module::test": "5HizepgsAH5CSkPUHPoiYYkEJBxT5No5WExJtRzpf6Bxm3Ny",
    "module": "5DFztJFTafuDHRTuBGeKpuAdmjqCFPp4NcviZUAZ452hZEuJ",
    "demo": "5ELFAqGeUc3RVHH6ZsUSv2apcAwaHtLdcCVXusqSZBvpVrzx",
}


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


#Key the balance of keys in the keys dict
def balance(key):
    return key, c.balance(keys[key])


if __name__ == "__main__":
    #status()
    print(balances())
    