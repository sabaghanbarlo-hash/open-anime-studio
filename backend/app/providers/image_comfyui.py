from __future__ import annotations

from .. import config
from ..errors import ProviderError, ProviderNotConfigured
from . import comfy_client
from .base import GenResult, ImageProvider, ImageRequest


class ComfyImageProvider(ImageProvider):
    id = 'comfyui-sdxl'
    name = 'ComfyUI - SDXL anime checkpoint (+ optional IP-Adapter)'
    requires_gpu = True
    license_note = 'License depends on the checkpoint you choose. Read its model card before publishing output.'

    def configured(self):
        if not config.SDXL_CHECKPOINT:
            return False, 'Set OAS_SDXL_CHECKPOINT to a checkpoint filename inside ComfyUI/models/checkpoints.'
        if not (config.WORKFLOW_DIR / 'sdxl_keyframe.json').exists():
            return False, 'backend/workflows/sdxl_keyframe.json is missing.'
        return True, ''

    async def generate(self, req: ImageRequest) -> GenResult:
        ok, detail = self.configured()
        if not ok:
            raise ProviderNotConfigured(detail)
        if not await comfy_client.client.is_up():
            raise ProviderError('ComfyUI is not reachable at ' + config.COMFY_URL + '. Start ComfyUI first.')
        notes = []
        template = 'sdxl_keyframe.json'
        values = {
            'CHECKPOINT': config.SDXL_CHECKPOINT,
            'PROMPT': req.prompt,
            'NEGATIVE': req.negative_prompt,
            'WIDTH': req.width,
            'HEIGHT': req.height,
            'SEED': req.seed,
        }
        if req.reference_image:
            if (config.WORKFLOW_DIR / 'sdxl_keyframe_ipadapter.json').exists():
                values['REFERENCE'] = await comfy_client.client.upload_image(req.reference_image)
                template = 'sdxl_keyframe_ipadapter.json'
                notes.append('Reference image applied through the IP-Adapter workflow.')
            else:
                notes.append('Reference image ignored: sdxl_keyframe_ipadapter.json is not installed, so consistency relies on the character prompt only.')
        else:
            notes.append('No reference image: consistency relies on the character prompt only.')
        workflow = comfy_client.fill_template(comfy_client.load_template(template), values)
        entry = await comfy_client.client.run(workflow, timeout=1200)
        files = comfy_client.client.output_files(entry)
        if not files:
            raise ProviderError('ComfyUI finished but returned no image.')
        data = await comfy_client.client.download(files[-1])
        req.output.parent.mkdir(parents=True, exist_ok=True)
        req.output.write_bytes(data)
        notes.append('seed ' + str(req.seed))
        return GenResult(req.output, notes)
