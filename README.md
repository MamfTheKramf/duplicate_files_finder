## How To Use
1. download the repository,
2. install python3 ([Python download page](https://www.python.org/downloads/))
3. locate all the folders you want to search for duplicate files and copy their _absolute_ path into `searchSpace.txt` (use a new line for each path),
4. for each file extension of which you want to find duplicates: write the file extension into `fileTypes.txt` (again, use a new line for each type). E.g. when you want to find duplicate PNGs write a line with `.png`
5. go inside the folder of `dff.py` and run `python3 dff.py -f searchSpace.txt -t fileTypes.txt [-r]` (`-r` being in square brackets means that this is optional. If set the subdirectories of the folders in `searchSpace.txt` will be searched recursively for duplicates as well. If you don't want this, leave it out of the command.)
    Note: you don't have to use the available files `searchSpace.txt` and `fileTypes.txt`. You can make your own files (located where ever you want) and provide their paths as arguments.