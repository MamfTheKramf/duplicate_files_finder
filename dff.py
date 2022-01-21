import hashlib
import os
import sys
from getopt import getopt, GetoptError
import shutil
from dataclasses import dataclass
from typing import Optional


class DuplicateFinder:
    """
        A class for finding duplicates of the given file-types in the given folders.
        When recursion is set to True (default) all the subdirectories of the given golders will be checked as well.
        When set to False only the top-level of these directories will be checked
    """

    @dataclass
    class DuplicateEntry:
        name_in_duplicates: str
        orig_path: str

    def __init__(self, folders: list[str] = [], types: list[str] = [], recursion: bool = True) -> None:
        self._abs_path = os.path.dirname(os.path.abspath(__file__)) + "/"
        # list of files we don't want to include in the duplicate check
        self._bad_files: list[str] = [self._abs_path + "duplicate_images/dif.py",
                                      self._abs_path + "duplicate_images/searchSpace.txt",
                                      self._abs_path + "duplicate_images/fileTypes.txt"]

        self._folders: list[str] = []
        self.set_folders(folders)
        self._types: list[str] = []
        self.set_types(types)
        self._files: dict[str, dict] = {}
        self.types_updated()
        self._duplicates: list[DuplicateFinder.DuplicateEntry] = []
        self._already_checked = 0
        self._last_perc = 0
        self._total_files = 0
        self._do_recursion = recursion

    def set_folders(self, folders: list[str]) -> None:
        self._folders = folders

    def extract_folders_from_file(self, filename: str):
        """
            reads the folders to look through from the given file
        """
        with open(filename, "r", encoding="utf-8") as f:
            # read each line as a path
            self._folders = f.read().split("\n")
            # remove empty lines
            self._folders = list(filter(lambda x: x.strip() != "", self._folders))

    def set_types(self, types: list[str]) -> None:
        self._types = types
        self.types_updated()

    def extract_types_from_file(self, filename: str):
        """
            reads the file-types to look for from the given file
        """
        with open(filename, "r", encoding="utf-8") as f:
            # read each line as a file extension
            self._types = f.read().split("\n")
            # remove empty lines
            self._types = list(filter(lambda x: x.strip() != "", self._types))
        self.types_updated()

    def get_recursion(self) -> bool:
        return self._do_recursion

    def set_recursion(self, val: bool) -> None:
        self._do_recursion = val

    def types_updated(self):
        """
            method to be called when types are updates
        """
        self.update_files()
        self.create_folders()

    def update_files(self):
        """
            updates the files-dict to match the given file-types
        """
        self._files = dict([(key, dict()) for key in self._types])

    def create_folders(self):
        """
            creates folders for the found duplicates
        """
        if not os.path.exists(self._abs_path + "duplicates"):
            os.mkdir(self._abs_path + "duplicates")
            
        for t in self._types:
            if not os.path.exists(self._abs_path + "duplicates/" + t[1:]):
                os.mkdir(self._abs_path + "duplicates/" + t[1:])

    def to_exclude(self, dirname: str, root: str) -> bool:
        """
            checks whether the dir with the given name shall be excluded or not from the traversal
        """
        return (dirname == "duplicates" and "duplicate_images" in root) or "." in dirname

    def get_number_of_files(self, folders: list) -> int:
        ret = 0
        for folder in folders:
            for (dirpath, dirnames, filenames) in os.walk(folder, topdown=True):
                p = dirpath
                # when we don't want to recursively check all the subdirs we just remove all of them
                if not self._do_recursion:
                    dirnames[:] = []
                # pruning subdirs so we won't traverse the duplicates folder of this program or any folders like .git
                dirnames[:] = [d for d in dirnames if not self.to_exclude(d, p)]
                ret += len(filenames)
        return ret

    def get_filename(self, p: str) -> str:
        """
            gets a string of the complete filename with extension.
            returns a string of the filename without extension
        """
        index = p.rfind(".")
        return p[:index]

    def log(self, total_files: int, already_checked: int, last_perc: float, needed_change: float = 0.0001) -> float:
        """
            will log the progress when there is a change of needed_change
            will return the new percentage only if needed_change is passed
        """
        perc = already_checked / total_files
        if abs(perc - already_checked) >= needed_change:
            print(f"\r{round(perc * 100, 2)}% done...", end="")
            return perc
        return last_perc

    def find_duplicates(self):
        """
            actual code for finding the duplicate files
        """
        print("Counting number of files...")
        self._total_files = self.get_number_of_files(self._folders)
        print(f"Found {self._total_files} Files")

        print("start finding duplicate files...")
        # go through all files, hash them and write them in the corresponding dict with their hash-code as key
        # when there already is a file with this hash-code, check if there is actually the same file
        # if not, append it to the list
        for path in self._folders:
            for (dirpath, dirnames, filenames) in os.walk(path, topdown=True):
                p = dirpath

                # when we don't want to recursively check all the subdirs we just remove all of them
                if not self._do_recursion:
                    dirnames[:] = []

                # pruning subdirs so we won't traverse the duplicates folder of this program or any folders like .git
                dirnames[:] = [d for d in dirnames if not self.to_exclude(d, p)]

                self.find_duplicate_files(filenames, dirpath)

        self.write_duplicates_file()

    def find_duplicate_files(self, filenames: str, dirpath: str):
        """
            goes through each file in the list an checks if its a duplicate
        """
        for f in filenames:
            file_path = dirpath + "\\" + f
            # when we're looking at a file that is used by this program we skip it
            if any([file_path.endswith(badFile) for badFile in self._bad_files]):
                break

            # find out whether or not we're dealing with a file-type we're looking for
            t = self.find_type(f)
            if t is None:
                continue

            try:
                hash_code, file_content = self.get_hash_and_content(file_path)
            except FileNotFoundError:
                continue

            self.check_file(file_path, f, hash_code, file_content, t)

            # logging progress
            self.log(self._total_files, self._already_checked, self._last_perc)
            self._already_checked += 1

    def find_type(self, filename: str) -> Optional[str]:
        """
            returns the type of the file if its type is in self._types else None
        """
        for t in self._types:
            if filename.endswith(t):
                return t
        return None

    def get_hash_and_content(self, file_path: str) -> tuple[str, bytes]:
        """
            returns the hash-value (first) and the content (second) of the file at the given path
        """
        hash_code = ""
        file_content = ""
        with open(file_path, "rb") as newFile:
            file_content = newFile.read()
        hash_code = hashlib.blake2b(file_content).hexdigest()
        return hash_code, file_content

    def check_file(self, file_path: str, f: str, hash_code: str, file_content: bytes, t: str):
        """
            checks whether we already found a version of this file and performs the corresponding action
        """
        # get the dict responsible for the file type
        d = self._files[t]
        if hash_code not in d:
            # when there isn't this hash_code as key already, start a new list since we haven't seen this file yet
            # we're done
            d[hash_code] = [file_path]
            return

        # otherwise: there were already files with that hash-value so we have to check if they're the same
        # check for all the file in this list, if the contents match
        for original_file_path in d[hash_code]:
            try:
                if not self.files_are_equal(file_content, original_file_path):
                    continue  # check for the next file
            except FileNotFoundError:
                continue

            # we found a duplicate
            # we want to write that file into the duplicates folder, 
            # but when it happens that there already is a file with the same name we append the new one by a suffix
            without_extension = self.get_filename(f)
            suffix = self.get_suffix(without_extension, t)
            dest_path = self._abs_path + "duplicates/" + t[1:] + "/" + without_extension + suffix + t

            # moving the duplicate to the duplicates folder
            shutil.move(file_path, dest_path)

            # update list of duplicates to later write the file
            self._duplicates.append(self.DuplicateEntry(without_extension + suffix + t, original_file_path))

            # since we already found out, we're dealing with a duplicate we don't have to look any further
            return

        else:
            # didn't find a duplicate in the list, so it must be a new one
            # -> write it to the list
            d[hash_code].append(file_path)

    def files_are_equal(self, file_content: bytes, path_to_other: str) -> bool:
        """
            checks if the file at path_to_other has the content file_content
        """
        with open(path_to_other, "rb") as other_file:
            return file_content == other_file.read()

    def get_suffix(self, without_extension: str, t: str) -> str:
        """
            finds a suffix to the filename without_extension such that there won't be files with the same name
        """
        suffix = ""
        while os.path.exists(self._abs_path + "duplicates/" + t[1:] + "/" + without_extension + suffix + t):
            if suffix == "":
                suffix = "1"
            else:
                suffix = str(int(suffix) + 1)
        return suffix

    def write_duplicates_file(self):
        with open(self._abs_path + "duplicates/duplicates.txt", "a", encoding="utf-8") as duplicatesFile:
            for entry in self._duplicates:
                duplicatesFile.write(entry.name_in_duplicates + "," + entry.orig_path + "\n")


@dataclass
class CmdLineReturn:
    """
        class that holds the information needed to build up the DuplicateFinder Object.
        folders_file and types_file are paths to text-files that hold the corresponding data
    """
    folders_file: str
    types_file: str
    recursion: bool


def parse_argv(argv: list) -> CmdLineReturn:
    """
        parses the cmd-line-arguments
    """
    structure = "dif.py -f <searchspace_file> -t <types_file> [-r]"

    try:
        opts, args = getopt(argv, "hrf:t:", ["help", "folders=", "types="])
    except GetoptError:
        print(structure)
        sys.exit(2)

    searchspace: str = ""
    types: str = ""
    recursion: bool = False
    for opt, arg in opts:
        if opt in ("-f", "--folders"):
            searchspace = arg
            continue
        elif opt in ("-t", "--types"):
            types = arg
            continue
        elif opt in ("-h", "--help"):
            print(structure)
            sys.exit()
        recursion = opt == "-r"
        print(recursion)

    if not os.path.isfile(searchspace):
        print(f"Valid file for searchspace must be given! Got {searchspace}")
        print(structure)
        sys.exit(2)
    if not os.path.isfile(types):
        print(f"Valid file for types must be given! Got {types}")
        print(structure)
        sys.exit(2)

    return CmdLineReturn(searchspace, types, recursion)


def main(argv: list):
    config: CmdLineReturn = parse_argv(argv)
    finder: DuplicateFinder = DuplicateFinder()
    finder.extract_folders_from_file(config.folders_file)
    finder.extract_types_from_file(config.types_file)
    finder.set_recursion(config.recursion)
    finder.find_duplicates()


if __name__ == "__main__":
    main(sys.argv[1:])
