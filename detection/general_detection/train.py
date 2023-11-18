from detection.cnn.dataset import V2Dataset

import torch

from torchvision.models.resnet import ResNet, Bottleneck, resnet50
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm
from torch import nn
import numpy as np

def train_one_epoch(model: ResNet, device: torch.device, criterion, data_loader: DataLoader):
  if not model.training:
    raise Exception("Model must be in training mode in order to train.")
  
  losses = []
  correct, total = 0, 0

  for batch in tqdm(data_loader):
    input, target = batch

    input, target = input.to(device), target.to(device)

    # Forward pass of input
    output = model(input)

    # Compute loss
    loss = criterion(output, target)

    # Backward pass
    loss.backward()

    losses.append(loss.item())

    print(target)

    pred = output.argmax(dim=1, keepdim=True)
    total += len(target)

    correct += pred.eq(target.view_as(pred)).sum().item()

  train_loss = float(np.mean(losses))
  train_acc = (correct / total) * 100

  return train_loss, train_acc


if __name__ == '__main__':
  model = resnet50(num_classes=10)
  device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
  model.to(device)
  model.train()

  transform = transforms.Compose([
        transforms.Resize((224,224)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,0.5,0.5), (0.5,0.5,0.5))
  ])

  criterion = nn.CrossEntropyLoss()

  train_dataset = V2Dataset(cam1_path="./data/v2_cam1_cam2_split_by_driver/Camera 1/train", cam2_path="./data/v2_cam1_cam2_split_by_driver/Camera 2/train", transform=transform)
  train_dataloader = DataLoader(train_dataset, batch_size=64, shuffle=True)

  epochs = 100

  for epoch in tqdm(range(epochs)):
    loss, train_acc = train_one_epoch(model=model, device=device, data_loader=train_dataloader, criterion=criterion)  

    # Log statistics
    print(f"Epoch {epoch} loss = {float(np.mean(loss))}, train accuracy = {train_acc}")



  




  
  