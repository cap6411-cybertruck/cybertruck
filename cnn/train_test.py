import cv2
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from torchvision import transforms

def visualize_roi(roi):
    roi = roi.cpu().numpy().transpose(1, 2, 0)
    roi_img = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)

    # Display the ROI
    cv2.imshow("Region of Interest", roi_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def extract_detection(images, results, target):
    data_list = []
    target_list = []

    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224,224)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,0.5,0.5), (0.5,0.5,0.5))
    ])

    for idx, result in enumerate(results):
        num_boxes = len(result.boxes)

        for box in result.boxes.xyxy:
            
            # Convert normalized coordinates to absolute coordinates
            x_min, y_min, x_max, y_max = box
        
            # Convert normalized coordinates to absolute coordinates
            x_min = int(x_min)
            y_min = int(y_min)
            x_max = int(x_max)
            y_max = int(y_max)

            roi = images[idx][:,y_min:y_max, x_min:x_max] 
            # visualize_roi(roi)
            data_list.append(roi)
        
        # Add target for each box
        target_list.extend([target[idx]] * num_boxes)

    # Upsample data to 224x224, normalize, and create tensors
    data = torch.stack([transform(data) for data in data_list])
    data = data.to('cuda')

    target = torch.stack(target_list)

    return data, target            
        


def train(model, detector, device, train_loader, optimizer, criterion, epoch, batch_size):
    '''
    Trains the model for an epoch and optimizes it.
    model: The model to train. Should already be in correct device.
    device: 'cuda' or 'cpu'.
    train_loader: dataloader for training samples.
    optimizer: optimizer to use for model parameter updates.
    criterion: used to compute loss for prediction and target 
    epoch: Current epoch to train for.
    batch_size: Batch size to be used.
    '''
    
    # Set model to train mode before each epoch
    model.train()
    
    # Empty list to store losses 
    losses = []
    correct, total = 0, 0
    
    
    # Iterate over entire training samples (1 epoch
    for batch_idx, batch_sample in enumerate(train_loader):
        data, target = batch_sample
        
        # Push data/label to correct device
        data, target = data.to(device), target.to(device)

        detection = detector(data, verbose=False)
        rois, target = extract_detection(data, detection, target)
        
        # Reset optimizer gradients. Avoids grad accumulation (accumulation used in RNN).
        optimizer.zero_grad()
        
        # Do forward pass for current set of data
        output = model(rois)
        
        # ======================================================================
        # Compute loss based on criterion
        loss = criterion(output,target)
        
        # Computes gradient based on final loss
        loss.backward()
        
        # Store loss
        losses.append(loss.item())
        
        # Optimize model parameters based on learning rate and gradient 
        optimizer.step()
        
        # Get predicted index by selecting maximum log-probability
        pred = output.argmax(dim=1, keepdim=True)
        total += len(target)
        # ======================================================================
        # Count correct predictions overall 
        correct += pred.eq(target.view_as(pred)).sum().item()
        
    train_loss = float(np.mean(losses))
    train_acc = (correct / total) * 100
    print(f'Epoch {epoch}: Average loss: {float(np.mean(losses)):.4f}, Accuracy: {correct}/{total} ({train_acc:.0f}%)\n')
    return train_loss, train_acc
    


def test(model, detector, device, test_loader):
    '''
    Tests the model.
    model: The model to train. Should already be in correct device.
    device: 'cuda' or 'cpu'.
    test_loader: dataloader for test samples.
    '''
    
    # Set model to eval mode to notify all layers.
    model.eval()
    
    losses = []
    correct, total = 0, 0
    
    # Set torch.no_grad() to disable gradient computation and backpropagation
    with torch.no_grad():
        for  sample in test_loader:
            data, target = sample
            data, target = data.to(device), target.to(device)
            
            detection = detector(data)
            rois, target = extract_detection(data, detection, target)
            rois.to(device)

            # Predict for data by doing forward pass
            output = model(rois)
            
            # ======================================================================
            # Compute loss based on same criterion as training
            criterion = nn.CrossEntropyLoss()
            
            # Compute loss based on same criterion as training 
            loss = criterion(output,target)
            
            # Append loss to overall test loss
            losses.append(loss.item())
            
            # Get predicted index by selecting maximum log-probability
            pred = output.argmax(dim=1, keepdim=True)
            total += len(target)
            # ======================================================================
            # Count correct predictions overall 
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss = float(np.mean(losses))
    accuracy = 100. * (correct / total)

    print(f'\nTest set: Average loss: {test_loss:.4f}, Accuracy: {correct}/{total} ({accuracy:.0f}%)\n')
    
    return test_loss, accuracy

def plot_accuracies(train_acc, test_acc, mode, x_len):
    '''
    Plots the accuracies
    train_acc: Array-like. Contains all of training accuracies
    test_acc: Array-like. Contains all of the test accuracies
    mode: str. Needed to add to title.
    x_len: int. Number of epochs.  Used to define length of x-axis.
    '''
    fig = plt.figure(figsize=(15, 5))
    x_axis = np.linspace(1,x_len,x_len)
    ax = fig.add_subplot(1, 2, 1)
    ax.plot(x_axis, train_acc,'b-',zorder=1,label='Training')
    ax.scatter(x_axis, train_acc,c='white',edgecolors='blue',zorder=2)

    ax.plot(x_axis, test_acc,'r-',zorder=1,label='Test')
    ax.scatter(x_axis, test_acc,c='white',edgecolors='red',zorder=2)
    ax.set_title("Model " + mode)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Accuracy")
    ax.legend(loc=4)
    ax.grid(alpha=0.05)