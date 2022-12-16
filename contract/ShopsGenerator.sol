// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract AccessShop {
    address public constant approver =
    0x46511aa6A3151E86367f645DFa374875955f4aFe;
    address payable public manager;
    int256 public groupId;
    string public requestAccessLink;

    // setting maxAccesses to zero will make the number of accesses unbound
    uint256 public maxAccesses;
    uint256 public releasedAccesses;
    mapping(uint256 => bool) didUserBuy;

    // price to join chat in wei
    uint256 public price;

    constructor(
        address payable managerAddressArg,
        int256 groupIdArg,
        string memory linkArg,
        bytes memory sig,
        uint256 priceArg,
        uint256 maxAccessesArg
    ) isSigned(sig, groupIdArg) {
        manager = managerAddressArg;
        groupId = groupIdArg;
        requestAccessLink = linkArg;
        price = priceArg;
        maxAccesses = maxAccessesArg;
    }

    // buying access
    function buyAccess(uint256 userId) public payable {
        require(msg.value >= price, "Not enough paid");
        require(
            maxAccesses > releasedAccesses || maxAccesses == 0,
            "The maximum number of granted accesses is reached"
        );
        releasedAccesses += 1;
        didUserBuy[userId] = true;
        manager.transfer(msg.value);
    }

    function increaseMaxAccesses(uint256 increaseVal) public {
        require(msg.sender == manager, "Only manager can access this function");
        maxAccesses += increaseVal;
    }

    function setMaxAccesses(uint256 maxAccessesArg) public {
        require(msg.sender == manager, "Only manager can access this function");
        maxAccesses = maxAccessesArg;
    }

    // to check if user bought an access
    function didUserBuyGetter(uint256 userId) public view returns (bool) {
        return didUserBuy[userId];
    }

    // helper function to split signature
    function splitSignature(bytes memory sig)
    private
    pure
    returns (
        bytes32 r,
        bytes32 s,
        uint8 v
    )
    {
        require(sig.length == 65, "invalid signature length");

        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
    }

    // getting signer
    function checkSignature(bytes memory sig, int256 groupIdArg)
    private
    pure
    returns (address)
    {
        bytes memory groupIdBytes = abi.encodePacked(groupIdArg);
        bytes32 hashMsg = keccak256(bytes(groupIdBytes));
        bytes32 hashFinal = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", hashMsg)
        );

        (bytes32 r, bytes32 s, uint8 v) = splitSignature(sig);
        return ecrecover(hashFinal, v, r, s);
    }

    // verifying that groupIdArg was signed by approver
    modifier isSigned(bytes memory sig, int256 groupIdArg) {
        address signer = checkSignature(sig, groupIdArg);
        require(signer == approver, "Not signed");
        _;
    }
}

// main contract through which contracts for each group is created
contract ShopsGenerator {
    // stores the address of shop contract for group_id
    mapping(int256 => AccessShop) shopOfGroup;

    function createAccessShop(
        int256 groupIdArg,
        string memory linkArg,
        bytes memory sig,
        uint256 priceArg,
        uint256 maxAccessesArg
    ) public returns (AccessShop) {
        require(
            address(shopOfGroup[groupIdArg]) == address(0),
            "Shop for this group already exists"
        );
        AccessShop shop = new AccessShop(
            payable(msg.sender),
            groupIdArg,
            linkArg,
            sig,
            priceArg,
            maxAccessesArg
        );
        shopOfGroup[groupIdArg] = shop;
        return shop;
    }

    // getter
    function getShopOfGroup(int256 groupId) public view returns (AccessShop) {
        return shopOfGroup[groupId];
    }
}
