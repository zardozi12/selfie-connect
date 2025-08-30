from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.models.image import Image
from app.models.album import Album, AlbumImage
from app.models.face import Face
from app.models.user import PersonCluster
from app.services.embeddings import image_embedding
import numpy as np


class AlbumService:
    """Service for automatic album generation and management"""
    
    @staticmethod
    async def create_location_albums(user_id: str) -> List[Album]:
        """Create albums based on location clustering"""
        # Get all images with location data
        images = await Image.filter(
            user_id=user_id,
            location_text__not_isnull=True
        ).all()
        
        # Group by location
        location_groups: Dict[str, List[Image]] = {}
        for img in images:
            location = img.location_text or "Unknown"
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(img)
        
        # Create albums for locations with multiple images
        created_albums = []
        for location, imgs in location_groups.items():
            if len(imgs) >= 2:  # Only create albums for locations with multiple images
                # Check if album already exists
                existing = await Album.filter(
                    user_id=user_id,
                    location_text=location,
                    is_auto_generated=True
                ).first()
                
                if not existing:
                    album = await Album.create(
                        user_id=user_id,
                        name=f"{location}",
                        description=f"Photos from {location}",
                        album_type="location",
                        location_text=location,
                        is_auto_generated=True,
                        cover_image=imgs[0] if imgs else None
                    )
                    
                    # Add images to album
                    for img in imgs:
                        await AlbumImage.create(album=album, image=img)
                    
                    created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def create_date_albums(user_id: str) -> List[Album]:
        """Create albums based on date clustering"""
        # Get all images with creation dates
        images = await Image.filter(user_id=user_id).order_by("created_at").all()
        
        if not images:
            return []
        
        # Group images by date ranges (within 7 days)
        date_groups: Dict[str, List[Image]] = {}
        current_group = []
        current_date = None
        
        for img in images:
            img_date = img.created_at.date()
            
            if current_date is None:
                current_date = img_date
                current_group = [img]
            elif (img_date - current_date).days <= 7:
                current_group.append(img)
            else:
                # Create album for previous group
                if len(current_group) >= 2:
                    group_key = f"{current_date} to {current_group[-1].created_at.date()}"
                    date_groups[group_key] = current_group.copy()
                
                current_date = img_date
                current_group = [img]
        
        # Handle last group
        if len(current_group) >= 2:
            group_key = f"{current_date} to {current_group[-1].created_at.date()}"
            date_groups[group_key] = current_group
        
        # Create albums
        created_albums = []
        for date_range, imgs in date_groups.items():
            # Check if album already exists
            existing = await Album.filter(
                user_id=user_id,
                name=date_range,
                is_auto_generated=True
            ).first()
            
            if not existing:
                album = await Album.create(
                    user_id=user_id,
                    name=date_range,
                    description=f"Photos from {date_range}",
                    album_type="date",
                    start_date=imgs[0].created_at.date(),
                    end_date=imgs[-1].created_at.date(),
                    is_auto_generated=True,
                    cover_image=imgs[0] if imgs else None
                )
                
                # Add images to album
                for img in imgs:
                    await AlbumImage.create(album=album, image=img)
                
                created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def cluster_faces_by_similarity(user_id: str, similarity_threshold: float = 0.85) -> List[PersonCluster]:
        """Cluster faces by similarity using embeddings"""
        # Get all faces for the user
        faces = await Face.filter(image__user_id=user_id).prefetch_related("image").all()
        
        if not faces:
            return []
        
        # Get face embeddings (we'll use the image embedding as a proxy for now)
        # In a real implementation, you'd extract face embeddings specifically
        face_embeddings = []
        face_data = []
        
        for face in faces:
            if face.image.embedding_json:
                face_embeddings.append(face.image.embedding_json)
                face_data.append(face)
        
        if not face_embeddings:
            return []
        
        # Simple clustering based on cosine similarity
        clusters = []
        used_faces = set()
        
        for i, embedding1 in enumerate(face_embeddings):
            if i in used_faces:
                continue
            
            # Start new cluster
            cluster_faces = [face_data[i]]
            used_faces.add(i)
            
            # Find similar faces
            for j, embedding2 in enumerate(face_embeddings):
                if j in used_faces or i == j:
                    continue
                
                # Calculate cosine similarity
                similarity = _cosine_similarity(embedding1, embedding2)
                if similarity >= similarity_threshold:
                    cluster_faces.append(face_data[j])
                    used_faces.add(j)
            
            # Create person cluster if we have multiple faces
            if len(cluster_faces) >= 2:
                cluster = await PersonCluster.create(
                    user_id=user_id,
                    label=f"Person {len(clusters) + 1}"
                )
                
                # Assign faces to cluster
                for face in cluster_faces:
                    face.cluster = cluster
                    await face.save()
                
                clusters.append(cluster)
        
        return clusters
    
    @staticmethod
    async def create_person_albums(user_id: str) -> List[Album]:
        """Create albums for each person cluster"""
        clusters = await PersonCluster.filter(user_id=user_id).prefetch_related("faces__image").all()
        
        created_albums = []
        for cluster in clusters:
            # Get unique images for this person
            images = list(set([face.image for face in cluster.faces]))
            
            if len(images) >= 2:
                # Check if album already exists
                existing = await Album.filter(
                    user_id=user_id,
                    person_cluster=cluster,
                    is_auto_generated=True
                ).first()
                
                if not existing:
                    album = await Album.create(
                        user_id=user_id,
                        name=f"{cluster.label}",
                        description=f"Photos of {cluster.label}",
                        album_type="person",
                        person_cluster=cluster,
                        is_auto_generated=True,
                        cover_image=images[0] if images else None
                    )
                    
                    # Add images to album
                    for img in images:
                        await AlbumImage.create(album=album, image=img)
                    
                    created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def auto_generate_all_albums(user_id: str) -> Dict[str, List[Album]]:
        """Generate all types of albums automatically"""
        results = {
            "location_albums": await AlbumService.create_location_albums(user_id),
            "date_albums": await AlbumService.create_date_albums(user_id),
            "person_clusters": await AlbumService.cluster_faces_by_similarity(user_id),
            "person_albums": []
        }
        
        # Create person albums after clustering
        results["person_albums"] = await AlbumService.create_person_albums(user_id)
        
        return results


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)
