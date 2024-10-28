import os
import shutil

def merge_directories(src, dest):
    # Ensure the destination directory exists
    os.makedirs(dest, exist_ok=True)
    
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dest_item = os.path.join(dest, item)
        
        if os.path.isdir(src_item):
            merge_directories(src_item, dest_item)
        else:
            # If it's a file, move it and overwrite if it exists
            if os.path.exists(dest_item):
                os.remove(dest_item)
            shutil.move(src_item, dest_item)

def move_res_folders_to_resources(root_dir):
    # Create the destination folder
    resources_dir = os.path.join(root_dir, 'resources')
    os.makedirs(resources_dir, exist_ok=True)
    
    # Walk through the directory tree
    for root, dirs, files in os.walk(root_dir):
        for dir_name in dirs:
            if dir_name.startswith('res_normal') or dir_name.startswith('res_global'):
                source_dir = os.path.join(root, dir_name)
                
                # Move the contents of the source directory to the resources directory
                merge_directories(source_dir, resources_dir)
                
                # After moving, remove the empty original directory
                shutil.rmtree(source_dir)

if __name__ == "__main__":
    root_directory = r'B:\SteamLibrary\steamapps\common\Once Human'
    move_res_folders_to_resources(root_directory)
