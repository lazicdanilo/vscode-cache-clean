#!/usr/bin/env python

# Standard library imports (no installation needed)
import shutil
import os
import json

# Third-party library imports (need to be installed)
import click
from colorama import init, Fore, Back, Style
import send2trash


class VsCodeCacheClean:
    CHECK_FOLDERS = ["Code", "Code - OSS"]
    WORKSPACE_STORAGE_PATH = "User/workspaceStorage/"
    WORKSPACE_FILE = "workspace.json"

    def __init__(self, path, dry_run):
        """
        Initialize the class
        Args:
            path (str): Path to the vscode cache folder
            dry_run (bool): Flag to do a dry run. If True, nothing will be deleted
        """
        self.dry_run = dry_run
        self.path = path
        self.non_existent_workspaces = {}
        init()

    def _get_workspace_from_folder(self, folder: str) -> str:
        """
        Get the workspace path from cache data
        Args:
            folder (str): Path to the cache folder
        Returns:
            str: Path to the workspace
        """
        workspace_file = os.path.join(folder, self.WORKSPACE_FILE)
        raw_json = ""
        if os.path.exists(workspace_file):
            with open(workspace_file, "r") as f:
                raw_json = f.read()

        if raw_json:
            try:
                json_folder = json.loads(raw_json)["folder"]
                return json_folder[7:]  # Remove the "file://" from the path
            except json.JSONDecodeError:
                print(Fore.RED + f"Error decoding JSON for {folder}" + Fore.RESET)
                return ""
        return ""

    def _get_size_of_folder(self, folder: str) -> int:
        """
        Get the size of the folder by looping through all the files and subfolders
        Args:
            folder (str): Path to the folder
        Returns:
            int: Size of the folder in bytes
        """
        size_on_disk = 0
        for root, dirs, files in os.walk(folder):
            size_on_disk += sum(
                os.path.getsize(os.path.join(root, name)) for name in files
            )
        return size_on_disk

    def _find_all_workspaces(self, in_path) -> dict:
        """
        Finds all the cached folders in the cache folder
        Args:
            in_path (str): Path to the cache folder
        Returns:
            dict: Dictionary of all the cached folders
        """
        ret = {}
        for folder in self.CHECK_FOLDERS:
            dir = os.path.join(in_path + folder, self.WORKSPACE_STORAGE_PATH)
            try:
                folder_name = [f for f in os.listdir(dir)]
            except FileNotFoundError:
                print(Fore.YELLOW + f"Folder {dir} not found. Skipping..." + Fore.RESET)
                continue
            for f in folder_name:
                ret.update(
                    {
                        os.path.join(dir, f): {
                            "workspace": self._get_workspace_from_folder(
                                os.path.join(dir, f)
                            ),
                            "size": self._get_size_of_folder(os.path.join(dir, f)),
                        }
                    }
                )
        return ret

    def _find_non_existent_workspaces(self, cached_folder_path: dict) -> dict:
        """
        Loops over all the cached folders and finds the worlspaces that don't exist
        Args:
            cached_folder_path (dict): Dictionary of all the cached folders
        Returns:
            dict: Dictionary of all the non-existent workspaces
        """
        ret = {}
        for folder, workspace in cached_folder_path.items():
            if not os.path.exists(workspace["workspace"]):
                ret.update({folder: workspace})
        return ret

    def _scan(self) -> dict:
        """
        Scans the cache folder and finds all the non-existent workspaces
        Returns:
            dict: Dictionary of all the non-existent workspaces
        """
        all_cache_data = self._find_all_workspaces(self.path)

        if not all_cache_data:
            print(
                Fore.RED
                + f"No cache folder found. Looked in {self.path} for {self.CHECK_FOLDERS}"
                + Fore.RESET
            )
            exit(0)

        return self._find_non_existent_workspaces(all_cache_data)

    def _get_user_input(self, non_existent_workspaces: dict) -> dict:
        """
        Get user input on which folders to delete
        Args:
            non_existent_workspaces (dict): Dictionary of all the non-existent workspaces
        Returns:
            dict: Dictionary of all the folders to delete
        """
        
        if not non_existent_workspaces:
            print(Fore.LIGHTGREEN_EX + "No non-existent workspaces found" + Fore.RESET)
            exit(0)

        print(
            Fore.LIGHTGREEN_EX
            + "Found the following non-existent workspaces:"
            + Fore.RESET
        )
        print(
            "|"
            + Fore.LIGHTGREEN_EX
            + f" <<< Number >>> "
            + Fore.RESET
            + "|"
            + Fore.LIGHTMAGENTA_EX
            + f" <<< Non existing workspace path >>> "
            + Fore.RESET
            + "|"
            + Fore.LIGHTRED_EX
            + f" <<< Cached dir size >>> "
            + Fore.RESET
            + "|"
            + Fore.BLUE
            + f" <<< Cached dir path >>> "
            + Fore.RESET
            + "|"
        )

        sum_size = 0
        for i, (folder, workspace) in enumerate(non_existent_workspaces.items()):
            print(
                Fore.LIGHTGREEN_EX
                + f"{i+1}: "
                + Fore.LIGHTMAGENTA_EX
                + f"{workspace['workspace']}"
                + Fore.LIGHTRED_EX
                + f" [{workspace['size'] / 1024 / 1024:.2f} MB]"
                + Fore.BLUE
                + f" ({folder})"
                + Fore.RESET
            )
            sum_size += workspace["size"]

        print(
            Fore.LIGHTYELLOW_EX
            + "\nTotal size of non-existent workspaces: "
            + f"{sum_size / 1024 / 1024:.2f} MB, {sum_size / 1024 / 1024 / 1024:.2f} GB\n"
            + Fore.RESET
        )
        print(
            Fore.LIGHTGREEN_EX
            + "Type 'a' to delete all, 'n' to exit or 'd' to selectively delete (select numbers)"
            + Fore.RESET
        )

        user_input = input(">>> ")

        if user_input == "n":
            print(Fore.LIGHTGREEN_EX + "Exiting" + Fore.RESET)
            exit(0)
        elif user_input == "a":
            return non_existent_workspaces
        elif user_input == "d":
            print(
                Fore.LIGHTGREEN_EX
                + "Enter the numbers of the folders to delete separated by a space"
                + Fore.RESET
            )
            print(
                Fore.LIGHTGREEN_EX + "You can also input a range like 1-3" + Fore.RESET
            )
            user_input = input(">>> ")
            try:
                user_input = user_input.split(" ")

                selected_folders = []
                for i in user_input:
                    if "-" in i:
                        start, end = i.split("-")
                        selected_folders.extend(range(int(start), int(end) + 1))
                    else:
                        selected_folders.append(int(i))
            except ValueError:
                print(Fore.LIGHTRED_EX + "Invalid input. Exiting" + Fore.RESET)
                exit(0)

            selected_folders = list(set(selected_folders))

            non_existent_workspaces = {
                k: v
                for i, (k, v) in enumerate(non_existent_workspaces.items())
                if i + 1 in selected_folders
            }

            print(Fore.LIGHTGREEN_EX + "Selected Folders:" + Fore.RESET)
            sum_size = 0
            for folder, workspace in non_existent_workspaces.items():
                print(
                    Fore.LIGHTMAGENTA_EX
                    + f"{workspace['workspace']}"
                    + Fore.LIGHTRED_EX
                    + f" [{workspace['size'] / 1024 / 1024:.2f} MB]"
                    + Fore.BLUE
                    + f" ({folder})"
                    + Fore.RESET
                )
                sum_size += workspace["size"]

            print(
                Fore.LIGHTYELLOW_EX
                + "\nTotal size of selected non-existent workspaces: "
                + f"{sum_size / 1024 / 1024:.2f} MB, {sum_size / 1024 / 1024 / 1024:.2f} GB\n"
                + Fore.RESET
            )
            print(
                Fore.LIGHTGREEN_EX
                + "Do you want to delete the above folders? (y/n)"
                + Fore.RESET
            )
            user_input = input(">>> ")

            if user_input == "n":
                print(Fore.LIGHTGREEN_EX + "Exiting" + Fore.RESET)
                exit(0)
            elif user_input == "y":
                return non_existent_workspaces
            else:
                print(Fore.LIGHTRED_EX + "Invalid input. Exiting" + Fore.RESET)
                exit(0)

        else:
            print(Fore.LIGHTRED_EX + "Invalid input. Exiting" + Fore.RESET)
            exit(0)

    def _remove_folders(self, for_removal: dict) -> None:
        """
        Remove the folders
        Args:
            for_removal (dict): Dictionary of all the folders to delete
        """
        if self.dry_run:
            print(Fore.LIGHTGREEN_EX + "Dry run. Not deleting anything" + Fore.RESET)
            return

        # Check if user wants to delete the folders or move them to trash
        print(
            Fore.LIGHTGREEN_EX
            + "Do you want to move the folders to trash (t) or delete them permanently (d)?"
            + Fore.RESET
        )
        user_input = input(">>> ")

        if user_input == "t":
            for folder, workspace in for_removal.items():
                print(
                    Fore.LIGHTGREEN_EX
                    + f"Moving {workspace['workspace']} to trash"
                    + Fore.RESET
                )
                try:
                    send2trash.send2trash(folder)
                except Exception as e:
                    print(
                        Fore.LIGHTRED_EX
                        + f"Error moving {workspace['workspace']} to trash: {e}"
                        + Fore.RESET
                    )
        elif user_input == "d":
            for folder, workspace in for_removal.items():
                print(
                    Fore.LIGHTGREEN_EX
                    + f"Deleting {workspace['workspace']}"
                    + Fore.RESET
                )
                try:
                    shutil.rmtree(folder)
                except Exception as e:
                    print(
                        Fore.LIGHTRED_EX
                        + f"Error deleting {workspace['workspace']}: {e}"
                        + Fore.RESET
                    )
        else:
            print(Fore.LIGHTRED_EX + "Invalid input. Exiting" + Fore.RESET)
            exit(0)

    def run(self):
        non_existent_workspaces = self._scan()
        for_removal = self._get_user_input(non_existent_workspaces)
        self._remove_folders(for_removal)


@click.command()
@click.option(
    "--path",
    "-p",
    default=f"{os.environ.get('HOME')}/.config/",
    help="Path to the vscode cache folder. Default: ~/.config/",
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    default=False,
    help="Do a dry run. Nothing will be deleted",
)
@click.help_option("-h", "--help")
def cli(path, dry_run):
    vsccc = VsCodeCacheClean(path, dry_run)
    vsccc.run()


if __name__ == "__main__":
    cli()
