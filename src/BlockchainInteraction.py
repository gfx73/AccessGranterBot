from web3 import Web3
import os
from dotenv import load_dotenv
from eth_account.messages import encode_defunct
import json

load_dotenv()
endpoint = os.getenv('ENDPOINT')
w3 = Web3(Web3.HTTPProvider(endpoint))
private_key = os.getenv('PRIVATE_KEY')


with open('../assets/generator_abi.json', 'r') as f:
    generator_contract_abi = json.load(f)
generator_contract = w3.eth.contract('0x543De2524B1EC32aA44c277C582c807034e8D740', abi=generator_contract_abi)


def sign(group_id: int):
    hex_message = Web3.solidityKeccak(['int256'], [group_id])
    message = encode_defunct(primitive=hex_message)
    signed_message = w3.eth.account.sign_message(message, private_key=private_key)
    return signed_message.signature.hex()


def get_shop_address(group_id: int):
    return generator_contract.functions.getShopOfGroup(group_id).call()


def get_shop_contract(group_id: int):
    contract_address = get_shop_address(group_id)
    with open('../assets/shop_abi.json', 'r') as f:
        abi = json.load(f)
    contract = w3.eth.contract(contract_address, abi=abi)
    return contract


def get_shop_info(group_id: int):
    shop_address = generator_contract.functions.getShopOfGroup(group_id).call()
    contract = get_shop_contract(group_id)
    manager_address = contract.functions.manager().call()
    price = contract.functions.price().call()
    max_accesses = contract.functions.maxAccesses().call()
    released_accesses = contract.functions.releasedAccesses().call()
    request_access_link = contract.functions.requestAccessLink().call()
    return {
        'Shop address': shop_address,
        'Manager address': manager_address,
        'Price': price,
        'Max accesses': max_accesses,
        'Released accesses': released_accesses,
        'Request access link': request_access_link
    }


def has_available_place(group_id: int):
    contract = get_shop_contract(group_id)
    max_accesses = contract.functions.maxAccesses().call()
    if max_accesses == 0:
        return True
    released_accesses = contract.functions.releasedAccesses().call()
    return max_accesses - released_accesses > 0


def did_user_buy(group_id: int, user_id: int):
    contract = get_shop_contract(group_id)
    return contract.functions.didUserBuyGetter(user_id).call()
