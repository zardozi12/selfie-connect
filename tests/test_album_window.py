# tests/test_album_window.py
"""Test deterministic album windowing logic"""

import datetime as dt
import pytest
import hashlib
from app.services.album_service import AlbumService
from app.models.image import Image
from app.models.user import User


@pytest.mark.asyncio
async def test_7day_window_grouping(db_setup):
    """Test that 7-day windows group images correctly"""
    # Create test user
    u = await User.create(
        email="test@test.com", 
        password_hash="test_hash",
        dek_encrypted_b64="test_dek"
    )
    
    # Create images at specific dates: D0, D3, D7, D12
    base = dt.datetime(2025, 3, 1, 12, 0, 0)
    
    d0 = await Image.create(
        user=u, 
        created_at=base,
        storage_key="test_key_0",
        original_filename="img0.jpg",
        checksum_sha256=hashlib.sha256(b"test_key_0").hexdigest(),
    )
    d3 = await Image.create(
        user=u, 
        created_at=base + dt.timedelta(days=3),
        storage_key="test_key_3", 
        original_filename="img3.jpg",
        checksum_sha256=hashlib.sha256(b"test_key_3").hexdigest(),
    )
    d7 = await Image.create(
        user=u, 
        created_at=base + dt.timedelta(days=7),
        storage_key="test_key_7",
        original_filename="img7.jpg",
        checksum_sha256=hashlib.sha256(b"test_key_7").hexdigest(),
    )
    d12 = await Image.create(
        user=u, 
        created_at=base + dt.timedelta(days=12),
        storage_key="test_key_12",
        original_filename="img12.jpg",
        checksum_sha256=hashlib.sha256(b"test_key_12").hexdigest(),
    )

    # Create albums using the service
    res = await AlbumService.create_date_albums(str(u.id))
    names = [a.name for a in res]
    
    # Should have at least one album
    assert len(res) >= 1
    
    # First album should contain d0, d3, d7 (within 7 days)
    # Second album should start at d12
    first_album_images = []
    second_album_images = []
    
    for album in res:
        album_images = await album.images.all()
        image_ids = [str(img.id) for img in album_images]
        
        if str(d0.id) in image_ids:
            first_album_images = image_ids
        elif str(d12.id) in image_ids:
            second_album_images = image_ids
    
    # Verify grouping logic
    assert str(d0.id) in first_album_images
    assert str(d3.id) in first_album_images  
    assert str(d7.id) in first_album_images
    assert str(d12.id) in second_album_images
    
    # Clean up
    await d0.delete()
    await d3.delete() 
    await d7.delete()
    await d12.delete()
    for album in res:
        await album.delete()
    await u.delete()


@pytest.mark.asyncio
async def test_window_boundary_behavior(db_setup):
    """Test edge cases around 7-day boundary"""
    u = await User.create(
        email="boundary@test.com",
        password_hash="test_hash", 
        dek_encrypted_b64="test_dek"
    )
    
    base = dt.datetime(2025, 3, 1, 12, 0, 0)
    
    # Images exactly 7 days apart
    img1 = await Image.create(
        user=u,
        created_at=base,
        storage_key="test_key_1",
        original_filename="img1.jpg",
        checksum_sha256=hashlib.sha256(b"test_key_1").hexdigest(),
    )
    img2 = await Image.create(
        user=u, 
        created_at=base + dt.timedelta(days=7),
        storage_key="test_key_2",
        original_filename="img2.jpg",
        checksum_sha256=hashlib.sha256(b"test_key_2").hexdigest(),
    )
    
    res = await AlbumService.create_date_albums(str(u.id))
    
    # Should create one album with both images (7 days inclusive)
    assert len(res) == 1
    album_images = await res[0].images.all()
    assert len(album_images) == 2
    
    # Clean up
    await img1.delete()
    await img2.delete()
    await res[0].delete()
    await u.delete()
