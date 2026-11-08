# Stack PDF Workbench

Stack PDF Workbench is a native Arch Linux desktop app for everyday PDF assembly and page operations. It does not run a web server and it does not upload files.

The dark violet interface keeps the app easy to spot in your desktop and window switcher. PDF work runs in a background worker, so larger documents do not freeze the window. The app always writes a new output file and leaves the source PDFs in place.

## Run it on Arch Linux

Install the desktop dependencies, then launch the app:

```sh
sudo pacman -S python pyside6 python-pypdf python-cryptography
./run.sh
```

To install from this repository:

```sh
./install.sh
```

Or build and install the package directly with `makepkg -si`.

## Use it

Add PDFs with the file picker or drag them into the window. Drag rows to reorder them, remove any selected file, then choose **Merge files** and a destination.

Select one PDF to use the quick tools:

- **Extract pages** saves the chosen pages into a new PDF. Enter ranges like `1-3, 5, 8-end`.
- **Split into pages** writes one PDF per page to a folder you choose.
- **Rotate** applies a clockwise 90°, 180°, or 270° turn to the selected pages.
- **Optimize** compresses page content streams and removes duplicate objects where possible. It is lossless and may not reduce image-heavy files.
- **Protect** encrypts a new copy with AES-256 and a password you enter twice.

Password-protected source PDFs can be unlocked for supported operations. Originals are never overwritten. Files remain on this device throughout; there are no uploads or telemetry.
