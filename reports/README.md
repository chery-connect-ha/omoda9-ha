# Vehicle reports

One file per car, produced by Home Assistant, not written by hand.

## How to add yours

1. In Home Assistant: **Settings -> Devices & services -> Chery Connect -> the
   three dots -> Download diagnostics.** Needs `v1.14.0-beta.10` or later;
   earlier versions do not report the vehicle.
2. **Look at the file.** It is written to redact VIN, email address, vehicle PIN
   and coordinates, and this directory is public and permanent. If you see
   something in it you would rather not publish, stop and say so on
   [the discussion](https://github.com/chery-connect-ha/omoda9-ha/discussions/82)
   instead.
3. **Rename it** `<brand>-<model>-<region>.json`, lowercase, for example
   `omoda-omoda-5-ev-it.json`. This is not tidiness: the diagnostics redacts
   what is *inside* the file and nothing checks what the file is *called*, and a
   committed filename is in the git history exactly like its contents. CI
   refuses a name carrying a VIN or an email address, but renaming it yourself
   is the point at which you look.
4. Open a pull request with it in this directory.

CI validates it. If something is wrong the check says what, in words.

## Why a file in the repository rather than an attachment somewhere

Because the checks can only run on something the CI can read, and the most
important check protects you: a diagnostics file that slipped through
unredacted, once committed, is in the git history for good. Deleting the file
afterwards does not remove it, and whoever cloned already has it. So it is
verified before the merge, every time, rather than when somebody remembers.

## What is checked

- **no VIN, email address, coordinates or token** - the one that is about you;
- **a confirmed BEV has no combustion sensors.** If the file says both, one of
  the two is wrong, and which one is precisely what this collection exists to
  find out. That is an issue to open, not a file to fix;
- **every entity id is one this integration knows how to produce.** An unknown
  one means a different version, or a hand-edited file;
- internal consistency: the count matches the list, brand and model are filled
  in.

`docs/tested-models.md` is generated from these files and is not edited by hand.
