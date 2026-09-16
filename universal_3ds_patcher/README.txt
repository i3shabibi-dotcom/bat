Arabic Hesham - Universal 3DS Patcher
=====================================

Usage
-----
1. Run Arabic_Hesham_3DS_Patcher.exe.
2. Choose an .ah3p patch file.
3. Choose the original .3ds/.cci image required by that patch.
4. The tool verifies the source SHA-256, applies the RomFS overlay, preserves the original file, and creates a separate patched .3ds.
5. The rebuilt output is re-opened and every patched RomFS file is SHA-256 verified before success is reported.

AH3P patch format
-----------------
AH3P is a normal ZIP container with a different extension. It contains patch.json plus a romfs/ directory. patch.json declares the accepted source hashes and the SHA-256 of every overlay file. The executable is generic; adding a new game/localization only requires creating a new AH3P package, not rebuilding the program.

Current test patch included in this build
-----------------------------------------
Story of Seasons: Trio of Towns (USA) Arabic Runtime10.

Notes
-----
- The source game is never modified in place.
- The tool is intended for compatible decrypted Nintendo 3DS/CCI images that 3dstool can rebuild.
- No Python, PowerShell, CMD, 7-Zip, WinRAR, or separately installed 3dstool is required by the end user.
