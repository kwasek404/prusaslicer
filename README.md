# Moje Profile PrusaSlicer

To repozytorium przechowuje moją osobistą konfigurację dla PrusaSlicer. Zawiera profile drukarek, filamentów oraz ustawień druku. Umożliwia to łatwą synchronizację ustawień pomiędzy różnymi komputerami i systemami operacyjnymi.

## Struktura

* `printer/` - Profile drukarek (np. ustawienia maszyny, G-code startowy/końcowy).
* `print/` - Profile ustawień druku (np. wysokość warstwy, prędkości, wypełnienie).
* `filament/` - Profile filamentów (np. temperatury, chłodzenie, ustawienia retrakcji).

---

## Instalacja

Poniższe kroki wyjaśniają, jak podlinkować profile z tego repozytorium do konfiguracji PrusaSlicer, aby program mógł z nich korzystać.

### 🐧 Linux

Na Linuksie folder konfiguracyjny PrusaSlicer znajduje się zazwyczaj w `~/.config/PrusaSlicer`.

1.  Sklonuj to repozytorium w wybranej lokalizacji, np. `~/repo/github.com/kwasek404/prusaslicer`.

2.  Przejdź do folderu konfiguracyjnego PrusaSlicer:
    ```bash
    cd ~/.config/PrusaSlicer
    ```

3.  Jeśli istnieją już foldery `filament`, `print` lub `printer`, usuń je lub zmień ich nazwy.
    ```bash
    # Opcja 1: Zmiana nazwy (bezpieczniej)
    mv filament filament.bak
    mv print print.bak
    mv printer printer.bak

    # Opcja 2: Usunięcie (jeśli jesteś pewien, że nie zawierają ważnych danych)
    # rm -rf filament print printer
    ```

4.  Utwórz dowiązania symboliczne (`symlinks`) do folderów w repozytorium (pamiętaj o dostosowaniu ścieżki źródłowej):
    ```bash
    # Zastąp <ścieżka-do-repo> właściwą ścieżką
    ln -s /home/kwasek/repo/[github.com/kwasek404/prusaslicer/filament](https://github.com/kwasek404/prusaslicer/filament) .
    ln -s /home/kwasek/repo/[github.com/kwasek404/prusaslicer/print](https://github.com/kwasek404/prusaslicer/print) .
    ln -s /home/kwasek/repo/[github.com/kwasek404/prusaslicer/printer](https://github.com/kwasek404/prusaslicer/printer) .
    ```

### 🪟 Windows

Na systemie Windows folder konfiguracyjny PrusaSlicer znajduje się w `%APPDATA%\PrusaSlicer`. Do tworzenia dowiązań symbolicznych wymagane są uprawnienia administratora.

1.  Sklonuj to repozytorium w wybranej lokalizacji, np. `C:\Users\kwase\repo\github.com\kwasek404\prusaslicer`.

2.  **Uruchom PowerShell jako Administrator.**

3.  Przejdź do folderu konfiguracyjnego PrusaSlicer:
    ```powershell
    cd $env:APPDATA\PrusaSlicer
    ```

4.  PrusaSlicer tworzy domyślne foldery przy pierwszym uruchomieniu. Zmień ich nazwy, aby uniknąć konfliktu.
    ```powershell
    Rename-Item -Path ".\filament" -NewName "filament.bak"
    Rename-Item -Path ".\print" -NewName "print.bak"
    Rename-Item -Path ".\printer" -NewName "printer.bak"
    ```

5.  Utwórz dowiązania symboliczne, wskazując na foldery w swoim repozytorium.
    ```powershell
    # Upewnij się, że ścieżka w parametrze -Target jest poprawna
    New-Item -ItemType SymbolicLink -Path ".\filament" -Target "C:\Users\kwase\repo\github.com\kwasek404\prusaslicer\filament"
    New-Item -ItemType SymbolicLink -Path ".\print"    -Target "C:\Users\kwase\repo\github.com\kwasek404\prusaslicer\print"
    New-Item -ItemType SymbolicLink -Path ".\printer"  -Target "C:\Users\kwase\repo\github.com\kwasek404\prusaslicer\printer"
    ```

6.  Po potwierdzeniu, że wszystko działa, możesz usunąć foldery z kopiami zapasowymi (`.bak`).
    ```powershell
    Remove-Item -Path ".\*.bak" -Recurse -Force
    ```