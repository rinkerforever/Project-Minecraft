# Spawner Placer

This is a standalone Forge mod workspace for Minecraft `26.3`.

## What it does

- Adds a craftable `Mob Spawner` item.
- Placing the item places the vanilla spawner block.
- After placing it, use any spawn egg on the spawner to choose which mob it spawns.
- The item is also added to the `Functional Blocks` creative tab.

## Crafting recipe

```text
Iron Bars  Iron Bars  Iron Bars
Iron Bars  Diamond    Iron Bars
Obsidian   Obsidian   Obsidian
```

## Build notes

- Forge version is set to `26.3-66.0.2`.
- Java target is `25`, matching Forge's Minecraft `26.3` toolchain.
- Build from this directory with `./gradlew build` on macOS/Linux or `./gradlew.bat build` on Windows.
- On this machine, `JAVA_HOME` currently points to an old Java 8 installation. Before building in PowerShell, run `$env:JAVA_HOME = 'C:\Program Files\Java\jdk-26.0.1'`.

## Install on a server

1. Run a Forge dedicated server for Minecraft `26.3` using Forge `66.0.2`. A vanilla server cannot load Forge mods.
2. Stop the server, then upload `build/libs/spawnerplacer-1.0.0.jar` through the manager's **Mods** page. The manager places it in the active profile's `mods` directory.
3. Restart the server. Its startup log should list `spawnerplacer` as a loaded mod.
4. Every player must run the same Forge `26.3-66.0.2` version and place the same JAR in their Minecraft client's `mods` directory before joining.

Use `/give @p spawnerplacer:mob_spawner` to verify the item after joining. It also appears in the Creative inventory's **Functional Blocks** tab.
