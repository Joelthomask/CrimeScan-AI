import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models._utils as _utils
from .net import MobileNetV1, FPN, SSH

class ClassHead(nn.Module):
    def __init__(self, inchannels=512, num_anchors=3):
        super().__init__()
        self.num_anchors = num_anchors
        self.conv1x1 = nn.Conv2d(inchannels, self.num_anchors*2, kernel_size=1, stride=1, padding=0)

    def forward(self, x):
        out = self.conv1x1(x)
        out = out.permute(0,2,3,1).contiguous()
        return out.view(out.shape[0], -1, 2)

class BboxHead(nn.Module):
    def __init__(self, inchannels=512, num_anchors=3):
        super().__init__()
        self.conv1x1 = nn.Conv2d(inchannels, num_anchors*4, kernel_size=1, stride=1, padding=0)

    def forward(self, x):
        out = self.conv1x1(x)
        out = out.permute(0,2,3,1).contiguous()
        return out.view(out.shape[0], -1, 4)

class LandmarkHead(nn.Module):
    def __init__(self, inchannels=512, num_anchors=3):
        super().__init__()
        self.conv1x1 = nn.Conv2d(inchannels, num_anchors*10, kernel_size=1, stride=1, padding=0)

    def forward(self, x):
        out = self.conv1x1(x)
        out = out.permute(0,2,3,1).contiguous()
        return out.view(out.shape[0], -1, 10)


class RetinaFace(nn.Module):
    def __init__(self, cfg=None, phase='train'):
        """
        RetinaFace model without default pretrain.
        Weights should be loaded externally via your wrapper.
        """
        super().__init__()
        self.phase = phase
        backbone = None

        # Build backbone
        if cfg['name'] == 'mobilenet0.25':
            backbone = MobileNetV1()
            # skip pretrain entirely
        elif cfg['name'].lower() == 'resnet50':
            import torchvision.models as models
            backbone = models.resnet50(pretrained=False)  # no pretrain

        self.body = _utils.IntermediateLayerGetter(backbone, cfg['return_layers'])

        # FPN + SSH
        in_channels_stage2 = cfg['in_channel']
        in_channels_list = [
            in_channels_stage2 * 2,
            in_channels_stage2 * 4,
            in_channels_stage2 * 8
        ]
        out_channels = cfg['out_channel']
        self.fpn = FPN(in_channels_list, out_channels)
        self.ssh1 = SSH(out_channels, out_channels)
        self.ssh2 = SSH(out_channels, out_channels)
        self.ssh3 = SSH(out_channels, out_channels)

        # Prediction heads
        self.ClassHead = self._make_class_head(fpn_num=3, inchannels=out_channels)
        self.BboxHead = self._make_bbox_head(fpn_num=3, inchannels=out_channels)
        self.LandmarkHead = self._make_landmark_head(fpn_num=3, inchannels=out_channels)

    def _make_class_head(self, fpn_num=3, inchannels=64, anchor_num=2):
        return nn.ModuleList([ClassHead(inchannels, anchor_num) for _ in range(fpn_num)])

    def _make_bbox_head(self, fpn_num=3, inchannels=64, anchor_num=2):
        return nn.ModuleList([BboxHead(inchannels, anchor_num) for _ in range(fpn_num)])

    def _make_landmark_head(self, fpn_num=3, inchannels=64, anchor_num=2):
        return nn.ModuleList([LandmarkHead(inchannels, anchor_num) for _ in range(fpn_num)])

    def forward(self, inputs):
        out = self.body(inputs)
        fpn = self.fpn(out)

        feature1 = self.ssh1(fpn[0])
        feature2 = self.ssh2(fpn[1])
        feature3 = self.ssh3(fpn[2])
        features = [feature1, feature2, feature3]

        bbox_regressions = torch.cat([self.BboxHead[i](f) for i, f in enumerate(features)], dim=1)
        classifications = torch.cat([self.ClassHead[i](f) for i, f in enumerate(features)], dim=1)
        ldm_regressions = torch.cat([self.LandmarkHead[i](f) for i, f in enumerate(features)], dim=1)

        if self.phase == 'train':
            return bbox_regressions, classifications, ldm_regressions
        else:
            return bbox_regressions, F.softmax(classifications, dim=-1), ldm_regressions
