# CidreMaker 4

Portable desktop application for cider and wine production management.

## Prototype status

This first prototype establishes the desktop shell and navigation. It currently uses demonstration data held in memory. Database persistence, production calculations, import/export and backup are planned for subsequent milestones.

## Technology

- Rust
- egui / eframe
- SQLite (planned; not yet connected)

## Portable layout

The application is designed to keep its data beside the executable:

```
CidreMaker4/
  CidreMaker4.exe
  CidreMakerData/
    cidremaker.db
    Photos/
    Backups/
    Exports/
```

The current prototype creates the `CidreMakerData` directory beside the executable (or in the current directory if the executable path cannot be resolved). It does not yet write a database.

## Run from source

Install the Rust stable toolchain, then run:

```powershell
cargo run
```

## Build a portable Windows executable

```powershell
cargo build --release
```

The executable will be in `target\release\cidremaker4.exe`. Copy it to any folder or USB drive. The data folder is created next to the executable on first launch.
