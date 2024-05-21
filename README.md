# VSCode Cache Clean

This is a simple script to clean the cache of Visual Studio Code. By default, this script analyzes the following folders:

- `~/.config/Code/User/workspaceStorage/`
- `~/.config/Code - OSS/User/globalStorage/`

In the above-mentioned folders, VSCode stores the cache of extensions and workspaces. If the folder where VSCode was run is large, the cache can grow significantly and consume a lot of disk space. Additionally, if the original folder where VSCode was run is deleted, the cache is not automatically removed. This script analyzes the cached data, checks if the original folder exists, and presents the user with the option to delete the cache if the original folder does not exist.

The script was tested on Arch Linux with Python 3.12.3 and Visual Studio Code 1.89.1.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 vscode_cache_clean.py
```
