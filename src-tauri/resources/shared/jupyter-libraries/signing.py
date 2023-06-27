# Standard library imports
import base64
import os
import platform
import shutil
import stat
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import NamedTuple

import ipywidgets as widgets
import keyring
import requests
import tomli
import tomli_w
from IPython.display import HTML, display
from ipywidgets import interact
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


class Config:
    """A config holds basic info about the local configuration.

    During initialization, the object tries to read from a file config.toml and
        a backup file config_back.toml. If they do not exist, create a default
        configuration and save it to both files.

    If the config.toml that has been corrupted, tell the user that there is a
        problem and point to a solution. If the file can be read as a text
        file, save it to a file that has the string "invalid" in the
        name.

    """

    def __init__(self):
        self.d = self.read_toml("config.toml")
        self.update()

    @staticmethod
    def project_home() -> Path:
        if platform.system() == "Darwin":
            p_home = Path.home() / "Library" / "Gennaker"
        elif platform.system() == "Windows":
            p_home = Path.home() / "AppData" / "Local" / "Gennaker"
        return p_home

    def paths_dict(self):
        d = {}
        d["tk"] = self.project_home() / "config" / "trusted_keys.toml"
        d["config.toml"] = self.project_home() / "config" / "config.toml"
        d["config_back.toml"] = self.project_home() / "config" / "config_back.toml"
        return d

    def valid_toml_file(self, p):
        """Verify that the file at location p is a valid toml file."""
        invalid = p.parent / ("invalid_" + p.stem)
        try:
            s = p.read_text()
            try:
                d = tomli.loads(s)
                if not self.validate(d):
                    print(ConfigWarnings.not_valid())
                    print()
                    print(ConfigWarnings.backed_up(invalid))
                    print()
                    print(ConfigWarnings.replaced())
                    print()
                    invalid.write_text(s)
                    return False
            except tomli.TOMLDecodeError:
                print(ConfigWarnings.not_valid())
                print()
                print(ConfigWarnings.backed_up(invalid))
                print()
                print(ConfigWarnings.replaced())
                print()
                invalid.write_bytes(p.read_bytes())
                return False
        except UnicodeDecodeError:
            print(ConfigWarnings.not_unicode())
            print()
            print(ConfigWarnings.backed_up(invalid))
            print()
            print(ConfigWarnings.replaced())
            print()
            invalid.write_bytes(p.read_bytes())
            return False
        except FileNotFoundError:
            print(ConfigWarnings.does_not_exist(p))
            print()
            return False
        return True

    def read_toml(self, fname):
        """Try to read the toml file at location
        project_home() / "config" / fname.

        If the file does not exist, or if the toml can't be parsed, or if the
            in the file are invalid, tell user to create new files using
            edit_config.ipynb.
        """
        p = self.paths_dict()[fname]
        if not p.exists():
            print(f"Warning: {fname} is missing; using default")  ###
            d = self.create_default_config()
            p.write_text(tomli_w.dumps(d))
        elif not self.valid_toml_file(p):
            print(f"{fname} could not be read as text and parsed as toml")
            print("using default")  ###
            d = self.create_default_config()
            p.write_text(tomli_w.dumps(d))
        elif not self.validate(tomli.loads(p.read_text()), verbose=False):
            print(f"{fname} file contains invalid values.")  ###
            print("using default")  ###
            d = self.create_default_config()
            p.write_text(tomli_w.dumps(d))

        return tomli.loads(p.read_text())

    def folders_dict(self, d):
        sign_folders = {}
        if d["folders_location"] == "Desktop":
            sign_folders = {
                "to-sign": Path.home() / "Desktop" / "to-sign",
                "signed": Path.home() / "Desktop" / "to-sign" / "signed",
                "to-check": Path.home() / "Desktop" / "to-check",
                "quarantined": Path.home() / "Desktop" / "to-check" / "quarantine",
                "authenticated": Path.home() / "Desktop" / "to-check" / "authenticated",
            }
        elif d["folders_location"] == "Documents":
            sign_folders = {
                "to-sign": Path.home()
                / "Documents"
                / "_digital_signatures"
                / "to-sign",
                "signed": Path.home()
                / "Documents"
                / "_digital_signatures"
                / "to-sign"
                / "signed",
                "to-check": Path.home()
                / "Documents"
                / "_digital_signatures"
                / "to-check",
                "quarantined": Path.home()
                / "Documents"
                / "_digital_signatures"
                / "to-check"
                / "quarantine",
                "authenticated": Path.home()
                / "Documents"
                / "_digital_signatures"
                / "to-check"
                / "authenticated",
            }
        elif d["folders_location"] == "project_home":
            sign_folders = {
                "to-sign": self.project_home() / "_digital_signatures" / "to-sign",
                "signed": self.project_home()
                / "_digital_signatures"
                / "to-sign"
                / "signed",
                "to-check": self.project_home() / "_digital_signatures" / "to-check",
                "quarantined": self.project_home()
                / "_digital_signatures"
                / "to-check"
                / "quarantine",
                "authenticated": self.project_home()
                / "_digital_signatures"
                / "to-check"
                / "authenticated",
            }
        return sign_folders

    def create_default_config(self):
        """Specifies the default values for the variables for the
        config.toml file or the config_temp.toml file. Usually,
        these files will be created during the install process, but
        This function can recreate either if it is deleted.

        They also help cover the case of other users on a machine
        other than the user who did the program install.

        Warning: Notice the capitalization for "Keychain" and "Filesystem"
        when they are values associated with the "key_management_strategy"
        key. For example, every instance of ' = "Keychain' should have a
        capital K; every instance of ' = "Filesystem' should have a capital
        F.
        """
        if platform.system() == "Darwin":
            default = {
                "folders_location": "Desktop",
                "math_rendering": "MathJax3",
                "git_extensions": "Hidden",
                "key_management_strategy": "Keychain",
                "keychain_name": "login",
                "key_dir_string": "",
            }
        elif platform.system() == "Windows":
            default = {
                "folders_location": "Desktop",
                "math_rendering": "MathJax3",
                "git_extensions": "Hidden",
                "key_management_strategy": "Locker",
                "keychain_name": "",
                "key_dir_string": "",
            }
        return default

    @classmethod
    def validate(cls, d, verbose=True):
        """Validate checks the values of the variables specified
        in a configuration dictionary. Note that in contrast,
        self.ensure_valid_toml_file() only confirms that the
        file can be read and converted into a dictionary.

        Tests:
        t0, t1, t2: Are the values from the feasible set.
        (The only way this could fail is if someone edits the
        config.toml file directly.)

        t3: Is Key Management Strategy (KMS) feasible on this platform?

        t4: Does key_dir_string map to a valid directory?
                Set to True if it does not matter because
                KMS != "Filesystem"

        t5: Does keychain_name exist?
                Set to True if KMS != "Keychain"
        """

        t0 = d["folders_location"] in ["Desktop", "Documents", "project_home"]
        t1 = d["math_rendering"] in ["MathJax3", "KaTeX"]
        t2 = d["git_extensions"] in ["Hidden", "Visible"]
        if d["key_management_strategy"] == "Keychain":
            t3 = platform.system() == "Darwin"
        elif d["key_management_strategy"] == "Locker":
            t3 = platform.system() == "Windows"
        else:
            t3 = d["key_management_strategy"] == "Filesystem"
        if d["key_management_strategy"] == "Filesystem":
            t4 = cls.test_dir_string(d["key_dir_string"])
        else:
            t4 = True
        if d["key_management_strategy"] == "Keychain":
            t5 = cls.keychain_exists(d["keychain_name"])
        else:
            t5 = True

        if verbose:
            if not t0:
                print("Bad value for folder_location")
            if not t1:
                print("Bad value for math_rendering")
            if not t2:
                print("Bad value for git_extensions")
            if not t3:
                print("Bad value for key_management_strategy")
            if not t4:
                print("Bad value for key_dir_string")
            if not t5:
                print("Bad value for keychain_name")

        all = t0 and t1 and t2 and t3 and t4 and t5
        return all

    @staticmethod
    def test_dir_string(s):
        try:
            Path(s).mkdir(exist_ok=True, parents=True)
            return True
        except:
            return False

    @staticmethod
    def keychain_exists(s):
        """Check whether a keychain name corresponds to an existing keychain."""
        if s == "login":
            return True
        else:
            try:
                cp = run(
                    ["/usr/bin/security", "list-keychains"],
                    text=True,
                    check=True,
                    capture_output=True,
                )
            except CalledProcessError:
                print("There was an unexpected problem in examining your keychains.")
                print()
                print(
                    "You will not be able to store your key in the keychain you named."
                )
                return False
            else:
                if s in cp.stdout:
                    return True
                else:
                    print(ConfigWarnings.not_a_keychain(s))
                    return False

    @staticmethod
    def same_key_loc(d1, d2):
        """For two configuration dictionaries d1 and d2, return true if the
        location where the secret is saved is the same; false otherwise.
        """
        if d1["key_management_strategy"] == d2["key_management_strategy"]:
            if d1["key_management_strategy"] == "Keychain":
                if d1["keychain_name"] == d2["keychain_name"]:
                    return True
                else:
                    return False
            elif d1["key_management_strategy"] == "Locker":
                return True
            elif d1["key_management_strategy"] == "Filesystem":
                if d1["key_dir_string"] == d2["key_dir_string"]:
                    return True
                else:
                    return False
        else:
            return False

    def write_to_config_back(self, d_back):
        """Write d_back to config_back.toml.
        Requires setting and unsetting of write access.
        """
        # os.chmod(self.paths_dict()["config_back.toml"], stat.S_IWUSR)
        self.paths_dict()["config_back.toml"].write_text(tomli_w.dumps(d_back))
        # os.chmod(self.paths_dict()["config_back.toml"], stat.S_IRUSR)
        return

    # =============== high level operations with secrets ==============
    # read, exists, write, delete, update
    #   - take dictionaries as arguments
    #   - supported by platform specific functions
    #

    def read_secret_string(self, d):
        """Returns the secret string."""
        if d["key_management_strategy"] == "Keychain":
            return self.from_keychain(d["keychain_name"])
        elif d["key_management_strategy"] == "Locker":
            return self.from_locker()
        elif d["key_management_strategy"] == "Filesystem":
            print(d["key_dir_string"])
            return self.from_filesystem(d["key_dir_string"])

    def secret_exists(self, d):
        """Tests for a saved secret key string in the
        location specified by the dictionary d.

        Use to test before attempting a save that could
        overwrite an existing key.
        """
        if d["key_management_strategy"] == "Keychain":
            return bool(self.from_keychain(d["keychain_name"]))
        elif d["key_management_strategy"] == "Locker":
            return bool(self.from_locker())
        elif d["key_management_strategy"] == "Filesystem":
            return bool(self.from_filesystem(d["key_dir_string"]))

    def write_secret_string(self, secret_string, d):
        if self.secret_exists(d):
            print(ConfigWarnings.existing_same_loc())  ###?
            return
        else:
            if d["key_management_strategy"] == "Keychain":
                return self.to_keychain(d["keychain_name"], secret_string)
            elif d["key_management_strategy"] == "Locker":
                return self.to_locker(secret_string)
            elif d["key_management_strategy"] == "Filesystem":
                return self.to_filesystem(d["key_dir_string"], secret_string)

    def delete_secret(self, d):
        if d["key_management_strategy"] == "Keychain":
            self.del_from_keychain(d["keychain_name"])
        elif d["key_management_strategy"] == "Locker":
            self.del_from_locker()
        elif d["key_management_strategy"] == "Filesystem":
            self.del_from_filesystem(d["key_dir_string"])

    def update(self):
        """
        Starts by checking to see if there are any differences between
        config.toml and config_toml.back. If there are, this is a sign that
        something has gone wrong; in particular, the update process may have
        been interupted. If so, complete the update process.

        If there is a difference in the location of the saved key,
        update makes a safe move of the secret from a location specified in
        congig_back.toml to the new location specified in config.back.

        There are three steps:
            - copy the secret
            - delete the secret if copy succeeds
            - rewrite the config_back toml file so it has the
                same info as the config.toml file.

        At the end:
              - config.toml and config_back.toml exist and are identical
              - If a secret exists it is in location specified in config.toml
              - Signing folders will exist in the correct location
              - config_back.toml is protected by read-only access
        """
        d = self.read_toml("config.toml")
        d_back = self.read_toml("config_back.toml")
        # Define flags
        back_update_required = False
        # folders_differ = False ### CHANGE
        folders_differ = []

        # Fix problems with key location
        if not self.same_key_loc(d, d_back):
            back_update_required = True
            if self.secret_exists(d):
                if self.secret_exists(d_back):
                    self.delete_secret(d_back)
                elif not self.secret_exists(d_back):
                    pass
            elif not self.secret_exists(d):
                if self.secret_exists(d_back):
                    self.write_secret_string(self.read_secret_string(d_back), d)
                    self.delete_secret(d_back)
                elif not self.secret_exists(d_back):
                    pass
            for k in ["key_management_strategy", "keychain_name", "key_dir_string"]:
                d_back[k] = d[k]

        # Make sure that signing folders are as specified in d
        #     and move anything that could have been missed
        for v in self.folders_dict(d).values():
            v.mkdir(exist_ok=True, parents=True)
        fd = self.folders_dict(d)
        fd_back = self.folders_dict(d_back)

        for k in fd:
            # folders_differ &= not (fd[k] == fd_back[k]) ### CHANGE
            folders_differ.append(not (fd[k] == fd_back[k]))
        # if folders_differ: ### CHANGE
        if any(folders_differ):
            for k in fd:
                if fd_back[k].exists():
                    shutil.copytree(src=fd_back[k], dst=fd[k], dirs_exist_ok=True)
                    shutil.rmtree(fd_back[k])

        if d["folders_location"] == "Desktop":
            if (Config.project_home() / "Documents/_digital_signatures").exists():
                shutil.rmtree(Config.project_home() / "_digital_signatures")

        # Fix any other differences between d and d_back
        if not d_back["folders_location"] == d["folders_location"]:
            d_back["folders_location"] = d["folders_location"]
            back_update_required = True
        if not d_back["math_rendering"] == d["math_rendering"]:
            d_back["math_rendering"] = d["math_rendering"]
            back_update_required = True
        if not d_back["git_extensions"] == d["git_extensions"]:
            d_back["git_extensions"] = d["git_extensions"]
            back_update_required = True

        # If there were any differences between d and d_back
        if back_update_required:
            self.write_to_config_back(d_back)

        return

    # =========================== 1. read from ==========================
    @staticmethod
    def from_keychain(keychain_name):
        """ """
        arg_list = [
            "/usr/bin/security",
            "find-generic-password",
            "-w",
            "-s",
            "mainsail_signing_service",
            "-a",
            "mainsail_secret_string",
            keychain_name + ".keychain-db",
        ]
        try:
            cp = run(arg_list, check=True, text=True, capture_output=True)
            key_str = cp.stdout.rstrip()
            return key_str
        except CalledProcessError as e:
            if e.returncode == 128:
                print(
                    f"    The attempted read from the keychain '{keychain_name}' failed."
                )
                if not keychain_name == "login":
                    print()
                    print(
                        "    You must unlock this keychain by supplying the password at the prompt or"
                    )
                    print("    by using the Keychain Access utility.")
                    print()
                    print(
                        f"    If you have forgotten the password for the keychain '{keychain_name}', you may have to"
                    )
                    print("    create a new secret key and save it in a new location.")
                    print()
                else:
                    print()
                    print(
                        "    Use the Keychain Access utility to confirm whether there is a key in your"
                    )
                    print("    login keychain called mainsail_secret_string.")
                    print()
                    print("    If not, you need to create a new signing key.")
                    print()
            return

    @staticmethod
    def from_locker():
        """Retrieve secret key string from Windows Credential locker."""
        key_str = keyring.get_password("mainsail_secret_string", "ed25519_secret")
        if key_str:
            return key_str
        else:
            print(
                "The key doesn't exist. If you haven't done so, "
                "generate keys first."
                "If you have lost your keys, generate a new key pair."
            )
            return

    @staticmethod
    def from_filesystem(key_dir):
        """Read plain text secret key from the filesystem."""
        while not Path(key_dir).is_dir():
            print(ConfigWarnings.dir_does_not_exist(key_dir))
            retry_usb = input("Enter 'y' or 'Y' to retry, anything else to cancel.")
            if retry_usb in ["y", "Y"]:
                print("Retrying ...")
                continue
            else:
                print("Canceled.")
                return False

        p = Path(key_dir) / "mainsail_secret_string.secret"
        if p.is_file():
            return p.read_text()
        else:
            return

    # ============================ 2. write to ==========================
    @staticmethod
    def to_keychain(keychain_name, secret_key_string) -> str | bool:
        """Save a secret key string to keychain"""
        arg_list = [
            "/usr/bin/security",
            "add-generic-password",
            "-s",
            "mainsail_signing_service",
            "-a",
            "mainsail_secret_string",
            "-D",
            "ed25519_secret",
            "-w",
            secret_key_string,
            keychain_name + ".keychain-db",
        ]
        try:
            run(arg_list, check=True, text=True, capture_output=True)
            return True
        except CalledProcessError as e:
            if e.returncode == 128:
                print(
                    f"    The attempted write to the keychain '{keychain_name}' failed."
                )
                if not keychain_name == "login":
                    print()
                    print(
                        "    You must unlock this keychain by supplying the password at the prompt or"
                    )
                    print("    by using the Keychain Access utility.")
                    print()
                    print(
                        f"    If you have forgotten the password for the keychain '{keychain_name}', you may have to"
                    )
                    print("    create a new secret key and save it in a new location.")
                    print()
                else:
                    print("   ", e.stderr, "\n")
            else:
                print("   ", e.stderr, "\n")
            return False

    @staticmethod
    def to_locker(secret_key_string) -> str | bool:
        """Save a secret key string to Windows Credential locker."""
        keyring.set_password(
            "mainsail_secret_string",
            "ed25519_secret",
            secret_key_string,
        )
        return True

    @staticmethod
    def to_filesystem(key_dir, secret_key_string) -> str | bool:
        """Save a secret key to filesystem."""
        while not Path(key_dir).is_dir():
            print(ConfigWarnings().dir_does_not_exist(key_dir))
            retry_usb = input("Enter 'y' to retry, any other key to cancel.")
            if retry_usb in ["y", "Y"]:
                print("Retrying ... ")
                continue
            else:
                print("Canceling")
                return False
        (Path(key_dir) / "mainsail_secret_string.secret").write_text(secret_key_string)
        # Encourage anyone who uses git to add .secret to .gitignore.
        return True

    # ============================== 3. delete ==========================
    @staticmethod
    def del_from_keychain(kcn) -> bool:
        """Delete secret key in Keychain"""
        arg_list = [
            "/usr/bin/security",
            "delete-generic-password",
            "-s",
            "mainsail_signing_service",
            "-a",
            "mainsail_secret_string",
            "-D",
            "ed25519_secret",
            kcn + ".keychain-db",
        ]
        try:
            run(arg_list, check=True, text=True, capture_output=True)
            return True
        except CalledProcessError as e:
            print(e.stderr)
            return False

    @staticmethod
    def del_from_locker():
        keyring.delete_password(
            "mainsail_secret_string",
            "ed25519_secret",
        )

    @staticmethod
    def del_from_filesystem(key_dir):
        """Save a secret key to filesystem."""
        while not Path(key_dir).is_dir():
            print(ConfigWarnings().dir_does_not_exist(key_dir))
            retry_usb = input("Enter 'y' to retry, any other key to cancel.")
            if retry_usb in ["y", "Y"]:
                print("Retrying ... ")
                continue
            else:
                print("Canceling")
                return False

        (Path(key_dir) / "mainsail_secret_string.secret").unlink()


class Edsig:
    """Conversions between formats:

    Let b be a bytearray
    Let b64 be a array encoded using base64

    Let M stand for either 44 or 88
        s_M is a string of length M

    Let n stand for either 32 or 64
        b_n is a bytearray of length n

    b64_M is a base64 encoded bytearray of length M
    Every byte corresponds to an ascii character,
    so any b64_m is equivalent to an ascii string s_M.

    A key can be represented as
        b_32: 32 arbitrary bytes or
        b64_44: base64 encoded bytearray
        s_44: string len = 44

    A signature can be represented as
        b_64: 64 arbitrary bytes or
        b64_88: base64 encoded bytesarray of len = 88
        s_88: string len = 88

    To convert, use functions:
        b_2_s: b_n to s_M
        s_2_b: s_M to b_n

    """

    @staticmethod
    def bundle_suffix():
        return ".edbdl"

    @staticmethod
    def signature_suffix():
        return ".edsig"

    @staticmethod
    def b_2_s(b):
        """From bytes to urlsafe base64 to string"""
        return str(base64.urlsafe_b64encode(b), "utf-8")

    @staticmethod
    def s_2_b(s):
        """Converts to bytes any string that is in the image of
        b_2_s(). It is defined only on a subset of all possible
        strings. If applied to other strings, it will throw an error.

        For any byte array b,
            s_to_b(b_to_s(b)) = b
        """
        return base64.urlsafe_b64decode(bytes(s, "utf-8"))

    @staticmethod
    def block(
        sig_88="a" * 88,
        ps_44="b" * 44,
    ):
        """Takes as input, a base64 encoded signature for a file sig_88
        and a base64 encoded public string ps_44.

        Given sig_88 and ps_44, block returns:

        - the bytes that will be prepended to the file being signed

        - the length of this block, and

        - the ranges to use to extract sig_88 and ps_44 from this block.
        """

        s = " SIGNATURE "
        sig_box1 = "\u2554" + "\u2550" * 38 + s + "\u2550" * 39 + "\u2557" + "\n"
        sig_box2 = "\u2551" + sig_88 + "\u2551" + "\n"
        sig_box3 = "\u255A" + "\u2550" * 88 + "\u255D" + "\n"
        bs1 = bytes(sig_box1, "utf-8")
        bs2 = bytes(sig_box2, "utf-8")
        bs3 = bytes(sig_box3, "utf-8")
        bs = bs1 + bs2 + bs3

        ls1 = len(bytes(sig_box1, "utf-8"))
        ls2 = len(bytes(sig_box2, "utf-8"))
        ls3 = len(bytes(sig_box3, "utf-8"))

        ls = ls1 + ls2 + ls3

        pk = " PUBLIC KEY "
        ps_box1 = "\u2554" + "\u2550" * 16 + pk + "\u2550" * 16 + "\u2557" + "\n"
        ps_box2 = "\u2551" + ps_44 + "\u2551" + "\n"
        ps_box3 = "\u255A" + "\u2550" * 44 + "\u255D" + "\n"
        bp1 = bytes(ps_box1, "utf-8")
        bp2 = bytes(ps_box2, "utf-8")
        bp3 = bytes(ps_box3, "utf-8")
        bp = bp1 + bp2 + bp3

        lp1 = len(bytes(ps_box1, "utf-8"))
        lp2 = len(bytes(ps_box2, "utf-8"))
        lp3 = len(bytes(ps_box3, "utf-8"))
        lp = lp1 + lp2 + lp3

        b = bs + bp

        sig_range = (ls1 + 3, ls1 + ls2 - 4)
        ps_range = (ls + lp1 + 3, ls + lp1 + lp2 - 4)

        return (len(b), sig_range, ps_range, b)

    @classmethod
    def blk_2_sig(cls, bdl: bytes) -> str:
        """Takes a block of bytes as input.
        Returns the embedded signature string."""
        sig_range = cls.block()[1]
        sig = str(bdl[sig_range[0] : sig_range[1]], "utf-8")
        return sig

    @classmethod
    def blk_2_ps(cls, bdl: bytes) -> str:
        """Takes a block of bytes as input.
        Returns the embedded public string.
        """
        ps_range = cls.block()[2]
        ps = str(bdl[ps_range[0] : ps_range[1]], "utf-8")
        return ps

    @classmethod
    def bdl_2_msg(cls, bdl: bytes) -> bytes:
        """Extract the msg bytes from a bundle"""
        l = cls.block()[0]
        n = cls.not_ascii()[0]
        return bdl[l:-n]

    @staticmethod
    def not_ascii():
        """Null bytes
        - don't seem to stop the Jupyter editor
        - do seem to get git to treat the file as not text
        """
        n = 32
        return (n, bytes.fromhex("00") * n)


class PublicObject:
    """Expects a file path with the extension '.edbdl'.
    Returns a PublicObject with a .verify() method that can
    can be used to verify the signature of the included file.
    """

    def __init__(self, p: Path, mock = False):
        if p.suffix == ".edbdl":
            self.p_bdl = p
            self.mock = mock
            b = self.p_bdl.read_bytes()
            self.p_doc = self.p_bdl.parent / (self.p_bdl.stem)
            self.p_sig = self.p_doc.parent / (self.p_doc.stem + ".sig")
            self.msg = Edsig.bdl_2_msg(b)
            self.sig = Edsig.blk_2_sig(b)
            self.ps = Edsig.blk_2_ps(b)


        else:
            raise TypeError(
                """
The only types of files that can be verified are signed bundles 
that should have the extension '.edbdl'.
"""
            )

    def __str__(self):
        """If valid, return the string for the public key from p."""
        return self.ps

    def __bytes__(self):
        """If valid, returns the bytes for the public key from p."""
        return Edsig.s_2_b(self.ps)

    def verify(self) -> bool:
        try:
            VerifyKey(Edsig.s_2_b(self.ps)).verify(self.msg, Edsig.s_2_b(self.sig))
            return True
        except BadSignatureError:
            return False

    def fetch_profile(self, mock):
        """Find a member profile associated with a public key specified in a
        verify_files object.
        """
        if not self.mock:
            # Find the urls of member profile in all three services

            urls = [b + self.ps for b in list(BaseUrls())]

            with ThreadPoolExecutor(max_workers=3) as e:
                reqs = e.map(requests.get, urls)

            c = Counter([r.text for r in reqs if "error" not in r.text.lower()])


        elif self.mock:
            mock_profile_paths = [
                Path.home() / "Library/Gennaker/projects/Testing/review/member_profiles0" / self.ps,
                Path.home() / "Library/Gennaker/projects/Testing/review/member_profiles1" / self.ps,
            ]

            c = Counter([p.read_text() for p in mock_profile_paths if p.is_file()])


        # Get trusted keys
        if Config().paths_dict()["tk"].is_file():
            d_trusted = tomli.loads(Config().paths_dict()["tk"].read_text())
        else:
            d_trusted = {}

        d = None
        found = False
        agreement = False
        in_trusted = False
        changed = False
        active = False
        verified = self.verify()

        if c:
            found = True
            d = tomli.loads(c.most_common()[0][0])
            if c.most_common()[0][1] >= 2:
                agreement = True
            if self.ps in d_trusted:
                in_trusted = True
            if self.ps in d_trusted and d != d_trusted[self.ps]:
                changed = True
            if d["Public_key"]["Active"]:
                active = True

        return (d, verified, found, agreement, in_trusted, changed, active)

    # def fetch_profile_mock(self):
    #     # Find the urls of member profile in all three services

    #     mock_profile_paths = [
    #         Path.home() / "Library/Gennaker/projects/Testing/review/member_profiles0" / self.ps,
    #         Path.home() / "Library/Gennaker/projects/Testing/review/member_profiles1" / self.ps,
    #     ]
        
    #     c = Counter([p.read_text() for p in mock_profile_paths if p.is_file()])

    #     # Get trusted keys
    #     if Config().paths_dict()["tk"].is_file():
    #         d_trusted = tomli.loads(Config().paths_dict()["tk"].read_text())
    #     else:
    #         d_trusted = {}

    #     d = None
    #     found = False
    #     agreement = False
    #     in_trusted = False
    #     changed = False
    #     active = False
    #     verified = self.verify()

    #     if c:
    #         found = True
    #         d = tomli.loads(c.most_common()[0][0])
    #         if c.most_common()[0][1] >= 2:
    #             agreement = True
    #         if self.ps in d_trusted:
    #             in_trusted = True
    #         if self.ps in d_trusted and d != d_trusted[self.ps]:
    #             changed = True
    #         if d["Public_key"]["Active"]:
    #             active = True
                
    #     return (d, verified, found, agreement, in_trusted, changed, active)



class SecretObject:
    """
    Composes with Edsig and KeyManagement.

    The state for a SecretObject is the seed, which is encoded as a string.

    There are two ways get the seed:

        1. Use a random string of bytes as seed:
            SecretObject.from_generated()

        2. Read in saved version of the seed:
            SecretObject.from_saved()

    """

    def __init__(self, string_seed):
        self.secret_key = SigningKey(Edsig.s_2_b(string_seed))
        self.public_string = Edsig.b_2_s(bytes(self.secret_key.verify_key))

    def __bytes__(self):
        """Returns the same bytes as the corresponding NaCl object."""
        return bytes(self.secret_key)

    @classmethod
    def from_generated(cls):
        return cls(Edsig.b_2_s(bytes(SigningKey.generate())))

    @classmethod
    def from_saved(cls):
        cfg = Config()
        return cls(cfg.read_secret_string(cfg.d))

    def save_key(self):
        """Tests for an exising key, then writes if
        none exists. Will create a default config.toml if it
        does not exist.
        """
        cfg = Config()
        if cfg.secret_exists(cfg.d):
            print(ConfigWarnings.existing_same_loc())
            if platform.system() == "Darwin":
                keyapp_dir = "/Applications/Utilities"
                keyapp = "Keychain Access"
            elif platform.system() == "Windows":
                keyapp_dir = "Control Panel"
                keyapp = "Credential Manager"
            print(ConfigWarnings.remove_rerun(keyapp_dir, keyapp))
            return False
        else:
            b = self.__bytes__()
            cfg.write_secret_string(Edsig.b_2_s(b), cfg.d)

    def sign_file(self, p_doc):
        """Sign a file and write to a bundle.
        Use this name to differentiate from secret_key.sign()
        """
        if not p_doc.is_file():
            print("The specified file doesn't exist. Check the file path.")
            print("Path =", p_doc)
            return
        msg = p_doc.read_bytes()
        sig = Edsig.b_2_s(self.secret_key.sign(msg).signature)
        ps = self.public_string
        b = Edsig.block(sig, ps)[3] + msg + Edsig.not_ascii()[1]
        p = Path(str(p_doc) + Edsig.bundle_suffix())
        p.write_bytes(b)
        return True


class EditConfigWidgets:
    def __init__(self):
        cfg = Config()

        self.width = "70%"
        rdbtn_layout = widgets.Layout(
            padding="2em 2em 1em 4em",
            height="auto",
            width=self.width,
            border_bottom="thin solid",
        )

        floc_options = ["Desktop", "Documents"]

        self.floc_w = widgets.RadioButtons(
            options=floc_options,
            # description='Folders Location',
            layout=rdbtn_layout,
            disabled=False,
            value=cfg.d["folders_location"],
        )

        self.floc_th = self.field_title_and_helper_text(
            "Folders Location",
            (
                """<p>Choose the location to put the 'to-sign'and 
                'to-check' folders for auto-signing and verification. 
                The default is 'Desktop', which faciliates drag-and-drop. 
                Alternatively, create the folders in the 'Documents' Folder. 
                </p>"""
            ),
        )

        self.math_rendering_w = widgets.RadioButtons(
            options=["MathJax3", "KaTeX"],
            # description='Math Rendering',
            layout=rdbtn_layout,
            disabled=False,
            value=cfg.d["math_rendering"],
        )

        self.math_rendering_th = self.field_title_and_helper_text(
            "Math Rendering",
            str(
                """<p>The recommended option is 'MathJax3' because 
                KaTeX covers most, but not all, of AMS-LaTeX. KaTeX 
                was much faster than MathJax2, but with the update to 
                version 3, the performance of MathJax is so much better 
                that for most content users will notice any difference. 
                Nevertheless, if your content is math intensive, 
                you may still want to compare the responsiveness of 
                these alternatives. </p>"""
            ),
        )

        self.git_extensions_th = self.field_title_and_helper_text(
            "Git Extensions", "Show Git related Jupyter Extensions and gitignore file"
        )

        self.git_extensions_w = widgets.RadioButtons(
            options=["Hidden", "Visible"],
            # description='Git Extensions',
            layout=rdbtn_layout,
            disabled=False,
            value=cfg.d["git_extensions"],
        )

        if platform.system() == "Darwin":
            kms_options = ["Keychain", "Filesystem"]
        elif platform.system() == "Windows":
            kms_options = ["Locker", "Filesystem"]


        self.kms_w = widgets.RadioButtons(
            options=kms_options,
            description=" ",
            layout=rdbtn_layout,
            disabled=False,
            value=cfg.d["key_management_strategy"],
        )

        self.kms_th = self.field_title_and_helper_text(
            "Key Management Strategy",
            str(
                "<p>The default option is 'Keychain', the macOS "
                "native system for key management. View it using the "
                "'Keychain Access' app"
                "Alternatively, choose 'Filesystem' to store your keys "
                "as plaintext on a removable drive. The removable drive "
                "should have encryption, it's your weakest line of defense. "
                "We don't recommend storing keys as plaintext on your local disk. "
                "Use the default option instead.</p>"
            ),
        )

        text_input_layout = widgets.Layout(
            padding="2em",
            height="auto",
            width=self.width,
            description_width="initial",
        )

        #### Need to add analog for Windows and Credential Locker/Manager 

        self.kcn_th = self.field_title_and_helper_text(
            "Keychain Name",
            (
                "By default, Gennaker uses the macOS 'login' keychain, where apps "
                "typically store your credentials. It's automatically unlocked and "
                "available when you log into your computer. See detailed instructions "
                "below for creating a custom keychain"
            ),
        )

        self.kcn_w = widgets.Text(
            value=cfg.d["keychain_name"],
            description="Keychain Name",
            layout=text_input_layout,
            style={"description_width": "7.5em"},
            disabled=False,
        )

        self.kdir_th = self.field_title_and_helper_text(
            "Key Directory",
            (
                "Required When you select 'Filesystem' for 'Key Management Strategy'"
                "Enter the absolute path to the directory representing the removable "
                "drive where you want your secret key stored"
            ),
        )

        self.kdir_w = widgets.Text(
            value=cfg.d["key_dir_string"],
            description="Key Directory",
            layout=text_input_layout,
            style={"description_width": "7.5em"},
            disabled=False,
        )

        self.confirm_button = widgets.Button(
            description="Click to confirm all choices",
            disabled=False,
            button_style="info",  # 'success', 'info', 'warning', 'danger' or ''
            tooltip="Click me",
            icon="check",  # (FontAwesome names without the `fa-` prefix)
            layout=widgets.Layout(
                width="max-content",
                margin="2em",
                # border_top='thin solid'
            ),
        )

        self.confirm_button.on_click(self.respond_to_user_selections)

        self.out = widgets.Output(layout=text_input_layout)

        self.display_settings()

    def display_settings(self):
        title = widgets.HTML(
            value='<h1 style="text-align: center">Advanced Config Settings</h1>',
            layout=widgets.Layout(
                padding="2em",
                height="auto",
                width=self.width,
                border_bottom="thin solid",
            ),
        )
        b = widgets.VBox(
            children=[
                title,
                self.floc_th,
                self.floc_w,
                self.math_rendering_th,
                self.math_rendering_w,
                self.git_extensions_th,
                self.git_extensions_w,
                self.kms_th,
            ]
        )
        display(b)

        @interact(kms=self.kms_w)
        def link_widgets(kms):
            if self.kms_w.value == "Keychain":
                self.kcn_w.value = "login"
                display(widgets.VBox([self.kcn_th, self.kcn_w]))
            elif self.kms_w.value == "Filesystem":
                display(widgets.VBox([self.kdir_th, self.kdir_w]))

            self.out.clear_output()

        display(self.confirm_button)
        display(self.out)

    def respond_to_user_selections(self, *args):
        self.out.clear_output(wait=True)
        cfg = Config()

        d_new = {}
        d_new["folders_location"] = self.floc_w.value
        d_new["math_rendering"] = self.math_rendering_w.value
        d_new["git_extensions"] = self.git_extensions_w.value

        if self.kms_w.value == "Filesystem":
            d_new["key_management_strategy"] = self.kms_w.value
            d_new["key_dir_string"] = self.kdir_w  # Text widget specific
            d_new["keychain_name"] = ""

        elif self.kms_w.value == "Keychain":
            d_new["key_management_strategy"] = self.kms_w.value
            d_new["keychain_name"] = self.kcn_w.value
            d_new["key_dir_string"] = ""

        elif self.kms_w.value == "Locker":
            d_new["key_management_strategy"] = "Locker"
            d_new["keychain_name"] = ""
            d_new["key_dir_string"] = ""

        with self.out:
            if cfg.validate(d_new):
                cfg.paths_dict()["config.toml"].write_text(tomli_w.dumps(d_new))
                cfg.update()

        return

    def field_title_and_helper_text(self, field_title: str, helper_text: str):
        field_title_w = widgets.Label(
            value=field_title,
            style=dict(font_weight="bold", font_size="1.1em"),
            layout=widgets.Layout(
                padding="2em 2em 0 2em",
                height="auto",
                width=self.width,
            ),
        )
        helper_text_w = widgets.HTML(
            value=helper_text,
            layout=widgets.Layout(
                padding="1em 2em 0 2em",
                height="auto",
                width=self.width,
            ),
        )
        return widgets.VBox(children=[field_title_w, helper_text_w])


# ================== NamedTuples: used in Authenticate ======================


class ProfileData(NamedTuple):
    d: dict
    verified: bool
    found: bool
    agreement: bool
    in_trusted: bool
    changed: bool
    active: bool


class Row(NamedTuple):
    file_name: HTML
    profile: HTML
    status: HTML
    action: (widgets.RadioButtons | HTML)
    pd: ProfileData
    po: PublicObject


class BaseUrls(NamedTuple):
    aws: str = "https://mainsail-s3-cli-test.s3.amazonaws.com/"
    do: str = "https://fra1.digitaloceanspaces.com/mainsail-do-cli-test/"
    azure: str = "https://publickeyregistry.blob.core.windows.net/mainsail-az-cli-test/"


class Authenticate:
    """
    Need to finish the threading to make the button work.
    Also, fix the code that changes state of buttons on click
    of confirm button.
    """

    rdbtn_options = [
        "Move to Quarantine",
        "Move to Authenticated",
        "Move to Authenticated, always trust this person",
    ]
    rdbtn_options_alt = [
        "Move to Quarantine",
        "Move to Authenticated, remove from trusted signers",
        "Move to Authenticated, update trusted signers",
    ]

    def __init__(self, mock = False):
        self.mock = mock
        self.rows = self.get_rows(self.mock)

        self.confirm_b = widgets.Button(
            description="Implement Actions",
            disabled=False,
            button_style="info",
            tooltip="Click me",
            icon="check",
            layout=widgets.Layout(
                width="max-content",
                margin="1em",
            ),
        )
        self.confirm_b.on_click(self.confirm_b_click)

        self.refresh_b = widgets.Button(
            description="Check for files",
            disabled=False,
            button_style="info",
            tooltip="Click me",
            icon="rotate-right",
            layout=widgets.Layout(
                width="max-content",
                margin="1em",
            ),
        )
        self.refresh_b.on_click(self.refresh_b_click)

    def display(self):
        self.out1 = widgets.Output()
        self.out2 = widgets.Output()
        display(self.out1)
        display(self.out2)

        with self.out1:
            display(self.refresh_b)

        self.display_widgets()

    def get_rows(self, mock):
        cfg = Config()
        pos = [
            PublicObject(p, mock)
            for p in cfg.folders_dict(cfg.d)["to-check"].iterdir()
            if p.suffix == ".edbdl"
        ]
        return [Row(*self.row_tuple(po)) for po in pos]

    def refresh_b_click(self, mock, *args):
        self.rows = self.get_rows(self.mock)
        # Remove existing content then display new
        self.out2.clear_output()
        self.display_widgets()
        self.confirm_b.disabled = False

    def row_tuple(self, po: PublicObject):
        """Creates a tuple that is used to display rows."""

        def h_format(s: str, c="k") -> HTML:
            if c == "k":
                value = (
                    '<div style="padding-left: 5%; word-break: break-all">'
                    + s
                    + "</div>"
                )

                html_w = widgets.HTML(
                    value=value, layout=widgets.Layout(height="auto", width="auto")
                )
            elif c == "r":
                value = '<div style="padding-left: 5%">' + s + "</div>"
                html_w = widgets.HTML(
                    value=value, layout=widgets.Layout(height="auto", width="auto")
                )
                html_w.style.text_color = "red"
            elif c == "o":
                value = '<div style="padding-left: 5%">' + s + "</div>"
                html_w = widgets.HTML(
                    value=value, layout=widgets.Layout(height="auto", width="auto")
                )
                html_w.style.text_color = "orange"
            elif c == "g":
                value = '<div style="padding-left: 5%">' + s + "</div>"
                html_w = widgets.HTML(
                    value=value, layout=widgets.Layout(height="auto", width="auto")
                )
                html_w.style.text_color = "green"
            return html_w

        rdbtn = widgets.RadioButtons(
            placeholder="Check profile; then select an action",
            options=self.rdbtn_options,
            description="User Input Required:",
            value=None,
            disabled=False,
            layout=widgets.Layout(height="auto", width="auto", padding="0 0 0 5%"),
        )

        pd = ProfileData(*po.fetch_profile(self.mock))


        file_name = h_format(po.p_doc.name)

        if pd.found:
            s = f"""
                <div>
                    <p>{pd.d["Name"]["Value"]}</p>
                    <p>{pd.d["Location"]["Value"]}</p>
                    <p>{pd.d["Affiliation"]["Value"]}</p>
                    <p>Verified: {"{0:%b} {0.day},{0: %Y} ".format(
                        date.fromisoformat((
                            pd.d["Public_key"]["Last_verification_date"]
                        ).replace("/", "-"))
                    )}</p>
                </div>
                """

            profile = h_format(s)

        else:
            profile = h_format("<p></p>", c="r")

        status1 = ""
        status2 = ""
        status3 = ""

        # Add status1 text first
        if not pd.verified:
            status1 += "<p>- Signature is invalid</p>"
        if not pd.found:
            status1 += "<p>- No profile found</p>"
        if pd.found and not pd.agreement:
            status1 += "<p>- Profile found on a single server</p>"
        if not pd.active and pd.found:
            status1 += "<p>- Key is not active</p>"
        elif pd.verified and pd.found and pd.agreement and pd.active:
            status1 += "<p>- Checks passed</p>"
            if pd.in_trusted:
                status2 += "<p>- In trusted signers</p>"
            else:
                status2 += "<p>- Not in trusted signers</p>"

        if pd.in_trusted and pd.changed:
            status3 += "<p>- But profile has changed</p>"
            if not pd.active:
                status2 += "<p>- In trusted signers</p>"

        # Next, format text for status1, 2, 3
        if not (pd.verified and pd.found and pd.agreement):
            status1 = h_format(status1, c="r")
        elif pd.verified and pd.found and pd.agreement:
            if not pd.active:
                status1 = h_format(status1, c="o")
                status2 = h_format(status2, c="k")
            if pd.active:
                status1 = h_format(status1, c="g")
                if pd.in_trusted:
                    status2 = h_format(status2, c="g")
                elif not pd.in_trusted:
                    status2 = h_format(status2, c="k")

        if pd.in_trusted and pd.changed:
            status3 = h_format(status3, c="o")

        l = [i for i in [status1, status2, status3] if i != ""]
        status = widgets.VBox(children=l)

        action = rdbtn
        if not pd.verified:
            action = h_format("<p>Move to Quarantine</p>", c="r")
        if pd.verified and not pd.found:
            action = h_format("<p>Move to Quarantine</p>", c="r")
        if not pd.agreement:
            action = h_format("<p>Move to Quarantine</p>", c="r")
        if pd.verified and pd.found and pd.agreement and pd.active:
            if pd.in_trusted and not pd.changed:
                action = h_format("<p>Move to Authenticated</p>", c="g")
            if not pd.in_trusted:
                action = rdbtn
            elif pd.in_trusted and pd.changed:
                action = rdbtn
                rdbtn.options = self.rdbtn_options_alt

        if pd.verified and pd.found and pd.agreement and not pd.active:
            action = h_format(
                "<p>Move to Quarantine</p>"
                + "<p>(You might want to request a newly signed copy)</p>",
                c="o",
            )

        return (file_name, profile, status, action, pd, po)

    def confirm_b_click(self, *args):
        cfg = Config()

        self.confirm_b.disabled = True
        counter = 0
        for row in self.rows:
            counter += 1
            # if hasattr(row.action, "disabled"):
            #     row.action.disabled = True

            if isinstance(row.action, widgets.widget_string.HTML):
                if "Move to Quarantine" in repr(row.action):
                    p_dst = cfg.folders_dict(cfg.d)["quarantined"]
                elif "Move to Authenticated" in repr(row.action):
                    p_dst = cfg.folders_dict(cfg.d)["authenticated"]

            elif isinstance(row.action, widgets.widget_selection.RadioButtons):
                if row.action.value is None:
                    continue
                elif row.action.value == self.rdbtn_options[0]:  ### CHANGE
                    p_dst = cfg.folders_dict(cfg.d)["quarantined"]
                elif row.action.value in [
                    self.rdbtn_options[1],
                    self.rdbtn_options_alt[1],
                ]:  ### CHANGE
                    p_dst = cfg.folders_dict(cfg.d)["authenticated"]
                    if "remove" in repr(row.action.value):
                        self.remove_trusted_key(row.po.ps)
                elif row.action.value in [
                    self.rdbtn_options[2],
                    self.rdbtn_options_alt[2],
                ]:  ### CHANGE
                    p_dst = cfg.folders_dict(cfg.d)["authenticated"]
                    self.add_trusted_key(row.po.ps, row.pd.d)

            if p_dst == cfg.folders_dict(cfg.d)["quarantined"]:
                if row.po.p_bdl.is_file():
                    shutil.move(row.po.p_bdl, p_dst / row.po.p_bdl.name)
                if row.po.p_doc.is_file():
                    shutil.move(row.po.p_doc, p_dst / row.po.p_doc.name)
                if row.po.p_sig.is_file():
                    shutil.move(row.po.p_sig, p_dst / row.po.p_sig.name)

            elif p_dst == cfg.folders_dict(cfg.d)["authenticated"]:
                if row.po.p_bdl.is_file():
                    shutil.move(row.po.p_bdl, p_dst / row.po.p_bdl.name)
                    (p_dst / row.po.p_doc.name).write_bytes(row.po.msg)
                if row.po.p_doc.is_file():
                    shutil.move(row.po.p_doc, p_dst / row.po.p_doc.name)
                if row.po.p_sig.is_file():
                    shutil.move(row.po.p_sig, p_dst / row.po.p_sig.name)

        self.refresh_b_click()

    def display_widgets(self):
        """The code needed to display table of results."""

        def header():
            children = []
            for elem in ["File Name", "Profile", "Status", "Action"]:
                s = '<div style="padding-left: 5%"><b>' + elem + "</b></div>"
                children.append(widgets.HTML(value=s))
            hdr = widgets.GridBox(
                children=children,
                layout=widgets.Layout(
                    overflow="hidden",
                    width="100%",
                    height="auto",
                    grid_template_rows="auto",
                    grid_template_columns="20% 22% 18% 40%",
                ),
            )
            return hdr

        def hb(h):
            return widgets.HBox(
                (h,), layout=widgets.Layout(border_top="thin solid", padding="1em")
            )

        if len(self.rows) > 0:
            title_s = "Authenticate Senders"
        else:
            title_s = "No files to consider"

        v = '<h3 style="text-align: center">' + title_s + "</h3>"
        t = widgets.HTML(value=v)

        l = []
        if len(self.rows) > 0:
            l.append(hb(header()))
            for row in self.rows:
                rg = widgets.GridBox(
                    children=[row.file_name, row.profile, row.status, row.action],
                    layout=widgets.Layout(
                        overflow="hidden",
                        width="100%",
                        height="auto",
                        grid_template_rows="auto",
                        grid_template_columns="20% 22% 18% 40%",
                        align_items="baseline",
                    ),
                )
                l.append(hb(rg))
            l.append(self.confirm_b)

            v = widgets.VBox(children=[*l])

        if l:
            self.v2 = widgets.VBox(children=[t, v])
        else:
            self.v2 = widgets.VBox(children=[t])

        with self.out2:
            display(self.v2)

    @staticmethod
    def remove_trusted_key(ps):
        cfg = Config()
        if cfg.paths_dict()["tk"].is_file():
            d_trusted = tomli.loads(cfg.paths_dict()["tk"].read_text())
        else:
            d_trusted = {}
        del d_trusted[ps]
        with open(cfg.paths_dict()["tk"], "wb") as f:  ###
            tomli_w.dump(d_trusted, f)

    @staticmethod
    def add_trusted_key(ps, d):
        cfg = Config()
        if cfg.paths_dict()["tk"].is_file():
            d_trusted = tomli.loads(cfg.paths_dict()["tk"].read_text())
        else:
            d_trusted = {}
        d_trusted[ps] = d
        with open(cfg.paths_dict()["tk"], "wb") as f:  ###
            tomli_w.dump(d_trusted, f)


# class Table(Authenticate)
#     """Table takes a list of urls as
#     """

# =================== Functions for use in notebooks ======================


def generate_secret_and_save():
    so = SecretObject.from_generated()
    so.save_key()


def sign_file(p_doc: str):
    so = SecretObject.from_saved()
    if so:
        so.sign_file(Path(p_doc))
    else:
        print("Could not perform signing operation.")


def verify_bundle(fname: str):
    po = PublicObject(Path(fname))
    if po.verify():
        print("The signature and message verify for:")
        print(Path(fname).resolve())
        print()
        return True
    else:
        print("The signature and file are not consistent.")
        print("You should not trust the document.")
        return False


# =================== Warnings About Config Settings ======================


class ConfigWarnings:
    """Collect the long multiline warning messages here."""

    @staticmethod
    def does_not_exist(p):
        return f"""
Because there was no file at {str(p)}, Gennaker has created 
one with the default configuration for your computer.
"""

    @staticmethod
    def not_valid():
        return "The toml file is not valid."

    @staticmethod
    def not_unicode():
        return "The toml file is not encoded as Unicode."

    @staticmethod
    def backed_up(invalid):
        return f"The toml file has been saved as {str(invalid)}"

    @staticmethod
    def replaced():
        return """The toml file has been replaced by a new file with default values 
for the configuration."""

    @staticmethod
    def dir_does_not_exist(key_dir_string):
        return f"""
The directory {key_dir_string} does not exist.

If you keep your secret key on an external drive,
make sure that the operating system can read
from this drive.

If the disk is connected by the directory {key_dir_string}
does not exist, create it and try again.

"""

    @staticmethod
    def existing_same_loc():
        return f"""
You already have a secret Mainsail signing key in the specified 
location.

To prevent the inadvertent loss of an existing key, no new key will be
created. The existing key is still there.
"""

    @staticmethod
    def remove_rerun(keyapp_dir, keyapp):
        return f"""
If you want to stop using an existing secret and generate and save
a new one:

    i) Consider carefully whether you might want to retrieve the existing 
    secret in the future. If so, it might make sense to rename the existing 
    secret or save a backup copy.

    ii) Nextr, remove or rename any key that includes the phrase
    'mainsail_secret_string' in the location specified in your current
    configuration.

    iii) Re-run the command to generate and save a new key in
    the location specified in your current configuration.


To remove an existing Mainsail signing key from its
current location:

    - If the current location is a directory, go to it and
    rename or delete the file named 'mainsail_secret_string.secret'.

    - Otherwise, if your operating system is macOS or Windows, your key 
    may be  stored in a location managed by the operating system:

        i) Look in {keyapp_dir}. 
        
        Open {keyapp}. 

        ii) Search for the phrase 'mainsail_secret_string'.

        iii) Delete or rename any entries you find.
    """

    @staticmethod
    def prob_w_new_key_location():
        return f"""
Because there was a problem copying your secret string to the new location,
the  key management strategy and the location for storing the secret in the
config.toml file have not been changed. 

If you still want to move your key to the new location, please make sure 
that there is no orphaned secret string in the new location before trying
again.
"""

    @staticmethod
    def prob_w_new_signing_folders():
        return f"""
There was a problem with the proposed new location for the signing 
folders. No change was made to folder location in the configuration 
file. No files were moved. 

To make the proposed change, try removing any folders in the new location
with names that could conflict with names for the signing folders or 
cleaning out your existing signing folders. Then try your edit to make 
the change in the configuration.
"""

    @staticmethod
    def not_a_keychain(s):
        return f"""
'{s}' is not the name of an existing keychain.
Create a keychain with this name using the Keychain Access app, then try again."""
