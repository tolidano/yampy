import os
import socket
import stat
from typing import List

""" Make this go away by a simple https://python-for-system-administrators.readthedocs.io/en/latest/ssh.html """
import paramiko

class SFTP:
    """ Heavily based on https://github.com/AlexOrlek/sftp_py """
    TIMEOUT: int = 5

    def __init__(
        self,
        host: str,
        username: str,
        port: int = 22,
        key: str = None,
        key_passphrase: str = None,
        password: str = None,
        downloaded_files: List[str] = None,
    ):
        self.host = host
        self.username = username
        self.port = port
        self.key = key
        self.key_passphrase = key_passphrase
        self.password = password
        self.downloaded_files = downloaded_files

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.key is not None:
                self.key = paramiko.RSAKey.from_private_key_file(self.key)
            self.client.connect(
                hostname=self.host,
                username=self.username,
                port=self.port,
                password=self.password,
                pkey=self.key,
                passphrase=self.key_passphrase,
                timeout=self.TIMEOUT,
            )
            self.sftp_client = self.client.open_sftp()
        except Exception as e:
            if isinstance(e, paramiko.SSHException):
                print("Could not establish SSH connection: %s" % e)
            elif isinstance(e, socket.timeout):
                print("Connection timed out")
            else:
                print("Error connecting to remote: " + repr(e))
            self.close()

    def list_remote_dir(self, remote_path: str, show_hidden: bool = True) -> List[str]:
        try:
            dir_contents = self.sftp_client.listdir(remote_path)
            if not show_hidden:
                dir_contents = [i for i in dir_contents if not i.startswith(".")]
            return dir_contents
        except Exception as e:
            if isinstance(e, IOError):
                print("%s is an invalid directory path" % remote_path)
            else:
                print("Error listing remote directory contents: " + repr(e))
            self.close()

    def remote_download(
        self,
        remote_path: str,
        local_path: str,
        copy_hidden_files: bool = True,
        copy_symlink_files: bool = True,
        remove: bool = False,
    ) -> int:
        self.downloaded_files = []
        file_counter: int = 0
        try:
            if self.client is None or self.sftp_client is None:
                self.close()
                return
            if not os.path.isdir(local_path):
                self.close()
                return
            if self.remote_isdir(remote_path):
                dir_contents: List[str] = self.list_remote_dir(remote_path)
                if not copy_hidden_files:
                    dir_contents = [i for i in dir_contents if not i.startswith(".")]
                for indx, item in enumerate(dir_contents):
                    if indx == 0:
                        linux_path = "/".join([remote_path, item])
                        try:
                            _ = self.sftp_client.lstat(linux_path)
                            path_sep = "/"
                        except Exception:
                            path_sep = "\\"
                    _remote_path = path_sep.join([remote_path, item])
                    _local_path = os.path.join(local_path, item)
                    download_bool: bool = self.remote_isfile(_remote_path)
                    if (
                        copy_symlink_files
                        and not download_bool
                        and self.remote_islink(_remote_path)
                    ):
                        try:
                            download_bool = self.remote_isfile(
                                self.sftp_client.normalize(_remote_path)
                            )
                        except Exception:
                            pass
                    if download_bool:
                        self.sftp_client.get(_remote_path, _local_path)
                        self.downloaded_files.append(_remote_path)
                        file_counter += 1
            else:
                try:
                    _remote_path = self.sftp_client.normalize(remote_path)
                    if self.remote_isfile(_remote_path):
                        _local_path = os.path.join(
                            local_path, os.path.split(remote_path)[-1]
                        )
                        self.sftp_client.get(remote_path, _local_path)
                        self.downloaded_files.append(remote_path)
                        file_counter += 1
                except Exception:
                    pass
            if remove:
                self.remove_downloaded()
        except Exception:
            self.close()
        return file_counter

    def remote_upload(
        self,
        remote_path: str,
        local_path: str,
        copy_hidden_files: bool = True,
        copy_symlink_files: bool = True,
        remove: bool = False,
    ):
        self.uploaded_files = []
        try:
            if self.client is None or self.sftp_client is None:
                self.close()
                return
            if not self.remote_isdir(remote_path):
                self.close()
                return
            if os.path.isdir(local_path):
                file_counter: int = 0
                dir_contents = os.listdir(local_path)
                if not copy_hidden_files:
                    dir_contents = [i for i in dir_contents if not i.startswith(".")]
                for indx, item in enumerate(dir_contents):
                    _remote_path_linux = "/".join([remote_path, item])
                    _remote_path_windows = "\\".join([remote_path, item])
                    _local_path = os.path.join(local_path, item)
                    if not copy_symlink_files and os.path.islink(_local_path):
                        continue
                    try:
                        self.sftp_client.put(_local_path, _remote_path_linux)
                        self.uploaded_files.append(_local_path)
                        file_counter += 1
                    except Exception:
                        self.sftp_client.put(_local_path, _remote_path_windows)
                        self.uploaded_files.append(_local_path)
                        file_counter += 1
            elif os.path.isfile(local_path):
                _local_file = os.path.split(local_path)[-1]
                linux_path = "/".join([remote_path, _local_file])
                try:
                    _ = self.sftp_client.lstat(linux_path)
                    path_sep = "/"
                except Exception:
                    path_sep = "\\"
                _remote_path = path_sep.join([remote_path, _local_file])
                self.sftp_client.put(local_path, _remote_path)
                self.uploaded_files.append(local_path)
            if remove:
                self.remove_uploaded()
        except Exception:
            self.close()

    def remove_downloaded(self):
        for item in self.downloaded_files:
            self.sftp_client.remove(item)
        self.downloaded_files = []

    def remove_uploaded(self):
        for item in self.uploaded_files:
            os.remove(item)
        self.uploaded_files = []

    def remote_isdir(self, remote_path: str) -> bool:
        fileattr = self.sftp_client.lstat(remote_path)
        return stat.S_ISDIR(fileattr.st_mode)

    def remote_isfile(self, remote_path) -> bool:
        fileattr = self.sftp_client.lstat(remote_path)
        return stat.S_ISREG(fileattr.st_mode)

    def remote_islink(self, remote_path) -> bool:
        fileattr = self.sftp_client.lstat(remote_path)
        return stat.S_ISLNK(fileattr.st_mode)

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
        if self.sftp_client is not None:
            self.sftp_client.close()
            self.sftp_client = None
