import os
import re
import shutil
from pathlib import Path
from aiida.orm import Node
from aiida.repository import FileType

def copy_between_nodes(name: str,
                       source: str,
                       node: Node,
                       dst: Node,
                       exclude=None):

    # For check the regex the first thing because this function will be called recursively
    if exclude and re.match(exclude, name):
        return
    obj = node.get_object(f"{source}/{name}")
    # If it is a directory, copy the contents one by one
    if obj.file_type == FileType.DIRECTORY:
        for sub_obj in node.list_objects(f"{source}/{name}"):
            copy_between_nodes(os.path.join(f"{name}", sub_obj.name), source, node, dst, exclude=exclude)
    else:
        # It is a file
        with node.open(f"{source}/{name}", mode='rb') as fsource:
            # Write the file
            dst.put_object_from_filelike(fsource, str(name), mode = "wb")

def copy_to_file(name: str,
                 source: str,
                 node: Node,
                 dst: Path,
                 exclude=None):
    # For check the regex the first thing because this function will be called recursively
    if exclude and re.match(exclude, name):
        return
    obj = node.get_object(f"{source}/{name}")
    # If it is a directory, copy the contents one by one
    if obj.file_type == FileType.DIRECTORY:
        for sub_obj in node.list_objects(f"{source}/{name}"):
            copy_to_file(os.path.join(f"{name}", sub_obj.name), source, node, dst, exclude=exclude)
    else:
        # It is a file
        with node.open(f"{source}/{name}", mode='rb') as fsource:
            # Make parent directory if needed
            frepo_path = dst / name
            Path(frepo_path.parent).mkdir(exist_ok=True, parents=True)
            # Write the file
            with open(frepo_path, 'wb') as fdst:
                shutil.copyfileobj(fsource, fdst)
