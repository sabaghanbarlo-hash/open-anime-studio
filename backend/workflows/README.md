# ComfyUI workflow templates

The backend drives ComfyUI by loading **API-format workflow JSON** and replacing placeholders.

| Placeholder | Meaning |
|---|---|
| `{{CHECKPOINT}}` | SDXL checkpoint filename (from `OAS_SDXL_CHECKPOINT`) |
| `{{PROMPT}}`, `{{NEGATIVE}}` | Positive / negative prompt |
| `{{WIDTH}}`, `{{HEIGHT}}` | Output size (integers) |
| `{{SEED}}` | Random seed |
| `{{REFERENCE}}` | Uploaded reference image name (IP-Adapter template only) |
| `{{IMAGE}}` | Uploaded keyframe name for image-to-video templates |
| `{{LENGTH}}` | Frame count, already snapped to the model's rule (LTX: 8k+1, Wan: 4k+1) |
| `{{FPS}}` | Frames per second |

## Included

- `sdxl_keyframe.json` - plain SDXL text-to-image. Needs only core ComfyUI nodes.
- `sdxl_keyframe_ipadapter.json` - **experimental, untested.** Needs the `ComfyUI_IPAdapter_plus` custom nodes and an SDXL IP-Adapter model. If node names differ in your install, re-export it from your own ComfyUI and keep the placeholders.

## You must add (image-to-video)

Video graphs depend on the exact ComfyUI version and the model files you downloaded, so they are **not** bundled as guesses. Create them from ComfyUI's own templates:

1. In ComfyUI open **Workflow > Browse Templates** and load the LTX-Video (or Wan 2.2) **image-to-video** template. Download any model files it asks for.
2. Run it once by hand to confirm it works on your GPU.
3. Replace the values with the placeholders above: the Load Image node's image becomes `{{IMAGE}}`, the prompts become `{{PROMPT}}` / `{{NEGATIVE}}`, width/height/length/fps/seed likewise.
4. Make sure the graph ends in a node that **saves an mp4** (SaveVideo or VHS Video Combine).
5. Use **Export (API)** and save it as `video_ltx.json` or `video_wan22.json` in this folder.
6. Restart the backend. The provider shows as configured in the UI.

Placeholders that are the whole string value are replaced with real numbers, so `"width": "{{WIDTH}}"` becomes `"width": 832`.
