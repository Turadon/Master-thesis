import os
from PIL import Image
from torch.utils.data import Dataset, Subset
import numpy as np
import pydicom
from skimage.exposure import match_histograms
from torch.utils.data import DataLoader
import torch
import albumentations as A
from albumentations.pytorch import ToTensorV2

TRAIN_IMAGE_DIR = r'/home/alex/Documents/new try/Data/Lung Unet/data/train/images' #r'.\data\train\images'
TRAIN_MASKS_DIR = r'/home/alex/Documents/new try/Data/Lung Unet/data/train/masks' #r'.\data\train\masks'
TEST_IMAGE_DIR = r'/home/alex/Documents/new try/Data/Lung Unet/data/test/images' #r'.\data\test\images'
TEST_MASKS_DIR = r'/home/alex/Documents/new try/Data/Lung Unet/data/test/masks' #r'.\data\test\masks'
IMAGE_SIZE = 256
BATCH_SIZE = 8


class LungDataset_simulated(Dataset):
    def __init__(self, dir_images, dir_masks, image_std, noise_std_ratio, transform=None):
        self.transform = transform
        self.dir_images = dir_images
        self.dir_masks = dir_masks
        self.image_std = image_std
        self.noise_std_ratio = noise_std_ratio
        self.images = sorted(os.listdir(dir_images))
        self.masks = sorted(os.listdir(dir_masks))

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = os.path.join(self.dir_images, self.images[idx])
        mask_path = os.path.join(self.dir_masks, self.masks[idx])
        image = np.array(Image.open(img_path).convert('L'))
        mask = np.array(Image.open(mask_path).convert('L'))
        s = np.random.normal(130, self.image_std, (2995, 2993)).astype(int)
        matched = match_histograms(image, s)
        if self.transform is not None:
            transform_output = (self.transform(image=matched, mask=mask))
            matched = transform_output["image"]
            mask = transform_output["mask"]
        gaussian_noise = torch.normal(0, self.image_std / self.noise_std_ratio, matched.shape)
        matched_gaussian = matched + gaussian_noise
        return matched_gaussian.to(torch.float)/255, mask.unsqueeze(0)/255

transform_padding = A.Compose(
    [
        A.Resize(height=256, width=256),
        A.CropAndPad(px = 40, keep_size=True),
        A.Rotate(limit= 15, p = 0.5),
        ToTensorV2(),
    ],
)

transform_test_padding = A.Compose(
    [
        A.Resize(height=256, width=256),
        A.CropAndPad(px = 40, keep_size=True),
        ToTensorV2(),
    ],
)

def get_loaders_simulated(
    batch_size=BATCH_SIZE,
    train_transform = transform_padding,
    test_transform = transform_test_padding,
    train_dir=TRAIN_IMAGE_DIR,
    train_maskdir=TRAIN_MASKS_DIR,
    test_dir=TEST_IMAGE_DIR,
    test_maskdir=TEST_MASKS_DIR,
    image_std = 13, 
    noise_std_ratio = 2,
    num_workers=0,
    pin_memory=False
):
    train_ds = LungDataset_simulated(
        train_dir,
        train_maskdir,
        image_std, 
        noise_std_ratio,
        transform=train_transform,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=pin_memory,
        shuffle=True,
    )

    test_ds = LungDataset_simulated(
        test_dir,
        test_maskdir,
        image_std, 
        noise_std_ratio,
        transform=test_transform,
    )

    test_size =  test_ds.__len__()
    validation_indices = list(range(test_size))[:int(test_size/2)]
    test_indices = list(range(test_size))[int(test_size/2):]

    test_loader = DataLoader(
        Subset(test_ds, test_indices),
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=pin_memory,
        shuffle=False,
    )

    validation_loader = DataLoader(
        Subset(test_ds, validation_indices),
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=pin_memory,
        shuffle=False,
    )

    return train_loader, test_loader, validation_loader