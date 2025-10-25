"""
Duplicate detection service using perceptual hashing (pHash)
Detects near-duplicate images using Hamming distance
"""


def is_near_duplicate(phash_hex_a: str, phash_hex_b: str, threshold: int = 8) -> bool:
    """
    Check if two perceptual hashes represent near-duplicate images.
    
    Args:
        phash_hex_a: First image's pHash as hex string
        phash_hex_b: Second image's pHash as hex string  
        threshold: Maximum Hamming distance to consider as duplicate (default: 8)
    
    Returns:
        True if images are considered near-duplicates
    """
    if not phash_hex_a or not phash_hex_b:
        return False
    
    try:
        # Convert hex strings to integers
        a, b = int(phash_hex_a, 16), int(phash_hex_b, 16)
        
        # Calculate Hamming distance (number of different bits)
        hamming_distance = (a ^ b).bit_count()
        
        return hamming_distance <= threshold
        
    except (ValueError, TypeError):
        # If conversion fails, assume not duplicate
        return False


def calculate_hamming_distance(phash_hex_a: str, phash_hex_b: str) -> int:
    """
    Calculate the exact Hamming distance between two pHash values.
    
    Args:
        phash_hex_a: First image's pHash as hex string
        phash_hex_b: Second image's pHash as hex string
    
    Returns:
        Hamming distance (number of different bits)
    """
    if not phash_hex_a or not phash_hex_b:
        return 64  # Maximum possible distance for 64-bit hash
    
    try:
        a, b = int(phash_hex_a, 16), int(phash_hex_b, 16)
        return (a ^ b).bit_count()
    except (ValueError, TypeError):
        return 64
