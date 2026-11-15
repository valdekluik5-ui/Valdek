# Home: a bear cartoon (Blender 5.3)

These are Python scripts that build the film in Blender. Each script builds a full scene: the set, the bears, the animation, the cameras and the render settings.

| File | What it is |
|---|---|
| `bears.py` | The two plush bears from Quiet Moon, rebuilt in Blender with the same sculpted body as the app (`sculptBear`/`buildBear`). They have a 12-bone rig, real hair fur, glossy eyes, closed eyes, heart eyes, a nose, a stitched mouth and paw pads. She also has her blush, three eyelashes and the rose. |
| `scene04_cliff.py` | Test shot for scene 4, the first date. The bears sit on granite cliffs about 45 m above a still lake, among pines, at sunset. His paw creeps to hers and she leans on his shoulder. It has three cameras: `Cam_Wide` (from behind, sun beyond), `Cam_Faces` (close, from over the drop) and `Cam_Establish` (the whole cliff from over the lake). |

## Run it on the laptop (EEVEE)

1. Put `bears.py` and `scene04_cliff.py` in the same folder.
2. In Blender, go to **Scripting** → **Open** → `scene04_cliff.py` → **Run Script**. The build takes about 30 s and saves `scene04_cliff.blend` next to the script.
3. Press **F12** to render frame 170. To change camera, right-click `Cam_Faces` or `Cam_Establish` in the Outliner and choose **Set Active Camera**.

You can also render from a terminal. This prints how long each frame took:

```
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b --python scene04_cliff.py -- --frames 170 --percent 50
```

Options go after `--`:
- `--frames 170`, `1-216` or `1-216x8` (every 8th frame)
- `--camera wide`, `faces` or `establish`
- `--engine eevee` or `cycles`, plus `--gpu` for Cycles on a GPU
- `--percent 50` (a share of 1080×1920)
- `--samples N`
- `--out folder`

Frames that already exist in the output folder are skipped, so a batch can always be resumed.

## Controls inside the .blend

- Each bear is an armature named `He` or `She`. Its custom property **eyes** sets the eyes: 0 open, 1 closed, 2 heart. You can keyframe it.
- Pose the bones like any rig. On each bone, Y runs along the bone and Z points to the bear's front.
- Fur settings live in `FUR` at the top of `bears.py`: length, density, droop and thickness.

## Privacy

This repo is public. The song stays out of it (see `.gitignore`).
