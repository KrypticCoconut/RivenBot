import os

def create_dir_path(path):
    path = os.path.dirname(path)
    os.makedirs(path)
    
