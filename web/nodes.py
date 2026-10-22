from anytree import NodeMixin
from html import escape
from os import environ

DOWNLOAD_DIR = environ.get("DOWNLOAD_DIR", "/usr/src/app/downloads/")
if not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR += "/"


class TorNode(NodeMixin):
    def __init__(
        self,
        name,
        is_folder=False,
        is_file=False,
        parent=None,
        size=None,
        priority=None,
        file_id=None,
        progress=None,
    ):
        super().__init__()
        self.name = name
        self.is_folder = is_folder
        self.is_file = is_file

        if parent is not None:
            self.parent = parent
        if size is not None:
            self.fsize = size
        if priority is not None:
            self.priority = priority
        if file_id is not None:
            self.file_id = file_id
        if progress is not None:
            self.progress = progress


def qb_get_folders(path):
    return path.split("/")


def get_folders(path):
    prefix = DOWNLOAD_DIR.rstrip("/") + "/"
    is_download_path = path.startswith(prefix)
    relative_path = path[len(prefix) :] if is_download_path else path
    parts = [part for part in relative_path.split("/") if part]
    # Aria2 paths include the per-task numeric directory; the selector UI
    # should show the torrent's content, not that implementation detail.
    if is_download_path and parts and parts[0].isdigit():
        parts.pop(0)
    return parts


def make_tree(res, aria2=False):
    parent = TorNode("Torrent")
    if not aria2:
        for i in res:
            folders = qb_get_folders(i.name)
            if len(folders) > 1:
                previous_node = parent
                for j in range(len(folders) - 1):
                    current_node = next(
                        (k for k in previous_node.children if k.name == folders[j]),
                        None,
                    )
                    if current_node is None:
                        previous_node = TorNode(
                            folders[j], parent=previous_node, is_folder=True
                        )
                    else:
                        previous_node = current_node
                TorNode(
                    folders[-1],
                    is_file=True,
                    parent=previous_node,
                    size=i.size,
                    priority=i.priority,
                    file_id=i.id,
                    progress=round(i.progress * 100, 2),
                )
            else:
                TorNode(
                    folders[-1],
                    is_file=True,
                    parent=parent,
                    size=i.size,
                    priority=i.priority,
                    file_id=i.id,
                    progress=round(i.progress * 100, 2),
                )
    else:
        for i in res:
            folders = get_folders(i["path"])
            priority = 1
            if i["selected"] == "false":
                priority = 0
            length = int(i["length"])
            progress = (
                round((int(i["completedLength"]) / length) * 100, 2) if length else 0
            )
            if len(folders) > 1:
                previous_node = parent
                for j in range(len(folders) - 1):
                    current_node = next(
                        (k for k in previous_node.children if k.name == folders[j]),
                        None,
                    )
                    if current_node is None:
                        previous_node = TorNode(
                            folders[j], parent=previous_node, is_folder=True
                        )
                    else:
                        previous_node = current_node
                TorNode(
                    folders[-1],
                    is_file=True,
                    parent=previous_node,
                    size=length,
                    priority=priority,
                    file_id=i["index"],
                    progress=progress,
                )
            else:
                TorNode(
                    folders[-1],
                    is_file=True,
                    parent=parent,
                    size=length,
                    priority=priority,
                    file_id=i["index"],
                    progress=progress,
                )
    return create_list(parent, ["", 0])


def create_list(par, msg):
    if par.name != ".unwanted":
        msg[0] += "<ul>"
    for i in par.children:
        if i.is_folder:
            msg[0] += "<li>"
            if i.name != ".unwanted":
                folder_id = f"foldernode_{msg[1]}"
                folder_name = escape(str(i.name), quote=True)
                msg[0] += (
                    f'<input type="checkbox" id="{folder_id}" name="{folder_id}"> '
                    f'<label for="{folder_id}">{folder_name}</label>'
                )
            create_list(i, msg)
            msg[0] += "</li>"
            msg[1] += 1
        else:
            msg[0] += "<li>"
            file_id = escape(str(i.file_id), quote=True)
            file_size = escape(str(i.fsize), quote=True)
            file_name = escape(str(i.name))
            checked = " checked" if i.priority != 0 else ""
            msg[0] += (
                f'<input type="checkbox"{checked} name="filenode_{file_id}" '
                f'data-size="{file_size}"> '
                f'<label data-size="{file_size}" for="filenode_{file_id}">{file_name}</label> '
                f"/ {escape(str(i.progress))}%"
            )
            msg[0] += f'<input type="hidden" value="off" name="filenode_{file_id}">'
            msg[0] += "</li>"

    if par.name != ".unwanted":
        msg[0] += "</ul>"
    return msg
