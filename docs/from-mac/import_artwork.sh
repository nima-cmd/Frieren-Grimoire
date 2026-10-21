#!/bin/zsh
# Copies the artwork in artwork/ into the app bundle (App/Artwork), resized.
# The originals in artwork/ are never modified.
set -euo pipefail
cd "$(dirname "$0")/.."
out=App/Artwork
mkdir -p "$out"
sips -s format jpeg -s formatOptions 82 -Z 1920 artwork/yHyB55x.jpg --out "$out/landscape.jpg" >/dev/null
sips -s format jpeg -s formatOptions 88 artwork/images.jpeg --out "$out/frieren-staff.jpg" >/dev/null
sips -s format jpeg -s formatOptions 88 artwork/does-frieren-think-about-or-even-consider-herself-as-cute-v0-e1smwo5pns9h1.webp --out "$out/frieren-scarf.jpg" >/dev/null
sips -s format png artwork/Frieren_anime_-_Fern_anime_profile_2.webp --out "$out/fern.png" >/dev/null
ls -l "$out"
