# Home: a bear cartoon (Blender 5.3)

These are Python scripts that build the film in Blender. Each script builds a full scene: the set, the bears, the animation, the cameras and the render settings.

| File | What it is |
|---|---|
| `bears.py` | The two plush bears from Quiet Moon, rebuilt in Blender with the same sculpted body as the app (`sculptBear`/`buildBear`). They have a 12-bone rig, real hair fur, glossy eyes, closed eyes, heart eyes, a nose, a stitched mouth and paw pads. She also has her blush, three eyelashes and the rose. Also contains the walk cycle and posing helpers. |
| `film.py` | Shared toolkit: **the timeline** (every scene's start and end in the song, plus its captions), sky and sun, materials, trees, cameras and cuts, the magnetic hearts, the car, and the render settings. |
| `scene01_helsinki.py` … `scene16_home.py` | One script per scene. Each builds its sets, the bears, the animation and the camera cuts, timed to its part of the song. |
| `make_preview.py` | Turns rendered frames into an mp4 and burns in the captions (Cormorant Garamond italic). It can also join every scene into the whole film and lay the song underneath. |
| `render_colab.ipynb` | Renders scenes on Google Colab's free T4 GPU into your Google Drive. It can be resumed. |
| `render_laptop.bat` | Renders scenes on the Windows laptop with EEVEE. It can be resumed. |
| `bear_portraits.py` | Reference images of the bears, for AI video tools. |

## The scenes and the song (5:05)

| # | Scene | Song |
|---|---|---|
| 1 | Helsinki in spring: the cathedral, melting snow, three glimpses that warm each time | 0:00–0:32 |
| 2 | "It feels like home": a night window seat facing the floodlit cathedral | 0:32–0:50 |
| 3 | Asking her out: the blue-hour esplanade, his paw, her paw | 0:50–1:02 |
| 4 | First date at Kaitalampi: the granite knoll, the paw, the lean, then night with stars and fireflies | 1:02–1:28 |
| 5 | Ordinary evenings: the balcony at sunset, movie glow, asleep on the sofa | 1:28–1:44 |
| 6 | The magnetic hearts: the click, the night, the trade in the morning | 1:44–2:04 |
| 7 | The storm: the heart turns grey, a silent drive in the rain, she walks away | 2:04–2:30 |
| 8 | The Baltic Sea: he throws the hearts, they click while sinking and glow on the sea floor | 2:30–2:48 |
| 9 | The call: "Alona" on his phone; the harbour bench from night to dawn | 2:48–3:04 |
| 10 | "Please drive": the packed car, sunrise, the open road | 3:04–3:18 |
| 11 | June, the train to Kyiv: fields, the platform, the run into a hug | 3:18–3:34 |
| 12 | The road north (montage): map, Palanga, Latvia, his parents' farm, the waterfall, Tallinn, berries, Helsinki | 3:34–4:04 |
| 13 | Through the storms: the tree on the hill, she runs, he chases, the scared part said out loud | 4:04–4:35 |
| 14 | The Rainbow Bridge in Kyiv: the proposal in the quiet break | 4:35–4:47 |
| 15 | The wedding: the flower arch, the rings, the kiss, petals | 4:47–4:57 |
| 16 | Home: back on the cliff with rings, then down to the glowing heart | 4:57–5:05 |

To change any timing or caption, edit `TIMELINE` in `film.py`. Every scene follows it.

## Look at a scene on the laptop

1. Put all the `.py` files in one folder (keep the `fonts` folder next to them).
2. In Blender 5.3, go to **Scripting** → **Open** → `sceneNN_….py` → **Run Script**. This builds the scene and saves `sceneNN.blend`.
3. Press **Space** to play it, or **F12** to render a frame. The camera cuts are timeline markers.

## Render the film

- **Colab (free GPU):** open `render_colab.ipynb` in Colab and follow the notes in it. Frames land in Google Drive (`home-film/renders/sceneNN/`).
- **Laptop (EEVEE):** double-click `render_laptop.bat`, or run `render_laptop.bat 04 05` for chosen scenes. Frames land in `renders\sceneNN\`.
- Either way, finished frames are skipped, so a render can always be resumed.

## Make the video with the song

Put the renders folder and the MP3 on your computer (never in the repo), then run:

```
python make_preview.py film home_film.mp4 renders --song "I Want to Know What Love Is.mp3"
```

This needs Python with Pillow, and ffmpeg. The result is a 9:16 mp4 with captions and music, ready for your phones.

## Privacy

This repo is public. The song, the renders and the `.blend` files stay out of it (see `.gitignore`). The captions are in `film.py`, so if the story text should stay private, move this folder to a private repo.
