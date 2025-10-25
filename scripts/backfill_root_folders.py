from tortoise import run_async
from app.models.user import User
from app.models.folder import Folder
from app.models.photo import Photo

async def main():
    users = await User.all()
    for user in users:
      
        root_folder = await Folder.get_or_create(
            user=user,
            parent=None,
            defaults={
                'name': 'Root',
                'encrypted_fek': '' 
            }
        )
       
        await Photo.filter(user=user).update(folder=root_folder)

if __name__ == '__main__':
    run_async(main())