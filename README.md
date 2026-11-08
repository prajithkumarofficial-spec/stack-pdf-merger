# Stack PDF Merger

Stack PDF Merger is a native Arch Linux desktop app for joining PDFs in the order you choose. It does not run a web server and it does not upload files.

The custom Stack icon and dark violet theme keep the app easy to spot in your desktop and window switcher. Merging runs in a background worker, so large documents do not freeze the window.

## Run it on Arch Linux

Install the desktop dependencies, then launch the app:

```sh
sudo pacman -S python pyside6 poppler
./run.sh
```

To install from this repository:

```sh
./install.sh
```

Or build and install the package directly with `makepkg -si`.

## Use it

Add PDFs with the file picker or drag them into the window. Drag rows to reorder them, remove any selected file, then choose **Merge PDFs** and a destination. The original files are left in place.

The app uses Poppler's `pdfunite` for merging. If it is unavailable, install the optional Python fallback with `python -m pip install -r requirements.txt`.
