from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.models.image import Image
from app.models.album import Album, AlbumImage
from app.models.face import Face
from app.models.user import PersonCluster
from app.services.embeddings import image_embedding
import numpy as np


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


def _short_id(uuid_val) -> str:
    """Generate short human-friendly ID from UUID"""
    return str(uuid_val).split("-")[0].upper()


class AlbumService:
    """Service for automatic album generation and management"""
    
    @staticmethod
    async def create_location_albums(user_id: str) -> List[Album]:
        """Create albums based on location clustering"""
        images = await Image.filter(
            user_id=user_id,
            location_text__not_isnull=True
        ).all()
        
        location_groups: Dict[str, List[Image]] = {}
        for img in images:
            location = img.location_text or "Unknown"
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(img)
        
        created_albums = []
        for location, imgs in location_groups.items():
            if len(imgs) >= 2:
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
                    
                    for img in imgs:
                        await AlbumImage.create(album=album, image=img)
                    
                    created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def create_date_albums(user_id: str) -> List[Album]:
        """Create albums based on date clustering"""
        images = await Image.filter(user_id=user_id).order_by("created_at").all()
        
        if not images:
            return []
        
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
                if len(current_group) >= 1:
                    group_key = f"{current_date} to {current_group[-1].created_at.date()}"
                    date_groups[group_key] = current_group.copy()
                
                current_date = img_date
                current_group = [img]
        
        if len(current_group) >= 1:
            group_key = f"{current_date} to {current_group[-1].created_at.date()}"
            date_groups[group_key] = current_group
        
        created_albums = []
        for date_range, imgs in date_groups.items():
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
                
                for img in imgs:
                    await AlbumImage.create(album=album, image=img)
                
                created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def cluster_faces_by_similarity(user_id: str, similarity_threshold: float = 0.85) -> List[PersonCluster]:
        """Cluster faces by similarity using embeddings"""
        faces = await Face.filter(image__user_id=user_id).prefetch_related("image").all()
        
        if not faces:
            return []
        
        face_embeddings = []
        face_data = []
        
        for face in faces:
            # Use per-face embeddings (not image-level)
            if face.embedding_json:
                face_embeddings.append(face.embedding_json)
                face_data.append(face)
        
        if not face_embeddings:
            return []
        
        clusters = []
        used_faces = set()
        
        for i, embedding1 in enumerate(face_embeddings):
            if i in used_faces:
                continue
            
            cluster_faces = [face_data[i]]
            used_faces.add(i)
            
            for j, embedding2 in enumerate(face_embeddings):
                if j in used_faces or i == j:
                    continue
                
                similarity = _cosine_similarity(embedding1, embedding2)
                if similarity >= similarity_threshold:
                    cluster_faces.append(face_data[j])
                    used_faces.add(j)
            
            if len(cluster_faces) >= 2:
                cluster = await PersonCluster.create(
                    user_id=user_id,
                    label=f"Person {len(clusters) + 1}"
                )
                
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
            images = list(set([face.image for face in cluster.faces]))
            
            if len(images) >= 2:
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
        
        results["person_albums"] = await AlbumService.create_person_albums(user_id)
        
        return results

    @staticmethod
    async def create_top_n_person_albums(user_id: str, top_n: int = 10) -> List[Album]:
        """
        Pick top-N clusters by number of images and create 'person' albums
        named like 'Person-<SHORTID>'. Skip if album exists.
        Move encrypted files into person-specific folders.
        """
        from app.services.deta_storage import storage
        import asyncio
        
        clusters = await PersonCluster.filter(user_id=user_id).prefetch_related("faces__image").all()
        if not clusters:
            return []

        clist = []
        for c in clusters:
            imgs = list({f.image for f in c.faces if f.image is not None})
            clist.append((c, imgs))

        clist.sort(key=lambda t: len(t[1]), reverse=True)
        top = clist[:top_n]

        created = []
        for idx, (cluster, images) in enumerate(top, start=1):
            short = _short_id(cluster.id)
            folder_name = f"person-{short}"
            name = f"Person-{short}"
            existing = await Album.filter(user_id=user_id, name=name, album_type="person").first()
            if existing:
                continue
            album = await Album.create(
                user_id=user_id,
                name=name,
                description=f"Auto person folder for cluster {cluster.id}",
                album_type="person",
                person_cluster=cluster,
                is_auto_generated=True,
                cover_image=images[0] if images else None,
            )
            for img in images:
                await AlbumImage.create(album=album, image=img)
                try:
                    if asyncio.iscoroutinefunction(storage.move_to_folder):
                        new_key = await storage.move_to_folder(img.storage_key, folder_name)
                    else:
                        new_key = storage.move_to_folder(img.storage_key, folder_name)
                    img.storage_key = new_key
                    await img.save()
                except Exception:
                    pass
            created.append(album)
        return created