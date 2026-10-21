import hashlib

# Base58 character map
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode(b: bytes) -> str:
    """Encodes a byte string into Base58 format."""
    n = int.from_bytes(b, 'big')
    res = []
    while n > 0:
        n, r = divmod(n, 58)
        res.append(BASE58_ALPHABET[r])
    for byte in b:
        if byte == 0:
            res.append(BASE58_ALPHABET[0])
        else:
            break
    return ''.join(reversed(res))

def generate_unspendable_ltc(vanity_text: str) -> str:
    """
    Generates a valid Base58Check Litecoin legacy address from arbitrary text.
    Addresses generated this way have no known private key (unspendable burn outputs).
    """
    # 1. Mainnet Litecoin P2PKH prefix = 0x30 (yields 'L' addresses)
    prefix = b'\x30'
    
    # 2. Pad or truncate payload to 20 bytes (standard RIPEMD-160 hash size)
    raw_bytes = vanity_text.encode('utf-8')
    if len(raw_bytes) < 20:
        # Right pad with zeros to hit exact 20-byte payload length
        payload = raw_bytes.ljust(20, b'\x00')
    else:
        payload = raw_bytes[:20]
        
    version_payload = prefix + payload
    
    # 3. Double SHA-256 for Base58Check checksum calculation
    checksum = hashlib.sha256(hashlib.sha256(version_payload).digest()).digest()[:4]
    
    # 4. Final Base58 encoding
    full_payload = version_payload + checksum
    return base58_encode(full_payload)

if __name__ == "__main__":
    # Custom parameter target
    vanity_string = "LLxGemini"
    address = generate_unspendable_ltc(vanity_string)
    
    print(f"Target String    : {vanity_string}")
    print(f"Unspendable LTC  : {address}")
