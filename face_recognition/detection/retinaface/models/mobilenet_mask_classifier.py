import torch
import torch.nn as nn
import torchvision.models as models


class MobileNetMaskClassifier(nn.Module):
    def __init__(self, num_classes=2, pretrained=True, fine_tune=True):
        super(MobileNetMaskClassifier, self).__init__()

        # Load MobileNetV2 backbone
        self.model = models.mobilenet_v2(
            weights=models.MobileNet_V2_Weights.IMAGENET1K_V1 if pretrained else None
        )

        # Replace classifier head (last layer)
        in_features = self.model.classifier[1].in_features
        self.model.classifier[1] = nn.Linear(in_features, num_classes)

        # Fine-tune or freeze backbone
        if not fine_tune:
            for param in self.model.features.parameters():
                param.requires_grad = False

    def forward(self, x):
        # Ensure input is on same device as model
        x = x.to(next(self.parameters()).device)
        return self.model(x)


def get_model(num_classes=2, pretrained=True, fine_tune=True, device=None):
    """
    Build the model and move it to the correct device.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model = MobileNetMaskClassifier(
        num_classes=num_classes, pretrained=pretrained, fine_tune=fine_tune
    )

    return model.to(device)


if __name__ == "__main__":
    # Quick test
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    model = get_model(device=device)
    dummy = torch.randn(4, 3, 224, 224).to(device)
    out = model(dummy)
    print("Output shape:", out.shape)  # should be [4, 2]
