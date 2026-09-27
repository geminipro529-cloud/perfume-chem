Historical test inputs only; not current stock or compounding authority.

Source: Git commit `8d5cb54bd5f045c3d804a370069d7a464a6ed920`, paths `inventory.txt` and `data/materials/O.yaml`.
The original receipt pins CRLF bytes. Tests reconstruct CRLF deterministically
and validate the original size and SHA-256 without changing production pins.
Live inventory files are never replaced by these fixtures.
